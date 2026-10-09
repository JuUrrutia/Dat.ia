"""Gobernanza de la memoria de aprendizaje (`query_learning_memories`).

La tabla NO tiene `user_id`: `sql_executor` la inyecta como few-shot en el prompt
de TODOS los usuarios de la conexion, y `toggle_golden_query` hace upsert por
`(connection_id, question_pattern)`. O sea que un admin puede enseñar a toda la
empresa un SQL equivocado, y antes de este modulo no habia forma de ver que hay
ni de deshacerlo.

Estos tests fijan los tres bordes: quien puede mirar/borrar, el aislamiento por
conexion, y que el listado refleje el uso REAL (`execution_count`).
"""
import uuid
import unittest

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.chat_engine.models import QueryLearningMemory
from app.core.security import create_access_token


# Prefijo de las filas que crea el test. El aislamiento por `connection_id` es lo
# que se prueba, asi que las filas se crean por la API (`POST /chat/golden-query`)
# y no por INSERT: asi tambien se cubre que la escritura respeta la conexion.
TAG = "gob-lm"


class TestLearningMemoryGovernance(unittest.TestCase):

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
            self.users[username] = {"Authorization": f"Bearer {create_access_token(subject=u.id, jti=jti)}"}
        self.admin_headers = self.users["admin"]
        self.user_headers = self.users["juan_ti"]
        # Dos conexiones distintas para probar el aislamiento por `connection_id`.
        self.conn_a = 91001
        self.conn_b = 91002

    def tearDown(self):
        self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.question_pattern.like(f"%{TAG}%")
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _teach(self, question: str, connection_id: int, is_golden: bool = True) -> dict:
        """Enseña una memoria por el endpoint real (no por INSERT)."""
        res = self.client.post(
            "/api/v1/chat/golden-query",
            json={
                "question": question,
                "sql": f"SELECT COUNT(*) FROM fact_table WHERE tag = '{TAG}'",
                "connection_id": connection_id,
                "is_golden": is_golden,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        return res.json()

    def _list(self, connection_id: int, headers=None):
        return self.client.get(
            "/api/v1/chat/golden-queries",
            params={"connection_id": connection_id},
            headers=headers or self.admin_headers,
        )

    # 1. Control de acceso
    def test_get_requires_admin(self):
        self._teach(f"{TAG} acceso", self.conn_a)

        anon = self.client.get(
            "/api/v1/chat/golden-queries", params={"connection_id": self.conn_a})
        self.assertEqual(anon.status_code, 401, anon.text[:300])

        as_user = self._list(self.conn_a, headers=self.user_headers)
        self.assertEqual(as_user.status_code, 403, as_user.text[:300])

    def test_delete_requires_admin(self):
        """Borrar la memoria compartida tambien es admin-only: el efecto es global."""
        self._teach(f"{TAG} delete-acceso", self.conn_a)
        mem = self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.question_pattern == f"{TAG} delete-acceso",
            QueryLearningMemory.connection_id == self.conn_a,
        ).first()

        anon = self.client.delete(f"/api/v1/chat/golden-queries/{mem.id}")
        self.assertEqual(anon.status_code, 401, anon.text[:300])

        as_user = self.client.delete(
            f"/api/v1/chat/golden-queries/{mem.id}", headers=self.user_headers)
        self.assertEqual(as_user.status_code, 403, as_user.text[:300])

        # Y la fila sigue ahí: el 403 no borró nada.
        still = self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.id == mem.id).first()
        self.assertIsNotNone(still)

    # 2. Aislamiento por conexion, verificado por los dos lados
    def test_list_is_isolated_by_connection(self):
        qa = f"{TAG} venta anual"
        qb = f"{TAG} margen bruto"
        self._teach(qa, self.conn_a)
        self._teach(qb, self.conn_b)

        a = self._list(self.conn_a).json()
        b = self._list(self.conn_b).json()
        patterns_a = [i["question_pattern"] for i in a["items"]]
        patterns_b = [i["question_pattern"] for i in b["items"]]

        self.assertIn(qa, patterns_a)
        self.assertNotIn(qb, patterns_a, "La memoria de la conexion B se coló en el listado de la A.")
        self.assertIn(qb, patterns_b)
        self.assertNotIn(qa, patterns_b, "La memoria de la conexion A se coló en el listado de la B.")

    # 3. 404, no borrado silencioso
    def test_delete_nonexistent_returns_404(self):
        """Id inexistente = 404. Un success:True seria un 'lo revirti' mentiroso."""
        res = self.client.delete(
            "/api/v1/chat/golden-queries/99999999", headers=self.admin_headers)
        self.assertEqual(res.status_code, 404, res.text[:300])
        self.assertNotIn("success", res.json())

    # 4. El DELETE borra de verdad
    def test_delete_removes_from_listing(self):
        q = f"{TAG} borrable"
        self._teach(q, self.conn_a)
        mem = self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.question_pattern == q,
            QueryLearningMemory.connection_id == self.conn_a,
        ).first()
        self.assertIsNotNone(mem)

        res = self.client.delete(
            f"/api/v1/chat/golden-queries/{mem.id}", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertTrue(res.json()["success"])

        after = self._list(self.conn_a).json()
        self.assertNotIn(
            q, [i["question_pattern"] for i in after["items"]],
            "La memoria sigue en el listado tras un DELETE que devolvio 200.")

    # 5. El mas importante: el listado refleja el uso real
    def test_listing_reports_measured_usage(self):
        """Una golden con `execution_count=10` tiene que listarse con ese 10.

        `execution_count` es veces que `sql_executor` la inyecto en el prompt de
        los usuarios. Si el listado no lo muestra, la pantalla no dice que
        knowledge esta en uso y no cumple para que existe.
        """
        q = f"{TAG} muy usada"
        self._teach(q, self.conn_a, is_golden=True)
        mem = self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.question_pattern == q,
            QueryLearningMemory.connection_id == self.conn_a,
        ).first()
        self.assertIsNotNone(mem)
        # Uso real medido, escrito a mano como lo haria `sql_executor`.
        mem.execution_count = 10
        self.db.commit()

        items = self._list(self.conn_a).json()["items"]
        row = next(i for i in items if i["question_pattern"] == q)
        self.assertEqual(row["execution_count"], 10)
        self.assertTrue(row["is_golden"])

        # Y el orden pone las doradas primero, luego por uso descendente.
        goldens = [i for i in items if i["is_golden"]]
        counts = [i["execution_count"] for i in goldens]
        self.assertEqual(counts, sorted(counts, reverse=True),
                         "Las goldens no vienen ordenadas por uso descendente.")


if __name__ == "__main__":
    unittest.main()