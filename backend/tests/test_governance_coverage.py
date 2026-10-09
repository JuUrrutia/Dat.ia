"""La cobertura de gobernanza tiene que distinguir "asignada" de "huérfana".

`GET /permissions` muestra la matriz, pero no responde "¿qué de esta conexión no
ve NINGÚN rol?". `GET /permissions/coverage` sí, y todo lo que devuelve es
DERIVADO: sale del mismo `GovernanceGuard` que decide en el chat. Estos tests no
comprueban que haya una barra bonita, comprueban que el número sea el que el
guardarraíl realmente aplica — y sobre todo que una tabla sin ningún lector
aparezca como huérfana, que es el único motivo por el que existe el endpoint.
"""

import os
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient

from main import app  # noqa: F401  registra los mappers de SQLAlchemy

from app.modules.admin_catalog.models import (
    CorporateConnection, DatabaseType, RoleColumnPermission, RoleTablePermission,
)
from app.modules.auth.models import Role
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.chat_engine.governance_guard import GovernanceGuard

COVERAGE_URL = "/api/v1/permissions/coverage"
CONN_NAME = "TEST cobertura (efimera)"


class TestGovernanceCoverage(unittest.TestCase):
    """Cada test siembra su propio archivo SQLite: el universo de tablas de una
    conexión sale de la introspección FÍSICA, así que sin un archivo propio las
    afirmaciones correrían contra las tablas de la demo y no probarían nada."""

    def setUp(self):
        from app.core.database import SessionLocal

        self.client = TestClient(app)
        self.db = SessionLocal()
        self.admin_token = self._login("admin", "admin123")
        self.analista = self._role("Analista Financiero & Comercial") or self._role("Economista")
        self._tmpdir = tempfile.TemporaryDirectory()
        self.conn_id = None

        # Rastro de una corrida anterior interrumpida: `name` es UNIQUE y el
        # teardown puede no haber corrido (Ctrl+C, timeout). Un nombre fijo sin
        # esta limpieza hace fallar el setUp por `UniqueViolation`, que no es el
        # bug que este archivo investiga.
        self.db.query(CorporateConnection).filter(CorporateConnection.name == CONN_NAME).delete(
            synchronize_session=False
        )
        self.db.commit()

    def _role(self, name):
        r = self.db.query(Role).filter(Role.name == name).first()
        self.assertIsNotNone(r, f"el rol {name} no esta sembrado")
        return r

    def _login(self, username, password):
        resp = self.client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(resp.status_code, 200, resp.text[:200])
        return resp.json()["access_token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _apunta_a(self, *tablas):
        """Crea un SQLite con exactamente esas tablas y una conexion que lo apunte."""
        path = os.path.join(self._tmpdir.name, f"cobertura_{self.conn_id}_{len(tablas)}.sqlite")
        conn = sqlite3.connect(path)
        try:
            for t in tablas:
                conn.execute(f'CREATE TABLE "{t}" (id INTEGER PRIMARY KEY, valor TEXT)')
            conn.commit()
        finally:
            conn.close()

        row = CorporateConnection(
            name=CONN_NAME,
            db_type=DatabaseType.SQLITE,
            host=path,
            port=0,
            database_name=os.path.basename(path),
            username="admin",
            encrypted_password="",
            is_active=False,
            is_uploaded=True,
        )
        self.db.add(row)
        self.db.commit()
        self.conn_id = row.id
        return self.conn_id

    def _grant(self, role_id, table, is_allowed=True):
        self.db.add(RoleTablePermission(
            role_id=role_id, connection_id=self.conn_id,
            schema_name="main", table_name=table,
            is_allowed=is_allowed, granted_by_admin=True,
        ))
        self.db.commit()
        # El prompt del chat esta cacheado 10 minutos: sin esto el grant no se ve
        # y el endpoint reportaria la matriz de antes.
        DynamicSchemaPruningService.invalidate_schema_cache(self.conn_id)

    def _coverage(self, token=None):
        resp = self.client.get(
            COVERAGE_URL,
            params={"connection_id": self.conn_id},
            headers=self._auth(token or self.admin_token),
        )
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        return resp.json()

    def _table(self, payload, name):
        for t in payload["tables"]:
            if t["table"] == name:
                return t
        self.fail(f"la tabla {name} no aparece en la cobertura: {[t['table'] for t in payload['tables']]}")

    # --- 1. El endpoint es de admin, como la matriz que audita ----------------

    def test_es_de_admin(self):
        self._apunta_a("fact_con_lector", "fact_huerfana_prueba")

        sin_token = self.client.get(COVERAGE_URL, params={"connection_id": self.conn_id})
        self.assertEqual(sin_token.status_code, 401, sin_token.text[:200])

        no_admin = self._login("economista", "economista123")
        resp = self.client.get(
            COVERAGE_URL, params={"connection_id": self.conn_id}, headers=self._auth(no_admin)
        )
        self.assertEqual(resp.status_code, 403, resp.text[:200])

    # --- 2. Con al menos un lector NO es huérfana -----------------------------

    def test_tabla_con_lector_no_es_huerfana(self):
        self._apunta_a("fact_con_lector", "fact_huerfana_prueba")
        self._grant(self.analista.id, "fact_con_lector")
        self._grant(self.analista.id, "fact_huerfana_prueba", is_allowed=False)

        payload = self._coverage()
        con_lector = self._table(payload, "fact_con_lector")

        self.assertEqual(con_lector["coverage"], "assigned")
        self.assertIn(self.analista.name, con_lector["visible_to_roles"])
        self.assertEqual(
            [t["table"] for t in payload["tables"] if t["coverage"] == "orphaned"],
            ["fact_huerfana_prueba"],
        )

    # --- 3. Sin ningún lector SÍ es huérfana (el caso que justifica la vista) --

    def test_tabla_que_ningun_rol_puede_leer_es_huerfana(self):
        # Denegada al unico rol con fila: "alguien la toco" pero NADIE la lee. Un
        # `is_allowed` leido por rol daria esta tabla por visible.
        self._apunta_a("fact_huerfana_prueba")
        self._grant(self.analista.id, "fact_huerfana_prueba", is_allowed=False)

        payload = self._coverage()
        huerfana = self._table(payload, "fact_huerfana_prueba")

        self.assertEqual(huerfana["coverage"], "orphaned")
        self.assertEqual(huerfana["visible_to_roles"], [])
        self.assertEqual(payload["summary"]["orphaned_tables"], 1)
        self.assertEqual(payload["summary"]["assigned_tables"], 0)
        self.assertIn(self.analista.name, huerfana["assigned_roles"],
                      "un DENY es una decision del admin sobre esa tabla")

    # --- 4. El summary cuadra con la lista ------------------------------------

    def test_summary_cuadra_con_la_lista(self):
        self._apunta_a("fact_con_lector", "fact_huerfana_prueba")
        self._grant(self.analista.id, "fact_con_lector")
        self._grant(self.analista.id, "fact_huerfana_prueba", is_allowed=False)

        payload = self._coverage()
        s = payload["summary"]
        asignadas = [t["table"] for t in payload["tables"] if t["coverage"] == "assigned"]
        huerfanas = [t["table"] for t in payload["tables"] if t["coverage"] == "orphaned"]

        self.assertEqual(s["total_tables"], len(payload["tables"]))
        self.assertEqual(s["assigned_tables"], len(asignadas))
        self.assertEqual(s["orphaned_tables"], len(huerfanas))
        self.assertEqual(s["assigned_tables"] + s["orphaned_tables"], s["total_tables"])
        self.assertEqual(asignadas, ["fact_con_lector"])
        self.assertEqual(huerfanas, ["fact_huerfana_prueba"])

    # --- 5. Las columnas vienen del guard, no de reglas propias ---------------

    def test_columnas_coinciden_con_governance_guard(self):
        from app.modules.admin_catalog.models import ColumnPermissionType

        self._apunta_a("dim_clientes")
        self._grant(self.analista.id, "dim_clientes")
        # Las mismas reglas que la demo usa para dim_clientes, pero en la conexion
        # de este test: sin fila de columna no hay nada que atribuir y el assert
        # compararia dos conjuntos vacios.
        for columna, tipo in (("tarjeta_credito_token", ColumnPermissionType.BLOCKED),
                              ("rut_dni_cliente", ColumnPermissionType.MASKED)):
            self.db.add(RoleColumnPermission(
                role_id=self.analista.id, connection_id=self.conn_id,
                schema_name="main", table_name="dim_clientes",
                column_name=columna, permission_type=tipo,
            ))
        self.db.commit()
        DynamicSchemaPruningService.invalidate_schema_cache(self.conn_id)

        reportada = self._table(self._coverage(), "dim_clientes")
        guard_bloqueadas = GovernanceGuard.get_blocked_columns_for_role(
            self.analista.name, False, db=self.db,
            role_id=self.analista.id, connection_id=self.conn_id,
        ) or set()
        guard_enmascaradas = GovernanceGuard.get_masked_columns_for_role(
            self.analista.name, False, db=self.db,
            role_id=self.analista.id, connection_id=self.conn_id,
        ) or set()

        # Guarda anti-vacío: sin esto, si el guard no bloqueara nada, los dos
        # asserts de abajo compararian `set() == set()` y pasarían sin comprobar.
        self.assertIn("tarjeta_credito_token", guard_bloqueadas,
                      f"el guard no bloqueo tarjeta_credito_token: {guard_bloqueadas}")
        self.assertIn("rut_dni_cliente", guard_enmascaradas,
                      f"el guard no enmascaro rut_dni_cliente: {guard_enmascaradas}")

        self.assertEqual(reportada["blocked_columns"], ["tarjeta_credito_token"])
        self.assertEqual(reportada["masked_columns"], ["rut_dni_cliente"])

    # --- Aislamiento ---------------------------------------------------------

    def tearDown(self):
        DynamicSchemaPruningService.invalidate_schema_cache(getattr(self, "conn_id", None))
        db = getattr(self, "db", None)
        if db is not None:
            if getattr(self, "conn_id", None):
                db.query(RoleTablePermission).filter(
                    RoleTablePermission.connection_id == self.conn_id
                ).delete(synchronize_session=False)
                db.query(RoleColumnPermission).filter(
                    RoleColumnPermission.connection_id == self.conn_id
                ).delete(synchronize_session=False)
                db.query(CorporateConnection).filter(
                    CorporateConnection.id == self.conn_id
                ).delete(synchronize_session=False)
                db.commit()
            db.close()
        td = getattr(self, "_tmpdir", None)
        if td is not None:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()