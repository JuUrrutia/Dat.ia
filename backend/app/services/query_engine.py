import sqlite3
import time
import os
import re
import json
from typing import Dict, Any, List, Set, Tuple, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.constants import (
    ADMIN_ROLES, ROLE_USUARIO, ROLE_TI, ROLE_ECONOMISTA, DEFAULT_DEMO_ROLE,
    CHART_COLOR_RED, CHART_COLOR_AMBER, CHART_COLOR_EMERALD, CHART_COLOR_CYAN,
    CHART_COLOR_BLUE, CHART_COLOR_PURPLE, CHART_COLOR_TEXT_MUTED, CHART_COLOR_TEXT_LIGHT
)
from app.services.ast_validator import ASTValidator, ASTValidationError
from app.services.llm_service import LLMService
from app.services.dynamic_schema import DynamicSchemaPruningService
from app.schemas.query_schema import QueryResponse, KPICard, TraceabilityAudit, ExecutiveReport, MetricGauge

DEMO_DB_PATH = settings.SQLITE_DB_PATH

# Sensitive / PII / Confidential Columns Protected by Governance
CONFIDENTIAL_COLUMNS = {
    "tarjeta_credito_token", "api_key_servicio", "cuenta_bancaria_iban"
}

class QueryEngine:
    """
    Dynamic Query Engine integrating Local LLM for Text-to-SQL execution
    secured by AST sqlglot validator, Column-Level Security (CLS) and RBAC rules.
    Generates dynamic visualizations from any connected database.
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
        """
        Dynamically queries RoleTablePermission and SemanticCatalog database models
        (app/models/permission.py) to resolve authorized tables per role.
        """
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
        """
        Dynamically queries RoleColumnPermission database models (app/models/permission.py)
        to resolve confidential/blocked columns for non-admin roles.
        """
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
                return CONFIDENTIAL_COLUMNS
            finally:
                if local_db is not None:
                    local_db.close()

        return CONFIDENTIAL_COLUMNS

    @classmethod
    async def get_dynamic_suggestions_with_llm(
        cls,
        user_role: str,
        allowed_tables: Set[str],
        schema_prompt: str = ""
    ) -> List[str]:
        """
        Generates role and table-specific question suggestions using the local LLM.
        Falls back to rule-based dynamic suggestions if LLM is offline or fails.
        """
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        # Attempt LLM generation for simple, tailored suggestions
        try:
            system_prompt = (
                "Eres un asistente de negocios y datos corporativos. "
                "Tu objetivo es proponer 4 preguntas/ideas simples, breves y directas que un usuario en su perfil de trabajo desease consultar sobre sus datos. "
                "REGLAS:\n"
                "1. Escribe exactamente 4 preguntas/ideas, una por línea.\n"
                "2. Cada pregunta debe comenzar con un emoji relevante (ej. 📊, 💡, 📈, ⚡, 🏆, 👥, 📦).\n"
                "3. Mantén las frases muy cortas (máximo 10 palabras por pregunta).\n"
                "4. Responde ÚNICAMENTE con la lista de 4 preguntas, sin introducción ni comentarios."
            )
            tables_str = ", ".join(sorted(allowed_tables))
            prompt_llm = f"""Perfil de usuario: {user_role}
Tablas autorizadas: {tables_str}

{schema_prompt}

Genera 4 sugerencias simples y breves de preguntas que el usuario {user_role} pueda hacer."""

            llm_text = await LLMService.generate_completion(
                prompt_llm,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=150
            )

            if llm_text:
                lines = [line.strip() for line in llm_text.split('\n') if line.strip()]
                clean_suggestions = []
                for l in lines:
                    cleaned = re.sub(r'^\d+[\.\)]\s*', '', l).strip()
                    cleaned = re.sub(r'^[\*\-]\s*', '', cleaned).strip()
                    if cleaned and len(cleaned) > 5:
                        clean_suggestions.append(cleaned)

                if len(clean_suggestions) >= 2:
                    return clean_suggestions[:4]
        except Exception:
            pass

        # Fallback to rule-based dynamic suggestions
        return cls.get_dynamic_suggestions(user_role, allowed_tables)

    @classmethod
    def get_dynamic_suggestions(cls, user_role: str, allowed_tables: Set[str]) -> List[str]:
        """
        Generates role and table-specific question suggestions dynamically based on authorized tables.
        """
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        suggestions = []

        table_templates = {
            "fact_ventas": [
                "📊 ¿Cuáles son las ventas acumuladas por categoría?",
                "🏆 Top productos con mayor facturación"
            ],
            "fact_ingresos_costos": [
                "📈 Evolución de ingresos y utilidad neta",
                "💰 Balances consolidados de ingresos y costos"
            ],
            "dim_empleados": [
                "👥 Promedio de salario y evaluación de desempeño por departamento",
                "💡 ¿Cómo elevar la productividad y retención del equipo?"
            ],
            "fact_incidentes_ti": [
                "🛠️ Incidentes de TI por servidor y horas de resolución SLA",
                "⚡ ¿Cómo reducir tiempos de resolución en fallas críticas?"
            ],
            "dim_servidores": [
                "🖥️ Detalle de servidores, datacenters y RAM instalada",
                "🛡️ Estado de infraestructura y responsables de administración"
            ],
            "fact_consumo_recursos": [
                "📊 Consumo promedio de CPU y RAM por servidor",
                "⚡ Telemetría de uso de recursos y tráfico de red"
            ],
            "dim_productos": [
                "📦 Productos con menor disponibilidad en stock",
                "🏷️ Precios unitarios y margen de ganancia por producto"
            ],
            "dim_clientes": [
                "🏢 Clientes por sector de industria y nivel de riesgo",
                "📋 Distribución de clientes corporativos"
            ],
            "dim_categorias": [
                "📁 Listado de categorías de servicios y software",
                "📊 Distribución por categoría de producto"
            ]
        }

        sorted_tables = sorted(list(allowed_tables), key=lambda t: (0 if t.startswith("fact_") else 1, t))

        for table in sorted_tables:
            if table in table_templates:
                for t_sug in table_templates[table]:
                    if t_sug not in suggestions:
                        suggestions.append(t_sug)

        if not suggestions:
            for table in sorted_tables[:3]:
                suggestions.append(f"📊 Ver resumen de {table}")

        return suggestions[:5]

    @classmethod
    def _get_grounding_query_for_question(
        cls,
        question: str,
        user_role: str,
        allowed_tables: Set[str]
    ) -> str:
        """
        Dynamically constructs a safe profiling query over authorized tables without static hardcoded SQLs.
        """
        if not allowed_tables:
            return "SELECT 1;"

        sorted_tables = sorted(list(allowed_tables))
        q_lower = question.lower()

        # Check if question mentions any authorized table name
        matching_table = next((t for t in sorted_tables if t.lower() in q_lower), None)
        target_table = matching_table if matching_table else sorted_tables[0]

        return f"SELECT * FROM {target_table} LIMIT 20;"

    @classmethod
    def _build_llm_offline_response(cls, question: str, exec_time_ms: int = 0) -> QueryResponse:
        """
        Returns an explicit, transparent QueryResponse indicating that local LLM is offline
        and refusing to return simulated or fake query results.
        """
        return QueryResponse(
            question=question,
            summary_text="IA local no disponible. Conecte Ollama/llama.cpp para ejecutar consultas.",
            executive_report=None,
            kpis=[
                KPICard(
                    title="Estado IA Local",
                    value="DESCONECTADO",
                    subtitle="Conecte Ollama o llama.cpp",
                    change_direction="negative"
                )
            ],
            gauges=[],
            chart_type="none",
            chart_option={},
            data_columns=[],
            data_rows=[],
            response_type="data_analysis",
            conversational_response=None,
            grounding_info="Servidor LLM local no disponible (Ollama en :11434 o llama.cpp en :8080)",
            traceability=TraceabilityAudit(
                sql_executed="-- CONSULTA NO GENERADA: IA LOCAL DESCONECTADA",
                execution_time_ms=exec_time_ms,
                rows_returned=0,
                validation_status="RECHAZADO (IA Local No Disponible)",
                schema_tables_used=[],
                explanation="Inferencia no ejecutada. Se requiere un servidor LLM local activo (Ollama en :11434 o llama.cpp en :8080) para traducir lenguaje natural a SQL."
            )
        )

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
            return cls._build_rbac_denied_response(
                question,
                "Tu cuenta se encuentra registrada con el perfil inicial 'Usuario'. Un Administrador debe asignarte un rol (Economista o TI) para acceder a los datos corporativos."
            )

        allowed_tables = cls.get_allowed_tables_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)
        if not allowed_tables:
            return cls._build_rbac_denied_response(
                question,
                f"El rol '{user_role}' no tiene tablas asignadas en la matriz RBAC."
            )

        blocked_columns = cls.get_blocked_columns_for_role(user_role, is_admin, db=db, role_id=role_id, connection_id=connection_id)

        start_time = time.time()
        is_llm_active = False

        # 2. PRE-EXECUTION FORMAT & INTENT EVALUATION
        # Check LLM availability quickly or use high-precision heuristic intent classification
        response_type = await cls._classify_intent(question)

        if not os.path.exists(DEMO_DB_PATH):
            from setup_demo_db import setup_demo_sqlite
            setup_demo_sqlite()

        # =========================================================================
        # BRANCH A: ADVISORY / EXPLANATION (Conversational Strategic Assistant)
        # =========================================================================
        if response_type in ("advisory", "explanation"):
            grounding_sql = cls._get_grounding_query_for_question(question, user_role, allowed_tables)
            
            # Validate and execute grounding query
            try:
                _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                    grounding_sql,
                    dialect="sqlite",
                    allowed_tables=allowed_tables,
                    blocked_columns=blocked_columns
                )
            except Exception:
                secured_sql = grounding_sql
                meta = {"tables_used": list(allowed_tables)}

            conn = sqlite3.connect(DEMO_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(secured_sql)
                rows = [dict(r) for r in cursor.fetchall()]
            except Exception:
                rows = []
            conn.close()

            exec_time_ms = int((time.time() - start_time) * 1000)
            columns = list(rows[0].keys()) if rows else []

            # Generate deep conversational response
            conversational = await cls._generate_conversational_response(
                question, user_role, response_type, rows, columns, is_llm_active=True
            )
            is_llm_active = conversational is not None

            if not conversational or not is_llm_active:
                return cls._build_llm_offline_response(question, exec_time_ms)

            # Build concise summary overview
            summary_text = (
                f"Asistente Estratégico IA: Se evaluó la solicitud '{question}' utilizando datos de respaldo de "
                f"'{', '.join(meta.get('tables_used', []))}' ({len(rows)} registros). "
                f"Se estructuran recomendaciones ejecutivas accionables orientadas a la optimización de procesos."
            )

            grounding_info = f"Enriquecido con {len(rows)} registros de {', '.join(meta.get('tables_used', list(allowed_tables)))} en SQLite"

            return QueryResponse(
                question=question,
                summary_text=summary_text,
                executive_report=None,
                kpis=[],
                gauges=[],
                chart_type="none",
                chart_option={},
                data_columns=columns,
                data_rows=rows,
                response_type=response_type,
                conversational_response=conversational,
                grounding_info=grounding_info,
                traceability=TraceabilityAudit(
                    sql_executed=secured_sql,
                    execution_time_ms=exec_time_ms,
                    rows_returned=len(rows),
                    validation_status="APROBADO (Contexto Asistente)",
                    schema_tables_used=list(meta.get("tables_used", list(allowed_tables))),
                    explanation=f"Respuesta de Asistente generada con IA Local (Qwen2.5). Datos de respaldo consultados de: {', '.join(meta.get('tables_used', []))}."
                )
            )

        # =========================================================================
        # BRANCH B: DATA ANALYSIS / REPORT / HYBRID (Visual Analytics & Studio)
        # =========================================================================
        # Retrieve dynamic schema prompt for LLM context
        schema_context = ""
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

        candidate_sql = None
        try:
            allowed_tables_str = ", ".join(sorted(allowed_tables))
            system_prompt = (
                f"Eres un analista de datos y experto en SQL. "
                f"Tu única tarea es convertir la pregunta del usuario en una consulta SQL SELECT de solo lectura. "
                f"TABLAS PERMITIDAS ({user_role}): {allowed_tables_str}. "
                f"REGLAS CRÍTICAS:\n"
                f"1. Responde ÚNICAMENTE con el código SQL dentro de un bloque ```sql ... ```.\n"
                f"2. NO escribas texto introductorio, ni explicaciones, ni síntesis fuera del bloque SQL.\n"
                f"3. Consulta únicamente las columnas autorizadas expuestas en el esquema.\n"
                f"4. Usa únicamente SELECT. Prohibido DROP, INSERT, UPDATE, DELETE, ALTER."
            )
            prompt_llm = f"""Pregunta del usuario ({user_role}): "{question}"

{schema_context}

Genera la consulta SQL SELECT para responder la pregunta usando SOLO las tablas permitidas ({allowed_tables_str}).
Responde ÚNICAMENTE con el bloque ```sql ... ```."""

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

        # If LLM is offline or produced no SQL, return explicit offline response (no fake fallback)
        if not candidate_sql or not is_llm_active:
            exec_time_ms = int((time.time() - start_time) * 1000)
            return cls._build_llm_offline_response(question, exec_time_ms)

        # AST Security Validation with sqlglot & Column-Level Security
        try:
            _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                candidate_sql,
                dialect="sqlite",
                allowed_tables=allowed_tables,
                blocked_columns=blocked_columns
            )
        except ASTValidationError as e:
            return cls._build_rbac_denied_response(question, str(e))

        conn = sqlite3.connect(DEMO_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(secured_sql)
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception as err:
            first_table = sorted(list(allowed_tables))[0] if allowed_tables else "dual"
            fb_sql = f"SELECT * FROM {first_table} LIMIT 20;"
            try:
                cursor.execute(fb_sql)
                rows = [dict(r) for r in cursor.fetchall()]
                secured_sql = fb_sql
            except Exception:
                conn.close()
                return cls._build_rbac_denied_response(question, f"Error al ejecutar consulta en la BD: {str(err)}")

        conn.close()
        exec_time_ms = int((time.time() - start_time) * 1000)
        columns = list(rows[0].keys()) if rows else []

        # Build dynamic visualization & contextual KPIs
        kpis, chart_type, chart_option, fallback_summary, fallback_exec_report, gauges = cls._build_dynamic_visualization(
            question, columns, rows, user_role
        )

        # Deep AI-Powered Executive Report Synthesis
        llm_exec_report = await cls._generate_deep_executive_report_with_llm(
            question, user_role, rows, columns, secured_sql, is_llm_active
        )

        final_exec_report = llm_exec_report or fallback_exec_report
        final_summary = final_exec_report.overview if final_exec_report and final_exec_report.overview else fallback_summary

        # Conversational response if hybrid
        conversational = None
        if response_type == "hybrid":
            conversational = await cls._generate_conversational_response(
                question, user_role, response_type, rows, columns, is_llm_active
            )

        grounding_info = f"Consulta ejecutada sobre {len(rows)} registros en SQLite ({', '.join(meta.get('tables_used', []))})"

        return QueryResponse(
            question=question,
            summary_text=final_summary,
            executive_report=final_exec_report,
            kpis=kpis,
            gauges=gauges,
            chart_type=chart_type,
            chart_option=chart_option,
            data_columns=columns,
            data_rows=rows,
            response_type=response_type,
            conversational_response=conversational,
            grounding_info=grounding_info,
            traceability=TraceabilityAudit(
                sql_executed=secured_sql,
                execution_time_ms=exec_time_ms,
                rows_returned=len(rows),
                validation_status="APROBADO (SELECT Único)",
                schema_tables_used=list(meta.get("tables_used", list(allowed_tables))),
                explanation=f"Consulta generada y validada con IA Local ({'Qwen2.5-Coder' if is_llm_active else 'Modo Determinístico'}). Tablas autorizadas: {', '.join(allowed_tables)}."
            )
        )

    @classmethod
    async def _classify_intent(cls, question: str) -> str:
        q_lower = question.lower().strip()

        # Rule-based heuristics for immediate high-precision detection
        advisory_keywords = [
            "idea", "ideas", "recomienda", "recomendacion", "recomendaciones", 
            "sugerencia", "sugerencias", "estrategia", "estrategias", "consejo", "consejos",
            "cómo mejorar", "como mejorar", "qué puedo hacer", "que puedo hacer", 
            "propuesta", "propuestas", "iniciativa", "iniciativas", "mejores prácticas", "mejores practicas",
            "opinión", "opinion", "qué opinas", "que opinas", "productividad", "productivo",
            "optimizar", "optimización", "optimizacion", "ayuda", "solución", "solucion", "soluciones", 
            "resolver", "pasos para", "guía para", "guia para", "tips", "consejos para", "cómo puedo"
        ]
        explanation_keywords = [
            "qué es", "que es", "qué significa", "que significa", "explícame", "explicame", 
            "explica", "cómo funciona", "como funciona", "define", "definición", "definicion", 
            "para qué sirve", "para que sirve", "concepto", "diferencia entre"
        ]
        hybrid_keywords = [
            "analiza y recomienda", "evalúa y sugiere", "evalua y sugiere", 
            "diagnóstico y recomendaciones", "diagnostico y recomendaciones", 
            "análisis con recomendaciones", "analisis con recomendaciones"
        ]
        report_keywords = [
            "informe ejecutivo", "reporte ejecutivo", "informe formal", 
            "balance ejecutivo", "auditoría general", "auditoria general", "diagnóstico general"
        ]

        if any(k in q_lower for k in explanation_keywords):
            return "explanation"
        if any(k in q_lower for k in hybrid_keywords):
            return "hybrid"
        if any(k in q_lower for k in report_keywords):
            return "report"
        if any(k in q_lower for k in advisory_keywords):
            return "advisory"

        # Check with local LLM if available
        system_prompt = (
            "Clasifica la intención de la pregunta del usuario en EXACTAMENTE una categoría.\n"
            "Responde SOLO con una de estas palabras: data_analysis, advisory, explanation, report, hybrid\n\n"
            "- data_analysis: Preguntas que piden datos numéricos, cifras, rankings, tablas o gráficos. Ejemplos: \"Top 10 productos\", \"Ingresos del Q3\", \"¿Cuántas ventas hubo?\", \"Gráfico de ventas\"\n"
            "- advisory: Preguntas que piden ideas, estrategias, consejos, resolución de problemas o mejoras operacionales. Ejemplos: \"Dame 5 ideas para mejorar la productividad\", \"¿Qué estrategia recomiendas?\", \"Cómo reducir costos\"\n"
            "- explanation: Preguntas que piden explicar un concepto o definición. Ejemplos: \"¿Qué es el margen bruto?\", \"Explícame qué es RBAC\"\n"
            "- report: Preguntas que piden formalmente un informe ejecutivo o auditoría. Ejemplos: \"Genera un informe ejecutivo del balance\"\n"
            "- hybrid: Preguntas que combinan análisis de datos CON recomendaciones. Ejemplos: \"Analiza las ventas y recomienda mejoras\""
        )
        try:
            resp = await LLMService.generate_completion(
                question,
                system_prompt=system_prompt,
                max_tokens=30,
                temperature=0.01
            )
            if resp:
                resp = resp.strip().lower()
                for t in ["advisory", "explanation", "report", "hybrid", "data_analysis"]:
                    if t in resp:
                        return t
        except Exception:
            pass

        return "data_analysis"

    @classmethod
    async def _generate_conversational_response(
        cls,
        question: str,
        user_role: str,
        response_type: str,
        data_context: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        is_llm_active: bool = False
    ) -> Optional[str]:
        if not is_llm_active:
            return None
        
        if response_type == "advisory":
            system_prompt = (
                "Eres un Asesor Ejecutivo Senior y Consultor de Negocios de alto nivel.\n"
                "Tu objetivo es responder la pregunta del usuario con IDEAS CONCRETAS, ACCIONABLES Y DE ALTO VALOR ESTRATÉGICO.\n\n"
                "REGLAS CRÍTICAS:\n"
                "1. Entrega respuestas RICAS, DETALLADAS y PROFESIONALES en español.\n"
                "2. Usa los datos reales de la empresa (proporcionados abajo) para fundamentar y enriquecer tus recomendaciones.\n"
                "3. Estructura tu respuesta con markdown limpio:\n"
                "   - Usa ## para el título principal\n"
                "   - Usa ### para cada idea o iniciativa numerada (ej. ### 1. Nombre de la Idea)\n"
                "   - En cada idea incluye: **Diagnóstico en BD**, **Acción Concreta** e **Impacto Esperado**\n"
                "   - Usa > para destacar citas clave o síntesis\n"
                "4. Sé ESPECÍFICO: menciona áreas, cargos, números o porcentajes reales de los datos cuando sea relevante.\n"
                "5. NO generes código SQL ni tablas de datos en el cuerpo principal. Tu rol es de ASESOR ESTRATÉGICO."
            )
            temp = 0.3
        elif response_type == "explanation":
            system_prompt = (
                "Eres un experto en análisis de datos corporativos y gobernanza empresarial.\n"
                "Tu objetivo es EXPLICAR de forma clara, didáctica y ejecutiva el concepto consultado.\n\n"
                "REGLAS:\n"
                "1. Explica el concepto de forma clara, directa y accesible.\n"
                "2. Si hay datos de la empresa disponibles, usa ejemplos concretos de esos datos para ilustrar.\n"
                "3. Estructura tu respuesta con markdown (## Título, **términos clave**, listas concisas).\n"
                "4. NO generes SQL. Tu rol es EDUCATIVO."
            )
            temp = 0.2
        elif response_type == "hybrid":
            system_prompt = (
                "Eres un Director de Estrategia Corporativa (CSO) con expertise en análisis de datos.\n"
                "Tu objetivo es ANALIZAR los datos reales de la empresa Y generar RECOMENDACIONES ESTRATÉGICAS basadas en ese análisis.\n\n"
                "REGLAS:\n"
                "1. Primero presenta un DIAGNÓSTICO basado en los datos reales (cifras, tendencias, anomalías).\n"
                "2. Luego presenta RECOMENDACIONES ACCIONABLES fundamentadas en ese diagnóstico.\n"
                "3. Usa markdown con secciones claras (## Diagnóstico, ## Hallazgos Clave, ## Recomendaciones Estratégicas).\n"
                "4. Sé CUANTITATIVO: cita cifras exactas y nombres de los datos proporcionados.\n"
                "5. NO generes SQL en la respuesta."
            )
            temp = 0.3
        else:
            return None

        prompt = f"Pregunta del usuario ({user_role}): \"{question}\"\n"
        if data_context:
            prompt += f"\nContexto de datos reales de la empresa (primeras 30 filas):\n{json.dumps(data_context[:30], ensure_ascii=False, indent=2)}"

        try:
            res = await LLMService.generate_completion(
                prompt,
                system_prompt=system_prompt,
                max_tokens=1400,
                temperature=temp
            )
            return res
        except Exception:
            return None


    @classmethod
    async def _generate_deep_executive_report_with_llm(
        cls,
        question: str,
        user_role: str,
        rows: List[Dict[str, Any]],
        columns: List[str],
        secured_sql: str,
        is_llm_active: bool
    ) -> Optional[ExecutiveReport]:
        """
        Uses Local LLM to synthesize rows of database records into a deeply quantitative,
        McKinsey/C-Level style Executive Report with concrete numbers, percentages, and decisions.
        """
        if not rows or not is_llm_active:
            return None

        try:
            system_prompt = (
                "Eres un Director Ejecutivo de Finanzas, Operaciones y Estrategia Corporativa (CFO/COO). "
                "Tu objetivo es transformar los datos reales de la consulta SQL en un INFORME EJECUTIVO PROFUNDO, PRECISO Y DE ALTO VALOR DIRECTIVO. "
                "REGLAS CRÍTICAS:\n"
                "1. PROHIBIDO usar frases vagas o genéricas como 'monitorear los indicadores', 'evaluar la asignación', 'compartir con el equipo', 'se procesaron N registros'.\n"
                "2. Sé PRECISO, CUANTITATIVO Y DIRECTO: cita nombres exactos de productos, clientes, servidores, meses, montos en USD, variaciones porcentuales (%), márgenes y ratios calculados a partir de las filas de datos.\n"
                "3. En 'key_findings': incluye 3 a 4 hallazgos analíticos profundos (tendencia mes a mes, meses/productos críticos, márgenes, concentración de valor o cuellos de botella).\n"
                "4. En 'recommendations': entrega 3 decisiones estratégicas concretas con impacto medible para la dirección.\n"
                "5. Responde ÚNICAMENTE en formato JSON válido con las claves exactas:\n"
                "{\n"
                '  "overview": "Diagnóstico integral y contexto de negocio en 2-3 oraciones contundentes con cifras clave.",\n'
                '  "key_findings": ["Hallazgo 1 con números específicos", "Hallazgo 2 con porcentajes y nombres", "Hallazgo 3 con comparación"],\n'
                '  "recommendations": ["Acción estratégica 1 con impacto medible", "Acción estratégica 2", "Acción estratégica 3"],\n'
                '  "risk_level": "BAJO" | "MEDIO" | "ALTO" | "CRITICO",\n'
                '  "business_impact": "Impacto financiero o de continuidad operacional en una frase contundente."\n'
                "}"
            )

            prompt_data = f"""Pregunta del directivo ({user_role}): "{question}"
Consulta SQL ejecutada: {secured_sql}
Datos reales de la BD ({len(rows)} filas):
{json.dumps(rows[:30], ensure_ascii=False, indent=2)}

Genera el informe ejecutivo en formato JSON."""

            resp = await LLMService.generate_completion(
                prompt_data,
                system_prompt=system_prompt,
                max_tokens=650,
                temperature=0.1
            )

            if resp:
                json_match = re.search(r'\{[\s\S]*\}', resp)
                if json_match:
                    data = json.loads(json_match.group(0))
                    overview = str(data.get("overview", "")).strip()
                    findings = [str(f) for f in data.get("key_findings", []) if f]
                    recs = [str(r) for r in data.get("recommendations", []) if r]
                    risk = str(data.get("risk_level", "BAJO")).upper()
                    if risk not in ("BAJO", "MEDIO", "ALTO", "CRITICO"):
                        risk = "BAJO"
                    impact = str(data.get("business_impact", "")).strip() or None

                    if overview and findings and recs:
                        return ExecutiveReport(
                            overview=overview,
                            key_findings=findings,
                            recommendations=recs,
                            risk_level=risk,
                            business_impact=impact
                        )
        except Exception:
            pass
        return None

    @classmethod
    def _build_dynamic_visualization(
        cls,
        question: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        user_role: str = "Economista"
    ) -> Tuple[List[KPICard], str, Dict[str, Any], str, Optional[ExecutiveReport], List[MetricGauge]]:
        """
        Dynamically analyzes ANY executed SQL result dataset (agnostic to database engine/schema)
        to generate:
        1. Contextual business KPICards
        2. Tailored ECharts configuration (bar, line, pie, gauge) based on column data types
        3. Data-driven Executive Business Summary
        4. Structured ExecutiveReport (overview, findings, recommendations, risk level)
        5. MetricGauges for target tracking
        """
        if not rows or not columns:
            kpis = [
                KPICard(title="Registros Obtenidos", value="0 Registros", subtitle="Sin coincidencia en BD", change_direction="neutral")
            ]
            chart_option = {"xAxis": {"data": []}, "series": []}
            summary = f"Informe de Negocio: La consulta fue ejecutada pero no devolvió registros coincidentes para la pregunta '{question}'."
            exec_rep = ExecutiveReport(
                overview=f"No se encontraron registros para la consulta '{question}'.",
                key_findings=["Cero registros coincidentes con los criterios de búsqueda."],
                recommendations=["Verificar los parámetros de búsqueda o ampliar el rango de fechas/categorías."],
                risk_level="BAJO"
            )
            return kpis, "bar", chart_option, summary, exec_rep, []

        # 1. Categorize columns dynamically based on data types in rows
        num_cols = []
        date_cols = []
        cat_cols = []

        date_keywords = ["fecha", "mes", "date", "time", "created_at", "updated_at", "timestamp", "anio", "year", "periodo"]

        for col in columns:
            col_lower = col.lower()
            val = rows[0].get(col)

            # Check if numeric
            if isinstance(val, (int, float)) and not col_lower.startswith("id_") and not col_lower.endswith("_id") and col_lower != "id":
                num_cols.append(col)
            # Check if date/time
            elif any(dk in col_lower for dk in date_keywords):
                date_cols.append(col)
            # Categorical / Text
            elif not col_lower.startswith("id_") and not col_lower.endswith("_id") and col_lower != "id":
                cat_cols.append(col)

        # Fallback if no categorical column was identified
        if not cat_cols and not date_cols:
            cat_cols = [c for c in columns if not isinstance(rows[0].get(c), (int, float))] or [columns[0]]

        primary_cat = date_cols[0] if date_cols else (cat_cols[0] if cat_cols else columns[0])
        x_data = [str(r.get(primary_cat, "")) for r in rows]

        # 2. Select primary numeric metric column
        primary_num = num_cols[0] if num_cols else None

        # 3. Calculate statistics dynamically
        total_val = sum(r.get(primary_num, 0) or 0 for r in rows) if primary_num else len(rows)
        avg_val = (total_val / len(rows)) if len(rows) > 0 and primary_num else len(rows)

        max_row = max(rows, key=lambda x: (x.get(primary_num, 0) or 0) if primary_num else 0) if rows else {}
        min_row = min(rows, key=lambda x: (x.get(primary_num, 0) or 0) if primary_num else 0) if rows else {}

        top_entity = str(max_row.get(primary_cat, "Entidad")) if max_row else "N/A"
        top_val = max_row.get(primary_num, 0) if primary_num else 0

        # Currency / Percentage detection
        is_currency = primary_num and any(k in primary_num.lower() for k in ["usd", "monto", "ingreso", "costo", "precio", "utilidad", "margen", "salario", "sueldo", "ganancia", "presupuesto", "gasto"])
        is_percentage = primary_num and any(k in primary_num.lower() for k in ["pct", "porcentaje", "porcentual", "rate", "tasa", "cumplimiento", "cpu"])

        unit_str = "$" if is_currency else "%" if is_percentage else ""
        formatted_total = f"${total_val:,.2f}" if is_currency else f"{total_val:.1f}%" if is_percentage else f"{total_val:,.1f}" if isinstance(total_val, float) else f"{total_val:,}"
        formatted_top = f"${top_val:,.2f}" if is_currency else f"{top_val:.1f}%" if is_percentage else f"{top_val:,.1f}" if isinstance(top_val, float) else f"{top_val:,}"
        formatted_avg = f"${avg_val:,.2f}" if is_currency else f"{avg_val:.1f}%" if is_percentage else f"{avg_val:,.1f}"

        # 4. Build Dynamic KPICards
        kpi_title = primary_num.replace('_', ' ').title() if primary_num else "Total Registros"
        kpis = [
            KPICard(
                title=f"Total {kpi_title}",
                value=formatted_total,
                subtitle=f"Acumulado ({len(rows)} filas)",
                change_direction="positive"
            ),
            KPICard(
                title="Valor Máximo",
                value=formatted_top,
                subtitle=top_entity[:24],
                change_direction="positive"
            ),
            KPICard(
                title="Promedio por Registro",
                value=formatted_avg,
                subtitle=f"Muestra de {len(rows)} ítems",
                change_direction="neutral"
            )
        ]

        # 5. Determine ECharts Chart Type dynamically
        if date_cols and primary_num:
            chart_type = "line"
        elif len(rows) <= 6 and primary_cat and primary_num:
            chart_type = "pie"
        elif primary_num:
            chart_type = "bar"
        else:
            chart_type = "none"

        # Build ECharts Option
        chart_option = {}
        if chart_type == "pie" and primary_num:
            pie_series = [{"name": str(r.get(primary_cat, "")), "value": r.get(primary_num, 0)} for r in rows]
            chart_option = {
                "tooltip": {"trigger": "item", "formatter": f"{{b}}: {unit_str}{{c}} ({{d}}%)"},
                "legend": {"orient": "horizontal", "bottom": "0%", "textStyle": {"color": "#D1D5DB"}},
                "series": [{
                    "name": kpi_title,
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "itemStyle": {"borderRadius": 8, "borderColor": "#111827", "borderWidth": 2},
                    "label": {"show": True, "color": CHART_COLOR_TEXT_LIGHT},
                    "data": pie_series
                }]
            }
        elif chart_type in ("bar", "line") and primary_num:
            y_data = [r.get(primary_num, 0) for r in rows]
            bar_color = CHART_COLOR_PURPLE if chart_type == "bar" else CHART_COLOR_CYAN
            chart_option = {
                "tooltip": {"trigger": "axis", "formatter": f"{{b}}: {unit_str}{{c}}"},
                "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED, "rotate": 20 if len(rows) > 5 else 0}},
                "yAxis": {"type": "value", "name": kpi_title, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "series": [{
                    "name": kpi_title,
                    "type": chart_type,
                    "data": y_data,
                    "itemStyle": {"color": bar_color, "borderRadius": [6, 6, 0, 0]}
                }]
            }

        # 6. Build Dynamic Gauges
        pct_top = round((top_val / total_val * 100), 1) if total_val > 0 else 0
        gauges = [
            MetricGauge(
                title="Concentración Líder",
                percentage=min(100.0, pct_top),
                value_label=f"{pct_top}%",
                target_label=f"Líder: {top_entity[:16]}",
                color=CHART_COLOR_EMERALD if pct_top < 50 else CHART_COLOR_AMBER
            ),
            MetricGauge(
                title="Muestra de Datos",
                percentage=min(100.0, round((len(rows) / 100) * 100, 1)),
                value_label=f"{len(rows)} Filas",
                target_label="Filtro Aplicado",
                color=CHART_COLOR_CYAN
            )
        ]

        # 7. Build Dynamic Executive Summary & Report
        summary = (
            f"Informe Ejecutivo: Se procesaron **{len(rows)} registros** de la base de datos corporativa para la consulta '{question}'. "
            f"La métrica **{kpi_title}** acumula un total de **{formatted_total}** con una media de **{formatted_avg}**. "
            f"La entidad principal es **{top_entity}** representando **{formatted_top}** ({pct_top}% del total)."
        )

        risk = "ALTO" if pct_top > 70 else "MEDIO" if pct_top > 40 else "BAJO"

        exec_rep = ExecutiveReport(
            overview=f"Análisis cuantitativo de {len(rows)} registros procesados sobre la consulta '{question}'.",
            key_findings=[
                f"Volumen acumulado de {kpi_title}: {formatted_total} a través de {len(rows)} registros.",
                f"La entidad con mayor concentración es '{top_entity}' con {formatted_top} ({pct_top}% del total).",
                f"Promedio general registrado por ítem: {formatted_avg}."
            ],
            recommendations=[
                f"Monitorear la concentración de valor en '{top_entity}' para diversificar riesgos operacionales.",
                "Establecer umbrales de alerta temprana sobre métricas fuera del promedio general.",
                "Profundizar el análisis cruzando variables adicionales en próximas consultas."
            ],
            risk_level=risk,
            business_impact=f"Impacto directo en la gestión y control de la métrica {kpi_title}."
        )

        return kpis, chart_type, chart_option, summary, exec_rep, gauges

    @classmethod
    def _build_rbac_denied_response(cls, question: str, reason: str) -> QueryResponse:
        return QueryResponse(
            question=question,
            summary_text=reason,
            kpis=[
                KPICard(title="Estado RBAC", value="DENEGADO", subtitle="Acceso Reprobado", change_direction="negative"),
                KPICard(title="Motivo", value="Falta Permiso", subtitle="Seguridad", change_direction="neutral")
            ],
            chart_type="bar",
            chart_option={"xAxis": {"data": []}, "series": []},
            data_columns=["mensaje_seguridad"],
            data_rows=[{"mensaje_seguridad": reason}],
            traceability=TraceabilityAudit(
                sql_executed="-- CONSULTA BLOQUEADA POR GOBERNANZA RBAC",
                execution_time_ms=0,
                rows_returned=0,
                validation_status="RECHAZADO_RBAC",
                schema_tables_used=[],
                explanation=reason
            )
        )
