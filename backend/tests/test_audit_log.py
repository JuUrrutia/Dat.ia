import unittest
from fastapi.testclient import TestClient
from main import app
from app.core.database import SessionLocal, Base, engine
from app.db.init_db import init_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.core.security import create_access_token
from app.models.session import UserSession
import uuid

class TestAuditLog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Ensure admin user exists
        self.admin_user = self.db.query(User).filter(User.username == "admin").first()
        self.admin_jti = str(uuid.uuid4())
        self.admin_token = create_access_token(subject=self.admin_user.id, jti=self.admin_jti)
        
        # Create active session for admin
        session = UserSession(
            user_id=self.admin_user.id,
            jti=self.admin_jti,
            is_revoked=False
        )
        self.db.add(session)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_approved_query_persists_audit_log(self):
        """Approved query against demo endpoint records an AuditLog with validation_status APROBADO."""
        initial_count = self.db.query(AuditLog).count()

        headers = {"Authorization": f"Bearer {self.admin_token}"}
        resp = self.client.post(
            "/api/v1/chat/query",
            json={"question": "hola buenos dias", "connection_id": 1},
            headers=headers
        )
        self.assertEqual(resp.status_code, 200)

        new_count = self.db.query(AuditLog).count()
        self.assertGreater(new_count, initial_count)

        latest_log = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        self.assertEqual(latest_log.username, "admin")
        self.assertTrue("APROBADO" in latest_log.validation_status)
        self.assertEqual(latest_log.question_prompt, "hola buenos dias")

    def test_rejected_rbac_query_persists_audit_log(self):
        """Rejected query (e.g. forbidden SQL) records an AuditLog with RECHAZADO status via /chat/query."""
        user = self.db.query(User).filter(User.username == "felipe_economista").first()
        jti = str(uuid.uuid4())
        user_token = create_access_token(subject=user.id, jti=jti)
        session = UserSession(user_id=user.id, jti=jti, is_revoked=False)
        self.db.add(session)
        self.db.commit()

        headers = {"Authorization": f"Bearer {user_token}"}
        resp = self.client.post(
            "/api/v1/chat/query",
            json={"question": "DROP TABLE fact_ventas", "connection_id": 1},
            headers=headers
        )
        self.assertEqual(resp.status_code, 200)

        latest_log = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        self.assertEqual(latest_log.username, "felipe_economista")
        self.assertTrue("RECHAZADO" in latest_log.validation_status or "ERROR" in latest_log.validation_status)

    def test_audit_list_and_export_endpoints(self):
        """Admin can list and export audit logs via /api/v1/audit and /api/v1/audit/export."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        # 1. List audit logs
        list_resp = self.client.get("/api/v1/audit?page=1&page_size=10", headers=headers)
        self.assertEqual(list_resp.status_code, 200)
        data = list_resp.json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(len(data["items"]), 1)

        # 2. Export CSV
        csv_resp = self.client.get("/api/v1/audit/export", headers=headers)
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("text/csv", csv_resp.headers.get("content-type", ""))
        self.assertIn("Fecha", csv_resp.text)
        self.assertIn("Usuario", csv_resp.text)
