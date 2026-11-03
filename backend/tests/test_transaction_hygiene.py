"""Higiene transaccional: un error tragado no puede envenenar la sesion.

Que un endpoint devuelva 500 un turno y 200 al siguiente, con un error que no
tiene relacion con lo que hizo, es siempre esto: una sentencia fallida ABORTA la
transaccion en PostgreSQL, y todo lo que se ejecute despues en esa misma sesion
responde `InFailedSqlTransaction`. Este proyecto tiene varios handlers
best-effort que se tragan su error a proposito (el audit log, las guardas de
esquema, la memoria de aprendizaje) y seguian usando la sesion de la request.
"""

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from sqlalchemy.orm import Session

from app.core.constants import SYSTEM_STATUS_DEGRADED
from app.core.database import engine, discard_failed_transaction, SessionLocal
from app.modules.catalog.services.null_manager import NullManagerService
from app.modules.chat_engine.engine import QueryEngine
from main import app


def fail_a_query(db):
    """Provoca un error REAL de PostgreSQL dentro de `db` y lo traga.

    Importa que la sentencia se manda de verdad: la transaccion queda abortada en
    el servidor, que es exactamente lo que dispara `InFailedSqlTransaction` en la
    siguiente consulta de la misma sesion.
    """
    try:
        db.execute(text("SELECT * FROM tabla_inexistente_para_probar_rollback"))
    except DBAPIError:
        pass


class TestRollbackHelper(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_swallowed_error_really_does_poison_the_session(self):
        """El mecanismo, medido: sin rollback, la sesion queda MUERTA.

        No es un test del fix: es la demostracion de que el sintoma
        `InFailedSqlTransaction` es real y no una imaginacion del reporte.
        """
        fail_a_query(self.db)
        with self.assertRaises(DBAPIError) as ctx:
            self.db.execute(text("SELECT 1"))
        self.assertIn("InFailedSqlTransaction", str(ctx.exception))
        discard_failed_transaction(self.db)

    def test_session_is_reusable_after_discard(self):
        """Despues del rollback la sesion vuelve a servir consultas."""
        fail_a_query(self.db)
        discard_failed_transaction(self.db)
        self.assertEqual(self.db.execute(text("SELECT 1")).scalar(), 1)

    def test_two_failing_sessions_do_not_contaminate_each_other(self):
        """La request siguiente arranca limpia.

        Medido a proposito: `Session.close()` ya devuelve la conexion al pool con
        rollback, asi que el defecto NUNCA fue cross-request. Este test deja esa
        verdad escrita para que nadie "arregle" `get_db` en su lugar.
        """
        fail_a_query(self.db)
        self.db.close()

        other = SessionLocal()
        try:
            self.assertEqual(other.execute(text("SELECT 1")).scalar(), 1)
        finally:
            other.close()
        self.db = SessionLocal()

    def test_helper_never_raises(self):
        """El helper es best-effort: si el rollback falla, no tumba al que traga."""
        class _Dead:
            def rollback(self):
                raise RuntimeError("conexion muerta")

        self.assertIsNone(discard_failed_transaction(_Dead()))


class _OneShotProbeFailure:
    """Hace fallar el proximo `SELECT 1` de nivel de motor, y solo uno.

    Falla DENTRO del evento de SQLAlchemy mandando la sentencia al servidor, no
    simulando una excepcion: asi la transaccion queda abortada de verdad, que es
    lo que hace que la sesion quede inutilizable.
    """

    def __init__(self):
        self.armed = False
        self.fired = 0

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        if self.armed and statement.strip() == "SELECT 1" and self.fired == 0:
            self.fired += 1
            cursor.execute("SELECT * FROM tabla_inexistente_para_probar_rollback")


class TestEndpointsSurviveTheirOwnSwallowedFailure(unittest.TestCase):
    """Los dos endpoints que tragan un error y despues siguen usando la sesion."""

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        for probe in getattr(self, "_probes", []):
            event.remove(engine, "before_cursor_execute", probe)
        self._probes = []

    def _h(self):
        resp = self.client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
        )
        self.assertEqual(resp.status_code, 200)
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _arm(self):
        probe = _OneShotProbeFailure()
        probe.armed = True
        event.listen(engine, "before_cursor_execute", probe)
        self._probes = getattr(self, "_probes", []) + [probe]
        return probe

    def test_health_survives_its_own_failed_probe(self):
        """`/system/health` sondea `SELECT 1`, traga el error, y consulta después."""
        probe = self._arm()
        resp = self.client.get("/api/v1/system/health", headers=self._h())

        self.assertEqual(probe.fired, 1, "la sonda no llego a dispararse; test incompleto")
        self.assertEqual(
            resp.status_code, 200,
            f"la sonda best-effort tumbo el endpoint: {resp.status_code} {resp.text[:300]}",
        )
        body = resp.json()
        self.assertIn("status", body)
        # El componente que no pudo sondearse se declara degradado: no se inventa.
        self.assertEqual(body["metadata_db"]["status"], SYSTEM_STATUS_DEGRADED)

    def test_anomalies_survives_a_failure_in_its_own_best_effort_scan(self):
        """El escaneo de anomalias falla y se traga; el endpoint sigue sirviendo.

        Antes del fix, la seccion 5 (la consulta siguiente) moria con
        `InFailedSqlTransaction` y el endpoint devolvia 500 sin relacion con nada.
        """
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

        original = DynamicSchemaPruningService.get_authorized_schema_prompt

        def _falla_despues_de_tocar_la_sesion(*args, **kwargs):
            fail_a_query(kwargs.get("db"))
            raise DBAPIError("SELECT 1", {}, Exception("almacen de esquema caido"))

        DynamicSchemaPruningService.get_authorized_schema_prompt = staticmethod(
            _falla_despues_de_tocar_la_sesion
        )
        try:
            resp = self.client.get(
                "/api/v1/system/anomalies?connection_id=1", headers=self._h()
            )
        finally:
            DynamicSchemaPruningService.get_authorized_schema_prompt = original

        self.assertEqual(
            resp.status_code, 200,
            f"el escaneo best-effort tumbo el endpoint: {resp.status_code} {resp.text[:300]}",
        )
        body = resp.json()
        self.assertIsInstance(body["anomalies"], list)
        self.assertEqual(body["count"], len(body["anomalies"]))

    def test_two_consecutive_failing_requests_do_not_contaminate_each_other(self):
        """Request 1 falla por dentro; request 2 tiene que servir normal."""
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

        original = DynamicSchemaPruningService.get_authorized_schema_prompt
        DynamicSchemaPruningService.get_authorized_schema_prompt = staticmethod(
            lambda *a, **k: (_ for _ in ()).throw(
                DBAPIError("SELECT 1", {}, Exception("almacen caido"))
            )
        )
        try:
            first = self.client.get(
                "/api/v1/system/anomalies?connection_id=1", headers=self._h()
            )
        finally:
            DynamicSchemaPruningService.get_authorized_schema_prompt = original

        second = self.client.get("/api/v1/system/anomalies?connection_id=1", headers=self._h())

        self.assertEqual(first.status_code, 200, first.text[:300])
        self.assertEqual(
            second.status_code, 200,
            f"la request 2 heredó la transacción muerta: {second.text[:300]}",
        )


class TestQueryEngineSwallowedFailures(unittest.TestCase):
    """Los dos `except` de `QueryEngine.execute_query` que se tragan su error.

    Este es el ultimo sitio del mismo defecto: `engine.py` resolvia la conexion
    con `except Exception: pass`, y tragaba tambien un `db.commit()` fallido de
    la remediacion de nulos. Los dos dejaron la sesion de la request envenenada,
    asi que la consulta siguiente moria con un error sin relacion con nada.
    """

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def _run(self, **kwargs):
        import asyncio

        kwargs.setdefault("question", "SELECT * FROM test_sales")
        return asyncio.run(QueryEngine.execute_query(
            user_role="Administrador",
            is_admin=True,
            db=self.db,
            connection_id=1,
            **kwargs,
        ))

    def test_failed_connection_lookup_leaves_the_session_usable(self):
        """La resolucion de conexion falla y se traga: la request sigue igual.

        Antes del fix, `engine.py` hacia `except Exception: pass` ahi. La consulta
        fallida dejaba la transaccion abortada y TODO lo que se ejecutara despues
        en esa request respondia `InFailedSqlTransaction`.
        """
        original = Session.query
        original_tables = QueryEngine.get_allowed_tables_for_role.__func__
        session_under_test = self.db
        fired = []
        passed_rbac = []

        def _consulta_que_falla(self, *args, **kwargs):
            # Falla SOLO la PRIMERA consulta de CorporateConnection que viene
            # DESPUES de `get_allowed_tables_for_role`, que es exactamente la
            # primera linea del `try` de `engine.py` (la resolucion de conexion).
            #
            # Las consultas anteriores no son el sujeto del test: salen de
            # `get_allowed_tables_for_role`, que corre antes y tiene su propio
            # manejo. Y falla una sola vez: si cada consulta envenenara la
            # sesion, la ultima la dejaria muerta igual con el fix puesto y el
            # test probaria otra cosa.
            #
            # Importa que la sentencia FALLE DE VERDAD contra el servidor: si la
            # excepcion se levanta en Python sin mandar nada, la transaccion no
            # se aborta y el test probaria un defecto que no existe (medido: asi
            # pasaba y el test daba verde con el fix revertido).
            is_conn_lookup = any(
                getattr(entity, "__name__", "") == "CorporateConnection" for entity in args
            )
            if passed_rbac and is_conn_lookup and not fired:
                fired.append(True)
                fail_a_query(session_under_test)
                raise DBAPIError("SELECT", {}, Exception("almacen de conexiones caido"))
            return original(self, *args, **kwargs)

        def _marca_rbac(cls, *a, **k):
            result = original_tables(cls, *a, **k)
            passed_rbac.append(True)
            return result

        Session.query = _consulta_que_falla
        QueryEngine.get_allowed_tables_for_role = classmethod(_marca_rbac)
        try:
            response = self._run()
        finally:
            Session.query = original
            QueryEngine.get_allowed_tables_for_role = classmethod(original_tables)

        self.assertTrue(fired, "la consulta de conexion no llego a fallar; test incompleto")
        self.assertIsNotNone(response, "una excepcion tragada no puede romper la request")
        # Lo que importa: la sesion quedo utilizable para lo que siga.
        self.assertEqual(self.db.execute(text("SELECT 1")).scalar(), 1)

    def test_failed_remediation_commit_leaves_the_session_usable(self):
        """El `db.commit()` de la remediacion falla y se traga: sesion usable.

        Ojo con el estado: un commit que revienta en el flush NO deja la sesion
        como una query fallida. Medido contra PostgreSQL, `db.commit()` abortado
        por constraint deja `PendingRollbackError` ("rolled back due to a
        previous exception during flush"), mientras que una sentencia fallida
        deja `InFailedSqlTransaction`. Los dos se limpian con el mismo rollback,
        asi que el helper serves para los dos casos.
        """
        original = NullManagerService.apply_null_policy

        def _falla_el_commit(conn_record, remediation_action, db):
            # Se hace el trabajo y se envenena la sesion en el commit, que es el
            # caso que el `except` de `engine.py` se tragaba.
            db.execute(text("SELECT * FROM tabla_inexistente_para_probar_rollback"))
            raise DBAPIError("COMMIT", {}, Exception("no se pudo confirmar"))

        NullManagerService.apply_null_policy = staticmethod(_falla_el_commit)
        try:
            # `remediation_action` no es un parametro: `execute_query` lo deduce
            # del texto de la pregunta (NullHandler.detect_remediation_intent).
            response = self._run(
                question="Tratar nulos en test_sales (eliminar registros con nulos) "
                         "para la consulta: SELECT * FROM test_sales",
                conversation_history=[
                    {"question": "SELECT * FROM test_sales", "sql": "SELECT * FROM test_sales"}
                ],
            )
        finally:
            NullManagerService.apply_null_policy = original

        self.assertIsNotNone(response)
        # Y no se Announces remediacion aplicada sobre una base sin remediar.
        self.assertNotIn(
            "Tratamiento de nulos",
            response.conversational_response or "",
            "un commit fallido no puede anunciarse como remediacion aplicada",
        )
        self.assertEqual(self.db.execute(text("SELECT 1")).scalar(), 1)


class TestBestEffortAuditIsPreserved(unittest.TestCase):
    """El audit log que falla NO tumba la request principal, y NO la envenena."""

    def setUp(self):
        self.client = TestClient(app)

    def test_failing_audit_log_returns_none_and_leaves_session_usable(self):
        """El `except` de auditoria se traga el error: eso se preserva."""
        from app.modules.chat_engine.router import _persist_audit_log
        from app.modules.telemetry_audit.models import AuditLog

        db = SessionLocal()
        original_init = AuditLog.__init__

        def _init_que_falla(self, **kwargs):
            original_init(self, **kwargs)
            fail_a_query(db)  # aborta la transaccion de verdad
            raise DBAPIError("INSERT", {}, Exception("audit log no escribible"))

        try:
            AuditLog.__init__ = _init_que_falla
            try:
                audit_id = _persist_audit_log(
                    db=db,
                    user_id=None,
                    username="admin",
                    user_role=None,
                    question_prompt="q",
                    sql_generated=None,
                    validation_status=None,
                    target_database="demo",
                )
            finally:
                AuditLog.__init__ = original_init

            self.assertIsNone(audit_id, "un audit log fallido no devuelve id")
            # Y sobre todo: la request sigue viva.
            self.assertEqual(db.execute(text("SELECT 1")).scalar(), 1)
        finally:
            db.close()

    def test_persisted_audit_log_is_still_recorded(self):
        """El camino feliz de auditoria no se rompió con el arreglo."""
        from app.modules.chat_engine.router import _persist_audit_log
        from app.modules.telemetry_audit.models import AuditLog

        db = SessionLocal()
        try:
            audit_id = _persist_audit_log(
                db=db,
                user_id=None,
                username="tx-hygiene-probe",
                user_role=None,
                question_prompt="q",
                sql_generated="SELECT 1",
                validation_status=None,
                target_database="demo",
            )
            self.assertIsInstance(audit_id, int)
            row = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
            self.assertIsNotNone(row)
            db.delete(row)
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()