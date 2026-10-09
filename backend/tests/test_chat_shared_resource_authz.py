"""
`QueryLearningMemory` es un recurso COMPARTIDO: `sql_executor` lo inyecta en el
prompt de todos los usuarios de la conexion con el tag "[Consulta Maestra
Verificada]" y la tabla no tiene `user_id`, asi que no se puede distinguir "mi
feedback" de "la memoria curada de la plataforma".

Consecuencia antes del fix: un "Usuario Consultor" podia POSTear `/chat/golden-query`
con un SQL arbitrario e `is_golden: true` y contaminar el prompt de todos, y de yapa
pisar la golden query real del admin (el endpoint hace upsert por
`(connection_id, question_pattern)`).

Criterio aplicado: el corte por rol, no una columna `user_id`. La memoria es de la
plataforma, no del usuario, asi que "separar el feedback propio" seria un modelo de
datos distinto con el que no se quiere por el bien minimo.
"""
import json
import unittest
import uuid

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.core.constants import ROLE_ADMINISTRADOR, ROLE_ANALISTA_FINANCIERO, ROLE_DIRECTOR_EJECUTIVO
from app.modules.auth.models import User, UserSession
from app.modules.chat_engine.models import QueryLearningMemory
from app.core.security import create_access_token

CONNECTION_ID = 987654


def _headers_for(db, username: str):
    user = db.query(User).filter(User.username == username).first()
    jti = str(uuid.uuid4())
    db.add(UserSession(user_id=user.id, jti=jti, is_revoked=False))
    db.commit()
    return jti, {"Authorization": f"Bearer {create_access_token(subject=user.id, jti=jti)}"}


class TestSharedLearningMemoryAuthorization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.admin_jti, self.admin_headers = _headers_for(self.db, "admin")
        self.user_jti, self.user_headers = _headers_for(self.db, "juan_ti")

    def tearDown(self):
        self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.connection_id == CONNECTION_ID
        ).delete()
        self.db.query(UserSession).filter(
            UserSession.jti.in_([self.admin_jti, self.user_jti])
        ).delete()
        self.db.commit()
        self.db.close()

    def _memories(self):
        self.db.expire_all()
        return self.db.query(QueryLearningMemory).filter(
            QueryLearningMemory.connection_id == CONNECTION_ID
        ).all()

    def _golden_payload(self, is_golden=True):
        return {
            "question": "  Ventas Totales  ",
            "sql": "SELECT * FROM tabla_bloqueada",
            "connection_id": CONNECTION_ID,
            "is_golden": is_golden,
        }

    # --- golden-query: solo admin ---------------------------------------

    def test_non_admin_cannot_create_golden_query(self):
        res = self.client.post(
            "/api/v1/chat/golden-query", json=self._golden_payload(), headers=self.user_headers
        )
        self.assertEqual(res.status_code, 403, res.text[:300])
        self.assertEqual(self._memories(), [], "un no-admin escribio en la memoria compartida")

    def test_non_admin_cannot_mark_an_existing_memory_as_golden(self):
        """El caso importante: pisar la golden query YA curada por el admin."""
        admin_res = self.client.post(
            "/api/v1/chat/golden-query", json=self._golden_payload(), headers=self.admin_headers
        )
        self.assertEqual(admin_res.status_code, 200, admin_res.text[:300])

        attack = self.client.post(
            "/api/v1/chat/golden-query",
            json={**self._golden_payload(), "sql": "SELECT * FROM tabla_bloqueada"},
            headers=self.user_headers,
        )
        self.assertEqual(attack.status_code, 403, attack.text[:300])

        mem = self._memories()[0]
        self.assertEqual(mem.successful_sql, "SELECT * FROM tabla_bloqueada")  # el del admin
        self.assertTrue(mem.is_golden)

    def test_non_admin_cannot_unmark_a_golden_query(self):
        """Desmarcar tambien es tocar la memoria compartida."""
        self.client.post(
            "/api/v1/chat/golden-query", json=self._golden_payload(), headers=self.admin_headers
        )
        res = self.client.post(
            "/api/v1/chat/golden-query",
            json=self._golden_payload(is_golden=False),
            headers=self.user_headers,
        )
        self.assertEqual(res.status_code, 403, res.text[:300])
        self.assertTrue(self._memories()[0].is_golden)

    def test_admin_can_create_and_toggle_golden_query(self):
        res = self.client.post(
            "/api/v1/chat/golden-query", json=self._golden_payload(), headers=self.admin_headers
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertTrue(res.json()["is_golden"])
        mem = self._memories()[0]
        self.assertTrue(mem.is_golden)
        # question_pattern se normaliza, para que el upsert no duplique por mayusculas.
        self.assertEqual(mem.question_pattern, "ventas totales")

        off = self.client.post(
            "/api/v1/chat/golden-query",
            json=self._golden_payload(is_golden=False),
            headers=self.admin_headers,
        )
        self.assertEqual(off.status_code, 200, off.text[:300])
        self.assertFalse(self._memories()[0].is_golden)
        self.assertEqual(len(self._memories()), 1)

    # --- feedback: el no-admin califica, pero no escribe la memoria ------

    def test_non_admin_cannot_request_golden_via_feedback(self):
        res = self.client.post(
            "/api/v1/chat/feedback",
            json={
                "question": "Ventas Totales",
                "sql": "SELECT * FROM tabla_bloqueada",
                "connection_id": CONNECTION_ID,
                "rating": "positive",
                "is_golden": True,
            },
            headers=self.user_headers,
        )
        self.assertEqual(res.status_code, 403, res.text[:300])
        self.assertEqual(self._memories(), [])

    def test_non_admin_positive_feedback_does_not_write_shared_memory(self):
        res = self.client.post(
            "/api/v1/chat/feedback",
            json={
                "question": "Ventas Totales",
                "sql": "SELECT * FROM tabla_bloqueada",
                "connection_id": CONNECTION_ID,
                "rating": "positive",
            },
            headers=self.user_headers,
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        body = res.json()
        self.assertFalse(body["learning_saved"], "dijo que no guardo pero la memoria escribio")
        self.assertNotIn("se reforzó", body["message"])
        self.assertEqual(self._memories(), [])

    def test_non_admin_negative_feedback_still_works(self):
        """El feedback negativo nunca escribia memoria: no se le rompe nada."""
        res = self.client.post(
            "/api/v1/chat/feedback",
            json={
                "question": "Ventas Totales",
                "sql": "SELECT * FROM tabla_bloqueada",
                "connection_id": CONNECTION_ID,
                "rating": "negative",
            },
            headers=self.user_headers,
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertFalse(res.json()["learning_saved"])
        self.assertEqual(self._memories(), [])

    def test_admin_positive_feedback_still_reinforces_memory(self):
        res = self.client.post(
            "/api/v1/chat/feedback",
            json={
                "question": "Ventas Totales",
                "sql": "SELECT 1",
                "connection_id": CONNECTION_ID,
                "rating": "positive",
            },
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertTrue(res.json()["learning_saved"])
        self.assertEqual(len(self._memories()), 1)
        self.assertEqual(self._memories()[0].successful_sql, "SELECT 1")

    def test_injected_sql_does_not_reach_the_shared_prompt(self):
        """El escenario completo: el SQL de un no-admin no aparece en el prompt."""
        self.client.post(
            "/api/v1/chat/feedback",
            json={
                "question": "Ventas Totales",
                "sql": "SELECT * FROM tabla_bloqueada",
                "connection_id": CONNECTION_ID,
                "rating": "positive",
            },
            headers=self.user_headers,
        )
        from app.modules.chat_engine.sql_executor import SQLExecutor
        prompt = SQLExecutor.retrieve_few_shot_memories(
            self.db, "Ventas Totales", CONNECTION_ID, "Usuario Consultor"
        )
        self.assertNotIn("tabla_bloqueada", prompt)
        self.assertNotIn("[Consulta Maestra Verificada]", prompt)

    # --- el corte por rol de la memoria ---------------------------------
    #
    # `ADMIN_ROLES` tiene UN solo elemento con mayusculas ("Administrador de
    # Plataforma"), asi que la comparacion tiene que ser exacta. Con un
    # `str(user_role).lower()` el admin caia en la rama de no-admin y perdia la
    # memoria de los demas roles: nunca entra, comparacion contra un set con
    # mayusculas.

    def _seed_memories_for_roles(self):
        self.db.add(QueryLearningMemory(
            question_pattern="patron_del_analista",
            connection_id=CONNECTION_ID,
            user_role=ROLE_ANALISTA_FINANCIERO,
            successful_sql="SELECT * FROM tabla_del_analista",
        ))
        self.db.add(QueryLearningMemory(
            question_pattern="patron_sin_rol",
            connection_id=CONNECTION_ID,
            user_role=None,
            successful_sql="SELECT * FROM tabla_sin_rol",
        ))
        self.db.commit()

    def test_admin_role_sees_memories_of_other_roles(self):
        from app.modules.chat_engine.sql_executor import SQLExecutor
        self._seed_memories_for_roles()
        prompt = SQLExecutor.retrieve_few_shot_memories(
            self.db, "Ventas Totales", CONNECTION_ID, ROLE_ADMINISTRADOR
        )
        self.assertIn("tabla_del_analista", prompt)
        self.assertIn("tabla_sin_rol", prompt)

    def test_non_admin_role_does_not_see_other_roles_memories(self):
        """El filtro sigue cerrandose: el fix no abre la memoria a cualquiera."""
        from app.modules.chat_engine.sql_executor import SQLExecutor
        self._seed_memories_for_roles()
        prompt = SQLExecutor.retrieve_few_shot_memories(
            self.db, "Ventas Totales", CONNECTION_ID, ROLE_DIRECTOR_EJECUTIVO
        )
        self.assertNotIn("tabla_del_analista", prompt)
        self.assertIn("tabla_sin_rol", prompt)


if __name__ == "__main__":
    unittest.main()
