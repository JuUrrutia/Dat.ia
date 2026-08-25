import json
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from app.core.constants import (
    DATA_REQUEST_KEYWORDS, GREETING_KEYWORDS, ADVISORY_KEYWORDS, EXPLANATION_KEYWORDS,
    HYBRID_KEYWORDS, REPORT_KEYWORDS, LIST_KEYWORDS, COUNT_KEYWORDS
)
from app.core.prompts import PromptManager
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.schemas import PresentationHints

class IntentClassifier:
    """
    Handles query intent classification, conversational responses, and dynamic presentation format hints.
    """

    @classmethod
    async def classify_intent(cls, question: str) -> str:
        q_lower = question.lower().strip()

        if any(k in q_lower for k in DATA_REQUEST_KEYWORDS):
            if any(k in q_lower for k in REPORT_KEYWORDS) or "informe" in q_lower:
                return "report"
            if any(k in q_lower for k in HYBRID_KEYWORDS):
                return "hybrid"
            return "data_analysis"

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
    async def classify_presentation_format(
        cls,
        question: str,
        response_type: str,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> PresentationHints:
        if response_type in ("advisory", "explanation"):
            return PresentationHints(
                show_executive_report=False,
                show_kpis=False,
                show_gauges=False,
                show_chart=False,
                preferred_view="assistant",
                summary_style="detailed"
            )

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

        return cls.heuristic_presentation_hints(question, response_type, rows, columns)

    @classmethod
    def heuristic_presentation_hints(
        cls,
        question: str,
        response_type: str,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> PresentationHints:
        q_lower = question.lower()

        if response_type == "report":
            return PresentationHints(
                show_executive_report=True, show_kpis=True,
                show_gauges=True, show_chart=True,
                preferred_view="report", summary_style="executive"
            )

        if response_type == "hybrid":
            return PresentationHints(
                show_executive_report=True, show_kpis=True,
                show_gauges=False, show_chart=True,
                preferred_view="studio", summary_style="detailed"
            )

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
                show_gauges=False, show_chart=True,
                preferred_view="studio", summary_style="detailed"
            )

        return PresentationHints(
            show_executive_report=False, show_kpis=False,
            show_gauges=False, show_chart=True if has_numeric else False,
            preferred_view="studio" if has_numeric else "table",
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
