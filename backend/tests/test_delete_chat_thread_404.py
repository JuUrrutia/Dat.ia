"""
BUG 9: `DELETE /chat/threads/{id}` respondia `success: True` tanto si el hilo
existia como si no. El filtro por `user_id` ya venia puesto de auditorias
previas (no hay IDOR), lo que quedaba era la mentira: el llamador no podia
distinguir "borre tu hilo" de "no encontre ese hilo".
"""
import uuid
import unittest

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.core.security import create_access_token


class TestDeleteChatThreadNotFound(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.users = {}
        for username in ("admin", "juan_ti"):
            u = self.db.query(User).filter(User.username == username).first()
            jti = str(uuid.uuid4())
            self.db.add(UserSession(user_id=u.id, jti=jti, is_revoked=False))
            self.db.commit()
            self.users[username] = (
                u.id, {"Authorization": f"Bearer {create_access_token(subject=u.id, jti=jti)}"}
            )
        self.thread_id = f"test-delete-404-{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        from sqlalchemy import text
        self.db.execute(text(
            "DELETE FROM chat_conversations WHERE id LIKE 'test-delete-404-%'"))
        self.db.commit()
        self.db.close()

    def _save_thread(self):
        owner_id, headers = self.users["juan_ti"]
        payload = {
            "id": self.thread_id,
            "title": "Hilo de prueba",
            "connection_id": 1,
            "results": [{"summary_text": "contenido"}],
        }
        res = self.client.post("/api/v1/chat/threads", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200, res.text[:300])
        return self.thread_id

    def test_delete_nonexistent_thread_returns_404(self):
        """Un id que no existe tiene que ser 404, no un success:True."""
        _, headers = self.users["admin"]
        res = self.client.delete(
            f"/api/v1/chat/threads/{self.thread_id}", headers=headers)
        self.assertEqual(res.status_code, 404, res.text[:300])
        self.assertNotIn("success", res.json())

    def test_delete_another_users_thread_returns_404(self):
        """El filtro por user_id ya estaba: un hilo ajeno se ve como inexistente."""
        self._save_thread()
        _, admin_headers = self.users["admin"]
        res = self.client.delete(
            f"/api/v1/chat/threads/{self.thread_id}", headers=admin_headers)
        self.assertEqual(res.status_code, 404, res.text[:300])

    def test_delete_own_thread_still_succeeds(self):
        """El camino feliz no se rompió."""
        self._save_thread()
        _, econ_headers = self.users["juan_ti"]
        res = self.client.delete(
            f"/api/v1/chat/threads/{self.thread_id}", headers=econ_headers)
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertTrue(res.json()["success"])

        # Y un segundo DELETE del mismo id ahora sí es 404
        again = self.client.delete(
            f"/api/v1/chat/threads/{self.thread_id}", headers=econ_headers)
        self.assertEqual(again.status_code, 404)
