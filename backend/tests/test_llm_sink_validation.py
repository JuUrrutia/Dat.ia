"""
La allowlist del SSRF estaba en los ROUTERS, no en los SINKs. Los routers ya
validan (importan `_resolve_llm_base_url`), asi que hoy no es explotable: los 7
call sites de `LLMService.generate_completion` pasan `settings`, nadie pasa
`base_url`. El agujero es pre-armado — el proximo endpoint que lo pase emite POST
a donde le digan.

Estos tests fijan la regla en el sink:
  - una URL fuera de la politica se RECHAZA y no se emite ninguna request
  - el camino legitimo no se rompio, y sobre todo: lo que usa el despliegue REAL
    (docker-compose pone OLLAMA_BASE_URL=http://host.docker.internal:11434, que
    NO es loopback) sigue pasando.

Detalle de diseño documentado: el sink acepta mas que loopback a proposito. Una
allowlist de solo loopback en el sink romperia Docker y las IPs de la LAN. Lo que
no acepta es cualquier otro hostname (redis-interno, metadata.google.internal,
nombres de servicio del compose) ni IPs publicas.
"""
import asyncio
import inspect
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.modules.chat_engine.llm_service import (
    LLMService,
    validate_llm_base_url,
)
from app.modules.system.health_service import HealthService


def _auth_client():
    """Cliente autenticado como admin, para probar las puertas HTTP de verdad."""
    import uuid
    from main import app
    from app.core.database import SessionLocal
    from app.db.init_db import init_db
    from app.modules.auth.models import User, UserSession
    from app.core.security import create_access_token

    db = SessionLocal()
    init_db(db)
    user = db.query(User).filter(User.username == "admin").first()
    jti = str(uuid.uuid4())
    token = create_access_token(subject=user.id, jti=jti)
    db.add(UserSession(user_id=user.id, jti=jti, is_revoked=False))
    db.commit()
    db.close()
    return TestClient(app), {"Authorization": f"Bearer {token}"}


def _no_request(*args, **kwargs):
    """Falla si el sink emite alguna request."""
    raise AssertionError("Se emitio una request HTTP a un host no permitido")


class TestSinkRejectsHostileUrls(unittest.TestCase):
    """El sink es la ultima puerta: rechaza lo que el router deberia haber rechazado."""

    def test_generate_completion_rejects_cloud_metadata_ip(self):
        """169.254.169.254 -> ni una request sale, ni al host ni a ningun fallback."""
        with patch("httpx.AsyncClient.post", side_effect=_no_request), \
             patch("httpx.AsyncClient.get", side_effect=_no_request):
            with self.assertRaises(ValueError) as ctx:
                asyncio.run(LLMService.generate_completion(
                    prompt="hola", base_url="http://169.254.169.254"))
        self.assertIn("no permitido", str(ctx.exception).lower())

    def test_generate_completion_rejects_internal_hostname(self):
        """Mismo ataque con nombre en vez de IP: mismo rechazo."""
        with patch("httpx.AsyncClient.post", side_effect=_no_request), \
             patch("httpx.AsyncClient.get", side_effect=_no_request):
            with self.assertRaises(ValueError):
                asyncio.run(LLMService.generate_completion(
                    prompt="hola", base_url="http://redis-interno:6379"))

    def test_generate_completion_rejects_userinfo_trick(self):
        """`http://localhost@169.254.169.254` tiene hostname interno, no localhost."""
        with patch("httpx.AsyncClient.post", side_effect=_no_request), \
             patch("httpx.AsyncClient.get", side_effect=_no_request):
            with self.assertRaises(ValueError):
                asyncio.run(LLMService.generate_completion(
                    prompt="hola", base_url="http://localhost@169.254.169.254"))

    def test_generate_completion_rejects_non_http_scheme(self):
        with patch("httpx.AsyncClient.post", side_effect=_no_request), \
             patch("httpx.AsyncClient.get", side_effect=_no_request):
            with self.assertRaises(ValueError):
                asyncio.run(LLMService.generate_completion(
                    prompt="hola", base_url="file:///etc/passwd"))

    def test_check_llm_connectivity_rejects_internal_hostname(self):
        """El sink de health tampoco emite GET a un host fuera de la politica, y
        NO cae a los fallbacks de loopback: reportar success:False con el motivo
        es honesto; seguir sondeando y devolver un resultado seria tapar el
        rechazo."""
        with patch("httpx.AsyncClient.get", side_effect=_no_request), \
             patch("httpx.AsyncClient.post", side_effect=_no_request):
            res = asyncio.run(HealthService.check_llm_connectivity(
                provider="ollama", base_url="http://redis-interno:6379",
                model_name="m"))
        self.assertFalse(res["success"])
        self.assertIn("no permitido", res["message"].lower())
        # Ningun default afirma un resultado: sin URL activa y sin modelos.
        self.assertEqual(res["active_url"], "")
        self.assertEqual(res["available_models"], [])


class TestSinkAcceptsLegitimateUrls(unittest.TestCase):
    """El fix de SSRF no puede romper la instalacion real."""

    def test_loopback_urls_pass(self):
        for url in ("http://127.0.0.1:11434", "http://localhost:11434",
                    "http://127.0.0.1:8080", "http://localhost:1234"):
            with self.subTest(url=url):
                self.assertTrue(validate_llm_base_url(url))

    def test_loopback_url_is_actually_used_by_generate_completion(self):
        """Un loopback valido se emite de verdad (no solo se valida sin quejarse)."""
        captured = {}

        class _Res:
            status_code = 200

            @staticmethod
            def json():
                return {"choices": [{"message": {"content": "hola"}}]}

        async def fake_post(self, url, **kwargs):
            captured["url"] = url
            return _Res()

        with patch("httpx.AsyncClient.post", new=fake_post):
            out = asyncio.run(LLMService.generate_completion(
                prompt="p", base_url="http://127.0.0.1:8080"))
        self.assertEqual(out, "hola")
        self.assertEqual(captured["url"], "http://127.0.0.1:8080/v1/chat/completions")

    def test_docker_host_url_passes(self):
        """CRITICO: docker-compose.yml:55 define por defecto
        OLLAMA_BASE_URL=http://host.docker.internal:11434 con
        extra_hosts host.docker.internal:host-gateway (docker-compose.yml:63).
        Un backend en contenedor NO alcanza al LLM del host por loopback. Si este
        valor no pasa, el fix rompe la instalacion de Docker."""
        self.assertTrue(validate_llm_base_url("http://host.docker.internal:11434"))
        self.assertTrue(validate_llm_base_url("http://host.docker.internal:11434/v1"))

    def test_lan_private_ip_passes(self):
        """Servidor LLM en otra maquina de la red local: montaje valido local-first."""
        for url in ("http://192.168.1.50:11434", "http://10.0.0.8:8080",
                    "http://172.16.4.2:1234"):
            with self.subTest(url=url):
                self.assertTrue(validate_llm_base_url(url))

    def test_project_default_settings_urls_pass(self):
        """CRITICO: los valores por defecto reales del proyecto tienen que pasar,
        o el panel de salud y las inferencias se rompen en una instalacion limpia."""
        self.assertTrue(validate_llm_base_url(settings.OLLAMA_BASE_URL),
                        f"OLLAMA_BASE_URL por defecto rechazado: {settings.OLLAMA_BASE_URL}")
        # OPENAI_COMPATIBLE_URL se pasa por _as_base_url, que quita /v1.
        from app.modules.chat_engine.llm_service import LLMService as _L
        self.assertTrue(validate_llm_base_url(_L._as_base_url(settings.OPENAI_COMPATIBLE_URL)))

    def test_docker_compose_default_ollama_url_passes(self):
        """El valor por defecto del compose, leido del archivo, no del .env local."""
        import os
        import re
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        compose = os.path.join(root, "docker-compose.yml")
        with open(compose, encoding="utf-8") as fh:
            m = re.search(r"OLLAMA_BASE_URL:-\s*(\S+)\}", fh.read())
        self.assertIsNotNone(m, "no se encontro el default de OLLAMA_BASE_URL en el compose")
        self.assertTrue(validate_llm_base_url(m.group(1)), m.group(1))


class TestDoubleValidationIsIdempotent(unittest.TestCase):
    """Router + sink: la segunda validacion no puede romper el camino bueno."""

    def test_url_that_passed_the_router_still_passes_the_sink(self):
        from app.modules.chat_engine.llm_diagnostic_router import _resolve_llm_base_url
        for url in ("http://127.0.0.1:8080", "http://localhost:11434", "http://localhost:1234"):
            with self.subTest(url=url):
                self.assertEqual(validate_llm_base_url(_resolve_llm_base_url(url)), url)

    def test_router_then_sink_over_http(self):
        """Flujo real: POST /llm/test-connection -> router valida -> sink valida."""
        client, headers = _auth_client()

        async def boom(*a, **k):
            raise RuntimeError("connection refused")

        # El router acepta el loopback; el sink lo vuelve a validar y lo usa.
        with patch("httpx.AsyncClient.get", new=boom), \
             patch("httpx.AsyncClient.post", new=boom):
            res = client.post(
                "/api/v1/llm/test-connection",
                json={"provider": "ollama", "base_url": "http://127.0.0.1:11434",
                      "model_name": settings.OLLAMA_MODEL},
                headers=headers,
            )
        self.assertEqual(res.status_code, 200, res.text[:300])
        # success:False es lo correcto: nadie respondio. Lo que se verifica aqui
        # es que la doble validacion no devolvio 400 y no afirmo conexion.
        self.assertFalse(res.json()["success"])

        # Y por la segunda puerta (system/health), que pasa la config del
        # servidor (en Docker: host.docker.internal): tambien se valida en el
        # sink y no se rompe.
        with patch("httpx.AsyncClient.get", new=boom), \
             patch("httpx.AsyncClient.post", new=boom), \
             patch.object(HealthService, "check_db_connectivity", return_value={
                 "success": True, "latency_ms": 1, "message": "ok"}):
            res2 = client.get("/api/v1/system/health", headers=headers)
        self.assertEqual(res2.status_code, 200, res2.text[:300])

    def test_hostile_url_through_http_still_never_reaches_the_network(self):
        """La doble validacion no debe dejar pasar lo que el router ya rechaza."""
        client, headers = _auth_client()
        with patch("httpx.AsyncClient.get", side_effect=_no_request), \
             patch("httpx.AsyncClient.post", side_effect=_no_request):
            res = client.get("/api/v1/system/health",
                             params={"base_url": "http://169.254.169.254"},
                             headers=headers)
        self.assertEqual(res.status_code, 400, res.text[:300])


class TestValidationLivesInTheSinkNotOnlyTheRouter(unittest.TestCase):
    """Causa raiz: si alguien reintroduce la validacion solo en los routers,
    estos tests siguen verdes mientras el sink vuelve a ser una puerta abierta."""

    def test_sinks_call_the_validator(self):
        from app.modules.chat_engine import llm_service
        self.assertIn("validate_llm_base_url(base_url)",
                      inspect.getsource(LLMService.generate_completion))
        from app.modules.system import health_service
        self.assertIn("validate_llm_base_url",
                      inspect.getsource(HealthService.check_llm_connectivity))

    def test_sink_delegates_the_loopback_allowlist_to_the_router(self):
        """El sink tiene su propia politica (host.docker.internal / LAN) pero
        DELEGA el loopback en la del router, no lo copia. Si alguien agrega un
        host al allowlist del router, el sink lo acepta sin tocarlo."""
        from app.modules.chat_engine import llm_diagnostic_router
        with patch.object(llm_diagnostic_router, "LLM_ALLOWED_HOSTS", {"localhost"}):
            # 'localhost' sigue en el allowlist del router -> el sink lo acepta.
            self.assertTrue(validate_llm_base_url("http://localhost:11434"))
            # '127.0.0.1' ya no esta -> el sink lo rechaza tambien (misma fuente).
            with self.assertRaises(ValueError):
                validate_llm_base_url("http://127.0.0.1:11434")


if __name__ == "__main__":
    unittest.main()
