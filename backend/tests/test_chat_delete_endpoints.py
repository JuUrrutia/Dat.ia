"""
`success: True` cuando no se borro nada.

`delete_chat_thread` ya habia sido corregido (404). Este archivo fija los dos
hermanos que quedaban, y cada uno con SU semantica, que no es la misma:

- `DELETE /widgets/{id}` = "borra ESTE widget". No exista -> 404, igual que el
  hilo. El filtro por `user_id` ya impedia el IDOR; lo que faltaba era que el
  `if w:` sin `else` hacia que un widget inexistente o ajeno respondiera success.
- `DELETE /threads` = "borra todo lo mio". No haya nada -> no-op honesto, NO 404:
  un 404 ahi rompe el segundo click del usuario y cualquier retry de red. Lo que
  se agrega es `deleted_count`, para que el llamador distinga "borre 3" de "no
  habia nada" en lugar de leer un success indistinguible.
"""
import unittest
import uuid

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.chat_engine.models import ChatConversation, DashboardWidget
from app.core.security import create_access_token, get_password_hash

# Usuario propio de este archivo: los endpoints de chat filtran por `user_id`, asi
# que tests que usan cuentas demo se pisan entre si (y con el resto de la suite,
# que es order-dependent). Un usuario dedicado deja los conteos deterministas.
TEST_USERNAME = "test_delete_honesty_user"


class TestDeleteEndpointHonesty(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.jtis = []
        self.headers = {}
        for username in ("admin", TEST_USERNAME):
            user = self.db.query(User).filter(User.username == username).first()
            if user is None:
                user = User(
                    username=username,
                    email=f"{username}@test.local",
                    hashed_password=get_password_hash("x"),
                    is_admin=username == "admin",
                    is_active=True,
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
            jti = str(uuid.uuid4())
            self.db.add(UserSession(user_id=user.id, jti=jti, is_revoked=False))
            self.db.commit()
            self.jtis.append(jti)
            self.headers[username] = {
                "Authorization": f"Bearer {create_access_token(subject=user.id, jti=jti)}"
            }
        self.owner_id = self.db.query(User).filter(
            User.username == TEST_USERNAME
        ).first().id

    def tearDown(self):
        self.db.query(ChatConversation).filter(
            ChatConversation.user_id == self.owner_id
        ).delete(synchronize_session=False)
        self.db.query(DashboardWidget).filter(
            DashboardWidget.user_id == self.owner_id
        ).delete(synchronize_session=False)
        self.db.query(UserSession).filter(UserSession.jti.in_(self.jtis)).delete()
        self.db.commit()
        self.db.close()

    def _pin_widget(self):
        res = self.client.post(
            "/api/v1/chat/widgets",
            json={
                "title": "widget-honesty",
                "chart_type": "bar",
                "chart_option_json": "{}",
                "connection_id": 1,
            },
            headers=self.headers[TEST_USERNAME],
        )
        self.assertEqual(res.status_code, 201, res.text[:300])
        return res.json()["id"]

    def _save_thread(self, thread_id):
        res = self.client.post(
            "/api/v1/chat/threads",
            json={"id": thread_id, "title": "hilo", "connection_id": 1, "results": []},
            headers=self.headers[TEST_USERNAME],
        )
        self.assertEqual(res.status_code, 200, res.text[:300])

    # --- widgets: 404 cuando no hay nada que borrar ----------------------

    def test_unpin_missing_widget_returns_404(self):
        res = self.client.delete(
            "/api/v1/chat/widgets/999999", headers=self.headers[TEST_USERNAME]
        )
        self.assertEqual(res.status_code, 404, res.text[:300])
        self.assertNotIn("success", res.json())

    def test_unpin_another_users_widget_returns_404(self):
        widget_id = self._pin_widget()
        res = self.client.delete(
            f"/api/v1/chat/widgets/{widget_id}", headers=self.headers["admin"]
        )
        self.assertEqual(res.status_code, 404, res.text[:300])
        # Y el widget ajeno sigue existiendo.
        self.db.expire_all()
        self.assertIsNotNone(
            self.db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
        )

    def test_unpin_own_widget_still_succeeds_then_404(self):
        widget_id = self._pin_widget()
        ok = self.client.delete(
            f"/api/v1/chat/widgets/{widget_id}", headers=self.headers[TEST_USERNAME]
        )
        self.assertEqual(ok.status_code, 200, ok.text[:300])
        self.assertTrue(ok.json()["success"])

        again = self.client.delete(
            f"/api/v1/chat/widgets/{widget_id}", headers=self.headers[TEST_USERNAME]
        )
        self.assertEqual(again.status_code, 404)

    # --- clear all: no-op honesto, con conteo ---------------------------

    def test_clear_all_with_nothing_is_a_honest_noop(self):
        """Sin 404: "borra todo lo mio" sin nada que borrar es un no-op, no un error."""
        res = self.client.delete("/api/v1/chat/threads", headers=self.headers[TEST_USERNAME])
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["deleted_count"], 0)
        self.assertIn("No había", res.json()["message"])

    def test_clear_all_reports_how_many_it_deleted(self):
        for i in range(2):
            self._save_thread(f"test-del-honesty-{i}")
        res = self.client.delete("/api/v1/chat/threads", headers=self.headers[TEST_USERNAME])
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.json()["deleted_count"], 2)

        # Segundo click: ya no hay nada, y el llamador lo puede distinguir.
        again = self.client.delete("/api/v1/chat/threads", headers=self.headers[TEST_USERNAME])
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["deleted_count"], 0)

    def test_clear_all_only_deletes_own_threads(self):
        """Un clear de un usuario no toca los hilos de otro (y el conteo lo refleja)."""
        self._save_thread("test-del-honesty-mio")
        admin_thread = "test-del-honesty-admin"
        res = self.client.post(
            "/api/v1/chat/threads",
            json={"id": admin_thread, "title": "hilo", "connection_id": 1, "results": []},
            headers=self.headers["admin"],
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        try:
            res = self.client.delete("/api/v1/chat/threads", headers=self.headers[TEST_USERNAME])
            self.assertEqual(res.json()["deleted_count"], 1)
            self.db.expire_all()
            self.assertEqual(
                self.db.query(ChatConversation).filter(
                    ChatConversation.id == "test-del-honesty-mio"
                ).count(),
                0,
            )
            self.assertEqual(
                self.db.query(ChatConversation).filter(
                    ChatConversation.id == admin_thread
                ).count(),
                1,
                "el clear borro un hilo de otro usuario",
            )
        finally:
            self.db.query(ChatConversation).filter(
                ChatConversation.id == admin_thread
            ).delete(synchronize_session=False)
            self.db.commit()


if __name__ == "__main__":
    unittest.main()
