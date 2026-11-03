"""
La migracion que abre `audit_logs.validation_status` a NULL.

Corre sobre una base temporal de verdad: se construye la tabla con el DDL viejo
(NOT NULL, como la de un despliegue ya existente), se la migra, y se verifica que
los datos que ya estaban siguen intactos. Esto es lo que un `ALTER` a mano sobre el
modelo no cubre: el modelo solo decide como se crea la tabla nueva.
"""
import os
import tempfile
import unittest

from sqlalchemy import create_engine, inspect, text


LEGACY_DDL = """CREATE TABLE audit_logs (
\tid INTEGER NOT NULL,
\ttimestamp DATETIME,
\tuser_id INTEGER,
\tusername VARCHAR(50) NOT NULL,
\tuser_role VARCHAR(50),
\tquestion_prompt TEXT NOT NULL,
\tsql_generated TEXT,
\tvalidation_status VARCHAR(50) NOT NULL,
\ttarget_database VARCHAR(100),
\texecution_time_ms INTEGER,
\trows_returned INTEGER,
\terror_message TEXT,
\tresult_snapshot TEXT,
\tPRIMARY KEY (id)
)"""


class TestValidationStatusMigration(unittest.TestCase):

    def _legacy_db(self, path: str):
        """Base con el esquema de un despliegue previo (NOT NULL) y datos en ella."""
        engine = create_engine(f"sqlite:///{path}")
        with engine.begin() as conn:
            conn.execute(text(LEGACY_DDL))
            conn.execute(text("CREATE INDEX ix_audit_logs_id ON audit_logs (id)"))
            conn.execute(text("CREATE INDEX ix_audit_logs_timestamp ON audit_logs (timestamp)"))
            conn.execute(text(
                "INSERT INTO audit_logs (id, timestamp, username, question_prompt, validation_status) "
                "VALUES (1, '2024-01-01 00:00:00', 'admin', 'consulta vieja', 'APROBADO')"
            ))
            conn.execute(text(
                "INSERT INTO audit_logs (id, timestamp, username, question_prompt, validation_status) "
                "VALUES (2, '2024-01-02 00:00:00', 'ti', 'consulta rechazada', 'RECHAZADO_RBAC')"
            ))
        return engine

    def _migrate(self, engine):
        from app.core.database import ensure_schema_migrations
        ensure_schema_migrations(engine)

    def test_migration_opens_the_column_and_keeps_the_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.db")
            engine = self._legacy_db(path)

            before = {c["name"]: c for c in inspect(engine).get_columns("audit_logs")}
            self.assertFalse(before["validation_status"]["nullable"], "el DDL de prueba no es NOT NULL")

            self._migrate(engine)

            after = {c["name"]: c for c in inspect(engine).get_columns("audit_logs")}
            self.assertTrue(after["validation_status"]["nullable"], "la migracion no abrio la columna")
            self.assertEqual(set(after), set(before), "la migracion no debe agregar ni quitar columnas")

            with engine.begin() as conn:
                rows = conn.execute(text(
                    "SELECT id, username, question_prompt, validation_status FROM audit_logs ORDER BY id"
                )).fetchall()
            self.assertEqual(len(rows), 2, "la migracion perdio filas")
            self.assertEqual(rows[0][3], "APROBADO")
            self.assertEqual(rows[1][3], "RECHAZADO_RBAC")

            # Y ahora se puede insertar el valor honesto, que antes reventaba.
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO audit_logs (id, username, question_prompt, validation_status) "
                    "VALUES (3, 'usuario', 'sin trazabilidad', NULL)"
                ))
                val = conn.execute(text(
                    "SELECT validation_status FROM audit_logs WHERE id = 3"
                )).scalar()
            self.assertIsNone(val)

            # Los indices se reconstruyeron y siguen sirviendo.
            idx = {i["name"] for i in inspect(engine).get_indexes("audit_logs")}
            self.assertIn("ix_audit_logs_id", idx)
            self.assertIn("ix_audit_logs_timestamp", idx)
            engine.dispose()

    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.db")
            engine = self._legacy_db(path)
            self._migrate(engine)
            self._migrate(engine)   # segunda pasada: no debe hacer nada ni romper nada
            self._migrate(engine)

            with engine.begin() as conn:
                rows = conn.execute(text(
                    "SELECT id, validation_status FROM audit_logs ORDER BY id"
                )).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual([r[1] for r in rows], ["APROBADO", "RECHAZADO_RBAC"])
            cols = {c["name"]: c for c in inspect(engine).get_columns("audit_logs")}
            self.assertTrue(cols["validation_status"]["nullable"])
            engine.dispose()

    def test_migration_on_an_already_migrated_db_is_a_noop(self):
        """Base creada por el modelo nuevo: la migracion no la toca."""
        import app.modules.telemetry_audit.models  # noqa: F401 (registra la tabla)
        import app.modules.auth.models  # noqa: F401
        from app.core.database import Base

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fresh.db")
            engine = create_engine(f"sqlite:///{path}")
            Base.metadata.create_all(engine, tables=[
                app.modules.telemetry_audit.models.AuditLog.__table__
            ])
            self._migrate(engine)
            cols = {c["name"]: c for c in inspect(engine).get_columns("audit_logs")}
            self.assertTrue(cols["validation_status"]["nullable"])
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO audit_logs (username, question_prompt, validation_status) "
                    "VALUES ('u', 'q', NULL)"
                ))
            engine.dispose()

    def test_pg_statement_is_the_documented_one(self):
        """En Postgres (que es lo que corre Docker) la via es un ALTER, no un rebuild.

        No se puede ejecutar contra un PG real desde este test, asi que se verifica
        la cadena que el codigo arma: es el ALTER ... DROP NOT NULL y no otra cosa.
        """
        import inspect as pyinspect
        from app.core import database as db_module

        src = pyinspect.getsource(db_module.ensure_schema_migrations)
        self.assertIn("ALTER COLUMN validation_status DROP NOT NULL", src)
        self.assertIn('if is_pg:', src)


if __name__ == "__main__":
    unittest.main()
