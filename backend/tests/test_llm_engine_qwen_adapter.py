"""Lo que cambio para que el motor hable con un 7B cuantizado.

Tres grupos, todos del mismo tipo de problema: el backend sabia algo que el
modelo no, y el modelo decidia algo que el backend ya sabia.

1. `resolve_model_for`: el nombre del modelo no es el mismo en los tres
   servidores y el configurado suele no ser el de ninguno. LM Studio devuelve
   404 ante un nombre desconocido, y ese 404 se repite en los cuatro endpoints
   del fallback hasta terminar con "no hay servidor LLM" con el servidor sano.
2. `_looks_like_truncated_json`: un JSON que se corto no es prosa. Publicarlo
   como narrativa pintaba `{"narrative": "El total de` en el chat.
3. El dialecto en el prompt: `engine.py` lo calculaba y se lo daba al validador
   y al executor, pero no al LLM.
"""
import unittest
from unittest.mock import patch

from app.core.prompts import PromptManager
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.chat_engine.kpi_calculator import KPICalculator
from app.modules.chat_engine.llm_service import LLMService


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


class _FakeClient:
    """httpx.AsyncClient minimo: solo `.get`, que es lo que usa el resolver."""

    def __init__(self, responses, recorder):
        self._responses = responses
        self._recorder = recorder

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url):
        self._recorder.append(url)
        for pattern, response in self._responses.items():
            if pattern in url:
                return response
        return _FakeResponse(404, {})


class TestResolucionDeModelo(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        LLMService._resolved_models = {}

    async def _resolver(self, ids, configured, recorder):
        payload = {"data": [{"id": i} for i in ids]} if ids is not None else {}
        fake = _FakeClient({"/v1/models": _FakeResponse(200, payload)}, recorder)
        with patch("app.modules.chat_engine.llm_service.httpx.AsyncClient", return_value=fake):
            return await LLMService.resolve_model_for("http://localhost:1234", configured)

    async def test_un_solo_modelo_en_el_servidor_gana(self):
        # El caso de LM Studio y llama.cpp con un modelo cargado: el
        # configurado no existe y el 404 era el sintoma.
        recorder = []
        got = await self._resolver(
            ["Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M"], "qwen2.5-coder:7b", recorder
        )
        self.assertEqual(got, "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M")
        self.assertEqual(len(recorder), 1, "hizo mas de un GET a /v1/models")

    async def test_el_configurado_gana_si_el_servidor_lo_reporta(self):
        recorder = []
        got = await self._resolver(
            ["qwen2.5-coder:7b", "otro:7b"], "qwen2.5-coder:7b", recorder
        )
        self.assertEqual(got, "qwen2.5-coder:7b")

    async def test_varios_modelos_sin_el_configurado_no_se_adivina(self):
        # Elegir el primero seria agregar un 404 mas, no quitar uno.
        recorder = []
        got = await self._resolver(["a:7b", "b:7b", "c:7b"], "qwen2.5-coder:7b", recorder)
        self.assertEqual(got, "qwen2.5-coder:7b")

    async def test_servidor_sin_modelos_devuelve_el_configurado(self):
        recorder = []
        got = await self._resolver([], "qwen2.5-coder:7b", recorder)
        self.assertEqual(got, "qwen2.5-coder:7b")

    async def test_el_resultado_se_cachea(self):
        recorder = []
        await self._resolver(["unico:7b"], "qwen2.5-coder:7b", recorder)
        await self._resolver(["unico:7b"], "qwen2.5-coder:7b", recorder)
        self.assertEqual(len(recorder), 1, "el GET a /v1/models no se cacheo")


class TestPayloadDeChat(unittest.TestCase):

    def test_lleva_parametros_de_muestreo(self):
        payload = LLMService._chat_payload("m", "sys", "usr", 0.1, 300)
        for key in ("repeat_penalty", "top_p", "seed"):
            self.assertIn(key, payload, f"falta {key}: sin el, un 7B cuantizado entra en bucle")

    def test_stop_solo_cuando_se_pide(self):
        self.assertNotIn("stop", LLMService._chat_payload("m", "s", "u", 0.1, 10))
        self.assertEqual(
            LLMService._chat_payload("m", "s", "u", 0.1, 10, stop=["\n"])["stop"], ["\n"]
        )

    def test_num_ctx_viene_de_la_configuracion(self):
        from app.core.config import settings
        payload = LLMService._chat_payload("m", "s", "u", 0.1, 10)
        self.assertEqual(payload["options"]["num_ctx"], settings.LLM_NUM_CTX)


class TestJsonTruncadoNoEsNarrativa(unittest.TestCase):
    """Un JSON cortado no es prosa: publicarlo pintaba media sintaxis en el chat."""

    def test_detecta_intencion_de_json(self):
        for texto in ('{"narrative": "El total de', '  ```json\n{"narrative"', '```{'):
            self.assertTrue(
                KPICalculator._looks_like_truncated_json(texto),
                f"no detecto JSON truncado: {texto!r}",
            )

    def test_prosa_real_no_se_marca(self):
        for texto in ("Las ventas cerrieron en 1.5M.", "Resultado:\n- 3 filas", ""):
            self.assertFalse(
                KPICalculator._looks_like_truncated_json(texto),
                f"trato prosa como JSON truncado: {texto!r}",
            )

    def test_sintesis_truncada_cae_a_prosa(self):
        import asyncio, json
        from unittest.mock import AsyncMock
        # El modelo corto la respuesta a mitad del JSON de kpis.
        cortado = json.dumps({
            "narrative": "El total del mes",
            "kpis": [{"title": "Ventas Totales", "column": "monto", "agg": "tot"}][0:0],
        })[:40]  # corta dentro del objeto

        with patch(
            "app.modules.chat_engine.llm_service.LLMService.generate_completion",
            new_callable=AsyncMock, return_value=cortado,
        ):
            res = asyncio.run(KPICalculator.generate_unified_synthesis_with_llm(
                question="Como van las ventas?",
                user_role="Economista",
                rows=[{"monto": 100.0}],
                columns=["monto"],
                secured_sql="SELECT 1",
                is_llm_active=True,
            ))
        self.assertIsNone(res, f"publico un JSON truncado como narrativa: {res}")


class TestDialectoEnElPrompt(unittest.TestCase):
    """El motor calculaba el dialecto y no se lo pasaba al LLM."""

    def test_sqlite_no_le_dice_extract_ni_ilike(self):
        prompt = PromptManager.get_text_to_sql_system_prompt(
            "Economista", {"fact_ventas"}, dialect="sqlite"
        )
        self.assertIn("sqlite", prompt.lower())
        regla = prompt.split("8.")[1].split("9.")[0]
        self.assertIn("strftime('%Y'", regla)
        self.assertIn("NO uses EXTRACT", regla)
        self.assertIn("ILIKE", regla, "debe nombrar lo que prohibe, no solo callarse")
        self.assertNotIn("string_agg(", regla, "no debe(arrastrar la regla de postgres")

    def test_postgres_si_nombra_sus_funciones(self):
        prompt = PromptManager.get_text_to_sql_system_prompt(
            "Economista", {"fact_ventas"}, dialect="postgres"
        )
        regla = prompt.split("8.")[1].split("9.")[0]
        self.assertIn("EXTRACT", regla)
        self.assertIn("ILIKE", regla)
        self.assertIn("string_agg", regla)
        # La regla del otro dialecto no debe arrastrarse: el prompt de postgres
        # NO puede recomendar strftime, que en postgres no existe.
        self.assertNotIn("strftime('%Y'", regla)

    def test_el_dialecto_llega_al_user_prompt(self):
        up = PromptManager.get_text_to_sql_user_prompt(
            "cuantas ventas hay", "Economista", "ESQUEMA", {"fact_ventas"}, dialect="postgres"
        )
        self.assertIn("postgres", up)

    def test_el_default_no_roba_el_dialecto_explicito(self):
        # Sin dialecto explicito el prompt no debe afirmar un motor que nadie
        # eligio: el default coincide con lo que usa el motor en una demo SQLite,
        # y se documenta en la firma.
        self.assertIn("sqlite", PromptManager.get_text_to_sql_system_prompt("X", {"t"}))


class TestEsquemaComoDdl(unittest.TestCase):
    """El modelo base es un Coder: el DDL es la forma que ya conoce."""

    def test_una_columna_con_descripcion(self):
        ddl = DynamicSchemaPruningService._render_table_as_ddl(
            "fact_ventas", "",
            ["monto_neto (DECIMAL, ej: '1.5M') - Monto neto en moneda local"],
        )
        self.assertIn('CREATE TABLE "fact_ventas"', ddl)
        self.assertIn("monto_neto DECIMAL", ddl)
        self.assertIn("Monto neto en moneda local", ddl)
        self.assertIn("1.5M", ddl, "los ejemplos de valor son la unica senal del formato de los datos")

    def test_parentesis_anidado_no_parte_el_tipo(self):
        ddl = DynamicSchemaPruningService._render_table_as_ddl(
            "t", "", ["monto (DECIMAL(14,2)) - Monto"]
        )
        self.assertIn("monto DECIMAL(14,2)", ddl)
        self.assertIn("Monto", ddl)

    def test_marca_de_enmascarado_sobrevive(self):
        ddl = DynamicSchemaPruningService._render_table_as_ddl(
            "t", "", ["salario (REAL) - Sueldo [ENMASCARADO]"]
        )
        self.assertIn("[ENMASCARADO]", ddl)

    def test_sin_guion_duplicado_en_el_comentario(self):
        ddl = DynamicSchemaPruningService._render_table_as_ddl(
            "t", "", ["nombre (TEXT) - Nombre del cliente"]
        )
        self.assertNotIn("-- -", ddl)

    def test_tabla_sin_columnas_no_emite_ddl_vacio(self):
        out = DynamicSchemaPruningService._render_table_as_ddl("t", "sinon", [])
        self.assertNotIn("CREATE TABLE", out)
        self.assertIn("solo lectura", out)

    def test_sinonimos_de_tabla_quedan_comentados(self):
        ddl = DynamicSchemaPruningService._render_table_as_ddl(
            "fact_ventas", "ventas, facturacion", ["monto (DECIMAL)"]
        )
        self.assertIn("Sinónimos: ventas, facturacion", ddl)


if __name__ == "__main__":
    unittest.main()