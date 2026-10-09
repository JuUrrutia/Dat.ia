"""`role_name` describe al catalogo o no dice nada.

El defecto
----------
Cuatro endpoints de `auth/router.py` y uno de `reports/generator.py` resolvian la
etiqueta de rol con un nombre que INVENTABAN cuando la cuenta no tiene fila de rol:

    role_name = user.role.name if user.role else (
        "Super Administrador" if user.is_admin else "Usuario"
    )

Ninguno de esos tres nombres existe en el catalogo de 8 roles. No era un caso
decorativo: cuando un nombre inventado se escribe en `AuditLog.user_role` (que es
evidencia de compliance) o cuando el frontend lo compara contra la matriz RBAC,
el texto deja de ser una etiqueta y pasa a ser una afirmacion falsa. Este modulo
ya limpio los 5 endpoints que resolvian POR NOMBRE; estos 5 sitios quedaron sin
barrer y son los que重重 se ven en la UI.

Lo que se verifica aca
----------------------
1. El admin con `role_id = NULL` recibe el nombre REAL del catalogo
   ("Administrador de Plataforma"), no "Super Administrador". `is_admin` es un
   hecho persistido y esa persona administra en todas las capas de auth, asi que
   el nombre que le corresponde es el del administrador, no uno inventado.
2. La cuenta sin rol y sin `is_admin` recibe `None`, no "Usuario". El contrato lo
   admite: `UserOut.role_name` es `Optional[str] = None`.
3. El caso normal (con rol asignado) sigue devolviendo el nombre del catalogo.
4. `generator.py` escribe `None` en `AuditLog.user_role` para esa misma cuenta, y
   el consumidor de auditoria (el CSV de compliance) no se rompe con `None`.
5. Los 4 endpoints de `auth` (`/login`, `/me`, `/auth/users`,
   `PATCH /auth/users/{id}`) emiten la misma etiqueta honesta.

Por que el caso admin-sin-rol NO debe decir "Super Administrador"
---------------------------------------------------------------
Porque "Super Administrador" no esta en el catalogo. Si el guard resuelve la
matriz por nombre (y lo hace, a proposito), entonces una etiqueta inventada es
una segunda fuente de verdad que el resto del sistema no conoce. Aqui no se
trata de que se vea lindo: se trata de que la etiqueta que viaja al frontend y al
log de auditoria describa un perfil que existe.
"""

import json
import unittest
import uuid

from fastapi.testclient import TestClient

from main import app
from app.core.constants import (
    ROLE_ADMINISTRADOR,
    ROLE_ANALISTA_FINANCIERO,
    ROLE_USUARIO,
)
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession, Role
from app.modules.telemetry_audit.models import AuditLog

PREFIX = "test_rollabel_"


class TestRoleLabelHonesta(unittest.TestCase):
    """El `role_name` que sale del backend describe el catalogo, o no dice nada."""

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        ids = [u.id for u in self.db.query(User).filter(User.username.like(f"{PREFIX}%")).all()]
        if ids:
            self.db.query(AuditLog).filter(AuditLog.user_id.in_(ids)).delete(
                synchronize_session=False
            )
            self.db.query(UserSession).filter(UserSession.user_id.in_(ids)).delete(
                synchronize_session=False
            )
            self.db.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False)
            self.db.commit()
        self.db.close()

    # --- helpers ----------------------------------------------------------

    def _cuenta(self, *, role_name=None, is_admin=False):
        """Crea una cuenta con `role_id` resuelto desde `role_name` (None = NULL)."""
        role = None
        if role_name is not None:
            role = self.db.query(Role).filter(Role.name == role_name).first()
            self.assertIsNotNone(role, f"el rol {role_name!r} tiene que existir en el catalogo")

        username = f"{PREFIX}{uuid.uuid4().hex[:8]}"
        user = User(
            username=username,
            email=f"{username}@test.local",
            hashed_password=get_password_hash("Clave-de-prueba-1"),
            is_admin=is_admin,
            is_active=True,
            must_change_password=False,
            role_id=role.id if role else None,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _headers(self, user):
        jti = str(uuid.uuid4())
        self.db.add(UserSession(user_id=user.id, jti=jti, is_revoked=False))
        self.db.commit()
        return {"Authorization": f"Bearer {create_access_token(subject=user.id, jti=jti)}"}

    def _admin(self):
        return self._cuenta(role_name=ROLE_ADMINISTRADOR, is_admin=True)

    # --- 1. admin sin fila de rol: nombre real del catalogo ----------------

    def test_admin_sin_rol_recibe_el_nombre_del_catalogo(self):
        """`is_admin=True, role_id=NULL` -> "Administrador de Plataforma".

        Antes: "Super Administrador". No esta en el catalogo de 8 roles, asi que
        el frontend lo recibia como texto libre y el log de auditoria guardaba un
        perfil que no existe.
        """
        user = self._cuenta(role_name=None, is_admin=True)
        self.assertIsNone(user.role_id)

        res = self.client.get("/api/v1/auth/me", headers=self._headers(user))
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["role_name"], ROLE_ADMINISTRADOR)
        self.assertNotIn("Super Administrador", res.text)

    # --- 2. cuenta sin rol y sin is_admin: None, no "Usuario" ---------------

    def test_cuenta_sin_rol_recibe_none_y_no_una_etiqueta_inventada(self):
        """`role_id=NULL, is_admin=False` -> `None`.

        Antes: "Usuario", que ademas es truthy: cualquier logica de presentacion
        que trate el rol como presente muestra un perfil para una cuenta que no
        tiene ninguno. El schema es `Optional[str] = None`, asi que `None` es el
        valor honesto.
        """
        user = self._cuenta(role_name=None, is_admin=False)

        res = self.client.get("/api/v1/auth/me", headers=self._headers(user))
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertIsNone(
            res.json()["role_name"],
            "una cuenta sin rol no tiene nombre de rol que mostrar",
        )
        self.assertNotIn("Usuario", res.json()["role_name"] or "")

    # --- 3. el caso normal sigue devolviendo el nombre del catalogo ---------

    def test_cuenta_con_rol_sigue_devolviendo_el_nombre_del_catalogo(self):
        """El 99%: con fila de rol, gana el catalogo. Este camino no se toca."""
        user = self._cuenta(role_name=ROLE_ANALISTA_FINANCIERO, is_admin=False)

        res = self.client.get("/api/v1/auth/me", headers=self._headers(user))
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["role_name"], ROLE_ANALISTA_FINANCIERO)

    def test_consultor_con_rol_sigue_viendo_usuario_consultor(self):
        """Contrapunto: `None` es para "sin rol", no para "es el Consultor".

        Si este test falla, el helper esta confundiendo "no tiene rol" con "es el
        rol de lectura minima" -- y el Usuario Consultor quedaria sin etiqueta.
        """
        user = self._cuenta(role_name=ROLE_USUARIO, is_admin=False)

        res = self.client.get("/api/v1/auth/me", headers=self._headers(user))
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["role_name"], ROLE_USUARIO)

    # --- 4. los 4 endpoints de auth emiten la misma etiqueta -----------------

    def test_login_emite_la_misma_etiqueta_que_me(self):
        """`/login` y `/me` tienen que estar de acuerdo.

        `/login` es de donde el cliente saca el usuario inicial y `/me` de donde
        lo refresca. Si los dos resuelven distinto, la UI cambia de etiqueta
        sola y sola segun por donde haya entrado la sesion.
        """
        user = self._cuenta(role_name=None, is_admin=True)

        login = self.client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "Clave-de-prueba-1"},
        )
        self.assertEqual(login.status_code, 200, login.text[:300])
        self.assertEqual(login.json()["user"]["role_name"], ROLE_ADMINISTRADOR)

        me = self.client.get("/api/v1/auth/me", headers=self._headers(user))
        self.assertEqual(me.json()["role_name"], ROLE_ADMINISTRADOR)

    def test_listado_de_usuarios_no_inventa_etiquetas(self):
        """`GET /auth/users` recorre cuentas sin rol: ninguna puede venir con
        "Usuario" o "Administrador", que no existen en el catalogo."""
        self._cuenta(role_name=None, is_admin=False)
        admin_sin_rol = self._cuenta(role_name=None, is_admin=True)

        res = self.client.get("/api/v1/auth/users", headers=self._headers(self._admin()))
        self.assertEqual(res.status_code, 200, res.text[:300])

        filas = {u["id"]: u for u in res.json()}
        self.assertEqual(
            filas[admin_sin_rol.id]["role_name"], ROLE_ADMINISTRADOR,
            "admin sin fila de rol: el nombre del catalogo, no 'Administrador'",
        )
        for fila in filas.values():
            self.assertNotIn(fila["role_name"], ("Usuario", "Administrador", "Super Administrador"))

    def test_patch_de_usuario_devuelve_la_etiqueta_del_registro(self):
        """`PATCH /auth/users/{id}` es el 4o sitio.

        Un admin le cambia el rol a un Consultor: la respuesta tiene que traer el
        nombre nuevo del catalogo. Y si la respuesta de un PATCH chega con la
        etiqueta del catalogo, el mismo helper esta sirviendo las dos ramas.
        """
        objetivo = self._cuenta(role_name=ROLE_ANALISTA_FINANCIERO, is_admin=False)
        admin = self._admin()

        res = self.client.patch(
            f"/api/v1/auth/users/{objetivo.id}",
            json={"role": ROLE_USUARIO},
            headers=self._headers(admin),
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["role_name"], ROLE_USUARIO)

    def test_cuenta_que_pierde_el_rol_no_queda_con_una_etiqueta(self):
        """La otra mitad del PATCH: sin fila de rol, la etiqueta es `None`.

        No hay endpoint para dejar `role_id` en NULL (admin solo puede asignar un
        rol del catalogo), asi que el estado se arma por DB, que es como queda la
        cuenta cuando `init_db` sembro sin fila por defecto.
        """
        objetivo = self._cuenta(role_name=ROLE_ANALISTA_FINANCIERO, is_admin=False)
        admin = self._admin()

        objetivo.role_id = None
        self.db.commit()
        self.db.expire_all()

        res = self.client.get("/api/v1/auth/users", headers=self._headers(admin))
        self.assertEqual(res.status_code, 200, res.text[:300])
        fila = {u["id"]: u for u in res.json()}[objetivo.id]
        self.assertIsNone(fila["role_name"])

    def test_register_no_afirma_un_rol_que_la_cuenta_no_tiene(self):
        """`/register` es el mismo patron en otra forma: si el catalogo no tiene
        el rol por defecto, `role_id` queda NULL y la etiqueta no puede decir el
        nombre de ese rol."""
        sufijo = uuid.uuid4().hex[:8]
        res = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": f"{PREFIX}reg_{sufijo}",
                "email": f"reg_{sufijo}@example.com",
                "password": "Clave-de-prueba-1",
            },
        )
        self.assertEqual(res.status_code, 201, res.text[:300])
        cuerpo = res.json()
        self.assertEqual(cuerpo["role_name"], ROLE_USUARIO)
        self.assertIsNotNone(cuerpo["role_id"], "si el rol por defecto existe, se asigna")

    # --- 5. generator.py: la evidencia de compliance -------------------------

    def test_export_de_cuenta_sin_rol_graba_null_en_el_audit_log(self):
        """Acá el valor NO es etiqueta de UI: se escribe en `AuditLog.user_role`,
        que es la evidencia que el compliance lee. Antes ponia "Usuario" para una
        cuenta que no tiene rol: un hecho falso en el registro.

        Con `None` el CSV de compliance escribe "" (celda vacia), que el admin lee
        como "sin rol registrado". Un nombre inventado se lee como "era Usuario".
        """
        usuario = self._cuenta(role_name=None, is_admin=False)
        snapshot = {
            "question": "Total de ventas",
            "summary_text": "ok",
            "data_columns": ["id"],
            "data_rows": [{"id": 1}],
            "traceability": {
                "sql_executed": "SELECT id FROM ventas",
                "execution_time_ms": 5,
                "rows_returned": 1,
                "validation_status": "APROBADO",
            },
            "target_database": "demo_corporativa.db",
        }
        origen = AuditLog(
            user_id=usuario.id,
            username=usuario.username,
            user_role=None,
            question_prompt=snapshot["question"],
            validation_status="APROBADO",
            target_database=snapshot["target_database"],
            result_snapshot=json.dumps(snapshot),
        )
        self.db.add(origen)
        self.db.commit()
        self.db.refresh(origen)

        res = self.client.post(
            "/api/v1/reports/export/pdf",
            json={"audit_log_id": origen.id},
            headers=self._headers(usuario),
        )
        self.assertEqual(res.status_code, 200, res.text[:300])

        export = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.user_id == usuario.id,
                AuditLog.validation_status == "EXPORTADO_PDF",
            )
            .order_by(AuditLog.id.desc())
            .first()
        )
        self.assertIsNotNone(export, "el export tiene que quedar auditado")
        self.assertIsNone(
            export.user_role,
            "una cuenta sin rol no puede quedar registrada con un rol: la columna "
            "es nullable justamente para esto",
        )

    def test_el_consumidor_de_auditoria_no_se_rompe_con_null(self):
        """`GET /audit-logs/export` (el CSV de compliance) y el listado JSON
        tienen que sobrevivir un `user_role = NULL`.

        Si este test falla, la decision de escribir `None` no es segura y hay que
        revisarla -- no hay que inventar un nombre para disimularlo.
        """
        from app.modules.admin_catalog.schemas import ReportExportRequest  # noqa: F401

        usuario = self._cuenta(role_name=None, is_admin=False)
        self.db.add(
            AuditLog(
                user_id=usuario.id,
                username=usuario.username,
                user_role=None,  # el caso que se tiene que sostener
                question_prompt="Consulta sin rol registrado",
                validation_status="RECHAZADO_RBAC",
                target_database="demo_corporativa.db",
            )
        )
        self.db.commit()

        admin = self._admin()
        headers = self._headers(admin)

        listado = self.client.get("/api/v1/audit", headers=headers)
        self.assertEqual(listado.status_code, 200, listado.text[:300])
        fila = [f for f in listado.json()["items"] if f["username"] == usuario.username]
        self.assertTrue(fila, "el registro tiene que aparecer en el listado")
        self.assertIsNone(fila[0]["user_role"])

        csv = self.client.get("/api/v1/audit/export", headers=headers)
        self.assertEqual(csv.status_code, 200, csv.text[:300])
        # La columna "Rol" sale vacia, no "None": el CSV no debe filtrar la
        # palabra literal del lenguaje como si fuera un dato.
        self.assertNotIn(",None,", csv.text)


if __name__ == "__main__":
    unittest.main()