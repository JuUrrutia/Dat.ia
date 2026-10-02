import unittest
from unittest.mock import MagicMock
from app.modules.chat_engine.engine import QueryEngine
from app.core.prompts import PromptManager

class TestDynamicPrompts(unittest.TestCase):

    def test_prompt_manager_text_to_sql(self):
        """Verifica que PromptManager genere prompts de Text-to-SQL parametrizados."""
        prompt = PromptManager.get_text_to_sql_system_prompt("Economista", {"fact_ventas", "dim_clientes"})
        self.assertIn("fact_ventas", prompt)
        self.assertIn("dim_clientes", prompt)
        self.assertIn("SELECT", prompt)

    def test_prompt_manager_conversational(self):
        """Verifica que PromptManager devuelva configuraciones para respuestas conversacionales."""
        from app.core.prompts import ResponseType, RESPONSE_GENERATION_CONFIG
        advisory_prompt = PromptManager.get_conversational_system_prompt(ResponseType.ADVISORY)
        self.assertIn("asesor", advisory_prompt.lower())
        self.assertEqual(RESPONSE_GENERATION_CONFIG[ResponseType.ADVISORY].temperature, 0.2)

        expl_prompt = PromptManager.get_conversational_system_prompt(ResponseType.EXPLANATION)
        self.assertIn("pedagógica", expl_prompt.lower())
        self.assertEqual(RESPONSE_GENERATION_CONFIG[ResponseType.EXPLANATION].temperature, 0.2)

    def test_prompt_manager_data_analysis_conversational(self):
        """Verifica que el prompt de interpretación de datos genere instrucciones directas y fluidas."""
        prompt = PromptManager.get_data_analysis_conversational_system_prompt("Economista")
        self.assertIn("Economista", prompt)
        self.assertIn("inteligente", prompt.lower())

    def test_prompt_manager_greeting(self):
        """Verifica que el prompt de saludo reconozca las tablas autorizadas del rol."""
        prompt = PromptManager.get_general_greeting_system_prompt("TI", {"dim_servidores", "fact_incidentes"})
        self.assertIn("TI", prompt)
        self.assertIn("dim_servidores", prompt)

    def test_grounding_query_generation_dynamic(self):
        """Verifica que _get_grounding_query_for_question genere una consulta sobre la primera tabla autorizada."""
        allowed_tables = {"dim_clientes", "fact_ventas"}
        sql = QueryEngine._get_grounding_query_for_question(
            question="¿Cuántos clientes tenemos?",
            user_role="Economista",
            allowed_tables=allowed_tables
        )
        self.assertIn("dim_clientes", sql)
        self.assertTrue(sql.startswith("SELECT * FROM"))

    def test_grounding_query_fallback_table(self):
        """Verifica que si ninguna tabla coincide explícitamente en el texto, se use la primera autorizada en orden alfabético."""
        allowed_tables = {"fact_inventario", "dim_almacen"}
        sql = QueryEngine._get_grounding_query_for_question(
            question="Resumen general",
            user_role="TI",
            allowed_tables=allowed_tables
        )
        self.assertIn("dim_almacen", sql)

    def test_prompt_manager_unified_synthesis_prompts(self):
        """Verifica que el prompt de síntesis unificada adapte su enfoque según el rol y especifique las 4 claves JSON requeridas."""
        econ_sys = PromptManager.get_unified_synthesis_system_prompt("Economista")
        self.assertIn("financieras", econ_sys.lower())
        self.assertIn('"narrative"', econ_sys)
        self.assertIn('"kpis"', econ_sys)
        self.assertIn('"executive_report"', econ_sys)
        self.assertIn('"suggested_questions"', econ_sys)

        ti_sys = PromptManager.get_unified_synthesis_system_prompt("TI")
        self.assertIn("operativo", ti_sys.lower())

        user_prompt = PromptManager.get_unified_synthesis_user_prompt(
            question="¿Cuáles son las ventas?",
            user_role="Economista",
            rows=[{"total": 5000}],
            columns=["total"],
            secured_sql="SELECT total FROM fact_ventas",
            conversation_context="Pregunta previa: ¿Quiénes son los clientes?"
        )
        self.assertIn("fact_ventas", user_prompt)
        self.assertIn("5000", user_prompt)
        self.assertIn("Pregunta previa", user_prompt)

    def test_multi_turn_context_formatting(self):
        """Verifica que el formateador multi-turno incluya la instrucción adaptativa para SQL y narrativa."""
        history = [
            {"question": "Ventas del último año", "sql": "SELECT sum(monto) FROM fact_ventas"},
            {"question": "¿Y cuál es el top 3 productos?", "sql": "SELECT producto, sum(monto) FROM fact_ventas GROUP BY producto ORDER BY 2 DESC LIMIT 3"}
        ]
        sql_ctx = PromptManager.format_conversation_context(history)
        self.assertIn("INSTRUCCIÓN MULTI-TURNO", sql_ctx)
        self.assertIn("Turno 1", sql_ctx)
        self.assertIn("Turno 2", sql_ctx)

        synth_ctx = PromptManager.format_conversation_context_for_synthesis(history)
        self.assertIn("Turno previo 1", synth_ctx)
        self.assertIn("narrativa con fluidez", synth_ctx)

    def test_unified_synthesis_resilient_parser(self):
        """Verifica el parser resiliente de 3 capas en KPICalculator.generate_unified_synthesis_with_llm."""
        import asyncio
        from unittest.mock import patch, AsyncMock
        from app.modules.chat_engine.kpi_calculator import KPICalculator

        # Tier 1 & 2: JSON con trailing commas y subtítulos con relleno
        tier2_json = """{
            "narrative": "El total de ventas supera la meta proyectada.",
            "kpis": [
                {"title": "Total Facturado", "value": "$1.5M", "subtitle": "Este KPI indica el acumulado total.", "change_direction": "positive"},
                {"title": "Margen Operativo", "value": "28.5%", "subtitle": "Este KPI muestra la rentabilidad neta.", "change_direction": "positive"},
                {"title": "Clientes Activos", "value": "450", "subtitle": "Muestra del mes corriente.", "change_direction": "neutral"},
            ],
            "executive_report": {
                "overview": "Excelente desempeño trimestral.",
                "key_findings": ["Crecimiento de 12%"],
                "recommendations": ["Expandir canales"],
                "risk_level": "BAJO",
                "business_impact": "Consolidación de cuota de mercado."
            },
            "suggested_questions": [
                "¿Cuál es el margen por categoría?",
                "¿Cómo evolucionó el costo?",
                "¿Quién es el cliente principal?"
            ],
        }"""

        with patch("app.modules.chat_engine.llm_service.LLMService.generate_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = tier2_json
            result = asyncio.run(KPICalculator.generate_unified_synthesis_with_llm(
                question="¿Cómo van las ventas?",
                user_role="Economista",
                rows=[{"monto": 1500000}],
                columns=["monto"],
                secured_sql="SELECT monto FROM fact_ventas",
                is_llm_active=True
            ))

            self.assertIsNotNone(result)
            self.assertEqual(result["narrative"], "El total de ventas supera la meta proyectada.")
            self.assertEqual(len(result["kpis"]), 3)
            # Sanitization of AI filler in subtitle
            self.assertNotIn("Este KPI indica", result["kpis"][0].subtitle)
            self.assertEqual(result["executive_report"].risk_level, "BAJO")
            self.assertEqual(len(result["suggested_questions"]), 3)

        # Tier 3: LLM responde solo con texto plano/markdown en vez de JSON
        tier3_raw_text = "Resumen directo en prosa: Las ventas fueron de $1.5M sin incidentes."
        with patch("app.modules.chat_engine.llm_service.LLMService.generate_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = tier3_raw_text
            result = asyncio.run(KPICalculator.generate_unified_synthesis_with_llm(
                question="¿Cómo van las ventas?",
                user_role="Economista",
                rows=[{"monto": 1500000}],
                columns=["monto"],
                secured_sql="SELECT monto FROM fact_ventas",
                is_llm_active=True
            ))

            self.assertIsNotNone(result)
            self.assertEqual(result["narrative"], tier3_raw_text)
            self.assertIsNone(result["kpis"])
            self.assertIsNone(result["executive_report"])

if __name__ == "__main__":
    unittest.main()

