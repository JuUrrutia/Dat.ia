"""
Bugs 5-6: change-password no revocaba las otras sesiones (la credencial robada
sobrevivia al cambio) y /auth/register aceptaba una contraseña de 1 carácter.
"""
import uuid
import unittest
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.auth.schemas import validate_password_strength, MIN_PASSWORD_LENGTH
from app.core.security import create_access_token, get_password_hash


class TestChangePasswordRevokesSessions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.username == "admin").first()
        self._snapshot = (
            self.user.hashed_password,
            self.user.must_change_password,
            self.user.failed_login_attempts,
            self.user.locked_until,
        )

    def tearDown(self):
        db = SessionLocal()
        u = db.query(User).filter(User.username == "admin").first()
        (u.hashed_password, u.must_change_password,
         u.failed_login_attempts, u.locked_until) = self._snapshot
        db.commit()
        db.close()
        self.db.close()

    def _session_for(self, jti):
        s = UserSession(user_id=self.user.id, jti=jti, is_revoked=False)
        self.db.add(s)
        self.db.commit()
        return create_access_token(subject=self.user.id, jti=jti)

    def test_change_password_revokes_other_sessions_but_keeps_the_current_one(self):
        """BUG 5: el cambio de contraseña no tocaba UserSession, así que un token
        robado seguía valiendo hasta expirar. Ahora revoca las demás y conserva
        la sesión con la que se hizo el cambio."""
        attacker_jti = str(uuid.uuid4())
        victim_jti = str(uuid.uuid4())
        attacker_token = self._session_for(attacker_jti)
        victim_token = self._session_for(victim_jti)

        # Ambas sesiones sirven antes del cambio
        self.assertEqual(self.client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {attacker_token}"}).status_code, 200)

        res = self.client.post("/api/v1/auth/change-password", json={
            "old_password": "admin123",
            "new_password": "admin1234",
        }, headers={"Authorization": f"Bearer {victim_token}"})
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertGreaterEqual(res.json()["revoked_sessions"], 1)

        # La sesión del atacante queda revocada de verdad
        self.db.expire_all()
        attacker = self.db.query(UserSession).filter(UserSession.jti == attacker_jti).first()
        self.assertTrue(attacker.is_revoked, "la sesión ajena sigue viva tras el cambio de contraseña")
        after = self.client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {attacker_token}"})
        self.assertEqual(after.status_code, 401)

        # Y la sesión propia sigue funcionando
        self.assertEqual(self.client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {victim_token}"}).status_code, 200)

    def test_change_password_rejects_short_new_password(self):
        """El mínimo de 6 caracteres se mantiene (ahora compartido con register)."""
        jti = str(uuid.uuid4())
        token = self._session_for(jti)
        res = self.client.post("/api/v1/auth/change-password", json={
            "old_password": "admin123", "new_password": "abc",
        }, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 400)


class TestRegisterPasswordStrength(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        u = self.db.query(User).filter(
            User.username == "pwprobe_user").first()
        if u:
            self.db.delete(u)
            self.db.commit()
        self.db.close()

    def test_register_with_one_char_password_is_rejected(self):
        """BUG 6: `password: str` sin constraint en UserSelfRegister. Con "a" la
        API devolvía 201 y quedaba una credencial de 1 carácter que ni siquiera
        podía normalizarse después (change-password exigía 6)."""
        res = self.client.post("/api/v1/auth/register", json={
            "username": "pwprobe_user",
            "password": "a",
        })
        self.assertEqual(res.status_code, 400, res.text[:300])
        self.assertIsNone(self.db.query(User).filter(User.username == "pwprobe_user").first())

    def test_register_with_valid_password_is_accepted(self):
        """El camino legítimo no se rompió."""
        res = self.client.post("/api/v1/auth/register", json={
            "username": "pwprobe_user",
            "password": "claveValida123",
        })
        self.assertEqual(res.status_code, 201, res.text[:300])
        self.assertIsNotNone(self.db.query(User).filter(User.username == "pwprobe_user").first())

    def test_register_and_change_password_share_one_rule(self):
        """Una sola regla, en un solo lugar."""
        for bad in ("", "a", "abc", "   ", "     "):
            with self.subTest(password=bad):
                with self.assertRaises(ValueError):
                    validate_password_strength(bad)
        self.assertEqual(validate_password_strength("abcdef"), "abcdef")
        self.assertEqual(MIN_PASSWORD_LENGTH, 6)

        # Y el mismo umbral vale para el cambio de contraseña
        jti = str(uuid.uuid4())
        admin = self.db.query(User).filter(User.username == "admin").first()
        self.db.add(UserSession(user_id=admin.id, jti=jti, is_revoked=False))
        self.db.commit()
        token = create_access_token(subject=admin.id, jti=jti)
        res = self.client.post("/api/v1/auth/change-password", json={
            "old_password": "admin123", "new_password": "abc",
        }, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 400)