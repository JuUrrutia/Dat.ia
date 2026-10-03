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

    def test_cte_query_does_not_flag_cte_as_unauthorized_table(self):
        sql = "WITH metricas AS (SELECT id, monto FROM fact_ventas) SELECT id, monto FROM metricas"
        is_valid, secured, meta = ASTValidator.validate_and_secure_sql(
            sql,
            allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertIn("fact_ventas", meta["tables_used"])
        self.assertNotIn("metricas", meta["tables_used"])

    def test_limit_above_max_is_clamped_not_crashed(self):
        """sqlglot>=30: Literal.this es read-only. Limitar sobre el maximo no debe lanzar AttributeError."""
        for sql in (
            "SELECT id_venta FROM fact_ventas LIMIT 501",
            "SELECT id_venta FROM fact_ventas LIMIT 1000000",
        ):
            is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
                sql, dialect="postgres", allowed_tables={"fact_ventas"}
            )
            self.assertTrue(is_valid)
            self.assertIn("LIMIT 500", secured_sql)
            self.assertNotIn("501", secured_sql)
            self.assertNotIn("1000000", secured_sql)

    def test_limit_at_max_boundary_is_left_untouched(self):
        """El limite igual al maximo no se modifica."""
        is_valid, secured_sql, _ = ASTValidator.validate_and_secure_sql(
            "SELECT id_venta FROM fact_ventas LIMIT 500",
            dialect="postgres", allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertIn("LIMIT 500", secured_sql)

    def test_small_limit_is_preserved_not_raised_to_max(self):
        """El clamp es un techo, no un piso: LIMIT 5 debe seguir siendo 5."""
        for literal in ("5", "1"):
            is_valid, secured_sql, _ = ASTValidator.validate_and_secure_sql(
                f"SELECT id_venta FROM fact_ventas LIMIT {literal}",
                dialect="postgres", allowed_tables={"fact_ventas"}
            )
            self.assertTrue(is_valid)
            self.assertIn(f"LIMIT {literal}", secured_sql)
            self.assertNotIn("LIMIT 500", secured_sql)

    def test_tsql_top_above_max_is_clamped(self):
        """TOP es un Limit en el AST de tsql: tambien debe clampearse y no crashear."""
        is_valid, secured_sql, _ = ASTValidator.validate_and_secure_sql(
            "SELECT TOP 1000000 id FROM fact_ventas",
            dialect="tsql", allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertIn("TOP 500", secured_sql)

    def test_limit_inside_subquery_is_clamped(self):
        """El clamp aplica a todos los Limit del arbol, no solo al del nodo raiz."""
        sql = (
            "SELECT COUNT(*) FROM (SELECT id_venta, monto FROM fact_ventas "
            "LIMIT 1000000000) x"
        )
        is_valid, secured_sql, _ = ASTValidator.validate_and_secure_sql(
            sql, dialect="postgres", allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertNotIn("1000000000", secured_sql)
        self.assertIn("LIMIT 500", secured_sql)

    def test_small_limit_inside_subquery_is_preserved(self):
        """Un LIMIT chico legitimo dentro de una subconsulta no debe convertirse en 500."""
        is_valid, secured_sql, _ = ASTValidator.validate_and_secure_sql(
            "SELECT id_venta FROM (SELECT id_venta FROM fact_ventas LIMIT 5) y",
            dialect="postgres", allowed_tables={"fact_ventas"}
        )
        self.assertTrue(is_valid)
        self.assertIn("LIMIT 5", secured_sql)
        self.assertIn("LIMIT 500", secured_sql)

    def test_select_star_without_table_columns_fails_closed(self):
        """Sin columnas conocidas no se puede filtrar el star: falla cerrado, no pasa sin filtrar."""
        for table_columns in (None, {}):
            with self.assertRaises(ASTValidationError) as excinfo:
                ASTValidator.validate_and_secure_sql(
                    "SELECT * FROM dim_clientes",
                    dialect="postgres",
                    allowed_tables={"dim_clientes"},
                    table_columns=table_columns
                )
            self.assertIn("SELECT *", str(excinfo.exception))

    def test_select_star_with_partial_table_columns_still_fails_closed(self):
        """Consistencia: dict parcial y dict vacio deben comportarse igual."""
        with self.assertRaises(ASTValidationError):
            ASTValidator.validate_and_secure_sql(
                "SELECT * FROM dim_clientes",
                dialect="postgres",
                allowed_tables={"dim_clientes"},
                table_columns={"otra_tabla": ["id"]}
            )

    def test_count_star_without_table_columns_is_allowed(self):
        """COUNT(*) no es una proyeccion star: no revela columnas y debe seguir funcionando."""
        is_valid, secured_sql, _ = ASTValidator.validate_and_secure_sql(
            "SELECT COUNT(*) FROM dim_clientes",
            dialect="postgres",
            allowed_tables={"dim_clientes"}
        )
        self.assertTrue(is_valid)
        self.assertIn("COUNT(*)", secured_sql)

    def test_admin_bypasses_table_and_column_restrictions(self):
        sql = "SELECT id, salario_base FROM cualquier_tabla_corporativa"
        is_valid, secured, meta = ASTValidator.validate_and_secure_sql(
            sql,
            allowed_tables={"fact_ventas"},  # Table is outside allowed_tables
            blocked_columns={"salario_base"}, # Column is in blocked_columns
            is_admin=True
        )
        self.assertTrue(is_valid)
        self.assertIn("cualquier_tabla_corporativa", meta["tables_used"])

if __name__ == "__main__":
    unittest.main()
