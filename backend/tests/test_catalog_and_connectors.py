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

    def test_upload_csv_file(self):
        csv_content = (
            "id,producto,precio,categoria\n"
            "1,Laptop Dell,1200.50,Hardware\n"
            "2,Monitor 4K,450.00,Hardware\n"
            "3,Licencia Office,150.00,Software\n"
        ).encode("utf-8")

        file_obj = io.BytesIO(csv_content)
        conn_id = None

        try:
            res_upload = self.client.post(
                "/api/v1/connectors/upload",
                files={"file": ("ventas_importadas.csv", file_obj, "text/csv")},
                data={"name": "Ventas CSV Importadas"},
                headers=self.headers
            )
            self.assertEqual(res_upload.status_code, 201, res_upload.text)
            upload_data = res_upload.json()
            conn_id = upload_data["id"]
            self.assertTrue(upload_data["is_uploaded"])

            # Verify tables in SQLite
            conn_record = self.db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
            self.assertIsNotNone(conn_record)
            sqlite_file = conn_record.host
            self.assertTrue(os.path.exists(sqlite_file))

            sq_conn = sqlite3.connect(sqlite_file)
            cur = sq_conn.cursor()
            rows = cur.execute("SELECT * FROM ventas_importadas;").fetchall()
            self.assertEqual(len(rows), 3)
            sq_conn.close()
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_upload_excel_file(self):
        import openpyxl

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            excel_path = tmp.name

        try:
            wb = openpyxl.Workbook()
            # Sheet 1: Facturas
            ws1 = wb.active
            ws1.title = "Facturas"
            ws1.append(["id", "cliente", "monto", "fecha"])
            ws1.append([101, "Acme Corp", 5500.0, "2024-03-01"])
            ws1.append([102, "Beta LLC", 2300.0, "2024-03-02"])

            # Sheet 2: Clientes
            ws2 = wb.create_sheet(title="Clientes")
            ws2.append(["id", "razon_social", "ciudad"])
            ws2.append([1, "Acme Corp", "Santiago"])
            ws2.append([2, "Beta LLC", "Valparaíso"])

            wb.save(excel_path)
            wb.close()

            with open(excel_path, "rb") as f:
                excel_bytes = f.read()

            file_obj = io.BytesIO(excel_bytes)

            res_upload = self.client.post(
                "/api/v1/connectors/upload",
                files={"file": ("erp_reportes.xlsx", file_obj, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"name": "ERP Financiero Excel"},
                headers=self.headers
            )
            self.assertEqual(res_upload.status_code, 201, res_upload.text)
            upload_data = res_upload.json()
            conn_id = upload_data["id"]

            conn_record = self.db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
            self.assertIsNotNone(conn_record)
            sqlite_file = conn_record.host
            self.assertTrue(os.path.exists(sqlite_file))

            sq_conn = sqlite3.connect(sqlite_file)
            cur = sq_conn.cursor()
            fact_rows = cur.execute("SELECT * FROM facturas;").fetchall()
            client_rows = cur.execute("SELECT * FROM clientes;").fetchall()
            self.assertEqual(len(fact_rows), 2)
            self.assertEqual(len(client_rows), 2)
            sq_conn.close()
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)
            if os.path.exists(excel_path):
                try:
                    os.remove(excel_path)
                except Exception:
                    pass

    def test_upload_database_closed_by_default_permissions(self):
        """
        Uploading a new database must follow the principle of least privilege:
        - Only Admin role gets automatic read permissions.
        - Non-admin roles (Economista, TI, etc.) have NO automatic RoleTablePermission records.
        - Response includes requires_permission_review: True and detected_tables list.
        """
        from app.models.permission import RoleTablePermission
        from app.core.constants import ADMIN_ROLES

        csv_content = b"id_sensor,ubicacion,temperatura\n1,Servidor-01,23.5\n2,Servidor-02,28.1\n"
        file_obj = io.BytesIO(csv_content)

        conn_id = None
        try:
            res_upload = self.client.post(
                "/api/v1/connectors/upload",
                files={"file": ("sensores_iot.csv", file_obj, "text/csv")},
                data={"name": "Sensores IoT Test"},
                headers=self.headers
            )
            self.assertEqual(res_upload.status_code, 201)
            data = res_upload.json()
            conn_id = data["id"]

            self.assertTrue(data.get("requires_permission_review"))
            self.assertIn("sensores_iot", data.get("detected_tables", []))

            # Query all permissions for this connection
            perms = self.db.query(RoleTablePermission).filter(
                RoleTablePermission.connection_id == conn_id
            ).all()

            # Verify permissions exist ONLY for admin roles
            for p in perms:
                role = self.db.query(Role).filter(Role.id == p.role_id).first()
                is_admin_role = (
                    role.name in ADMIN_ROLES
                    or "admin" in role.name.lower()
                    or role.name == "Administrador"
                )
                self.assertTrue(
                    is_admin_role,
                    f"Role '{role.name}' should NOT have automatic permissions on newly uploaded database."
                )

            # Check that non-admin roles have 0 permissions for this connection
            non_admin_roles = self.db.query(Role).filter(
                ~Role.name.in_(ADMIN_ROLES)
            ).all()
            for nar in non_admin_roles:
                if "admin" in nar.name.lower():
                    continue
                nar_perms = self.db.query(RoleTablePermission).filter(
                    RoleTablePermission.connection_id == conn_id,
                    RoleTablePermission.role_id == nar.id
                ).all()
                self.assertEqual(
                    len(nar_perms), 0,
                    f"Non-admin role '{nar.name}' unexpectedly has {len(nar_perms)} permissions."
                )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_multi_active_databases_dictionary_and_catalog(self):
        """
        Ensures that when 2 active databases exist, their data dictionaries
        and semantic catalogs are accurately introspected, isolated, and updated.
        """
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp_path = tmp.name

        conn_id = None
        try:
            conn = sqlite3.connect(tmp_path)
            conn.execute("CREATE TABLE clientes_nuevos (id INTEGER PRIMARY KEY, nombre_cliente TEXT, saldo REAL);")
            conn.execute("INSERT INTO clientes_nuevos VALUES (1, 'Cliente Alfa', 1500.50);")
            conn.execute("INSERT INTO clientes_nuevos VALUES (2, 'Cliente Beta', 3200.00);")
            conn.commit()
            conn.close()

            with open(tmp_path, "rb") as f:
                file_bytes = f.read()

            file_obj = io.BytesIO(file_bytes)

            # Upload second database
            res_upload = self.client.post(
                "/api/v1/connectors/upload",
                files={"file": ("clientes_db.sqlite", file_obj, "application/octet-stream")},
                data={"name": "Base de Datos Clientes Nuevos"},
                headers=self.headers
            )
            self.assertEqual(res_upload.status_code, 201)
            conn_id = res_upload.json()["id"]

            # 1. Verify that semantic catalog was automatically seeded on upload for connection 2
            res_cat_conn2 = self.client.get(f"/api/v1/catalog/?connection_id={conn_id}", headers=self.headers)
            self.assertEqual(res_cat_conn2.status_code, 200)
            conn2_catalog_items = res_cat_conn2.json()
            self.assertTrue(len(conn2_catalog_items) > 0, "Initial catalog entries should be automatically seeded.")
            table_names_seeded = {i["table_name"] for i in conn2_catalog_items}
            self.assertIn("clientes_nuevos", table_names_seeded)

            # 2. Verify Data Dictionary for connection 2 returns its specific tables
            res_dict_conn2 = self.client.get(f"/api/v1/catalog/data-dictionary?connection_id={conn_id}", headers=self.headers)
            self.assertEqual(res_dict_conn2.status_code, 200)
            dict_data_conn2 = res_dict_conn2.json()
            self.assertEqual(dict_data_conn2["connection_id"], conn_id)
            self.assertEqual(dict_data_conn2["connection_name"], "Base de Datos Clientes Nuevos")
            tbl_names = [t["table_name"] for t in dict_data_conn2["tables"]]
            self.assertIn("clientes_nuevos", tbl_names)

            # 3. Verify auto-enriching connection 2 works
            res_enrich = self.client.post(
                "/api/v1/catalog/auto-enrich",
                json={"connection_id": conn_id},
                headers=self.headers
            )
            self.assertEqual(res_enrich.status_code, 200)
            self.assertTrue(res_enrich.json()["success"])

            # 4. Verify connection 1's dictionary is distinct from connection 2
            res_dict_conn1 = self.client.get("/api/v1/catalog/data-dictionary?connection_id=1", headers=self.headers)
            self.assertEqual(res_dict_conn1.status_code, 200)
            tbl_names_conn1 = [t["table_name"] for t in res_dict_conn1.json()["tables"]]
            self.assertNotIn("clientes_nuevos", tbl_names_conn1)

        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass



