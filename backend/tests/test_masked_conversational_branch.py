"""BRANCH A (conversacional) tambien tiene que enmascarar las columnas MASKED.

`mask_rows` solo se aplicaba en la rama analitica de `engine.py`. La conversacional
corre un grounding query `SELECT * ... LIMIT 20` y pasaba esas filas SIN enmascarar al
LLM y a la respuesta, asi que un RUT/token/API key en claro llegaba al modelo, al
snapshot de auditoria y a los exports PDF/Excel aunque el usuario no tuviera permiso
de lectura de esa columna.

Se reutiliza el patron de fixtures de `test_masked_columns.py` (SQLite temporal +
`MagicMock` de sesion + parcheo de los guards de RBAC) porque `engine.py` ya es
testable de punta a punta sin harness extra.
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from main import app  # noqa: F401  registra los mappers de SQLAlchemy

from app.modules.admin_catalog.models import DatabaseType
from app.modules.chat_engine.engine import QueryEngine
from app.modules.chat_engine.intent_classifier import IntentClassifier


class TestMaskedConversationalBranch(unittest.TestCase):
    """Atraviesa `execute_query` con `response_type == "conversational"`."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        con = sqlite3.connect(self.tmp.name)
        con.execute("CREATE TABLE clientes (nombre TEXT, rut_dni_cliente TEXT)")
        con.execute("INSERT INTO clientes VALUES ('Ana Perez', '12.345.678-9')")
        con.execute("INSERT INTO clientes VALUES ('Luis Soto', '98.765.432-4')")
        con.commit()
        con.close()

        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.tmp.name
        mock_conn.database_name = self.tmp.name
        mock_conn.null_policy = "open"

        self.mock_db = MagicMock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_conn
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_conn
        self.mock_db.query.return_value.order_by.return_value.first.return_value = mock_conn

        # Fuerza BRANCH A: la intencion se clasifica como conversacional y el LLM
        # devuelve algo, para que el motor llegue a `build_conversational_response`
        # con las filas del grounding query.
        self.patches = [
            patch.object(QueryEngine, "get_masked_columns_for_role",
                         classmethod(lambda cls, *a, **k: {"rut_dni_cliente"})),
            patch.object(QueryEngine, "get_blocked_columns_for_role",
                         classmethod(lambda cls, *a, **k: set())),
            patch.object(QueryEngine, "get_allowed_tables_for_role",
                         classmethod(lambda cls, *a, **k: {"clientes"})),
            patch.object(IntentClassifier, "classify_intent",
                         new=classmethod(lambda cls, *a, **k: asyncio.sleep(0, result="conversational"))),
            patch.object(IntentClassifier, "generate_conversational_response",
                         new=classmethod(lambda cls, *a, **k: asyncio.sleep(
                             0, result="Hay 2 clientes registrados en la base."))),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def _run(self):
        return asyncio.run(
            QueryEngine.execute_query(
                question="clientes",
                user_role="Economista",
                is_admin=False,
                db=self.mock_db,
                connection_id=1,
            )
        )

    def test_masked_column_never_reaches_the_conversational_response_in_clear(self):
        response = self._run()

        rows = getattr(response, "data_rows", None)
        self.assertTrue(rows, f"la rama conversacional no devolvio filas: {response}")

        for row in rows:
            self.assertIn("rut_dni_cliente", row)
            self.assertNotIn(
                "12.345.678-9", str(row),
                "el RUT en claro llego a la respuesta conversacional",
            )
            self.assertRegex(
                row["rut_dni_cliente"], r"^\*+\d{3}-\d$",
                f"el RUT no quedo enmascarado: {row['rut_dni_cliente']}",
            )
            self.assertNotIn("98.765.432-4", str(row))

        # Enmascarar no rompe el resto de la fila.
        self.assertEqual(rows[0]["nombre"], "Ana Perez")

    def test_rows_pass_untouched_when_there_are_no_masked_columns(self):
        """Caso normal: sin columnas MASKED la fila debe salir intacta."""
        with patch.object(QueryEngine, "get_masked_columns_for_role",
                          classmethod(lambda cls, *a, **k: set())):
            response = self._run()

        rows = getattr(response, "data_rows", None)
        self.assertTrue(rows, f"la rama conversacional no devolvio filas: {response}")
        values = {r["rut_dni_cliente"] for r in rows}
        self.assertIn("12.345.678-9", values)
        self.assertIn("98.765.432-4", values)


if __name__ == "__main__":
    unittest.main()