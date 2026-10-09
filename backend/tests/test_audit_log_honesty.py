"""
Honestidad del `AuditLog.validation_status` en la cadena completa.

El bug era de tres capas y las tres tenian que caer:

1. `chat_engine/router.py` persistia `"APROBADO"` cuando la respuesta no traia
   trazabilidad. Eso es afirmar una validacion que nadie hizo.
2. `AuditLog.validation_status` era `NOT NULL`, o sea que el router no tenia
   opcion honesta: el modelo lo obligaba a mentir.
3. El export de compliance lee la columna de la BD, asi que el documento que
   abre el admin decia "Estado AST: APROBADO".

Los exporters (`data_compiler.py`, `pdf_exporter.py`) ya sabian pintar "Sin
registro de validacion" cuando el campo viene vacio, pero con el `else "APROBADO"`
ese camino era inalcanzable. Estos tests fijan las dos puntas: lo que se persiste
y lo que sale en el documento.

Nota sobre como se llama al endpoint: los tests invocan la corrutina del router
directamente, no por HTTP. `QueryResponse.traceability` es obligatoria en el
schema, asi que una respuesta con `traceability: None` no puede atravesar la
validacion de `response_model` de FastAPI — y la rama que estamos probando es
justamente la que el router exercise cuando eso ocurre. Pasando por el cliente
HTTP estaria probando otra cosa.
"""
import asyncio
import json
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal, engine
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.modules.telemetry_audit.models import AuditLog
from app.core.security import create_access_token
from app.modules.chat_engine import router as chat_router
from app.modules.chat_engine.schemas import (
    KPICard, QueryRequest, QueryResponse, TraceabilityAudit, PresentationHints,
)

QUESTION = "pregunta de prueba sin trazabilidad"


def _response(status: str) -> QueryResponse:
    return QueryResponse(
        question=QUESTION,
        summary_text="Resultado de prueba.",
        response_type="data_analysis",
        data_columns=["id"],
        data_rows=[{"id": 1}],
        kpis=[KPICard(title="Ventas", value="1")],
        presentation_hints=PresentationHints(),
        traceability=TraceabilityAudit(
            sql_executed="SELECT 1",
            execution_time_ms=7,
            rows_returned=1,
            validation_status=status,
            schema_tables_used=["fact_ventas"],
            explanation="ok",
        ),
    )


class _NoTraceability:
    """Respuesta del engine sin bloque de trazabilidad.

    El router decide con `if response.traceability`, asi que para ejercitar la rama
    hace falta un objeto cuyo `.traceability` sea realmente None.
    """

    traceability = None
    data_rows = []
    response_type = "advisory"
    summary_text = "No hay datos para mostrar."
    audit_log_id = None

    def model_dump_json(self):
        return json.dumps({"question": QUESTION, "traceability": None})


class TestAuditValidationStatusHonesty(unittest.TestCase):

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
        self.db.add(UserSession(user_id=self.user.id, jti=self.jti, is_revoked=False))
        self.db.commit()
        token = create_access_token(subject=self.user.id, jti=self.jti)
        self.headers = {"Authorization": f"Bearer {token}"}
        self.created = []

    def tearDown(self):
        for audit_id in self.created:
            self.db.query(AuditLog).filter(AuditLog.id == audit_id).delete()
        self.db.query(UserSession).filter(UserSession.jti == self.jti).delete()
        self.db.commit()
        self.db.close()

    def _run_query(self, engine_result):
        """Ejecuta el endpoint con el engine simulado y devuelve el AuditLog creado."""
        async def _fake_execute_query(**kwargs):
            if isinstance(engine_result, Exception):
                raise engine_result
            return engine_result

        with patch.object(chat_router.QueryEngine, "execute_query", _fake_execute_query):
            asyncio.run(chat_router.process_chat_query(
                QueryRequest(question=QUESTION, connection_id=1),
                current_user=self.user,
                db=self.db,
            ))

        self.db.expire_all()
        log = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        self.created.append(log.id)
        return log

    def test_no_traceability_does_not_persist_approved(self):
        """Sin trazabilidad el estado queda sin valor: no se inventa una validacion."""
        log = self._run_query(_NoTraceability())
        self.assertIsNone(
            log.validation_status,
            'Una consulta sin trazabilidad se esta persistiendo como "%s"' % log.validation_status,
        )

    def test_no_traceability_export_does_not_print_approved(self):
        """El CSV que abre el admin no puede afirmar APROBADO sobre un log sin estado."""
        log = self._run_query(_NoTraceability())
        self.assertIsNone(log.validation_status)

        export = self.client.get("/api/v1/audit/export", headers=self.headers)
        self.assertEqual(export.status_code, 200, export.text[:300])
        rows = [
            line for line in export.content.decode("utf-8-sig").splitlines()
            if QUESTION in line
        ]
        self.assertTrue(rows, "el log recien creado no aparece en el CSV de compliance")
        self.assertNotIn("APROBADO", rows[-1])
        self.assertIn(",,", rows[-1])  # celda de estado vacia, no afirmada

    def test_audit_listing_survives_a_log_without_status(self):
        """El listado paginado no puede romper con un NULL en la columna."""
        self._run_query(_NoTraceability())
        listing = self.client.get("/api/v1/audit", headers=self.headers)
        self.assertEqual(listing.status_code, 200, listing.text[:300])

    def test_rejected_rbac_is_preserved(self):
        """Un RECHAZADO real no se pisa ni se transforma."""
        log = self._run_query(_response("RECHAZADO_RBAC"))
        self.assertEqual(log.validation_status, "RECHAZADO_RBAC")

    def test_execution_error_is_preserved(self):
        log = self._run_query(_response("ERROR_EJECUCION"))
        self.assertEqual(log.validation_status, "ERROR_EJECUCION")

    def test_real_approved_is_still_approved(self):
        """El camino feliz no se rompio."""
        log = self._run_query(_response("APROBADO"))
        self.assertEqual(log.validation_status, "APROBADO")

    def test_failed_query_still_records_error_status(self):
        """El except del router sigue dejando rastro real del fallo."""
        with self.assertRaises(RuntimeError):
            self._run_query(RuntimeError("motor caido"))
        self.db.expire_all()
        log = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        self.created.append(log.id)
        self.assertEqual(log.validation_status, "ERROR_EJECUCION")


class TestValidationStatusColumnIsNullable(unittest.TestCase):
    """La columna tiene que admitir el valor honesto, o el router no puede mentir."""

    def test_model_allows_null_and_db_column_matches(self):
        from sqlalchemy import inspect

        self.assertTrue(
            AuditLog.__table__.c.validation_status.nullable,
            "El modelo sigue declarando NOT NULL: el router no tiene opcion honesta.",
        )
        cols = {c["name"]: c for c in inspect(engine).get_columns("audit_logs")}
        self.assertTrue(
            cols["validation_status"]["nullable"],
            "La migracion no abrio la columna en la base.",
        )

    def test_null_survives_a_round_trip_to_the_database(self):
        init_db(SessionLocal())
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "admin").first()
            entry = AuditLog(
                user_id=user.id,
                username=user.username,
                question_prompt="sin trazabilidad",
                validation_status=None,
            )
            db.add(entry)
            db.commit()
            entry_id = entry.id
            db.expire_all()
            reloaded = db.query(AuditLog).filter(AuditLog.id == entry_id).first()
            self.assertIsNone(reloaded.validation_status)
            db.query(AuditLog).filter(AuditLog.id == entry_id).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
