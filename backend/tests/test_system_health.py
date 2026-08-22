import unittest
import uuid
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.models.session import UserSession
from app.core.security import create_access_token
from app.core.constants import (
    SYSTEM_STATUS_OPERATIONAL,
    SYSTEM_STATUS_CRITICAL,
    SYSTEM_STATUS_DEGRADED
)

class TestSystemHealth(unittest.TestCase):
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

        session = UserSession(
            user_id=self.user.id,
            jti=self.jti,
            is_revoked=False
        )
        self.db.add(session)
        self.db.commit()

        # Clean up any leftover test connector records with missing files
        from app.models.connection import CorporateConnection
        self.db.query(CorporateConnection).filter(CorporateConnection.name.like("Test Uploaded Database%")).delete()
        self.db.commit()

        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.close()

    @patch("app.services.health_service.HealthService.check_db_connectivity")
    @patch("app.services.health_service.HealthService.check_llm_connectivity", new_callable=AsyncMock)
    def test_system_health_operational(self, mock_check_llm, mock_check_db):
        mock_check_llm.return_value = {
            "success": True,
            "latency_ms": 15,
            "message": "Conectado exitosamente con Ollama.",
            "available_models": ["llama3.2:3b"]
        }
        mock_check_db.return_value = {
            "success": True,
            "latency_ms": 5,
            "message": "Conexión exitosa en modo SOLO LECTURA."
        }

        response = self.client.get("/api/v1/system/health", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], SYSTEM_STATUS_OPERATIONAL, data)
        self.assertEqual(data["llm_engine"]["status"], SYSTEM_STATUS_OPERATIONAL)
        self.assertEqual(data["metadata_db"]["status"], SYSTEM_STATUS_OPERATIONAL)
        self.assertIn("corporate_connectors", data)

    @patch("app.services.health_service.HealthService.check_db_connectivity")
    @patch("app.services.health_service.HealthService.check_llm_connectivity", new_callable=AsyncMock)
    def test_system_health_with_custom_query_params(self, mock_check_llm, mock_check_db):
        mock_check_llm.return_value = {
            "success": True,
            "latency_ms": 12,
            "message": "Conectado exitosamente.",
            "available_models": ["Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M"],
            "provider": "llama_cpp"
        }
        mock_check_db.return_value = {
            "success": True,
            "latency_ms": 3,
            "message": "OK"
        }

        url = "/api/v1/system/health?base_url=http:%2F%2F127.0.0.1:8080&provider=llama_cpp&model_name=Qwen%2FQwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], SYSTEM_STATUS_OPERATIONAL)
        self.assertIn("llama.cpp", data["llm_engine"]["name"])

    @patch("app.services.health_service.HealthService.check_llm_connectivity", new_callable=AsyncMock)
    def test_system_health_critical_when_llm_down(self, mock_check_llm):
        mock_check_llm.return_value = {
            "success": False,
            "latency_ms": 0,
            "message": "No se pudo contactar al servidor LLM.",
            "available_models": []
        }

        response = self.client.get("/api/v1/system/health", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], SYSTEM_STATUS_CRITICAL)
        self.assertEqual(data["llm_engine"]["status"], SYSTEM_STATUS_CRITICAL)

    def test_system_health_requires_auth(self):
        response = self.client.get("/api/v1/system/health")
        self.assertEqual(response.status_code, 401)

    @patch("app.services.health_service.HealthService.check_llm_connectivity", new_callable=AsyncMock)
    def test_llm_test_connection_regression(self, mock_check_llm):
        mock_check_llm.return_value = {
            "success": True,
            "latency_ms": 20,
            "message": "Conectado exitosamente con Ollama en http://127.0.0.1:11434.",
            "available_models": ["llama3.2:3b"]
        }

        req_payload = {
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model_name": "llama3.2:3b"
        }
        response = self.client.post("/api/v1/llm/test-connection", json=req_payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["latency_ms"], 20)
        self.assertIn("llama3.2:3b", data["available_models"])

    @patch("app.services.health_service.HealthService.check_db_connectivity")
    def test_connector_test_regression(self, mock_check_db):
        mock_check_db.return_value = {
            "success": True,
            "latency_ms": 8,
            "message": "Conexión exitosa al puerto 5432 de POSTGRESQL."
        }

        req_payload = {
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database_name": "corp_db",
            "username": "readonly_user",
            "password": "secret_password"
        }
        response = self.client.post("/api/v1/connectors/test", json=req_payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["latency_ms"], 8)
