"""
Segunda entrada del SSRF: GET /system/health acepta `base_url` como QUERY PARAM
y lo pasaba crudo a HealthService.check_llm_connectivity, que emite httpx GET a
donde se le digera. Con ?base_url=http://169.254.169.254 cualquier usuario
autenticado hacia GET a la red interna.

La proteccion NO se reimplementa: system/router.py importa la MISMA funcion
(`_resolve_llm_base_url`) que usan /llm/test-connection y /llm/test-completion,
asi que las tres entradas comparten una sola implementacion del allowlist.
"""
import unittest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.system import router as system_router
from app.core.security import create_access_token


def _no_httpx(*args, **kwargs):
    """Falla si se emite alguna request HTTP durante el test."""
    raise AssertionError("Se emitio una request HTTP a un host no permitido")


class TestSystemHealthSSRF(unittest.TestCase):

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

    def tearDown(self):
        self.db.close()

    # ------------------------------------------------------------------ BUG
    def test_cloud_metadata_url_is_rejected_with_400_and_no_request(self):
        """169.254.169.254 -> 400 y ni una sola request sale hacia esa IP."""
        with patch("httpx.AsyncClient.get", side_effect=_no_httpx), \
             patch("httpx.AsyncClient.post", side_effect=_no_httpx):
            res = self.client.get(
                "/api/v1/system/health",
                params={"base_url": "http://169.254.169.254"},
                headers=self.headers,
            )
        self.assertEqual(res.status_code, 400, res.text[:300])
        self.assertIn("no permitido", res.json()["detail"].lower())

    def test_internal_service_host_is_rejected_with_400_and_no_request(self):
        """Nombre interno en vez de IP: mismo ataque, misma puerta."""
        with patch("httpx.AsyncClient.get", side_effect=_no_httpx), \
             patch("httpx.AsyncClient.post", side_effect=_no_httpx):
            res = self.client.get(
                "/api/v1/system/health",
                params={"base_url": "http://redis-interno:6379"},
                headers=self.headers,
            )
        self.assertEqual(res.status_code, 400, res.text[:300])
        self.assertIn("no permitido", res.json()["detail"].lower())

    def test_userinfo_trick_does_not_bypass_the_allowlist(self):
        """`http://localhost@169.254.169.254` tiene hostname interno, no localhost."""
        with patch("httpx.AsyncClient.get", side_effect=_no_httpx), \
             patch("httpx.AsyncClient.post", side_effect=_no_httpx):
            res = self.client.get(
                "/api/v1/system/health",
                params={"base_url": "http://localhost@169.254.169.254"},
                headers=self.headers,
            )
        self.assertEqual(res.status_code, 400, res.text[:300])

    def test_loopback_base_url_is_still_accepted(self):
        """El camino legitimo no se rompio: un loopback valido se usa de verdad."""
        captured = {}

        async def fake_check(provider=None, base_url=None, model_name=None, timeout=2.0):
            captured["base_url"] = base_url
            return {
                "success": True, "latency_ms": 3,
                "message": "ok", "available_models": ["llama3.2:3b"],
                "active_url": base_url, "provider": provider or "ollama",
            }

        with patch.object(system_router.HealthService, "check_llm_connectivity", new=fake_check), \
             patch.object(system_router.HealthService, "check_db_connectivity", return_value={
                 "success": True, "latency_ms": 1, "message": "ok"}):
            res = self.client.get(
                "/api/v1/system/health",
                params={"base_url": "http://127.0.0.1:8080"},
                headers=self.headers,
            )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(captured.get("base_url"), "http://127.0.0.1:8080")

    def test_health_without_base_url_still_works(self):
        """Sin base_url se usa la config del servidor: no se rompe el panel."""
        with patch.object(system_router.HealthService, "check_llm_connectivity",
                          new=_async_ok()) as mock, \
             patch.object(system_router.HealthService, "check_db_connectivity", return_value={
                 "success": True, "latency_ms": 1, "message": "ok"}):
            res = self.client.get("/api/v1/system/health", headers=self.headers)
        self.assertEqual(res.status_code, 200, res.text[:300])
        from app.core.config import settings
        self.assertEqual(mock.await_args.kwargs["base_url"], settings.OLLAMA_BASE_URL)

    def test_ssrf_still_requires_authentication(self):
        """La validacion no reemplaza la authz: anonimo sigue siendo 401."""
        with patch("httpx.AsyncClient.get", side_effect=_no_httpx), \
             patch("httpx.AsyncClient.post", side_effect=_no_httpx):
            res = self.client.get("/api/v1/system/health", params={"base_url": "http://169.254.169.254"})
        self.assertEqual(res.status_code, 401)

    # ------------------------------------------------------- causa raiz
    def test_router_reuses_the_shared_validator_instead_of_a_second_copy(self):
        """Si alguien reintroduce un allowlist propio en system/router, esto falla.
        Las tres entradas (health, test-connection, test-completion) deben pasar por
        la MISMA funcion, o la siguiente puerta que se abra repite el error."""
        from app.modules.chat_engine.llm_diagnostic_router import _resolve_llm_base_url as shared
        self.assertIs(system_router._resolve_llm_base_url, shared)

    def test_health_service_never_reports_success_without_verifying(self):
        """health_service fue arreglado antes (success:True sin verificar en la rama
        sqlite). Si el LLM no responde NINGUN endpoint debe devolver success:False
        con el motivo, nunca True."""
        import asyncio
        from app.modules.system.health_service import HealthService

        async def boom(*a, **k):
            raise RuntimeError("connection refused")

        with patch("httpx.AsyncClient.get", new=boom), \
             patch("httpx.AsyncClient.post", new=boom):
            res = asyncio.run(HealthService.check_llm_connectivity(
                provider="ollama", base_url="http://127.0.0.1:59999", model_name="m"))

        self.assertFalse(res["success"], "reporto LLM conectado sin haberlo verificado")
        self.assertTrue(res["message"])


def _async_ok():
    from unittest.mock import AsyncMock
    from app.core.config import settings
    m = AsyncMock(return_value={
        "success": True, "latency_ms": 3, "message": "ok",
        "available_models": [settings.OLLAMA_MODEL],
        "active_url": settings.OLLAMA_BASE_URL, "provider": "ollama",
    })
    return m


if __name__ == "__main__":
    unittest.main()