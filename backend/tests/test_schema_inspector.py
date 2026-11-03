"""SchemaInspector no puede reportar un fallo de conexion como "0 tablas".

Escenario real: password mal descifrada, Postgres caido, o un usuario sin
USAGE sobre el schema. `introspect_connection_metadata` se tragaba la excepcion
y devolvia `[]`, que es indistinguible de una base vacia. El diccionario
respondia HTTP 200 con `DataDictionaryResponse(total_tables=0)` y el frontend
le mostraba al usuario "esta base no tiene tablas".

El mismo archivo (y el mismo patron) tiene el bug del engine sin dispose():
`core/database.connector_engine` existe exactamente para eso y ya lo usan
sql_executor.py y dynamic_schema.py.
"""

import inspect
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.modules.admin_catalog.models import DatabaseType
from app.modules.catalog.services import schema_inspector as si
from app.modules.catalog.services.schema_inspector import SchemaInspector, SchemaIntrospectionError


class TestConnectionFailureIsNotAnEmptyDatabase(unittest.TestCase):
    def test_postgres_connection_failure_raises_instead_of_returning_empty_list(self):
        conn = MagicMock()
        conn.db_type = DatabaseType.POSTGRESQL
        conn.name = "Produccion"
        conn.is_uploaded = False

        import app.core.database as core_db

        def boom(_conn):
            raise OperationalErrorShim("could not connect to server: connection refused")

        with patch.object(core_db, "connector_engine", boom):
            with self.assertRaises(SchemaIntrospectionError) as ctx:
                SchemaInspector.introspect_connection_metadata(conn)

        self.assertIn("Produccion", str(ctx.exception))

    def test_the_error_message_does_not_claim_the_database_is_empty(self):
        conn = MagicMock()
        conn.db_type = DatabaseType.POSTGRESQL
        conn.name = "Produccion"
        conn.is_uploaded = False

        import app.core.database as core_db

        def boom(_conn):
            raise OperationalErrorShim("password authentication failed")

        with patch.object(core_db, "connector_engine", boom):
            with self.assertRaises(SchemaIntrospectionError) as ctx:
                SchemaInspector.introspect_connection_metadata(conn)

        msg = str(ctx.exception).lower()
        self.assertNotIn("no tiene tablas", msg)
        self.assertNotIn("0 tablas", msg)

    def test_schema_introspection_error_is_a_distinct_exception_type(self):
        """El caller tiene que poder distinguirlo de un error de negocio."""
        self.assertTrue(issubclass(SchemaIntrospectionError, Exception))
        self.assertFalse(issubclass(SchemaIntrospectionError, AssertionError))


class OperationalErrorShim(Exception):
    pass


class TestSqliteResourceIsClosed(unittest.TestCase):
    """`with sqlite3.connect(...)` es un context manager de TRANSACCION, no de
    recurso: cierra el commit, no el handle del fichero."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        c.execute("INSERT INTO t VALUES (1, 'a')")
        c.commit()
        c.close()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def test_unreadable_sqlite_file_raises_rather_than_returning_empty(self):
        fd, junk_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        with open(junk_path, "wb") as fh:
            fh.write(b"esto no es una base de datos" * 100)
        try:
            with self.assertRaises(SchemaIntrospectionError):
                SchemaInspector.introspect_connection_metadata(None, junk_path)
        finally:
            os.remove(junk_path)

    def test_sqlite_source_uses_closing_not_bare_connect(self):
        src = inspect.getsource(SchemaInspector.introspect_connection_metadata)
        self.assertIn(
            "closing(sqlite3.connect(", src,
            "sigue el `with sqlite3.connect(...)`, que no cierra el recurso",
        )

    def test_valid_sqlite_file_still_introspects(self):
        meta = SchemaInspector.introspect_connection_metadata(None, self.db_path)
        names = [t["table_name"] for t in meta]
        self.assertIn("t", names)
        self.assertEqual(meta[0]["row_count"], 1)


class TestPostgresEngineIsDisposed(unittest.TestCase):
    def test_introspection_uses_connector_engine_not_build_engine_for_connector(self):
        src = inspect.getsource(SchemaInspector.introspect_connection_metadata)
        self.assertIn(
            "connector_engine", src,
            "la rama Postgres sigue usando build_engine_for_connector, que deja "
            "el pool de sockets huerfano",
        )
        self.assertNotIn("eng = build_engine_for_connector", src)

    def test_connector_engine_is_the_shared_context_manager(self):
        """Verifica que el helper realmente dispone el engine al salir."""
        from contextlib import contextmanager
        disposed = []

        @contextmanager
        def fake(_conn):
            eng = MagicMock()
            try:
                yield eng
            finally:
                disposed.append(True)

        import app.core.database as core_db
        original = core_db.connector_engine
        core_db.connector_engine = fake
        try:
            conn = MagicMock()
            conn.db_type = DatabaseType.POSTGRESQL
            conn.name = "X"
            conn.is_uploaded = False
            try:
                SchemaInspector.introspect_connection_metadata(conn)
            except Exception:
                # Da igual si la introspeccion falla contra el MagicMock:
                # lo que se verifica es que el engine se libero igual.
                pass
        finally:
            core_db.connector_engine = original

        self.assertEqual(len(disposed), 1, "el engine no se libero al salir de la introspeccion")


if __name__ == "__main__":
    unittest.main()