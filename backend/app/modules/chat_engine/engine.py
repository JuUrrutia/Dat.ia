import time
import re
import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_DEMO_ROLE, ROLE_USUARIO, ADMIN_ROLES
from app.modules.chat_engine.schemas import QueryResponse, PresentationHints
from app.modules.chat_engine.ast_validator import ASTValidator, ASTValidationError
from app.modules.chat_engine.intent_classifier import IntentClassifier
from app.modules.chat_engine.kpi_calculator import KPICalculator, is_true_numeric_metric
from app.modules.chat_engine.response_builder import ResponseBuilder
from app.modules.chat_engine.sql_executor import SQLExecutor
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.catalog.services.null_manager import NullManagerService
from app.modules.chat_engine.governance_guard import GovernanceGuard
from app.modules.chat_engine.suggestions_service import SuggestionsService
from app.modules.chat_engine.sql_generator import SQLGenerator
from app.modules.chat_engine.null_handler import NullHandler

logger = logging.getLogger(__name__)

class QueryEngine:
    """
    Unified Orchestrator for DATIA conversational analytics and data democratization.
    Delegates domain governance, intent classification, SQL generation, execution,
    null remediation, and visualization to specialized modules.
    """

    # --- Governance & RBAC Facade ---
    get_allowed_tables_for_role = GovernanceGuard.get_allowed_tables_for_role
    get_blocked_columns_for_role = GovernanceGuard.get_blocked_columns_for_role
    check_domain_governance = GovernanceGuard.check_domain_governance

    # --- Suggestions Facade ---
    get_dynamic_suggestions_with_llm = SuggestionsService.get_dynamic_suggestions_with_llm
    get_dynamic_suggestions = SuggestionsService.get_dynamic_suggestions

    # --- Null & Remediation Facade ---
    _detect_remediation_intent = NullHandler.detect_remediation_intent
    _apply_in_memory_null_remediation = NullManagerService.apply_in_memory_remediation

    # --- Response & Intent Facade ---
    _build_llm_offline_response = ResponseBuilder.build_llm_offline_response
    _build_rbac_denied_response = ResponseBuilder.build_rbac_denied_response
    _classify_intent = IntentClassifier.classify_intent
    _classify_presentation_format = IntentClassifier.classify_presentation_format
    _heuristic_presentation_hints = IntentClassifier.heuristic_presentation_hints
    _generate_conversational_response = IntentClassifier.generate_conversational_response
    _generate_deep_executive_report_with_llm = KPICalculator.generate_deep_executive_report_with_llm
    _build_dynamic_visualization = KPICalculator.build_dynamic_visualization
    _get_grounding_query_for_question = SQLExecutor.get_grounding_query
    _retrieve_few_shot_memories = SQLExecutor.retrieve_few_shot_memories
    _persist_learning_memory = SQLExecutor.persist_learning_memory

    @classmethod
    def _extract_suggested_questions(
        cls,
        conversational: Optional[str],
        rows: List[Dict[str, Any]],
        columns: List[str],
        tables_used: List[str]
    ) -> Tuple[List[str], Optional[str]]:
        """
        Extracts <preguntas_sugeridas> tags or markdown question headers from conversational response,
        cleaning up the text body. Falls back to physical metric-derived questions if empty.
        """
        suggested: List[str] = []
        cleaned_conversational = conversational

        if cleaned_conversational:
            sugg_match = re.search(r'<preguntas_sugeridas>\s*(.*?)\s*</preguntas_sugeridas>', cleaned_conversational, re.DOTALL | re.IGNORECASE)
            if sugg_match:
                raw_suggs = sugg_match.group(1).strip().split("\n")
                suggested = [re.sub(r'^[-*0-9.)\s]+', '', s).strip() for s in raw_suggs if s.strip()]
                cleaned_conversational = re.sub(r'<preguntas_sugeridas>[\s\S]*?</preguntas_sugeridas>', '', cleaned_conversational).strip()

            text_sugg_match = re.search(r'(?:###?\s*)?(?:Preguntas\s+de\s+Profundización|Próximas\s+Preguntas|Preguntas\s+Sugeridas)[\s:]*([\s\S]*)$', cleaned_conversational, re.IGNORECASE)
            if text_sugg_match:
                lines = [re.sub(r'^[-*0-9.)\s]+', '', l).strip() for l in text_sugg_match.group(1).strip().split("\n") if l.strip()]
                if not suggested and lines:
                    suggested = [l for l in lines if l.startswith("¿") or len(l) > 10][:3]
                cleaned_conversational = cleaned_conversational[:text_sugg_match.start()].strip()

        if not suggested and rows and columns:
            first_col = columns[0]
            num_cols = [c for c in columns if is_true_numeric_metric(c, rows[0].get(c))]
            if num_cols:
                suggested = [
                    f"¿Cuál es la evolución temporal de {num_cols[0]}?",
                    f"¿Cómo se distribuye {num_cols[0]} según {first_col}?",
                    f"¿Cuáles son los valores más destacados de {num_cols[0]}?"
                ]
            else:
                table_label = tables_used[0] if tables_used else "esta tabla"
                suggested = [
                    f"¿Cuántos registros totales existen en {table_label}?",
                    f"¿Cuáles son los registros más recientes?",
                    f"¿Cómo se desglosan por {first_col}?"
                ]

        return suggested, cleaned_conversational

    @classmethod
    async def execute_query(
        cls,
        question: str,
        user_role: str = DEFAULT_DEMO_ROLE,
        is_admin: bool = False,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> QueryResponse:

        # 1. Null remediation directive resolution
        remediation_action = NullHandler.detect_remediation_intent(question)
        original_question = None
        original_sql = None

        if remediation_action:
            m_para = re.search(r'(?:para|sobre)\s+la\s+consulta:\s*[\'"]?([^\r\n]+?)[\'"]?$', question, re.IGNORECASE)
            if m_para:
                original_question = m_para.group(1).strip()

            if conversation_history:
                for turn in reversed(conversation_history):
                    t_q = turn.get("question", "").strip()
                    if t_q and not NullHandler.detect_remediation_intent(t_q):
                        if not original_question:
                            original_question = t_q
                        if turn.get("sql") and not original_sql:
                            original_sql = turn.get("sql")
                        break

        effective_question = original_question or question

        # 2. RBAC check for unassigned "Usuario" role
        if not is_admin and (user_role == ROLE_USUARIO or not user_role):
            return ResponseBuilder.build_rbac_denied_response(
                effective_question,
                "Tu cuenta se encuentra registrada con el perfil inicial 'Usuario'. Un Administrador debe asignarte un rol (Economista o TI) para acceder a los datos corporativos."
            )

        allowed_tables = cls.get_allowed_tables_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)

        # 3. Strict Cross-Domain RBAC Governance Check (Defense Layer 1 - Fail Closed)
        if not is_admin and user_role not in ADMIN_ROLES:
            domain_denial = cls.check_domain_governance(effective_question, user_role, allowed_tables)
            if domain_denial:
                return ResponseBuilder.build_rbac_denied_response(effective_question, domain_denial)

        if not allowed_tables and not is_admin:
            return ResponseBuilder.build_rbac_denied_response(
                effective_question,
                f"El rol '{user_role}' no tiene tablas asignadas en la matriz RBAC."
            )

        # 4. Intent Classification
        response_type = await IntentClassifier.classify_intent(effective_question)

        # BRANCH 0: Greeting
        if response_type == "greeting" and not remediation_action:
            clarification_opts = IntentClassifier.detect_ambiguity_and_options(effective_question, allowed_tables)
            conversational = await IntentClassifier.generate_conversational_response(
                effective_question, user_role, "greeting", columns=list(allowed_tables), is_llm_active=True
            )
            return ResponseBuilder.build_greeting_response(
                effective_question, user_role, allowed_tables, conversational, clarification_options=clarification_opts
            )

        # BRANCH 0.1: Out of scope capabilities
        if response_type == "out_of_scope" and not remediation_action:
            conversational = await IntentClassifier.generate_conversational_response(
                effective_question, user_role, "out_of_scope", columns=list(allowed_tables), is_llm_active=True
            )
            return ResponseBuilder.build_out_of_scope_response(
                effective_question, user_role, allowed_tables, conversational
            )

        blocked_columns = cls.get_blocked_columns_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)
        start_time = time.time()
        is_llm_active = False

        # 5. Resolve active connection and target dialect
        conn_record = None
        if db is not None:
            try:
                from app.modules.admin_catalog.models import CorporateConnection
                if connection_id:
                    conn_record = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
                if not conn_record:
                    conn_record = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).order_by(CorporateConnection.id.desc()).first()
                if not conn_record:
                    conn_record = db.query(CorporateConnection).order_by(CorporateConnection.id.desc()).first()
            except Exception:
                pass

        if remediation_action and conn_record and db:
            try:
                NullManagerService.apply_null_policy(conn_record, remediation_action, db)
                conn_record.null_policy = 'open'
                db.commit()
            except Exception as ex:
                logger.warning(f"Error applying null remediation to DB: {ex}")

        is_pg = conn_record is not None and str(getattr(conn_record, "db_type", "")).lower() == "postgresql"
        engine_dialect = "postgres" if is_pg else "sqlite"
        target_db_path = DynamicSchemaPruningService.resolve_db_path(db, connection_id)
        exec_target = conn_record if is_pg else target_db_path

        table_columns_map: Dict[str, List[str]] = {}
        for tbl in allowed_tables:
            phys_cols_info = DynamicSchemaPruningService.get_physical_table_columns(
                tbl, db_path=exec_target, include_samples=False
            )
            table_columns_map[tbl.lower()] = [c["name"] for c in phys_cols_info if "name" in c]

        # BRANCH A: Conversational Assistant
        if response_type == "conversational" and not remediation_action:
            grounding_sql = SQLExecutor.get_grounding_query(effective_question, user_role, allowed_tables)
            try:
                _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                    grounding_sql,
                    dialect=engine_dialect,
                    allowed_tables=allowed_tables,
                    blocked_columns=blocked_columns,
                    table_columns=table_columns_map
                )
                rows = SQLExecutor.execute_raw_sql(exec_target, secured_sql, dialect=engine_dialect)
            except ASTValidationError:
                secured_sql = "-- CONSULTA NO AUTORIZADA POR GOBERNANZA RBAC"
                meta = {"tables_used": []}
                rows = []
            except Exception:
                rows = []

            exec_time_ms = int((time.time() - start_time) * 1000)
            conversational = await IntentClassifier.generate_conversational_response(
                effective_question, user_role, "conversational", rows, list(rows[0].keys()) if rows else [], is_llm_active=True
            )

            if not conversational:
                return ResponseBuilder.build_llm_offline_response(effective_question, exec_time_ms)

            suggested_questions, conversational = cls._extract_suggested_questions(
                conversational, rows, list(rows[0].keys()) if rows else [], meta.get("tables_used", list(allowed_tables))
            )

            clarification_opts = IntentClassifier.detect_ambiguity_and_options(effective_question, allowed_tables)
            anomalies_detected = KPICalculator.detect_statistical_anomalies(rows, list(rows[0].keys()) if rows else [])
            sql_explanation = ASTValidator.generate_sql_explanation(secured_sql, dialect=engine_dialect)

            return ResponseBuilder.build_conversational_response(
                effective_question, user_role, secured_sql, rows, meta, conversational, exec_time_ms, allowed_tables,
                suggested_questions=suggested_questions,
                clarification_options=clarification_opts,
                anomalies_detected=anomalies_detected,
                sql_explanation=sql_explanation
            )

        # BRANCH B: Data Analysis / Report / Hybrid
        candidate_sql = None
        thinking_process: Optional[str] = None
        schema_context = ""

        if remediation_action and original_sql:
            candidate_sql = original_sql
            is_llm_active = True
        else:
            q_strip = effective_question.strip().rstrip(';')
            if q_strip.upper().startswith(("SELECT", "WITH", "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE")):
                try:
                    _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                        q_strip,
                        dialect=engine_dialect,
                        allowed_tables=allowed_tables,
                        blocked_columns=blocked_columns,
                        table_columns=table_columns_map
                    )
                    candidate_sql = secured_sql
                    is_llm_active = True
                except ASTValidationError as e:
                    return ResponseBuilder.build_rbac_denied_response(effective_question, str(e))

        if not candidate_sql:
            candidate_sql, thinking_process, rbac_denial, schema_context, is_llm_active = await SQLGenerator.generate_candidate_sql(
                question=effective_question,
                user_role=user_role,
                allowed_tables=allowed_tables,
                db=db,
                role_id=role_id,
                connection_id=connection_id,
                is_admin=is_admin,
                conversation_history=conversation_history
            )
            if rbac_denial:
                return ResponseBuilder.build_rbac_denied_response(effective_question, rbac_denial)

        if not candidate_sql or not is_llm_active:
            exec_time_ms = int((time.time() - start_time) * 1000)
            return ResponseBuilder.build_llm_offline_response(effective_question, exec_time_ms)

        # 6. SQL Execution & Self-Healing
        try:
            rows, secured_sql, meta, was_self_healed, validation_label = await SQLExecutor.execute_with_self_healing(
                target_db_path=exec_target,
                question=effective_question,
                initial_sql=candidate_sql,
                allowed_tables=allowed_tables,
                blocked_columns=blocked_columns,
                table_columns_map=table_columns_map,
                schema_context=schema_context,
                is_llm_active=is_llm_active,
                dialect=engine_dialect
            )
        except Exception as e:
            return ResponseBuilder.build_rbac_denied_response(effective_question, str(e))

        SQLExecutor.persist_learning_memory(
            db=db,
            question=effective_question,
            sql=secured_sql,
            connection_id=connection_id,
            user_role=user_role,
            tables_used=meta.get("tables_used", list(allowed_tables)),
            was_healed=was_self_healed
        )

        exec_time_ms = int((time.time() - start_time) * 1000)
        columns = list(rows[0].keys()) if rows else []

        # 7. Null Detection & Interactive Remediation
        nulls_detected: Optional[Dict[str, Any]] = None
        null_cols_in_rows, null_rows_count = NullHandler.inspect_nulls(rows)
        conn_policy = getattr(conn_record, 'null_policy', 'open') or 'open'
        is_remediation = bool(remediation_action)

        if remediation_action and null_cols_in_rows:
            rows = NullManagerService.apply_in_memory_remediation(rows, columns, remediation_action)
            null_cols_in_rows = set()
            null_rows_count = 0

        # Early pause on Prompt 1 when nulls are found under policy 'open'
        if null_rows_count > 0 and conn_policy == 'open' and not is_remediation:
            primary_table = meta.get("tables_used", ["la tabla"])[0] if meta.get("tables_used") else "la tabla activa"
            nulls_detected, conversational = NullHandler.build_null_alert_payload(
                rows, null_cols_in_rows, null_rows_count, primary_table, effective_question
            )
            pres_hints = PresentationHints(
                show_executive_report=False, show_kpis=False, show_chart=False,
                preferred_view="assistant", summary_style="detailed"
            )
            sql_explanation = ASTValidator.generate_sql_explanation(secured_sql, dialect=engine_dialect)

            return ResponseBuilder.build_analytics_response(
                question=effective_question,
                response_type=response_type,
                rows=rows,
                columns=columns,
                meta=meta,
                allowed_tables=allowed_tables,
                secured_sql=secured_sql,
                validation_label=validation_label,
                exec_time_ms=exec_time_ms,
                is_llm_active=is_llm_active,
                pres_hints=pres_hints,
                kpis=[],
                chart_type="none",
                chart_option={"series": []},
                final_summary=conversational,
                final_exec_report=None,
                conversational=conversational,
                thinking_process=thinking_process,
                suggested_questions=[],
                clarification_options=[],
                anomalies_detected=[],
                sql_explanation=sql_explanation,
                nulls_detected=nulls_detected
            )

        # 8. Visual Presentation & Semantic Synthesis
        pres_hints = await IntentClassifier.classify_presentation_format(
            effective_question, response_type, rows, columns
        )

        kpis, chart_type, chart_option, fallback_summary, fallback_exec_report = KPICalculator.build_dynamic_visualization(
            effective_question, columns, rows, user_role
        )
        final_exec_report = fallback_exec_report

        if is_llm_active:
            semantic_res = await KPICalculator.generate_semantic_analysis_with_llm(
                question=effective_question,
                user_role=user_role,
                rows=rows,
                columns=columns,
                secured_sql=secured_sql,
                schema_context=schema_context,
                is_llm_active=is_llm_active
            )
            if semantic_res:
                kpis, semantic_overview, final_exec_report = semantic_res
                fallback_summary = semantic_overview
            elif pres_hints.show_executive_report:
                llm_exec_report = await KPICalculator.generate_deep_executive_report_with_llm(
                    effective_question, user_role, rows, columns, secured_sql, is_llm_active
                )
                if llm_exec_report:
                    final_exec_report = llm_exec_report

        if not pres_hints.show_executive_report:
            final_exec_report = None
        if not pres_hints.show_kpis:
            kpis = []
        if not pres_hints.show_chart:
            chart_type = "none"
            chart_option = {"series": []}

        conversational = await IntentClassifier.generate_conversational_response(
            effective_question, user_role, response_type, rows, columns, is_llm_active
        )

        if is_remediation:
            banner = NullHandler.format_remediation_banner(remediation_action, effective_question)
            conversational = (banner + conversational) if conversational else banner
            if fallback_summary:
                fallback_summary = banner + fallback_summary

        suggested_questions, conversational = cls._extract_suggested_questions(
            conversational, rows, columns, meta.get("tables_used", list(allowed_tables))
        )

        clarification_opts = IntentClassifier.detect_ambiguity_and_options(effective_question, allowed_tables)
        anomalies_detected = KPICalculator.detect_statistical_anomalies(rows, columns)
        sql_explanation = ASTValidator.generate_sql_explanation(secured_sql, dialect=engine_dialect)

        if conversational:
            first_block = conversational.split("\n\n")[0].replace("#", "").strip()
            final_summary = first_block if len(first_block) > 10 else fallback_summary
            if pres_hints.preferred_view in ("table", "report") or response_type in ("data_analysis", "conversational", "advisory", "explanation", "hybrid"):
                pres_hints.preferred_view = "assistant"
        elif pres_hints.summary_style == "executive" and final_exec_report and final_exec_report.overview:
            final_summary = final_exec_report.overview
        elif pres_hints.summary_style == "concise":
            final_summary = f"Se obtuvieron {len(rows)} registros de {', '.join(meta.get('tables_used', []))} para la consulta '{effective_question}'."
        else:
            final_summary = final_exec_report.overview if final_exec_report and final_exec_report.overview else fallback_summary

        return ResponseBuilder.build_analytics_response(
            question=effective_question,
            response_type=response_type,
            rows=rows,
            columns=columns,
            meta=meta,
            allowed_tables=allowed_tables,
            secured_sql=secured_sql,
            validation_label=validation_label,
            exec_time_ms=exec_time_ms,
            is_llm_active=is_llm_active,
            pres_hints=pres_hints,
            kpis=kpis,
            chart_type=chart_type,
            chart_option=chart_option,
            final_summary=final_summary,
            final_exec_report=final_exec_report,
            conversational=conversational,
            thinking_process=thinking_process,
            suggested_questions=suggested_questions,
            clarification_options=clarification_opts,
            anomalies_detected=anomalies_detected,
            sql_explanation=sql_explanation,
            nulls_detected=nulls_detected
        )
