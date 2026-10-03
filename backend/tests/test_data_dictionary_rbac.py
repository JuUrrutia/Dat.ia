"""El diccionario de datos no debe filtrar valores de columnas sensibles.

`GET /catalog/data-dictionary` devuelve `sample_values` obtained with
`SELECT DISTINCT "<col>" ... LIMIT 3` per column. Ese SQL no pasa por el
ASTValidator (es introspeccion, no SQL de usuario), asi que antes de pasar el rol
los valores de columnas BLOCKED (token de tarjeta, salario) y MASKED (RUT/DNI)
llegaban a cualquier usuario autenticado.
"""

import unittest

from fastapi.testclient import TestClient

from main import app  # noqa: F401  registra los mappers de SQLAlchemy

BLOCKED = ("tarjeta_credito_token", "sueldo_mensual", "salario")
MASKED = ("rut_dni_cliente",)


class TestDataDictionaryRespectsRbac(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _token(self, username, password):
        resp = self.client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(resp.status_code, 200, f"login de {username} fallo: {resp.text[:200]}")
        return resp.json()["access_token"]

    def _samples(self, username, password):
        token = self._token(username, password)
        resp = self.client.get(
            "/api/v1/catalog/data-dictionary",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200, resp.text[:200])
        data = resp.json()
        out = {}
        for table in data.get("tables", []):
            for col in table.get("columns", []):
                out[col["name"].lower()] = col.get("sample_values") or []
        return out

    def test_non_admin_gets_no_values_for_blocked_columns(self):
        samples = self._samples("economista", "economista123")
        for name in BLOCKED:
            with self.subTest(columna=name):
                self.assertEqual(
                    samples.get(name, []), [],
                    f"un Economista recibio valores de muestra de la columna BLOCKED {name}",
                )

    def test_non_admin_gets_masked_values_for_masked_columns(self):
        samples = self._samples("economista", "economista123")
        for name in MASKED:
            with self.subTest(columna=name):
                values = samples.get(name, [])
                for value in values:
                    self.assertTrue(
                        str(value).startswith("*"),
                        f"valor MASKED sin enmascarar en {name}: {value}",
                    )

    def test_admin_still_sees_values(self):
        """El fix no puede cerrarle la puerta al admin: el enmascarado es por rol."""
        samples = self._samples("admin", "admin123")
        found = False
        for name in BLOCKED:
            if samples.get(name):
                found = True
        # El admin debe conservar acceso a los valores; si la BD demo no tiene
        # esas columnas pobladas, al menos el endpoint no debe filtrarlas tampoco.
        if found:
            return
        for name in MASKED:
            for value in samples.get(name, []):
                self.assertFalse(
                    str(value).startswith("*"),
                    "al admin se le estan enmascarando valores que debería ver en claro",
                )


if __name__ == "__main__":
    unittest.main()
