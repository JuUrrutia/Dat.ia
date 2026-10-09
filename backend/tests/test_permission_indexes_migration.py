"""Los indices de permisos y catalogo existen en una BD YA desplegada.

Por que estan en un test
------------------------
Los `Index(...)` de `admin_catalog/models.py` solo aplican a las bases creadas
desde cero (`Base.metadata.create_all`). Una instalacion que ya tiene las tablas
nunca los va a tener, y el proyecto no usa Alembic para esto: las columnas nuevas
se resuelven con auto-migracion en `core.database.ensure_schema_migrations`. Este
test es el que cierra ese hueco, porque el fallo que evita (seq scan de la tabla
de permisos en cada query del chat) no se ve en ningun test funcional: todo pasa
igual de lento.

`CREATE INDEX IF NOT EXISTS` es idempotente en PostgreSQL y en SQLite, asi que
llamar dos veces no debe fallar ni cambiar nada.
"""

import os
import sqlite3
import tempfile
import unittest

from sqlalchemy import create_engine, inspect, text

# Los mappers de SQLAlchemy se resuelven por nombre de clase en string
# (`relationship("RoleDomainLink")`), asi que los dos modulos tienen que estar
# importados ANTES de que se configure cualquier mapper. Sin esto:
# `InvalidRequestError: expression 'RoleDomainLink' failed to locate a name`.
import app.modules.auth.models  # noqa: F401
import app.modules.admin_catalog.models  # noqa: F401
from app.core.database import ensure_schema_migrations

ESPERADOS = [
    ("role_table_permissions", "ix_role_table_perm_lookup"),
    ("role_column_permissions", "ix_role_column_perm_lookup"),
    ("semantic_catalog", "ix_semantic_catalog_connection"),
]


class TestEnsureSchemaMigrationsCreatesIndexes(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        self.engine = create_engine(f"sqlite:///{self.path}")

    def tearDown(self):
        self.engine.dispose()
        for suffix in ("", "-journal", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except OSError:
                pass

    def _create_stale_tables(self):
        """Las tablas tal como quedaron ANTES de este cambio: sin ningun indice."""
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE corporate_connections (id INTEGER PRIMARY KEY)"))
            conn.execute(text(
                "CREATE TABLE role_table_permissions (id INTEGER PRIMARY KEY, role_id INTEGER, "
                "connection_id INTEGER, is_allowed BOOLEAN)"
            ))
            conn.execute(text(
                "CREATE TABLE role_column_permissions (id INTEGER PRIMARY KEY, role_id INTEGER, "
                "connection_id INTEGER, column_name VARCHAR(100))"
            ))
            conn.execute(text(
                "CREATE TABLE semantic_catalog (id INTEGER PRIMARY KEY, connection_id INTEGER, "
                "table_name VARCHAR(100), column_name VARCHAR(100))"
            ))

    def test_creates_missing_indexes_on_existing_database(self):
        self._create_stale_tables()

        antes = {i["name"] for i in inspect(self.engine).get_indexes("role_table_permissions")}
        self.assertNotIn("ix_role_table_perm_lookup", antes)

        ensure_schema_migrations(self.engine)

        for tabla, nombre in ESPERADOS:
            with self.subTest(tabla=tabla):
                nombres = {i["name"] for i in inspect(self.engine).get_indexes(tabla)}
                self.assertIn(nombre, nombres, f"{nombre} no se creo en {tabla}")

    def test_is_idempotent(self):
        """Se puede llamar en cada arranque (que es cuando se llama)."""
        self._create_stale_tables()
        ensure_schema_migrations(self.engine)
        ensure_schema_migrations(self.engine)

        for tabla, nombre in ESPERADOS:
            with self.subTest(tabla=tabla):
                nombres = [i["name"] for i in inspect(self.engine).get_indexes(tabla)]
                self.assertEqual(nombres.count(nombre), 1, f"{nombre} quedo duplicado en {tabla}")

    def test_does_not_break_when_permission_tables_are_absent(self):
        """Una BD sin esas tablas no puede reventar el arranque."""
        ensure_schema_migrations(self.engine)  # no hay nada, no debe lanzar


if __name__ == "__main__":
    unittest.main()