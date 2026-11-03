"""
Tests de los arreglos de CatalogEnricher y de la dependencia de must_change_password.

Cubre:
  1. Un enrich que no puede leer la conexión NO devuelve success=True.
  2. Una descripción curada por un admin NO se pisa en un enrich posterior.
  3. Dos columnas homónimas en schema1/schema2 NO colisionan.
  4. must_change_password realmente bloquea la API.
"""
import os
import sqlite3
import tempfile
import unittest
import uuid
import asyncio
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.db.init_db import init_db
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType, SemanticCatalog
from app.modules.admin_catalog.schemas import AutoEnrichRequest
from app.modules.auth.models import User, UserSession, Role
from app.modules.catalog.services.catalog_enricher import CatalogEnricher
from app.modules.catalog.services.schema_inspector import SchemaInspector



def _run_enrich(db, *args, **kwargs):
    """`auto_enrich_catalog` es async; los tests lo esperan sin ceremony."""
    return asyncio.run(CatalogEnricher.auto_enrich_catalog(db, *args, **kwargs))
def _table_meta(schema, table, columns):
    return {
        "schema_name": schema,
        "table_name": table,
        "row_count": 1,
        "columns": [
            {"name": c, "data_type": "TEXT", "is_pk": False,
             "is_nullable": True, "default_value": None, "sample_values": []}
            for c in columns
        ],
    }


class TestCatalogEnricher(unittest.TestCase):

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
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("CREATE TABLE ventas (monto INTEGER, fecha TEXT)")
        conn.commit()
        conn.close()

        self.conn = CorporateConnection(
            name=f"enrich_test_{uuid.uuid4().hex[:8]}",
            db_type=DatabaseType.SQLITE,
            host=self.sqlite_path,
            port=0,
            database_name=os.path.basename(self.sqlite_path),
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
        try:
            os.unlink(self.sqlite_path)
        except OSError:
            pass

    def _items(self):
        return self.db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == self.conn.id
        ).all()

    # ---------------------------------------------------------------- BUG 1

    def test_unreadable_connection_does_not_report_success(self):
        """No se pudo leer la conexión -> success=False, no 'enriquecido: 0 campos'."""
        with patch.object(
            SchemaInspector, "introspect_connection_metadata",
            side_effect=RuntimeError("connection refused"),
        ):
            resp = _run_enrich(
                self.db, AutoEnrichRequest(connection_id=self.conn.id)
            )

        self.assertFalse(resp.success, resp.message)
        self.assertEqual(resp.enriched_count, 0)
        self.assertIn("connection refused", resp.message)

    def test_empty_metadata_does_not_report_success(self):
        """Una introspection que devuelve [] no se reporta como éxito vacío."""
        with patch.object(
            SchemaInspector, "introspect_connection_metadata", return_value=[]
        ):
            resp = _run_enrich(
                self.db, AutoEnrichRequest(connection_id=self.conn.id)
            )

        self.assertFalse(resp.success, resp.message)
        self.assertEqual(resp.enriched_count, 0)

    def test_successful_enrich_reports_true_with_count(self):
        """Contraparte: cuando sí se lee y se enriquece, sigue siendo success=True."""
        resp = _run_enrich(
            self.db, AutoEnrichRequest(connection_id=self.conn.id)
        )
        self.assertTrue(resp.success, resp.message)
        self.assertEqual(resp.enriched_count, 2)

        # Segunda corrida: nada pendiente, y NO se afirma haber enriquecido nada.
        resp2 = _run_enrich(
            self.db, AutoEnrichRequest(connection_id=self.conn.id)
        )
        self.assertTrue(resp2.success, resp2.message)
        self.assertEqual(resp2.enriched_count, 0)
        self.assertIn("No se modificó ningún campo", resp2.message)

    # ---------------------------------------------------------------- BUG 2

    def test_admin_curated_description_is_not_overwritten(self):
        """Una descripción escrita por un admin sobrevive al enrich, aun con el flag True."""
        curated = SemanticCatalog(
            connection_id=self.conn.id,
            schema_name="main",
            table_name="ventas",
            column_name="monto",
            friendly_name="Monto NETO de venta",
            description="Descripción escrita a mano por el administrador del catálogo.",
            synonyms="neto",
            business_formula="SUM(monto) - descuentos",
            # El seeder marca todo con True: el flag NO distingue humano de máquina.
            is_ai_generated=True,
        )
        self.db.add(curated)
        self.db.commit()

        resp = _run_enrich(
            self.db, AutoEnrichRequest(connection_id=self.conn.id)
        )
        self.assertTrue(resp.success, resp.message)

        after = self.db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == self.conn.id,
            SemanticCatalog.table_name == "ventas",
            SemanticCatalog.column_name == "monto",
        ).first()
        self.assertEqual(after.description, curated.description)
        self.assertEqual(after.friendly_name, curated.friendly_name)
        self.assertEqual(after.business_formula, curated.business_formula)
        self.assertEqual(after.synonyms, "neto")
        # No se contó como enriquecido: no se tocó.
        self.assertEqual(resp.enriched_count, 1)  # solo la columna `fecha`

    def test_empty_fields_are_still_filled(self):
        """El enrich sigue rellenando lo que está vacío."""
        partial = SemanticCatalog(
            connection_id=self.conn.id,
            schema_name="main",
            table_name="ventas",
            column_name="monto",
            description="Solo esto lo escribió alguien",
            is_ai_generated=True,
        )
        self.db.add(partial)
        self.db.commit()

        _run_enrich(
            self.db, AutoEnrichRequest(connection_id=self.conn.id)
        )

        after = self.db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == self.conn.id,
            SemanticCatalog.table_name == "ventas",
            SemanticCatalog.column_name == "monto",
        ).first()
        self.assertEqual(after.description, "Solo esto lo escribió alguien")
        self.assertTrue(after.friendly_name)   # estaba vacío -> se rellenó
        self.assertTrue(after.business_formula)

    # ---------------------------------------------------------------- BUG 3

    def test_homonym_columns_in_different_schemas_do_not_collide(self):
        """schema1.ventas y schema2.ventas son columnas distintas."""
        meta = [
            _table_meta("schema1", "ventas", ["monto"]),
            _table_meta("schema2", "ventas", ["monto"]),
        ]
        with patch.object(
            SchemaInspector, "introspect_connection_metadata", return_value=meta
        ):
            _run_enrich(
                self.db, AutoEnrichRequest(connection_id=self.conn.id)
            )

        rows = self._items()
        self.assertEqual(len(rows), 2, [(r.schema_name, r.column_name) for r in rows])
        self.assertEqual({r.schema_name for r in rows}, {"schema1", "schema2"})

        # Una segunda pasada no debe colapsar una sobre la otra ni duplicar.
        with patch.object(
            SchemaInspector, "introspect_connection_metadata", return_value=meta
        ):
            _run_enrich(
                self.db, AutoEnrichRequest(connection_id=self.conn.id)
            )
        self.assertEqual(len(self._items()), 2)

    def test_lookup_is_case_insensitive(self):
        """Postgres devuelve minúsculas y el catálogo puede tener mayúsculas."""
        meta = [_table_meta("schema1", "VENTAS", ["Monto"])]
        with patch.object(
            SchemaInspector, "introspect_connection_metadata", return_value=meta
        ):
            _run_enrich(
                self.db, AutoEnrichRequest(connection_id=self.conn.id)
            )
        # El motor normalizó a minúscula el mismo objeto.
        lower_meta = [_table_meta("schema1", "ventas", ["monto"])]
        with patch.object(
            SchemaInspector, "introspect_connection_metadata", return_value=lower_meta
        ):
            resp = _run_enrich(
                self.db, AutoEnrichRequest(connection_id=self.conn.id)
            )
        self.assertEqual(len(self._items()), 1, "el case distinto duplicó la columna")
        self.assertEqual(resp.enriched_count, 0)


class TestMustChangePasswordEnforcement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.username = f"mcp_test_{uuid.uuid4().hex[:8]}"
        role = self.db.query(Role).filter(Role.name == "Usuario").first()
        self.user = User(
            username=self.username,
            email=f"{self.username}@test.local",
            hashed_password=get_password_hash("Password123!"),
            is_admin=False,
            is_active=True,
            role_id=role.id if role else None,
            failed_login_attempts=0,
            must_change_password=True,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        jti = str(uuid.uuid4())
        self.db.add(UserSession(user_id=self.user.id, jti=jti, is_revoked=False))
        self.db.commit()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(subject=self.user.id, jti=jti)}"
        }

    def tearDown(self):
        self.db.query(UserSession).filter(
            UserSession.user_id == self.user.id
        ).delete(synchronize_session=False)
        self.db.delete(self.user)
        self.db.commit()
        self.db.close()

    def test_temp_password_user_is_blocked_on_api(self):
        """Con must_change_password=True, el resto de la API responde 403."""
        resp = self.client.get("/api/v1/catalog/", headers=self.headers)
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertIn("cambiar tu contraseña", resp.json()["detail"])

        resp_admin = self.client.get("/api/v1/auth/users", headers=self.headers)
        self.assertEqual(resp_admin.status_code, 403)

    def test_user_can_still_reach_me_and_change_password(self):
        """`/auth/me` y `/auth/change-password` quedan accesibles, si no es un deadlock."""
        me = self.client.get("/api/v1/auth/me", headers=self.headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertTrue(me.json()["must_change_password"])

        change = self.client.post("/api/v1/auth/change-password", headers=self.headers, json={
            "old_password": "Password123!",
            "new_password": "NuevaClave123!",
        })
        self.assertEqual(change.status_code, 200, change.text)

        # Y con el flag limpio vuelve a usar la API.
        self.db.expire_all()
        self.assertFalse(self.db.query(User).filter(User.id == self.user.id).first().must_change_password)
        after = self.client.get("/api/v1/catalog/", headers=self.headers)
        self.assertEqual(after.status_code, 200, after.text)


if __name__ == "__main__":
    unittest.main()
