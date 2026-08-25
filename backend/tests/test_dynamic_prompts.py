import unittest
from unittest.mock import MagicMock
from app.services.query_engine import QueryEngine
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
        self.assertIn("gobernanza", expl_prompt.lower())
        self.assertEqual(RESPONSE_GENERATION_CONFIG[ResponseType.EXPLANATION].temperature, 0.1)

    def test_prompt_manager_data_analysis_conversational(self):
        """Verifica que el prompt de interpretación de datos genere instrucciones directas y fluidas."""
        prompt = PromptManager.get_data_analysis_conversational_system_prompt("Economista")
        self.assertIn("Economista", prompt)
        self.assertIn("directamente", prompt.lower())

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

if __name__ == "__main__":
    unittest.main()
