"""
Cierres mecanicos de la Fase B. 4 bugs, todos verificados:

  1. catalog_enricher: `SchemaInspector` propaga `SchemaIntrospectionError` y los
     call sites sin try daban 500 crudo. `auto_enrich_catalog` ya lo manejaraba;
     `seed_catalog_heuristics_for_connection` no.
  2. data_compiler.compile_findings: con include_raw_data=False `generator.py`
     vacia data_rows antes de compilar, y los hallazgos desaparecian sin aviso.
  3. connector_service: `X and "y"` en el set de bases de plataforma.
  4. api/deps: `datetime.utcnow()` deprecado -> patron de la linea 64.
"""
import asyncio
import inspect
import os
import sqlite3
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, PropertyMock, patch

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import create_access_token, decode_token_payload
from app.db.init_db import init_db
from app.modules.admin_catalog.models import (
    CorporateConnection,
    DatabaseType,
    SemanticCatalog,
)
from app.modules.admin_catalog.schemas import AutoEnrichRequest, ReportExportData
from app.modules.auth.models import User, UserSession
from app.modules.catalog.services.catalog_enricher import CatalogEnricher
from app.modules.catalog.services.connector_service import ConnectorDomainService
from app.modules.catalog.services.schema_inspector import (
    SchemaInspector,
    SchemaIntrospectionError,
)
from app.modules.reports.data_compiler import ReportDataCompiler


class TestEnrichWithDeadConnection(unittest.TestCase):
    """BUG 1: leer una conexion caida no puede terminar en 500."""

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.db = SessionLocal()
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        self.sqlite_path = tmp.name
        sqlite3.connect(self.sqlite_path).close()
        self.conn = CorporateConnection(
            name=f"dead_conn_{uuid.uuid4().hex[:8]}",
            db_type=DatabaseType.SQLITE,
            host=self.sqlite_path,
            port=0,
            database_name="dead.db",
            is_active=True,
        )
        self.db.add(self.conn)
        self.db.commit()

    def tearDown(self):
        self.db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == self.conn.id
        ).delete(synchronize_session=False)
        self.db.delete(self.conn)
        self.db.commit()
        self.db.close()

    def test_auto_enrich_reports_failure_not_500(self):
        """`SchemaIntrospectionError` Specifically: la conexion caida se reporta."""
        with patch.object(
            SchemaInspector,
            "introspect_connection_metadata",
            side_effect=SchemaIntrospectionError("connection refused"),
        ):
            resp = asyncio.run(
                CatalogEnricher.auto_enrich_catalog(
                    self.db, AutoEnrichRequest(connection_id=self.conn.id)
                )
            )

        self.assertFalse(resp.success, resp.message)
        self.assertEqual(resp.enriched_count, 0)
        self.assertIn("connection refused", resp.message)

    def test_seed_does_not_raise_on_dead_connection(self):
        """La siembra no propaga: sus 3 llamadores ya persistieron la conexion,
        asi que propagar seria un 500 por algo que si se creo."""
        with patch.object(
            SchemaInspector,
            "introspect_connection_metadata",
            side_effect=SchemaIntrospectionError("connection refused"),
        ):
            seeded = CatalogEnricher.seed_catalog_heuristics_for_connection(
                self.db, self.conn.id, self.sqlite_path
            )

        self.assertEqual(seeded, 0)
        self.assertEqual(
            self.db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == self.conn.id
            ).count(),
            0,
        )

    def test_seed_still_seeds_when_readable(self):
        """Contraparte: la guarda no dejo de sembrar."""
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        path = tmp.name
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE ventas (monto INTEGER)")
        con.commit()
        con.close()
        try:
            seeded = CatalogEnricher.seed_catalog_heuristics_for_connection(
                self.db, self.conn.id, path
            )
            self.assertEqual(seeded, 1)
        finally:
            os.unlink(path)


class TestFindingsWithoutRawData(unittest.TestCase):
    """BUG 2: sin datos crudos no hay analisis, y eso se declara."""

    def _data(self, **kw):
        return ReportExportData(question="¿Cuanto vendimos?", **kw)

    def test_no_findings_is_declared_not_silent(self):
        out = ReportDataCompiler.compile_findings(
            self._data(include_raw_data=False)
        )
        self.assertTrue(out, "lista vacia presentada como resultado de un analisis")
        self.assertTrue(
            any("include_raw_data=False" in f for f in out), out
        )

    def test_declaration_appears_when_the_whole_export_dropped_rows(self):
        """Reconstruccion de lo que hace generator.py: vacia data_rows y columnas."""
        payload = {
            "question": "¿Cuanto vendimos?",
            "data_rows": [],
            "data_columns": [],
            "include_raw_data": False,
        }
        out = ReportDataCompiler.compile_findings(ReportExportData(**payload))
        self.assertTrue(out)
        self.assertIn("No se incluyen hallazgos", out[0])

    def test_with_raw_data_still_reports_findings(self):
        out = ReportDataCompiler.compile_findings(
            self._data(
                include_raw_data=True,
                data_rows=[{"monto": 1}],
                data_columns=["monto"],
            )
        )
        self.assertEqual(len(out), 2)
        self.assertIn("1 registros", out[0])

    def test_key_findings_win_over_the_declaration(self):
        out = ReportDataCompiler.compile_findings(
            self._data(
                include_raw_data=False,
                executive_report={"key_findings": ["La venta cayo 12%"]},
            )
        )
        self.assertEqual(out, ["La venta cayo 12%"])


class TestPlatformDbsProtection(unittest.TestCase):
    """BUG 3: la base de metadata no puede caer en DROP DATABASE."""

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.db = SessionLocal()
        self.created = []

    def tearDown(self):
        for c in self.created:
            self.db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == c.id
            ).delete(synchronize_session=False)
            self.db.delete(c)
        self.db.commit()
        self.db.close()

    def _pg_connector(self, database_name):
        conn = CorporateConnection(
            name=f"pg_probe_{uuid.uuid4().hex[:8]}",
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database_name=database_name,
            is_active=True,
            is_uploaded=True,
        )
        self.db.add(conn)
        self.db.commit()
        self.created.append(conn)
        return conn

    def _delete_with_mock_pg(self, database_name):
        conn = self._pg_connector(database_name)
        m_engine = MagicMock()
        with patch("sqlalchemy.create_engine", return_value=m_engine) as create:
            ConnectorDomainService.delete_connector(self.db, conn.id)
        return create

    def test_metadata_db_is_never_dropped(self):
        create = self._delete_with_mock_pg("democratizacion_metadatos")
        create.assert_not_called()

    def test_metadata_db_protected_even_with_empty_metadata_path(self):
        """El caso que rompia: METADATA_DB_PATH vacio + POSTGRES_DB con otro
        nombre. Antes el `and` metia "" en el set y la base quedaba desprotegida."""
        with patch.object(
            type(settings), "METADATA_DB_PATH",
            new_callable=PropertyMock, return_value="",
        ), patch.object(settings, "POSTGRES_DB", "otra_base_de_plataforma"):
            create = self._delete_with_mock_pg("democratizacion_metadatos")
        create.assert_not_called()

    def test_uploaded_dataset_is_still_dropped(self):
        """Contraparte: la proteccion no dejo de borrar los datasets subidos."""
        create = self._delete_with_mock_pg("probe_dataset_subido")
        create.assert_called_once()


class TestTokenSurvivesUtcNowChange(unittest.TestCase):
    """BUG 4: `utcnow()` -> `now(utc)`. Los tokens no pueden invalidarse."""

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.db = SessionLocal()
        self.username = f"utc_token_{uuid.uuid4().hex[:8]}"
        self.user = User(
            username=self.username,
            email=f"{self.username}@test.local",
            hashed_password="x",
            is_admin=False,
            is_active=True,
            must_change_password=False,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.jti = str(uuid.uuid4())
        self.db.add(
            UserSession(user_id=self.user.id, jti=self.jti, is_revoked=False)
        )
        self.db.commit()

    def tearDown(self):
        self.db.query(UserSession).filter(
            UserSession.user_id == self.user.id
        ).delete(synchronize_session=False)
        self.db.delete(self.user)
        self.db.commit()
        self.db.close()

    def test_token_issued_before_still_validates(self):
        """`create_access_token` es tz-aware en core/security.py y no cambio;
        el `now` de deps.py solo compara/escribe last_seen_at. Igual se prueba
        el camino completo: emitir, validar, y que la sesion no se invalide."""
        token = create_access_token(subject=self.user.id, jti=self.jti)
        payload = decode_token_payload(token)
        self.assertIsNotNone(payload)
        self.assertEqual(str(payload["sub"]), str(self.user.id))
        self.assertEqual(payload["jti"], self.jti)

    def test_optional_user_accepts_old_token_and_updates_last_seen(self):
        """El camino de deps.py:148 (antes `utcnow()`) con un token emitido
        antes del cambio."""
        from app.api.deps import get_current_user_optional

        token = create_access_token(subject=self.user.id, jti=self.jti)
        user = get_current_user_optional(db=self.db, token=token)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
        self.db.refresh(self.user)
        self.assertIsNotNone(
            self.db.query(UserSession).filter(
                UserSession.jti == self.jti
            ).first().last_seen_at
        )

    def test_no_deprecated_utcnow_left_in_deps(self):
        from app.api import deps

        self.assertNotIn(
            "datetime.utcnow()", inspect.getsource(deps), "utcnow() deprecado"
        )


if __name__ == "__main__":
    unittest.main()