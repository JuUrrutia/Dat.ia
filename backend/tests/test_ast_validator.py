import unittest
from app.services.ast_validator import ASTValidator, ASTValidationError

class TestASTValidator(unittest.TestCase):

    def test_valid_select_query(self):
        sql = "SELECT id, monto, fecha FROM fact_ventas WHERE fecha >= '2026-01-01'"
        is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
            sql,
            dialect="postgres",
            allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertIn("LIMIT 1000", secured_sql)
        self.assertIn("fact_ventas", meta["tables_used"])

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
