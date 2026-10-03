"""Aritmetica de KPIs: el numero que se publica tiene que ser el numero real.

Tres bugs corregidos, todos del mismo tipo: el calculo era plausible, pero
dividia por el denominador equivocado o exponentially sobre una metrica que no lo
admite, y el resultado erroneo se publicaba en la tarjeta KPI y en el informe
ejecutivo sin ninguna marca de error.
"""
import unittest

from app.modules.chat_engine.kpi_calculator import KPICalculator


class TestKpiArithmetic(unittest.TestCase):
    """El promedio debe dividir por la cantidad de valores NUMERICOS."""

    def _kpis_de(self, rows, num_col="monto", cat_col="categoria"):
        # KPICard es un modelo Pydantic: se accede por atributo, no por .get().
        kpis, _, _, _, _ = KPICalculator.build_dynamic_visualization(
            "Todas las metricas", [cat_col, num_col], rows
        )
        for k in kpis:
            title = k.title or ""
            if "romedio" in title:
                return k.value
        return None

    def test_promedio_ignora_filas_no_numericas(self):
        # 10 filas, solo 5 con valor de 40.
        # Promedio real = 200/5 = 40. El bug dividia por len(rows)=10 -> 20.
        rows = [
            {"categoria": f"c{i}", "monto": 40} for i in range(5)
        ] + [
            {"categoria": f"x{i}", "monto": None} for i in range(5)
        ]
        value = self._kpis_de(rows)
        self.assertIsNotNone(value, "no se genero KPI de promedio")
        self.assertIn("40", str(value), f"el promedio salio {value}; debia ser 40, no 20")
        self.assertNotIn("$20", str(value), "el promedio sigue usando len(rows) como divisor")

    def test_promedio_no_rompe_con_todas_numericas(self):
        rows = [{"categoria": f"c{i}", "monto": 10} for i in range(4)]
        value = self._kpis_de(rows)
        self.assertIn("10", str(value))

    def test_sin_valores_numericos_no_revienta(self):
        rows = [{"categoria": f"c{i}", "monto": "n/a"} for i in range(4)]
        # No debe lanzar.
        KPICalculator.build_dynamic_visualization(
            "prueba", ["categoria", "monto"], rows
        )


class TestParetoConNegativos(unittest.TestCase):
    """Una proporcion no es interpretable si la metrica admite negativos."""

    def test_no_informa_concentracion_sobre_valores_negativos(self):
        rows = [
            {"entidad": "A", "margen": 100.0},
            {"entidad": "B", "margen": -10.0},
            {"entidad": "C", "margen": -10.0},
        ]
        # Antes: total=80, top=100 -> 125% de concentracion con riesgo ALTO,
        # escrito en el informe como "concentra el 125%".
        result = KPICalculator.compute_pareto_concentration(rows, ["entidad", "margen"])
        self.assertIsNone(
            result,
            f"se informo concentracion sobre metricas con negativos: {result}",
        )

    def test_concentracion_normal_sigue_funcionando(self):
        rows = [
            {"entidad": f"e{i}", "monto": float(100 - i * 10)} for i in range(10)
        ]
        result = KPICalculator.compute_pareto_concentration(rows, ["entidad", "monto"])
        self.assertIsNotNone(result, "una metrica positiva debe seguir informando concentracion")
        share = result.get("top_entity_share")
        self.assertIsNotNone(share)
        self.assertGreaterEqual(share, 0)
        self.assertLessEqual(share, 100, f"concentracion fuera de rango: {share}%")


class TestKpiValorCalculadoPorElBackend(unittest.TestCase):
    """El modelo elige la METRICA; el numero sale de las filas reales.

    Antes el modelo escribia tambien el valor y el backend lo publicaba tal cual.
    Eso produjo dos bugs que costaron codigo de reparacion: `normalize_llm_number`
    nacio porque "1,234" se publicaba como "1.2%" (error de 1000x), y el bloque de
    porcentajes de `_sanitize_kpis` reformateaba a mano lo que el modelo habia
    escrito.

    Ese damage ya no es representable, y estos tests son la prueba: el `value`
    que el modelo manda se ignora SIEMPRE, incluso cuando es absurdo.
    """

    # `monto` esta en CURRENCY_COLUMN_KEYWORDS y `tasa` en
    # PERCENTAGE_COLUMN_KEYWORDS, asi que las dos formatean distinto; `unidades`
    # no esta en ninguna de las dos y exercise el caso plano.
    ROWS = [
        {"entidad": "A", "monto": 100.0, "tasa": 0.25, "costo": 40.0, "unidades": 2},
        {"entidad": "B", "monto": 200.0, "tasa": 0.75, "costo": 60.0, "unidades": 4},
        {"entidad": "C", "monto": 300.0, "tasa": 0.50, "costo": 100.0, "unidades": 6},
    ]
    COLS = ["entidad", "monto", "tasa", "costo", "unidades"]

    def _sintetizar(self, kpis_payload, rows=None, cols=None):
        """Corre _sanitize_kpis sobre KPIs crudas del LLM."""
        return KPICalculator._sanitize_kpis(
            kpis_payload, rows if rows is not None else self.ROWS,
            cols if cols is not None else self.COLS,
        )

    def test_el_value_del_modelo_se_ignora(self):
        # El modelo dice "$1.42M" sobre filas que suman 600. Gana la fila.
        kpis = self._sintetizar([
            {"title": "Total montos", "column": "monto", "agg": "total", "value": "$1.42M"},
        ])
        self.assertEqual(kpis[0].value, "$600.00", f"publico el numero del modelo: {kpis[0].value}")

    def test_cada_agregacion_calcula_su_valor(self):
        esperados = {
            "total": "12",
            "avg": "4.0",
            "max": "6",
            "min": "2",
            "count": "3",
        }
        for agg, esperado in esperados.items():
            kpis = self._sintetizar([
                {"title": f"KPI {agg}", "column": "unidades", "agg": agg},
            ])
            self.assertEqual(kpis[0].value, esperado, f"agg={agg} dio {kpis[0].value}, no {esperado}")

    def test_columna_de_dinero_y_de_porcentaje_se_formatean(self):
        kpis = self._sintetizar([
            {"title": "Costo total", "column": "costo", "agg": "total"},
            {"title": "Tasa promedio", "column": "tasa", "agg": "avg"},
        ])
        self.assertIn("$", kpis[0].value, f"columna de costo sin signo de moneda: {kpis[0].value}")
        self.assertTrue(kpis[1].value.endswith("%"), f"columna de tasa sin %: {kpis[1].value}")

    def test_columna_desconocida_se_descarta(self):
        # Inventar el nombre de la columna es el modo de falla principal: el
        # numero seria incalculable, y caer al value del modelo seria publicar
        # una cifra sin verificar.
        kpis = self._sintetizar([
            {"title": "Inventado", "column": "columna_que_no_existe", "agg": "total", "value": "999"},
        ])
        self.assertEqual(kpis, [], f"publico un KPI sobre columna inexistente: {kpis}")

    def test_agregacion_invalida_se_descarta(self):
        kpis = self._sintetizar([
            {"title": "raro", "column": "monto", "agg": "stddev", "value": "5"},
        ])
        self.assertEqual(kpis, [], f"acepto una agregacion desconocida: {kpis}")

    def test_columna_sin_numeros_no_publica_un_cero(self):
        rows = [{"entidad": "A", "estado": "ANULADO"}, {"entidad": "B", "estado": "OK"}]
        kpis = self._sintetizar(
            [{"title": "Suma de estados", "column": "estado", "agg": "total"}],
            rows=rows, cols=["entidad", "estado"],
        )
        self.assertEqual(kpis, [], f"sumo texto y publico el resultado: {kpis}")

    def test_valor_cero_de_datos_se_conserva(self):
        # El 0 es un dato legitimo ("Clientes en mora: 0"), no un campo faltante.
        rows = [{"entidad": "A", "unidades": 0}, {"entidad": "B", "unidades": 0}]
        kpis = self._sintetizar(
            [{"title": "Clientes en mora", "column": "unidades", "agg": "total"}],
            rows=rows, cols=["entidad", "unidades"],
        )
        self.assertEqual(len(kpis), 1, "el KPI en cero fue descartado")
        self.assertEqual(kpis[0].value, "0")

    def test_sin_titulo_se_descarta(self):
        kpis = self._sintetizar([
            {"column": "unidades", "agg": "total"},          # sin titulo
            {"title": "   ", "column": "unidades", "agg": "total"},
            {"title": "Bueno", "column": "unidades", "agg": "total"},
        ])
        self.assertEqual([k.title for k in kpis], ["Bueno"], f"filtro permisivo de mas: {kpis}")

    def test_avg_divide_por_valores_numericos(self):
        # Mismo criterio que build_dynamic_visualization: 3 filas, solo 2 con
        # valor. Dividir por len(rows) daria 3 en vez de 4.
        rows = [
            {"entidad": "A", "unidades": 4},
            {"entidad": "B", "unidades": 4},
            {"entidad": "C", "unidades": None},
        ]
        kpis = self._sintetizar(
            [{"title": "Promedio", "column": "unidades", "agg": "avg"}],
            rows=rows, cols=["entidad", "unidades"],
        )
        self.assertEqual(kpis[0].value, "4.0", f"el promedio salio {kpis[0].value}")


class TestSintesisConCantidadVariableDeKpis(unittest.TestCase):
    """len(kpis) == 3 era una condicion fragil: 2 o 4 KPIs validos descartaban todo."""

    @staticmethod
    def _payload(n_kpis, valor_cero=False):
        kpis = [
            {"title": f"KPI {i}", "column": "monto", "agg": "total"}
            for i in range(n_kpis)
        ]
        return {
            "overview": "Panorama del mes.",
            "kpis": kpis,
            "key_findings": ["Hallazgo 1"],
            "recommendations": ["Accion 1"],
            "risk_level": "MEDIO",
        }

    def _correr_semantico(self, payload, rows=None):
        import asyncio, json
        from unittest.mock import patch, AsyncMock
        resp = json.dumps(payload)
        with patch(
            "app.modules.chat_engine.llm_service.LLMService.generate_completion",
            new_callable=AsyncMock,
            return_value=resp,
        ):
            return asyncio.run(
                KPICalculator.generate_unified_synthesis_with_llm(
                    question="Como va el mes?",
                    user_role="Economista",
                    rows=rows or [{"entidad": "A", "monto": 10.0}],
                    columns=["entidad", "monto"],
                    secured_sql="SELECT 1",
                    is_llm_active=True,
                )
            )

    def test_dos_kpis_validos_producen_informe(self):
        res = self._correr_semantico(self._payload(2))
        self.assertIsNotNone(res, "2 KPIs validos descartaron la sintesis completa")
        self.assertEqual(len(res["kpis"]), 2)

    def test_cuatro_kpis_validos_producen_informe(self):
        res = self._correr_semantico(self._payload(4))
        self.assertIsNotNone(res, "4 KPIs validos descartaron la sintesis completa")
        self.assertGreaterEqual(len(res["kpis"]), 1)

    def test_sin_kpis_no_produce_informe(self):
        # Sin KPIs validos no se emite una lista vacia: el motor conserva las
        # tarjetas deterministas de build_dynamic_visualization.
        res = self._correr_semantico({"overview": "Panorama.", "kpis": []})
        self.assertFalse(res["kpis"], "una lista de KPIs vacia pisaria las KPIs deterministas")

    def test_kpi_sobre_columna_inexistente_no_produce_informe(self):
        # Es la degradacion nueva: si el modelo no puede anclar el KPI a una
        # columna real, se descartan TODOS y mandan las deterministas. Publicar
        # el `value` del modelo seria volver al numero sin verificar.
        res = self._correr_semantico({"overview": "Panorama.", "kpis": [
            {"title": "Imaginario", "column": "no_existe", "agg": "total", "value": "999"},
        ]})
        self.assertFalse(res["kpis"], "publico un KPI anclado a una columna inexistente")

    def test_kpi_en_cero_no_tira_la_sintesis(self):
        rows = [{"entidad": "A", "monto": 0.0}, {"entidad": "B", "monto": 0.0}]
        res = self._correr_semantico(self._payload(3), rows=rows)
        self.assertIsNotNone(res, "un KPI en 0 (dato real) tiro el analisis entero")
        self.assertEqual(len(res["kpis"]), 3)
        self.assertEqual(res["kpis"][0].value, "$0.00")


if __name__ == "__main__":
    unittest.main()
