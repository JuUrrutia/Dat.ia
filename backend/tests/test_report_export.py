import unittest
import uuid
from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.session import UserSession
from app.core.security import create_access_token

SAMPLE_EXPORT_PAYLOAD = {
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
    # 1x1 transparent PNG base64
    "chart_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
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

    def tearDown(self):
        self.db.close()

    def test_export_pdf_success(self):
        response = self.client.post(
            "/api/v1/reports/export/pdf",
            json=SAMPLE_EXPORT_PAYLOAD,
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/pdf", response.headers["content-type"])
        self.assertIn("attachment; filename=informe_ejecutivo_datia_", response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

        # Verify AuditLog entry was registered
        log = self.db.query(AuditLog).filter(AuditLog.validation_status == "EXPORTADO_PDF").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.username, "admin")
        self.assertEqual(log.question_prompt, SAMPLE_EXPORT_PAYLOAD["question"])

    def test_export_excel_success(self):
        response = self.client.post(
            "/api/v1/reports/export/excel",
            json=SAMPLE_EXPORT_PAYLOAD,
            headers=self.headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", response.headers["content-type"])
        self.assertIn("attachment; filename=datos_datia_", response.headers["content-disposition"])
        # Check ZIP / OpenXML magic header: PK\x03\x04
        self.assertTrue(response.content.startswith(b"PK\x03\x04"))

        # Verify AuditLog entry was registered
        log = self.db.query(AuditLog).filter(AuditLog.validation_status == "EXPORTADO_EXCEL").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.username, "admin")
        self.assertEqual(log.rows_returned, 5)

    def test_export_endpoints_require_authentication(self):
        resp_pdf = self.client.post("/api/v1/reports/export/pdf", json=SAMPLE_EXPORT_PAYLOAD)
        self.assertEqual(resp_pdf.status_code, 401)

        resp_excel = self.client.post("/api/v1/reports/export/excel", json=SAMPLE_EXPORT_PAYLOAD)
        self.assertEqual(resp_excel.status_code, 401)
