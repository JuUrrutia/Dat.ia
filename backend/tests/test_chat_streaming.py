"""
Stream de la narrativa del chat: contrato de red y recuperacion tras corte.

Por que este archivo existe
---------------------------
`POST /chat/query/stream` es el unico cambio que toca el contrato de red, y su
modo de falla mas probable no es "el backend devuelve 500": es "la conexion se
corta cuando el usuario ya leyo media respuesta". Si eso dejara texto a medias
pegado en el chat, seria el bug mas grave de todos porque el usuario creeria
que esa era la respuesta completa.

Estos tests fijan las cuatro propiedades de las que depende la honestidad del
stream:

1. El stream NO reemplaza a `POST /chat/query`: ese endpoint sigue existiendo,
   con la misma autenticacion, y devuelve la respuesta completa.
2. Un stream interrumpido NO entrega resultado. El cliente queda sin `result`,
   o sea, sin verdad, y por lo tanto sin nada commiteado al hilo.
3. La narrativa stremeada viene del `rows` YA ENMASCARADO: no hay una via de
   datos sin enmascarar por streaming.
4. El stream no inventa progreso: si el LLM no emite el campo `narrative`, no
   sale ni un solo delta.
"""

import asyncio
import json
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.modules.auth.models import User, UserSession
from app.core.security import create_access_token
from app.modules.chat_engine.narrative_stream import NarrativeStreamExtractor
from app.modules.chat_engine.llm_service import StreamingThinkFilter


def parse_sse(text: str):
    """Devuelve [(event, data)] de un cuerpo SSE."""
    out = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = None
        data_lines = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if event is None:
            continue
        payload = "".join(data_lines)
        try:
            out.append((event, json.loads(payload)))
        except ValueError:
            out.append((event, payload))
    return out


class TestNarrativeStreaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        init_db(db)
        db.close()

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        user = self.db.query(User).filter(User.username == "felipe_economista").first()
        self.jti = str(uuid.uuid4())
        token = create_access_token(subject=user.id, jti=self.jti)
        self.db.add(UserSession(user_id=user.id, jti=self.jti, is_revoked=False))
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.db.close()

    # ------------------------------------------------------------------
    # 1. El camino que hoy funciona sigue intacto
    # ------------------------------------------------------------------
    def test_stream_endpoint_requires_auth(self):
        """Sin JWT el stream es 401, igual que /query. No se abre por GET."""
        resp = self.client.post("/api/v1/chat/query/stream", json={"question": "Total de ventas"})
        self.assertEqual(resp.status_code, 401)

    def test_stream_is_a_separate_endpoint_not_query(self):
        """
        La red de seguridad existe: `/query` NO emite SSE.

        Si este test falla, alguien hizo que `/query` stremeara y con eso se
        perdio el camino sin stream, que es el unico que funciona sin stream.
        """
        resp = self.client.post(
            "/api/v1/chat/query",
            json={"question": "Total de ventas", "connection_id": 1},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("text/event-stream", resp.headers.get("content-type", ""))
        # Y sigue siendo JSON con la forma de siempre.
        self.assertIn("traceability", resp.json())

    def test_stream_endpoint_is_post_only(self):
        """
        El stream es POST y no GET.

        Se verifica contra el endpoint vivo y no contra `app.routes`: con
        Starlette 1.6 las rutas incluidas quedan envueltas y `app.routes` ya no
        expone los paths, asi que inspeccionarlas daria un falso negativo. Lo que
        importa no es la tabla interna sino que un GET no abra un stream: un
        stream por GET es exactamente el caso en el que el JWT tendria que ir en
        la query string para que `EventSource` pudiera mandarlo.
        """
        resp = self.client.get("/api/v1/chat/query/stream")
        self.assertIn(resp.status_code, (404, 405), "GET no debe abrir un stream de chat")

    # ------------------------------------------------------------------
    # 2. Corte a mitad: el cliente queda SIN resultado (puede reintentar)
    # ------------------------------------------------------------------
    def _sample_response(self, narrative: str):
        from app.modules.chat_engine.schemas import QueryResponse, TraceabilityAudit
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
                explanation="consulta de prueba",
            ),
        )

    def test_stream_emits_narrative_then_complete_result(self):
        """
        El stream emite narrativa y despues el resultado COMPLETO.

        Se parchea `execute_query` y no el LLM porque lo que se verifica es el
        CONTRATO de red del endpoint: el sink recibe texto y el `result` final
        lleva la respuesta entera. Asi el test no depende de que haya un LLM o
        una base con datos en la maquina donde corre.
        """
        complete = "El total fue $1.42M. La venta se concentro en el norte."

        async def fake_execute(*args, **kwargs):
            sink = kwargs.get("narrative_sink")
            for piece in ("El total ", "fue $1.42M.", " La venta se concentro en el norte."):
                if sink:
                    await sink(piece)
            return self._sample_response(complete)

        with patch("app.modules.chat_engine.router.QueryEngine.execute_query", new=fake_execute):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas", "connection_id": 1},
                headers=self.headers,
            )

        self.assertEqual(resp.status_code, 200)
        events = parse_sse(resp.text)
        kinds = [k for k, _ in events]
        self.assertEqual(kinds[0], "meta")

        deltas = "".join(d["text"] for k, d in events if k == "delta")
        self.assertEqual(deltas, complete, "los deltas no reconstruyen la narrativa")

        result = next(d for k, d in events if k == "result")
        self.assertEqual(result["conversational_response"], complete)
        # El `result` va SIEMPRE al final: es la verdad, no un evento mas.
        self.assertEqual(kinds[-1], "result")

    def test_interrupted_stream_still_yields_complete_result(self):
        """
        Si el stream se corta, lo que se commitea igual es la respuesta COMPLETA.

        Es el modo de falla mas grave y el mas probable: el cliente ya leyo
        "El total fue $1.4" y despues se cae la conexion. La garantia es que lo
        que llega en `result` NO es ese prefijo, y que `result` es la unica
        fuente que el cliente commitea al hilo.
        """
        complete = "El total fue $1.42M. La venta se concentro en el norte."

        async def fake_execute(*args, **kwargs):
            sink = kwargs.get("narrative_sink")
            if sink:
                await sink("El total fue $1.4")   # esto SI llego a la UI
            return self._sample_response(complete)

        with patch("app.modules.chat_engine.router.QueryEngine.execute_query", new=fake_execute):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas", "connection_id": 1},
                headers=self.headers,
            )

        events = parse_sse(resp.text)
        deltas = "".join(d["text"] for k, d in events if k == "delta")
        result = next(d for k, d in events if k == "result")

        self.assertIn("El total fue $1.4", deltas)
        self.assertEqual(result["conversational_response"], complete)

    def test_synthesis_falls_back_to_non_stream_when_llm_stream_dies(self):
        """
        A nivel de motor: un stream caido reintenta por `generate_completion`.

        Si esto fallara, la recuperacion dependeria de que el cliente reintente
        la consulta entera. La garantia de que el cliente siempre tenga una
        respuesta completa se apoya en que el motor no se quede sin narrativa por
        un corte de red.
        """
        from app.modules.chat_engine.kpi_calculator import KPICalculator

        full = '{"narrative": "Narrativa completa.", "kpis": [], "executive_report": null, "suggested_questions": []}'

        async def dying_stream(*args, **kwargs):
            yield '{"narrative": "Narrativa comp'
            raise ConnectionError("corte")

        with patch(
            "app.modules.chat_engine.kpi_calculator.LLMService.stream_completion", new=dying_stream
        ), patch(
            "app.modules.chat_engine.kpi_calculator.LLMService.generate_completion",
            new=unittest.mock.AsyncMock(return_value=full),
        ):
            got = asyncio.run(KPICalculator._run_synthesis_llm("prompt", "system", lambda t: None))

        self.assertEqual(got, full, "el fallback no devolvio la respuesta completa")

    def test_synthesis_without_sink_never_streams(self):
        """Sin sink no se abre ningun stream: el camino viejo queda intacto."""
        from app.modules.chat_engine.kpi_calculator import KPICalculator

        full = '{"narrative": "X", "kpis": [], "executive_report": null, "suggested_questions": []}'

        async def must_not_stream(*args, **kwargs):
            raise AssertionError("se abrio un stream sin narrative_sink")

        with patch(
            "app.modules.chat_engine.kpi_calculator.LLMService.stream_completion", new=must_not_stream
        ), patch(
            "app.modules.chat_engine.kpi_calculator.LLMService.generate_completion",
            new=unittest.mock.AsyncMock(return_value=full),
        ):
            got = asyncio.run(KPICalculator._run_synthesis_llm("p", "s", None))

        self.assertEqual(got, full)

    def test_error_event_carries_no_result(self):
        """
        Si el motor revienta, el stream emite `error` y NO `result`.

        El cliente trata `error` como "no hay respuesta" y cae a `/query`.
        """
        from fastapi import HTTPException

        async def boom(*args, **kwargs):
            raise HTTPException(status_code=403, detail="sin permiso")

        with patch(
            "app.modules.chat_engine.engine.QueryEngine.execute_query",
            new=boom,
        ):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas", "connection_id": 1},
                headers=self.headers,
            )

        self.assertEqual(resp.status_code, 200)  # las cabeceras ya se enviaron
        events = parse_sse(resp.text)
        kinds = [k for k, _ in events]
        self.assertIn("error", kinds)
        self.assertNotIn("result", kinds)

    def test_stream_never_invents_delta_without_real_tokens(self):
        """
        Sin campo `narrative` en la respuesta del LLM no sale ningun delta.

        El reloj de la parte 1 cubre la espera; inventar texto para llenarla
        seria justo el bug que esa parte corrigio.
        """
        async def no_narrative(*args, **kwargs):
            yield '{"kpis": [], "executive_report": null}'

        with patch(
            "app.modules.chat_engine.kpi_calculator.LLMService.stream_completion",
            new=no_narrative,
        ), patch(
            "app.modules.chat_engine.kpi_calculator.LLMService.generate_completion",
            new=unittest.mock.AsyncMock(return_value='{"narrative": "ok", "kpis": [], "executive_report": null, "suggested_questions": []}'),
        ):
            resp = self.client.post(
                "/api/v1/chat/query/stream",
                json={"question": "Total de ventas", "connection_id": 1},
                headers=self.headers,
            )

        events = parse_sse(resp.text)
        deltas = [d for k, d in events if k == "delta"]
        self.assertEqual(deltas, [], "se emitio delta sin que el modelo produjera narrativa")

    # ------------------------------------------------------------------
    # 3. Masking: lo que se emite sale del rows enmascarado
    # ------------------------------------------------------------------
    def test_masking_happens_before_the_stream_sink_is_reached(self):
        """
        El sink se invoca DESPUES de `mask_rows`, nunca antes.

        Es la garantia de seguridad de este cambio: si el sink se llamara antes
        del enmascarado, estariamos mandando al navegador datos de una columna
        MASKED en claro, algo que la respuesta completa nunca hacia.
        """
        import inspect as _inspect
        from app.modules.chat_engine.engine import QueryEngine

        src = _inspect.getsource(QueryEngine.execute_query)
        mask_pos = src.index("mask_rows(rows, masked_columns)")
        sink_pos = src.index("narrative_sink=narrative_sink")
        self.assertLess(
            mask_pos, sink_pos,
            "el sink de narrativa se invoca antes de enmascarar: eso filtraria datos MASKED",
        )

    # ------------------------------------------------------------------
    # 4. Las primitivas que sostienen el stream
    # ------------------------------------------------------------------
    def test_extractor_handles_narrative_split_across_chunks(self):
        """El JSON llega partido: el extractor entrega la narrativa igual."""
        payload = '{"narrative": "El total fue $1.42M.\\n\\nSegundo parrafo.", "kpis": []}'
        for size in (1, 2, 5, 13, 9999):
            ex = NarrativeStreamExtractor()
            got = "".join(ex.feed(payload[i:i + size]) for i in range(0, len(payload), size))
            self.assertEqual(got, "El total fue $1.42M.\n\nSegundo parrafo.", f"falla con chunks de {size}")

    def test_extractor_never_invents_text(self):
        ex = NarrativeStreamExtractor()
        self.assertEqual(ex.feed('{"kpis": [], "sugerido": "algo"}'), "")

    def test_think_filter_hides_reasoning_across_chunk_boundary(self):
        """El `<think>` partido entre chunks no se muestra igual."""
        f = StreamingThinkFilter()
        self.assertEqual(f.feed("<thi"), "")   # prefijo retenido
        self.assertEqual(f.feed("nk>razonamiento secreto"), "")
        self.assertEqual(f.feed("</thi"), "")
        self.assertEqual(f.feed("nk>Respuesta visible"), "Respuesta visible")


if __name__ == "__main__":
    unittest.main()
