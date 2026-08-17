import unittest
from unittest.mock import MagicMock
from app.services.query_engine import QueryEngine, ALL_TABLES, DOMAIN_TABLES
from app.services.dynamic_schema import DynamicSchemaPruningService

class TestRBACGovernance(unittest.TestCase):

    def test_admin_gets_all_tables(self):
        res = QueryEngine.get_allowed_tables_for_role("Administrador", is_admin=True, db=None)
        self.assertEqual(res, ALL_TABLES)

    def test_role_id_none_non_admin_db_active_fails_closed(self):
        """
        Non-admin user with role_id=None and active DB session must NOT get full catalog access or fallback.
        It should return empty set (fail closed).
        """
        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=None,
            connection_id=1
        )
        self.assertEqual(res, set(), "Unassigned role_id=None with active DB must return empty set")

    def test_db_revoked_permissions_returns_empty_set(self):
        """
        When DB is active and a role has 0 allowed tables configured in DB,
        it must return empty set and NOT fall back to DOMAIN_TABLES.
        """
        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = []

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=10,
            connection_id=1
        )
        self.assertEqual(res, set(), "Revoked permissions in DB must return set(), not DOMAIN_TABLES fallback")

    def test_db_exception_fails_closed(self):
        """
        When DB query raises an Exception, system must fail closed (return empty set).
        """
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database connection lost")

        res = QueryEngine.get_allowed_tables_for_role(
            user_role="Economista",
            is_admin=False,
            db=mock_db,
            role_id=10,
            connection_id=1
        )
        self.assertEqual(res, set(), "DB Exception must fail closed by returning set()")

    def test_offline_mode_fallback_when_db_is_none(self):
        """
        When db is None (offline demo mode), fallback to DOMAIN_TABLES should function for demo roles.
        """
        res_econ = QueryEngine.get_allowed_tables_for_role("Economista", is_admin=False, db=None)
        self.assertEqual(res_econ, DOMAIN_TABLES["Economía & Finanzas"])

        res_ti = QueryEngine.get_allowed_tables_for_role("TI", is_admin=False, db=None)
        self.assertEqual(res_ti, DOMAIN_TABLES["Tecnología & TI"])

        res_usuario = QueryEngine.get_allowed_tables_for_role("Usuario", is_admin=False, db=None)
        self.assertEqual(res_usuario, set())

if __name__ == "__main__":
    unittest.main()
