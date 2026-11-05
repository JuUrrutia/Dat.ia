"""Una cuenta SIN rol no entra a los endpoints que leen datos corporativos.

El defecto
----------
`/chat/query`, `/chat/query/stream` y `/chat/predict` ya cortaban por `require_assigned_role`
(`app/api/deps.py`). Los otros endpoints que resuelven el nombre del rol para
pasarlo al guard NO lo usaban, y cada uno tenia su propia copia del mismo fallback:

    role_name = current_user.role.name if current_user.role else ROLE_USUARIO

`ROLE_USUARIO` es "Usuario Consultor": un rol REAL y VALIDO del catalogo. El guard
resuelve por nombre cuando `role_id` es None -- a proposito, asi funcionan sus
tests y el self-healing -- y el nombre era truthy, asi que el corte no disparaba.
Consecuencia medida sobre la cuenta sin rol:

    allowed_tables = ['dim_categorias', 'dim_productos']
    blocked = 7 columnas
    masked  = 2 columnas

O sea: `/catalog/data-dictionary` le servia el diccionario con los valores de
muestra de las columnas sensibles que el Consultor tiene permitidas,
`/system/anomalies` le describia outliers de tablas de negocio, y
`/chat/suggestions` le devolvia `user_role` y `allowed_tables` del Consultor en el
cuerpo de la respuesta.

Lo que se verifica aca, con usuarios de verdad y JWT de verdad
-------------------------------------------------------------
1. Los tres devuelven 403 para `role_id = NULL, is_admin = False`, y NO devuelven
   el diccionario, ni las anomalias, ni las tablas. Sin esto el test pasaria por
   la rama equivocada: "no fue 200" no prueba nada, hay que afirmar el motivo.
2. La denegacion queda en auditoria como `RECHAZADO_RBAC` con `user_role = NULL`.
3. Contrapunto: el Usuario Consultor CON su rol asignado sigue recibiendo su
   diccionario minimo. El corte es "sin rol", no "es el Consultor".
4. El admin sin fila de rol sigue funcionando: `is_admin` manda sobre el rol
   (comportamiento explicito que el endpoint ya contemplaba y no se debe romper).
5. El anonimo de `/chat/suggestions` sigue recibiendo sugerencias genericas sin
   tablas: es el unico endpoint con dependencia opcional y no debe pasar por el gate.

Por que el caso positivo de anomalias no afirma un 200 con anomalias
--------------------------------------------------------------------
`/system/anomalies` solo entra al escaneo de datos si la conexion esta alcanzable,
y en este entorno puede no estarlo. Lo que NO puede aparecer es el 403 ni el
mensaje de "no tiene un rol asignado": si el gate se cerrara de mas, el status
seria 403 y el mensaje seria el de la denegacion.
"""

import unittest
import uuid

from fastapi.testclient import TestClient

from main import app
from app.core.constants import ROLE_USUARIO
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession, Role
from app.modules.telemetry_audit.models import AuditLog

MENSAJE_SIN_ROL = "no tiene un rol asignado"


class TestEndpointsSinRolAsignado(unittest.TestCase):
    """Cuentas reales con `role_id` NULL o resuelto, no `MagicMock` de User."""

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self._creados = []

    def tearDown(self):
        for username in self._creados:
            user = self.db.query(User).filter(User.username == username).first()
            if user:
                self.db.query(UserSession).filter(UserSession.user_id == user.id).delete()
                self.db.query(AuditLog).filter(AuditLog.user_id == user.id).delete()
                self.db.delete(user)
        self.db.commit()
        self.db.close()

    def _cuenta(self, role_name=None, is_admin=False):
        role = None
        if role_name is not None:
            role = self.db.query(Role).filter(Role.name == role_name).first()
            self.assertIsNotNone(role, f"el rol {role_name!r} tiene que existir en la metadata")

        username = f"test_sinrol2_{uuid.uuid4().hex[:8]}"
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password="x",  # nunca se verifica: se entra con JWT
            is_admin=is_admin,
            is_active=True,
            role_id=role.id if role else None,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self._creados.append(username)
        return user

    def _headers(self, user):
        jti = str(uuid.uuid4())
        self.db.add(UserSession(user_id=user.id, jti=jti, is_revoked=False))
        self.db.commit()
        return {"Authorization": f"Bearer {create_access_token(subject=user.id, jti=jti)}"}

    # --- 1. El corte, en los tres endpoints ------------------------------

    def test_data_dictionary_corta_a_la_cuenta_sin_rol(self):
        """`role_id = NULL, is_admin = False` -> 403, y sin diccionario.

        Antes: 200 con el diccionario del Consultor, `sample_values` de columnas
        BLOCKED y MASKED incluidas. El nombre caia en "Usuario Consultor" y el
        guard lo resolvia contra la matriz de ese rol.
        """
        user = self._cuenta(role_name=None)
        self.assertIsNone(user.role_id)
        self.assertFalse(user.is_admin)

        resp = self.client.get(
            "/api/v1/catalog/data-dictionary",
            headers=self._headers(user),
        )

        self.assertEqual(
            resp.status_code, 403,
            "una cuenta sin rol asignado no puede leer el diccionario corporativo",
        )
        self.assertIn(MENSAJE_SIN_ROL, resp.json().get("detail", "").lower())
        # El motivo importa tanto como el status: un 403 por otra cosa (permisos
        # de conexion, config) pasaria este assert y no probaria el gate de rol.
        self.assertNotIn("tables", resp.json())

    def test_system_anomalies_corta_a_la_cuenta_sin_rol(self):
        """`role_id = NULL, is_admin = False` -> 403 en `/system/anomalies`.

        Antes: 200, y el escaneo le describia outliers de tablas de negocio
        usando la matriz del Consultor.

        El gate va FUERA del `try/except Exception: pass` del escaneo a proposito:
        adentro el 403 se traga y el endpoint responde 200 sin anomalias, que es
        indistinguible de "no hay anomalias". Si este test falla con un 200, el
        corte quedo del lado equivocado.
        """
        user = self._cuenta(role_name=None)

        resp = self.client.get(
            "/api/v1/system/anomalies?connection_id=1",
            headers=self._headers(user),
        )

        self.assertEqual(
            resp.status_code, 403,
            "una cuenta sin rol asignado no puede leer anomalias sobre datos corporativos",
        )
        self.assertIn(MENSAJE_SIN_ROL, resp.text.lower())
        self.assertNotIn("anomalies", resp.json())

    def test_chat_suggestions_corta_a_la_cuenta_sin_rol(self):
        """Tercera copia del mismo fallback, en `/chat/suggestions`.

        Este no devuelve columnas sino `user_role` y `allowed_tables` EN EL CUERPO:
        la cuenta sin rol se enteraba de que su identidad era "Usuario Consultor" y
        de cuales eran sus tablas. Menos grave que el diccionario, misma confusion
        de identidad, y por eso mismo el mismo helper.
        """
        user = self._cuenta(role_name=None)

        resp = self.client.get(
            "/api/v1/chat/suggestions?connection_id=1",
            headers=self._headers(user),
        )

        self.assertEqual(
            resp.status_code, 403,
            "una cuenta sin rol asignado no puede ver las tablas de ningun perfil",
        )
        self.assertIn(MENSAJE_SIN_ROL, resp.text.lower())
        self.assertNotIn("Usuario Consultor", resp.text)

    # --- 2. La denegacion deja rastro --------------------------------------

    def test_la_denegacion_queda_en_auditoria(self):
        """Un corte sin registro no es un corte: el compliance lo tiene que ver.

        `user_role` queda en NULL y no en "Usuario Consultor": afirmar ese rol
        en el log seria escribir en el registro de compliance un rol que la
        cuenta no tiene.
        """
        user = self._cuenta(role_name=None)

        self.client.get("/api/v1/catalog/data-dictionary", headers=self._headers(user))

        entry = (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user.id)
            .order_by(AuditLog.id.desc())
            .first()
        )
        self.assertIsNotNone(entry, "la denegacion tiene que quedar registrada")
        self.assertEqual(entry.validation_status, "RECHAZADO_RBAC")
        self.assertIsNone(entry.user_role)

    # --- 3. Contrapunto: el Consultor con rol sigue entrando ---------------

    def test_consultor_con_rol_asignado_sigue_recibiendo_su_diccionario(self):
        """El corte es "sin rol", no "es el Consultor".

        Si este test falla, el gate volvio a bloquear por nombre y el Usuario
        Consultor -- un rol del catalogo con lectura minima declarada -- quedo
        como un perfil que no puede hacer nada.
        """
        user = self._cuenta(role_name=ROLE_USUARIO)
        self.assertIsNotNone(user.role_id)

        resp = self.client.get(
            "/api/v1/catalog/data-dictionary",
            headers=self._headers(user),
        )

        self.assertEqual(resp.status_code, 200, resp.text[:300])
        self.assertIn("tables", resp.json())
        self.assertNotIn(
            MENSAJE_SIN_ROL, resp.text.lower(),
            "el mensaje de 'no tenes rol' es de otra cuenta",
        )

    def test_consultor_con_rol_no_es_bloqueado_en_anomalias(self):
        """Contrapunto del mismo corte en el segundo endpoint."""
        user = self._cuenta(role_name=ROLE_USUARIO)

        resp = self.client.get(
            "/api/v1/system/anomalies?connection_id=1",
            headers=self._headers(user),
        )

        self.assertNotEqual(
            resp.status_code, 403,
            "el Consultor tiene rol asignado y tablas declaradas: no es una cuenta sin rol",
        )
        self.assertNotIn(MENSAJE_SIN_ROL, resp.text.lower())

    def test_anonimo_sigue_recibiendo_sugerencias_genericas(self):
        """La rama de `current_user is None` no pasa por el gate.

        `/chat/suggestions` es el unico endpoint con dependencia opcional, y el
        anonimo tiene que seguir recibiendo sugerencias genericas sin tablas.
        """
        resp = self.client.get("/api/v1/chat/suggestions")

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json().get("allowed_tables"))
        self.assertIsNone(resp.json().get("user_role"))

    # --- 4. No-regresion del admin ----------------------------------------

    def test_admin_sin_fila_de_rol_sigue_accediendo_al_diccionario(self):
        """`is_admin` manda sobre la fila de rol: no se rompio ese fallback.

        El endpoint lo contemplaba explicitamente antes del fix, asi que perderlo
        seria cambiar un comportamiento que ya existia.
        """
        user = self._cuenta(role_name=None, is_admin=True)

        resp = self.client.get(
            "/api/v1/catalog/data-dictionary",
            headers=self._headers(user),
        )

        self.assertEqual(resp.status_code, 200, resp.text[:300])
        self.assertNotIn(MENSAJE_SIN_ROL, resp.text.lower())

    def test_admin_sin_fila_de_rol_no_es_bloqueado_en_anomalias(self):
        """Lo mismo en el segundo endpoint."""
        user = self._cuenta(role_name=None, is_admin=True)

        resp = self.client.get(
            "/api/v1/system/anomalies?connection_id=1",
            headers=self._headers(user),
        )

        self.assertNotEqual(resp.status_code, 403)
        self.assertNotIn(MENSAJE_SIN_ROL, resp.text.lower())


if __name__ == "__main__":
    unittest.main()