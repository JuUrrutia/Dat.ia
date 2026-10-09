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

# Columnas que la conexion activa EXPONE de verdad. `salario` estaba aqui y se
# salio: no existe en el esquema de la demo ni en el de la base corporativa, asi
# que sus asserts pasaban en vacio (`samples.get('salario', [])` es `[]` porque
# la columna no esta, no porque este filtrada). La guarda de `setUp` ahora
# falla si aparece una columna sensible nueva sin cubrir, que es el caso que
# `salario` representaba sin comprobar.
BLOCKED = ("tarjeta_credito_token", "sueldo_mensual")
MASKED = ("rut_dni_cliente",)


class TestDataDictionaryRespectsRbac(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Precondicion: sin esto los tres tests de abajo pasan EN VACIO.
        #
        # `samples.get(name, [])` devuelve `[]` cuando la columna no existe, y
        # `for value in samples.get(name, [])` no itera si no hay columna. O sea:
        # si la conexion activa no trae `tarjeta_credito_token` ni
        # `rut_dni_cliente`, los dos asserts son verdaderos sin comprobar nada y
        # el archivo entero reporta verde sobre datos que nunca vio.
        #
        # Este archivo se creo porque `scripts/verify_dictionary_filter.py`
        # detectaba exactamente eso; el script se borro (ceremonia manual) pero
        # el agujero es real, asi que la guarda vive aca.
        admin_samples = self._samples("admin", "admin123")
        ausentes = [n for n in BLOCKED + MASKED if n not in admin_samples]
        self.assertEqual(
            ausentes,
            [],
            f"la conexion activa no expone {ausentes}: estos tests pasarian sin "
            "comprobar nada. Sembrar la BD demo antes de correrlos.",
        )
        # El caso que `salario` tapaba sin comprobar: una columna sensible nueva
        # que llega al esquema y nadie agrego a las tuplas de arriba. Se pasa por
        # alto hoy y por eso el diccionario podria filtrarla.
        covered = set(BLOCKED) | set(MASKED)
        # Por TOKEN, no por subcadena: `ingreso_bruto` contiene "rut" dentro de
        # "bruto" y no es una columna de RUT. Comparar sobre `_` evita ese falso
        # positivo, que es la razon de que este chequeo no puede ser un `in`.
        SENSITIVE_TOKENS = {
            "token", "salario", "sueldo", "rut", "dni", "api_key",
            "apikey", "password", "contrasena", "secret", "iban", "tarjeta",
        }
        sospechosas = sorted(
            name
            for name in admin_samples
            if name not in covered
            and SENSITIVE_TOKENS & set(name.lower().split("_"))
        )
        self.assertEqual(
            sospechosas,
            [],
            f"columnas sensibles fuera de BLOCKED/MASKED: {sospechosas}. Si la "
            "conexion debe filtrarlas, agregalas a las tuplas de arriba.",
        )

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
