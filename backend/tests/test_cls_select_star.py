import os
import unittest
from unittest.mock import patch, MagicMock
from app.services.ast_validator import ASTValidator, ASTValidationError
from app.services.query_engine import QueryEngine
from app.models.connection import DatabaseType

class TestCLSSelectStar(unittest.IsolatedAsyncioTestCase):
    """
    Tests ensuring that SELECT * and qualified table.* cannot bypass
    Column-Level Security (CLS) and that all execution paths enforce AST security.
    """

    def setUp(self):
        self.table_columns = {
            "clientes": ["id", "nombre", "rut", "email", "telefono"],
            "fact_ventas": ["id_venta", "fecha", "monto", "tarjeta_credito", "cliente_id"],
            "dim_empleados": ["id_empleado", "nombre", "salario_bruto", "departamento"]
        }

    def test_select_star_masks_blocked_columns(self):
        """
        SELECT * FROM clientes with blocked 'rut' and 'email' must rewrite
        the AST to only include authorized columns (id, nombre, telefono).
        """
        raw_sql = "SELECT * FROM clientes"
        blocked_cols = {"rut", "email"}
        allowed_tbls = {"clientes"}

        is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
            raw_sql,
            dialect="sqlite",
            allowed_tables=allowed_tbls,
            blocked_columns=blocked_cols,
            table_columns=self.table_columns
        )

        self.assertTrue(is_valid)
        # Verify rewritten SQL excludes rut and email
        self.assertNotIn("rut", secured_sql.lower())
        self.assertNotIn("email", secured_sql.lower())
        self.assertIn("nombre", secured_sql.lower())
        self.assertIn("id", secured_sql.lower())
        self.assertIn("telefono", secured_sql.lower())

        # Verify metadata extracted columns
        self.assertNotIn("rut", meta["columns_used"])
        self.assertNotIn("email", meta["columns_used"])
        self.assertIn("nombre", meta["columns_used"])

    def test_select_star_qualified_alias_also_masks(self):
        """
        SELECT t.* FROM clientes t with blocked 'rut' must rewrite
        to qualified columns excluding 'rut' (t.id, t.nombre, t.email, t.telefono).
        """
        raw_sql = "SELECT t.* FROM clientes t"
        blocked_cols = {"rut"}
        allowed_tbls = {"clientes"}

        is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
            raw_sql,
            dialect="sqlite",
            allowed_tables=allowed_tbls,
            blocked_columns=blocked_cols,
            table_columns=self.table_columns
        )

        self.assertTrue(is_valid)
        self.assertNotIn("rut", secured_sql.lower())
        self.assertIn("t.nombre", secured_sql.lower())
        self.assertIn("t.id", secured_sql.lower())
        self.assertNotIn("rut", meta["columns_used"])

    def test_select_star_raises_if_all_columns_blocked(self):
        """
        If all physical columns in a table are blocked for a role,
        expanding SELECT * must raise ASTValidationError.
        """
        raw_sql = "SELECT * FROM clientes"
        blocked_cols = {"id", "nombre", "rut", "email", "telefono"}
        allowed_tbls = {"clientes"}

        with self.assertRaises(ASTValidationError) as ctx:
            ASTValidator.validate_and_secure_sql(
                raw_sql,
                dialect="sqlite",
                allowed_tables=allowed_tbls,
                blocked_columns=blocked_cols,
                table_columns=self.table_columns
            )
        self.assertIn("Acceso denegado", str(ctx.exception))

    def test_admin_role_select_star_unrestricted(self):
        """
        For Admin role (no blocked columns), SELECT * expands to all physical columns
        without error or restriction.
        """
        raw_sql = "SELECT * FROM clientes"
        allowed_tbls = {"clientes"}

        is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
            raw_sql,
            dialect="sqlite",
            allowed_tables=allowed_tbls,
            blocked_columns=None,
            table_columns=self.table_columns
        )

        self.assertTrue(is_valid)
        self.assertIn("rut", secured_sql.lower())
        self.assertIn("email", secured_sql.lower())
        self.assertIn("nombre", secured_sql.lower())
        self.assertEqual(len(meta["columns_used"]), 5)

    @patch("app.services.llm_service.LLMService.generate_completion")
    @patch("app.services.query_engine.DynamicSchemaPruningService.resolve_db_path")
    @patch("app.services.query_engine.DynamicSchemaPruningService.get_physical_table_columns")
    async def test_self_healing_fallback_respects_cls(
        self, mock_get_cols, mock_resolve_db, mock_llm
    ):
        """
        Simulates that when primary SQL fails and self-healing LLM correction also fails,
        the emergency fallback path (SELECT * FROM table) passes through ASTValidator
        and enforces Column-Level Security (CLS) by masking blocked columns.
        """
        mock_resolve_db.return_value = "dummy.db"
        mock_get_cols.return_value = [
            {"name": "id", "type": "INTEGER"},
            {"name": "nombre", "type": "TEXT"},
            {"name": "salario_bruto", "type": "REAL"},
        ]
        # LLM returns invalid SQL to trigger fallback
        mock_llm.return_value = "```sql\nSELECT non_existent FROM dim_empleados;\n```"

        with patch("sqlite3.connect") as mock_sqlite:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_sqlite.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # First query fails with sqlite error to trigger self-healing
            # Second (healing attempt) fails to trigger emergency fallback
            # Third (fallback execution) succeeds
            mock_cursor.execute.side_effect = [
                Exception("no such column: non_existent"),
                Exception("no such column: non_existent"),
                None
            ]
            mock_cursor.fetchall.return_value = [
                {"id": 1, "nombre": "Juan"}
            ]

            with patch.object(QueryEngine, "get_allowed_tables_for_role", return_value={"dim_empleados"}):
                with patch.object(QueryEngine, "get_blocked_columns_for_role", return_value={"salario_bruto"}):
                    response = await QueryEngine.execute_query(
                        question="muestrame los empleados",
                        user_role="Economista",
                        is_admin=False
                    )

                    # Traceability SQL executed must be secured and not contain salario_bruto
                    executed_sql = response.traceability.sql_executed.lower()
                    self.assertNotIn("salario_bruto", executed_sql)
                    self.assertIn("dim_empleados", executed_sql)
                    self.assertIn("id", executed_sql)
                    self.assertIn("nombre", executed_sql)

if __name__ == "__main__":
    unittest.main()
