import unittest
from unittest.mock import MagicMock
from app.services.query_engine import QueryEngine
from app.services.dynamic_schema import DynamicSchemaPruningService

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
        from app.models.permission import ColumnPermissionType
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

if __name__ == "__main__":
    unittest.main()
