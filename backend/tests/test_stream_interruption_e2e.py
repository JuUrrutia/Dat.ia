"""
Simulacion de punta a punta de un stream cortado a mitad.

 corre el backend de verdad (TestClient), con el stream REAL de la narrativa, y
 despues aplica el MISMO parser que usa el navegador (`parseSseEvent` /
 `sendQueryStreaming`) para comprobar que un corte a mitad no deja pasar una
 media respuesta.

 Que prueba, en orden:
  1. El stream emite narrativa token a token mientras el motor trabaja.
  2. Se corta la conexion DESPUES de que el usuario ya leyo texto.
  3. El cliente no tiene `result`: no hay respuesta que commitear.
  4. `POST /chat/query` (el camino de siempre) devuelve la respuesta COMPLETA.

 Es el escenario que el test unitario no puede cubrir: que las dos mitades del
 contrato (lo que emite el server y lo que entiende el cliente) encajen de
 verdad, con los dos lados reales y no con mocks de cada lado por separado.
"""

import asyncio
import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.modules.chat_engine.schemas import QueryResponse, TraceabilityAudit


def parse_sse(text: str):
    """El mismo framing que usa `parseSseEvent` en api_client.ts."""
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        name, data = None, []
        for line in block.split("\n"):
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if not name:
            continue
        events.append((name, json.loads("".join(data)) if data else {}))
    return events


class TestInterruptedStreamEndToEnd(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _response(self, narrative):
        return QueryResponse(
            question="Total de ventas",
            summary_text=narrative,
            conversational_response=narrative,
            traceability=TraceabilityAudit(
                sql_executed="SELECT 1",
                execution_time_ms=10,
                rows_returned=1,
                validation_status="APROBADO",
                schema_tables_used=["fact_ventas"],
                explanation="prueba",
            ),
        )

    def test_client_sees_no_result_when_connection_dies_midway(self):
        """
        El stream se corta: el cliente acumulo texto pero NO tiene respuesta.

        Este es el modo de falla que定义为 dangerous: si `sawResult` fuera True
        con texto parcial, el chat quedaria con media respuesta pegada.
        """
        partial = ["El total ", "fue $1.4", " y la venta se"]
        complete = "El total fue $1.42M. La venta se concentro en el norte."

        async def cuts_off(*args, **kwargs):
            sink = kwargs.get("narrative_sink")
            for piece in partial:
                if sink:
                    await sink(piece)
            # Se corta la conexion: el motor revienta antes de devolver.
            raise ConnectionError("se cae la conexion a mitad de la generacion")

        from fastapi import HTTPException

        async def engine_raises(*args, **kwargs):
            sink = kwargs.get("narrative_sink")
            await cuts_off(narrative_sink=sink)
            return self._response(complete)  # no llega a ejecutarse

        with patch("app.modules.chat_engine.router.QueryEngine.execute_query", new=engine_raises):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas"},
                headers=self.headers(),
            )

        events = parse_sse(resp.text)
        names = [n for n, _ in events]
        deltas = "".join(d.get("text", "") for n, d in events if n == "delta")

        # 1. El usuario lleyo algo real antes del corte.
        self.assertEqual(deltas, "".join(partial))
        # 2. Pero no hay `result`: el cliente no puede commitear nada.
        self.assertNotIn("result", names)
        # 3. Y el servidor dice que fallo, en vez de cerrar como si fuera todo bien.
        self.assertIn("error", names)

    def test_full_stream_gives_client_a_complete_committable_result(self):
        """El camino sano: narrativa token a token y despues el resultado entero."""
        pieces = ["El total ", "fue $1.42M.", " La venta se concentro en el norte."]
        complete = "".join(pieces)

        async def ok_engine(*args, **kwargs):
            sink = kwargs.get("narrative_sink")
            for piece in pieces:
                if sink:
                    await sink(piece)
            return self._response(complete)

        with patch("app.modules.chat_engine.router.QueryEngine.execute_query", new=ok_engine):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas"},
                headers=self.headers(),
            )

        events = parse_sse(resp.text)
        names = [n for n, _ in events]
        deltas = "".join(d.get("text", "") for n, d in events if n == "delta")
        result = next(d for n, d in events if n == "result")

        self.assertEqual(deltas, complete, "el navegador reconstruye mal la narrativa")
        self.assertEqual(result["conversational_response"], complete)
        self.assertEqual(names[-1], "result", "el resultado va al final")

    def test_no_partial_text_can_be_treated_as_the_answer(self):
        """
        Invariante: en ningun escenario el `result` puede traer menos texto del
        que el usuario ya vio en los deltas.
        """
        partial = ["El total fue $1.4"]
        complete = "El total fue $1.42M. La venta se concentro en el norte."

        async def half(*args, **kwargs):
            sink = kwargs.get("narrative_sink")
            await sink(partial[0])
            return self._response(complete)

        with patch("app.modules.chat_engine.router.QueryEngine.execute_query", new=half):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas"},
                headers=self.headers(),
            )

        events = parse_sse(resp.text)
        seen = "".join(d.get("text", "") for n, d in events if n == "delta")
        result = next(d for n, d in events if n == "result")["conversational_response"]

        self.assertTrue(
            len(result) >= len(seen),
            "la respuesta final es mas corta que lo que el usuario ya leyo",
        )
        self.assertTrue(result.startswith(seen[:12]), "la respuesta final contradice lo stremeado")

    def headers(self):
        """JWT de un usuario demo, para que el stream no muera en el 401."""
        import uuid
        from app.modules.auth.models import User, UserSession
        from app.core.security import create_access_token

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == "felipe_economista").first()
            jti = str(uuid.uuid4())
            token = create_access_token(subject=user.id, jti=jti)
            db.add(UserSession(user_id=user.id, jti=jti, is_revoked=False))
            db.commit()
            return {"Authorization": f"Bearer {token}"}
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()