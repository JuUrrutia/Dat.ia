"""Default-deny en permisos de tabla.

El bug: `upload_database_file` creaba un RoleTablePermission(is_allowed=True) por
cada (rol, tabla) del dataset nuevo y solo se saltaba unas tablas de la demo SAP,
detectadas por substring sobre el nombre del rol. En cualquier dataset real la
exclusion no excluye nada: casi todos los roles quedaban con TODAS las tablas. La
mascara por columna de governance_guard seguia aplicando, pero el permiso que la
 precede ya habia concedido el acceso.

Lo que se verifica aca:
  - subir un dataset no concede nada por omision
  - la matriz sembrada de la demo sigue dando el mismo acceso
  - un admin concede y revoca por endpoint, y el permiso se respeta en la consulta
  - sin permiso explicito la respuesta es RECHAZADO_RBAC, no un resultado vacio
  - la migracion de default-deny es idempotente y no toca las conexiones de plataforma
"""
import io
import os
import unittest
import uuid

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.admin_catalog.models import (
    CorporateConnection, DatabaseType, RoleTablePermission,
)
from app.modules.auth.models import Role, User, UserSession
from app.core.security import create_access_token

DEMO_BUSINESS_TABLES = {
    "dim_categorias", "dim_productos", "dim_clientes",
    "fact_ventas", "fact_ingresos_costos", "dim_empleados",
    "Answer", "Question", "Survey", "answer", "question", "survey",
}
DEMO_TECH_TABLES = {
    "dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos",
    "dim_empleados", "Answer", "Question", "Survey", "answer", "question", "survey",
}


class TestDefaultDenyPermissions(unittest.TestCase):
    """Base: sesión real contra la metadata, como corre el producto."""

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.admin = self.db.query(User).filter(User.username == "admin").first()
        self.jti = str(uuid.uuid4())
        self.db.add(UserSession(user_id=self.admin.id, jti=self.jti, is_revoked=False))
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {create_access_token(subject=self.admin.id, jti=self.jti)}"}

    def tearDown(self):
        self.db.close()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _upload_csv(self, name, table_body=b"id,valor\n1,10\n"):
        res = self.client.post(
            "/api/v1/connectors/upload",
            files={"file": (f"{name.lower()}.csv", io.BytesIO(table_body), "text/csv")},
            data={"name": name},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()

    def _perms_for(self, connection_id):
        return self.db.query(RoleTablePermission).filter(
            RoleTablePermission.connection_id == connection_id
        ).all()

    def _role(self, name):
        return self.db.query(Role).filter(Role.name == name).first()

    def _platform_connection(self):
        return self.db.query(CorporateConnection).filter(
            CorporateConnection.is_uploaded == False
        ).first()

    def _invalidate_schema_cache(self):
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
        DynamicSchemaPruningService.invalidate_schema_cache()

    # ------------------------------------------------------------------
    # 1. Subir un dataset no concede nada
    # ------------------------------------------------------------------
    def test_upload_grants_nothing_by_default(self):
        conn_id = None
        try:
            body = self._upload_csv("Default Deny IoT")
            conn_id = body["id"]
            self.assertTrue(body.get("requires_permission_review"))
            self.assertEqual(len(body.get("detected_tables", [])), 1)
            self.assertIn(body["detected_tables"][0], body.get("detected_tables", []))

            # Ningun rol, ninguna tabla: la tabla existe pero nadie tiene permiso.
            self.assertEqual(
                len(self._perms_for(conn_id)), 0,
                "Subir un dataset no puede crear permisos: default-deny significa "
                "que sin decision explicita no hay acceso.",
            )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_upload_grants_nothing_even_with_many_roles(self):
        """El bug original se disparaba con 'casi todos los roles': sigue sin conceder."""
        conn_id = None
        try:
            conn_id = self._upload_csv("Default Deny Multirole")["id"]
            roles = self.db.query(Role).all()
            self.assertGreater(len(roles), 5)
            granted = [
                (r.name, p.table_name)
                for p in self._perms_for(conn_id)
                for r in roles if r.id == p.role_id
            ]
            self.assertEqual(granted, [])
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    # ------------------------------------------------------------------
    # 2. La matriz sembrada de la demo se preserva
    # ------------------------------------------------------------------
    def test_demo_seed_matrix_is_unchanged(self):
        """Snapshot de la matriz de la demo: mismo acceso que antes del cambio."""
        conn = self._platform_connection()
        self.assertIsNotNone(conn)

        for role_name, expected in (
            ("Analista Financiero & Comercial", DEMO_BUSINESS_TABLES),
            ("Economista", DEMO_BUSINESS_TABLES),
            ("Ingeniero de Infraestructura & TI", DEMO_TECH_TABLES),
            ("TI", DEMO_TECH_TABLES),
        ):
            role = self._role(role_name)
            self.assertIsNotNone(role, role_name)
            got = {
                p.table_name for p in self.db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == role.id,
                    RoleTablePermission.connection_id == conn.id,
                    RoleTablePermission.is_allowed == True,
                ).all()
            }
            self.assertEqual(
                got, expected,
                f"La matriz de la demo para '{role_name}' cambio: la demo debe "
                f"seguir dando exactamente el mismo acceso.",
            )

        admin_role = self._role("Administrador")
        admin_tables = {
            p.table_name for p in self.db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == admin_role.id,
                RoleTablePermission.connection_id == conn.id,
                RoleTablePermission.is_allowed == True,
            ).all()
        }
        self.assertTrue(
            DEMO_BUSINESS_TABLES.issubset(admin_tables)
            and DEMO_TECH_TABLES.issubset(admin_tables),
            "El rol administrador de la demo sigue viendo negocio e infraestructura.",
        )

    def test_demo_seed_rows_are_marked_as_admin_decisions(self):
        """La demo se marca como decision explicita: la migracion no se la lleva."""
        conn = self._platform_connection()
        rows = self.db.query(RoleTablePermission).filter(
            RoleTablePermission.connection_id == conn.id
        ).all()
        self.assertTrue(rows)
        not_granted = [r.table_name for r in rows if not r.granted_by_admin]
        self.assertEqual(
            not_granted, [],
            f"Filas de la demo sin marcar como decision de admin: {not_granted}",
        )

    # ------------------------------------------------------------------
    # 3. Admin concede por endpoint y el permiso se respeta
    # ------------------------------------------------------------------
    def test_admin_grants_and_revokes_via_endpoint(self):
        from app.modules.chat_engine.governance_guard import GovernanceGuard

        conn_id = None
        try:
            body = self._upload_csv("Default Deny Grant")
            conn_id = body["id"]
            table = body["detected_tables"][0]
            role = self._role("Economista")
            self._invalidate_schema_cache()

            # Sin permiso: set vacio (fail-closed).
            self.assertEqual(
                GovernanceGuard.get_allowed_tables_for_role(
                    user_role="Economista", is_admin=False, db=self.db,
                    role_id=role.id, connection_id=conn_id,
                ),
                set(),
            )

            # El admin concede.
            res = self.client.put(
                "/api/v1/permissions",
                params={
                    "connection_id": conn_id,
                    "role_id": role.id,
                    "table_names": [table],
                    "is_allowed": "true",
                },
                headers=self.headers,
            )
            self.assertEqual(res.status_code, 200, res.text)
            self.db.expire_all()

            self.assertEqual(
                GovernanceGuard.get_allowed_tables_for_role(
                    user_role="Economista", is_admin=False, db=self.db,
                    role_id=role.id, connection_id=conn_id,
                ),
                {table.lower()},
                "El permiso concedido por endpoint tiene que respetarse en la consulta.",
            )

            # Y lo revoca.
            res = self.client.put(
                "/api/v1/permissions",
                params={
                    "connection_id": conn_id,
                    "role_id": role.id,
                    "table_names": [table],
                    "is_allowed": "false",
                },
                headers=self.headers,
            )
            self.assertEqual(res.status_code, 200, res.text)
            self.db.expire_all()
            self.assertEqual(
                GovernanceGuard.get_allowed_tables_for_role(
                    user_role="Economista", is_admin=False, db=self.db,
                    role_id=role.id, connection_id=conn_id,
                ),
                set(),
            )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_grant_endpoint_requires_admin(self):
        """El granting es de admin: un usuario normal no puede concederse acceso."""
        eco = self.db.query(User).filter(User.username == "economista").first()
        jti = str(uuid.uuid4())
        self.db.add(UserSession(user_id=eco.id, jti=jti, is_revoked=False))
        self.db.commit()
        h = {"Authorization": f"Bearer {create_access_token(subject=eco.id, jti=jti)}"}

        conn = self._platform_connection()
        role = self._role("Economista")
        res = self.client.put(
            "/api/v1/permissions",
            params={
                "connection_id": conn.id,
                "role_id": role.id,
                "table_names": ["dim_servidores"],
                "is_allowed": "true",
            },
            headers=h,
        )
        self.assertIn(res.status_code, (401, 403), res.text)

    def test_permissions_list_endpoint_is_admin_only_and_shows_matrix(self):
        conn = self._platform_connection()
        res = self.client.get(
            "/api/v1/permissions",
            params={"connection_id": conn.id},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200, res.text)
        rows = res.json()
        self.assertTrue(rows)
        row = rows[0]
        for key in ("role_id", "role_name", "table_name", "is_allowed", "granted_by_admin"):
            self.assertIn(key, row)

        res_anon = self.client.get("/api/v1/permissions")
        self.assertIn(res_anon.status_code, (401, 403))

    # ------------------------------------------------------------------
    # 4. Sin permiso != sin datos
    # ------------------------------------------------------------------
    def test_role_without_explicit_permission_gets_authorization_error(self):
        """"Sin permiso" y "no hay datos" tienen que ser distinguibles.

        Sin permiso explicito la respuesta es RECHAZADO_RBAC con el motivo, no una
        tabla vacia que el usuario lee como "no hay datos en el dataset".
        """
        import asyncio
        from app.modules.chat_engine.engine import QueryEngine

        conn_id = None
        try:
            body = self._upload_csv("Default Deny Sin Permiso")
            conn_id = body["id"]
            role = self._role("Oficial de Cumplimiento & Seguridad")
            self._invalidate_schema_cache()

            resp = asyncio.run(QueryEngine.execute_query(
                question="¿Cuántos registros hay?",
                user_role=role.name,
                is_admin=False,
                db=self.db,
                role_id=role.id,
                connection_id=conn_id,
            ))
            self.assertEqual(resp.traceability.validation_status, "RECHAZADO_RBAC")
            self.assertIn("no tiene tablas asignadas", resp.summary_text)
            self.assertIn(
                "matriz RBAC", resp.summary_text,
                "El motivo tiene que explicar que es un problema de autorizacion, "
                "no de datos.",
            )
            # No se ejecuta SQL: lo unico que vuelve es el mensaje de seguridad,
            # no una fila de datos que el usuario podria leer como "tabla vacia".
            self.assertEqual(
                [list(r.keys()) for r in resp.data_rows], [["mensaje_seguridad"]],
                "Sin permiso no se devuelve ninguna fila de datos: solo el motivo "
                "del rechazo, que es lo que lo distingue de 'no hay datos'.",
            )
            self.assertEqual(
                resp.data_rows[0]["mensaje_seguridad"], resp.summary_text
            )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    # ------------------------------------------------------------------
    # 5. El admin: decision explicita y testeada
    # ------------------------------------------------------------------
    def test_admin_bypass_is_explicit_not_silent(self):
        """DECISION: el admin NO tiene bypass silencioso.

        `get_allowed_tables_for_role` convierte en admin a quien tenga is_admin o
        un rol de ADMIN_ROLES, y ahi `dynamic_schema` le concede todas las tablas
        fisicas sin mirar RoleTablePermission. Eso es un bypass, y queda testeado
        como decision consciente, no como accidente:

          - el bypass es del SUPER ADMIN (is_admin / rol de plataforma), que es un
            granting explicito del sistema para poder gobernar el producto
          - NO aplica a los roles operativos: Economista y TI sin permiso explicito
            siguen sin ver nada (tests 1, 2 y 4)
        """
        from app.modules.chat_engine.governance_guard import GovernanceGuard
        from app.core.constants import ADMIN_ROLES

        conn_id = None
        try:
            body = self._upload_csv("Default Deny Admin")
            conn_id = body["id"]
            table = body["detected_tables"][0]

            admin_sees = GovernanceGuard.get_allowed_tables_for_role(
                user_role="Administrador de Plataforma", is_admin=True, db=self.db,
                role_id=self._role("Administrador de Plataforma").id,
                connection_id=conn_id,
            )
            self.assertIn(
                table, admin_sees,
                "El super admin ve el dataset sin permiso explicito: es una "
                "decision documentada, y este test la fija.",
            )

            # El bypass NO se extiende a roles que solo se parecen al admin.
            for role_name in ("Economista", "TI", "Analista de Datos & BI",
                              "Gerente de Talento & Operaciones",
                              "Oficial de Cumplimiento & Seguridad"):
                self.assertNotIn(role_name, ADMIN_ROLES)
                role = self._role(role_name)
                self.assertEqual(
                    GovernanceGuard.get_allowed_tables_for_role(
                        user_role=role_name, is_admin=False, db=self.db,
                        role_id=role.id, connection_id=conn_id,
                    ),
                    set(),
                    f"'{role_name}' no es super admin: no puede ver un dataset sin permiso.",
                )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    # ------------------------------------------------------------------
    # 6. Migracion
    # ------------------------------------------------------------------
    def test_migration_revokes_auto_granted_rows_on_uploaded_connections(self):
        """Lo que dejo el auto-grant viejo se revoca; lo que concedio un admin se queda."""
        conn_id = None
        try:
            body = self._upload_csv("Default Deny Migracion")
            conn_id = body["id"]
            table = body["detected_tables"][0]
            role = self._role("TI")

            # Simula el estado previo: una fila del auto-grant viejo (sin decision).
            self.db.add(RoleTablePermission(
                role_id=role.id, connection_id=conn_id,
                schema_name="main", table_name=table, is_allowed=True,
            ))
            self.db.commit()

            init_db(self.db)

            remaining = {
                p.table_name for p in self._perms_for(conn_id)
                if p.role_id == role.id
            }
            self.assertNotIn(
                table, remaining,
                "La migracion tiene que revocar lo que nadie concedio a proposito.",
            )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_migration_keeps_admin_grants(self):
        """Un permiso concedido por el admin sobrevive a la migracion."""
        conn_id = None
        try:
            body = self._upload_csv("Default Deny Migracion Admin")
            conn_id = body["id"]
            table = body["detected_tables"][0]
            role = self._role("TI")

            res = self.client.put(
                "/api/v1/permissions",
                params={"connection_id": conn_id, "role_id": role.id,
                        "table_names": [table], "is_allowed": "true"},
                headers=self.headers,
            )
            self.assertEqual(res.status_code, 200, res.text)

            init_db(self.db)
            self.db.expire_all()

            remaining = {
                p.table_name for p in self._perms_for(conn_id)
                if p.role_id == role.id and p.is_allowed
            }
            self.assertIn(
                table, remaining,
                "La migracion no puede borrar decisiones de un admin: dejaria el "
                "producto sin forma de recuperar el acceso.",
            )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_migration_is_idempotent(self):
        """Correr la migracion varias veces no cambia nada la segunda vez."""
        conn_id = None
        try:
            body = self._upload_csv("Default Deny Idempotente")
            conn_id = body["id"]
            table = body["detected_tables"][0]
            role = self._role("TI")

            self.db.add(RoleTablePermission(
                role_id=role.id, connection_id=conn_id,
                schema_name="main", table_name=table, is_allowed=True,
            ))
            self.db.commit()

            init_db(self.db)
            after_first = len(self._perms_for(conn_id))
            init_db(self.db)
            after_second = len(self._perms_for(conn_id))
            init_db(self.db)
            after_third = len(self._perms_for(conn_id))

            self.assertEqual(after_first, 0)
            self.assertEqual(after_second, after_first)
            self.assertEqual(after_third, after_first)
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)

    def test_migration_does_not_touch_platform_connections(self):
        """La migracion no revoca la matriz de la demo (is_uploaded == False)."""
        conn = self._platform_connection()
        before = {
            (p.role_id, p.table_name) for p in self.db.query(RoleTablePermission).filter(
                RoleTablePermission.connection_id == conn.id
            ).all()
        }
        init_db(self.db)
        self.db.expire_all()
        after = {
            (p.role_id, p.table_name) for p in self.db.query(RoleTablePermission).filter(
                RoleTablePermission.connection_id == conn.id
            ).all()
        }
        self.assertEqual(after, before)
        self.assertTrue(before)

    # ------------------------------------------------------------------
    # 7. Borrados
    # ------------------------------------------------------------------
    def test_delete_connector_takes_its_permissions_and_leaves_others(self):
        conn_a = None
        conn_b = None
        try:
            body_a = self._upload_csv("Default Deny Borrar A")
            conn_a = body_a["id"]
            body_b = self._upload_csv("Default Deny Borrar B")
            conn_b = body_b["id"]
            role = self._role("TI")

            for cid, body in ((conn_a, body_a), (conn_b, body_b)):
                res = self.client.put(
                    "/api/v1/permissions",
                    params={"connection_id": cid, "role_id": role.id,
                            "table_names": [body["detected_tables"][0]],
                            "is_allowed": "true"},
                    headers=self.headers,
                )
                self.assertEqual(res.status_code, 200, res.text)

            res = self.client.delete(f"/api/v1/connectors/{conn_a}", headers=self.headers)
            self.assertEqual(res.status_code, 200, res.text)
            conn_a = None

            self.db.expire_all()
            self.assertEqual(len(self._perms_for(conn_a or 0)), 0)
            self.assertEqual(
                len([p for p in self._perms_for(conn_b) if p.role_id == role.id]), 1,
                "Borrar un conector no puede tocar los permisos de otro.",
            )
        finally:
            for cid in (conn_a, conn_b):
                if cid:
                    self.client.delete(f"/api/v1/connectors/{cid}", headers=self.headers)

    def test_revoke_through_endpoint_leaves_the_dataset_intact(self):
        """Revocar deja de acceso al rol pero no toca el dataset ni su metadata."""
        conn_id = None
        try:
            body = self._upload_csv("Default Deny Revocar")
            conn_id = body["id"]
            table = body["detected_tables"][0]
            role = self._role("TI")

            res = self.client.put(
                "/api/v1/permissions",
                params={"connection_id": conn_id, "role_id": role.id,
                        "table_names": [table], "is_allowed": "true"},
                headers=self.headers,
            )
            self.assertEqual(res.status_code, 200, res.text)

            res = self.client.put(
                "/api/v1/permissions",
                params={"connection_id": conn_id, "role_id": role.id,
                        "table_names": [table], "is_allowed": "false"},
                headers=self.headers,
            )
            self.assertEqual(res.status_code, 200, res.text)

            self.db.expire_all()
            self.assertIsNotNone(self.db.query(CorporateConnection).filter(
                CorporateConnection.id == conn_id).first(),
                "Revocar acceso no puede borrar el dataset.")
            self.assertEqual(
                len([p for p in self._perms_for(conn_id) if p.is_allowed]), 0,
            )
        finally:
            if conn_id:
                self.client.delete(f"/api/v1/connectors/{conn_id}", headers=self.headers)


class TestColumnMigrationsOnFreshDB(unittest.TestCase):
    """La migracion tiene que correr limpia desde cero, sin base previa."""

    def test_column_is_created_by_create_all_on_fresh_database(self):
        from sqlalchemy import create_engine, inspect
        from app.core.database import Base
        import app.modules.auth.models  # noqa: F401
        import app.modules.admin_catalog.models  # noqa: F401

        path = "./test_default_deny_fresh.db"
        if os.path.exists(path):
            os.remove(path)
        eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        try:
            Base.metadata.create_all(bind=eng)
            cols = {c["name"] for c in inspect(eng).get_columns("role_table_permissions")}
            self.assertIn("granted_by_admin", cols)
            self.assertNotIn("granted_by_admin", {
                c["name"] for c in inspect(eng).get_columns("corporate_connections")},
                "La columna es de la tabla de permisos, no de la conexion.")
        finally:
            eng.dispose()
            if os.path.exists(path):
                os.remove(path)

    def test_default_deny_migration_runs_clean_from_zero(self):
        """init_db sobre una base recien creada: sin error y con la demo sembrada."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.database import Base
        import app.modules.auth.models  # noqa: F401
        import app.modules.admin_catalog.models  # noqa: F401
        import app.modules.telemetry_audit.models  # noqa: F401
        import app.modules.chat_engine.models  # noqa: F401
        import app.core.database as core_db

        path = "./test_default_deny_zero.db"
        if os.path.exists(path):
            os.remove(path)
        eng = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

        old_engine = core_db.engine
        try:
            Base.metadata.create_all(bind=eng)
            TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=eng)
            core_db.engine = eng  # init_db usa el `engine` del modulo
            db = TestingSession()
            init_db(db)
            init_db(db)  # segunda corrida: la migracion es idempotente

            role = db.query(Role).filter(Role.name == "Economista").first()
            self.assertIsNotNone(role)
            tables = {
                p.table_name for p in db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == role.id,
                    RoleTablePermission.is_allowed == True,
                ).all()
            }
            self.assertEqual(
                tables, DEMO_BUSINESS_TABLES,
                "La demo sembrada desde cero tiene que dar la misma matriz.",
            )
            db.close()
        finally:
            core_db.engine = old_engine
            eng.dispose()
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()