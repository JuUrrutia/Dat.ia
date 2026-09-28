import unittest
from app.modules.chat_engine.ast_validator import ASTValidator, ASTValidationError

class TestASTValidator(unittest.TestCase):

    def test_valid_select_query(self):
        sql = "SELECT id, monto, fecha FROM fact_ventas WHERE fecha >= '2026-01-01'"
        is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
            sql,
            dialect="postgres",
            allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertIn("LIMIT 500", secured_sql)
        self.assertIn("fact_ventas", meta["tables_used"])

    def test_generate_sql_explanation(self):
        sql = "SELECT dim_clientes.nombre, SUM(fact_ventas.monto) FROM fact_ventas JOIN dim_clientes ON fact_ventas.cliente_id = dim_clientes.id WHERE fact_ventas.monto > 100 GROUP BY dim_clientes.nombre ORDER BY SUM(fact_ventas.monto) DESC LIMIT 10"
        explanation = ASTValidator.generate_sql_explanation(sql, dialect="sqlite")
        self.assertIn("fact_ventas", explanation)
        self.assertIn("dim_clientes", explanation)
        self.assertIn("suma", explanation.lower())
        self.assertIn("filtra por", explanation.lower())
        self.assertIn("agrupa por", explanation.lower())
        self.assertIn("10", explanation)

    def test_reject_dml_operation(self):
        sql = "DELETE FROM fact_ventas WHERE id = 1"
        with self.assertRaises(ASTValidationError) as excinfo:
            ASTValidator.validate_and_secure_sql(sql, allowed_tables={"fact_ventas"})
        self.assertIn("Únicamente se permiten consultas SELECT", str(excinfo.exception))

    def test_reject_semicolon_chaining(self):
        sql = "SELECT * FROM fact_ventas; DROP TABLE dim_clientes;"
        with self.assertRaises(ASTValidationError) as excinfo:
            ASTValidator.validate_and_secure_sql(sql, allowed_tables={"fact_ventas"})
        self.assertIn("Se prohíbe el encadenamiento", str(excinfo.exception))

    def test_reject_unauthorized_table(self):
        sql = "SELECT * FROM dim_empleados_rrhh"
        with self.assertRaises(ASTValidationError) as excinfo:
            ASTValidator.validate_and_secure_sql(sql, allowed_tables={"fact_ventas", "dim_productos"})
        self.assertIn("Gobernanza RBAC: Acceso denegado. No tienes permisos para acceder ni manejar estos datos.", str(excinfo.exception))

    def test_reject_blocked_column(self):
        sql = "SELECT id, salario_base FROM fact_ventas"
        with self.assertRaises(ASTValidationError) as excinfo:
            ASTValidator.validate_and_secure_sql(
                sql,
                allowed_tables={"fact_ventas"},
                blocked_columns={"salario_base"}
            )
        self.assertIn("Gobernanza RBAC: Acceso denegado. No tienes permisos para acceder ni manejar estos datos.", str(excinfo.exception))

if __name__ == "__main__":
    unittest.main()
