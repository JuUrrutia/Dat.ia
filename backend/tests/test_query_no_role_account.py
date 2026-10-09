"""Una cuenta SIN rol asignado no entra al chat.

El defecto
----------
`engine.py` corta cuando `not user_role`, o sea cuando el nombre no llego. Pero
`router.py` resolvia el nombre ANTES de llamar al motor, con este fallback:

    user_role_name = current_user.role.name if current_user.role else (
        ROLE_ADMINISTRADOR if current_user.is_admin else ROLE_USUARIO
    )

Una cuenta con `role_id = NULL` y `is_admin = False` caia en `"Usuario Consultor"`,
que es truthy: el gate no disparaba y `/chat/query` devolvia `data_analysis`. El
mismo caso en `/predict` SI bloqueaba, porque ese endpoint mira el objeto
(`not current_user.role`) y no el nombre. Los dos endpoints divergian sobre la
misma cuenta y el mismo hecho.

Lo que se verifica aca, con usuarios de verdad y JWT de verdad
--------------------------------------------------------------
1. `POST /chat/query` con `role_id = NULL, is_admin = False` responde 403 y lo
   dice. Sin esto, el test pasaria por la rama equivocada: sin LLM local la
   request falla por conexion, no por RBAC, y "no fue 200" no prueba nada.
   Lo que se afirma es el status Y el texto de gobernanza.
2. La denegacion queda en auditoria. Un corte que no deja rastro no es un corte.
3. Contrapunto: el Usuario Consultor CON su rol asignado sigue entrando. El gate
   corta cuentas sin rol, no al rol de lectura minima del catalogo.
4. El admin sin fila de rol sigue siendo admin: `is_admin` manda sobre el rol.

Por que el caso positivo no afirma un 200
------------------------------------------
En este entorno no hay LLM local, asi que la request del Consultor cae por
conexion (RECHAZADO por IA desconectada, o `no_active_connection` si no hay base
encendida). Lo que NO puede aparecer es el 403 ni el texto "no tiene un rol
asignado": si el gate se cerrara al Consultor, el status seria 403 y el mensaje
seria el de la denegacion.
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


class TestChatQueryCuentaSinRol(unittest.TestCase):
    """Una cuenta real con `role_id = NULL`, no un `MagicMock` de User."""

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
                self.db.delete(user)
        self.db.commit()
        self.db.close()

    def _cuenta(self, role_name=None):
        """Crea una cuenta con `role_id` resuelto desde `role_name` (None = NULL)."""
        role = None
        if role_name is not None:
            role = self.db.query(Role).filter(Role.name == role_name).first()
            self.assertIsNotNone(role, f"el rol {role_name!r} tiene que existir en la metadata")

        username = f"test_sinrol_{uuid.uuid4().hex[:8]}"
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password="x",  # nunca se verifica: se entra con JWT
            is_admin=False,
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
        token = create_access_token(subject=user.id, jti=jti)
        return {"Authorization": f"Bearer {token}"}

    # --- 1. El corte, con el caso real -------------------------------------

    def test_cuenta_sin_rol_no_entra_al_chat(self):
        """`role_id = NULL, is_admin = False` -> 403 con el motivo de gobernanza.

        Antes: 200 con `response_type = data_analysis`. El nombre caia en
        "Usuario Consultor" y el gate de `engine.py` no lo veia.
        """
        user = self._cuenta(role_name=None)
        self.assertIsNone(user.role_id)
        self.assertFalse(user.is_admin)

        resp = self.client.post(
            "/api/v1/chat/query",
            json={"question": "Total de ventas del ultimo trimestre", "connection_id": 1},
            headers=self._headers(user),
        )

        self.assertEqual(
            resp.status_code, 403,
            "una cuenta sin rol asignado no puede consultar datos corporativos",
        )
        detalle = str(resp.json().get("detail", ""))
        self.assertIn(
            MENSAJE_SIN_ROL, detalle.lower(),
            "el 403 tiene que decir POR QUE: sin rol, no hay nada que explicar",
        )

    def test_el_403_tambien_corta_el_stream(self):
        """`/chat/query/stream` es el camino por defecto del cliente.

        El corte va ANTES de abrir el stream: una vez enviadas las cabeceras, un
        rechazo solo puede viajar como evento `error`, que el cliente trata como
        "el servidor se cayo" y reintenta por `/chat/query`. Si este test falla,
        el gate quedo del lado equivocado.
        """
        user = self._cuenta(role_name=None)

        resp = self.client.post(
            "/api/v1/chat/query/stream",
            json={"question": "Total de ventas", "connection_id": 1},
            headers=self._headers(user),
        )
        self.assertEqual(
            resp.status_code, 403,
            "el corte tiene que ser un 403 HTTP, no un evento SSE de error: "
            "con las cabeceras ya enviadas el cliente no lo distingue de una caida",
        )
        self.assertIn(MENSAJE_SIN_ROL, resp.text.lower())

    # --- 2. La denegacion deja rastro ---------------------------------------

    def test_la_denegacion_queda_en_auditoria(self):
        """Un corte sin registro no es un corte: el compliance lo tiene que ver."""
        user = self._cuenta(role_name=None)
        headers = self._headers(user)

        self.client.post(
            "/api/v1/chat/query",
            json={"question": "Total de ventas", "connection_id": 1},
            headers=headers,
        )

        entry = (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user.id)
            .order_by(AuditLog.id.desc())
            .first()
        )
        self.assertIsNotNone(entry, "la denegacion tiene que quedar registrada")
        self.assertEqual(entry.validation_status, "RECHAZADO_RBAC")
        # `user_role` nullable existe para este caso: afirmar "Usuario Consultor"
        # en el log seria inventar el rol que la cuenta no tiene.
        self.assertIsNone(entry.user_role)
        self.assertEqual(entry.rows_returned, 0)

    # --- 3. Contrapunto: el Consultor con rol sigue entrando ----------------

    def test_consultor_con_rol_asignado_no_es_bloqueado(self):
        """El gate corta "sin rol", no "es el Consultor".

        Si este test falla, el gate volvio a bloquear por nombre y el Usuario
        Consultor -- un rol del catalogo con lectura minima declarada -- quedo
        como un perfil que no puede hacer nada.
        """
        user = self._cuenta(role_name=ROLE_USUARIO)
        self.assertIsNotNone(user.role_id)

        resp = self.client.post(
            "/api/v1/chat/query",
            json={"question": "Total de ventas del ultimo trimestre", "connection_id": 1},
            headers=self._headers(user),
        )

        self.assertNotEqual(
            resp.status_code, 403,
            "el Consultor tiene rol asignado y tablas declaradas: no es una cuenta sin rol",
        )
        cuerpo = resp.text.lower()
        self.assertNotIn(
            MENSAJE_SIN_ROL, cuerpo,
            "el mensaje de 'no tenes rol' es de otra cuenta",
        )

    # --- 4. El admin sin fila de rol sigue siendo admin --------------------

    def test_admin_sin_rol_no_es_bloqueado(self):
        """`is_admin` manda sobre la fila de rol: no se rompio ese fallback."""
        user = self._cuenta(role_name=None)
        user.is_admin = True
        self.db.commit()

        resp = self.client.post(
            "/api/v1/chat/query",
            json={"question": "Total de ventas del ultimo trimestre", "connection_id": 1},
            headers=self._headers(user),
        )

        self.assertNotEqual(resp.status_code, 403)
        self.assertNotIn(MENSAJE_SIN_ROL, resp.text.lower())


if __name__ == "__main__":
    unittest.main()
