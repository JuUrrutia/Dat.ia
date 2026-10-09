import unittest
from fastapi.testclient import TestClient
from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db


class TestAdminEndpointAuth(unittest.TestCase):
    """
    Governance endpoints /auth/users and /auth/roles leaked the full user
    table (incl. locked_until) and the role catalog to anonymous callers.
    """

    PROTECTED = ["/api/v1/auth/users", "/api/v1/auth/roles"]

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)

    def _token(self, username: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        self.assertEqual(resp.status_code, 200)
        return resp.json()["access_token"]

    def test_anonymous_gets_401(self):
        for path in self.PROTECTED:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_non_admin_gets_403(self):
        headers = {"Authorization": f"Bearer {self._token('economista', 'economista123')}"}
        for path in self.PROTECTED:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers=headers).status_code, 403)

    def test_admin_gets_200(self):
        headers = {"Authorization": f"Bearer {self._token('admin', 'admin123')}"}
        for path in self.PROTECTED:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers=headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()