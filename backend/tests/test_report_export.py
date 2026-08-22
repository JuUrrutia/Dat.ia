import io
import json
import uuid
import unittest
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models.session import UserSession
from app.core.security import create_access_token, get_password_hash

SAMPLE_SNAPSHOT_DATA = {
    "question": "¿Cuáles fueron los 5 productos más vendidos del trimestre?",
    "summary_text": "Los 5 productos más vendidos totalizaron 12,500 unidades vendidas.",
    "executive_report": {
        "overview": "El desempeño del trimestre muestra un crecimiento sólido en la línea de periféricos.",
        "key_findings": [
            "El producto 'Teclado Mecánico RGB' lidera el volumen con 4,200 unidades.",
            "El ticket promedio aumentó un 12% interanual.",
            "El canal online representa el 68% de las conversiones totales."
        ],
        "recommendations": [
            "Aumentar el stock de seguridad para el producto líder.",
            "Lanzar campaña de cross-selling con monitores gamer.",
            "Revisar márgenes de distribución en el canal retail."
        ],
        "risk_level": "MEDIO",
        "business_impact": "Generación proyectada de $45,000 USD en ingresos adicionales."
    },
    "kpis": [
        {"title": "Ventas Totales", "value": "$145,200", "subtitle": "+15% vs Q anterior"},
        {"title": "Unidades", "value": "12,500", "subtitle": "Top 5 productos"},
        {"title": "Margen Bruto", "value": "34.5%", "subtitle": "Estable"}
    ],
    "gauges": [
        {"title": "Cumplimiento Meta", "percentage": 88.5, "value_label": "88.5%", "target_label": "100%"}
    ],
    "data_columns": ["id_producto", "nombre_producto", "unidades_vendidas", "total_ingresos"],
    "data_rows": [
        {"id_producto": 101, "nombre_producto": "Teclado Mecánico RGB", "unidades_vendidas": 4200, "total_ingresos": 42000.0},
        {"id_producto": 102, "nombre_producto": "Mouse Gamer Pro", "unidades_vendidas": 3100, "total_ingresos": 24800.0},
        {"id_producto": 103, "nombre_producto": "Monitor 27 UHD", "unidades_vendidas": 2200, "total_ingresos": 55000.0},
        {"id_producto": 104, "nombre_producto": "Auriculares Wireless", "unidades_vendidas": 1800, "total_ingresos": 14400.0},
        {"id_producto": 105, "nombre_producto": "Mousepad XL", "unidades_vendidas": 1200, "total_ingresos": 9000.0}
    ],
    "traceability": {
        "sql_executed": "SELECT id_producto, nombre_producto, unidades_vendidas, total_ingresos FROM ventas ORDER BY unidades_vendidas DESC LIMIT 5",
        "execution_time_ms": 14,
        "rows_returned": 5,
        "validation_status": "APROBADO",
        "schema_tables_used": ["ventas"]
    },
    "target_database": "demo_corporativa.db"
}

class TestReportExport(unittest.TestCase):
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

        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create an AuditLog entry with result_snapshot for admin user
        self.audit_log = AuditLog(
            user_id=self.user.id,
            username=self.user.username,
            user_role="Administrador",
            question_prompt=SAMPLE_SNAPSHOT_DATA["question"],
            sql_generated=SAMPLE_SNAPSHOT_DATA["traceability"]["sql_executed"],
            validation_status="APROBADO",
            target_database="demo_corporativa.db",
            execution_time_ms=14,
            rows_returned=5,
            result_snapshot=json.dumps(SAMPLE_SNAPSHOT_DATA)
        )
        self.db.add(self.audit_log)
        self.db.commit()
        self.db.refresh(self.audit_log)

    def tearDown(self):
        if hasattr(self, "audit_log") and self.audit_log.id:
            self.db.query(AuditLog).filter(AuditLog.id == self.audit_log.id).delete()
            self.db.commit()
        self.db.close()

    def test_export_pdf_success(self):
        """Generates PDF using server-persisted audit snapshot by audit_log_id."""
        chart_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = self.client.post(
            "/api/v1/reports/export/pdf",
            json={"audit_log_id": self.audit_log.id, "chart_image_base64": chart_base64},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/pdf", response.headers["content-type"])
        self.assertIn("attachment; filename=informe_ejecutivo_datia_", response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

        # Verify export audit log entry was registered
        log = self.db.query(AuditLog).filter(AuditLog.validation_status == "EXPORTADO_PDF").order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.username, "admin")
        self.assertEqual(log.question_prompt, SAMPLE_SNAPSHOT_DATA["question"])

    def test_export_excel_success(self):
        """Generates Excel workbook using server-persisted audit snapshot by audit_log_id."""
        response = self.client.post(
            "/api/v1/reports/export/excel",
            json={"audit_log_id": self.audit_log.id},
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", response.headers["content-type"])
        self.assertIn("attachment; filename=datos_datia_", response.headers["content-disposition"])
        # Check ZIP / OpenXML magic header: PK\x03\x04
        self.assertTrue(response.content.startswith(b"PK\x03\x04"))

        # Verify export audit log entry was registered
        log = self.db.query(AuditLog).filter(AuditLog.validation_status == "EXPORTADO_EXCEL").order_by(AuditLog.id.desc()).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.username, "admin")
        self.assertEqual(log.rows_returned, 5)

    def test_export_endpoints_require_authentication(self):
        """Without JWT Authorization header, export endpoints return 401."""
        resp_pdf = self.client.post("/api/v1/reports/export/pdf", json={"audit_log_id": self.audit_log.id})
        self.assertEqual(resp_pdf.status_code, 401)

        resp_excel = self.client.post("/api/v1/reports/export/excel", json={"audit_log_id": self.audit_log.id})
        self.assertEqual(resp_excel.status_code, 401)

    def test_export_nonexistent_audit_log_returns_404(self):
        """Exporting a non-existent audit_log_id returns 404 Not Found."""
        response = self.client.post(
            "/api/v1/reports/export/pdf",
            json={"audit_log_id": 99999999},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Registro de auditoría no encontrado", response.json().get("detail", ""))

    def test_cannot_export_other_user_audit_log(self):
        """
        A non-admin user cannot export another user's audit log result snapshot.
        Must return 403 Forbidden.
        """
        # 1. Create User A (regular non-admin)
        usuario_role = self.db.query(Role).filter(Role.name == "Usuario").first()
        user_a = User(
            username=f"user_a_{uuid.uuid4().hex[:6]}",
            hashed_password=get_password_hash("Password123!"),
            is_admin=False,
            is_active=True,
            role_id=usuario_role.id if usuario_role else None
        )
        # 2. Create User B (regular non-admin)
        user_b = User(
            username=f"user_b_{uuid.uuid4().hex[:6]}",
            hashed_password=get_password_hash("Password123!"),
            is_admin=False,
            is_active=True,
            role_id=usuario_role.id if usuario_role else None
        )
        self.db.add(user_a)
        self.db.add(user_b)
        self.db.commit()
        self.db.refresh(user_a)
        self.db.refresh(user_b)

        # 3. Create AuditLog owned by User A
        log_a = AuditLog(
            user_id=user_a.id,
            username=user_a.username,
            user_role="Usuario",
            question_prompt="Consulta confidencial de User A",
            sql_generated="SELECT 1",
            validation_status="APROBADO",
            target_database="demo_corporativa.db",
            execution_time_ms=5,
            rows_returned=1,
            result_snapshot=json.dumps(SAMPLE_SNAPSHOT_DATA)
        )
        self.db.add(log_a)
        self.db.commit()
        self.db.refresh(log_a)

        # 4. Generate JWT for User B
        jti_b = str(uuid.uuid4())
        token_b = create_access_token(subject=user_b.id, jti=jti_b)
        session_b = UserSession(user_id=user_b.id, jti=jti_b, is_revoked=False)
        self.db.add(session_b)
        self.db.commit()
        headers_b = {"Authorization": f"Bearer {token_b}"}

        try:
            # User B attempts to export User A's audit log
            resp_pdf = self.client.post(
                "/api/v1/reports/export/pdf",
                json={"audit_log_id": log_a.id},
                headers=headers_b
            )
            self.assertEqual(resp_pdf.status_code, 403)
            self.assertIn("No tienes permisos para exportar consultas de otro usuario", resp_pdf.json().get("detail", ""))

            resp_excel = self.client.post(
                "/api/v1/reports/export/excel",
                json={"audit_log_id": log_a.id},
                headers=headers_b
            )
            self.assertEqual(resp_excel.status_code, 403)
            self.assertIn("No tienes permisos para exportar consultas de otro usuario", resp_excel.json().get("detail", ""))
        finally:
            self.db.query(AuditLog).filter(AuditLog.id == log_a.id).delete()
            self.db.query(UserSession).filter(UserSession.user_id == user_b.id).delete()
            self.db.query(User).filter(User.id.in_([user_a.id, user_b.id])).delete()
            self.db.commit()

if __name__ == "__main__":
    unittest.main()
