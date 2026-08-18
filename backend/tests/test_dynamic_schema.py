import unittest
from unittest.mock import MagicMock
from app.services.dynamic_schema import DynamicSchemaPruningService

class TestDynamicSchema(unittest.TestCase):

    def test_economista_role_authorized_tables(self):
        """Verifica que para el rol 'Economista' se devuelvan EXACTAMENTE las 6 tablas autorizadas."""
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.name = "Economista"

        expected_tables = {
            "dim_categorias",
            "dim_productos",
            "dim_clientes",
            "fact_ventas",
            "fact_ingresos_costos",
            "dim_empleados"
        }

        mock_perms = [MagicMock(table_name=tbl, is_allowed=True) for tbl in expected_tables]

        mock_db = MagicMock()
        # Mock Role lookup via db.query(Role).filter(...).first()
        mock_db.query().filter().first.return_value = mock_role
        # Mock RoleTablePermission, RoleColumnPermission, and SemanticCatalog queries
        mock_db.query().filter().all.side_effect = [
            mock_perms,  # table_perms
            [],          # col_perms
            []           # catalog_entries
        ]

        schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=mock_db,
            user_role="Economista",
            connection_id=1,
            is_admin=False
        )

        self.assertEqual(
            schema_info["allowed_tables"],
            expected_tables,
            f"Se esperaban exactamente las tablas {expected_tables}, pero se obtuvo {schema_info['allowed_tables']}"
        )

    def test_economista_role_excludes_ti_tables(self):
        """Verifica que para el rol 'Economista' las tablas de TI NUNCA aparecen en el resultado."""
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.name = "Economista"

        econ_tables = {
            "dim_categorias",
            "dim_productos",
            "dim_clientes",
            "fact_ventas",
            "fact_ingresos_costos",
            "dim_empleados"
        }

        ti_tables = {
            "dim_servidores",
            "fact_incidentes_ti",
            "fact_consumo_recursos"
        }

        mock_perms = [MagicMock(table_name=tbl, is_allowed=True) for tbl in econ_tables]

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_role
        mock_db.query().filter().all.side_effect = [
            mock_perms,  # table_perms
            [],          # col_perms
            []           # catalog_entries
        ]

        schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=mock_db,
            user_role="Economista",
            connection_id=1,
            is_admin=False
        )

        allowed = schema_info["allowed_tables"]
        schema_prompt = schema_info["schema_prompt"]

        for ti_tbl in ti_tables:
            self.assertNotIn(
                ti_tbl,
                allowed,
                f"La tabla de TI '{ti_tbl}' NO debe estar en allowed_tables para el rol Economista"
            )
            self.assertNotIn(
                ti_tbl,
                schema_prompt,
                f"La tabla de TI '{ti_tbl}' NO debe aparecer en schema_prompt para el rol Economista"
            )

    def test_ti_role_authorized_tables(self):
        """Verifica que para el rol 'TI' se devuelvan EXACTAMENTE las 3 tablas autorizadas."""
        mock_role = MagicMock()
        mock_role.id = 2
        mock_role.name = "TI"

        expected_tables = {
            "dim_servidores",
            "fact_incidentes_ti",
            "fact_consumo_recursos"
        }

        mock_perms = [MagicMock(table_name=tbl, is_allowed=True) for tbl in expected_tables]

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_role
        mock_db.query().filter().all.side_effect = [
            mock_perms,  # table_perms
            [],          # col_perms
            []           # catalog_entries
        ]

        schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=mock_db,
            user_role="TI",
            connection_id=1,
            is_admin=False
        )

        self.assertEqual(
            schema_info["allowed_tables"],
            expected_tables,
            f"Se esperaban exactamente las tablas {expected_tables}, pero se obtuvo {schema_info['allowed_tables']}"
        )

    def test_ti_role_excludes_economia_tables(self):
        """Verifica que para el rol 'TI' las tablas de Economía NUNCA aparecen en el resultado."""
        mock_role = MagicMock()
        mock_role.id = 2
        mock_role.name = "TI"

        ti_tables = {
            "dim_servidores",
            "fact_incidentes_ti",
            "fact_consumo_recursos"
        }

        economia_tables = {
            "fact_ventas",
            "dim_clientes",
            "dim_productos"
        }

        mock_perms = [MagicMock(table_name=tbl, is_allowed=True) for tbl in ti_tables]

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_role
        mock_db.query().filter().all.side_effect = [
            mock_perms,  # table_perms
            [],          # col_perms
            []           # catalog_entries
        ]

        schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=mock_db,
            user_role="TI",
            connection_id=1,
            is_admin=False
        )

        allowed = schema_info["allowed_tables"]
        schema_prompt = schema_info["schema_prompt"]

        for econ_tbl in economia_tables:
            self.assertNotIn(
                econ_tbl,
                allowed,
                f"La tabla de Economía '{econ_tbl}' NO debe estar en allowed_tables para el rol TI"
            )
            self.assertNotIn(
                econ_tbl,
                schema_prompt,
                f"La tabla de Economía '{econ_tbl}' NO debe aparecer en schema_prompt para el rol TI"
            )

if __name__ == "__main__":
    unittest.main()
