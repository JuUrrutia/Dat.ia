import time
import re
import logging
from typing import Any, Callable, List, Dict, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_DEMO_ROLE, ROLE_USUARIO, ADMIN_ROLES
from app.core.database import discard_failed_transaction
from app.core.prompts import PromptManager
from app.core.security import mask_rows
from app.modules.admin_catalog.models import DatabaseType
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
    get_masked_columns_for_role = GovernanceGuard.get_masked_columns_for_role
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
    _build_visibility_diagnostic_response = ResponseBuilder.build_visibility_diagnostic_response
    _classify_intent = IntentClassifier.classify_intent
    _heuristic_presentation_hints = IntentClassifier.heuristic_presentation_hints
    _generate_conversational_response = IntentClassifier.generate_conversational_response
    _generate_unified_synthesis_with_llm = KPICalculator.generate_unified_synthesis_with_llm
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
    def _diagnose_empty_visibility(
        cls, db: Optional[Session], connection_id: Optional[int], is_admin: bool
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Por que `allowed_tables` vuelve vacio. Sin esto los tres casos son el
        mismo "sin resultados": no hay datos, tu rol no ve tablas, o NADIE ha
        encendido la base. El tercero es real en este despliegue (11 conexiones,
        las 11 con `is_active=False`) y es el unico que el usuario no puede
        arreglar solo.

        `state`:
          - `"no_active_connection"`: hay conectores y ninguno activo.
          - `"role_without_tables"`: hay al menos uno activo (el caso que ya
            reportaba `build_rbac_denied_response`).
          - `"unknown"`: no se pudo comprobar. Se devuelve `unknown` y NO
            "no hay conexiones": afirmar sin medir es el bug que esto cierra
            (mismo criterio que `test_audit_log_honesty.py`).

        La accion de activar solo se propone al admin y solo cuando se pudo
        comprobar: es una escritura que `get_current_admin` rechazaria para
        cualquier otro perfil.
        """
        state = "unknown"
        activate: Optional[Dict[str, Any]] = None
        if db is None:
            return state, activate
        try:
            from app.modules.admin_catalog.models import CorporateConnection
            # Una sola lectura y la cuenta en Python: dos `filter` sobre el
            # mismo modelo se contradicen en cuanto algo cambia entre ambos, y
            # aqui solo hace falta "hay alguna activa?".
            conns = db.query(CorporateConnection).all()
            inactive = [c for c in conns if not c.is_active]
            if any(c.is_active for c in conns):
                return "role_without_tables", None
            if not conns:
                # Cero conectores NO es "nadie activó uno": es que no hay ninguna
                # base dada de alta. La accion util es crear una, no activar, y el
                # mensaje de `no_active_connection` mandaria al admin a buscar un
                # interruptor que no existe. Se declara aparte.
                return "no_connections_registered", None
            state = "no_active_connection"
            # La del propio pedido manda: es la que el usuario esta mirando en
            # el selector. Con una sola inactiva no hay duda posible.
            target = next((c for c in inactive if c.id == connection_id), None)
            if target is None and len(inactive) == 1:
                target = inactive[0]
            if is_admin and target is not None:
                activate = {
                    "connection_id": target.id,
                    "connection_name": target.name,
                    "endpoint": f"/api/v1/connectors/{target.id}/toggle-active"
                }
        except Exception as ex:
            logger.warning(f"No se pudo verificar el estado de las conexiones de datos: {ex}")
            # La sesion es del CALLER: tragarnos el error sin deshacer la
            # transaccion abortada la deja muerta para el resto de la request.
            discard_failed_transaction(db)
        return state, activate

    @classmethod
    async def execute_query(
        cls,
        question: str,
        user_role: str = DEFAULT_DEMO_ROLE,
        is_admin: bool = False,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        narrative_sink: Optional[Callable[[str], Any]] = None
    ) -> QueryResponse:
        """
        `narrative_sink` es opcional y solo lo usa `POST /chat/query/stream`.

        Opcional a proposito: cuando es `None` (o sea, en TODOS los caminos que
        ya existian, incluido `POST /chat/query`) el motor se comporta exactamente
        igual que antes. El sink se invoca DESPUES del enmascarado de
        `mask_rows` y en el mismo punto donde hoy se construye la narrativa, asi
        que lo que se emite al navegador sale del mismo `rows` enmascarado que
        alimenta la respuesta completa: stremear no abre una via de datos sin
        enmascarar.
        """

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

        # 3.0 Por que no hay tablas, ANTES de gastar un grounding_query o una
        # llamada al LLM. Sin tablas no hay nada que consultar, y el mensaje
        # tiene que decir cual de los dos motivos es; el resto del pipeline solo
        # sabe producir "sin resultados", que es lo que hace que el producto
        # parezca roto cuando en realidad nadie encendio la base.
        if not allowed_tables:
            diag_state, activate_action = cls._diagnose_empty_visibility(db, connection_id, is_admin)
            if diag_state in ("no_active_connection", "no_connections_registered") or (diag_state == "unknown" and not is_admin):
                # El `unknown` del admin NO corta el flujo: antes un admin sin
                # tablas caia al resto del motor y ese comportamiento se
                # conserva. No hay ningun dato nuevo que contarle.
                return cls._build_visibility_diagnostic_response(
                    effective_question, user_role, diag_state, activate_action
                )

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
        masked_columns = cls.get_masked_columns_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)
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
                # `conn_record` queda None y la request sigue por el resto del
                # camino, pero la sesion no: la consulta fallida la dejo
                # abortada, asi que todo lo que se ejecute despues en esta misma
                # request moriria con `InFailedSqlTransaction` sin relacion con
                # nada. Es exactamente el defecto de los demas handlers
                # best-effort, y por eso usa el mismo helper.
                discard_failed_transaction(db)

        # El retorno de `apply_null_policy` NO se descarta: devuelve `status:
        # no_op` / `rows_affected: 0` cuando no remedio nada. Mirar solo el exito
        # hacia que el chat anunciara "remediacion aplicada" sobre una base sin
        # remediar. La politica aplicada no cambia aqui; solo se comunica el
        # resultado (el banner de la seccion 8 usa este texto en vez del exito).
        remediation_notice: Optional[str] = None
        if remediation_action and conn_record and db:
            try:
                result = NullManagerService.apply_null_policy(conn_record, remediation_action, db) or {}
                conn_record.null_policy = 'open'
                db.commit()
                if result.get("status") != "success" or not (result.get("rows_affected") or 0):
                    remediation_notice = (
                        "⚠️ **No se remedió ningún valor nulo**\n\n"
                        f"{result.get('message') or 'La remediación no modificó ninguna celda.'}\n\n"
                    )
            except Exception as ex:
                logger.warning(f"Error applying null remediation to DB: {ex}")
                # Medido contra PostgreSQL, y NO es el mismo estado que una query
                # fallida: un `db.commit()` que revienta en el flush deja la sesion
                # en `PendingRollbackError` ("rolled back due to a previous
                # exception during flush"), mientras que una sentencia fallida la
                # deja en `InFailedSqlTransaction`. Los dos envenenan la sesion y
                # los dos se limpian con el mismo rollback; lo que cambia es que
                # aqui el fallo puede venir del propio commit, asi que el rollback
                # va DESPUES de la excepcion, nunca antes.
                discard_failed_transaction(db)
                # `apply_null_policy` revierte la política si falla: tampoco se
                # logro remediar nada, y decirlo es lo unico honesto.
                remediation_notice = (
                    "⚠️ **No se remedió ningún valor nulo**\n\n"
                    f"La remediación falló y se revirtió: {ex}. La base queda sin cambios.\n\n"
                )

        is_pg = conn_record is not None and (
            getattr(conn_record, "db_type", None) == DatabaseType.POSTGRESQL
            or "postgres" in str(getattr(conn_record, "db_type", "")).lower()
        )
        engine_dialect = "postgres" if is_pg else "sqlite"
        try:
            target_db_path = DynamicSchemaPruningService.resolve_db_path(db, connection_id)
        except Exception as ex:
            # Fallar cerrado: sin ruta resuelta no se sabe a que base del cliente
            # apuntan los permisos ya calculados, y seguir con `exec_target` caeria
            # en la BD demo interna de Datia.
            return ResponseBuilder.build_execution_error_response(
                effective_question, str(ex), int((time.time() - start_time) * 1000)
            )
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
                    table_columns=table_columns_map,
                    is_admin=is_admin
                )
                rows = SQLExecutor.execute_raw_sql(exec_target, secured_sql, dialect=engine_dialect)
            except ASTValidationError:
                secured_sql = "-- CONSULTA NO AUTORIZADA POR GOBERNANZA RBAC"
                meta = {"tables_used": []}
                rows = []
            except Exception:
                secured_sql = "-- CONSULTA NO EJECUTADA POR ERROR TÉCNICO"
                meta = {"tables_used": []}
                rows = []

            # Enmascarado de columnas MASKED, identico al de la rama analitica mas
            # abajo. Esta rama estaba fuera del:`mask_rows` solo se aplicaba en
            # BRANCH B, y el grounding query es `SELECT * ... LIMIT 20`, o sea que
            # se llevaba al LLM (y de ahi al snapshot de auditoria y a los exports
            # PDF/Excel) el RUT/token/API key en claro aunque el usuario no tuviera
            # permiso de lectura. `forecast_service.py` ya lo hacia y lo documentaba
            # como "una prediccion no es una exencion del RBAC": el hueco era
            # accidental.
            # ponytail: el sitio definitivo seria `SQLExecutor.execute_raw_sql`, que
            # es el punto unico por el que pasa TODA ejecucion (incluido
            # `execute_with_self_healing`). Ahi no se puede sin cambiar su contrato:
            # el executor es agnostico al RBAC y no recibe `masked_columns`.
            if masked_columns and rows:
                mask_rows(rows, masked_columns)

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
                        table_columns=table_columns_map,
                        is_admin=is_admin
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
                conversation_history=conversation_history,
                dialect=engine_dialect,
            )
            if rbac_denial and not is_admin:
                return ResponseBuilder.build_rbac_denied_response(effective_question, rbac_denial)

        if not candidate_sql or not is_llm_active:
            exec_time_ms = int((time.time() - start_time) * 1000)
            return ResponseBuilder.build_llm_offline_response(effective_question, exec_time_ms)

        # 5.5 Pre-flight Physical Schema Verification (Fail-Fast < 1ms)
        physical_tables = DynamicSchemaPruningService.get_physical_db_tables(exec_target)
        if physical_tables:
            candidate_tables = ASTValidator.extract_tables_from_query(candidate_sql, dialect=engine_dialect)
            missing_physical_tables = [t for t in candidate_tables if t.lower() not in physical_tables]
            if missing_physical_tables:
                exec_time_ms = int((time.time() - start_time) * 1000)
                conn_name = getattr(conn_record, "name", "Base de datos activa") if conn_record else "Base de datos activa"
                missing_str = ", ".join(f"`{t}`" for t in missing_physical_tables)
                avail_str = ", ".join(f"`{t}`" for t in sorted(physical_tables))
                err_msg = (
                    f"La consulta requiere la tabla {missing_str}, que no existe en '{conn_name}'. "
                    f"Tablas disponibles en esta conexión: [{avail_str}]. "
                    f"Faltan datos para realizar esta consulta en la fuente seleccionada."
                )
                return ResponseBuilder.build_execution_error_response(effective_question, err_msg, exec_time_ms)

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
                dialect=engine_dialect,
                is_admin=is_admin
            )
        except ASTValidationError as e:
            return ResponseBuilder.build_rbac_denied_response(effective_question, str(e))
        except Exception as e:
            exec_time_ms = int((time.time() - start_time) * 1000)
            return ResponseBuilder.build_execution_error_response(effective_question, str(e), exec_time_ms)

        # Enmascarado de columnas MASKED: se aplica a las filas recien ejecutadas y
        # ANTES de que entren a cualquier respuesta. A partir de aca `rows` es lo
        # unico que circula, asi que el RUT en claro no llega ni al snapshot de
        # auditoria, ni a los reportes exportados a PDF/Excel, ni a la vista.
        if masked_columns and rows:
            mask_rows(rows, masked_columns)

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

        # 8. Visual Presentation & Single-Pass Unified Synthesis
        pres_hints = IntentClassifier.heuristic_presentation_hints(
            effective_question, response_type, rows, columns
        )

        kpis, chart_type, chart_option, fallback_summary, fallback_exec_report = KPICalculator.build_dynamic_visualization(
            effective_question, columns, rows, user_role
        )
        final_exec_report = fallback_exec_report
        conversational: Optional[str] = None
        extracted_suggs: Optional[List[str]] = None

        if is_llm_active:
            conv_context = PromptManager.format_conversation_context_for_synthesis(conversation_history) if conversation_history else ""
            unified_res = await KPICalculator.generate_unified_synthesis_with_llm(
                question=effective_question,
                user_role=user_role,
                rows=rows,
                columns=columns,
                secured_sql=secured_sql,
                conversation_context=conv_context,
                is_llm_active=is_llm_active,
                narrative_sink=narrative_sink
            )
            if unified_res:
                if unified_res.get("narrative"):
                    conversational = unified_res["narrative"]
                if unified_res.get("kpis"):
                    kpis = unified_res["kpis"]
                if unified_res.get("executive_report"):
                    final_exec_report = unified_res["executive_report"]
                if unified_res.get("suggested_questions"):
                    extracted_suggs = unified_res["suggested_questions"]

            # Fallback to standalone conversational call if unified synthesis yielded no narrative
            if not conversational:
                conversational = await IntentClassifier.generate_conversational_response(
                    effective_question, user_role, response_type, rows, columns, is_llm_active
                )

        if is_remediation:
            banner = remediation_notice or NullHandler.format_remediation_banner(remediation_action, effective_question)
            conversational = (banner + conversational) if conversational else banner
            if fallback_summary:
                fallback_summary = banner + fallback_summary

        if extracted_suggs:
            suggested_questions = extracted_suggs
            if conversational:
                conversational = re.sub(r'<preguntas_sugeridas>[\s\S]*?</preguntas_sugeridas>', '', conversational).strip()
        else:
            suggested_questions, conversational = cls._extract_suggested_questions(
                conversational, rows, columns, meta.get("tables_used", list(allowed_tables))
            )

        if not pres_hints.show_executive_report:
            final_exec_report = None
        if not pres_hints.show_kpis:
            kpis = []
        if not pres_hints.show_chart:
            chart_type = "none"
            chart_option = {"series": []}

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
