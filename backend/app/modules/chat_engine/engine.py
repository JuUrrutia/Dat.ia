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
from app.modules.chat_engine.schemas import QueryResponse, PresentationHints
from app.modules.chat_engine.intent_classifier import IntentClassifier
from app.modules.chat_engine.sql_executor import SQLExecutor
from app.modules.chat_engine.kpi_calculator import KPICalculator, is_true_numeric_metric
from app.modules.chat_engine.response_builder import ResponseBuilder
from app.modules.catalog.services.null_manager import NullManagerService

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
        connection_id: Optional[int] = None
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

        return cls.get_dynamic_suggestions(user_role, allowed_tables, schema_prompt=schema_prompt)

    @classmethod
    def get_dynamic_suggestions(
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

        suggestions = []
        sorted_tables = sorted(list(allowed_tables), key=lambda t: (0 if t.lower().startswith("fact_") else 1, t.lower()))

        # Attempt to extract physical metrics & dimensions from schema_prompt
        extracted_metrics = []
        extracted_categories = []
        extracted_dates = []

        if schema_prompt:
            col_matches = re.findall(r'^\s*-\s*([a-zA-Z0-9_]+)\s*\(([^)]+)\)', schema_prompt, re.MULTILINE)
            for c_name, c_type in col_matches:
                c_low = c_name.lower()
                t_low = c_type.lower()
                if c_low in {"id", "id_tabla"} or c_low.endswith("_id") or c_low.endswith("_key"):
                    continue
                if any(m in c_low for m in ["monto", "total", "precio", "ingreso", "costo", "venta", "salario", "sueldo", "cantidad", "consumo", "cpu", "ram", "incidente", "unidades", "horas", "duracion"]) or any(it in t_low for it in ["int", "real", "float", "numeric", "decimal", "double"]):
                    extracted_metrics.append(c_name)
                elif any(d in c_low for d in ["fecha", "mes", "anio", "date", "periodo", "created_at", "timestamp"]):
                    extracted_dates.append(c_name)
                elif any(cat in c_low for cat in ["categoria", "producto", "cliente", "departamento", "region", "sucursal", "canal", "tipo", "estado", "ciudad", "pais", "marca", "servidor", "usuario", "proveedor"]):
                    extracted_categories.append(c_name)

        clean_table_names = []
        for tbl in sorted_tables:
            clean_name = tbl
            for prefix in ["fact_", "dim_", "tbl_", "table_"]:
                if clean_name.lower().startswith(prefix):
                    clean_name = clean_name[len(prefix):]
                    break
            clean_table_names.append((tbl, clean_name.replace("_", " ").strip()))

        # If we have extracted metrics and categories from the active database schema
        if extracted_metrics and (extracted_categories or clean_table_names):
            best_metric = extracted_metrics[0].replace("_", " ").strip()
            best_cat = (extracted_categories[0].replace("_", " ").strip()) if extracted_categories else clean_table_names[0][1]
            primary_tbl = clean_table_names[0][1]

            suggestions.append(f"📊 ¿Cuál es el total de {best_metric} agrupado por {best_cat}?")
            suggestions.append(f"📈 Top 5 {best_cat} con mayor {best_metric}")
            if extracted_dates:
                best_date = extracted_dates[0].replace("_", " ").strip()
                suggestions.append(f"📅 Evolución temporal de {best_metric} por {best_date}")
            elif len(extracted_metrics) > 1:
                sec_metric = extracted_metrics[1].replace("_", " ").strip()
                suggestions.append(f"⚡ Comparativa de {best_metric} y {sec_metric} en {primary_tbl}")
            else:
                suggestions.append(f"🔍 Promedio y registros destacados de {best_metric} en {primary_tbl}")

            if len(clean_table_names) > 1:
                sec_tbl = clean_table_names[1][1]
                suggestions.append(f"💡 Resumen consolidado y principales indicadores de {sec_tbl}")
            else:
                suggestions.append(f"📋 Desglose detallado y análisis de {primary_tbl}")

        # Fallback table-based templates
        if len(suggestions) < 4:
            templates = [
                "📊 Distribución y resumen de registros en {name}",
                "📈 Métricas acumuladas y evolución en {name}",
                "📋 Listado detallado y consulta de {name}",
                "💡 Indicadores clave y registros principales de {name}"
            ]

            for i, (orig_tbl, clean_spaced) in enumerate(clean_table_names):
                tmpl = templates[i % len(templates)]
                suggestions.append(tmpl.format(name=clean_spaced))

                if len(clean_table_names) == 1:
                    suggestions.append(f"🔍 Top registros con mayores valores en {clean_spaced}")
                    suggestions.append(f"⚡ Totales agregados y promedio general de {clean_spaced}")

        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique[:4]

    @classmethod
    def check_domain_governance(cls, question: str, user_role: str, allowed_tables: Set[str]) -> Optional[str]:
        """
        Enforces cross-domain governance guardrails (Fail-Closed).
        Detects if a user role attempts to query topics strictly outside their business domain.
        Returns a denial reason string if violated, or None if permitted.
        """
        role_lower = (user_role or "").lower().strip()
        q_lower = (question or "").lower().strip()
        allowed_lower = {t.lower() for t in (allowed_tables or set())}

        # 0. Global Admin and C-Level have cross-domain visibility
        if any(k in role_lower for k in ["admin", "director ejecutivo", "c-level", "super", "plataforma"]):
            return None

        # Domain 1: Tech / TI / Infrastructure roles attempting to access financial, commercial or sales data
        is_tech_role = any(k in role_lower for k in ["ti", "infraestructura", "tecnolog", "sistemas", "devops", "soporte"])
        if is_tech_role and not any(k in role_lower for k in ["financ", "comercial", "econom"]):
            financial_keywords = [
                r'\b(saldo|saldos|balance|balances)\b',
                r'\b(venta|ventas|preventa|postventa)\b',
                r'\b(ingreso|ingresos|recaudaci[oó]n|cobro|cobros)\b',
                r'\b(ganancia|ganancias|lucro|utilidad|utilidades)\b',
                r'\b(precio|precios|tarifa|tarifas|cotizaci[oó]n|cotizaciones)\b',
                r'\b(facturaci[oó]n|factura|facturas|facturado)\b',
                r'\b(margen|m[aá]rgenes|ebitda|rentabilidad)\b',
                r'\b(costo|costos|gasto|gastos|egreso|egresos|presupuesto|presupuestos)\b',
                r'\b(dinero|monto|montos|financier[oa]s?|finanzas)\b',
                r'\b(econ[oó]mic[oa]s?|econom[íi]a|comercial(es)?)\b',
                r'\b(cartera\s+de\s+clientes|comprador|compradores)\b',
                r'\b(m[oó]dulo|[aá]rea|departamento)\s+(de\s+)?(finanzas|financier[oa]|comercial|ventas|facturaci[oó]n|econom[íi]a)\b',
                r'\b(fact_ventas|fact_ingresos_costos|vbak_cabpedidoventa|vbap_pospedidoventa|kna1_clientes)\b'
            ]
            if re.search('|'.join(financial_keywords), q_lower):
                return (
                    f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización "
                    "para consultar información financiera, facturación, ventas, ingresos ni balances comerciales de la organización."
                )

        # Domain 2: Business / Financial / Commercial roles attempting to access technical IT infrastructure
        is_fin_role = any(k in role_lower for k in ["economista", "financiero", "finanzas", "comercial", "negocio", "contab"])
        if is_fin_role and not any(k in role_lower for k in ["ti", "infraestructura", "tecnolog"]):
            # Check if it is a legitimate product or catalog inquiry about technology goods
            commercial_context = r'\b(vendid[oa]s?|vendieron|vendimos|vender|venta|ventas|comprad[oa]s?|compraron|compramos|compras?|precio|precios|facturaci[oó]n|facturas?|cliente|clientes)\b'
            product_context = r'\b(producto|productos|categor[íi]a|categor[íi]as|art[íi]culo|art[íi]culos|cat[aá]logo)\b'
            is_product_query = bool(re.search(product_context, q_lower) and re.search(commercial_context, q_lower))

            if not is_product_query:
                tech_keywords = [
                    r'\b(tecnol[oó]gic[oa]s?|tecnolog[ií]a)\b',
                    r'\b(ti|it|t\.i\.)\b',
                    r'\b(inform[aá]tic[oa]s?|telecomunicaci[oó]n|telecomunicaciones)\b',
                    r'\b(servidor|servidores|server|servers|host|hosts|cluster|clusters|nodo|nodos)\b',
                    r'\b(cpu|memoria\s+ram|\bram\b|disco|discos|almacenamiento)\b',
                    r'\b(incidente|incidentes|incidentes\s+ti|incidentes_ti)\b',
                    r'\b(ticket|tickets|soporte\s+t[ée]cnico|helpdesk|mesa\s+de\s+ayuda)\b',
                    r'\b(uptime|downtime|ca[íi]da|ca[íi]das|disponibilidad\s+del?\s+sistema)\b',
                    r'\b(consumo\s+de\s+recursos|latencia|ancho\s+de\s+banda|ping|router|switch|firewall)\b',
                    r'\b(infraestructura(\s+de\s+ti|\s+tecnol[oó]gica|\s+t[ée]cnica)?)\b',
                    r'\b(m[oó]dulo|[aá]rea|departamento)\s+(de\s+)?(ti|it|tecnolog[íi]a|infraestructura|sistemas)\b',
                    r'\b(m[oó]dulo\s+(ti|it|tecnol[oó]gic[oa]))\b',
                    r'\b(sistemas\s+inform[aá]ticos|telemetr[íi]a)\b',
                    r'\b(parche|parches|vulnerabilidad|vulnerabilidades|ciberseguridad|seguridad\s+ti)\b',
                    r'\b(backup|backups|respaldo|respaldos)\b',
                    r'\b(dim_servidores|fact_incidentes_ti|fact_consumo_recursos)\b'
                ]
                if re.search('|'.join(tech_keywords), q_lower):
                    return (
                        f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización "
                        "para consultar servidores, incidentes técnicos ni métricas de infraestructura TI."
                    )

        # Domain 3: HR / Payroll Isolation (only HR / Gerente de Talento, C-Level, Admin can access salaries/payroll)
        is_hr_role = any(k in role_lower for k in ["talento", "rrhh", "recursos humanos", "personas"])
        if not is_hr_role:
            hr_keywords = [
                r'\b(sueldo|sueldos|salario|salarios|remuneraci[oó]n|remuneraciones)\b',
                r'\b(n[oó]mina|n[oó]minas|honorario|honorarios)\b',
                r'\b(cu[aá]nto\s+gana[n]?|compensaci[oó]n|compensaciones)\b',
                r'\b(m[oó]dulo|[aá]rea|departamento)\s+(de\s+)?(rrhh|recursos humanos|talento|personal)\b',
            ]
            if re.search('|'.join(hr_keywords), q_lower):
                return (
                    f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización "
                    "para consultar salarios, remuneraciones, nóminas ni información confidencial de Recursos Humanos."
                )

        return None

    # Delegates to ResponseBuilder and NullManagerService
    _build_llm_offline_response = ResponseBuilder.build_llm_offline_response
    _build_rbac_denied_response = ResponseBuilder.build_rbac_denied_response
    _apply_in_memory_null_remediation = NullManagerService.apply_in_memory_remediation

    @classmethod
    def _detect_remediation_intent(cls, text: str) -> Optional[str]:
        if not text:
            return None
        t_low = text.lower()
        if any(k in t_low for k in ["eliminar filas", "eliminar registros", "eliminar nulos", "quitar nulos", "delete_rows"]):
            return "delete_rows"
        if any(k in t_low for k in ["adaptar a la moda", "moda estadística", "imputar moda", "tratar nulos: moda", "a la moda"]) or ("moda" in t_low and ("nulo" in t_low or "tratar" in t_low)):
            return "mode"
        if any(k in t_low for k in ["adaptar al más cercano", "más cercano", "mas cercano", "nearest", "imputar cercano"]) or (("cercano" in t_low or "nearest" in t_low) and ("nulo" in t_low or "tratar" in t_low)):
            return "nearest"
        return None

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

        # 0. Check if question is a null remediation directive for a previous query
        remediation_action = cls._detect_remediation_intent(question)
        original_question = None
        original_sql = None

        if remediation_action:
            m_para = re.search(r'(?:para|sobre)\s+la\s+consulta:\s*[\'"]?([^\r\n]+?)[\'"]?$', question, re.IGNORECASE)
            if m_para:
                original_question = m_para.group(1).strip()

            if conversation_history:
                for turn in reversed(conversation_history):
                    t_q = turn.get("question", "").strip()
                    if t_q and not cls._detect_remediation_intent(t_q):
                        if not original_question:
                            original_question = t_q
                        if turn.get("sql") and not original_sql:
                            original_sql = turn.get("sql")
                        break

        effective_question = original_question or question

        # 1. RBAC check for unassigned "Usuario" role
        if not is_admin and (user_role == ROLE_USUARIO or not user_role):
            return ResponseBuilder.build_rbac_denied_response(
                effective_question,
                "Tu cuenta se encuentra registrada con el perfil inicial 'Usuario'. Un Administrador debe asignarte un rol (Economista o TI) para acceder a los datos corporativos."
            )

        allowed_tables = cls.get_allowed_tables_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)

        # 2. Strict Cross-Domain RBAC Governance Check (Defense Layer 1 - Fail Closed)
        if not is_admin and user_role not in ADMIN_ROLES:
            domain_denial = cls.check_domain_governance(effective_question, user_role, allowed_tables)
            if domain_denial:
                return ResponseBuilder.build_rbac_denied_response(effective_question, domain_denial)

        if not allowed_tables and not is_admin:
            return ResponseBuilder.build_rbac_denied_response(
                effective_question,
                f"El rol '{user_role}' no tiene tablas asignadas en la matriz RBAC."
            )

        # 3. INTENT CLASSIFICATION
        response_type = await IntentClassifier.classify_intent(effective_question)

        # BRANCH 0: GREETING / GENERAL CONVERSATION
        if response_type == "greeting" and not remediation_action:
            clarification_opts = IntentClassifier.detect_ambiguity_and_options(effective_question, allowed_tables)
            conversational = await IntentClassifier.generate_conversational_response(
                effective_question, user_role, "greeting", columns=list(allowed_tables), is_llm_active=True
            )
            return ResponseBuilder.build_greeting_response(
                effective_question, user_role, allowed_tables, conversational, clarification_options=clarification_opts
            )

        blocked_columns = cls.get_blocked_columns_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)
        start_time = time.time()
        is_llm_active = False

        # Resolve active connection and dialect
        conn_record = None
        if db is not None:
            try:
                from app.modules.admin_catalog.models import CorporateConnection, DatabaseType
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

        is_pg = conn_record is not None and (conn_record.db_type == DatabaseType.POSTGRESQL or str(conn_record.db_type).lower() == "postgresql")
        engine_dialect = "postgres" if is_pg else "sqlite"
        target_db_path = DynamicSchemaPruningService.resolve_db_path(db, connection_id)
        exec_target = conn_record if is_pg else target_db_path

        table_columns_map: Dict[str, List[str]] = {}
        for tbl in allowed_tables:
            phys_cols_info = DynamicSchemaPruningService.get_physical_table_columns(
                tbl, db_path=exec_target, include_samples=False
            )
            table_columns_map[tbl.lower()] = [c["name"] for c in phys_cols_info if "name" in c]

        # BRANCH A: CONVERSATIONAL ASSISTANT
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

            suggested_questions: List[str] = []
            if conversational:
                sugg_match = re.search(r'<preguntas_sugeridas>\s*(.*?)\s*</preguntas_sugeridas>', conversational, re.DOTALL | re.IGNORECASE)
                if sugg_match:
                    raw_suggs = sugg_match.group(1).strip().split("\n")
                    suggested_questions = [re.sub(r'^[-*0-9.)\s]+', '', s).strip() for s in raw_suggs if s.strip()]
                    conversational = re.sub(r'<preguntas_sugeridas>[\s\S]*?</preguntas_sugeridas>', '', conversational).strip()

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

        # BRANCH B: DATA ANALYSIS / REPORT / HYBRID
        candidate_sql = None
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

        schema_context = ""
        thinking_process: Optional[str] = None
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

            few_shots = SQLExecutor.retrieve_few_shot_memories(db, effective_question, connection_id)
            conv_context = PromptManager.format_conversation_context(conversation_history) if conversation_history else ""
            try:
                system_prompt = PromptManager.get_text_to_sql_system_prompt(user_role, allowed_tables)
                prompt_llm = PromptManager.get_text_to_sql_user_prompt(
                    effective_question, user_role, schema_context, allowed_tables, few_shots, conversation_context=conv_context
                )

                llm_response_text = await LLMService.generate_completion(
                    prompt_llm,
                    system_prompt=system_prompt,
                    temperature=0.05,
                    max_tokens=600
                )

                if llm_response_text:
                    is_llm_active = True
                    denied_match = re.search(r'<acceso_denegado>\s*(.*?)\s*</acceso_denegado>', llm_response_text, re.DOTALL | re.IGNORECASE)
                    if denied_match:
                        denied_reason = denied_match.group(1).strip()
                        return ResponseBuilder.build_rbac_denied_response(effective_question, denied_reason)

                    lower_llm = llm_response_text.lower()
                    if any(phrase in lower_llm for phrase in [
                        "acceso denegado", "no tiene autorización", "no está autorizado",
                        "no tiene permisos", "fuera de sus tablas permitidas",
                        "no tiene autorizacion", "no esta autorizado"
                    ]) and "```sql" not in llm_response_text:
                        return ResponseBuilder.build_rbac_denied_response(
                            effective_question,
                            f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización para acceder a estos datos."
                        )

                    thinking_match = re.search(r'<pensamiento>\s*(.*?)\s*</pensamiento>', llm_response_text, re.DOTALL | re.IGNORECASE)
                    if thinking_match:
                        thinking_process = thinking_match.group(1).strip()

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
            return ResponseBuilder.build_llm_offline_response(effective_question, exec_time_ms)

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

        # --- NULL DETECTION & REMEDIATION (Policy: 'open') ---
        null_cols_in_rows = set()
        null_rows_count = 0
        for r in rows:
            row_has_null = False
            for c_name, val in r.items():
                if val is None or str(val).strip().lower() in ("none", "null"):
                    null_cols_in_rows.add(c_name)
                    row_has_null = True
            if row_has_null:
                null_rows_count += 1

        if remediation_action and null_cols_in_rows:
            rows = NullManagerService.apply_in_memory_remediation(rows, columns, remediation_action)
            null_cols_in_rows = set()
            null_rows_count = 0

        nulls_detected = None
        conn_policy = getattr(conn_record, 'null_policy', 'open') or 'open'
        is_remediation = bool(remediation_action)

        # Early pause on Prompt 1 when nulls are found under policy 'open':
        # Do NOT compute distorted KPIs or false conclusions analyzing "null" as a data category!
        if null_rows_count > 0 and conn_policy == 'open' and not is_remediation:
            primary_table = meta.get("tables_used", ["la tabla"])[0] if meta.get("tables_used") else "la tabla activa"
            cols_sorted = sorted(list(null_cols_in_rows))
            cols_text = ", ".join(f"`{c}`" for c in cols_sorted)
            nulls_detected = {
                "has_nulls": True,
                "table_name": primary_table,
                "columns_with_nulls": cols_sorted,
                "null_rows_count": null_rows_count,
                "total_rows": len(rows),
                "options": [
                    {
                        "action": "delete_rows",
                        "label": "Eliminar registros con nulos",
                        "prompt": f"Tratar nulos en {primary_table} (eliminar registros con nulos) para la consulta: {effective_question}"
                    },
                    {
                        "action": "mode",
                        "label": "Adaptar a la moda",
                        "prompt": f"Tratar nulos en {primary_table} (adaptar a la moda) para la consulta: {effective_question}"
                    },
                    {
                        "action": "nearest",
                        "label": "Adaptar al más cercano",
                        "prompt": f"Tratar nulos en {primary_table} (adaptar al más cercano) para la consulta: {effective_question}"
                    }
                ]
            }

            conversational = (
                f"⚠️ **Valores nulos detectados en la consulta**\n\n"
                f"Se detectaron valores nulos en la tabla `{primary_table}` (columnas: {cols_text}), "
                f"afectando a {null_rows_count} de {len(rows)} registros analizados.\n\n"
                f"Para entregarte un análisis confiable y evitar distorsiones en los resultados o gráficos "
                f"(como considerar los valores nulos como una categoría de datos), "
                f"por favor selecciona cómo deseas procesar estos registros antes de calcular la respuesta definitiva:"
            )
            fallback_summary = conversational
            kpis = []
            chart_type = "none"
            chart_option = {"series": []}
            final_exec_report = None
            suggested_questions = []
            anomalies_detected = []
            clarification_opts = []
            sql_explanation = ASTValidator.generate_sql_explanation(secured_sql, dialect=engine_dialect)
            pres_hints = PresentationHints(
                show_executive_report=False,
                show_kpis=False,
                show_chart=False,
                preferred_view="assistant",
                summary_style="detailed"
            )

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
                final_summary=fallback_summary,
                final_exec_report=final_exec_report,
                conversational=conversational,
                thinking_process=thinking_process,
                suggested_questions=suggested_questions,
                clarification_options=clarification_opts,
                anomalies_detected=anomalies_detected,
                sql_explanation=sql_explanation,
                nulls_detected=nulls_detected
            )

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
            action_labels = {
                "delete_rows": "Eliminación de registros con nulos",
                "mode": "Adaptación a la moda estadística",
                "nearest": "Adaptación al valor más cercano"
            }
            lbl = action_labels.get(remediation_action, remediation_action)
            banner = f"✅ **Tratamiento de nulos ({lbl}) aplicado para responder a:** *\"{effective_question}\"*\n\n"
            if conversational:
                conversational = banner + conversational
            if fallback_summary:
                fallback_summary = banner + fallback_summary

        suggested_questions: List[str] = []
        if conversational:
            # 1. Extract from XML tags <preguntas_sugeridas>
            sugg_match = re.search(r'<preguntas_sugeridas>\s*(.*?)\s*</preguntas_sugeridas>', conversational, re.DOTALL | re.IGNORECASE)
            if sugg_match:
                raw_suggs = sugg_match.group(1).strip().split("\n")
                suggested_questions = [re.sub(r'^[-*0-9.)\s]+', '', s).strip() for s in raw_suggs if s.strip()]
                conversational = re.sub(r'<preguntas_sugeridas>[\s\S]*?</preguntas_sugeridas>', '', conversational).strip()

            # 2. Also strip any un-tagged question headers like 'Preguntas de Profundización:' from text body
            text_sugg_match = re.search(r'(?:###?\s*)?(?:Preguntas\s+de\s+Profundización|Próximas\s+Preguntas|Preguntas\s+Sugeridas)[\s:]*([\s\S]*)$', conversational, re.IGNORECASE)
            if text_sugg_match:
                lines = [re.sub(r'^[-*0-9.)\s]+', '', l).strip() for l in text_sugg_match.group(1).strip().split("\n") if l.strip()]
                if not suggested_questions and lines:
                    suggested_questions = [l for l in lines if l.startswith("¿") or len(l) > 10][:3]
                conversational = conversational[:text_sugg_match.start()].strip()

        if not suggested_questions and rows and columns:
            first_col = columns[0]
            num_cols = [c for c in columns if is_true_numeric_metric(c, rows[0].get(c))]
            if num_cols:
                suggested_questions = [
                    f"¿Cuál es la evolución temporal de {num_cols[0]}?",
                    f"¿Cómo se distribuye {num_cols[0]} según {first_col}?",
                    f"¿Cuáles son los valores más destacados de {num_cols[0]}?"
                ]
            else:
                suggested_questions = [
                    f"¿Cuántos registros totales existen en {meta.get('tables_used', ['esta tabla'])[0]}?",
                    f"¿Cuáles son los registros más recientes?",
                    f"¿Cómo se desglosan por {first_col}?"
                ]

        clarification_opts = IntentClassifier.detect_ambiguity_and_options(effective_question, allowed_tables)
        anomalies_detected = KPICalculator.detect_statistical_anomalies(rows, columns)
        sql_explanation = ASTValidator.generate_sql_explanation(secured_sql, dialect=engine_dialect)

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
                f"{', '.join(meta.get('tables_used', []))} para la consulta '{effective_question}'."
            )
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
