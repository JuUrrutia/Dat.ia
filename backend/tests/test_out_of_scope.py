import pytest
import unittest
from unittest.mock import patch, AsyncMock
from app.modules.chat_engine.engine import QueryEngine
from app.modules.chat_engine.intent_classifier import IntentClassifier
from app.modules.chat_engine.response_builder import ResponseBuilder
from app.core.prompts import PromptManager, ResponseType

class TestOutOfScopeCapabilities(unittest.IsolatedAsyncioTestCase):

    async def test_intent_classifier_detects_out_of_scope_queries(self):
        """Unsupported out-of-scope requests are accurately detected."""
        out_of_scope_samples = [
            "Me puedes generar una imagen",
            "¿Me puedes generar una imagen?",
            "genera una foto",
            "crea un logo para la empresa",
            "hazme un dibujo",
            "puedes hacer un video",
            "cuéntame un chiste",
            "busca en internet las noticias de hoy",
            "cuáles son tus limitaciones"
        ]
        for query in out_of_scope_samples:
            detected = await IntentClassifier.classify_intent(query)
            self.assertEqual(
                detected,
                "out_of_scope",
                f"Query '{query}' should be classified as out_of_scope, got '{detected}'"
            )

    async def test_intent_classifier_preserves_standard_business_queries(self):
        """Data analysis and standard queries are NOT classified as out_of_scope."""
        valid_samples = [
            "¿Cuál es el total de ventas por categoría?",
            "Top 5 clientes con mayores compras",
            "Hola DATIA, buenos días",
            "Explícame qué significa el margen de contribución"
        ]
        for query in valid_samples:
            detected = await IntentClassifier.classify_intent(query)
            self.assertNotEqual(
                detected,
                "out_of_scope",
                f"Valid query '{query}' should not be out_of_scope"
            )

    async def test_query_engine_returns_dynamic_out_of_scope_response(self):
        """QueryEngine returns a dynamic, empathetic out_of_scope response with proper traceability."""
        query = "Me puedes generar una imagen"
        role = "Analista Financiero & Comercial"

        # Mock LLM response to verify conversational response generation
        simulated_llm_text = (
            "Como asistente de analítica e inteligencia de datos, mi especialidad es analizar y democratizar "
            "la información corporativa de la organización. Actualmente no dispongo de capacidades para generar "
            "imágenes o contenido multimedia. Sin embargo, para tu rol como Analista Financiero & Comercial, "
            "puedo diseñar gráficos estadísticos interactivos (barras, líneas, áreas o tortas) y desglosar KPIs "
            "sobre ventas, ingresos y costos a partir de las tablas disponibles."
        )

        with patch("app.modules.chat_engine.llm_service.LLMService.generate_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = simulated_llm_text

            resp = await QueryEngine.execute_query(
                question=query,
                user_role=role,
                is_admin=False,
                connection_id=1
            )

            self.assertEqual(resp.response_type, "out_of_scope")
            self.assertEqual(resp.traceability.validation_status, "FUERA_DE_ALCANCE")
            self.assertIn("FUERA DE ALCANCE", resp.traceability.sql_executed)
            self.assertEqual(resp.traceability.rows_returned, 0)
            self.assertIn("Analista Financiero & Comercial", resp.conversational_response)
            self.assertIn("gráficos estadísticos", resp.conversational_response)
            self.assertEqual(len(resp.kpis), 2)
            self.assertEqual(resp.kpis[0].title, "Alcance DATIA")
            self.assertEqual(resp.presentation_hints.preferred_view, "assistant")
            self.assertTrue(resp.presentation_hints.show_kpis)
            self.assertFalse(resp.presentation_hints.show_chart)

    def test_response_builder_out_of_scope_fallback_when_llm_offline(self):
        """ResponseBuilder provides high-quality fallback text even when conversational generation is None."""
        resp = ResponseBuilder.build_out_of_scope_response(
            question="Me puedes generar una imagen",
            user_role="Economista",
            allowed_tables={"dim_clientes", "fact_ventas"},
            conversational=None
        )

        self.assertEqual(resp.response_type, "out_of_scope")
        self.assertEqual(resp.traceability.validation_status, "FUERA_DE_ALCANCE")
        self.assertIn("no dispongo de funciones para generar imágenes", resp.conversational_response)
        self.assertIn("Economista", resp.conversational_response)
        self.assertIn("gráficos estadísticos interactivos", resp.conversational_response)
        self.assertGreaterEqual(len(resp.suggested_questions), 2)

    def test_prompt_manager_out_of_scope_prompt(self):
        """PromptManager generates the comprehensive out_of_scope system prompt with role and tables."""
        prompt = PromptManager.get_out_of_scope_system_prompt("Economista", {"fact_ventas", "dim_clientes"})
        self.assertIn("Economista", prompt)
        self.assertIn("fact_ventas", prompt)
        self.assertIn("FUERA DE TUS FUNCIONES", prompt)
        self.assertIn("Transparencia empática", prompt)
        self.assertEqual(ResponseType.OUT_OF_SCOPE.value, "out_of_scope")
