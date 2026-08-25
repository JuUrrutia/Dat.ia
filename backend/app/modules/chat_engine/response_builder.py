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
            gauges=[],
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
        return QueryResponse(
            question=question,
            summary_text=reason,
            kpis=[
                KPICard(title="Estado RBAC", value="DENEGADO", subtitle="Acceso Reprobado", change_direction="negative"),
                KPICard(title="Motivo", value="Falta Permiso", subtitle="Seguridad", change_direction="neutral")
            ],
            chart_type="bar",
            chart_option={"series": []},
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

    @classmethod
    def build_greeting_response(
        cls,
        question: str,
        user_role: str,
        allowed_tables: Set[str],
        conversational: Optional[str] = None
    ) -> QueryResponse:
        summary_text = "Asistente DATIA listo para responder tus consultas sobre la base de datos activa."
        return QueryResponse(
            question=question,
            summary_text=summary_text,
            executive_report=None,
            kpis=[],
            gauges=[],
            chart_type="none",
            chart_option={"series": []},
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
    def build_conversational_response(
        cls,
        question: str,
        user_role: str,
        secured_sql: str,
        rows: List[Dict[str, Any]],
        meta: Dict[str, Any],
        conversational: str,
        exec_time_ms: int,
        allowed_tables: Set[str]
    ) -> QueryResponse:
        return QueryResponse(
            question=question,
            summary_text=conversational.split("\n\n")[0].replace("#", "").strip(),
            executive_report=None,
            kpis=[],
            gauges=[],
            chart_type="none",
            chart_option={"series": []},
            data_columns=list(rows[0].keys()) if rows else [],
            data_rows=rows,
            response_type="conversational",
            conversational_response=conversational,
            grounding_info=f"Datos contextuales consultados de {', '.join(meta.get('tables_used', []))} ({len(rows)} registros evaluados)",
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
        gauges: List[Any],
        chart_type: str,
        chart_option: Dict[str, Any],
        final_summary: str,
        final_exec_report: Optional[Any],
        conversational: Optional[str]
    ) -> QueryResponse:
        grounding_info = f"Consulta ejecutada sobre {len(rows)} registros ({', '.join(meta.get('tables_used', []))})"
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
                validation_status=validation_label,
                schema_tables_used=list(meta.get("tables_used", list(allowed_tables))),
                explanation=f"Consulta generada y validada con IA Local ({'Qwen2.5-Coder' if is_llm_active else 'Modo Determinístico'}). Tablas autorizadas: {', '.join(allowed_tables)}."
            )
        )
