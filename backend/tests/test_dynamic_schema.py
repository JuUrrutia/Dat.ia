import time
import unittest
from unittest.mock import MagicMock
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

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

    def test_relevance_pruning_for_product_query(self):
        """Verifica que para una consulta sobre productos e ingresos se seleccionen solo las tablas relevantes."""
        allowed_tables = {
            "dim_categorias", "dim_clientes", "dim_empleados", "dim_productos",
            "dim_servidores", "fact_consumo_recursos", "fact_incidentes_ti",
            "fact_ingresos_costos", "fact_ventas"
        }
        query = "Compara los ingresos contra los costos por producto y dime cuáles tienen menor margen"
        
        # Test ranking directly
        selected = DynamicSchemaPruningService.rank_relevant_tables(
            allowed_tables=allowed_tables,
            query=query,
            catalog_entries=[],
            target_db_target=None
        )
        self.assertIn("dim_productos", selected)
        self.assertNotIn("dim_servidores", selected)
        self.assertNotIn("fact_incidentes_ti", selected)
        self.assertNotIn("fact_consumo_recursos", selected)

    def test_formula_compaction_filters_fake_formulas(self):
        """Verifica que fórmulas con 'Columna directa' o sin cálculos matemáticos sean ignoradas en el prompt."""
        mock_db = MagicMock()
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.name = "Admin"
        mock_db.query().filter().first.return_value = mock_role

        mock_cat_real = MagicMock(
            table_name="fact_ventas",
            column_name="margen",
            friendly_name="Margen de Ganancia",
            business_formula="monto_total - costo_total",
            description="Margen real",
            synonyms=""
        )
        mock_cat_fake = MagicMock(
            table_name="fact_ventas",
            column_name="estado",
            friendly_name="Estado Venta",
            business_formula="Columna directa",
            description="Registro de datos tipo VARCHAR",
            synonyms=""
        )
        mock_perms = [MagicMock(table_name="fact_ventas", is_allowed=True)]

        mock_db.query().filter().all.side_effect = [
            mock_perms,
            [],
            [mock_cat_real, mock_cat_fake]
        ]

        schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=mock_db,
            user_role="Admin",
            connection_id=1,
            is_admin=False,
            query="ventas"
        )
        prompt = schema_info["schema_prompt"]
        self.assertIn("monto_total - costo_total", prompt)
        self.assertNotIn("Columna directa", prompt)
        self.assertNotIn("Registro de datos tipo", prompt)

    def test_schema_cache_ttl_and_invalidation(self):
        """La cache de schema se puebla, se invalida por conexion y se vacia entera."""
        DynamicSchemaPruningService.invalidate_schema_cache()
        self.assertEqual(len(DynamicSchemaPruningService._schema_cache), 0)

        # Se siembra a mano una entrada en la cache
        key = "1:1:Economista:False"
        dummy_result = {"schema_prompt": "Prompt Test", "allowed_tables": {"fact_ventas"}, "blocked_columns": set()}
        DynamicSchemaPruningService._schema_cache[key] = (time.time(), dummy_result)

        self.assertIn(key, DynamicSchemaPruningService._schema_cache)

        # Invalidacion selectiva por conexion
        DynamicSchemaPruningService.invalidate_schema_cache(connection_id=1)
        self.assertNotIn(key, DynamicSchemaPruningService._schema_cache)

if __name__ == "__main__":
    unittest.main()

