"""
Bugs 1-4: /llm/test-completion (500 siempre por AttributeError), SSRF autenticado
por `base_url` sin validar, URL compuesta con /v1 duplicado y el mensaje de
error del LLM que no decia por que fallo.
"""
import asyncio
import uuid
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.chat_engine.llm_diagnostic_router import (
    LLM_ALLOWED_HOSTS,
    _resolve_llm_base_url,
)
from app.modules.chat_engine.llm_service import LLMService
from app.core.security import create_access_token
from app.core.prompts import PromptManager


def _no_httpx(*args, **kwargs):
    """Falla si se emite alguna request HTTP durante el test."""
    raise AssertionError("Se emitió una request HTTP a un host no permitido")


class TestLLMDiagnosticRouter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user = self.db.query(User).filter(User.username == "admin").first()
        self.jti = str(uuid.uuid4())
        self.token = create_access_token(subject=self.user.id, jti=self.jti)
        self.db.add(UserSession(user_id=self.user.id, jti=self.jti, is_revoked=False))
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.base_payload = {
            "provider": "llama_cpp",
            "base_url": "http://127.0.0.1:8080",
            "model_name": "test-model",
        }

    def tearDown(self):
        self.db.close()

    # ------------------------------------------------------------------ BUG 1
    def test_test_completion_does_not_return_500(self):
        """BUG 1: `PromptManager.SQL_TEST_SYSTEM_PROMPT` no existe. El AttributeError
        ocurria en la linea 66, antes de los tres try, sin exception_handler en la
        app -> 500 garantizada en cada request. Ahora responde 200."""
        payload = {**self.base_payload, "prompt": "ping"}
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "pong"}}]},
                text='{"choices":[]}',
            )

            res = self.client.post("/api/v1/llm/test-completion", json=payload, headers=self.headers)

        self.assertEqual(res.status_code, 200, res.text[:300])
        body = res.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["completion_text"], "pong")

    def test_test_completion_returns_response_even_when_llm_is_down(self):
        """Sin LLM local responde success=False con 200, no 500."""
        payload = {**self.base_payload, "prompt": "ping"}
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RuntimeError("connection refused")
            res = self.client.post("/api/v1/llm/test-completion", json=payload, headers=self.headers)

        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertFalse(res.json()["success"])

    def test_prompt_manager_has_the_attribute_used_by_the_router(self):
        """Guardarra contra volver a referenciar un prompt inexistente."""
        self.assertTrue(hasattr(PromptManager, "DEFAULT_SYSTEM_PROMPT"))

    # ------------------------------------------------------------------ BUG 2
    def test_ssrf_base_url_is_rejected_with_400_and_no_request(self):
        """BUG 2: `base_url` venía del body sin validar. Con 169.254.169.254 el
        backend hacia POST a la red interna y devolvia la respuesta al atacante.
        Ahora: 400 y ni una sola request sale hacia esa IP."""
        for path in ("/api/v1/llm/test-completion", "/api/v1/llm/test-connection"):
            with patch("httpx.AsyncClient.post", side_effect=_no_httpx), \
                 patch("httpx.AsyncClient.get", side_effect=_no_httpx):
                payload = {**self.base_payload, "base_url": "http://169.254.169.254"}
                if path.endswith("test-completion"):
                    payload["prompt"] = "ping"
                res = self.client.post(path, json=payload, headers=self.headers)
            self.assertEqual(res.status_code, 400, f"{path}: {res.status_code} {res.text[:200]}")
            self.assertIn("no permitido", res.json()["detail"].lower())

    def test_internal_hosts_are_rejected_by_the_validator(self):
        """Otros objetivos internos que tampoco deben pasar."""
        for hostile in (
            "http://169.254.169.254",
            "http://10.0.0.1:8000",
            "http://192.168.1.1",
            "http://metadata.google.internal",
            "http://[::ffff:169.254.169.254]",
            "ftp://127.0.0.1",
            "not-a-url",
        ):
            with self.subTest(url=hostile):
                with self.assertRaises(Exception):
                    _resolve_llm_base_url(hostile)

    def test_localhost_urls_are_accepted(self):
        """El camino legitimo sigue funcionando: loopback con cualquier esquema."""
        for good in (
            "http://127.0.0.1:8080",
            "http://localhost:11434",
            "http://LOCALHOST:1234",
            "https://127.0.0.1",
            "http://[::1]:8080",
        ):
            with self.subTest(url=good):
                self.assertEqual(_resolve_llm_base_url(good), good.rstrip('/'))

    def test_userinfo_trick_does_not_bypass_the_allowlist(self):
        """`http://localhost@169.254.169.254` tiene hostname interno, no localhost."""
        with self.assertRaises(Exception):
            _resolve_llm_base_url("http://localhost@169.254.169.254")

    def test_ssrf_rejection_requires_authentication(self):
        """La validacion no reemplaza la authz: sin token sigue siendo 401."""
        with patch("httpx.AsyncClient.post", side_effect=_no_httpx):
            res = self.client.post("/api/v1/llm/test-completion", json={
                **self.base_payload, "base_url": "http://169.254.169.254", "prompt": "x"
            })
        self.assertEqual(res.status_code, 401)

    # ------------------------------------------------------------------ BUG 3
    def test_composed_url_has_no_duplicated_v1(self):
        """BUG 3: OPENAI_COMPATIBLE_URL ya termina en /v1, y se le concatenaba
        /v1/chat/completions -> /v1/v1/chat/completions, o sea el backend se
        POSTeaba a si mismo y recibia 404."""
        self.assertEqual(
            LLMService._as_base_url("http://localhost:8000/v1"),
            "http://localhost:8000",
        )
        self.assertEqual(
            LLMService._as_base_url("http://localhost:8000/v1/"),
            "http://localhost:8000",
        )
        self.assertEqual(
            LLMService._as_base_url("http://localhost:11434"),
            "http://localhost:11434",
        )
        composed = f"{LLMService._as_base_url('http://localhost:8000/v1')}/v1/chat/completions"
        self.assertNotIn("/v1/v1", composed)
        self.assertEqual(composed, "http://localhost:8000/v1/chat/completions")

    def test_generate_completion_never_hits_a_v1_v1_path(self):
        """Ninguna URL que arme generate_completion puede quedar en /v1/v1."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "ok"}}]},
                text='{"choices":[]}',
            )
            asyncio.run(LLMService.generate_completion("hola"))

        urls = [c.args[0] for c in mock_post.call_args_list]
        self.assertTrue(urls, "no se intentó ningún endpoint")
        for u in urls:
            self.assertNotIn("/v1/v1", u)

    # ------------------------------------------------------------------ BUG 4
    def test_final_error_message_lists_the_real_attempt_reasons(self):
        """BUG 4: los 6 motivos reales se perdian en logger.debug (nivel INFO) y el
        mensaje final solo nombraba :8080 y :11434. Ahora van arriba."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=503, text="server starting up")
            with self.assertRaises(Exception) as ctx:
                asyncio.run(LLMService.generate_completion("hola"))

        msg = str(ctx.exception)
        self.assertIn("Endpoints intentados:", msg)
        self.assertIn("503", msg)
        self.assertIn("server starting up", msg)

    def test_failure_reasons_are_logged_at_error_level(self):
        """Un diagnóstico que solo existe a nivel debug no es un diagnóstico."""
        from app.core.logging import logger as real_logger
        logged = []
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RuntimeError("connection refused")
            with patch.object(real_logger, "error", side_effect=lambda *a, **k: logged.append(a)):
                with self.assertRaises(Exception):
                    asyncio.run(LLMService.generate_completion("hola"))
        self.assertTrue(logged, "no se registró ningún error")
        self.assertTrue(any("connection refused" in " ".join(str(x) for x in args) for args in logged))