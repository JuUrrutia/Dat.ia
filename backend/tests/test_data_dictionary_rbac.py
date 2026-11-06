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

# Columnas sensibles de las dos demos y lo que la matriz RBAC hace con cada una.
#
# Son la UNION de las dos, y a proposito: la demo de PostgreSQL y la de SQLite no
# tienen el mismo esquema (`sueldo_mensual` vs `salario_bruto`, y la de SQLite anade
# IBAN y RUT del empleado), asi que una lista fija por motor hacia que el test
# pasara en vacio contra el otro. Lo que se verifica es la columna sensible que la
# conexion ACTIVA expone de verdad, y que este clasificada. Las columnas que la
# conexion activa no expone se saltan solas: no hay nada que filtrar en ellas.
SENSITIVE = {
    "tarjeta_credito_token": "BLOCKED",
    "sueldo_mensual": "BLOCKED",
    "salario_bruto": "BLOCKED",
    "cuenta_bancaria_iban": "BLOCKED",
    "api_key_servicio": "BLOCKED",
    "rut_dni_cliente": "MASKED",
    "rut_dni": "MASKED",
}


# Tokens que delatan una columna sensible aunque nadie la haya clasificado. El
# escaneo los cruza contra los TRAMOS CONTIGUOS de tokens del nombre, no contra
# subcadenas: `ingreso_bruto` contiene "rut" dentro de "bruto" y no es una columna
# de RUT, que es la razon de que este chequeo no puede ser un `in`.
SENSITIVE_TOKENS = {
    "token", "salario", "sueldo", "rut", "dni", "api_key",
    "apikey", "password", "contrasena", "secret", "iban", "tarjeta",
}


def _ngrams_de_tokens(name):
    """Los tramos CONTIGUOS de tokens del nombre, como texto unido por `_`.

    Antes el escaneo comparaba `SENSITIVE_TOKENS & set(name.split("_"))`, y eso
    hacia que los tokens de VARIAS palabras de la lista fueran codigo muerto:
    `split("_")` nunca devuelve "api_key", asi que `api_key_servicio` no podia
    salir sospechosa nunca y la guarda daba verde sobre una columna sensible sin
    clasificar (medido: el API key de `dim_servidores` se lo servia en claro a
    `economista`).

    Se comparan por token y no por subcadena todavia: los n-gramas respetan los
    limites de palabra, asi que `ingreso_bruto` NO produce "rut" (que es lo unico
    que lo separaba de un `in`) y si produce "api_key".
    """
    partes = name.lower().split("_")
    return {
        "_".join(partes[i:j])
        for i in range(len(partes))
        for j in range(i + 1, len(partes) + 1)
    }


class TestDataDictionaryRespectsRbac(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Precondicion: sin esto los tests de abajo pasan EN VACIO.
        #
        # `samples.get(name, [])` devuelve `[]` cuando la columna no existe, y
        # `for value in samples.get(name, [])` no itera si no hay columna. O sea:
        # si la conexion activa no trae ninguna columna sensible de `SENSITIVE`, los
        # asserts son verdaderos sin comprobar nada y el archivo entero reporta
        # verde sobre datos que nunca vio. Por eso se exige al menos una BLOCKED y
        # una MASKED de verdad, no solo que el diccionario de arriba no este vacio.
        #
        # Este archivo se creo porque `scripts/verify_dictionary_filter.py`
        # detectaba exactamente eso; el script se borro (ceremonia manual) pero
        # el agujero es real, asi que la guarda vive aca.
        admin_samples = self._samples("admin", "admin123")
        self.assertTrue(
            self._blockers(admin_samples),
            f"la conexion activa no expone ninguna columna BLOCKED de {sorted(SENSITIVE)}: "
            "estos tests pasarian sin comprobar nada. Sembrar la BD demo antes de "
            "correrlos.",
        )
        self.assertTrue(
            self._maskers(admin_samples),
            f"la conexion activa no expone ninguna columna MASKED de {sorted(SENSITIVE)}: "
            "estos tests pasarian sin comprobar nada. Sembrar la BD demo antes de "
            "correrlos.",
        )
        # El caso que `salario` tapaba sin comprobar: una columna sensible nueva
        # que llega al esquema y nadie agrego a `SENSITIVE`. Se pasa por alto hoy
        # y por eso el diccionario podria filtrarla.
        covered = set(SENSITIVE)
        sospechosas = sorted(
            name
            for name in admin_samples
            if name not in covered
            and SENSITIVE_TOKENS & _ngrams_de_tokens(name)
        )
        self.assertEqual(
            sospechosas,
            [],
            f"columnas sensibles fuera de SENSITIVE: {sospechosas}. Si la "
            "conexion debe filtrarlas, agregalas al diccionario de arriba.",
        )

    def _blockers(self, samples):
        return [n for n, kind in SENSITIVE.items() if kind == "BLOCKED" and n in samples]

    def _maskers(self, samples):
        return [n for n, kind in SENSITIVE.items() if kind == "MASKED" and n in samples]

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
        admin_samples = self._samples("admin", "admin123")
        samples = self._samples("economista", "economista123")
        for name in self._blockers(admin_samples):
            with self.subTest(columna=name):
                self.assertEqual(
                    samples.get(name, []), [],
                    f"un Economista recibio valores de muestra de la columna BLOCKED {name}",
                )

    def test_non_admin_gets_masked_values_for_masked_columns(self):
        admin_samples = self._samples("admin", "admin123")
        samples = self._samples("economista", "economista123")
        for name in self._maskers(admin_samples):
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
        for name in self._blockers(samples):
            self.assertTrue(
                samples[name],
                f"al admin no le llegan valores de la columna BLOCKED {name}",
            )
        for name in self._maskers(samples):
            for value in samples.get(name, []):
                self.assertFalse(
                    str(value).startswith("*"),
                    "al admin se le estan enmascarando valores que debería ver en claro",
                )


class TestEscaneoDeColumnasSospechosas(unittest.TestCase):
    """El escaneo, aislado de la BD: es la parte que estaba dando verde en falso."""

    def test_marca_el_token_de_dos_palabras(self):
        self.assertTrue(
            SENSITIVE_TOKENS & _ngrams_de_tokens("api_key_servicio"),
            "api_key_servicio tiene que salir sospechosa: es un token de dos palabras",
        )

    def test_no_marca_ingreso_bruto(self):
        self.assertFalse(
            SENSITIVE_TOKENS & _ngrams_de_tokens("ingreso_bruto"),
            "ingreso_bruto no es una columna de RUT: 'rut' va dentro de 'bruto'",
        )


if __name__ == "__main__":
    unittest.main()
