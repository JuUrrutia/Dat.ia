import unittest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.models.session import UserSession
from app.core.security import create_access_token
from app.core.config import settings

class TestChatSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.economista_user = self.db.query(User).filter(User.username == "felipe_economista").first()
        self.jti = str(uuid.uuid4())
        self.token = create_access_token(subject=self.economista_user.id, jti=self.jti)

        session = UserSession(
            user_id=self.economista_user.id,
            jti=self.jti,
            is_revoked=False
        )
        self.db.add(session)
        self.db.commit()

        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.close()

    def test_chat_query_requires_authentication(self):
        """Without JWT Authorization header, /chat/query returns 401 Unauthorized."""
        resp = self.client.post("/api/v1/chat/query", json={"question": "Total de ventas", "connection_id": 1})
        self.assertEqual(resp.status_code, 401)

    def test_chat_query_derives_role_from_jwt_ignoring_body(self):
        """
        Even if client sends user_role='Administrador' in body, /chat/query strictly
        derives the role from the JWT session (Economista).
        """
        # User Economista attempts to query TI tables with spoofed body role
        resp = self.client.post(
            "/api/v1/chat/query",
            json={
                "question": "SELECT * FROM dim_servidores",
                "user_role": "Administrador",  # Spoofed attempt
                "connection_id": 1
            },
            headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        v_status = data.get("traceability", {}).get("validation_status", "")
        # Must be rejected because JWT user is Economista who cannot access dim_servidores (TI domain)
        self.assertTrue("RECHAZADO" in v_status or "ERROR" in v_status)

    def test_query_open_disabled_by_default_returns_403(self):
        """By default (ALLOW_OPEN_DEMO_ENDPOINT=False), /chat/query-open returns 403 Forbidden."""
        self.assertFalse(settings.ALLOW_OPEN_DEMO_ENDPOINT)
        resp = self.client.post(
            "/api/v1/chat/query-open",
            json={"question": "Total de ventas", "user_role": "Administrador"}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("deshabilitado", resp.json().get("detail", ""))

    def test_query_open_when_enabled_forces_least_privileged_role(self):
        """When ALLOW_OPEN_DEMO_ENDPOINT=True, client-provided user_role is ignored and Usuario role is forced."""
        with patch.object(settings, "ALLOW_OPEN_DEMO_ENDPOINT", True):
            resp = self.client.post(
                "/api/v1/chat/query-open",
                json={"question": "SELECT * FROM fact_ventas", "user_role": "Administrador"}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            v_status = data.get("traceability", {}).get("validation_status", "")
            # Because role is forced to 'Usuario' (which has no domain permissions), access is rejected
            self.assertTrue("RECHAZADO" in v_status or "ERROR" in v_status)
