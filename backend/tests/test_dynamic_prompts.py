import unittest
from unittest.mock import MagicMock
from app.services.query_engine import QueryEngine

class TestDynamicPrompts(unittest.TestCase):

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
