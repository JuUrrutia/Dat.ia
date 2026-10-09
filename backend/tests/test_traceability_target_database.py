"""El SQL de la trazabilidad tiene que decir contra que base se ejecuto.

Sin esto, "copiar consulta SQL" entrega un texto que no se puede reproducir: las
mismas tablas (`movimientos`, `fact_ventas`) existen en varias bases del mismo
servidor, y pegado en otra falla con `no existe la relacion ...`. El usuario
lee ese error como "no hay datos" en vez de "estabas en la base equivocada".
"""
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.modules.admin_catalog.models import CorporateConnection
import app.modules.admin_catalog.models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.telemetry_audit.models  # noqa: F401
import app.modules.chat_engine.models  # noqa: F401
import app.modules.chat_engine.schemas as chat_schemas


class TestTraceabilityCarriesTargetDatabase(unittest.TestCase):

    def setUp(self):
        self.eng = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=self.eng)
        self.db = sessionmaker(bind=self.eng)()

    def tearDown(self):
        self.db.close()
        self.eng.dispose()

    def _pg_conn(self, db_name):
        c = CorporateConnection(
            name=f"Conn {db_name}", db_type="POSTGRESQL", host="localhost",
            port=5432, database_name=db_name, username="postgres",
            encrypted_password="x", is_active=True, is_uploaded=False,
        )
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    def _sqlite_conn(self, db_name, path):
        c = CorporateConnection(
            name=f"Conn {db_name}", db_type="SQLITE", host=path,
            port=0, database_name=db_name, username="admin",
            encrypted_password="", is_active=True, is_uploaded=False,
        )
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    # --------------------------------------------------------------
    def test_schema_accepts_target_database(self):
        t = chat_schemas.TraceabilityAudit(
            sql_executed="SELECT 1", execution_time_ms=1, rows_returned=1,
            validation_status="APROBADO", schema_tables_used=["movimientos"],
            explanation="x", target_database="movimientos_maxi3d_sql",
        )
        self.assertEqual(t.target_database, "movimientos_maxi3d_sql")

    def test_target_database_is_optional_and_defaults_to_none(self):
        """Sin el dato no se inventa: `None` es 'no lo se', no la base actual."""
        t = chat_schemas.TraceabilityAudit(
            sql_executed="SELECT 1", execution_time_ms=1, rows_returned=1,
            validation_status="APROBADO", schema_tables_used=[], explanation="x",
        )
        self.assertIsNone(t.target_database)

    def test_executor_meta_carries_the_database_name(self):
        """`SQLExecutor` resuelve el nombre desde el conector, no desde settings.

        Va contra un SQLite temporal y no contra el PostgreSQL real: lo que se
        verifica es que el nombre de la base viaje en `meta`, y eso no depende
        del motor. Asi el test no necesita credenciales ni una base viva.
        """
        import asyncio
        import os
        import sqlite3
        import tempfile

        from app.modules.chat_engine.sql_executor import SQLExecutor

        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        con = sqlite3.connect(tmp.name)
        con.execute("CREATE TABLE movimientos (periodo TEXT)")
        con.execute("INSERT INTO movimientos VALUES ('2026-07'), ('2026-08')")
        con.commit()
        con.close()

        try:
            conn = self._sqlite_conn("movimientos_demo", tmp.name)
            rows, sql, meta, healed, label = asyncio.run(
                SQLExecutor.execute_with_self_healing(
                    target_db_path=conn,
                    question="movimientos por periodo",
                    initial_sql="SELECT periodo FROM movimientos ORDER BY periodo",
                    allowed_tables={"movimientos"},
                    blocked_columns=set(),
                    table_columns_map={"movimientos": ["periodo"]},
                    dialect="sqlite",
                )
            )
            self.assertEqual(meta["target_database"], "movimientos_demo")
            self.assertEqual([r["periodo"] for r in rows], ["2026-07", "2026-08"])
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)


if __name__ == "__main__":
    unittest.main()