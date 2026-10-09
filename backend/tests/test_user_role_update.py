"""
`PATCH /auth/users/{user_id}`: actualizacion de rol e `is_admin`.

La UI (AdminUsersTab) prometa "Editar Rol" y lo que habia era un boton que
guardaba en localStorage y decia "actualizado exitosamente": no habia endpoint
(`auth/router.py` no exponia ninguno) y un reload deshacia el cambio. Estos
tests fijan la capacidad real y, sobre todo, sus limites: sin ellos, un
endpoint de escalacion de privilegios es un 403 de decorado.

Casos:
  1. no-admin -> 403
  2. admin cambia el rol -> el usuario queda con el rol nuevo (y la respuesta lo confirma)
  3. admin NO puede quitarse `is_admin` a si mismo
  4. admin NO puede quitarle `is_admin` al ultimo admin
  5. rol inexistente -> 4xx, no se guarda el string suelto
  6. body {} -> 400, no un no-op que responda 200
  7. subir `is_admin` exige admin: ser el destinatario no alcanza

Todos los usuarios llevan prefijo `test_roleupd_` y se borran en tearDown: la
suite es order-dependent y las cuentas demo se usan en otros archivos.
"""
import unittest
import uuid

from fastapi.testclient import TestClient

from main import app  # noqa: F401
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, Role, UserSession
from app.core.constants import (ROLE_ADMINISTRADOR, ROLE_ANALISTA_FINANCIERO, ROLE_INGENIERO_TI)
from app.core.security import create_access_token, get_password_hash

PREFIX = "test_roleupd_"


class TestUserRoleUpdate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.jtis = []
        self._created = []
        # Admin propio de este archivo. Se usa el admin de demo solo como
        # referencia de "ultimo admin" cuando hace falta, nunca como actor.
        self.admin_id = self._make(f"{PREFIX}admin", is_admin=True, role_name=ROLE_ADMINISTRADOR)
        self.plain_id = self._make(f"{PREFIX}plain", is_admin=False, role_name=ROLE_ANALISTA_FINANCIERO)
        self.target_id = self._make(f"{PREFIX}target", is_admin=False, role_name=ROLE_ANALISTA_FINANCIERO)

    def tearDown(self):
        ids = [u.id for u in self.db.query(User).filter(User.username.like(f"{PREFIX}%")).all()]
        if ids:
            self.db.query(UserSession).filter(UserSession.user_id.in_(ids)).delete(
                synchronize_session=False
            )
            self.db.query(User).filter(User.id.in_(ids)).delete(synchronize_session=False)
            self.db.commit()
        self.db.close()

    # --- helpers ----------------------------------------------------------

    def _make(self, username, is_admin, role_name):
        user = User(
            username=username,
            email=f"{username}@test.local",
            hashed_password=get_password_hash("clave-de-prueba"),
            is_admin=is_admin,
            is_active=True,
            must_change_password=False,
        )
        if role_name:
            role = self.db.query(Role).filter(Role.name == role_name).first()
            self.assertIsNotNone(role, f"el catalogo no tiene el rol {role_name}")
            user.role_id = role.id
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self._created.append(user.id)
        return user.id

    def _headers(self, user_id):
        jti = str(uuid.uuid4())
        self.db.add(UserSession(user_id=user_id, jti=jti, is_revoked=False))
        self.db.commit()
        self.jtis.append(jti)
        return {"Authorization": f"Bearer {create_access_token(subject=user_id, jti=jti)}"}

    def _patch(self, target_id, body, as_user_id):
        return self.client.patch(
            f"/api/v1/auth/users/{target_id}",
            json=body,
            headers=self._headers(as_user_id),
        )

    def _role_of(self, user_id):
        self.db.expire_all()
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.role.name if user.role else None

    # --- 1. quien no es admin no entra -------------------------------------

    def test_non_admin_gets_403(self):
        res = self._patch(self.target_id, {"role": ROLE_INGENIERO_TI}, as_user_id=self.plain_id)
        self.assertEqual(res.status_code, 403, res.text[:300])
        self.assertEqual(self._role_of(self.target_id), ROLE_ANALISTA_FINANCIERO)

    def test_anonymous_gets_401(self):
        res = self.client.patch(f"/api/v1/auth/users/{self.target_id}", json={"role": ROLE_INGENIERO_TI})
        self.assertEqual(res.status_code, 401, res.text[:300])

    # --- 2. el admin cambia el rol y el usuario queda con el rol nuevo ------

    def test_admin_changes_role_and_response_confirms_it(self):
        res = self._patch(self.target_id, {"role": ROLE_INGENIERO_TI}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 200, res.text[:300])
        # La UI afirma contra la respuesta del servidor, asi que la respuesta
        # tiene que traer el rol nuevo y no el viejo.
        self.assertEqual(res.json()["role_name"], ROLE_INGENIERO_TI)
        self.assertEqual(self._role_of(self.target_id), ROLE_INGENIERO_TI)

    def test_admin_can_change_only_is_admin(self):
        res = self._patch(self.target_id, {"is_admin": True}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertTrue(res.json()["is_admin"])
        self.db.expire_all()
        self.assertTrue(
            self.db.query(User).filter(User.id == self.target_id).first().is_admin
        )

    def test_unknown_user_returns_404(self):
        res = self._patch(999999, {"role": ROLE_INGENIERO_TI}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 404, res.text[:300])

    # --- 3. un admin no se degrada a si mismo -------------------------------

    def test_admin_cannot_remove_own_is_admin(self):
        res = self._patch(self.admin_id, {"is_admin": False}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 400, res.text[:300])
        self.db.expire_all()
        self.assertTrue(
            self.db.query(User).filter(User.id == self.admin_id).first().is_admin,
            "el admin se quito sus propios permisos",
        )

    def test_admin_cannot_remove_own_admin_rights_by_moving_own_role(self):
        """El bloqueo no mira solo `is_admin`.

        `get_current_admin` acepta tambien el rol de catalogo, asi que un usuario
        con rol "Administrador de Plataforma" e `is_admin=False` administra igual.
        Moverle el rol a uno no-admin es degradarse a si mismo aunque el body no
        toque `is_admin`, asi que da el mismo 400."""
        role_admin_id = self._make(
            f"{PREFIX}roleadmin", is_admin=False, role_name=ROLE_ADMINISTRADOR
        )
        res = self._patch(role_admin_id, {"role": ROLE_ANALISTA_FINANCIERO}, as_user_id=role_admin_id)
        self.assertEqual(res.status_code, 400, res.text[:300])
        self.assertEqual(self._role_of(role_admin_id), ROLE_ADMINISTRADOR)

    def test_role_change_does_not_degrade_when_is_admin_stays_true(self):
        """Contrapunto del anterior: cambiar el rol no degrada a nadie si el flag
        `is_admin` sigue en True."""
        res = self._patch(self.admin_id, {"role": ROLE_ANALISTA_FINANCIERO}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["role_name"], ROLE_ANALISTA_FINANCIERO)
        self.assertTrue(res.json()["is_admin"])

    # --- 4. el ultimo admin no se puede degradar ----------------------------

    def test_admin_cannot_remove_is_admin_from_the_last_admin(self):
        # El admin de demo es el unico admin del sistema fuera de los usuarios de
        # este archivo, asi que primero hay que apartarlo (restaurandolo al final).
        demo_admin = self.db.query(User).filter(User.username == "admin").first()
        demo_snapshot = (demo_admin.is_active, demo_admin.is_admin)
        try:
            demo_admin.is_active = False
            self.db.commit()

            res = self._patch(self.admin_id, {"is_admin": False}, as_user_id=self.admin_id)
            # Da igual si el error venga por "no te degrades a vos" o por "es el
            # ultimo": lo que no puede pasar es que devuelva 200.
            self.assertEqual(res.status_code, 400, res.text[:300])
            self.db.expire_all()
            self.assertTrue(
                self.db.query(User).filter(User.id == self.admin_id).first().is_admin,
                "el sistema se quedo sin ningun administrador",
            )
        finally:
            demo_admin.is_active, demo_admin.is_admin = demo_snapshot
            self.db.commit()

    def test_last_admin_can_be_demoted_when_another_admin_exists(self):
        """La salvaguarda es "queda al menos uno", no "nunca se degrada"."""
        second_admin = self._make(f"{PREFIX}admin2", is_admin=True, role_name=ROLE_ADMINISTRADOR)
        res = self._patch(self.admin_id, {"is_admin": False}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 400, res.text[:300])

        # Ahora que hay otro admin, un admin distinto si puede degradarlo.
        res = self._patch(self.admin_id, {"is_admin": False}, as_user_id=second_admin)
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertFalse(res.json()["is_admin"])

    # --- 5. rol inexistente -------------------------------------------------

    def test_unknown_role_is_rejected_and_not_stored(self):
        res = self._patch(
            self.target_id, {"role": "Super Admin Inventado"}, as_user_id=self.admin_id
        )
        self.assertEqual(res.status_code, 400, res.text[:300])
        # Y lo importante: no queda el string suelto, que despues no matchea
        # ningun rol y rompe el badge.
        self.assertEqual(self._role_of(self.target_id), ROLE_ANALISTA_FINANCIERO)

    def test_empty_role_string_is_rejected(self):
        res = self._patch(self.target_id, {"role": "   "}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 400, res.text[:300])
        self.assertEqual(self._role_of(self.target_id), ROLE_ANALISTA_FINANCIERO)

    # --- 6. body vacio ------------------------------------------------------

    def test_empty_body_is_400_not_a_silent_noop(self):
        res = self._patch(self.target_id, {}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 400, res.text[:300])

    def test_body_with_only_nulls_is_400(self):
        res = self._patch(
            self.target_id, {"role": None, "is_admin": None}, as_user_id=self.admin_id
        )
        self.assertEqual(res.status_code, 400, res.text[:300])

    # --- 7. la escalada exige admin, no basta con ser el destinatario ------

    def test_granting_is_admin_requires_admin_caller(self):
        """El destinatario no se auto-promueve: `get_current_admin` corre antes
        de tocar nada, asi que un no-admin recibe 403 aunque sea el usuario
       _TARGET_ del PATCH."""
        res = self._patch(self.plain_id, {"is_admin": True}, as_user_id=self.plain_id)
        self.assertEqual(res.status_code, 403, res.text[:300])
        self.db.expire_all()
        self.assertFalse(
            self.db.query(User).filter(User.id == self.plain_id).first().is_admin,
            "un usuario se auto-otorgó is_admin",
        )

    def test_non_admin_cannot_revoke_admin_rights_either(self):
        res = self._patch(self.admin_id, {"is_admin": False}, as_user_id=self.plain_id)
        self.assertEqual(res.status_code, 403, res.text[:300])
        self.db.expire_all()
        self.assertTrue(
            self.db.query(User).filter(User.id == self.admin_id).first().is_admin
        )

    # --- sesiones: bajar permisos corta las sesiones abiertas ---------------

    def test_removing_admin_rights_revokes_open_sessions(self):
        """El JWT es de 24h y no lleva el rol adentro: si no se revocan, el token
        emitido con permisos altos sigue sirviendo hasta expirar."""
        target_session_jti = str(uuid.uuid4())
        target = self.db.query(User).filter(User.id == self.target_id).first()
        target.is_admin = True
        self.db.add(UserSession(user_id=target.id, jti=target_session_jti, is_revoked=False))
        self.db.commit()

        second_admin = self._make(f"{PREFIX}admin3", is_admin=True, role_name=ROLE_ADMINISTRADOR)
        token = None
        # Login de verdad para el objetivo, con su sesion propia.
        res = self.client.post("/api/v1/auth/login", json={
            "username": f"{PREFIX}target", "password": "clave-de-prueba",
        })
        self.assertEqual(res.status_code, 200, res.text[:300])
        token = res.json()["access_token"]
        self.assertEqual(
            self.client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {token}"}).status_code,
            200,
            "el admin de prueba no entraba a /auth/users antes de degradarlo",
        )

        res = self._patch(self.target_id, {"is_admin": False}, as_user_id=second_admin)
        self.assertEqual(res.status_code, 200, res.text[:300])

        after = self.client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(after.status_code, 401, "la sesion del usuario degradado sigue viva")
        self.assertIsNotNone(second_admin)

    def test_changing_role_alone_does_not_revoke_sessions(self):
        """Cambiar el perfil no es cambiar el acceso: el rol se relee de la base
        en cada request, asi que revocar aqui solo expulsaria al usuario."""
        res = self.client.post("/api/v1/auth/login", json={
            "username": f"{PREFIX}target", "password": "clave-de-prueba",
        })
        token = res.json()["access_token"]

        res = self._patch(self.target_id, {"role": ROLE_INGENIERO_TI}, as_user_id=self.admin_id)
        self.assertEqual(res.status_code, 200, res.text[:300])

        still = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(still.status_code, 200, still.text[:300])
        self.assertEqual(still.json()["role_name"], ROLE_INGENIERO_TI)


if __name__ == "__main__":
    unittest.main()
