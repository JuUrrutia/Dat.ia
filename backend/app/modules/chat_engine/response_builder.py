from typing import List, Dict, Any, Set, Optional
from app.modules.chat_engine.schemas import (
    QueryResponse, KPICard, TraceabilityAudit, PresentationHints
)

# (valor, subtitulo) del KPI de "Estado de las conexiones" segun el diagnostico.
# Fuera del metodo porque es una tabla de 3 entradas, no logica: leerla pegada al
# return es mas dificil que leerla aqui.
_VISIBILITY_KPI = {
    "no_active_connection": ("SIN CONEXIÓN ACTIVA", "Ninguna base encendida"),
    "no_connections_registered": ("SIN CONEXIÓN REGISTRADA", "No hay ninguna base dada de alta"),
    "unknown": ("DESCONOCIDO", "No se pudo comprobar"),
}

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
    def build_visibility_diagnostic_response(
        cls,
        question: str,
        user_role: str,
        state: str,  # "no_active_connection" | "unknown"
        activate_connection: Optional[Dict[str, Any]] = None
    ) -> QueryResponse:
        """
        "No hay tablas" tiene dos causas que el usuario distingue distinto y hoy
        son el mismo texto: que nadie haya encendido una base, o que su rol no
        tenga tablas en la matriz RBAC. Esta respuesta solo cubre la PRIMERA
        (y el caso `unknown`, que es el tercero: no se pudo comprobar), porque
        la segunda ya la construye `build_rbac_denied_response`.

        `activate_connection` llega `None` para todo perfil que no sea admin: la
        accion es una escritura que `get_current_admin` rechazaria igual, y
        ofrecerla seria una promesa que el backend no cumple.
        """
        if state == "no_active_connection":
            reason = (
                "No hay ninguna conexión de datos activa: ningún administrador ha "
                "activado una base, así que no hay tablas que consultar."
            )
            if activate_connection:
                action_text = (
                    f"\n\n**Podés resolverlo vos mismo:** la conexión "
                    f"'{activate_connection['connection_name']}' está dada de baja. "
                    "Activándola, el chat vuelve a tener tablas para consultar."
                )
            else:
                action_text = (
                    "\n\nEncender una base es una tarea de administración: pedile a un "
                    "administrador que active una conexión desde el panel de conectores."
                )
            conversational = (
                "🔌 **No hay ninguna conexión de datos activa**\n\n"
                "Ningún administrador ha activado una base de datos en DATIA. "
                "Por eso el chat no tiene nada que mostrar: **no es que la consulta "
                "no tenga resultados, es que no hay ninguna fuente de datos encendida**."
                f"{action_text}"
            )
            status = "SIN_CONEXION_ACTIVA"
            sql_note = "-- CONSULTA NO EJECUTADA: NO HAY NINGUNA CONEXIÓN ACTIVA"
            grounding = "No se ejecutó ninguna consulta: no hay ninguna conexión activa"
        elif state == "no_connections_registered":
            # Ni siquiera hay conectores dados de alta. No es lo mismo que "nadie
            # encendio uno": la accion que falta es CREAR la base, no activar un
            # interruptor que no existe. Decir lo otro manda al admin a buscar algo
            # inexistente.
            conversational = (
                "🗄️ **No hay ninguna base de datos registrada**\n\n"
                "DATIA no tiene ninguna conexión dada de alta todavía, así que no hay "
                "nada que consultar. No es que la consulta no tenga resultados: es que "
                "**aún no se ha conectado ninguna fuente de datos**."
                "\n\nUn administrador tiene que registrar una conexión en el panel de "
                "conectores antes de que el chat pueda responder algo."
            )
            reason = (
                "No hay ninguna conexión de datos registrada: un administrador debe "
                "dar de alta una base en el panel de conectores."
            )
            status = "SIN_CONEXION_REGISTRADA"
            sql_note = "-- CONSULTA NO EJECUTADA: NO HAY NINGUNA CONEXIÓN REGISTRADA"
            grounding = "No se ejecutó ninguna consulta: no hay ninguna conexión registrada"
        else:
            # `unknown`: se dice que NO SE PUDO COMPROBAR. Afirmar "no hay
            # conexiones" sin haberlo comprobado seria exactamente el bug que
            # esta respuesta viene a cerrar, y decir solo "tu rol no tiene
            # tablas" esconderia una causa que nadie midio. Lo que si esta
            # verificado es que este perfil no tiene tablas visibles.
            reason = (
                "No se pudo verificar si hay alguna conexión de datos activa, y tu "
                f"perfil '{user_role}' no tiene tablas visibles en esta conexión. "
                "Un administrador debe activar una base de datos y comprobar la "
                "asignación de tablas en la matriz RBAC."
            )
            conversational = (
                "❔ **No se pudo determinar por qué no hay datos**\n\n"
                f"{reason}"
            )
            status = "DIAGNOSTICO_DESCONOCIDO"
            sql_note = "-- CONSULTA NO EJECUTADA: ESTADO DE LAS CONEXIONES DESCONOCIDO"
            grounding = "No se ejecutó ninguna consulta: no se pudo verificar el estado de las conexiones"

        return QueryResponse(
            question=question,
            summary_text=reason,
            kpis=[
                KPICard(
                    title="Estado de las conexiones",
                    value=_VISIBILITY_KPI[state][0],
                    subtitle=_VISIBILITY_KPI[state][1],
                    change_direction="negative"
                )
            ],
            chart_type="none",
            chart_option={"series": []},
            data_columns=[],
            data_rows=[],
            response_type="conversational",
            conversational_response=conversational,
            grounding_info=grounding,
            # Clave discriminante: la UI pinta el botón de activar con esto, sin
            # leer el texto. `None` (desconocido) no ofrece ninguna acción.
            no_active_connection=True if state == "no_active_connection" else None,
            activate_connection_action=activate_connection,
            presentation_hints=PresentationHints(
                show_executive_report=False,
                show_kpis=True,
                show_chart=False,
                preferred_view="assistant",
                summary_style="conversational"
            ),
            traceability=TraceabilityAudit(
                sql_executed=sql_note,
                execution_time_ms=0,
                rows_returned=0,
                validation_status=status,
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

