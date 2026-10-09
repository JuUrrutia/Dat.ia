"""Los hilos de chat no son accesibles entre usuarios.

Los mensajes de un hilo guardan `data_rows`: filas reales de la base corporativa.
Por eso el aislamiento por `user_id` no es cosmetico.

Vulnerabilidades que cubre:
  1. `GET /threads/shared/{id}` filtraba solo por id: cualquier usuario autenticado
     que conociera un id leia el historial de otro.
  2. `POST /threads` buscaba por id sin `user_id`: se podia sobrescribir el hilo
     ajeno y además reasignarselo (`thread.user_id = current_user.id`).
"""
import unittest

from fastapi.testclient import TestClient

from main import app  # noqa: F401

from app.core.database import SessionLocal
from sqlalchemy import text


class TestChatThreadIsolation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.execute(text("DELETE FROM chat_conversations WHERE id LIKE 'test-idor-%'"))
        self.db.commit()
        self.db.close()

    def _token(self, username, password):
        r = self.client.post("/api/v1/auth/login", json={"username": username, "password": password})
        self.assertEqual(r.status_code, 200, r.text[:200])
        return r.json()["access_token"]

    def _save(self, token, thread_id, **extra):
        payload = {
            "id": thread_id,
            "title": "Consulta de ingresos",
            "connection_id": 1,
            "results": [{"data_rows": [{"saldo": "9999999"}], "summary_text": "secreto"}],
        }
        payload.update(extra)
        return self.client.post(
            "/api/v1/chat/threads", json=payload, headers={"Authorization": f"Bearer {token}"}
        )

    def test_private_thread_is_not_readable_by_another_user(self):
        owner = self._token("economista", "economista123")
        other = self._token("ti", "ti123")

        created = self._save(owner, "test-idor-privado")
        self.assertEqual(created.status_code, 200, created.text[:200])

        # El propietario sí lo ve por su endpoint normal.
        mine = self.client.get(
            "/api/v1/chat/threads/test-idor-privado", headers={"Authorization": f"Bearer {owner}"}
        )
        self.assertEqual(mine.status_code, 200)

        # Un tercero no, ni por /threads ni por /threads/shared.
        for path in ("/api/v1/chat/threads/test-idor-privado",
                     "/api/v1/chat/threads/shared/test-idor-privado"):
            with self.subTest(path=path):
                r = self.client.get(path, headers={"Authorization": f"Bearer {other}"})
                self.assertEqual(r.status_code, 404, f"{path} devolvio {r.status_code}")
                self.assertNotIn("9999999", r.text, "se filtered el contenido de otro usuario")

    def test_shared_thread_is_readable_once_flagged(self):
        owner = self._token("economista", "economista123")
        other = self._token("ti", "ti123")

        self.assertEqual(self._save(owner, "test-idor-compartido", is_shared=True).status_code, 200)

        r = self.client.get(
            "/api/v1/chat/threads/shared/test-idor-compartido",
            headers={"Authorization": f"Bearer {other}"},
        )
        self.assertEqual(r.status_code, 200, r.text[:200])
        self.assertEqual(r.json()["id"], "test-idor-compartido")

    def test_cannot_hijack_another_users_thread(self):
        owner = self._token("economista", "economista123")
        attacker = self._token("ti", "ti123")

        self.assertEqual(self._save(owner, "test-idor-sequestro").status_code, 200)

        # El atacante envia el id ajeno: no debe poder sobreescribirlo ni quedárselo.
        hijack = self._save(attacker, "test-idor-sequestro", title="PWN")
        self.assertIn(
            hijack.status_code, (200, 404, 409),
            f"la API respondio {hijack.status_code}: {hijack.text[:200]}",
        )

        owner_view = self.client.get(
            "/api/v1/chat/threads/test-idor-sequestro", headers={"Authorization": f"Bearer {owner}"}
        )
        self.assertEqual(owner_view.status_code, 200)
        self.assertEqual(
            owner_view.json()["title"], "Consulta de ingresos",
            "un usuario sobreescribio el hilo de otro",
        )

        # Y el hilo sigue siendo del dueño original.
        rows = self.db.execute(text(
            "SELECT user_id FROM chat_conversations WHERE id = 'test-idor-sequestro'"
        )).first()
        owner_id = self.db.execute(text(
            "SELECT id FROM users WHERE username = 'economista'"
        )).first().id
        self.assertEqual(rows.user_id, owner_id, "el atacante se apropio del hilo")


if __name__ == "__main__":
    unittest.main()
