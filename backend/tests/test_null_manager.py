"""NullManagerService no puede afirmar una remediacion que no ocurrio.

Contexto: este servicio ESCRIBE en la base del cliente (borra filas, hace
UPDATE). Decir "aplicada con exito" sin haber modificado una sola celda hace
que el usuario crea que su base quedo remediada cuando no fue asi, y tratar
el texto 'None' como nulo hacia que `delete_rows` borrara filas de datos
legitimos.

Cada test reproduce un escenario concreto verificado contra el codigo real.
"""

import asyncio
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.modules.admin_catalog.models import DatabaseType
from app.modules.catalog.services.null_manager import NullManagerService
from app.modules.chat_engine.engine import QueryEngine


def _make_sqlite_conn(path, db_mock=None):
    conn = MagicMock()
    conn.id = 1
    conn.db_type = DatabaseType.SQLITE
    conn.host = path
    conn.database_name = path
    conn.null_policy = "open"
    conn.name = "test"
    return conn


class NullManagerTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = MagicMock()

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def _exec(self, sql, params=()):
        c = sqlite3.connect(self.db_path)
        c.execute(sql, params)
        c.commit()
        c.close()

    def _rows(self, table):
        c = sqlite3.connect(self.db_path)
        out = c.execute(f'SELECT * FROM "{table}"').fetchall()
        c.close()
        return out


class TestDeleteRowsDoesNotEatTheStringNone(NullManagerTestCase):
    """BUG 2: `WHERE col IS NULL OR LOWER(col) IN ('null','none')`.

    Una columna de texto con el valor real 'None' (un proveedor, un estado, una
    observacion) era contada como nulo, y con policy='delete_rows' se BORRABA la
    fila de ese cliente. El usuario pidio borrar nulos, no borrar cosas que se
    llamen None.
    """

    def setUp(self):
        super().setUp()
        self._exec("CREATE TABLE clientes (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT)")
        self._exec("INSERT INTO clientes VALUES (1, 'None', 'activo')")
        self._exec("INSERT INTO clientes VALUES (2, 'Acme', 'activo')")
        self._exec("INSERT INTO clientes VALUES (3, 'None', 'inactivo')")

    def test_audit_does_not_count_string_none_as_null(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        audit = NullManagerService.audit_connection_nulls(conn, self.db)

        self.assertFalse(
            audit["has_nulls"],
            "una columna sin un solo NULL real fue reportada con nulos: el "
            "literal 'None' se esta tomando por SQL NULL",
        )
        self.assertTrue(audit["is_complete"])

    def test_delete_rows_keeps_rows_whose_value_is_the_string_none(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "delete_rows", self.db)

        rows = self._rows("clientes")
        self.assertEqual(len(rows), 3, f"delete_rows borro filas con dato legitimo: {rows}")
        self.assertIn((1, "None", "activo"), rows, "la fila del cliente con proveedor 'None' fue borrada")
        self.assertEqual(result["status"], "no_op")
        self.assertEqual(result["rows_affected"], 0)

    def test_delete_rows_still_removes_real_nulls(self):
        """El default IS NULL tiene que seguir borrando lo que es nulo de verdad."""
        self._exec("INSERT INTO clientes VALUES (4, NULL, 'activo')")

        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "delete_rows", self.db)

        rows = self._rows("clientes")
        self.assertEqual(len(rows), 3)
        self.assertNotIn((4, None, "activo"), rows)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["rows_affected"], 1)


class TestZeroRowsIsNotSuccess(NullManagerTestCase):
    """BUG 1: `status: "success"` incondicional en la linea de return.

    Columna 100% nulos + policy='mode' -> el SELECT de la moda no devuelve
    filas -> el `if` se saltea -> cero celdas modificadas -> "Remediacion de
    nulos aplicada con exito". Mismo resultado con 'nearest' y cuando el
    target_path no resuelve.
    """

    def setUp(self):
        super().setUp()
        self._exec("CREATE TABLE solo_nulos (id INTEGER PRIMARY KEY, valor TEXT)")
        self._exec("INSERT INTO solo_nulos VALUES (1, NULL)")
        self._exec("INSERT INTO solo_nulos VALUES (2, NULL)")
        self._exec("INSERT INTO solo_nulos VALUES (3, NULL)")

    def test_mode_on_all_null_column_does_not_report_success(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "mode", self.db)

        self.assertEqual(
            result["status"], "no_op",
            "una columna 100% nula no tiene moda: se modificaron 0 celdas y se reporto 'exito'",
        )
        self.assertEqual(result["rows_affected"], 0)
        self.assertIn("No se remedió nada", result["message"])

    def test_nearest_on_all_null_column_does_not_report_success(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "nearest", self.db)

        self.assertEqual(result["status"], "no_op")
        self.assertEqual(result["rows_affected"], 0)

    def test_nearest_with_unresolvable_target_does_not_report_success(self):
        """Sin target_path el bloque entero se saltea y aun asi decía exito."""
        conn = _make_sqlite_conn("/ruta/que/no/existe.db", self.db)
        conn.host = "/ruta/que/no/existe.db"
        conn.database_name = "/ruta/que/no/existe.db"

        tables_meta = [{
            "table_name": "solo_nulos", "schema_name": "main", "row_count": 3,
            "columns": [{"name": "valor", "data_type": "TEXT"}],
        }]
        with patch.object(
            NullManagerService, "audit_connection_nulls",
            return_value={
                "has_nulls": True, "total_tables_with_nulls": 1,
                "tables": [{**tables_meta[0], "columns_with_nulls": [
                    {"column_name": "valor", "data_type": "TEXT",
                     "null_count": 3, "null_percentage": 100.0}],
                    "total_null_columns": 1, "unverifiable_columns": []}],
                "total_unverifiable_columns": 0, "is_complete": True,
                "current_policy": "open",
            },
        ):
            # Ninguna ruta resuelve: el `if target_path and os.path.exists(...)`
            # se saltea y antes se reportaba "aplicada con exito" igual.
            with patch("os.path.exists", return_value=False):
                result = NullManagerService.apply_null_policy(conn, "delete_rows", self.db)

        self.assertEqual(result["status"], "no_op")
        self.assertEqual(result["rows_affected"], 0)

    def test_remediation_that_changes_cells_reports_the_count(self):
        """El camino feliz si debe decir success, y decir cuantas celdas toco."""
        self._exec("CREATE TABLE mixta (id INTEGER PRIMARY KEY, valor TEXT)")
        self._exec("INSERT INTO mixta VALUES (1, 'A')")
        self._exec("INSERT INTO mixta VALUES (2, NULL)")

        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "mode", self.db)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["rows_affected"], 1)
        self.assertIn("1 celda(s)", result["message"])


class TestNearestUsesThePrecedingValue(NullManagerTestCase):
    """BUG 3: la rama Postgres hacia `SELECT ... LIMIT 1` sin ORDER BY.

    Eso devuelve una fila arbitraria (tipicamente la primera). Con
    salario=[100, NULL, 500] rellenaba 100 en vez del precedente 500, y la
    rama SQLite si hacia forward-fill real por rowid. Fabricacion de dato.
    """

    def setUp(self):
        super().setUp()
        self._exec("CREATE TABLE salarios (id INTEGER PRIMARY KEY, salario INTEGER)")
        self._exec("INSERT INTO salarios VALUES (1, 100)")
        self._exec("INSERT INTO salarios VALUES (2, NULL)")
        self._exec("INSERT INTO salarios VALUES (3, 500)")

    def test_sqlite_forward_fill_takes_previous_value(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "nearest", self.db)

        rows = self._rows("salarios")
        self.assertEqual(result["status"], "success")
        self.assertEqual(rows[1][1], 100, f"el forward-fill no tomo el valor precedente: {rows}")

    def test_postgres_nearest_sql_uses_lag_over_ctid_not_bare_limit_1(self):
        """La rama Postgres tiene que pedir el predecessor, no una fila arbitraria."""
        import inspect as py_inspect
        src = py_inspect.getsource(NullManagerService.apply_null_policy)
        pg_branch = src.split("if is_pg:")[1].split("# SQLite")[0]

        self.assertIn("LAG(", pg_branch, "la rama Postgres no usa LAG(): no hay forward-fill real")
        self.assertIn("ORDER BY ctid", pg_branch)
        self.assertNotIn(
            "IS NOT NULL LIMIT 1'", pg_branch,
            "quedo el `LIMIT 1` sin ORDER BY que devuelve una fila arbitraria",
        )

    def test_postgres_forward_fill_updates_only_rows_that_were_null(self):
        """La CTE del forward-fill no debe pisar filas que ya tenian valor."""
        import inspect as py_inspect
        src = py_inspect.getsource(NullManagerService.apply_null_policy)
        pg_branch = src.split("if is_pg:")[1].split("# SQLite")[0]
        self.assertIn('t."{c_name}" IS NULL', pg_branch,
                      "el UPDATE de forward-fill debe filtrar por IS NULL: si no, pisa datos validos")


class TestScanMarksUnverifiableColumns(NullManagerTestCase):
    """BUG 4: `except Exception: pass` en el escaneo.

    GRANT de tabla pero no de columna -> el COUNT(*) lanza -> la columna se
    omite en silencio -> has_nulls=False -> "Base de datos limpia: No se
    detectaron valores nulos". Y peor: `delete_rows` borraba filas basandose en
    un conteo incompleto.
    """

    def setUp(self):
        super().setUp()
        self._exec("CREATE TABLE permisos (id INTEGER PRIMARY KEY, secreto TEXT, visible TEXT)")
        self._exec("INSERT INTO permisos VALUES (1, 'valor', 'ok')")
        self._exec("INSERT INTO permisos VALUES (2, NULL, NULL)")

    def test_column_scan_error_is_reported_as_unverifiable_not_clean(self):
        conn = _make_sqlite_conn(self.db_path, self.db)

        real_conn = sqlite3.connect(self.db_path)
        real_cursor = real_conn.cursor()

        class _FlakyCursor:
            """Delegates to a real cursor but raises on the restricted column,
            the way the server does when the user has a table GRANT but not a
            column GRANT."""

            def execute(self, sql, *a, **kw):
                if "secreto" in sql:
                    raise sqlite3.OperationalError("permission denied for column secreto")
                return real_cursor.execute(sql, *a, **kw)

            def __getattr__(self, k):
                return getattr(real_cursor, k)

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = _FlakyCursor()
        # `__enter__` debe devolver la MISMA conexion: si no, el `with` del
        # servicio agarra un mock nuevo y la columna restringida nunca falla.
        fake_conn.__enter__.return_value = fake_conn

        with patch("sqlite3.connect", return_value=fake_conn):
            audit = NullManagerService.audit_connection_nulls(conn, self.db)

        self.assertFalse(
            audit["is_complete"],
            "una columna que no se pudo escanear fue reportada como escaneo completo",
        )
        self.assertEqual(audit["total_unverifiable_columns"], 1)
        self.assertTrue(
            audit["has_nulls"],
            "la columna 'visible' tambien tiene un NULL real, asi que has_nulls debe ser True",
        )
        tbl = audit["tables"][0]
        unverifiable = [c["column_name"] for c in tbl["unverifiable_columns"]]
        self.assertIn("secreto", unverifiable)
        self.assertIn("permission denied", tbl["unverifiable_columns"][0]["reason"])

    def test_apply_policy_warns_instead_of_claiming_a_clean_database(self):
        """`no hay nulos` + escaneo incompleto no puede llamarse 'base limpia'."""
        with patch.object(
            NullManagerService, "audit_connection_nulls",
            return_value={
                "has_nulls": False, "total_tables_with_nulls": 1,
                "tables": [], "total_unverifiable_columns": 3,
                "is_complete": False, "current_policy": "open",
            },
        ):
            conn = _make_sqlite_conn(self.db_path, self.db)
            result = NullManagerService.apply_null_policy(conn, "delete_rows", self.db)

        self.assertEqual(result["status"], "no_op")
        self.assertIn("INCOMPLETO", result["message"])
        self.assertIn("permisos de columna", result["message"])


class TestPolicyIsNotPersistedBeforeItIsApplied(NullManagerTestCase):
    """BUG 5: `conn.null_policy = policy; db.commit()` iba ANTES del audit y de
    la aplicacion. Si el audit o la remediacion fallaban, la conexion quedaba
    diciendo que la politica estaba activa sobre una base sin remediar, y el
    frontend la mostraba como aplicada.
    """

    def setUp(self):
        super().setUp()
        self._exec("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        self._exec("INSERT INTO t VALUES (1, NULL)")

    def _commit_order(self):
        return [c.args[0] for c in self.db.commit.call_args_list]

    def test_audit_failure_rolls_back_the_policy(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        with patch.object(
            NullManagerService, "audit_connection_nulls",
            side_effect=RuntimeError("no se pudo abrir la base"),
        ):
            with self.assertRaises(RuntimeError):
                NullManagerService.apply_null_policy(conn, "delete_rows", self.db)

        self.db.commit.assert_not_called()
        self.db.rollback.assert_called_once()

    def test_remediation_failure_rolls_back_the_policy(self):
        conn = _make_sqlite_conn(self.db_path, self.db)
        audit_ok = {
            "has_nulls": True, "total_tables_with_nulls": 1,
            "total_unverifiable_columns": 0, "is_complete": True, "current_policy": "open",
            "tables": [{
                "table_name": "t", "schema_name": "main", "total_rows": 1,
                "columns_with_nulls": [{"column_name": "v", "data_type": "TEXT",
                                        "null_count": 1, "null_percentage": 100.0}],
                "total_null_columns": 1, "unverifiable_columns": [],
            }],
        }
        with patch.object(NullManagerService, "audit_connection_nulls", return_value=audit_ok):
            with patch("sqlite3.connect", side_effect=RuntimeError("archivo en uso")):
                with self.assertRaises(RuntimeError):
                    NullManagerService.apply_null_policy(conn, "delete_rows", self.db)

        self.db.commit.assert_not_called()
        self.db.rollback.assert_called_once()

    def test_success_commits_exactly_once_at_the_end(self):
        self._exec("INSERT INTO t VALUES (2, 'X')")
        conn = _make_sqlite_conn(self.db_path, self.db)
        result = NullManagerService.apply_null_policy(conn, "mode", self.db)

        self.assertEqual(result["status"], "success")
        self.db.commit.assert_called_once()


class _NullDbFixture(unittest.TestCase):
    """Base SQLite temporal con 2 filas con nulos, como el resto de la suite.

    `engine.execute_query` descartaba el retorno de `NullManagerService.apply_null_policy`.
    El servicio ya devuelve `status: "no_op"` / `rows_affected: 0` cuando no
    remedio nada, pero el chat miraba el exito viejo: el usuario clickeaba
    "eliminar nulos", la base no se tocaba y la respuesta decia
    "Tratamiento de nulos aplicado".
    """

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
    """Lo que el CHAT dice tras remediar: tiene que calcar lo que el servicio reporto."""

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
        """El aviso no puede cambiar la politica aplicada: sigue siendo 'open'."""
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


if __name__ == "__main__":
    unittest.main()