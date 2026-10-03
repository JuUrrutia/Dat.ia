"""El escaneo de anomalias debe respetar el RBAC y no proyectar columnas sensibles.

Antes de este fix, `/system/anomalies` elegia la primera tabla fact_ alfabetica del
servidor y ejecutaba `SELECT * FROM <tabla> LIMIT 60` via `execute_raw_sql`, sin pasar
por ASTValidator ni por el filtro de columnas. Eso devolvia valores reales de columnas
BLOCKED y MASKED a cualquier usuario autenticado, sin importar su rol, y los metia en
la descripcion de la anomalia.
"""

import unittest

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.modules.auth.models import User
from app.modules.chat_engine.governance_guard import GovernanceGuard
from main import app


def _table_from_title(title: str) -> str:
    """Los titulos son 'Anomalía estadística en <tabla>'."""
    return title.rsplit(" ", 1)[-1]


class TestAnomaliesRespectRbac(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def _token(self, username, password):
        resp = self.client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()["access_token"]

    def _scan_for(self, username, password):
        token = self._token(username, password)
        resp = self.client.get(
            "/api/v1/system/anomalies?connection_id=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()["anomalies"]

    def test_no_data_anomaly_outside_allowed_tables(self):
        """Ninguna anomalia de calidad de datos puede salir de una tabla prohibida."""
        for username, password in (("ti", "ti123"), ("economista", "economista123")):
            with self.subTest(rol=username):
                user = self.db.query(User).filter(User.username == username).first()
                if user is None:
                    self.skipTest(f"la cuenta demo {username} no existe")

                role_name = user.role.name if user.role else "Usuario"
                allowed = {
                    t.lower()
                    for t in (
                        GovernanceGuard.get_allowed_tables_for_role(
                            role_name, user.is_admin, db=self.db,
                            role_id=user.role_id, connection_id=1,
                        ) or set()
                    )
                }

                data_anomalies = [
                    a for a in self._scan_for(username, password)
                    if a.get("type") == "data_quality"
                ]

                for anomaly in data_anomalies:
                    table = _table_from_title(anomaly["title"]).lower()
                    self.assertIn(
                        table, allowed,
                        f"el rol {username} recibio una anomalia de {table}, "
                        f"fuera de su matriz RBAC {sorted(allowed)}",
                    )

    def test_anomaly_payload_has_no_raw_column_dump(self):
        """La descripcion no debe volcar valores de columnas no numericas.

        Con `SELECT *` la deteccion de outliers recibia todas las columnas y armaba
        descripciones con valores reales de columnas MASKED/BLOCKED. Ahora solo se
        proyecta la metrica numerica, asi que el payload es dimensional y no lleva
        ni RUT ni token ni salario.
        """
        anomalies = self._scan_for("admin", "admin123")
        for anomaly in anomalies:
            if anomaly.get("type") != "data_quality":
                continue
            payload = str(anomaly)
            for leaked in ("tarjeta_credito", "api_key", "rut_dni", "salario", "sueldo"):
                self.assertNotIn(
                    leaked, payload,
                    f"la anomalia expone una columna sensible: {leaked}",
                )


if __name__ == "__main__":
    unittest.main()
