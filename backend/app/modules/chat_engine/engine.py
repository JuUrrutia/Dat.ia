import os
import time
import re
from typing import Dict, Any, List, Set, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ADMIN_ROLES, ROLE_USUARIO, DEFAULT_DEMO_ROLE
from app.modules.chat_engine.ast_validator import ASTValidator, ASTValidationError
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.core.prompts import PromptManager
from app.modules.chat_engine.schemas import QueryResponse
from app.modules.chat_engine.intent_classifier import IntentClassifier
from app.modules.chat_engine.sql_executor import SQLExecutor
from app.modules.chat_engine.kpi_calculator import KPICalculator
from app.modules.chat_engine.response_builder import ResponseBuilder

DEMO_DB_PATH = settings.SQLITE_DB_PATH

class QueryEngine:
    """
    Refactored, modularized Dynamic Query Engine.
    Orchestrates IntentClassifier, DynamicSchemaPruningService, ASTValidator,
    PromptManager, LLMService, SQLExecutor, KPICalculator, and ResponseBuilder.
    """

    @classmethod
    def get_allowed_tables_for_role(
        cls,
        user_role: str,
        is_admin: bool,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1
    ) -> Set[str]:
        if is_admin or user_role in ADMIN_ROLES:
            is_admin = True

        local_db = None
        if db is None:
            try:
                from app.core.database import SessionLocal
                local_db = SessionLocal()
                active_db = local_db
            except Exception:
                active_db = None
        else:
            active_db = db

        if active_db is not None:
            try:
                schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=active_db,
                    role_id=role_id,
                    user_role=user_role,
                    connection_id=connection_id,
                    is_admin=is_admin
                )
                return schema_info.get("allowed_tables", set())
            except Exception:
                return set()
            finally:
                if local_db is not None:
                    local_db.close()

        return set()

    @classmethod
    def get_blocked_columns_for_role(
        cls,
        user_role: str,
        is_admin: bool,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1
    ) -> Set[str]:
        if is_admin or user_role in ADMIN_ROLES:
            return set()

        local_db = None
        if db is None:
            try:
                from app.core.database import SessionLocal
                local_db = SessionLocal()
                active_db = local_db
            except Exception:
                active_db = None
        else:
            active_db = db

        if active_db is not None:
            try:
                schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=active_db,
                    role_id=role_id,
                    user_role=user_role,
                    connection_id=connection_id,
                    is_admin=is_admin
                )
                return schema_info.get("blocked_columns", set())
            except Exception:
                return set()
            finally:
                if local_db is not None:
                    local_db.close()

        return set()

    @classmethod
    async def get_dynamic_suggestions_with_llm(
        cls,
        user_role: str,
        allowed_tables: Set[str],
        schema_prompt: str = ""
    ) -> List[str]:
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        try:
            system_prompt = PromptManager.get_suggestions_system_prompt()
            tables_str = ", ".join(sorted(allowed_tables))
            prompt_llm = f"""Perfil del usuario: {user_role}
Base de datos activa ({tables_str}):

{schema_prompt}

Genera 4 sugerencias simples y breves de preguntas sobre ESTA base de datos activa."""

            llm_text = await LLMService.generate_completion(
                prompt_llm,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=150
            )

            if llm_text:
                lines = [line.strip() for line in llm_text.split('\n') if line.strip()]
                clean_suggestions = []
                for line in lines:
                    line_clean = re.sub(r'^[\d\.\-\*\•\>\s]+', '', line).strip()
                    line_clean = line_clean.strip('"\'')
                    if len(line_clean) > 8 and ('?' in line_clean or '¿' in line_clean or any(k in line_clean.lower() for k in ['cuál', 'cuanto', 'mostrar', 'total', 'ventas', 'resumen', 'promedio', 'ingreso', 'costo', 'listar'])):
                        clean_suggestions.append(line_clean)
                if len(clean_suggestions) >= 2:
                    return clean_suggestions[:4]
        except Exception:
            pass

        return cls.get_dynamic_suggestions(user_role, allowed_tables)

    @classmethod
    def get_dynamic_suggestions(cls, user_role: str, allowed_tables: Set[str]) -> List[str]:
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        suggestions = []
        sorted_tables = sorted(list(allowed_tables), key=lambda t: (0 if t.lower().startswith("fact_") else 1, t.lower()))

        templates = [
            "📊 Distribución y resumen de registros en {name}",
            "📈 Métricas acumuladas y evolución en {name}",
            "📋 Listado detallado y consulta de {name}",
            "💡 Indicadores clave y registros principales de {name}"
        ]

        for i, tbl in enumerate(sorted_tables):
            clean_name = tbl
            for prefix in ["fact_", "dim_", "tbl_", "table_"]:
                if clean_name.lower().startswith(prefix):
                    clean_name = clean_name[len(prefix):]
                    break
            clean_spaced = clean_name.replace("_", " ").strip()

            tmpl = templates[i % len(templates)]
            suggestions.append(tmpl.format(name=clean_spaced))

            if len(sorted_tables) == 1:
                suggestions.append(f"🔍 Top registros con mayores valores en {clean_spaced}")
                suggestions.append(f"⚡ Totales agregados y promedio general de {clean_spaced}")

        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique[:4]

    # Delegates to ResponseBuilder
    _build_llm_offline_response = ResponseBuilder.build_llm_offline_response
    _build_rbac_denied_response = ResponseBuilder.build_rbac_denied_response

    @classmethod
    async def execute_query(
        cls,
        question: str,
        user_role: str = DEFAULT_DEMO_ROLE,
        is_admin: bool = False,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1
    ) -> QueryResponse:

        # 1. RBAC check for unassigned "Usuario" role
        if not is_admin and (user_role == ROLE_USUARIO or not user_role):
            return ResponseBuilder.build_rbac_denied_response(
                question,
                "Tu cuenta se encuentra registrada con el perfil inicial 'Usuario'. Un Administrador debe asignarte un rol (Economista o TI) para acceder a los datos corporativos."
            )

        allowed_tables = cls.get_allowed_tables_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)
        if not allowed_tables:
            return ResponseBuilder.build_rbac_denied_response(
                question,
                f"El rol '{user_role}' no tiene tablas asignadas en la matriz RBAC."
            )

        blocked_columns = cls.get_blocked_columns_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)
        start_time = time.time()
        is_llm_active = False

        # 2. INTENT CLASSIFICATION
        response_type = await IntentClassifier.classify_intent(question)

        if not os.path.exists(DEMO_DB_PATH):
            from setup_demo_db import setup_demo_sqlite
            setup_demo_sqlite()

        target_db_path = DynamicSchemaPruningService.resolve_db_path(db, connection_id)

        table_columns_map: Dict[str, List[str]] = {}
        for tbl in allowed_tables:
            phys_cols_info = DynamicSchemaPruningService.get_physical_table_columns(
                tbl, db_path=target_db_path, include_samples=False
            )
            table_columns_map[tbl.lower()] = [c["name"] for c in phys_cols_info if "name" in c]

        # BRANCH 0: GREETING / GENERAL CONVERSATION
        if response_type == "greeting":
            conversational = await IntentClassifier.generate_conversational_response(
                question, user_role, "greeting", columns=list(allowed_tables), is_llm_active=True
            )
            return ResponseBuilder.build_greeting_response(
                question, user_role, allowed_tables, conversational
            )

        # BRANCH A: CONVERSATIONAL ASSISTANT
        if response_type == "conversational":
            grounding_sql = SQLExecutor.get_grounding_query(question, user_role, allowed_tables)
            try:
                _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                    grounding_sql,
                    dialect="sqlite",
                    allowed_tables=allowed_tables,
                    blocked_columns=blocked_columns,
                    table_columns=table_columns_map
                )
            except ASTValidationError:
                secured_sql = grounding_sql
                meta = {"tables_used": list(allowed_tables)}

            try:
                rows = SQLExecutor.execute_raw_sql(target_db_path, secured_sql)
            except Exception:
                rows = []

            exec_time_ms = int((time.time() - start_time) * 1000)
            conversational = await IntentClassifier.generate_conversational_response(
                question, user_role, "conversational", rows, list(rows[0].keys()) if rows else [], is_llm_active=True
            )

            if not conversational:
                return ResponseBuilder.build_llm_offline_response(question, exec_time_ms)

            return ResponseBuilder.build_conversational_response(
                question, user_role, secured_sql, rows, meta, conversational, exec_time_ms, allowed_tables
            )

        # BRANCH B: DATA ANALYSIS / REPORT / HYBRID
        conn_record = None
        if db is not None:
            try:
                from app.models.connection import CorporateConnection, DatabaseType
                conn_record = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
            except Exception:
                pass

        is_pg = conn_record is not None and (conn_record.db_type == DatabaseType.POSTGRESQL or str(conn_record.db_type).lower() == "postgresql")
        engine_dialect = "postgres" if is_pg else "sqlite"
        exec_target = conn_record if is_pg else target_db_path

        q_strip = question.strip().rstrip(';')
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
                return ResponseBuilder.build_rbac_denied_response(question, str(e))
        else:
            candidate_sql = None

        schema_context = ""
        if not candidate_sql:
            try:
                s_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=db,
                    role_id=role_id,
                    user_role=user_role,
                    connection_id=connection_id,
                    is_admin=is_admin
                )
                schema_context = s_info.get("schema_prompt", "")
            except Exception:
                pass

        few_shots = SQLExecutor.retrieve_few_shot_memories(db, question, connection_id)
        try:
            system_prompt = PromptManager.get_text_to_sql_system_prompt(user_role, allowed_tables)
            prompt_llm = PromptManager.get_text_to_sql_user_prompt(
                question, user_role, schema_context, allowed_tables, few_shots
            )

            llm_response_text = await LLMService.generate_completion(
                prompt_llm,
                system_prompt=system_prompt,
                temperature=0.05,
                max_tokens=200
            )

            if llm_response_text:
                is_llm_active = True
                sql_match = re.search(r'```sql\s*(.*?)\s*```', llm_response_text, re.DOTALL | re.IGNORECASE)
                if sql_match:
                    extracted = sql_match.group(1).strip()
                    if "SELECT" in extracted.upper():
                        candidate_sql = extracted
                elif "SELECT" in llm_response_text.upper():
                    select_match = re.search(r'(SELECT\s+.*?(?:;|$))', llm_response_text, re.DOTALL | re.IGNORECASE)
                    if select_match:
                        candidate_sql = select_match.group(1).strip().rstrip(';')
        except Exception:
            is_llm_active = False

        if not candidate_sql or not is_llm_active:
            exec_time_ms = int((time.time() - start_time) * 1000)
            return ResponseBuilder.build_llm_offline_response(question, exec_time_ms)

        try:
            rows, secured_sql, meta, was_self_healed, validation_label = await SQLExecutor.execute_with_self_healing(
                target_db_path=exec_target,
                question=question,
                initial_sql=candidate_sql,
                allowed_tables=allowed_tables,
                blocked_columns=blocked_columns,
                table_columns_map=table_columns_map,
                schema_context=schema_context,
                is_llm_active=is_llm_active,
                dialect=engine_dialect
            )
        except Exception as e:
            return ResponseBuilder.build_rbac_denied_response(question, str(e))

        SQLExecutor.persist_learning_memory(
            db=db,
            question=question,
            sql=secured_sql,
            connection_id=connection_id,
            user_role=user_role,
            tables_used=meta.get("tables_used", list(allowed_tables)),
            was_healed=was_self_healed
        )

        exec_time_ms = int((time.time() - start_time) * 1000)
        columns = list(rows[0].keys()) if rows else []

        pres_hints = await IntentClassifier.classify_presentation_format(
            question, response_type, rows, columns
        )

        kpis, chart_type, chart_option, fallback_summary, fallback_exec_report, gauges = KPICalculator.build_dynamic_visualization(
            question, columns, rows, user_role
        )

        final_exec_report = fallback_exec_report

        if is_llm_active:
            semantic_res = await KPICalculator.generate_semantic_analysis_with_llm(
                question=question,
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
                    question, user_role, rows, columns, secured_sql, is_llm_active
                )
                if llm_exec_report:
                    final_exec_report = llm_exec_report

        if not pres_hints.show_kpis:
            kpis = []
        if not pres_hints.show_gauges:
            gauges = []
        if not pres_hints.show_chart:
            chart_type = "none"
            chart_option = {"series": []}

        conversational = await IntentClassifier.generate_conversational_response(
            question, user_role, response_type, rows, columns, is_llm_active
        )

        if conversational:
            first_block = conversational.split("\n\n")[0].replace("#", "").strip()
            final_summary = first_block if len(first_block) > 10 else fallback_summary
            if conversational and (pres_hints.preferred_view in ("table", "report") or response_type in ("data_analysis", "conversational", "advisory", "explanation", "hybrid")):
                pres_hints.preferred_view = "assistant"
        elif pres_hints.summary_style == "executive" and final_exec_report and final_exec_report.overview:
            final_summary = final_exec_report.overview
        elif pres_hints.summary_style == "concise":
            final_summary = (
                f"Se obtuvieron {len(rows)} registros de "
                f"{', '.join(meta.get('tables_used', []))} para la consulta '{question}'."
            )
        else:
            final_summary = final_exec_report.overview if final_exec_report and final_exec_report.overview else fallback_summary

        return ResponseBuilder.build_analytics_response(
            question=question,
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
            gauges=gauges,
            chart_type=chart_type,
            chart_option=chart_option,
            final_summary=final_summary,
            final_exec_report=final_exec_report,
            conversational=conversational
        )

    # Legacy static method aliases
    _classify_intent = IntentClassifier.classify_intent
    _classify_presentation_format = IntentClassifier.classify_presentation_format
    _heuristic_presentation_hints = IntentClassifier.heuristic_presentation_hints
    _generate_conversational_response = IntentClassifier.generate_conversational_response
    _generate_deep_executive_report_with_llm = KPICalculator.generate_deep_executive_report_with_llm
    _build_dynamic_visualization = KPICalculator.build_dynamic_visualization
    
    @classmethod
    def _get_grounding_query_for_question(
        cls,
        question: str,
        user_role: str = "Economista",
        allowed_tables: Optional[Set[str]] = None
    ) -> str:
        return SQLExecutor.get_grounding_query(question, user_role, allowed_tables)

    _retrieve_few_shot_memories = SQLExecutor.retrieve_few_shot_memories
    _persist_learning_memory = SQLExecutor.persist_learning_memory
