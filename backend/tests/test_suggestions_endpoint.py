import unittest
from app.services.query_engine import QueryEngine

class TestSuggestionsEndpoint(unittest.TestCase):

    def test_dynamic_suggestions_economista(self):
        """Verifica que las sugerencias para Economista contengan preguntas sobre ventas e ingresos."""
        allowed_tables = {"fact_ventas", "dim_productos", "fact_ingresos_costos"}
        suggestions = QueryEngine.get_dynamic_suggestions("Economista", allowed_tables)
        
        self.assertGreaterEqual(len(suggestions), 2)
        self.assertTrue(any("ventas" in s.lower() or "ingresos" in s.lower() for s in suggestions))

    def test_dynamic_suggestions_ti(self):
        """Verifica que las sugerencias para TI contengan preguntas sobre servidores e incidentes."""
        allowed_tables = {"fact_incidentes_ti", "dim_servidores"}
        suggestions = QueryEngine.get_dynamic_suggestions("TI", allowed_tables)

        self.assertGreaterEqual(len(suggestions), 2)
        self.assertTrue(any("ti" in s.lower() or "servidor" in s.lower() or "incidentes" in s.lower() for s in suggestions))

    def test_dynamic_suggestions_empty_role(self):
        """Verifica que si no hay tablas autorizadas (ej. rol Usuario), se sugiera solicitar acceso."""
        suggestions = QueryEngine.get_dynamic_suggestions("Usuario", set())
        self.assertEqual(len(suggestions), 2)
        self.assertIn("¿Qué información puedo consultar con mi perfil?", suggestions[0])

    def test_llm_suggestions_fallback(self):
        """Verifica que el método asíncrono get_dynamic_suggestions_with_llm funcione y use fallback cuando el LLM está offline."""
        import asyncio
        allowed_tables = {"fact_ventas", "dim_productos"}
        suggestions = asyncio.run(
            QueryEngine.get_dynamic_suggestions_with_llm(
                user_role="Economista",
                allowed_tables=allowed_tables
            )
        )
        self.assertGreaterEqual(len(suggestions), 2)

if __name__ == "__main__":
    unittest.main()
