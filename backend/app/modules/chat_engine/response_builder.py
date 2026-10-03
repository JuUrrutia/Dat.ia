from typing import List, Dict, Any, Set, Optional
from app.modules.chat_engine.schemas import (
    QueryResponse, KPICard, TraceabilityAudit, PresentationHints
)

class ResponseBuilder:
    """
    Encapsulates assembling and formatting of QueryResponse objects for all intents
    and contingency states.
    """

    @classmethod
    def build_llm_offline_response(cls, question: str, exec_time_ms: int = 0) -> QueryResponse:
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
            chart_type="none",
            chart_option={"series": []},
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
    def build_rbac_denied_response(cls, question: str, reason: str) -> QueryResponse:
        conversational_denial = (
            f"🚫 **Acceso Restringido por Gobernanza de Datos (RBAC)**\n\n"
            f"{reason}\n\n"
            "> **Aviso de Seguridad:** Tu perfil actual no dispone de autorización en la matriz de acceso para consultar "
            "o manipular este dominio de datos corporativos. Si necesitas consultar estas métricas para tus funciones, "
            "solicita la actualización de permisos a un **Administrador de Plataforma**."
        )
        return QueryResponse(
            question=question,
            summary_text=reason,
            kpis=[
                KPICard(title="Estado RBAC", value="DENEGADO", subtitle="Acceso Bloqueado", change_direction="negative"),
                KPICard(title="Gobernanza", value="Restringido", subtitle="Seguridad Activa", change_direction="neutral")
            ],
            chart_type="none",
            chart_option={"series": []},
            data_columns=["mensaje_seguridad"],
            data_rows=[{"mensaje_seguridad": reason}],
            response_type="conversational",
            conversational_response=conversational_denial,
            grounding_info="Consulta bloqueada por el motor de validación de seguridad RBAC",
            presentation_hints=PresentationHints(
                show_executive_report=False,
                show_kpis=False,
                show_chart=False,
                preferred_view="assistant",
                summary_style="conversational"
            ),
            traceability=TraceabilityAudit(
                sql_executed="-- CONSULTA BLOQUEADA POR GOBERNANZA RBAC",
                execution_time_ms=0,
                rows_returned=0,
                validation_status="RECHAZADO_RBAC",
                schema_tables_used=[],
                explanation=reason
            )
        )

    @classmethod
    def build_execution_error_response(
        cls,
        question: str,
        error_message: str,
        exec_time_ms: int = 0
    ) -> QueryResponse:
        conversational_err = (
            f"⚠️ **Error en la ejecución de la consulta**\n\n"
            f"El motor de base de datos no pudo completar la consulta debido a un error técnico:\n"
            f"> `{error_message}`\n\n"
            "Puedes reformular tu pregunta o verificar que los campos consultados existan en el modelo."
        )
        return QueryResponse(
            question=question,
            summary_text=f"Error al ejecutar consulta: {error_message}",
            kpis=[],
            chart_type="none",
            chart_option={"series": []},
            data_columns=["error"],
            data_rows=[{"error": error_message}],
            response_type="error",
            conversational_response=conversational_err,
            grounding_info="Error técnico durante la ejecución relacional",
            presentation_hints=PresentationHints(
                show_executive_report=False,
                show_kpis=False,
                show_chart=False,
                preferred_view="assistant",
                summary_style="conversational"
            ),
            traceability=TraceabilityAudit(
                sql_executed="-- ERROR EN EJECUCIÓN",
                execution_time_ms=exec_time_ms,
                rows_returned=0,
                validation_status="ERROR_EJECUCION",
                schema_tables_used=[],
                explanation=error_message
            )
        )

    @classmethod
    def build_greeting_response(
        cls,
        question: str,
        user_role: str,
        allowed_tables: Set[str],
        conversational: Optional[str] = None,
        suggested_questions: Optional[List[str]] = None,
        clarification_options: Optional[List[str]] = None
    ) -> QueryResponse:
        summary_text = "Asistente DATIA listo para responder tus consultas sobre la base de datos activa."
        default_suggs = [
            f"¿Qué datos contiene la tabla {t}?" for t in sorted(list(allowed_tables))[:3]
        ] if allowed_tables else [
            "¿Cuáles son las ventas totales?",
            "¿Cuál es el resumen de clientes?",
            "¿Cuáles son los productos principales?"
        ]
        return QueryResponse(
            question=question,
            summary_text=summary_text,
            executive_report=None,
            kpis=[],
            chart_type="none",
            chart_option={"series": []},
            data_columns=[],
            data_rows=[],
            response_type="greeting",
            conversational_response=conversational or summary_text,
            grounding_info=f"Asistente conectado al perfil {user_role} ({len(allowed_tables)} tablas autorizadas)",
            suggested_questions=suggested_questions or default_suggs,
            clarification_options=clarification_options or [],
            presentation_hints=PresentationHints(
                show_executive_report=False,
                show_kpis=False,
                show_chart=False,
                preferred_view="assistant",
                summary_style="conversational"
            ),
            traceability=TraceabilityAudit(
                sql_executed="-- INTENCIÓN CONVERSACIONAL (SALUDO): NO REQUIERE CONSULTA SQL",
                execution_time_ms=0,
                rows_returned=0,
                validation_status="APROBADO_CONVERSACIONAL",
                schema_tables_used=list(allowed_tables),
                explanation=f"Interacción conversacional resuelta directamente. Perfil: {user_role}."
            )
        )

    @classmethod
    def build_out_of_scope_response(
        cls,
        question: str,
        user_role: str,
        allowed_tables: Set[str],
        conversational: Optional[str] = None,
        suggested_questions: Optional[List[str]] = None,
        clarification_options: Optional[List[str]] = None
    ) -> QueryResponse:
        tables_str = ", ".join(sorted(allowed_tables)) if allowed_tables else "tus fuentes autorizadas"
        default_fallback = (
            f"Como asistente de inteligencia y analítica de datos, mi propósito es ayudarte "
            f"a explorar, consultar y analizar la información corporativa de la organización.\n\n"
            f"Actualmente **no dispongo de funciones para generar imágenes, contenido multimedia o realizar tareas externas** ajenas al análisis de datos. "
            f"Sin embargo, puedo generar gráficos estadísticos interactivos (barras, líneas, áreas o tortas), resúmenes cuantitativos y KPIs estratégicos para tu perfil (**{user_role}**) "
            f"a partir de las tablas disponibles ({tables_str}).\n\n"
            f"💡 **¿Qué análisis podemos realizar juntos?**\n"
            f"- Comparar volúmenes, totales o promedios sobre tus datos autorizados.\n"
            f"- Diseñar gráficos interactivos de tendencias o distribuciones por categoría.\n"
            f"- Analizar registros destacados para fundamentar decisiones comerciales o financieras."
        )
        final_conversational = conversational or default_fallback
        default_suggs = [
            f"¿Cuáles son las principales métricas en {t}?" for t in sorted(list(allowed_tables))[:3]
        ] if allowed_tables else [
            "¿Cuáles son las ventas acumuladas por categoría?",
            "¿Cuál es el resumen de clientes principales?",
            "¿Cuáles son los productos con mayor movimiento?"
        ]

        return QueryResponse(
            question=question,
            summary_text="Solicitud fuera de las funciones de analítica de datos corporativos de DATIA.",
            executive_report=None,
            kpis=[
                KPICard(
                    title="Alcance DATIA",
                    value="Analítica de Datos",
                    subtitle="Inteligencia Corporativa",
                    change_direction="neutral"
                ),
                KPICard(
                    title="Visualización",
                    value="Gráficos BI",
                    subtitle="Estadísticos e Interactivos",
                    change_direction="positive"
                )
            ],
            chart_type="none",
            chart_option={"series": []},
            data_columns=[],
            data_rows=[],
            response_type="out_of_scope",
            conversational_response=final_conversational,
            grounding_info=f"Asistente enfocado en analítica corporativa ({len(allowed_tables)} tablas disponibles)",
            suggested_questions=suggested_questions or default_suggs,
            clarification_options=clarification_options or [],
            presentation_hints=PresentationHints(
                show_executive_report=False,
                show_kpis=True,
                show_chart=False,
                preferred_view="assistant",
                summary_style="detailed"
            ),
            traceability=TraceabilityAudit(
                sql_executed="-- SOLICITUD FUERA DE ALCANCE: NO APLICA CONSULTA SQL DE BASE DE DATOS",
                execution_time_ms=0,
                rows_returned=0,
                validation_status="FUERA_DE_ALCANCE",
                schema_tables_used=list(allowed_tables),
                explanation=f"La solicitud '{question}' está fuera del alcance de analítica de datos y no requiere consulta a la base de datos corporativa."
            )
        )

    @classmethod
    def build_conversational_response(
        cls,
        question: str,
        user_role: str,
        secured_sql: str,
        rows: List[Dict[str, Any]],
        meta: Dict[str, Any],
        conversational: str,
        exec_time_ms: int,
        allowed_tables: Set[str],
        suggested_questions: Optional[List[str]] = None,
        clarification_options: Optional[List[str]] = None,
        anomalies_detected: Optional[List[Dict[str, Any]]] = None,
        sql_explanation: Optional[str] = None
    ) -> QueryResponse:
        return QueryResponse(
            question=question,
            summary_text=conversational.split("\n\n")[0].replace("#", "").strip(),
            executive_report=None,
            kpis=[],
            chart_type="none",
            chart_option={"series": []},
            data_columns=list(rows[0].keys()) if rows else [],
            data_rows=rows,
            response_type="conversational",
            conversational_response=conversational,
            grounding_info=f"Datos contextuales consultados de {', '.join(meta.get('tables_used', []))} ({len(rows)} registros evaluados)",
            suggested_questions=suggested_questions or [],
            clarification_options=clarification_options or [],
            anomalies_detected=anomalies_detected or [],
            sql_explanation=sql_explanation,
            presentation_hints=PresentationHints(
                show_executive_report=False,
                show_kpis=False,
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
                target_database=meta.get("target_database"),
                explanation=f"Respuesta de Asistente generada con IA Local. Datos de respaldo consultados de: {', '.join(meta.get('tables_used', []))}."
            )
        )

    @classmethod
    def build_analytics_response(
        cls,
        question: str,
        response_type: str,
        rows: List[Dict[str, Any]],
        columns: List[str],
        meta: Dict[str, Any],
        allowed_tables: Set[str],
        secured_sql: str,
        validation_label: str,
        exec_time_ms: int,
        is_llm_active: bool,
        pres_hints: PresentationHints,
        kpis: List[KPICard],
        chart_type: str,
        chart_option: Dict[str, Any],
        final_summary: str,
        final_exec_report: Optional[Any],
        conversational: Optional[str],
        thinking_process: Optional[str] = None,
        suggested_questions: Optional[List[str]] = None,
        clarification_options: Optional[List[str]] = None,
        anomalies_detected: Optional[List[Dict[str, Any]]] = None,
        sql_explanation: Optional[str] = None,
        nulls_detected: Optional[Dict[str, Any]] = None
    ) -> QueryResponse:
        grounding_info = f"Consulta ejecutada sobre {len(rows)} registros ({', '.join(meta.get('tables_used', []))})"
        return QueryResponse(
            question=question,
            summary_text=final_summary,
            executive_report=final_exec_report,
            kpis=kpis,
            chart_type=chart_type,
            chart_option=chart_option,
            data_columns=columns,
            data_rows=rows,
            response_type=response_type,
            conversational_response=conversational,
            grounding_info=grounding_info,
            presentation_hints=pres_hints,
            thinking_process=thinking_process,
            suggested_questions=suggested_questions or [],
            clarification_options=clarification_options or [],
            anomalies_detected=anomalies_detected or [],
            sql_explanation=sql_explanation,
            nulls_detected=nulls_detected,
            traceability=TraceabilityAudit(
                sql_executed=secured_sql,
                execution_time_ms=exec_time_ms,
                rows_returned=len(rows),
                validation_status=validation_label,
                schema_tables_used=list(meta.get("tables_used", list(allowed_tables))),
                target_database=meta.get("target_database"),
                explanation=f"Consulta generada y validada con IA Local ({'Qwen2.5-Coder' if is_llm_active else 'Modo Determinístico'}). Tablas autorizadas: {', '.join(allowed_tables)}."
            )
        )

