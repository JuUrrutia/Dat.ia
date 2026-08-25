import unittest
from app.core.database import get_database_url, build_engine_for_connector
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType
from app.modules.chat_engine.ast_validator import ASTValidator, ASTValidationError
from app.modules.catalog.services.catalog_service import CatalogDomainService

class TestPostgresCompatibility(unittest.TestCase):

    def test_postgres_url_generation(self):
        url = get_database_url(
            server="db.corporate.local",
            port=5432,
            user="datia_admin",
            password="secret_password",
            db_name="democratizacion_prod"
        )
        self.assertEqual(url, "postgresql+psycopg://datia_admin:secret_password@db.corporate.local:5432/democratizacion_prod")

    def test_build_engine_for_postgres_connector(self):
        conn = CorporateConnection(
            name="PG Primary Data Warehouse",
            db_type=DatabaseType.POSTGRESQL,
            host="127.0.0.1",
            port=5432,
            database_name="corporate_dw",
            username="analyst",
            encrypted_password="",
            is_active=True
        )
        engine = build_engine_for_connector(conn)
        self.assertIsNotNone(engine)
        self.assertEqual(engine.url.drivername, "postgresql+psycopg")
        self.assertEqual(engine.url.host, "127.0.0.1")
        self.assertEqual(engine.url.database, "corporate_dw")

    def test_ast_validator_postgres_dialect(self):
        sql = "SELECT id, monto, fecha FROM fact_ventas WHERE fecha >= NOW() - INTERVAL '30 days' LIMIT 10;"
        is_valid, secured, meta = ASTValidator.validate_and_secure_sql(
            sql,
            dialect="postgres",
            allowed_tables={"fact_ventas"},
            blocked_columns=set(),
            table_columns={"fact_ventas": ["id", "monto", "fecha"]}
        )
        self.assertTrue(is_valid)
        self.assertIn("fact_ventas", meta["tables_used"])

    def test_ast_validator_blocks_postgres_dml(self):
        sql = "DROP TABLE fact_ventas; SELECT 1;"
        with self.assertRaises(ASTValidationError):
            ASTValidator.validate_and_secure_sql(
                sql,
                dialect="postgres",
                allowed_tables={"fact_ventas"},
                blocked_columns=set()
            )

    def test_heuristic_enrichment_for_postgres_types(self):
        # Numeric / Decimal
        meta_num = CatalogDomainService._heuristic_enrich("fact_ventas", "monto_total", "NUMERIC(14,2)", ["1200.50", "340.00"])
        self.assertIn("Monto Total", meta_num["friendly_name"])
        self.assertIn("SUM", meta_num["business_formula"])

        # Timestamp with time zone
        meta_ts = CatalogDomainService._heuristic_enrich("audit_logs", "created_at", "TIMESTAMP WITH TIME ZONE", ["2026-08-24 12:00:00+00"])
        self.assertIn("Created At", meta_ts["friendly_name"])

        # JSONB
        meta_json = CatalogDomainService._heuristic_enrich("user_profiles", "preferences_json", "JSONB", ["{}"])
        self.assertIn("Preferences Json", meta_json["friendly_name"])

if __name__ == "__main__":
    unittest.main()
