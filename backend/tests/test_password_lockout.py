import unittest
from fastapi.testclient import TestClient
from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.core.constants import MAX_FAILED_LOGIN_ATTEMPTS

class TestPasswordLockout(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Ensure a dedicated test user exists and is unlocked
        self.test_username = "ti"
        user = self.db.query(User).filter(User.username == self.test_username).first()
        if user:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.must_change_password = False
            self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_five_failed_attempts_locks_account(self):
        """Entering incorrect password 5 times locks user account with 403 Forbidden."""
        for attempt in range(1, MAX_FAILED_LOGIN_ATTEMPTS):
            resp = self.client.post("/api/v1/auth/login", json={
                "username": self.test_username,
                "password": "wrongpassword123"
            })
            self.assertEqual(resp.status_code, 401)
            self.assertIn("intento(s)", resp.json()["detail"])

        # 5th failed attempt triggers lockout
        fifth_resp = self.client.post("/api/v1/auth/login", json={
            "username": self.test_username,
            "password": "wrongpassword123"
        })
        self.assertEqual(fifth_resp.status_code, 403)
        self.assertIn("bloqueada", fifth_resp.json()["detail"].lower())

        # Subsequent attempts while locked also return 403
        locked_resp = self.client.post("/api/v1/auth/login", json={
            "username": self.test_username,
            "password": "ti123"
        })
        self.assertEqual(locked_resp.status_code, 403)

    def test_admin_password_reset_and_change_password_flow(self):
        """Admin resets password -> gives temporary password with must_change_password=True -> user logs in and updates password."""
        # 1. Admin logs in
        admin_login = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["access_token"]

        user = self.db.query(User).filter(User.username == "ti").first()
        user_id = user.id

        # 2. Admin resets ti password
        reset_resp = self.client.post(
            f"/api/v1/auth/users/{user_id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(reset_resp.status_code, 200)
        temp_pwd = reset_resp.json()["temporary_password"]
        self.assertTrue(temp_pwd.startswith("Datia-"))

        # 3. User logs in with temporary password
        user_login = self.client.post("/api/v1/auth/login", json={
            "username": "ti",
            "password": temp_pwd
        })
        self.assertEqual(user_login.status_code, 200)
        user_data = user_login.json()
        self.assertTrue(user_data["user"]["must_change_password"])
        user_token = user_data["access_token"]

        # 4. User changes password
        change_resp = self.client.post(
            "/api/v1/auth/change-password",
            json={"old_password": temp_pwd, "new_password": "newSecurePassword123!"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        self.assertEqual(change_resp.status_code, 200)

        # 5. Verify must_change_password flag is now False
        me_resp = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(me_resp.status_code, 200)
        self.assertFalse(me_resp.json()["must_change_password"])
