import json
import re
import unicodedata
from typing import List, Dict, Any, Optional, Set
from app.core.constants import (
    DATA_REQUEST_KEYWORDS, GREETING_KEYWORDS, ADVISORY_KEYWORDS, EXPLANATION_KEYWORDS,
    HYBRID_KEYWORDS, REPORT_KEYWORDS, LIST_KEYWORDS, COUNT_KEYWORDS,
    UNSUPPORTED_CAPABILITY_PATTERNS
)
from app.core.prompts import PromptManager
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.schemas import PresentationHints

# Palabras que convierten un mensaje en una PETICION real. Si aparecen, el mensaje
# no es "solo un saludo/agradecimiento" aunque empiece con "Hola" o "Gracias".
# Se comparan sin acentos (ver _strip_accents). Los verbos de otros intents
# (explica, define, significa) NO van aqui: ya se evalúan antes que el saludo.
_REQUEST_MARKERS = {
    "cuanto", "cuantos", "cuanta", "cuantas", "cual", "cuales",
    "donde", "quien", "quienes", "cuando",
    "dame", "muestrame", "mostrar", "muestra", "ver", "ves",
    "necesito", "quiero", "podrias", "genera", "generame", "hazme",
    "calcula", "analiza", "compara", "grafica", "grafico", "grafiquen",
}


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


class IntentClassifier:
    """
    Handles query intent classification, conversational responses, and dynamic presentation format hints.
    """

    @classmethod
    async def classify_intent(cls, question: str) -> str:
        q_lower = question.lower().strip()

        # 0. Detect unsupported out-of-scope capabilities (images, audio, video, web search, destructive DDL/DML, etc.)
        if any(re.search(pat, q_lower) for pat in UNSUPPORTED_CAPABILITY_PATTERNS):
            return "out_of_scope"

        if any(k in q_lower for k in EXPLANATION_KEYWORDS):
            return "explanation"
        if any(k in q_lower for k in HYBRID_KEYWORDS):
            return "hybrid"
        if any(k in q_lower for k in REPORT_KEYWORDS):
            return "report"
        if any(k in q_lower for k in ADVISORY_KEYWORDS):
            return "advisory"

        # Los saludos/agradecimientos se evalúan ANTES que las peticiones de datos:
        # "Gracias, ya tengo los datos" matchea DATA_REQUEST_KEYWORDS ("datos") y
        # disparaba el pipeline SQL completo (SQL + audit_logs + memoria) para un
        # mensaje que no pedía nada.
        if cls._is_pure_greeting(q_lower):
            return "greeting"

        if any(k in q_lower for k in DATA_REQUEST_KEYWORDS):
            if any(k in q_lower for k in REPORT_KEYWORDS) or "informe" in q_lower:
                return "report"
            if any(k in q_lower for k in HYBRID_KEYWORDS):
                return "hybrid"
            return "data_analysis"

        system_prompt = PromptManager.get_intent_classification_system_prompt()
        try:
            resp = await LLMService.generate_completion(
                question,
                system_prompt=system_prompt,
                max_tokens=30,
                temperature=0.01,
                # El prompt pide UNA palabra. `stop` corta en el primer salto de
                # linea en vez de dejar que el modelo siga emitiendo una frase
                # entera dentro del presupuesto de 30 tokens que no se leia.
                stop=["\n"],
            )
            if resp:
                resp = resp.strip().lower()
                for t in ["out_of_scope", "greeting", "advisory", "explanation", "report", "hybrid", "data_analysis"]:
                    if t in resp:
                        return t
        except Exception:
            pass

        return "data_analysis"

    @classmethod
    def _is_pure_greeting(cls, q_lower: str) -> bool:
        """
        True solo si el mensaje es cortesía/agradecimiento SIN ninguna petición.

        Match por token (no substring) para que "Gest-ti-ón" no matchee "ti" ni
        "top" matchee dentro de "estopa". Las palabras multifrase de
        GREETING_KEYWORDS ("buenos dias", "qué puedes hacer") sí se buscan como
        substring, que es la única forma de detectarlas.
        """
        flat = _strip_accents(q_lower)
        tokens = re.sub(r'[^\w]+', ' ', flat).split()
        if not tokens or len(tokens) > 8:
            return False
        if any(m in tokens for m in _REQUEST_MARKERS):
            return False
        return any(_strip_accents(k) in flat if " " in k else _strip_accents(k) in tokens for k in GREETING_KEYWORDS)

    @classmethod
    def detect_ambiguity_and_options(cls, question: str, allowed_tables: Optional[Set[str]] = None) -> List[str]:
        """
        Detects broad or underspecified queries (<= 3 words without metrics/timeframes)
        and offers disambiguation chips so the user can clarify in 1 click (Idea #5).
        """
        q = question.strip().lower()
        clean_words = [w for w in re.sub(r'[?¿!¡.,;:\-_]', ' ', q).split() if len(w) > 1]

        if len(clean_words) > 3:
            return []

        specific_qualifiers = {"cuanto", "cuantos", "total", "suma", "promedio", "maximo", "minimo", "top", "primeros", "ultimos", "entre", "desde", "hasta", "donde", "por que", "quien"}
        if any(w in specific_qualifiers for w in clean_words):
            return []

        q_joined = " ".join(clean_words)

        # Cada chip declara las tablas que necesita. Se filtran contra
        # allowed_tables para no sugerir consultas que el rol no puede ejecutar
        # (o que governance_guard después rechaza con un error RBAC).
        if any(w in q_joined for w in ["venta", "ingreso", "factur", "ventas"]):
            return cls._filter_options([
                ("¿Cuál es el total acumulado de ventas?", ("fact_ventas",)),
                ("¿Cuál es la evolución mensual de ventas?", ("fact_ventas",)),
                ("¿Cuáles son los 10 clientes con mayores compras?", ("fact_ventas", "dim_clientes")),
                ("¿Cuáles son los productos más vendidos?", ("fact_ventas", "dim_productos")),
            ], allowed_tables)

        if any(w in q_joined for w in ["client", "comprador", "usuario"]):
            return cls._filter_options([
                ("¿Cuántos clientes tenemos en total?", ("dim_clientes",)),
                ("¿Cuáles son los mejores clientes por volumen?", ("dim_clientes", "fact_ventas")),
                ("¿Quiénes son los clientes más recientes?", ("dim_clientes",)),
                ("¿Cuál es la distribución por sector o industria?", ("dim_clientes",)),
            ], allowed_tables)

        if any(w in q_joined for w in ["gasto", "costo", "egreso"]):
            return cls._filter_options([
                ("¿A cuánto asciende el gasto total?", ("fact_ingresos_costos",)),
                ("¿Cuál es el desglose de costos por categoría?", ("fact_ingresos_costos",)),
                ("¿Cuáles son los 5 mayores gastos registrados?", ("fact_ingresos_costos",)),
                ("¿Cómo varían los costos mes a mes?", ("fact_ingresos_costos",)),
            ], allowed_tables)

        if any(w in q_joined for w in ["emplead", "personal", "rrhh", "trabajador"]):
            # Sin chip de salario/remuneración: dim_empleados está autorizada para
            # roles no-HR, pero governance_guard bloquea el salario por COLUMNAS.
            return cls._filter_options([
                ("¿Cuántos empleados hay por departamento?", ("dim_empleados",)),
                ("¿Cuál es la distribución de empleados por cargo?", ("dim_empleados",)),
                ("¿Quiénes son las incorporaciones más recientes?", ("dim_empleados",)),
                ("¿Cuál es la distribución por antigüedad laboral?", ("dim_empleados",)),
            ], allowed_tables)

        if any(w in q_joined for w in ["producto", "stock", "inventario", "item"]):
            return cls._filter_options([
                ("¿Cuáles productos tienen menor inventario disponible?", ("dim_productos",)),
                ("¿Cuáles son los productos de mayor precio?", ("dim_productos",)),
                ("¿Cuántos productos activos tenemos por categoría?", ("dim_productos",)),
                ("¿Cuál es el valor total del inventario?", ("dim_productos",)),
            ], allowed_tables)

        if len(clean_words) <= 2 and clean_words:
            base_entity = clean_words[0].capitalize()
            return [
                f"¿Cuál es el resumen general de {base_entity}?",
                f"¿Cuáles son los 10 registros principales en {base_entity}?",
                f"¿Cuál es el total acumulado en {base_entity}?",
                f"¿Cómo se distribuyen los registros de {base_entity} por categoría?"
            ]

        return []

    @staticmethod
    def _filter_options(
        options: List[tuple],
        allowed_tables: Optional[Set[str]]
    ) -> List[str]:
        """
        Filtra los chips por las tablas que el rol realmente tiene autorizadas.

        Sin allowed_tables (None / vacío) no se puede filtrar: se devuelve el set
        completo, que es el comportamiento previo de los callers.
        """
        if not allowed_tables:
            return [chip for chip, _tables in options]
        return [chip for chip, tables in options if set(tables) <= allowed_tables]


    @classmethod
    def heuristic_presentation_hints(
        cls,
        question: str,
        response_type: str,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> PresentationHints:
        q_lower = question.lower()

        is_report_requested = any(k in q_lower for k in ("informe", "reporte", "diagnóstico", "evaluación ejecutiva"))

        if response_type == "report" or is_report_requested:
            return PresentationHints(
                show_executive_report=True, show_kpis=True,
                show_chart=True,
                preferred_view="report", summary_style="executive"
            )

        if response_type == "hybrid":
            return PresentationHints(
                show_executive_report=False, show_kpis=True,
                show_chart=True,
                preferred_view="assistant", summary_style="detailed"
            )

        if any(k in q_lower for k in COUNT_KEYWORDS):
            return PresentationHints(
                show_executive_report=False, show_kpis=True,
                show_chart=False,
                preferred_view="table", summary_style="concise"
            )

        if any(k in q_lower for k in LIST_KEYWORDS):
            return PresentationHints(
                show_executive_report=False, show_kpis=False,
                show_chart=False,
                preferred_view="table", summary_style="concise"
            )

        has_numeric = False
        if rows and columns:
            for col in columns:
                val = rows[0].get(col)
                col_lower = col.lower()
                if isinstance(val, (int, float)) and not col_lower.startswith("id_") and not col_lower.endswith("_id") and col_lower != "id":
                    has_numeric = True
                    break

        if has_numeric and len(rows) > 1:
            return PresentationHints(
                show_executive_report=False, show_kpis=True,
                show_chart=True,
                preferred_view="assistant", summary_style="detailed"
            )

        return PresentationHints(
            show_executive_report=False, show_kpis=False,
            show_chart=True if has_numeric else False,
            preferred_view="assistant" if has_numeric else "table",
            summary_style="concise"
        )

    @classmethod
    async def generate_conversational_response(
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
                prompt += f"\nResultados obtenidos por DATIA desde la base de datos corporativa ({len(data_context)} registros encontrados):\n{json.dumps(data_context[:25], ensure_ascii=False, indent=2, default=str)}\n\nExplica estos datos obtenidos de la BD al usuario en respuesta a su pregunta."
            else:
                prompt += "\nLa base de datos fue consultada pero no se encontraron registros coincidentes. Explica cordialmente la situación al usuario."
        elif response_type == "greeting":
            system_prompt = PromptManager.get_general_greeting_system_prompt(user_role, set(columns or []))
            temp = 0.4
            prompt = f"Saludo/Mensaje del usuario ({user_role}): \"{question}\"\nSaluda cordialmente, explica tus funciones y sugiere ejemplos de preguntas para sus tablas autorizadas."
        elif response_type == "out_of_scope":
            system_prompt = PromptManager.get_out_of_scope_system_prompt(user_role, set(columns or []))
            temp = 0.25
            prompt = (
                f"Solicitud del usuario ({user_role}): \"{question}\"\n\n"
                "Responde de manera empática, conversacional y profesional explicando tus capacidades y limitaciones frente a esta solicitud específica, "
                "destacando lo que sí puedes hacer para su rol y proponiendo 2 o 3 alternativas analíticas o de visualización estadística basadas en sus datos corporativos."
            )
        elif response_type in ("advisory", "explanation", "hybrid"):
            system_prompt = PromptManager.get_conversational_system_prompt(response_type)
            temp = 0.2
            prompt = f"Pregunta del usuario ({user_role}): \"{question}\"\n"
            if data_context:
                prompt += f"\nContexto de datos reales leídos de la base de datos ({len(data_context)} registros encontrados):\n{json.dumps(data_context[:30], ensure_ascii=False, indent=2, default=str)}\n\nAnaliza e interpreta estos datos de la BD para responder a la consulta del usuario de forma perspicaz."
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
