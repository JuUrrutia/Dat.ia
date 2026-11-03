"""Predicciones: el limite de confianza viaja con el numero, o no se publica.

Que se verifica acá
------------------
Las tres afirmaciones que hacen que una prediccion sea informacion y no una
cifra con decimales falsos:

1. La banda SIEMPRE contiene el punto estimado. Un intervalo que excluye su
   propia estimacion es peor que no publicar banda, porque el lector no tiene
   forma de notarlo.
2. El MAPE y el ancho de banda salen de errores REALES de backtest, no de
   constantes. Un 37,5% impreso en pantalla tiene que ser el peor error que la
   serie cometio, no un numero que alguien eligio para que se vea creible.
3. Sin evidencia suficiente NO se publica porcentaje. `prob: None` y `0,0%` son
   afirmaciones opuestas y la UI las muestra distinto.

Ademas se cubre que el SQL que arma el servicio es de solo lectura y pasa el
mismo guardarrail que el chat: una prediccion no es un camino privilegiado
alrededor de la gobernanza.
"""

import unittest
from decimal import Decimal

from app.modules.chat_engine.ast_validator import ASTValidator
from app.modules.chat_engine.forecast_calculator import (
    MIN_EVIDENCE,
    MIN_PERIODS,
    forecast_next_period,
    next_period,
    normalize_period,
    parse_month_list,
    period_distance,
    score_retention,
)
from app.modules.chat_engine.forecast_service import (
    build_retention_sql,
    build_series_sql,
    resolve_columns,
)


# Serie que replica la de `movimientos_maxi3d_sql`: 9 periodos, quiebre en mayo.
SERIE_REAL = [
    {"periodo": p, "valor": v} for p, v in [
        ("2026-01", 9_761_026), ("2026-02", 8_524_173), ("2026-03", 7_319_140),
        ("2026-04", 11_712_796), ("2026-05", 17_599_629), ("2026-06", 20_179_434),
        ("2026-07", 23_380_686), ("2026-08", 20_237_007), ("2026-09", 22_545_032),
    ]
]


class TestForecastHonesty(unittest.TestCase):
    """La banda y el error publicado tienen que ser los medidos."""

    def test_banda_contiene_el_punto(self):
        fc = forecast_next_period(SERIE_REAL)
        self.assertIsNotNone(fc)
        self.assertLessEqual(fc["lower"], fc["point"])
        self.assertLessEqual(fc["point"], fc["upper"])

    def test_mape_es_el_de_los_backtests_no_otro(self):
        fc = forecast_next_period(SERIE_REAL)
        errores = []
        vals = [r["valor"] for r in SERIE_REAL]
        for i in range(1, len(vals)):
            real, pred = vals[i], vals[i - 1]
            if real > 0 and pred > 0:
                errores.append(abs(pred - real) / real * 100)
        esperado = round(sum(errores) / len(errores), 1)
        self.assertEqual(fc["n_backtests"], len(errores))
        self.assertEqual(fc["mape"], esperado)

    def test_banda_cubre_el_peor_error_observado(self):
        """Con piso en el peor residuo: si la banda fuera mas ajustada que el
        peor error historico, seria una promesa que la serie ya rompio una vez."""
        fc = forecast_next_period(SERIE_REAL)
        vals = [r["valor"] for r in SERIE_REAL]
        peor = max(abs(vals[i - 1] - vals[i]) / vals[i] * 100 for i in range(1, len(vals)))
        self.assertGreaterEqual(fc["band_pct"] + 0.05, round(peor, 1))
        self.assertGreaterEqual(fc["band_pct"], fc["mape"])

    def test_sin_periodos_suficientes_no_publica_nada(self):
        for n in range(0, MIN_PERIODS):
            self.assertIsNone(
                forecast_next_period(SERIE_REAL[:n]),
                f"publico forecast con {n} periodos; el piso es {MIN_PERIODS}",
            )

    def test_ultimo_valor_no_positivo_no_publica_nada(self):
        """El error relativo necesita denominador positivo. Con ultimo valor 0,
        un 0 devuelto se leeria como 'ingreso cero' y no como 'no calculable'."""
        rows = [{"periodo": f"2026-{m:02d}", "valor": 0} for m in range(1, 8)]
        self.assertIsNone(forecast_next_period(rows))
        rows[3]["valor"] = -5
        self.assertIsNone(forecast_next_period(rows))

    def test_serie_con_hueco_se_marca_y_no_se_declara_confiable(self):
        sin_mayo = [r for r in SERIE_REAL if r["periodo"] != "2026-05"]
        fc = forecast_next_period(sin_mayo)
        self.assertIsNotNone(fc)
        self.assertTrue(fc["has_gaps"])
        self.assertFalse(fc["reliable"], "una serie con huecos no puede declararse confiable")

    def test_periodo_siguiente_calculado_por_calculadora(self):
        fc = forecast_next_period(SERIE_REAL)
        self.assertEqual(fc["period"], "2026-10")
        self.assertEqual(next_period("2026-12"), "2027-01")
        self.assertEqual(next_period("2026-01"), "2026-02")
        # Cruce de año, que es donde un parseo ingenuo falla.
        self.assertEqual(next_period("2027-11"), "2027-12")

    def test_acepta_decimal_de_postgres(self):
        """`SUM()` de Postgres devuelve `numeric`. Sin esto devuelve None sobre
        una serie valida y el sintoma es 'no hay datos', que no es cierto."""
        crudo = [{"periodo": r["periodo"], "valor": Decimal(r["valor"])} for r in SERIE_REAL]
        self.assertEqual(forecast_next_period(crudo)["point"], forecast_next_period(SERIE_REAL)["point"])

    def test_bool_no_cuenta_como_numero(self):
        self.assertIsNone(forecast_next_period([{"periodo": "2026-01", "valor": True}]))


class TestRetentionSinLookahead(unittest.TestCase):
    """El tier se calcula con los meses activos HASTA `m`, nunca despues."""

    def test_tier_usa_solo_el_pasado(self):
        # C compra en 01 y 03: dos activos, pero NO consecutivos.
        clientes = [
            {"entidad": "A", "meses": "2026-01,2026-02,2026-03", "valor": 100},
            {"entidad": "B", "meses": "2026-01", "valor": 10},
            {"entidad": "C", "meses": "2026-01,2026-03", "valor": 50},
        ]
        ret = score_retention(clientes)
        tiers = {c["entity"]: c["tier"] for c in ret["clients"]}
        self.assertEqual(tiers["A"], "fiel")
        self.assertEqual(tiers["B"], "unico")
        self.assertEqual(tiers["C"], "recurrente")

        # C no puede contar como retorno en "unico": compro en 03, no en 02.
        # Si el replay mirara hacia adelante o ignorara el hueco, el retorno de
        # "unico" seria 2 en vez de 1.
        self.assertEqual(ret["tiers"]["unico"]["casos"], 3)
        self.assertEqual(ret["tiers"]["unico"]["retornaron"], 1)
        self.assertEqual(ret["tiers"]["recurrente"]["casos"], 2)
        self.assertEqual(ret["tiers"]["recurrente"]["retornaron"], 1)

    def test_sin_evidencia_no_publica_probabilidad(self):
        """Un porcentaje sobre pocos casos se lee como medida. `None` se muestra
        como 'sin evidencia', que es lo que corresponde."""
        clientes = [{"entidad": f"E{i}", "meses": "2026-01", "valor": 1} for i in range(MIN_EVIDENCE - 1)]
        ret = score_retention(clientes)
        t = ret["tiers"]["unico"]
        self.assertEqual(t["casos"], MIN_EVIDENCE - 1)
        self.assertLess(t["casos"], MIN_EVIDENCE)
        self.assertIsNone(t["prob"])
        self.assertFalse(t["evidence_sufficient"])

        # Con evidencia suficiente si se publica.
        muchos = [{"entidad": f"E{i}", "meses": "2026-01", "valor": 1} for i in range(MIN_EVIDENCE)]
        t2 = score_retention(muchos)["tiers"]["unico"]
        self.assertTrue(t2["evidence_sufficient"])
        self.assertIsNotNone(t2["prob"])

    def test_orden_es_por_peso_en_riesgo_no_por_nombre(self):
        clientes = [
            {"entidad": "chico", "meses": "2026-01", "valor": 1},
            {"entidad": "grande", "meses": "2026-01,2026-02,2026-03", "valor": 1000},
        ]
        ret = score_retention(clientes)
        self.assertEqual(ret["clients"][0]["entity"], "grande")

    def test_parseo_de_lista_de_meses_tolera_basura(self):
        self.assertEqual(parse_month_list("2026-01,2026-02"), ["2026-01", "2026-02"])
        self.assertEqual(parse_month_list("2026-01, 2026-02 ,2026-01"), ["2026-01", "2026-02"])
        self.assertEqual(parse_month_list("ene 2026,2026-02"), ["2026-02"], "una etiqueta no parseable se descarta, no se adivina")
        self.assertEqual(parse_month_list(None), [])

    def test_normalize_period_rechaza_texto_no_parseable(self):
        self.assertEqual(normalize_period("2026-01-15T00:00:00"), "2026-01")
        self.assertEqual(normalize_period("2026/1"), "2026-01")
        self.assertIsNone(normalize_period("enero 2026"))
        self.assertIsNone(normalize_period("2026-13"))
        self.assertIsNone(normalize_period(None))

    def test_distancia_entre_periodos(self):
        self.assertEqual(period_distance("2026-01", "2026-02"), 1)
        self.assertEqual(period_distance("2026-12", "2027-01"), 1)
        self.assertEqual(period_distance("2026-03", "2026-01"), -2)


class TestColumnResolution(unittest.TestCase):
    """La resolucion de columnas decide si la prediccion es real o basura."""

    COLS = [
        {"name": "id", "type": "bigint", "is_pk": False},
        {"name": "fecha", "type": "timestamp", "is_pk": False},
        {"name": "monto", "type": "bigint", "is_pk": False},
        {"name": "cantidad", "type": "bigint", "is_pk": False},
        {"name": "complemento", "type": "text", "is_pk": False},
    ]

    def test_nombre_conocido_gana_al_tipo_generico(self):
        """Con `monto` y `cantidad` las dos son bigint: elegir la primera seria
        una moneda de azar. El nombre manda."""
        r = resolve_columns(self.COLS)
        self.assertEqual(r["value_col"], "monto")
        self.assertEqual(r["date_col"], "fecha")
        self.assertEqual(r["entity_col"], "complemento")

    def test_excluye_correlativos_y_folios(self):
        cols = self.COLS + [
            {"name": "numero_documento", "type": "bigint", "is_pk": False},
            {"name": "folio", "type": "bigint", "is_pk": False},
        ]
        self.assertEqual(resolve_columns(cols)["value_col"], "monto")

    def test_entidad_sin_nombre_conocido_queda_none(self):
        """Sin columna de entidad NO se adivina. Elegir `descripcion` o
        `forma_pago` no falla ruidosamente: produce un score de retencion de
        basura que parece legitimo."""
        cols = [
            {"name": "fecha", "type": "date", "is_pk": False},
            {"name": "monto", "type": "numeric", "is_pk": False},
            {"name": "descripcion", "type": "text", "is_pk": False},
        ]
        self.assertIsNone(resolve_columns(cols)["entity_col"])


class TestGeneratedSqlIsReadOnly(unittest.TestCase):
    """El SQL de prediccion pasa el MISMO guardarrail que el chat."""

    def _assert_select_only(self, sql, dialect="postgres"):
        ok, secured, _ = ASTValidator.validate_and_secure_sql(sql, dialect=dialect)
        self.assertTrue(ok, f"el SQL de prediccion no paso el guardarrail: {secured}")

    def test_sql_de_serie_es_select_limitado(self):
        sql = build_series_sql("movimientos", "fecha", "monto")
        self.assertIn("SUM", sql)
        self.assertTrue(sql.upper().lstrip().startswith("SELECT"))
        for prohibido in ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"):
            self.assertNotIn(prohibido, sql.upper())
        self._assert_select_only(sql)

    def test_sql_de_retencion_una_fila_por_entidad(self):
        """Una fila por entidad-mes pasaria `max_limit=500` y volveria truncada
        sin avisar: 315 clientes x 9 meses = 2.835 filas."""
        sql = build_retention_sql("movimientos", "fecha", "monto", "complemento")
        self.assertIn("STRING_AGG", sql)
        self.assertIn("GROUP BY", sql)
        for prohibido in ("INSERT", "UPDATE", "DELETE", "DROP"):
            self.assertNotIn(prohibido, sql.upper())
        self._assert_select_only(sql)

    def test_dialecto_sqlite_no_usa_string_agg(self):
        sql = build_retention_sql("t", "fecha", "monto", "cliente", dialect="sqlite")
        self.assertIn("GROUP_CONCAT", sql)
        self.assertIn("strftime", sql)
        self._assert_select_only(sql, dialect="sqlite")

    def test_identificadores_se_neutralizan(self):
        """Un nombre de tabla con comillas no puede cerrar la sentencia.

        La propiedad que importa NO es que la palabra "DROP" desaparezca del
        texto — tras filtrar a alfanumerico queda DENTRO del identificador
        (`tablaDROPTABLEx`), que es un token inerte. Lo que importa es que siga
        siendo UN identificador entre comillas dobles y que el guardarrail lo
        acepte como el único SELECT.
        """
        sql = build_series_sql('tabla"; DROP TABLE x; --', "fecha", "monto")
        self.assertIn('FROM "tablaDROPTABLEx"', sql)
        self.assertEqual(sql.count(";"), 0, "no debe quedar ningun separador de sentencia")
        self._assert_select_only(sql)

    def test_solo_ingresos_y_asimetria_documentada(self):
        """El filtro `> 0` es una decision: la respuesta declara
        `income_only` para que la vista sea 'ingresos', no 'neto'."""
        sql = build_series_sql("movimientos", "fecha", "monto")
        self.assertIn('> 0', sql)


class TestEndpointPayload(unittest.TestCase):
    """El contrato HTTP tiene que armarse, no solo el calculo.

    Estos casos viven aca y no junto al calculo porque el bug que cubren no esta
    en `forecast_calculator`: `score_retention` devuelve `tiers` como DICT
    indexado por nombre y el valor no incluye la clave. `RetentionTier(**valor)`
    levanta `Field required: tier` y el endpoint responde 500 en TODAS las
    llamadas de retencion — mientrastodo el servicio, medido directo, funciona.
    """

    def test_tiers_del_servicio_se_modelan_inyectando_la_clave(self):
        from app.modules.chat_engine.schemas import RetentionTier

        stats = {"casos": 314, "retornaron": 52, "prob": 16.6, "evidence_sufficient": True}
        with self.assertRaises(Exception):
            RetentionTier(**stats)  # Sin la clave: falla.
        self.assertEqual(RetentionTier(**{"tier": "unico", **stats}).tier, "unico")

    def test_forecast_no_disponible_modela_sin_periodos(self):
        """El camino de 'no hay datos suficientes' no trae `n_periods`: si el
        modelo lo exigiera, el endpoint 500aria justo en el caso que existe para
        ser honesto."""
        from app.modules.chat_engine.schemas import ForecastCard

        card = ForecastCard(available=False, reason="faltan periodos")
        self.assertFalse(card.available)
        self.assertEqual(card.n_periods, 0)

    def test_fallo_parcial_no_tumba_el_envelope(self):
        """Forecast caido + retencion viva: 200 con `errors`, no 500."""
        from app.modules.chat_engine.schemas import ForecastCard, PredictionResponse

        p = PredictionResponse(
            question="predice el mes",
            forecast=ForecastCard(available=False, reason="sin columna de fecha"),
            retention=None,
            errors=["Retención: La tabla 'x' no tiene columna de entidad"],
        )
        self.assertEqual(len(p.errors), 1)
        self.assertIsNone(p.retention)


if __name__ == "__main__":
    unittest.main()

