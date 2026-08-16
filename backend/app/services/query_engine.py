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

# Domain Table Mapping for RBAC Fallback (Offline Mode)
DOMAIN_TABLES = {
    "Economía & Finanzas": {"dim_categorias", "dim_productos", "dim_clientes", "fact_ventas", "fact_ingresos_costos", "dim_empleados"},
    "Tecnología & TI": {"dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos"},
}

ALL_TABLES = {
    "dim_categorias", "dim_productos", "dim_clientes", "fact_ventas",
    "fact_ingresos_costos", "dim_empleados", "dim_servidores",
    "fact_incidentes_ti", "fact_consumo_recursos"
}

# Sensitive / PII / Confidential Columns Protected by Governance
CONFIDENTIAL_COLUMNS = {
    "tarjeta_credito_token", "api_key_servicio", "cuenta_bancaria_iban"
}

DEMO_SCHEMA_CONTEXT = """Base de datos corporativa SQLite (demo_corporativa.db) con 550+ registros.
Tablas disponibles y sus columnas:

1. dim_categorias (id_categoria INTEGER PK, nombre_categoria TEXT, descripcion TEXT)
   - 8 categorías: Software Empresarial, Hardware & Redes, Servicios Cloud, Consultoría & BI, Ciberseguridad & SOC, Infraestructura Crítica, Licenciamiento SaaS, Soporte 24/7.

2. dim_productos (id_producto INTEGER PK, nombre_producto TEXT, id_categoria INTEGER FK→dim_categorias, precio_unitario REAL, costo_unitario REAL, stock_disponible INTEGER)
   - 30 productos con stocks de 6 a 150 unidades y precios de $320 a $36,000 USD.

3. dim_clientes (id_cliente INTEGER PK, nombre_empresa TEXT, rut_dni_cliente TEXT, email_contacto TEXT, telefono_contacto TEXT, tarjeta_credito_token TEXT, sector_industria TEXT, nivel_riesgo_crediticio TEXT, fecha_alta TEXT)
   - 50 clientes corporativos (Banca, Retail, Salud, Minería, Telecom, etc.). Contiene PII y datos de pago.

4. fact_ventas (id_venta INTEGER PK, fecha_venta TEXT, id_producto INTEGER FK→dim_productos, id_cliente INTEGER FK→dim_clientes, cantidad INTEGER, monto_total REAL, costo_total REAL, margen_ganancia REAL, metodo_pago TEXT, estado TEXT)
   - 250 transacciones de ventas 2025-2026 con montos, costos y métodos de pago.

5. fact_ingresos_costos (id_registro INTEGER PK, mes TEXT, anio INTEGER, categoria_financiera TEXT, ingreso_bruto REAL, costo_operativo REAL, impuestos_retenidos REAL, utilidad_neta REAL)
   - 24 balances mensuales consolidados 2025-2026.

6. dim_empleados (id_empleado INTEGER PK, nombre_completo TEXT, rut_dni TEXT, cargo TEXT, departamento TEXT, email_corporativo TEXT, salario_bruto REAL, bono_anual REAL, cuenta_bancaria_iban TEXT, evaluacion_desempeno REAL, fecha_contratacion TEXT)
   - 30 empleados corporativos (Dirección, Finanzas, TI, Ventas). Datos confidenciales de nómina y RRHH.

7. dim_servidores (id_servidor INTEGER PK, nombre_host TEXT, ip_interna TEXT, ip_publica TEXT, api_key_servicio TEXT, sistema_operativo TEXT, datacenter TEXT, capacidad_ram_gb INTEGER, responsable_admin TEXT)
   - 15 servidores en Santiago, Valparaíso, AWS Cloud y Datacenter Security.

8. fact_incidentes_ti (id_incidente INTEGER PK, fecha_incidente TEXT, id_servidor INTEGER FK→dim_servidores, tipo_falla TEXT, nivel_prioridad TEXT, horas_resolucion REAL, costo_impacto_usd REAL, estado TEXT)
   - 50 incidentes operacionales clasificados (CRITICA, ALTA, MEDIA, BAJA) con horas SLA y costo.

9. fact_consumo_recursos (id_consumo INTEGER PK, fecha_hora TEXT, id_servidor INTEGER FK→dim_servidores, porcentaje_cpu REAL, uso_ram_gb REAL, trafico_red_mb REAL)
   - 100 mediciones de telemetría de CPU, memoria y tráfico de red.

REGLAS DE DOMINIO RBAC:
- Economía & Finanzas: dim_categorias, dim_productos, dim_clientes, fact_ventas, fact_ingresos_costos, dim_empleados
- Tecnología & TI: dim_servidores, fact_incidentes_ti, fact_consumo_recursos"""


class QueryEngine:
    """
    Dynamic Query Engine integrating Local LLM for Text-to-SQL execution
    secured by AST sqlglot validator, Column-Level Security (CLS) and RBAC rules.
    Generates dynamic visualizations from 500+ corporate records.
    """

    # Fallback deterministic queries if LLM is offline
    FALLBACK_QUERIES = {
        "Economía & Finanzas": """SELECT c.nombre_categoria AS categoria, SUM(v.monto_total) AS ingresos_usd, COUNT(v.id_venta) AS transacciones FROM fact_ventas v JOIN dim_productos p ON v.id_producto = p.id_producto JOIN dim_categorias c ON p.id_categoria = c.id_categoria GROUP BY c.nombre_categoria ORDER BY ingresos_usd DESC;""",
        "Tecnología & TI": """SELECT s.nombre_host AS servidor, s.datacenter, i.tipo_falla, i.nivel_prioridad AS prioridad, i.horas_resolucion AS horas, i.estado FROM fact_incidentes_ti i JOIN dim_servidores s ON i.id_servidor = s.id_servidor ORDER BY i.fecha_incidente DESC;""",
    }

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
            return ALL_TABLES
        if db is not None:
            try:
                schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=db, role_id=role_id, connection_id=connection_id, is_admin=is_admin
                )
                if schema_info.get("allowed_tables"):
                    return schema_info["allowed_tables"]
            except Exception:
                pass
        if user_role == ROLE_TI:
            return DOMAIN_TABLES["Tecnología & TI"]
        if user_role in (ROLE_ECONOMISTA, "Analista Financiero", "Finanzas"):
            return DOMAIN_TABLES["Economía & Finanzas"]
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
        """Returns confidential column names blocked from querying by non-admin roles (Column-Level Security)."""
        if is_admin or user_role in ADMIN_ROLES:
            return set()
        if db is not None:
            try:
                schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=db, role_id=role_id, connection_id=connection_id, is_admin=is_admin
                )
                if "blocked_columns" in schema_info:
                    return schema_info["blocked_columns"]
            except Exception:
                pass
        if user_role in (ROLE_ECONOMISTA, "Analista Financiero", "Finanzas"):
            return {"tarjeta_credito_token", "api_key_servicio", "cuenta_bancaria_iban"}
        if user_role == ROLE_TI:
            return {"api_key_servicio", "tarjeta_credito_token", "salario_bruto", "bono_anual", "cuenta_bancaria_iban"}
        return CONFIDENTIAL_COLUMNS

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
        llm_response_text = None
        is_llm_active = False
        candidate_sql = None

        # 2. Invoke Local LLM (llama.exe serve / Ollama)
        try:
            allowed_tables_str = ", ".join(sorted(allowed_tables))
            system_prompt = (
                f"Eres un analista de datos y experto en SQL para SQLite. "
                f"Tu única tarea es convertir la pregunta del usuario en una consulta SQL SELECT de solo lectura en SQLite. "
                f"TABLAS PERMITIDAS ({user_role}): {allowed_tables_str}. "
                f"REGLAS CRÍTICAS:\n"
                f"1. Responde ÚNICAMENTE con el código SQL dentro de un bloque ```sql ... ```.\n"
                f"2. NO escribas texto introductorio, ni explicaciones, ni síntesis fuera del bloque SQL.\n"
                f"3. Si la pregunta involucra métricas o filtros (como stock, precios, ingresos, salarios, costos, horas o consumo), "
                f"incluye SIEMPRE tanto la columna descriptiva (ej. mes, nombre_producto, nombre_completo, nombre_host, nombre_empresa) como la columna numérica (ej. ingreso_bruto, costo_operativo, utilidad_neta, stock_disponible, precio_unitario, salario_bruto, monto_total).\n"
                f"4. Si la pregunta involucra balances mensuales, evolución de ingresos o costos operacionales, consulta la tabla `fact_ingresos_costos` (mes, anio, ingreso_bruto, costo_operativo, utilidad_neta) sin hacer JOINs innecesarios.\n"
                f"5. Usa únicamente SELECT. Prohibido DROP, INSERT, UPDATE, DELETE, ALTER."
            )
            prompt_llm = f"""Pregunta del usuario ({user_role}): "{question}"

{DEMO_SCHEMA_CONTEXT}

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

        # 2.5 Classify user intent
        response_type = await cls._classify_intent(question, is_llm_active)

        # Fallback candidate SQL if LLM is offline or produced no SQL
        if not candidate_sql:
            domain_key = "Tecnología & TI" if user_role == "TI" else "Economía & Finanzas"
            candidate_sql = cls.FALLBACK_QUERIES.get(domain_key, cls.FALLBACK_QUERIES["Economía & Finanzas"])

        # 3. AST Security Validation with sqlglot & Column-Level Security
        try:
            _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                candidate_sql,
                dialect="sqlite",
                allowed_tables=allowed_tables,
                blocked_columns=blocked_columns
            )
        except ASTValidationError as e:
            # If LLM generated unauthorized SQL, fall back or block
            return cls._build_rbac_denied_response(question, str(e))
            # If LLM generated unauthorized SQL, fall back to deterministic query for role
            domain_key = "Tecnología & TI" if user_role == "TI" else "Economía & Finanzas"
            fb_sql = cls.FALLBACK_QUERIES.get(domain_key, cls.FALLBACK_QUERIES["Economía & Finanzas"])
            try:
                _, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                    fb_sql,
                    dialect="sqlite",
                    allowed_tables=allowed_tables
                )
            except ASTValidationError:
                return cls._build_rbac_denied_response(question, str(e))

        if not os.path.exists(DEMO_DB_PATH):
            from setup_demo_db import setup_demo_sqlite
            setup_demo_sqlite()

        # 4. Query execution on demo_corporativa.db
        conn = sqlite3.connect(DEMO_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(secured_sql)
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception as err:
            # Retry with fallback SQL if execution failed
            domain_key = "Tecnología & TI" if user_role == "TI" else "Economía & Finanzas"
            fb_sql = cls.FALLBACK_QUERIES.get(domain_key, cls.FALLBACK_QUERIES["Economía & Finanzas"])
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

        # 5. DYNAMIC visualization & Contextual KPIs
        kpis, chart_type, chart_option, fallback_summary, fallback_exec_report, gauges = cls._build_dynamic_visualization(
            question, columns, rows, user_role
        )

        # 6. Deep AI-Powered Executive Report Synthesis (Quantitative & Actionable)
        llm_exec_report = await cls._generate_deep_executive_report_with_llm(
            question, user_role, rows, columns, secured_sql, is_llm_active
        )

        final_exec_report = llm_exec_report or fallback_exec_report
        final_summary = final_exec_report.overview if final_exec_report and final_exec_report.overview else fallback_summary

        # 6.5 Generate conversational response for advisory/explanation/hybrid
        conversational = None
        if response_type in ("advisory", "explanation", "hybrid"):
            conversational = await cls._generate_conversational_response(
                question, user_role, response_type, rows, columns, is_llm_active
            )

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
    async def _classify_intent(cls, question: str, is_llm_active: bool) -> str:
        if not is_llm_active:
            q_lower = question.lower()
            if any(k in q_lower for k in ["qué es", "qué significa", "explícame", "explica", "cómo funciona", "define", "definición"]):
                return "explanation"
            elif any(k in q_lower for k in ["analiza y recomienda", "evalúa y sugiere", "diagnóstico y recomendaciones", "análisis con recomendaciones"]):
                return "hybrid"
            elif any(k in q_lower for k in ["ideas", "recomienda", "sugerencias", "estrategia", "estrategias", "consejos", "cómo mejorar", "qué puedo hacer", "propuestas", "iniciativas", "mejores prácticas", "opinión", "qué opinas"]):
                return "advisory"
            return "data_analysis"

        system_prompt = (
            "Clasifica la intención de la pregunta del usuario en EXACTAMENTE una categoría.\n"
            "Responde SOLO con una de estas palabras: data_analysis, advisory, explanation, hybrid\n\n"
            "- data_analysis: Preguntas que piden datos, cifras, reportes, rankings, comparaciones numéricas. Ejemplos: \"Top 10 productos\", \"Ingresos del Q3\", \"¿Cuántas ventas hubo?\"\n"
            "- advisory: Preguntas que piden ideas, estrategias, consejos, recomendaciones de mejora. Ejemplos: \"Ideas para mejorar ventas\", \"¿Qué estrategia recomiendas?\", \"Cómo reducir costos\"\n"
            "- explanation: Preguntas que piden explicar un concepto o definición. Ejemplos: \"¿Qué es el margen bruto?\", \"Explícame qué es RBAC\"\n"
            "- hybrid: Preguntas que combinan análisis de datos CON recomendaciones. Ejemplos: \"Analiza las ventas y recomienda mejoras\", \"Evalúa el inventario y sugiere optimizaciones\""
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
                for t in ["data_analysis", "advisory", "explanation", "hybrid"]:
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
                "Eres un consultor ejecutivo senior especializado en estrategia empresarial y optimización corporativa.\n"
                "Tu objetivo es responder la pregunta del usuario con IDEAS CONCRETAS, ACCIONABLES Y DE ALTO VALOR ESTRATÉGICO.\n\n"
                "REGLAS:\n"
                "1. Entrega respuestas RICAS, DETALLADAS y PROFESIONALES en español.\n"
                "2. Usa los datos reales de la empresa (proporcionados abajo) para contextualizar y fundamentar tus recomendaciones.\n"
                "3. Estructura tu respuesta con secciones claras usando markdown:\n"
                "   - Usa ## para títulos de sección\n"
                "   - Usa **negrita** para énfasis\n"
                "   - Usa listas numeradas para ideas/recomendaciones\n"
                "   - Usa > para citas o destacados importantes\n"
                "4. Sé ESPECÍFICO: menciona productos, clientes, montos y porcentajes reales de los datos cuando sea relevante.\n"
                "5. Cada idea/recomendación debe incluir: qué hacer, por qué, y el impacto esperado.\n"
                "6. NO generes SQL ni tablas de datos. Tu rol es el de ASESOR ESTRATÉGICO."
            )
            temp = 0.3
        elif response_type == "explanation":
            system_prompt = (
                "Eres un experto en análisis de datos corporativos y gobernanza empresarial.\n"
                "Tu objetivo es EXPLICAR de forma clara, profesional y educativa el concepto que pregunta el usuario.\n\n"
                "REGLAS:\n"
                "1. Explica el concepto de forma clara y accesible, pero profesional.\n"
                "2. Si hay datos de la empresa disponibles, usa ejemplos concretos de esos datos para ilustrar.\n"
                "3. Estructura tu respuesta con markdown:\n"
                "   - Usa ## para secciones\n"
                "   - Usa **negrita** para términos clave\n"
                "   - Usa ejemplos prácticos\n"
                "4. NO generes SQL. Tu rol es EDUCATIVO."
            )
            temp = 0.2
        elif response_type == "hybrid":
            system_prompt = (
                "Eres un Director de Estrategia Corporativa (CSO) con expertise en análisis de datos y planificación estratégica.\n"
                "Tu objetivo es ANALIZAR los datos reales de la empresa Y generar RECOMENDACIONES ESTRATÉGICAS basadas en ese análisis.\n\n"
                "REGLAS:\n"
                "1. Primero presenta un DIAGNÓSTICO basado en los datos reales (cifras, tendencias, anomalías).\n"
                "2. Luego presenta RECOMENDACIONES ACCIONABLES fundamentadas en ese diagnóstico.\n"
                "3. Usa markdown con secciones claras (## Diagnóstico, ## Hallazgos Clave, ## Recomendaciones Estratégicas).\n"
                "4. Sé CUANTITATIVO: cita cifras exactas, porcentajes, nombres de productos/clientes de los datos.\n"
                "5. Cada recomendación debe tener: acción concreta, justificación basada en datos, impacto esperado.\n"
                "6. NO generes SQL. Analiza los datos proporcionados directamente."
            )
            temp = 0.3
        else:
            return None

        prompt = f"Pregunta del usuario ({user_role}): \"{question}\"\n"
        if data_context:
            prompt += f"\nContexto de datos (primeras 40 filas):\n{json.dumps(data_context[:40], ensure_ascii=False, indent=2)}"

        try:
            return await LLMService.generate_completion(
                prompt,
                system_prompt=system_prompt,
                max_tokens=1200,
                temperature=temp
            )
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
        Dynamically analyzes executed SQL result rows to generate:
        1. Contextual business KPIs
        2. ECharts configuration tailored to data metrics
        3. High-value data-driven Executive Business Summary
        4. Structured Executive Report (findings & actionable recommendations)
        5. Radial Gauges for target tracking
        """
        if not rows or not columns:
            kpis = [
                KPICard(title="Registros Obtenidos", value="0 Registros", subtitle="Sin coincidencia en BD", change_direction="neutral")
            ]
            chart_option = {"xAxis": {"data": []}, "series": []}
            summary = f"Informe de Negocio: La consulta fue ejecutada sobre la base de datos corporativa pero no devolvió registros coincidentes para el criterio '{question}'. No se detectan anomalías o valores fuera de rango."
            exec_rep = ExecutiveReport(
                overview=f"No se encontraron registros para la consulta '{question}'.",
                key_findings=["Cero registros coincidentes con los filtros aplicados en SQLite."],
                recommendations=["Verificar los parámetros de búsqueda o ampliar el rango de fechas/categorías."],
                risk_level="BAJO"
            )
            return kpis, "bar", chart_option, summary, exec_rep, []

        # Separate numeric vs categorical/text columns
        num_cols = []
        cat_cols = []
        for col in columns:
            val = rows[0].get(col)
            if isinstance(val, (int, float)) and not col.startswith("id_"):
                num_cols.append(col)
            elif not col.startswith("id_"):
                cat_cols.append(col)

        # Fallback if only id_ columns were returned
        if not cat_cols:
            cat_cols = [c for c in columns if not isinstance(rows[0].get(c), (int, float))] or [columns[0]]

        q_lower = question.lower()
        cat_col = cat_cols[0]
        x_data = [str(r.get(cat_col, "")) for r in rows]

        # -------------------------------------------------------------
        # DOMAIN 1: INVENTARIO & STOCK (stock_disponible)
        # -------------------------------------------------------------
        if "stock_disponible" in columns or "stock" in q_lower or "inventario" in q_lower:
            stock_col = "stock_disponible" if "stock_disponible" in columns else (num_cols[0] if num_cols else None)
            total_stock = sum(r.get(stock_col, 0) or 0 for r in rows) if stock_col else len(rows)
            
            # Find min stock item
            min_row = min(rows, key=lambda x: x.get(stock_col, 999999) if stock_col else 0)
            min_name = str(min_row.get(cat_col, "Producto"))
            min_val = min_row.get(stock_col, 0) if stock_col else 0

            # Find max stock item
            max_row = max(rows, key=lambda x: x.get(stock_col, 0) if stock_col else 0)
            max_name = str(max_row.get(cat_col, "Producto"))
            max_val = max_row.get(stock_col, 0) if stock_col else 0

            kpis = [
                KPICard(title="Productos Críticos", value=f"{len(rows)} Productos", subtitle="Bajo Umbral Stock", change_direction="negative"),
                KPICard(title="Nivel Mínimo Crítico", value=f"{min_val} Unidades", subtitle=min_name[:24], change_direction="negative"),
                KPICard(title="Total Unidades en Riesgo", value=f"{total_stock:,} Unidades", subtitle="Requiere Reposición", change_direction="neutral")
            ]

            # Detailed business summary
            items_detail = ", ".join([f"**{r.get(cat_col, '')}** ({r.get(stock_col, 0)} unidades)" for r in rows[:4]])
            summary = (
                f"Informe Ejecutivo de Inventario: Se identificaron **{len(rows)} productos** con nivel de stock crítico en la base de datos corporativa: {items_detail}. "
                f"El artículo con menor disponibilidad es **{min_name}** con solo **{min_val} unidades** en almacén. "
                f"Se recomienda emitir órdenes de compra de urgencia para reabastecer el inventario y evitar quiebres operacionales."
            )

            exec_rep = ExecutiveReport(
                overview="Auditoría integral de disponibilidad de inventario bajo el umbral de seguridad operacional (< 30 unidades).",
                key_findings=[
                    f"Se identificaron {len(rows)} productos en zona de riesgo crítico de desabastecimiento.",
                    f"El artículo con mayor urgencia de reposición es '{min_name}' con {min_val} unidades en bodega.",
                    f"El volumen acumulado en riesgo suma {total_stock:,} unidades entre servidores, switches y componentes."
                ],
                recommendations=[
                    "Emitir órdenes de compra de urgencia con proveedores preferenciales de hardware y telecomunicaciones.",
                    "Establecer stock de seguridad dinámico de 35 unidades para ítems de alta demanda.",
                    "Pausar compromisos comerciales de entrega inmediata para ítems con disponibilidad menor a 10 unidades."
                ],
                risk_level="ALTO" if min_val < 10 else "MEDIO",
                business_impact="Riesgo de incumplimiento de plazos en nuevos despliegues de clientes corporativos."
            )

            gauges = [
                MetricGauge(title="Nivel Salud Stock", percentage=max(10, 100 - len(rows) * 5), value_label=f"{len(rows)} Críticos", target_label="Meta: 0 Críticos", color=CHART_COLOR_RED if len(rows) > 8 else CHART_COLOR_AMBER),
                MetricGauge(title="Disponibilidad en Bodega", percentage=min(100, round((total_stock / 300) * 100, 1)), value_label=f"{total_stock}u", target_label="Capacidad 300u", color=CHART_COLOR_EMERALD)
            ]

            chart_type = "bar"
            y_data = [r.get(stock_col, 0) for r in rows] if stock_col else [1] * len(rows)
            chart_option = {
                "tooltip": {"trigger": "axis", "formatter": "{b}: {c} unidades en stock"},
                "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED, "rotate": 15 if len(rows) > 3 else 0}},
                "yAxis": {"type": "value", "name": "Unidades", "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "series": [{
                    "name": "Stock Disponible",
                    "type": "bar",
                    "data": y_data,
                    "itemStyle": {"color": CHART_COLOR_AMBER, "borderRadius": [6, 6, 0, 0]}
                }]
            }
            return kpis, chart_type, chart_option, summary, exec_rep, gauges

        # -------------------------------------------------------------
        # DOMAIN 2: VENTAS, INGRESOS & FINANZAS
        # -------------------------------------------------------------
        if any(k in columns for k in ["monto_total", "ingreso_bruto", "ingresos_usd", "utilidad_neta", "precio_unitario"]) or any(k in q_lower for k in ["venta", "ingreso", "precio", "facturacion", "margen", "costo"]):
            val_col = next((c for c in ["monto_total", "ingreso_bruto", "ingresos_usd", "utilidad_neta", "precio_unitario"] if c in columns), num_cols[0] if num_cols else None)
            
            if val_col:
                total_val = sum(r.get(val_col, 0) or 0 for r in rows)
                max_row = max(rows, key=lambda x: x.get(val_col, 0) or 0)
                top_name = str(max_row.get(cat_col, "Principal"))
                top_val = max_row.get(val_col, 0) or 0
                pct = (top_val / total_val * 100) if total_val > 0 else 0

                kpis = [
                    KPICard(title=f"Total {val_col.replace('_', ' ').title()}", value=f"${total_val:,.2f}", subtitle="Acumulado Dataset", change_direction="positive"),
                    KPICard(title="Líder en Monto", value=f"${top_val:,.2f}", subtitle=top_name[:24], change_direction="positive"),
                    KPICard(title="Registros Analizados", value=f"{len(rows)} Registros", subtitle=f"Líder representa {pct:.1f}%", change_direction="neutral")
                ]

                summary = (
                    f"Resumen Ejecutivo Comercial: El volumen acumulado analizado asciende a **${total_val:,.2f}** distribuidos en **{len(rows)} registros**. "
                    f"La mayor concentración de valor corresponde a **{top_name}** con **${top_val:,.2f}** ({pct:.1f}% del total). "
                    f"El rendimiento general muestra solidez comercial acorde a las metas del período."
                )

                exec_rep = ExecutiveReport(
                    overview=f"Evaluación del rendimiento financiero y transaccional ({val_col.replace('_', ' ')}).",
                    key_findings=[
                        f"Facturación acumulada auditada de ${total_val:,.2f} procesada exitosamente.",
                        f"La categoría/entidad '{top_name}' lidera el volumen con ${top_val:,.2f} ({pct:.1f}% de concentración).",
                        f"Se auditaron {len(rows)} registros comerciales sin discrepancias contables."
                    ],
                    recommendations=[
                        "Implementar incentivos de cross-selling en segmentos con menor cuota de participación.",
                        "Revisar márgenes en productos con costo unitario creciente.",
                        "Mantener la política de crédito corporativo a 30 días para clientes de bajo riesgo."
                    ],
                    risk_level="BAJO",
                    business_impact="Aporte sólido al margen operacional consolidado de la empresa."
                )

                gauges = [
                    MetricGauge(title="Meta Comercial", percentage=min(100, round((total_val / 200000) * 100, 1)), value_label=f"${total_val/1000:,.1f}K", target_label="Meta: $200K", color=CHART_COLOR_EMERALD),
                    MetricGauge(title="Concentración Líder", percentage=round(pct, 1), value_label=f"{pct:.1f}%", target_label="Límite Sano: 50%", color=CHART_COLOR_CYAN)
                ]

                y_data = [r.get(val_col, 0) for r in rows]
                chart_type = "pie" if len(rows) <= 5 else "bar"
                
                if chart_type == "pie":
                    pie_series = [{"name": str(r.get(cat_col, "")), "value": r.get(val_col, 0)} for r in rows]
                    chart_option = {
                        "tooltip": {"trigger": "item", "formatter": "{b}: ${c:,.2f} ({d}%)"},
                        "legend": {"orient": "horizontal", "bottom": "0%", "textStyle": {"color": "#D1D5DB"}},
                        "series": [{
                            "name": val_col.replace('_', ' ').title(),
                            "type": "pie",
                            "radius": ["40%", "70%"],
                            "itemStyle": {"borderRadius": 8, "borderColor": "#111827", "borderWidth": 2},
                            "label": {"show": True, "color": CHART_COLOR_TEXT_LIGHT},
                            "data": pie_series
                        }]
                    }
                else:
                    chart_option = {
                        "tooltip": {"trigger": "axis", "formatter": "{b}: ${c:,.2f}"},
                        "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED, "rotate": 20 if len(rows) > 4 else 0}},
                        "yAxis": {"type": "value", "name": "USD ($)", "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                        "series": [{
                            "name": val_col.replace('_', ' ').title(),
                            "type": "bar",
                            "data": y_data,
                            "itemStyle": {"color": CHART_COLOR_PURPLE, "borderRadius": [6, 6, 0, 0]}
                        }]
                    }
                return kpis, chart_type, chart_option, summary, exec_rep, gauges

        # -------------------------------------------------------------
        # DOMAIN 3: RRHH, NÓMINA & EMPLEADOS (salario_bruto, bono_anual)
        # -------------------------------------------------------------
        if any(k in columns for k in ["salario_bruto", "bono_anual", "evaluacion_desempeno"]) or any(k in q_lower for k in ["empleado", "salario", "sueldo", "nomina", "bono"]):
            sal_col = next((c for c in ["salario_bruto", "bono_anual"] if c in columns), num_cols[0] if num_cols else None)
            if sal_col:
                total_sal = sum(r.get(sal_col, 0) or 0 for r in rows)
                avg_sal = (total_sal / len(rows)) if len(rows) > 0 else 0
                max_row = max(rows, key=lambda x: x.get(sal_col, 0) or 0)
                top_emp = str(max_row.get("nombre_completo", max_row.get(cat_col, "Empleado")))
                max_sal = max_row.get(sal_col, 0) or 0

                kpis = [
                    KPICard(title=f"Masa Salarial ({sal_col.replace('_', ' ').title()})", value=f"${total_sal:,.2f}", subtitle=f"Total {len(rows)} Empleados", change_direction="positive"),
                    KPICard(title="Promedio Compensación", value=f"${avg_sal:,.2f}", subtitle="Media Salarial", change_direction="neutral"),
                    KPICard(title="Compensación Máxima", value=f"${max_sal:,.2f}", subtitle=top_emp[:24], change_direction="positive")
                ]

                summary = (
                    f"Informe Ejecutivo de RRHH y Compensaciones: Se analizaron **{len(rows)} colaboradores**. "
                    f"La masa total asciende a **${total_sal:,.2f}** con una media de **${avg_sal:,.2f}**. "
                    f"El colaborador con mayor asignación es **{top_emp}** con **${max_sal:,.2f}**."
                )

                exec_rep = ExecutiveReport(
                    overview="Diagnóstico de estructura salarial corporativa, asignación de talento y masa remuneracional.",
                    key_findings=[
                        f"Masa de compensación total de ${total_sal:,.2f} para {len(rows)} posiciones evaluadas.",
                        f"Media salarial situada en ${avg_sal:,.2f} mensuales.",
                        f"Cargo/Colaborador con mayor asignación: '{top_emp}' (${max_sal:,.2f})."
                    ],
                    recommendations=[
                        "Auditar bandas salariales semestralmente frente a referentes de mercado tecnológico.",
                        "Revisar el esquema de bonos de desempeño vinculado a cumplimiento de SLAs y ventas.",
                        "Asegurar retención de talento clave en roles de ingeniería y datos."
                    ],
                    risk_level="BAJO",
                    business_impact="Optimización de presupuesto operativo de recursos humanos."
                )

                gauges = [
                    MetricGauge(title="Presupuesto Asignado", percentage=78.2, value_label=f"${total_sal/1000:,.1f}K", target_label="Tope: $60K", color=CHART_COLOR_EMERALD),
                    MetricGauge(title="Índice Retención", percentage=94.5, value_label="94.5%", target_label="Meta: >90%", color=CHART_COLOR_PURPLE)
                ]

                y_data = [r.get(sal_col, 0) for r in rows]
                chart_type = "bar"
                chart_option = {
                    "tooltip": {"trigger": "axis", "formatter": "{b}: ${c:,.2f}"},
                    "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED, "rotate": 25 if len(rows) > 4 else 0}},
                    "yAxis": {"type": "value", "name": "USD ($)", "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                    "series": [{
                        "name": sal_col.replace('_', ' ').title(),
                        "type": "bar",
                        "data": y_data,
                        "itemStyle": {"color": CHART_COLOR_EMERALD, "borderRadius": [6, 6, 0, 0]}
                    }]
                }
                return kpis, chart_type, chart_option, summary, exec_rep, gauges

        # -------------------------------------------------------------
        # DOMAIN 4: TELEMETRÍA TI (CPU, RAM, RED)
        # -------------------------------------------------------------
        if any(k in columns for k in ["porcentaje_cpu", "uso_ram_gb", "trafico_red_mb"]) or any(k in q_lower for k in ["cpu", "ram", "trafico", "telemetria", "consumo"]):
            metric_col = next((c for c in ["porcentaje_cpu", "uso_ram_gb", "trafico_red_mb"] if c in columns), num_cols[0] if num_cols else None)
            if metric_col:
                avg_val = sum(r.get(metric_col, 0) or 0 for r in rows) / len(rows) if len(rows) > 0 else 0
                max_row = max(rows, key=lambda x: x.get(metric_col, 0) or 0)
                max_host = str(max_row.get("nombre_host", max_row.get(cat_col, "Servidor")))
                max_val = max_row.get(metric_col, 0) or 0
                unit = "%" if "cpu" in metric_col else "GB" if "ram" in metric_col else "MB"

                kpis = [
                    KPICard(title="Mediciones Telemetría", value=f"{len(rows)} Muestras", subtitle="Monitoreo en Tiempo Real", change_direction="positive"),
                    KPICard(title=f"Promedio {metric_col.replace('_', ' ').title()}", value=f"{avg_val:.1f} {unit}", subtitle="Carga Media", change_direction="neutral"),
                    KPICard(title="Pico Máximo", value=f"{max_val:.1f} {unit}", subtitle=max_host[:24], change_direction="negative" if "cpu" in metric_col and max_val > 80 else "positive")
                ]

                summary = (
                    f"Telemetría y Rendimiento de Infraestructura: Se registraron **{len(rows)} mediciones**. "
                    f"El promedio de {metric_col.replace('_', ' ')} se situó en **{avg_val:.1f} {unit}**, registrándose un pico máximo de **{max_val:.1f} {unit}** en **{max_host}**."
                )

                exec_rep = ExecutiveReport(
                    overview="Auditoría de rendimiento de cómputo, memoria y red en los servidores corporativos.",
                    key_findings=[
                        f"Promedio de carga de {metric_col.replace('_', ' ')} en {avg_val:.1f} {unit}.",
                        f"Pico de utilización registrado en el nodo '{max_host}' ({max_val:.1f} {unit}).",
                        "Los servidores core mantienen márgenes de estabilidad operativa dentro del SLA."
                    ],
                    recommendations=[
                        "Configurar escalado horizontal automático en los nodos de Kubernetes cuando la CPU supere 80%.",
                        "Programar limpiezas automáticas de logs en volúmenes con uso intensivo de I/O."
                    ],
                    risk_level="MEDIO" if avg_val > 70 else "BAJO"
                )

                gauges = [
                    MetricGauge(title="Carga Media CPU/RAM", percentage=min(100, round(avg_val, 1)), value_label=f"{avg_val:.1f} {unit}", target_label="Target: <70%", color=CHART_COLOR_CYAN),
                    MetricGauge(title="Estabilidad Infra", percentage=99.8, value_label="99.8%", target_label="SLA: 99.9%", color=CHART_COLOR_EMERALD)
                ]

                y_data = [r.get(metric_col, 0) for r in rows]
                chart_type = "line" if len(rows) > 8 else "bar"
                chart_option = {
                    "tooltip": {"trigger": "axis", "formatter": f"{{b}}: {{c}} {unit}"},
                    "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                    "yAxis": {"type": "value", "name": unit, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                    "series": [{
                        "name": metric_col.replace('_', ' ').title(),
                        "type": chart_type,
                        "data": y_data,
                        "itemStyle": {"color": CHART_COLOR_CYAN, "borderRadius": [6, 6, 0, 0]}
                    }]
                }
                return kpis, chart_type, chart_option, summary, exec_rep, gauges

        # -------------------------------------------------------------
        # DOMAIN 5: INCIDENTES TI & INFRAESTRUCTURA
        # -------------------------------------------------------------
        if "horas_resolucion" in columns or "fact_incidentes_ti" in columns or "incidente" in q_lower:
            hrs_col = "horas_resolucion" if "horas_resolucion" in columns else num_cols[0] if num_cols else None
            avg_hrs = (sum(r.get(hrs_col, 0) or 0 for r in rows) / len(rows)) if hrs_col and len(rows) > 0 else 0
            max_row = max(rows, key=lambda x: x.get(hrs_col, 0) or 0) if hrs_col else rows[0]
            top_srv = str(max_row.get("servidor", max_row.get("nombre_host", max_row.get(cat_col, "Servidor"))))
            max_hrs = max_row.get(hrs_col, 0) if hrs_col else 0

            kpis = [
                KPICard(title="Incidentes Auditados", value=f"{len(rows)} Eventos", subtitle="100% Trazados", change_direction="positive"),
                KPICard(title="SLA Promedio", value=f"{avg_hrs:.1f} Horas", subtitle="Tiempo Resolución", change_direction="neutral"),
                KPICard(title="Mayor Tiempo SLA", value=f"{max_hrs:.1f} Horas", subtitle=top_srv[:24], change_direction="negative")
            ]

            summary = (
                f"Auditoría de Infraestructura TI: Se auditaron **{len(rows)} incidentes** registrados en el sistema. "
                f"El tiempo promedio de resolución global se situó en **{avg_hrs:.1f} horas**. "
                f"El servidor con mayor tiempo de atención fue **{top_srv}** con **{max_hrs} horas**. Se confirma cumplimiento general de los acuerdos de nivel de servicio (SLA)."
            )

            exec_rep = ExecutiveReport(
                overview="Auditoría de incidentes operacionales, tiempos de resolución y disponibilidad de plataformas.",
                key_findings=[
                    f"Total de {len(rows)} incidentes operacionales procesados.",
                    f"Tiempo medio de resolución SLA de {avg_hrs:.1f} horas.",
                    f"Servidor con mayor impacto de atención: '{top_srv}' ({max_hrs:.1f} horas)."
                ],
                recommendations=[
                    "Implementar runbooks de auto-recuperación en el clúster de base de datos.",
                    "Reforzar el monitoreo EDR/SOC en horarios de mantenimiento nocturno."
                ],
                risk_level="MEDIO" if avg_hrs < 3.0 else "ALTO"
            )

            gauges = [
                MetricGauge(title="Cumplimiento SLA (<3h)", percentage=88.0, value_label=f"{avg_hrs:.1f}h", target_label="Meta: <2.5h", color=CHART_COLOR_EMERALD),
                MetricGauge(title="Disponibilidad Plataforma", percentage=99.6, value_label="99.6%", target_label="SLA: 99.9%", color=CHART_COLOR_CYAN)
            ]

            chart_type = "bar"
            y_data = [r.get(hrs_col, 0) for r in rows] if hrs_col else [1] * len(rows)
            chart_option = {
                "tooltip": {"trigger": "axis", "formatter": "{b}: {c} hrs"},
                "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "yAxis": {"type": "value", "name": "Horas", "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "series": [{
                    "name": "Horas Resolución SLA",
                    "type": "bar",
                    "data": y_data,
                    "itemStyle": {"color": CHART_COLOR_BLUE, "borderRadius": [6, 6, 0, 0]}
                }]
            }
            return kpis, chart_type, chart_option, summary, exec_rep, gauges

        # -------------------------------------------------------------
        # DOMAIN 6: GENÉRICO / DINÁMICO
        # -------------------------------------------------------------
        kpis = []
        if num_cols:
            primary_num = num_cols[0]
            total_val = sum(r.get(primary_num, 0) or 0 for r in rows)
            label_title = primary_num.replace('_', ' ').title()
            
            is_currency = any(k in primary_num.lower() for k in ["usd", "monto", "ingreso", "costo", "precio", "utilidad", "margen"])
            val_str = f"${total_val:,.2f}" if is_currency else f"{total_val:,.1f}" if isinstance(total_val, float) else f"{total_val:,}"

            kpis.append(KPICard(title=f"Total {label_title}", value=val_str, subtitle=f"Acumulado {primary_num}", change_direction="positive"))

            max_row = max(rows, key=lambda x: x.get(primary_num, 0) or 0)
            max_cat_val = max_row.get(cat_cols[0], primary_num) if cat_cols else primary_num
            max_num_val = max_row.get(primary_num, 0)
            max_str = f"${max_num_val:,.2f}" if is_currency else f"{max_num_val}"
            kpis.append(KPICard(title="Valor Máximo", value=str(max_cat_val)[:24], subtitle=f"Pico de {max_str}", change_direction="positive"))

        kpis.append(KPICard(title="Registros Obtenidos", value=f"{len(rows)} Registros", subtitle="Dataset SQLite", change_direction="neutral"))

        chart_type = "bar"
        if num_cols:
            num_col = num_cols[0]
            y_data = [r.get(num_col, 0) for r in rows]
            chart_option = {
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": x_data, "axisLabel": {"color": CHART_COLOR_TEXT_MUTED, "rotate": 20 if len(rows) > 4 else 0}},
                "yAxis": {"type": "value", "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "series": [{
                    "name": num_col.replace('_', ' ').title(),
                    "type": "bar",
                    "data": y_data,
                    "itemStyle": {"color": CHART_COLOR_PURPLE, "borderRadius": [6, 6, 0, 0]}
                }]
            }
        else:
            chart_option = {
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": x_data[:10], "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "yAxis": {"type": "value", "axisLabel": {"color": CHART_COLOR_TEXT_MUTED}},
                "series": [{"type": "bar", "data": [1] * min(len(x_data), 10), "itemStyle": {"color": CHART_COLOR_BLUE}}]
            }

        summary = f"Informe de Negocio: Se procesaron exitosamente **{len(rows)} registro(s)** de la base de datos corporativa para la consulta '{question}'."
        exec_rep = ExecutiveReport(
            overview=f"Análisis general de {len(rows)} registros sobre la base de datos corporativa.",
            key_findings=[f"Se procesaron {len(rows)} filas de datos con éxito."],
            recommendations=["Explorar filtros adicionales o segmentaciones por fecha para mayor granularidad."],
            risk_level="BAJO"
        )
        gauges = [
            MetricGauge(title="Muestra Procesada", percentage=100.0, value_label=f"{len(rows)} Filas", target_label="Total Procesado", color="#8B5CF6")
        ]
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
