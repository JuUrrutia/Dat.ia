import unittest
from unittest.mock import MagicMock
from app.modules.chat_engine.engine import QueryEngine
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

class TestRBACGovernance(unittest.TestCase):

    def test_admin_gets_all_catalog_tables(self):
        """Admin role queries SemanticCatalog model and gets all catalog tables."""
        mock_entry1 = MagicMock(table_name="dim_clientes", column_name="id_cliente", description="ID")
        mock_entry2 = MagicMock(table_name="fact_ventas", column_name="id_venta", description="ID")
        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = [mock_entry1, mock_entry2]

        res = QueryEngine.get_allowed_tables_for_role("Administrador", is_admin=True, db=mock_db)
        self.assertEqual(res, {"dim_clientes", "fact_ventas"})

    def test_role_permissions_queried_from_permission_model(self):
        """Non-admin user permissions are dynamically resolved from RoleTablePermission model."""
        mock_perm1 = MagicMock(table_name="fact_ventas", is_allowed=True)
        mock_perm2 = MagicMock(table_name="dim_productos", is_allowed=True)
        mock_db = MagicMock()

        # Mock RoleTablePermission query result
        mock_db.query().filter().all.return_value = [mock_perm1, mock_perm2]

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=2,
            connection_id=1
        )
        self.assertEqual(res, {"fact_ventas", "dim_productos"})

    def test_role_id_none_unassigned_fails_closed(self):
        """Non-admin user with unassigned role_id=None and non-existent role name returns empty set."""
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None  # No matching Role found
        mock_db.query().filter().all.return_value = []

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="UsuarioSinRol",
            is_admin=False,
            db=mock_db,
            role_id=None,
            connection_id=1
        )
        self.assertEqual(res, set(), "Unassigned role_id=None must return empty set (Fail-Closed)")

    def test_db_revoked_permissions_returns_empty_set(self):
        """When a role has 0 allowed tables configured in RoleTablePermission, returns empty set."""
        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=10,
            connection_id=1
        )
        self.assertEqual(res, set())

    def test_db_exception_fails_closed(self):
        """When DB query raises an Exception, system fails closed by returning empty set."""
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database connection lost")

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=10,
            connection_id=1
        )
        self.assertEqual(res, set())

    def test_column_permissions_queried_from_permission_model(self):
        """Blocked columns are dynamically queried from RoleColumnPermission model."""
        mock_col_perm = MagicMock(
            table_name="fact_ventas",
            column_name="cuenta_bancaria_iban",
            permission_type=MagicMock(value="BLOCKED")
        )
        # Match enum comparison inside dynamic_schema
        from app.modules.admin_catalog.models import ColumnPermissionType
        mock_col_perm.permission_type = ColumnPermissionType.BLOCKED

        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = [mock_col_perm]

        res = QueryEngine.get_blocked_columns_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=2,
            connection_id=1
        )
        self.assertIn("cuenta_bancaria_iban", res)

    def test_ti_role_asking_financial_questions_blocked_by_governance(self):
        """TI role asking for sales/balances without business tables is denied by cross-domain guardrail."""
        denial = QueryEngine.check_domain_governance(
            question="¿Cuáles fueron los saldos y ventas totales del mes?",
            user_role="TI",
            allowed_tables={"dim_servidores", "fact_incidentes_ti"}
        )
        self.assertIsNotNone(denial)
        self.assertIn("Gobernanza RBAC: Acceso denegado", denial)
        self.assertIn("información financiera", denial)

    def test_economista_role_asking_infrastructure_questions_blocked_by_governance(self):
        """Economista role asking for servers/IT incidents without tech tables is denied by cross-domain guardrail."""
        denial = QueryEngine.check_domain_governance(
            question="¿Cuántos incidentes ti ocurrieron en los servidores?",
            user_role="Economista",
            allowed_tables={"fact_ventas", "dim_clientes"}
        )
        self.assertIsNotNone(denial)
        self.assertIn("Gobernanza RBAC: Acceso denegado", denial)
        self.assertIn("infraestructura TI", denial)

    def test_admin_role_can_query_any_domain(self):
        """Domain governance does not block allowed queries when roles match their domain."""
        # TI querying IT infrastructure
        ti_denial = QueryEngine.check_domain_governance(
            question="¿Cuántos incidentes ti ocurrieron en los servidores?",
            user_role="TI",
            allowed_tables={"dim_servidores", "fact_incidentes_ti"}
        )
        self.assertIsNone(ti_denial)

        # Economista querying sales
        eco_denial = QueryEngine.check_domain_governance(
            question="¿Cuáles son las ventas totales por cliente?",
            user_role="Economista",
            allowed_tables={"fact_ventas", "dim_clientes"}
        )
        self.assertIsNone(eco_denial)

    def test_ast_validation_error_in_execute_with_self_healing_propagates(self):
        """execute_with_self_healing strictly raises ASTValidationError on unauthorized table query (no silent pass)."""
        import asyncio
        from app.modules.chat_engine.sql_executor import SQLExecutor
        from app.modules.chat_engine.ast_validator import ASTValidationError

        unauthorized_sql = "SELECT * FROM fact_ventas WHERE id = 1;"
        ti_allowed_tables = {"dim_servidores", "fact_incidentes_ti"}

        with self.assertRaises(ASTValidationError):
            asyncio.run(SQLExecutor.execute_with_self_healing(
                target_db_path="./datia_demo.db",
                question="ventas",
                initial_sql=unauthorized_sql,
                allowed_tables=ti_allowed_tables,
                blocked_columns=set(),
                table_columns_map={"dim_servidores": ["id", "nombre"]}
            ))

    def test_execute_query_blocks_ti_for_financial_question(self):
        """QueryEngine.execute_query cleanly rejects TI asking for sales/financial data with RECHAZADO_RBAC."""
        import asyncio
        mock_db = MagicMock()
        # Mock TI permissions having only server tables
        mock_perm = MagicMock(table_name="dim_servidores", is_allowed=True)
        mock_db.query().filter().all.return_value = [mock_perm]

        resp = asyncio.run(QueryEngine.execute_query(
            question="¿Cuáles son los saldos totales de ventas del año?",
            user_role="TI",
            is_admin=False,
            db=mock_db,
            role_id=11,
            connection_id=1
        ))

        self.assertEqual(resp.traceability.validation_status, "RECHAZADO_RBAC")
        self.assertIn("Gobernanza RBAC: Acceso denegado", resp.summary_text)
        self.assertIn("información financiera", resp.summary_text)

    def test_execute_query_blocks_economista_for_infrastructure_question(self):
        """QueryEngine.execute_query cleanly rejects Economista asking for server/IT data with RECHAZADO_RBAC."""
        import asyncio
        mock_db = MagicMock()
        # Mock Economista permissions having only sales tables
        mock_perm = MagicMock(table_name="fact_ventas", is_allowed=True)
        mock_db.query().filter().all.return_value = [mock_perm]

        resp = asyncio.run(QueryEngine.execute_query(
            question="¿Cuántos incidentes ti ocurrieron en los servidores?",
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=10,
            connection_id=1
        ))

        self.assertEqual(resp.traceability.validation_status, "RECHAZADO_RBAC")
        self.assertIn("Gobernanza RBAC: Acceso denegado", resp.summary_text)
        self.assertIn("infraestructura TI", resp.summary_text)

    def test_financial_analyst_asking_it_infrastructure_and_modules_blocked(self):
        """Financial Analyst asking about IT modules, infrastructure, tickets or tech is strictly blocked."""
        it_questions = [
            "Hazme un analisis tecnologico",
            "Hazme un análisis tecnológico",
            "Hazme un analisis de tecnologia",
            "¿Cuál es el estado de la infraestructura de TI?",
            "¿Cuáles son los incidentes técnicos de soporte?",
            "¿Cómo está el módulo de tecnología?",
            "¿Qué servidores están activos?",
            "¿Cuál es el consumo de CPU y memoria de los servidores?",
            "Dame un reporte del área de TI",
            "¿Cuáles son los tickets de soporte técnico?"
        ]
        for q in it_questions:
            denial = QueryEngine.check_domain_governance(
                question=q,
                user_role="Analista Financiero & Comercial",
                allowed_tables={"fact_ventas", "dim_clientes"}
            )
            self.assertIsNotNone(denial, f"Question '{q}' should be blocked for Analista Financiero")
            self.assertIn("Gobernanza RBAC: Acceso denegado", denial)
            self.assertIn("infraestructura TI", denial)

    def test_greeting_with_cross_domain_it_question_is_blocked(self):
        """Conversational greeting containing out-of-domain IT questions is rejected by RBAC before greeting branch."""
        import asyncio
        mock_db = MagicMock()
        mock_perm = MagicMock(table_name="fact_ventas", is_allowed=True)
        mock_db.query().filter().all.return_value = [mock_perm]

        resp = asyncio.run(QueryEngine.execute_query(
            question="Hola, ¿cuántos servidores hay en el módulo de TI?",
            user_role="Analista Financiero & Comercial",
            is_admin=False,
            db=mock_db,
            role_id=3,
            connection_id=1
        ))
        self.assertEqual(resp.traceability.validation_status, "RECHAZADO_RBAC")
        self.assertIn("Gobernanza RBAC: Acceso denegado", resp.summary_text)

    def test_ti_asking_billing_money_and_financial_module_blocked(self):
        """TI role asking for money, billing, or financial modules is strictly blocked."""
        fin_questions = [
            "¿Cuánto dinero se recaudó este mes?",
            "¿Cuál es la facturación del período?",
            "¿Cómo va el módulo financiero?",
            "¿Cuáles son los márgenes de ganancia y EBITDA?"
        ]
        for q in fin_questions:
            denial = QueryEngine.check_domain_governance(
                question=q,
                user_role="Ingeniero de Infraestructura & TI",
                allowed_tables={"dim_servidores", "fact_incidentes_ti"}
            )
            self.assertIsNotNone(denial, f"Question '{q}' should be blocked for TI")
            self.assertIn("Gobernanza RBAC: Acceso denegado", denial)
            self.assertIn("información financiera", denial)

    def test_non_hr_asking_salaries_and_payroll_blocked(self):
        """Non-HR roles asking for salaries or employee compensation are strictly blocked."""
        salary_questions = [
            "¿Cuáles son los sueldos del personal?",
            "¿Cuánto gana el CTO o directores?",
            "Dame la nómina de remuneraciones",
            "¿Cuáles son los salarios por departamento?"
        ]
        for role in ["Analista Financiero & Comercial", "Ingeniero de Infraestructura & TI", "Economista", "TI"]:
            for q in salary_questions:
                denial = QueryEngine.check_domain_governance(
                    question=q,
                    user_role=role,
                    allowed_tables={"fact_ventas"}
                )
                self.assertIsNotNone(denial, f"Question '{q}' should be blocked for {role}")
                self.assertIn("Gobernanza RBAC: Acceso denegado", denial)
                self.assertIn("salarios, remuneraciones, nóminas", denial)

    def test_admin_never_blocked_by_domain_governance(self):
        """Admin role can query across all domains (financial, IT, HR) without RBAC block."""
        admin_questions = [
            "¿Cuáles son los sueldos del personal?",
            "¿Cuál es la facturación del período?",
            "Estado de servidores y CPU",
            "Compara los ingresos contra los costos por producto y dime cuáles tienen menor margen"
        ]
        for q in admin_questions:
            denial = QueryEngine.check_domain_governance(
                question=q,
                user_role="Administrador",
                allowed_tables={"fact_ventas", "dim_servidores", "dim_empleados"}
            )
            self.assertIsNone(denial, f"Admin should NEVER be blocked by RBAC on question '{q}'")

if __name__ == "__main__":
    unittest.main()
