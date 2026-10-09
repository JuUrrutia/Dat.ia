"""Higiene transaccional: un error tragado no puede envenenar la sesion.

Que un endpoint devuelva 500 un turno y 200 al siguiente, con un error que no
tiene relacion con lo que hizo, es siempre esto: una sentencia fallida ABORTA la
transaccion en PostgreSQL, y todo lo que se ejecute despues en esa misma sesion
responde `InFailedSqlTransaction`. Este proyecto tiene varios handlers
best-effort que se tragan su error a proposito (el audit log, las guardas de
esquema, la memoria de aprendizaje) y seguian usando la sesion de la request.

Que la asercion de varios de estos tests sea justamente "la consulta que sigue",
los hace depender del efecto del motor: bajo el fallback SQLite la sesion nunca
se envenena y darian verde con el arreglo revertido. Llevan `@requires_postgres`
por eso. Los que quedan sin marcador no dependen del motor y corren en los dos:
el helper contra una sesion falsa, los dos caminos del audit log (que devuelve
`None` en vez de propagar, y el feliz que escribe y borra la fila) y
`/system/health`, que sin PostgreSQL sigue muerdiendo porque comprueba que la
sonda llego a dispararse y que el componente se declara degradado.

Y al reves: un test que pasa en vacio es peor que uno que no existe. Por eso los
que barren una sesion envenenada llevan una guarda que falla en voz alta si la
inyeccion no llego a dispararse (`assertTrue(fired, ...)`), y ninguno se apoya en
un `connection_id` fijo de la base: el endpoint solo entra en su bloque
best-effort si la conexion que se le pide responde.
"""

import os
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from sqlalchemy.orm import Session

from app.core.constants import SYSTEM_STATUS_DEGRADED
from app.core.database import engine, discard_failed_transaction, SessionLocal
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType
from app.modules.catalog.services.null_manager import NullManagerService
from app.modules.chat_engine.engine import QueryEngine
from main import app


def _es_postgres():
    """La sesion envenenada es un hecho de PostgreSQL, no de SQLAlchemy.

    En SQLite una sentencia fallida NO aborta la transaccion: la siguiente consulta
    de la misma sesion funciona. Los tests cuya asercion es justamente esa consulta
    posterior no pueden fallar ahi, asi que llevan `@requires_postgres`: sin
    PostgreSQL darian verde en vacio (y ademas fallarian por el motivo equivocado,
    que es como se veia en CI: la suite sin servidor de base de datos corria contra
    el fallback SQLite). Los que no dependen del efecto del motor se quedan sin
    marcador, porque hay que seguir comprobandolos en los dos motores.
    """
    return engine.dialect.name == "postgresql"


requires_postgres = unittest.skipUnless(
    _es_postgres(),
    "el sintoma InFailedSqlTransaction es propio de PostgreSQL y el fallback "
    "SQLite no lo reproduce",
)


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

    @requires_postgres
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

    @requires_postgres
    def test_session_is_reusable_after_discard(self):
        """Despues del rollback la sesion vuelve a servir consultas."""
        # La asercion ES la consulta posterior al fallo, y bajo SQLite la sesion
        # nunca se envenena: daria verde con el arreglo revertido (medido).
        fail_a_query(self.db)
        discard_failed_transaction(self.db)
        self.assertEqual(self.db.execute(text("SELECT 1")).scalar(), 1)

    @requires_postgres
    def test_two_failing_sessions_do_not_contaminate_each_other(self):
        """La request siguiente arranca limpia.

        Medido a proposito: `Session.close()` ya devuelve la conexion al pool con
        rollback, asi que el defecto NUNCA fue cross-request. Este test deja esa
        verdad escrita para que nadie "arregle" `get_db` en su lugar.
        """
        # El `SELECT 1` de la sesion nueva no puede fallar bajo NINGUN motor: el
        # aislamiento lo da `Session.close()`, no el arreglo (medido: verde con el
        # arreglo en no-op). Marcado para que el fallback SQLite no lo reporte como
        # verde en vacuo; lo que deja es la verdad del docstring, no una prueba.
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

    CONN_NAME = "tx-hygiene-best-effort"

    def setUp(self):
        self.client = TestClient(app)
        self._tmpdir = tempfile.TemporaryDirectory()
        self._setup_db = SessionLocal()

    def tearDown(self):
        for probe in getattr(self, "_probes", []):
            event.remove(engine, "before_cursor_execute", probe)
        self._probes = []
        # `name` es UNIQUE y una corrida interrumpida puede no haber borrado la fila:
        # sin esta limpieza el siguiente setUp revienta con UniqueViolation y por un
        # motivo que no es el de este archivo.
        self._setup_db.query(CorporateConnection).filter(
            CorporateConnection.name == self.CONN_NAME
        ).delete(synchronize_session=False)
        self._setup_db.commit()
        self._setup_db.close()
        self._tmpdir.cleanup()

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

    def _connexion_alcanzable(self):
        """Crea un SQLite temporal y devuelve el id de la conexion que lo apunta.

        `/system/anomalies` solo entra en su bloque best-effort si `target_conn`
        responde (`if target_conn and is_reachable`), y la fila la elige el
        `connection_id` de la query. Medido: apuntando a la 1 --que en esta base la
        reclama un resto de otra suite, `is_active=false` y fichero temporal ya
        borrado-- el escaneo no se ejecutaba y los tests de abajo pasaban sin
        inyectar nada. Por eso el test crea su propia conexion en vez de confiar en
        un id fijo.

        `is_active=False` a proposito: la puerta mira la fila que pedio el
        `connection_id`, no las activas, y asi el test no mete una conexion
        alcanzable en el panel de salud del resto de la suite.
        """
        path = os.path.join(self._tmpdir.name, "mejor_esfuerzo.sqlite")
        sqlite3.connect(path).close()  # el fichero tiene que existir: el health lo abre
        row = CorporateConnection(
            name=self.CONN_NAME,
            db_type=DatabaseType.SQLITE,
            host=path,
            port=0,
            database_name=os.path.basename(path),
            username="admin",
            encrypted_password="",
            is_active=False,
            is_uploaded=True,
        )
        self._setup_db.add(row)
        self._setup_db.commit()
        return row.id

    def test_health_survives_its_own_failed_probe(self):
        """`/system/health` sondea `SELECT 1`, traga el error, y consulta después."""
        # Se queda SIN marcador a proposito. Sin PostgreSQL no prueba lo que su
        # nombre dice (que el endpoint sobreviva a una sesion envenenada): la sesion
        # no se envenena y el arreglo da igual. Lo que sigue muerdiendo bajo SQLite
        # es que la sonda llego a dispararse y que el componente se declara
        # degradado en vez de inventarse operativo: las dos aserciones caen si el
        # `except` best-effort deja de tragarse el error.
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

    @requires_postgres
    def test_anomalies_survives_a_failure_in_its_own_best_effort_scan(self):
        """El escaneo de anomalias falla y se traga; el endpoint sigue sirviendo.

        Antes del fix, la seccion 5 (la consulta siguiente) moria con
        `InFailedSqlTransaction` y el endpoint devolvia 500 sin relacion con nada.
        """
        # Marcado por el motor: lo que se prueba es que una sesion envenenada no
        # tumba lo que se ejecuta despues, y eso solo aborta en PostgreSQL.
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

        connection_id = self._connexion_alcanzable()
        original = DynamicSchemaPruningService.get_authorized_schema_prompt
        fired = []

        def _falla_despues_de_tocar_la_sesion(*args, **kwargs):
            # La sentencia va de verdad al servidor: es lo que aborta la
            # transaccion y hace que la sesion quede inutilizable.
            fail_a_query(kwargs.get("db"))
            fired.append(True)
            raise DBAPIError("SELECT 1", {}, Exception("almacen de esquema caido"))

        DynamicSchemaPruningService.get_authorized_schema_prompt = staticmethod(
            _falla_despues_de_tocar_la_sesion
        )
        try:
            resp = self.client.get(
                f"/api/v1/system/anomalies?connection_id={connection_id}", headers=self._h()
            )
        finally:
            DynamicSchemaPruningService.get_authorized_schema_prompt = original

        # Sin esta guarda el test vuelve a pasar en vacio: si el endpoint no entra en
        # su bloque best-effort no hay error que tragar y lo de abajo son las
        # aserciones de un endpoint sano.
        self.assertTrue(fired, "el escaneo best-effort no llego a ejecutarse; test incompleto")
        self.assertEqual(
            resp.status_code, 200,
            f"el escaneo best-effort tumbo el endpoint: {resp.status_code} {resp.text[:300]}",
        )
        body = resp.json()
        self.assertIsInstance(body["anomalies"], list)
        self.assertEqual(body["count"], len(body["anomalies"]))

    @requires_postgres
    def test_two_consecutive_failing_requests_do_not_contaminate_each_other(self):
        """Request 1 falla por dentro; request 2 tiene que servir normal.

        El defecto nunca fue cross-request, asi que esto no prueba el arreglo: deja
        escrita la garantia de que arreglarlo por `get_db` en vez de por el helper
        no hacia falta. Para que la request 1 envenene DE VERDAD, el parche manda una
        sentencia que falla contra el servidor en vez de levantar la excepcion en
        Python (medido: asi era antes y la sesion nunca se envenenaba).
        """
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

        connection_id = self._connexion_alcanzable()
        original = DynamicSchemaPruningService.get_authorized_schema_prompt
        fired = []

        def _falla_despues_de_tocar_la_sesion(*args, **kwargs):
            fail_a_query(kwargs.get("db"))
            fired.append(True)
            raise DBAPIError("SELECT 1", {}, Exception("almacen caido"))

        DynamicSchemaPruningService.get_authorized_schema_prompt = staticmethod(
            _falla_despues_de_tocar_la_sesion
        )
        try:
            first = self.client.get(
                f"/api/v1/system/anomalies?connection_id={connection_id}", headers=self._h()
            )
        finally:
            DynamicSchemaPruningService.get_authorized_schema_prompt = original

        second = self.client.get(
            f"/api/v1/system/anomalies?connection_id={connection_id}", headers=self._h()
        )

        self.assertTrue(fired, "la request 1 no llego a fallar por dentro; test incompleto")
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

    @requires_postgres
    def test_failed_connection_lookup_leaves_the_session_usable(self):
        """La resolucion de conexion falla y se traga: la request sigue igual.

        Antes del fix, `engine.py` hacia `except Exception: pass` ahi. La consulta
        fallida dejaba la transaccion abortada y TODO lo que se ejecutara despues
        en esa request respondia `InFailedSqlTransaction`.
        """
        # El `SELECT 1` final es la asercion que no puede fallar bajo SQLite: la
        # sesion sigue sirviendo consultas aunque el arreglo este revertido (medido).
        # Sin PostgreSQL solo muerden `fired` y `response is not None`, que ya no son
        # el arreglo.
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

    @requires_postgres
    def test_failed_remediation_commit_leaves_the_session_usable(self):
        """El `db.commit()` de la remediacion falla y se traga: sesion usable.

        Ojo con el estado: un commit que revienta en el flush NO deja la sesion
        como una query fallida. Medido contra PostgreSQL, `db.commit()` abortado
        por constraint deja `PendingRollbackError` ("rolled back due to a
        previous exception during flush"), mientras que una sentencia fallida
        deja `InFailedSqlTransaction`. Los dos se limpian con el mismo rollback,
        asi que el helper serves para los dos casos.
        """
        # El `SELECT 1` final es la asercion que no puede fallar bajo SQLite
        # (medido: verde con el arreglo revertido). Sin PostgreSQL sigue muerdiendo
        # el `assertNotIn` de mas abajo --un commit tragado no puede anunciarse como
        # remediacion aplicada--; el `SELECT 1` es lo que prueba el arreglo.
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
    """El audit log que falla NO tumba la request principal."""

    def setUp(self):
        self.client = TestClient(app)

    def test_failing_audit_log_returns_none_without_raising(self):
        """El audit log se traga su error: eso se preserva.

        Se queda sin marcador porque ya no afirma nada sobre la transaccion. Lo que
        demuestra es el contrato best-effort --un audit log no escribible devuelve
        `None` y no propaga-- y eso se cumple igual en los dos motores. Medido: lo
        que dejaba usable la sesion era el `db.rollback()` que `_persist_audit_log`
        ya tiene en su propio `except`, no `discard_failed_transaction`, asi que la
        asercion de "la sesion sigue viva" era verde en vacio bajo SQLite y no
        probaba el arreglo de este archivo. Por eso aqui no se manda ninguna
        sentencia que falle: sin asercion sobre la sesion, envenenarla seria teatro.
        """
        from app.modules.chat_engine.router import _persist_audit_log
        from app.modules.telemetry_audit.models import AuditLog

        db = SessionLocal()
        original_init = AuditLog.__init__

        def _init_que_falla(self, **kwargs):
            original_init(self, **kwargs)
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