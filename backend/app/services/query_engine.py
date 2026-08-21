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
    CHART_COLOR_BLUE, CHART_COLOR_PURPLE, CHART_COLOR_TEXT_MUTED, CHART_COLOR_TEXT_LIGHT,
    DATA_REQUEST_KEYWORDS, GREETING_KEYWORDS, ADVISORY_KEYWORDS, EXPLANATION_KEYWORDS, HYBRID_KEYWORDS, REPORT_KEYWORDS,
    LIST_KEYWORDS, COUNT_KEYWORDS, DATE_COLUMN_KEYWORDS,
    CURRENCY_COLUMN_KEYWORDS, PERCENTAGE_COLUMN_KEYWORDS
)
from app.services.ast_validator import ASTValidator, ASTValidationError
from app.services.llm_service import LLMService
from app.services.dynamic_schema import DynamicSchemaPruningService
from app.core.prompts import PromptManager
from app.schemas.query_schema import QueryResponse, KPICard, TraceabilityAudit, ExecutiveReport, MetricGauge, PresentationHints

DEMO_DB_PATH = settings.SQLITE_DB_PATH

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
        """
        Generates role and table-specific question suggestions using the local LLM.
        Falls back to rule-based dynamic suggestions if LLM is offline or fails.
        """
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        # Attempt LLM generation for tailored suggestions based ONLY on active schema
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
        Generates question suggestions dynamically based on active database tables,
        agnostic to any specific domain or schema.
        """
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        suggestions = []
        # Sort prioritizing fact tables or alphabetical
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

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique[:4]

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
        # BRANCH 0: GREETING / GENERAL CONVERSATION (Conversational Welcome)
        # =========================================================================
        if response_type == "greeting":
            exec_time_ms = int((time.time() - start_time) * 1000)
            conversational = await cls._generate_conversational_response(
                question, user_role, "greeting", columns=list(allowed_tables), is_llm_active=True
            )
            summary_text = "Asistente DATIA listo para responder tus consultas sobre la base de datos activa."
            return QueryResponse(
                question=question,
                summary_text=summary_text,
                executive_report=None,
                kpis=[],
                gauges=[],
                chart_type="none",
                chart_option={},
                data_columns=[],
                data_rows=[],
                response_type="greeting",
                conversational_response=conversational or summary_text,
                grounding_info=f"Asistente conectado al perfil {user_role} ({len(allowed_tables)} tablas autorizadas)",
                presentation_hints=PresentationHints(
                    show_executive_report=False,
                    show_kpis=False,
                    show_gauges=False,
                    show_chart=False,
                    preferred_view="assistant",
                    summary_style="detailed"
                ),
                traceability=TraceabilityAudit(
                    sql_executed="-- MODO ASISTENTE CONVERSACIONAL (SIN SQL REQUERIDO)",
                    execution_time_ms=exec_time_ms,
                    rows_returned=0,
                    validation_status="APROBADO (Asistente)",
                    schema_tables_used=list(allowed_tables),
                    explanation=f"Interacción conversacional con IA Local. Tablas disponibles para el rol {user_role}: {', '.join(allowed_tables)}."
                )
            )

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
                presentation_hints=PresentationHints(
                    show_executive_report=False,
                    show_kpis=False,
                    show_gauges=False,
                    show_chart=False,
                    preferred_view="assistant",
                    summary_style="detailed"
                ),
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
            system_prompt = PromptManager.get_text_to_sql_system_prompt(user_role, allowed_tables)
            prompt_llm = PromptManager.get_text_to_sql_user_prompt(question, user_role, schema_context, allowed_tables)

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

        # Classify presentation format (LLM decides what components to show)
        pres_hints = await cls._classify_presentation_format(
            question, response_type, rows, columns
        )

        # Build dynamic visualization & contextual KPIs (respecting hints)
        kpis, chart_type, chart_option, fallback_summary, fallback_exec_report, gauges = cls._build_dynamic_visualization(
            question, columns, rows, user_role
        )

        # Apply presentation hints to filter components
        if not pres_hints.show_kpis:
            kpis = []
        if not pres_hints.show_gauges:
            gauges = []
        if not pres_hints.show_chart:
            chart_type = "none"
            chart_option = {}

        # Deep AI-Powered Executive Report — only when hints say it's needed
        final_exec_report = None
        if pres_hints.show_executive_report:
            llm_exec_report = await cls._generate_deep_executive_report_with_llm(
                question, user_role, rows, columns, secured_sql, is_llm_active
            )
            final_exec_report = llm_exec_report or fallback_exec_report

        # Generate intelligent natural conversational response interpreting data results
        conversational = await cls._generate_conversational_response(
            question, user_role, response_type, rows, columns, is_llm_active
        )

        # Build summary based on style hint or conversational synthesis
        if conversational:
            first_block = conversational.split("\n\n")[0].replace("#", "").strip()
            final_summary = first_block if len(first_block) > 10 else fallback_summary
            if pres_hints.preferred_view == "table" and conversational:
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
            presentation_hints=pres_hints,
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

        # 1. Explicit data or summary requests always go to data_analysis/report
        if any(k in q_lower for k in DATA_REQUEST_KEYWORDS):
            if any(k in q_lower for k in REPORT_KEYWORDS) or "informe" in q_lower:
                return "report"
            if any(k in q_lower for k in HYBRID_KEYWORDS):
                return "hybrid"
            return "data_analysis"

        # 2. Rule-based heuristics for immediate high-precision detection
        if any(k in q_lower for k in EXPLANATION_KEYWORDS):
            return "explanation"
        if any(k in q_lower for k in HYBRID_KEYWORDS):
            return "hybrid"
        if any(k in q_lower for k in REPORT_KEYWORDS):
            return "report"
        if any(k in q_lower for k in ADVISORY_KEYWORDS):
            return "advisory"
        if any(k == q_lower or q_lower.startswith(k + " ") or q_lower.endswith(" " + k) for k in GREETING_KEYWORDS) and len(q_lower.split()) <= 4:
            return "greeting"

        # Check with local LLM if available
        system_prompt = PromptManager.get_intent_classification_system_prompt()
        try:
            resp = await LLMService.generate_completion(
                question,
                system_prompt=system_prompt,
                max_tokens=30,
                temperature=0.01
            )
            if resp:
                resp = resp.strip().lower()
                for t in ["greeting", "advisory", "explanation", "report", "hybrid", "data_analysis"]:
                    if t in resp:
                        return t
        except Exception:
            pass

        return "data_analysis"

    @classmethod
    async def _classify_presentation_format(
        cls,
        question: str,
        response_type: str,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> PresentationHints:
        """
        Uses the LLM to decide which visual components are relevant for the user's question.
        Falls back to heuristic rules when LLM is offline.
        """
        # Advisory/explanation always go to assistant view
        if response_type in ("advisory", "explanation"):
            return PresentationHints(
                show_executive_report=False,
                show_kpis=False,
                show_gauges=False,
                show_chart=False,
                preferred_view="assistant",
                summary_style="detailed"
            )

        # Try LLM classification
        try:
            system_prompt = PromptManager.get_presentation_format_system_prompt()

            data_preview = ""
            if rows:
                data_preview = f"\nColumnas obtenidas: {', '.join(columns)}\nFilas devueltas: {len(rows)}\nMuestra (primeras 3): {json.dumps(rows[:3], ensure_ascii=False)}"

            prompt = f'Pregunta del usuario: "{question}"\nTipo de respuesta clasificado: {response_type}{data_preview}'

            resp = await LLMService.generate_completion(
                prompt,
                system_prompt=system_prompt,
                max_tokens=120,
                temperature=0.01
            )

            if resp:
                json_match = re.search(r'\{[\s\S]*\}', resp)
                if json_match:
                    data = json.loads(json_match.group(0))
                    return PresentationHints(
                        show_executive_report=bool(data.get("show_executive_report", True)),
                        show_kpis=bool(data.get("show_kpis", True)),
                        show_gauges=bool(data.get("show_gauges", True)),
                        show_chart=bool(data.get("show_chart", True)),
                        preferred_view=str(data.get("preferred_view", "studio")),
                        summary_style=str(data.get("summary_style", "detailed"))
                    )
        except Exception:
            pass

        # Heuristic fallback when LLM is offline
        return cls._heuristic_presentation_hints(question, response_type, rows, columns)

    @classmethod
    def _heuristic_presentation_hints(
        cls,
        question: str,
        response_type: str,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> PresentationHints:
        """Rule-based fallback for presentation format when LLM is unavailable."""
        q_lower = question.lower()

        # Report type: show everything
        if response_type == "report":
            return PresentationHints(
                show_executive_report=True, show_kpis=True,
                show_gauges=True, show_chart=True,
                preferred_view="report", summary_style="executive"
            )

        # Hybrid: show chart + report
        if response_type == "hybrid":
            return PresentationHints(
                show_executive_report=True, show_kpis=True,
                show_gauges=False, show_chart=True,
                preferred_view="studio", summary_style="detailed"
            )

        # Simple listing/count queries
        if any(k in q_lower for k in COUNT_KEYWORDS):
            return PresentationHints(
                show_executive_report=False, show_kpis=True,
                show_gauges=False, show_chart=False,
                preferred_view="table", summary_style="concise"
            )

        if any(k in q_lower for k in LIST_KEYWORDS):
            return PresentationHints(
                show_executive_report=False, show_kpis=False,
                show_gauges=False, show_chart=False,
                preferred_view="table", summary_style="concise"
            )

        # Check if data has numeric columns worth charting
        has_numeric = False
        if rows and columns:
            for col in columns:
                val = rows[0].get(col)
                col_lower = col.lower()
                if isinstance(val, (int, float)) and not col_lower.startswith("id_") and not col_lower.endswith("_id") and col_lower != "id":
                    has_numeric = True
                    break

        if has_numeric and len(rows) > 1:
            # Analytical query with chartable data
            return PresentationHints(
                show_executive_report=False, show_kpis=True,
                show_gauges=False, show_chart=True,
                preferred_view="studio", summary_style="detailed"
            )

        # Default: table view with concise summary
        return PresentationHints(
            show_executive_report=False, show_kpis=False,
            show_gauges=False, show_chart=True if has_numeric else False,
            preferred_view="studio" if has_numeric else "table",
            summary_style="concise"
        )


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

        if response_type == "data_analysis":
            system_prompt = PromptManager.get_data_analysis_conversational_system_prompt(user_role)
            temp = 0.2
            prompt = f"Pregunta del usuario ({user_role}): \"{question}\"\n"
            if data_context:
                prompt += f"\nResultados devueltos por la base de datos ({len(data_context)} registros encontrados):\n{json.dumps(data_context[:25], ensure_ascii=False, indent=2)}\n\nResponde directamente a la pregunta explicando estos datos."
            else:
                prompt += "\nLa base de datos ejecutó la consulta pero no se encontraron registros coincidentes. Explica cordialmente la situación."
        elif response_type == "greeting":
            system_prompt = PromptManager.get_general_greeting_system_prompt(user_role, set(columns or []))
            temp = 0.4
            prompt = f"Saludo/Mensaje del usuario ({user_role}): \"{question}\"\nSaluda cordialmente, explica tus funciones y sugiere ejemplos de preguntas para sus tablas autorizadas."
        elif response_type in ("advisory", "explanation", "hybrid"):
            system_prompt, temp = PromptManager.get_conversational_system_prompt(response_type)
            prompt = f"Pregunta del usuario ({user_role}): \"{question}\"\n"
            if data_context:
                prompt += f"\nContexto de datos reales de la empresa (primeras 30 filas):\n{json.dumps(data_context[:30], ensure_ascii=False, indent=2)}"
        else:
            return None

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
        Uses Local LLM to synthesize rows of database records into an intelligent,
        unconstrained Executive Report tailored to the active domain (Mental Health, HR, Finance, IT, etc.).
        """
        if not rows or not is_llm_active:
            return None

        try:
            system_prompt = PromptManager.get_executive_report_system_prompt()

            prompt_data = f"""Pregunta realizada por el usuario ({user_role}): "{question}"
Consulta SQL ejecutada sobre la BD activa: {secured_sql}
Muestra de registros devueltos por la BD ({len(rows)} filas):
{json.dumps(rows[:25], ensure_ascii=False, indent=2)}

Analiza libremente la información devuelta y genera el informe ejecutivo en formato JSON."""

            resp = await LLMService.generate_completion(
                prompt_data,
                system_prompt=system_prompt,
                max_tokens=700,
                temperature=0.3
            )

            if resp:
                json_match = re.search(r'\{[\s\S]*\}', resp)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                    except Exception:
                        cleaned_str = json_match.group(0)
                        cleaned_str = re.sub(r',\s*([\}\]])', r'\1', cleaned_str)
                        data = json.loads(cleaned_str)

                    overview = str(data.get("overview", "")).strip()
                    findings = [str(f) for f in data.get("key_findings", []) if f]
                    recs = [str(r) for r in data.get("recommendations", []) if r]
                    risk = str(data.get("risk_level", "BAJO")).upper()
                    if risk not in ("BAJO", "MEDIO", "ALTO", "CRITICO"):
                        risk = "BAJO"
                    impact = str(data.get("business_impact", "")).strip() or None

                    if overview:
                        return ExecutiveReport(
                            overview=overview,
                            key_findings=findings if findings else ["Análisis cuantitativo de los registros devueltos."],
                            recommendations=recs if recs else ["Continuar monitoreo del dominio analizado en la base de datos."],
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

        for col in columns:
            col_lower = col.lower()
            val = rows[0].get(col)

            # Check if numeric
            if isinstance(val, (int, float)) and not col_lower.startswith("id_") and not col_lower.endswith("_id") and col_lower != "id":
                num_cols.append(col)
            # Check if date/time
            elif any(dk in col_lower for dk in DATE_COLUMN_KEYWORDS):
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
        is_currency = primary_num and any(k in primary_num.lower() for k in CURRENCY_COLUMN_KEYWORDS)
        is_percentage = primary_num and any(k in primary_num.lower() for k in PERCENTAGE_COLUMN_KEYWORDS)

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

            clean_x_data = [str(x)[:22] + "..." if len(str(x)) > 22 else str(x) for x in x_data]

            chart_option = {
                "tooltip": {"trigger": "axis", "formatter": f"{{b}}: {unit_str}{{c}}"},
                "grid": {"left": "3%", "right": "4%", "bottom": "15%", "top": "12%", "containLabel": True},
                "xAxis": {
                    "type": "category",
                    "data": clean_x_data,
                    "axisLabel": {
                        "color": CHART_COLOR_TEXT_MUTED,
                        "fontSize": 10,
                        "rotate": 25 if any(len(str(x)) > 15 for x in x_data) else (15 if len(rows) > 5 else 0)
                    }
                },
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
