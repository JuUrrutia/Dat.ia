"""
Bugs 7-8-10: CREATE DATABASE fallido se tragaba y el conector moría con 201,
colisión de ruta con dos uploads del mismo archivo en el mismo segundo, y
clasificación de rolesTI/Financieros por subcadena en vez de por token.
"""
import io
import os
import re
import time
import uuid
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType
from app.modules.admin_catalog.schemas import CorporateConnectionCreate
from app.modules.catalog.services.connector_service import ConnectorDomainService
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.core.security import create_access_token


def _role_matches_ti(role_name: str) -> bool:
    """Replica exacta de la regla del servicio para poder testearla aislada."""
    tokens = set(re.findall(r"[a-z0-9]+", role_name.lower()))
    return ("ti" in tokens) or ("infraestructura" in tokens)


def _role_matches_fin(role_name: str) -> bool:
    tokens = set(re.findall(r"[a-z0-9]+", role_name.lower()))
    return bool(tokens & {"economista", "financiero"})


class TestConnectorCreateDatabaseFailure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.username == "admin").first()
        self.jti = str(uuid.uuid4())
        self.token = create_access_token(subject=self.user.id, jti=self.jti)
        self.db.add(UserSession(user_id=self.user.id, jti=self.jti, is_revoked=False))
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        for name in ("probe_createdb_falla",):
            self.db.query(CorporateConnection).filter(
                CorporateConnection.name == name).delete()
            self.db.commit()
        self.db.close()

    def test_failed_create_database_does_not_return_201_and_inserts_nothing(self):
        """BUG 7: el `except Exception: pass` se tragaba la falta de privilegio
        CREATEDB y el servicio insertaba igual un CorporateConnection apuntando a
        una base inexistente, respondiendo 201 Created."""
        conn_in = CorporateConnectionCreate(
            name="probe_createdb_falla",
            db_type=DatabaseType.POSTGRESQL,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            database_name="probe_createdb_db",
            username="postgres",
            password="x",
        )

        boom = MagicMock()
        boom.execute.side_effect = RuntimeError("permission denied to create database")

        m_engine = MagicMock()
        m_conn_ctx = MagicMock()
        m_conn_ctx.__enter__.return_value = boom
        m_engine.connect.return_value = m_conn_ctx

        with patch("sqlalchemy.create_engine", return_value=m_engine):
            with self.assertRaises(Exception) as ctx:
                ConnectorDomainService.create_connector(self.db, conn_in)

        self.assertEqual(getattr(ctx.exception, "status_code", None), 502)
        self.assertIsNone(
            self.db.query(CorporateConnection).filter(
                CorporateConnection.name == "probe_createdb_falla").first(),
            "se insertó un conector apuntando a una base que nunca se creó",
        )

    def test_engine_is_disposed_even_on_failure(self):
        """El dispose() también se saltaba en el camino de error."""
        conn_in = CorporateConnectionCreate(
            name="probe_createdb_falla",
            db_type=DatabaseType.POSTGRESQL,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            database_name="probe_createdb_db2",
            username="postgres",
            password="x",
        )
        boom = MagicMock()
        boom.execute.side_effect = RuntimeError("boom")
        m_engine = MagicMock()
        m_conn_ctx = MagicMock()
        m_conn_ctx.__enter__.return_value = boom
        m_engine.connect.return_value = m_conn_ctx

        with patch("sqlalchemy.create_engine", return_value=m_engine):
            with self.assertRaises(Exception):
                ConnectorDomainService.create_connector(self.db, conn_in)

        m_engine.dispose.assert_called_once()

    def test_creation_succeeds_when_database_exists(self):
        """El camino bueno no se rompió: si la base ya existe, se crea el conector."""
        conn_in = CorporateConnectionCreate(
            name="probe_createdb_falla",
            db_type=DatabaseType.POSTGRESQL,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            database_name="probe_createdb_db3",
            username="postgres",
            password="x",
        )
        conn = MagicMock()
        conn.execute.return_value.scalar.return_value = 1  # ya existe
        m_engine = MagicMock()
        m_conn_ctx = MagicMock()
        m_conn_ctx.__enter__.return_value = conn
        m_engine.connect.return_value = m_conn_ctx

        with patch("sqlalchemy.create_engine", return_value=m_engine):
            with patch.object(
                CatalogDomainService, "seed_catalog_heuristics_for_connection"
            ):
                created = ConnectorDomainService.create_connector(self.db, conn_in)

        self.assertIsNotNone(created.id)
        # No se intentó el CREATE DATABASE porque ya existía
        statements = [str(c.args[0]) for c in conn.execute.call_args_list]
        self.assertFalse(any("CREATE DATABASE" in s for s in statements))


class TestUploadPathCollision(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.username == "admin").first()
        self.jti = str(uuid.uuid4())
        self.token = create_access_token(subject=self.user.id, jti=self.jti)
        self.db.add(UserSession(user_id=self.user.id, jti=self.jti, is_revoked=False))
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.names = []

    def tearDown(self):
        for name in self.names:
            self.db.query(CorporateConnection).filter(
                CorporateConnection.name == name).delete()
        self.db.commit()
        self.db.close()

    def _upload_csv(self, filename, name):
        """Sube un CSV forzando la rama SQLite, que es donde se construyen las rutas."""
        csv = b"col_a,col_b\n1,2\n3,4\n"
        from app.core.database import engine as app_engine
        with patch.object(type(app_engine.dialect), "name", "sqlite"):
            return self.client.post(
                "/api/v1/connectors/upload",
                files={"file": (filename, io.BytesIO(csv), "text/csv")},
                data={"name": name},
                headers=self.headers,
            )

    def test_two_uploads_of_same_file_in_same_second_get_distinct_paths(self):
        """BUG 8: `int(time.time())` como nombre de archivo tiene granularidad de
        segundo. Dos uploads de datos.csv en el mismo segundo producían dos
        conectores distintos (datos y datos_1) apuntando al MISMO archivo: el
        segundo import pisaba el primero y borrar uno dejaba al otro apuntando a
        la nada."""
        with patch("app.modules.catalog.services.connector_service.time.time",
                   return_value=1700000000.0):
            r1 = self._upload_csv("datos.csv", "probe-datos-1")
            r2 = self._upload_csv("datos.csv", "probe-datos-2")

        self.assertEqual(r1.status_code, 201, r1.text[:300])
        self.assertEqual(r2.status_code, 201, r2.text[:300])
        self.names = ["probe-datos-1", "probe-datos-2"]

        path1 = r1.json()["host"]
        path2 = r2.json()["host"]
        self.assertNotEqual(
            path1, path2,
            f"los dos conectores apuntan al mismo archivo: {path1}",
        )
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))

        # Y el segundo import NO pisa el contenido del primero: los dos archivos
        # existen y cada uno conserva sus filas.
        import sqlite3
        for p in (path1, path2):
            with sqlite3.connect(p) as c:
                tables = [r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")]
                self.assertTrue(tables, f"{p} no tiene ninguna tabla")
                self.assertEqual(
                    c.execute(f'SELECT COUNT(*) FROM "{tables[0]}"').fetchone()[0], 2,
                    f"contenido inesperado en {p}",
                )

    def test_same_file_uploaded_twice_does_not_alias_after_deletion(self):
        """Borrar un conector no deja al otro apuntando a un archivo inexistente."""
        with patch("app.modules.catalog.services.connector_service.time.time",
                   return_value=1700000100.0):
            r1 = self._upload_csv("alias.csv", "probe-alias-1")
            r2 = self._upload_csv("alias.csv", "probe-alias-2")
        self.assertEqual(r1.status_code, 201, r1.text[:300])
        self.assertEqual(r2.status_code, 201, r2.text[:300])
        self.names = ["probe-alias-1", "probe-alias-2"]

        path1, path2 = r1.json()["host"], r2.json()["host"]
        del_res = self.client.delete(
            f"/api/v1/connectors/{r1.json()['id']}", headers=self.headers)
        self.assertEqual(del_res.status_code, 200, del_res.text[:300])
        self.assertFalse(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2), "borrar un conector se llevó el archivo del otro")


class TestRoleTokenMatching(unittest.TestCase):

    def test_ti_substring_false_positives_are_gone(self):
        """BUG 10: `"ti" in role.name.lower()` es busqueda de subcadena, asi que
        estos roles perdiaban tablas de negocio sin ser de TI."""
        for name in ("Analítica", "Autenticación", "Capital Intelectivo",
                     "Notificaciones", "Política", "Calidad", "Gestión"):
            with self.subTest(role=name):
                self.assertFalse(_role_matches_ti(name), f"'{name}' se clasificó como TI")

    def test_real_ti_roles_still_match(self):
        """Los roles TI de verdad siguen clasificándose como TI."""
        for name in ("TI", "Ingeniero de Infraestructura & TI", "TI Junior"):
            with self.subTest(role=name):
                self.assertTrue(_role_matches_ti(name))

    def test_financial_roles_match_by_token(self):
        self.assertTrue(_role_matches_fin("Economista"))
        self.assertTrue(_role_matches_fin("Analista Financiero & Comercial"))
        self.assertFalse(_role_matches_fin("Analítica"))
        self.assertFalse(_role_matches_fin("Director Ejecutivo (C-Level)"))

    def test_service_source_uses_token_match_not_substring(self):
        """Guardarra contra volver al `in` de subcadena."""
        import inspect
        src = inspect.getsource(ConnectorDomainService.upload_database_file)
        self.assertNotIn('"ti", "infraestructura"]', src)
        self.assertNotIn('k in role.name.lower()', src)