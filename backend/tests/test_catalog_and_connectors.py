import os
import io
import uuid
import tempfile
import sqlite3
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.models.role import Role
from app.models.session import UserSession
from app.models.connection import CorporateConnection, DatabaseType
from app.models.catalog import SemanticCatalog
from app.core.security import create_access_token

class TestCatalogAndConnectors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.admin_user = self.db.query(User).filter(User.username == "admin").first()
        self.admin_jti = str(uuid.uuid4())
        self.admin_token = create_access_token(subject=self.admin_user.id, jti=self.admin_jti)

        session = UserSession(
            user_id=self.admin_user.id,
            jti=self.admin_jti,
            is_revoked=False
        )
        self.db.add(session)
        self.db.commit()

        self.headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        self.db.close()

    def test_catalog_crud_lifecycle(self):
        # 1. Create a catalog item
        payload = {
            "table_name": "test_fact_ventas",
            "column_name": "monto_total",
            "friendly_name": "Monto Total de Venta",
            "description": "Importe facturado bruto sin deducciones",
            "business_formula": "SUM(monto_total)",
            "is_ai_generated": False
        }
        res_post = self.client.post("/api/v1/catalog/", json=payload, headers=self.headers)
        self.assertEqual(res_post.status_code, 201)
        item_id = res_post.json()["id"]
        self.assertEqual(res_post.json()["friendly_name"], "Monto Total de Venta")

        # 2. Get list of catalog items
        res_get = self.client.get("/api/v1/catalog/", headers=self.headers)
        self.assertEqual(res_get.status_code, 200)
        items = res_get.json()
        self.assertTrue(any(i["id"] == item_id for i in items))

        # 3. Update catalog item
        update_payload = {
            "description": "Importe total actualizado",
            "business_formula": "SUM(monto_total) * 1.19"
        }
        res_put = self.client.put(f"/api/v1/catalog/{item_id}", json=update_payload, headers=self.headers)
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["description"], "Importe total actualizado")
        self.assertEqual(res_put.json()["business_formula"], "SUM(monto_total) * 1.19")

        # 4. Delete catalog item
        res_del = self.client.delete(f"/api/v1/catalog/{item_id}", headers=self.headers)
        self.assertEqual(res_del.status_code, 200)
        self.assertIn("eliminada", res_del.json()["message"])

        # Verify deletion
        res_get_after = self.client.get("/api/v1/catalog/", headers=self.headers)
        self.assertFalse(any(i["id"] == item_id for i in res_get_after.json()))

    def test_data_dictionary_introspection(self):
        res = self.client.get("/api/v1/catalog/data-dictionary", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tables", data)
        self.assertIn("total_tables", data)
        self.assertIn("total_columns", data)
        self.assertIsInstance(data["tables"], list)

    @patch("app.services.llm_service.LLMService.generate_completion", new_callable=AsyncMock)
    def test_auto_enrich_catalog(self, mock_llm):
        mock_llm.return_value = None  # Use fast heuristic auto-enrichment fallback
        res = self.client.post("/api/v1/catalog/auto-enrich", json={}, headers=self.headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("enriched_count", data)

    def test_upload_sqlite_database_and_delete(self):
        # Create a valid temporary sqlite database file with a table
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            conn = sqlite3.connect(tmp_path)
            conn.execute("CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, nombre TEXT);")
            conn.execute("INSERT INTO test_tbl VALUES (1, 'Ejemplo');")
            conn.commit()
            conn.close()

            with open(tmp_path, "rb") as f:
                file_bytes = f.read()

            file_obj = io.BytesIO(file_bytes)

            # Upload
            res_upload = self.client.post(
                "/api/v1/connectors/upload",
                files={"file": ("test_uploaded_db.sqlite", file_obj, "application/octet-stream")},
                data={"name": "Test Uploaded Database"},
                headers=self.headers
            )
            self.assertEqual(res_upload.status_code, 201, res_upload.text)
            upload_data = res_upload.json()
            conn_id = upload_data["id"]
            self.assertTrue(upload_data["is_uploaded"])

            # Toggle Active
            res_toggle = self.client.post(f"/api/v1/connectors/{conn_id}/toggle-active", headers=self.headers)
            self.assertEqual(res_toggle.status_code, 200)
            self.assertFalse(res_toggle.json()["is_active"])

            # Delete
            res_del = self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)
            self.assertEqual(res_del.status_code, 200)
            self.assertEqual(res_del.json()["id"], conn_id)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
