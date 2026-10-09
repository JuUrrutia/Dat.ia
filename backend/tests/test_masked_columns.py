"""Las columnas MASKED se consultan pero su valor no sale en claro.

El enum `ColumnPermissionType` define ALLOWED / BLOCKED / MASKED, e `init_db` siembra
`dim_clientes.rut_dni_cliente` como MASKED para todos los roles. Antes de este fix
MASKED no hacia nada: no entraba a `blocked_columns` (asi que el validador lo dejaba
pasar) y ningun modulo transformaba el valor, asi que un Economista leia el RUT/DNI
en claro. Habia enum, seed, `[ENMASCARADO]` en el prompt y un docstring que promete
"column masking"; nada de eso tocaba un valor.

Regla acordada: se conservan los ultimos 4 DIGITOS.
"""

import unittest

from main import app  # noqa: F401  registra los mappers de SQLAlchemy

from app.core.database import SessionLocal
from app.core.security import mask_rows, mask_value
from app.modules.chat_engine.governance_guard import GovernanceGuard


class TestMaskValue(unittest.TestCase):
    def test_keeps_last_four_digits_of_rut(self):
        # Regla acordada: 12.345.678-9 -> *******678-9
        self.assertEqual(mask_value("12.345.678-9"), "*******678-9")
        self.assertEqual(mask_value("98.765.432-4"), "*******432-4")

    def test_counts_digits_not_characters(self):
        # Los ultimos 4 CARACTERES serian "78-9" y perderian el 6.
        masked = mask_value("12.345.678-9")
        self.assertTrue(masked.endswith("678-9"), masked)
        self.assertNotIn("12.345", masked)

    def test_original_value_is_not_recoverable(self):
        original = "12.345.678-9"
        masked = mask_value(original)
        # Lo unico visible son los ultimos 4 digitos y los separadores posteriores.
        self.assertNotIn("12.345", masked)
        self.assertEqual(len(masked), len(original))

    def test_none_stays_none(self):
        # Un NULL tiene que seguir siendo NULL, no una cadena de asteriscos.
        self.assertIsNone(mask_value(None))

    def test_fails_closed_without_enough_digits(self):
        # Fallar abierto seria revelar el final del dato en una columna sensible.
        self.assertEqual(mask_value("texto sin numeros"), "*" * len("texto sin numeros"))
        self.assertEqual(mask_value("123"), "***")

    def test_empty_string(self):
        self.assertEqual(mask_value(""), "")


class TestMaskRows(unittest.TestCase):
    def test_masks_only_the_named_columns(self):
        rows = [{
            "nombre": "Ana Perez",
            "rut_dni_cliente": "12.345.678-9",
            "email": "ana@empresa.com",
        }]
        touched = mask_rows(rows, {"rut_dni_cliente"})

        self.assertEqual(touched, 1)
        self.assertEqual(rows[0]["rut_dni_cliente"], "*******678-9")
        self.assertEqual(rows[0]["nombre"], "Ana Perez")
        self.assertEqual(rows[0]["email"], "ana@empresa.com")

    def test_is_case_insensitive_on_the_column_key(self):
        # El motor puede devolver la clave con el casing usado en la consulta.
        rows = [{"RUT_DNI_CLIENTE": "12.345.678-9"}]
        mask_rows(rows, {"rut_dni_cliente"})
        self.assertEqual(rows[0]["RUT_DNI_CLIENTE"], "*******678-9")

    def test_empty_inputs_are_noop(self):
        rows = [{"rut_dni_cliente": "12.345.678-9"}]
        self.assertEqual(mask_rows(rows, set()), 0)
        self.assertEqual(mask_rows(rows, None), 0)
        self.assertEqual(mask_rows([], {"rut_dni_cliente"}), 0)
        self.assertEqual(rows[0]["rut_dni_cliente"], "12.345.678-9")


class TestMaskedColumnsAreGovernedSeparately(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_masked_column_is_not_blocked(self):
        """MASKED debe seguir consultable: si se bloqueara, el LLM no puede join-ear."""
        blocked = GovernanceGuard.get_blocked_columns_for_role(
            "Economista", False, db=self.db, role_id=None, connection_id=1
        )
        masked = GovernanceGuard.get_masked_columns_for_role(
            "Economista", False, db=self.db, role_id=None, connection_id=1
        )

        self.assertIn("rut_dni_cliente", masked)
        self.assertNotIn(
            "rut_dni_cliente", blocked,
            "MASKED no debe agregarse a blocked_columns o la consulta se rechaza entera",
        )

    def test_blocked_columns_are_unaffected(self):
        """El fix de MASKED no debe relajar el bloqueo de las columnas criticas."""
        blocked = GovernanceGuard.get_blocked_columns_for_role(
            "Economista", False, db=self.db, role_id=None, connection_id=1
        )
        for critical in ("tarjeta_credito_token", "sueldo_mensual", "salario"):
            self.assertIn(critical, blocked, f"{critical} dejo de estar bloqueada")

    def test_admin_sees_masked_columns_in_clear(self):
        masked = GovernanceGuard.get_masked_columns_for_role(
            "admin", True, db=self.db, role_id=None, connection_id=1
        )
        self.assertEqual(masked, set())


class TestMaskingReachesTheResponse(unittest.TestCase):
    """End-to-end: la mascara tiene que estar en la respuesta, no solo en la funcion.

    Los tests de arriba pasarian igual si el punto de aplicacion en engine.py
    estuviera mal o si rows se consumiera antes de enmascarar. Este test atraviesa
    el motor completo y comprueba la fila que ve el usuario.
    """
    def setUp(self):
        import sqlite3
        import tempfile
        from unittest.mock import MagicMock, patch

        from app.modules.admin_catalog.models import DatabaseType
        from app.modules.chat_engine.engine import QueryEngine

        self.QueryEngine = QueryEngine
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

        # El rol tiene la columna MASKED y NO bloqueada: consultable, valor tapado.
        self.patches = [
            patch.object(QueryEngine, "get_masked_columns_for_role",
                         classmethod(lambda cls, *a, **k: {"rut_dni_cliente"})),
            patch.object(QueryEngine, "get_blocked_columns_for_role",
                         classmethod(lambda cls, *a, **k: set())),
            patch.object(QueryEngine, "get_allowed_tables_for_role",
                         classmethod(lambda cls, *a, **k: {"clientes"})),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        import os
        for p in self.patches:
            p.stop()
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_rut_never_reaches_the_response_in_clear(self):
        import asyncio
        response = asyncio.run(
            self.QueryEngine.execute_query(
                question="SELECT nombre, rut_dni_cliente FROM clientes",
                user_role="Economista",
                is_admin=False,
                db=self.mock_db,
                connection_id=1,
            )
        )

        rows = getattr(response, "data_rows", None)
        self.assertTrue(rows, f"la consulta no devolvio filas: {response}")
        self.assertEqual(len(rows), 2)

        for row in rows:
            self.assertIn("rut_dni_cliente", row)
            self.assertNotIn(
                "12.345.678-9", str(row),
                "el RUT en claro llego a la respuesta del usuario",
            )
            self.assertRegex(
                row["rut_dni_cliente"], r"^\*+\d{3}-\d$",
                f"el RUT no quedo enmascarado con la regla acordada: {row['rut_dni_cliente']}",
            )

        # El resto de la fila debe seguir intacto: enmascarar no rompe la consulta.
        self.assertIn("nombre", rows[0])
        self.assertTrue(rows[0]["nombre"])


if __name__ == "__main__":
    unittest.main()
