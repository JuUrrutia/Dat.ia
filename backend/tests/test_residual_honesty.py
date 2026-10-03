"""Residuales de honestidad: la remediacion, la resolucion de conexion y el mapa
de enriquecimiento semantico.

1. `engine.execute_query` descartaba el retorno de `NullManagerService.apply_null_policy`.
   El servicio ya devuelve `status: "no_op"` / `rows_affected: 0` cuando no
   remedio nada, pero el chat miraba el exito viejo: el usuario clickeaba
   "eliminar nulos", la base no se tocaba y la respuesta decia
   "Tratamiento de nulos aplicado".

2. `SchemaInspector.resolve_connection_db_path` con un `connection_id` explicito e
   inexistente caia en silencio a "la conexion no-uploadada": el caller terminaba
   introspeccionando OTRA base creyendola la que pidio (mismo criterio que ya
   corrijo `create_catalog_item`).

3. `get_data_dictionary` armaba `catalog_map` por tabla+columna sin `schema_name`:
   columnas homonimas de `public` y `priv` colisionaban y una se llevaba la
   descripcion de la otra.
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.modules.admin_catalog.models import DatabaseType, SemanticCatalog
from app.modules.catalog.services import catalog_service as cs
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.modules.catalog.services.schema_inspector import SchemaInspector
from app.modules.chat_engine.engine import QueryEngine


def _conn_record(cid, name="conn"):
    rec = MagicMock()
    rec.id = cid
    rec.name = name
    rec.db_type = DatabaseType.SQLITE
    rec.is_active = True
    return rec


# ---------------------------------------------------------------- bug 1

class _NullDbFixture(unittest.TestCase):
    """Base SQLite temporal con 2 filas con nulos, como el resto de la suite."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE test_sales (id INTEGER PRIMARY KEY, category TEXT, amount REAL)")
        conn.executemany(
            "INSERT INTO test_sales VALUES (?, ?, ?)",
            [(1, "Electronics", 100.0), (2, None, 200.0), (3, "Books", 50.0)],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def _chat(self):
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path
        mock_conn.null_policy = "open"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conn
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_conn
        mock_db.query.return_value.order_by.return_value.first.return_value = mock_conn

        return asyncio.run(QueryEngine.execute_query(
            question="Tratar nulos en test_sales (eliminar registros con nulos) para la consulta: SELECT * FROM test_sales",
            user_role="Administrador",
            is_admin=True,
            db=mock_db,
            connection_id=1,
            conversation_history=[
                {"question": "SELECT * FROM test_sales", "sql": "SELECT * FROM test_sales"}
            ],
        ))


class TestChatReportsNullRemediationResult(_NullDbFixture):
    def test_no_op_is_communicated_instead_of_claiming_success(self):
        no_op = {
            "status": "no_op",
            "policy": "delete_rows",
            "rows_affected": 0,
            "message": "No se detectaron valores nulos: no había nada que remediar.",
        }
        with patch("app.modules.chat_engine.engine.NullManagerService.apply_null_policy", return_value=no_op):
            response = self._chat()

        text = response.conversational_response
        self.assertIn("No se remedió ningún valor nulo", text)
        self.assertIn("no había nada que remediar", text)
        self.assertNotIn(
            "Tratamiento de nulos",
            text,
            "el banner de exito no puede seguir apareciendo cuando no se remedio nada",
        )

    def test_zero_rows_with_success_status_is_also_not_claimed_as_applied(self):
        """El `status` viejo Sayba success con 0 filas: el aviso no depende solo de el."""
        with patch(
            "app.modules.chat_engine.engine.NullManagerService.apply_null_policy",
            return_value={"status": "success", "policy": "mode", "rows_affected": 0, "message": "0 celdas."},
        ):
            response = self._chat()

        self.assertIn("No se remedió ningún valor nulo", response.conversational_response)
        self.assertNotIn("Tratamiento de nulos", response.conversational_response)

    def test_remediation_with_rows_affected_is_reported_as_applied(self):
        applied = {
            "status": "success",
            "policy": "delete_rows",
            "rows_affected": 2,
            "message": "Remediación de nulos aplicada bajo la política 'delete_rows': 2 celda(s) modificada(s).",
        }
        with patch("app.modules.chat_engine.engine.NullManagerService.apply_null_policy", return_value=applied):
            response = self._chat()

        text = response.conversational_response
        self.assertIn("Tratamiento de nulos", text)
        self.assertIn("Eliminación de registros con nulos", text)
        self.assertNotIn("No se remedió ningún valor nulo", text)

    def test_policy_is_still_forced_to_open_afterwards(self):
        """El aviso no puede cambiar la política aplicada: sigue siendo 'open'."""
        no_op = {"status": "no_op", "policy": "delete_rows", "rows_affected": 0, "message": "nada que remediar"}
        mock_conn = MagicMock()
        mock_conn.id = 1
        mock_conn.db_type = DatabaseType.SQLITE
        mock_conn.host = self.db_path
        mock_conn.database_name = self.db_path
        mock_conn.null_policy = "delete_rows"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conn
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_conn
        mock_db.query.return_value.order_by.return_value.first.return_value = mock_conn

        with patch("app.modules.chat_engine.engine.NullManagerService.apply_null_policy", return_value=no_op):
            asyncio.run(QueryEngine.execute_query(
                question="Tratar nulos en test_sales (eliminar registros con nulos) para la consulta: SELECT * FROM test_sales",
                user_role="Administrador", is_admin=True, db=mock_db, connection_id=1,
                conversation_history=[{"question": "SELECT * FROM test_sales", "sql": "SELECT * FROM test_sales"}],
            ))

        self.assertEqual(mock_conn.null_policy, "open")


# ---------------------------------------------------------------- bug 2

class TestUnknownConnectionIdIsRejectedByTheInspector(unittest.TestCase):
    def test_explicit_unknown_id_raises_404(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            SchemaInspector.resolve_connection_db_path(db, 999)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("999", ctx.exception.detail)

    def test_it_does_not_silently_introspect_another_database(self):
        """El sintoma: pedir la 999 y terminar leyendo la base no-uploadada."""
        db = MagicMock()
        uploaded = _conn_record(1, name="Base de Datos Clientes Nuevos")
        uploaded.is_uploaded = False

        def query_side_effect(_model):
            q = MagicMock()
            # id=999 -> None; el fallback is_uploaded=False -> la otra base.
            q.filter.return_value.first.side_effect = [None, uploaded]
            return q

        db.query.side_effect = query_side_effect

        with self.assertRaises(HTTPException) as ctx:
            SchemaInspector.resolve_connection_db_path(db, 999)

        # Si hubiera caido en el fallback, el segundo `first` (la base
        # no-uploadada) se habria consumido y no habria raising.
        self.assertIn("999", ctx.exception.detail)
        self.assertNotEqual(uploaded.id, 999)

    def test_no_connection_id_still_resolves_the_active_one(self):
        """El camino legitimo: sin connection_id se usa la conexion activa."""
        active = _conn_record(7)
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = active

        db_path, conn = SchemaInspector.resolve_connection_db_path(db, None)

        self.assertIs(conn, active)
        self.assertTrue(db_path)

    def test_known_connection_id_still_resolves(self):
        known = _conn_record(3)
        known.db_type = DatabaseType.POSTGRESQL
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = known

        _db_path, conn = SchemaInspector.resolve_connection_db_path(db, 3)

        self.assertIs(conn, known)


# ---------------------------------------------------------------- bug 3

def _catalog_entry(table, column, schema, friendly):
    return SemanticCatalog(
        id=abs(hash((schema or "", table, column))) % 10000,
        connection_id=1,
        domain_id=None,
        schema_name=schema,
        table_name=table,
        column_name=column,
        friendly_name=friendly,
        description=f"desc de {friendly}",
        synonyms=None,
        business_formula=None,
        is_ai_generated=False,
    )


def _tables_meta(tables):
    return [
        {
            "table_name": tbl,
            "schema_name": schema,
            "row_count": 1,
            "columns": [{
                "name": col, "data_type": "TEXT", "is_pk": False,
                "is_nullable": True, "default_value": None, "sample_values": ["x"],
            }],
        }
        for schema, tbl, col in tables
    ]


def _dictionary(entries, tables):
    db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model.__name__ == "SemanticCatalog":
            q.filter.return_value.all.return_value = entries
        return q

    db.query.side_effect = query_side_effect

    with patch.object(
        cs.SchemaInspector, "resolve_connection_db_path",
        return_value=("/tmp/x.db", _conn_record(1)),
    ), patch.object(cs.SchemaInspector, "introspect_connection_metadata", return_value=tables):
        return CatalogDomainService.get_data_dictionary(db, connection_id=1)


class TestCatalogMapKey(unittest.TestCase):
    def test_homonymous_columns_in_two_schemas_do_not_collide(self):
        tables = [("public", "ventas", "codigo"), ("priv", "ventas", "codigo")]
        entries = [
            _catalog_entry("ventas", "codigo", "public", "Codigo publico"),
            _catalog_entry("ventas", "codigo", "priv", "Codigo privado"),
        ]

        resp = _dictionary(entries, _tables_meta(tables))
        by_schema = {t.schema_name: t.columns[0] for t in resp.tables}

        self.assertEqual(by_schema["public"].friendly_name, "Codigo publico")
        self.assertEqual(by_schema["priv"].friendly_name, "Codigo privado")

    def test_lookup_is_case_insensitive(self):
        """Postgres devuelve la tabla en minuscula y la curaduría la guardo en mayuscula."""
        tables = [("public", "ventas", "codigo")]
        entries = [_catalog_entry("VENTAS", "CODIGO", "PUBLIC", "Codigo curado")]

        resp = _dictionary(entries, _tables_meta(tables))

        self.assertEqual(resp.tables[0].columns[0].friendly_name, "Codigo curado")

    def test_legacy_row_without_schema_still_matches(self):
        """Filas sembradas antes de existir `schema_name` (NULL o "") no desaparecen."""
        for legacy_schema in (None, ""):
            with self.subTest(schema=legacy_schema):
                tables = [("public", "ventas", "codigo")]
                entries = [_catalog_entry("ventas", "codigo", legacy_schema, "Codigo legado")]

                resp = _dictionary(entries, _tables_meta(tables))

                self.assertEqual(resp.tables[0].columns[0].friendly_name, "Codigo legado")

    def test_specific_schema_wins_over_the_legacy_wildcard(self):
        tables = [("public", "ventas", "codigo")]
        entries = [
            _catalog_entry("ventas", "codigo", None, "Codigo legado"),
            _catalog_entry("ventas", "codigo", "public", "Codigo publico"),
        ]

        resp = _dictionary(entries, _tables_meta(tables))

        self.assertEqual(resp.tables[0].columns[0].friendly_name, "Codigo publico")

    def test_table_level_description_also_respects_the_schema(self):
        entries = [
            SemanticCatalog(
                id=1, connection_id=1, domain_id=None, schema_name="public",
                table_name="ventas", column_name=None, friendly_name="Ventas",
                description="Tabla de ventas publicas", is_ai_generated=False,
            ),
            SemanticCatalog(
                id=2, connection_id=1, domain_id=None, schema_name="priv",
                table_name="ventas", column_name=None, friendly_name="Ventas",
                description="Tabla de ventas privadas", is_ai_generated=False,
            ),
        ]

        resp = _dictionary(entries, _tables_meta([("public", "ventas", "codigo"), ("priv", "ventas", "codigo")]))
        by_schema = {t.schema_name: t.description for t in resp.tables}

        self.assertEqual(by_schema["public"], "Tabla de ventas publicas")
        self.assertEqual(by_schema["priv"], "Tabla de ventas privadas")


if __name__ == "__main__":
    unittest.main()