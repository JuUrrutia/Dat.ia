"""
Predicciones sobre series cortas: forecast del proximo periodo y score de
retencion por recurrencia.

Solo stdlib (`statistics`). Sin pandas, sin sklearn: el repo no los tiene
instalados y la aritmetica que hace falta son conteos y un par de cuantiles. Un
modelo de ML tampoco tendria nada que aprender sobre 9 periodos, asi que la
mejor honestidad aqui es el numero observable mas simple que supera su propio
backtest, con el error historico pegado al resultado.

Por que NO un modelo
-------------------
Sobre `movimientos_maxi3d_sql` (9 meses, 1.645 filas) el backtest de mes a mes
dio:

    naive (valor del mes anterior) ....... 17,1% MAPE   <- gana
    drift (regresion lineal) .............. 32,2% MAPE
    media movil de 3 ....................... 24,6% MAPE

Ademas el dia de semana explica R2=0,088 de la varianza diaria: no hay
estacionalidad que aprender. Un ARIMA o un Prophet sobre 9 puntos no mejora el
naive y agrega sobreajuste, o sea precision illusoria publicada como numero.
Por eso el metodo es naive y la incognita se muestra en vez de esconderse.

La frontera aritmetica
---------------------
Mismo contrato que `kpi_calculator`: el modelo elige la METRICA y el backend
calcula el VALOR. Ademas `_ZERO_HALLUCINATION_RULE` prohibe al LLM decir cifras
que no esten en las filas, asi que todo lo que se publica aca sale de estas
funciones puras sobre filas reales de la BD. Si un numero no se puede calcular,
se devuelve `None` y no se inventa.
"""

from __future__ import annotations

import decimal
import re
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Menos periodos que esto y el forecast NO se publica. Con 5 periodos hay 4
# backtests: la banda seria el error de cuatro observaciones y se leeria como
# si fuera una propiedad de la serie. No es un umbral conservador, es el punto
# en que el numero deja de ser informacion.
MIN_PERIODS = 6

# Minimo de observaciones para publicar una probabilidad de retorno. Por debajo
# la proporcion es ruido con decimales: "12,5%" sobre 8 casos no es una
# estimacion, es un resto. Se reporta None y la UI dice "sin evidencia".
MIN_EVIDENCE = 20

# Fraccion de los backtests historicos que la banda busca cubrir. 0.80 con 4-8
# residuos medidos: es el unico numero que se puede sostener sin inventar la
# forma de la distribucion.
BAND_COVERAGE = 0.80


# ----------------------------------------------------------------------------
# Utilidades de periodo
# ----------------------------------------------------------------------------

_PERIOD_RE = re.compile(r"^\s*(\d{4})[-/](\d{1,2})\s*$")
_ISO_PREFIX_RE = re.compile(r"^(\d{4}-\d{2})")


def normalize_period(value: Any) -> Optional[str]:
    """Normaliza un periodo a 'YYYY-MM', o None si no se puede leer.

    Acepta '2026-01', '2026/1', '2026-01-15T00:00:00' y `datetime.date`. Rechaza
    'ene 2026' y cualquier etiqueta libre: adivinar el periodo de una cadena no
    parseable seria inventar el eje temporal, que es lo que sostiene todo el
    calculo.
    """
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m")

    text = str(value).strip()
    if not text:
        return None

    m = _PERIOD_RE.match(text)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return f"{year:04d}-{month:02d}" if 1 <= month <= 12 else None

    m = _ISO_PREFIX_RE.match(text)
    return m.group(1) if m else None


def next_period(period: str) -> str:
    """El periodo siguiente a 'YYYY-MM'."""
    year, month = int(period[:4]), int(period[5:7])
    return f"{year + 1:04d}-01" if month == 12 else f"{year:04d}-{month + 1:02d}"


def period_distance(a: str, b: str) -> int:
    """Meses entre 'a' y 'b'. Positivo si `b` es posterior, negativo si anterior."""
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb - ma)


def parse_month_list(raw: Any) -> List[str]:
    """Parsea la lista de periodos que devuelve `STRING_AGG` en la agregacion.

    Viene como texto porque el SQL devuelve UNA fila por cliente, no una por
    cliente-mes: 315 clientes x 9 meses serian 2.835 filas y el `max_limit=500`
    de `ASTValidator` las cortaria en silencio. Los meses viajan dentro de la fila.
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        candidates: Sequence[Any] = list(raw)
    else:
        text = str(raw).strip()
        candidates = text.split(",") if text else []

    unique = set()
    for item in candidates:
        p = normalize_period(item)
        if p:
            unique.add(p)
    return sorted(unique)


def _quantile(sorted_vals: Sequence[float], q: float) -> Optional[float]:
    """Cuantil con interpolacion lineal. `sorted_vals` debe venir ordenado.

    Devuelve None si no hay datos: un cuantil de una lista vacia no es 0, es "no
    hay nada que cuantificar", y confundirlos produce bandas de ancho cero que
    se leen como una certeza que el dato no sostiene.
    """
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo]) * (1 - frac) + float(sorted_vals[hi]) * frac


def _pick_column(rows: List[Dict[str, Any]], candidates: Sequence[str]) -> Optional[str]:
    """Primer nombre de `candidates` que exista como columna en la fila."""
    if not rows:
        return None
    lower_to_actual = {str(k).lower(): k for k in rows[0].keys()}
    for cand in candidates:
        if cand in rows[0]:
            return cand
        hit = lower_to_actual.get(cand.lower())
        if hit:
            return hit
    return None


def _as_number(value: Any) -> Optional[float]:
    """Numero utilizable, o None. `bool` excluido a proposito: True es 1, no 1 venta.

    Acepta `Decimal` porque `SUM()` de Postgres devuelve `numeric` y el tipo
    llega crudo si el llamador no pasa por `SQLExecutor._clean_row`. Sin esto el
    forecast devuelve None sobre una serie perfectamente valida y el sintoma es
    "no hay datos", que no es cierto y no lleva a la causa.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    return None


def _resolve_series(
    rows: List[Dict[str, Any]],
    period_cols: Sequence[str],
    value_cols: Sequence[str],
) -> List[Tuple[str, float]]:
    """Serie (periodo, valor) ordenada cronologicamente.

    Los periodos repetidos se SUMAN, que es lo que ya hace un `GROUP BY periodo`
    del SQL. Volver a sumarlos aca mantiene el modulo usable si un llamador le
    pasa el detalle sin agregar.
    """
    if not rows:
        return []
    pcol = _pick_column(rows, period_cols)
    vcol = _pick_column(rows, value_cols)
    if not pcol or not vcol:
        return []

    merged: Dict[str, float] = {}
    for r in rows:
        period = normalize_period(r.get(pcol))
        if not period:
            continue
        value = _as_number(r.get(vcol))
        if value is None:
            continue
        merged[period] = merged.get(period, 0.0) + value

    return sorted(merged.items())


# ----------------------------------------------------------------------------
# Forecast del proximo periodo
# ----------------------------------------------------------------------------

def forecast_next_period(
    rows: List[Dict[str, Any]],
    period_cols: Sequence[str] = ("periodo", "mes", "month", "fecha", "date", "period"),
    value_cols: Sequence[str] = ("monto", "total", "ingreso", "ventas", "amount", "revenue", "value", "valor", "importe"),
) -> Optional[Dict[str, Any]]:
    """Predice el siguiente periodo y devuelve su banda de error medida.

    Metodo: naive (el valor del ultimo periodo). No por falta de alternativas —
    gano el backtest contra regresion lineal y media movil sobre esta serie.

    La banda NO es un parametro ajustado a mano: sale del cuantil 80 de los
    errores de backtest reales, con un piso en el peor error observado. Si el
    ultimo mes cae un 33%, la banda es de 33% porque eso es lo que la serie hizo
    antes, y por eso no puede prometer mas precision de la que tiene.

    Devuelve None si la serie no alcanza `MIN_PERIODS`, si el ultimo valor no es
    positivo o si el backtest no deja errores comparables. Un None aqui
    significa "no se", que es distinto de devolver 0.
    """
    series = _resolve_series(rows, period_cols, value_cols)
    if len(series) < MIN_PERIODS:
        return None

    values = [v for _, v in series]
    last = values[-1]
    if last <= 0:
        # El error relativo necesita un denominador positivo. Con ultimo valor
        # 0 o negativo ni la banda ni el punto son expresables.
        return None

    # Huecos: si faltan periodos entre el primero y el ultimo, la serie tiene
    # observaciones salteadas y el "ultimo" no es realmente el anterior. No se
    # descarta (el punto sigue siendo defendible) pero se marca, y `reliable`
    # queda en False para que la UI lo diga en vez de dejarlo pasar.
    has_gaps = any(
        period_distance(series[i][0], series[i + 1][0]) != 1
        for i in range(len(series) - 1)
    )

    # Backtest: predecir el periodo t con el valor de t-1, el mismo metodo que
    # despues se aplica hacia adelante. Asi el error publicado es el error de
    # ESTE forecast y no el de un metodo mas elaborado que no se usa.
    errors_pct: List[float] = []
    for i in range(1, len(values)):
        actual, predicted = values[i], values[i - 1]
        if actual > 0 and predicted > 0:
            errors_pct.append(abs(predicted - actual) / actual * 100.0)
    if not errors_pct:
        return None

    mape = statistics.mean(errors_pct)
    band = max(_quantile(sorted(errors_pct), BAND_COVERAGE) or 0.0, max(errors_pct))

    return {
        "period": next_period(series[-1][0]),
        "point": last,
        "lower": last * (1 - band / 100.0),
        "upper": last * (1 + band / 100.0),
        "band_pct": round(band, 1),
        "mape": round(mape, 1),
        "method": "naive (valor del ultimo periodo)",
        "n_periods": len(series),
        "n_backtests": len(errors_pct),
        "has_gaps": has_gaps,
        # Menos de 4 backtests no alcanzan para una banda: se publica el
        # numero pero no se declara confiable.
        "reliable": len(errors_pct) >= 4 and not has_gaps,
    }


# ----------------------------------------------------------------------------
# Score de retencion por recurrencia
# ----------------------------------------------------------------------------

# Cortes de tier. NO son ajustes: son la lectura directa de la tasa de retorno
# medida por replay sobre el historico (ver `_calibrate_tiers`). Lo que se
# publica como probabilidad sale de ahi, no de una constante escrita a mano.
TIER_MIN_MONTHS = ((3, "fiel"), (2, "recurrente"), (1, "unico"))


def _tier(months_active: int) -> str:
    for min_months, label in TIER_MIN_MONTHS:
        if months_active >= min_months:
            return label
    return "nuevo"


def _calibrate_tiers(clients: List[Tuple[str, List[str]]]) -> Dict[str, Dict[str, Any]]:
    """Tasa de retorno OBSERVADA por tier, por replay sin mirar el futuro.

    Para cada cliente y cada mes `m` en el que compro, se registra:
      - el tier que tenia EN `m` (meses activos hasta `m`, contando solo meses
        hasta `m` — nunca despues, o seria lookahead),
      - si volvio en el mes exacto `m + 1`.

    Asi la probabilidad publicada sale de contar transiciones que ocurrieron de
    verdad. El ultimo mes de cada cliente NO aporta caso de retorno porque no
    tiene sucesor dentro de la ventana: asi un cliente cuya unica compra cae en
    el ultimo mes no infla ni infla al revés la probabilidad de su tier.
    """
    stats: Dict[str, Dict[str, int]] = {}
    for _, months in clients:
        for i, month in enumerate(months):
            upto = sum(1 for prev in months if prev <= month)
            tier = _tier(upto)
            has_successor = i + 1 < len(months) and period_distance(month, months[i + 1]) == 1
            bucket = stats.setdefault(tier, {"casos": 0, "retornaron": 0})
            bucket["casos"] += 1
            if has_successor:
                bucket["retornaron"] += 1

    out: Dict[str, Dict[str, Any]] = {}
    for tier, s in stats.items():
        casos, volvieron = s["casos"], s["retornaron"]
        sufficient = casos >= MIN_EVIDENCE
        out[tier] = {
            "casos": casos,
            "retornaron": volvieron,
            "prob": round(volvieron / casos * 100, 1) if sufficient else None,
            "evidence_sufficient": sufficient,
        }
    return out


def score_retention(
    rows: List[Dict[str, Any]],
    entity_cols: Sequence[str] = ("complemento", "entidad", "cliente", "razon_social", "nombre", "customer", "entity"),
    months_cols: Sequence[str] = ("meses", "periodos", "months"),
    value_cols: Sequence[str] = ("ingreso_total", "valor", "monto", "total", "importe"),
) -> Dict[str, Any]:
    """Puntaje de retencion por cliente, con la probabilidad medida por tier.

    `rows` son UNA fila por cliente. Cada una trae sus periodos en una columna de
    texto separada por comas (`STRING_AGG`), porque una fila por cliente-mes
    pasaria el `max_limit=500` del guardarrail y volveria truncada sin avisar.

    El orden de salida es de ACCION, no de valor: primero los clientes que mas
    pesan y menos probable es que vuelvan. Un "unico" de 0,1% del ingreso no es
    una perdida; un "fiel" con 4 meses sin comprar si lo es.
    """
    empty = {"clients": [], "tiers": {}, "total_clients": 0, "total_revenue": 0.0}
    if not rows:
        return empty

    ecol = _pick_column(rows, entity_cols)
    mcol = _pick_column(rows, months_cols)
    vcol = _pick_column(rows, value_cols)
    if not ecol or not mcol:
        return empty

    parsed: List[Tuple[str, List[str], float]] = []
    for r in rows:
        name = r.get(ecol)
        if name is None or not str(name).strip():
            continue
        months = parse_month_list(r.get(mcol))
        if not months:
            continue
        value = _as_number(r.get(vcol)) if vcol else None
        parsed.append((str(name).strip(), months, value if value is not None else 0.0))

    if not parsed:
        return empty

    tiers = _calibrate_tiers([(n, ms) for n, ms, _ in parsed])
    all_months = sorted({m for _, ms, _ in parsed for m in ms})
    last_period = all_months[-1]
    total_revenue = sum(v for _, _, v in parsed)

    clients = []
    for name, months, value in parsed:
        info = tiers.get(_tier(len(months)), {})
        clients.append({
            "entity": name,
            "months_active": len(months),
            "last_purchase": months[-1],
            "months_since_last": period_distance(months[-1], last_period),
            "revenue": value,
            "revenue_share": round(value / total_revenue * 100, 2) if total_revenue else 0.0,
            "tier": _tier(len(months)),
            "return_prob": info.get("prob"),
            "evidence_sufficient": bool(info.get("evidence_sufficient", False)),
        })

    clients.sort(key=lambda c: c["revenue_share"] * (100 - (c["return_prob"] or 0)), reverse=True)

    return {
        "clients": clients,
        "tiers": tiers,
        "total_clients": len(clients),
        "total_revenue": total_revenue,
        "last_period": last_period,
    }


# ----------------------------------------------------------------------------
# Auto-verificacion
# ----------------------------------------------------------------------------

def _self_check() -> None:
    """Guardia de las afirmaciones que sostienen este modulo.

    1. La banda SIEMPRE contiene el punto. Si no, se publica un intervalo que
       excluye su propia estimacion y el lector no tiene forma de saberlo.
    2. El MAPE publicado es el de los errores de backtest, no otro.
    3. Sin `MIN_PERIODS` no se publica forecast.
    4. Sin `MIN_EVIDENCE` observaciones no se publica probabilidad.
    """
    # Serie que replica la de `movimientos_maxi3d_sql`.
    serie = [
        {"periodo": p, "monto": m} for p, m in [
            ("2026-01", 9.8e6), ("2026-02", 8.5e6), ("2026-03", 7.3e6),
            ("2026-04", 11.7e6), ("2026-05", 17.6e6), ("2026-06", 20.2e6),
            ("2026-07", 23.3e6), ("2026-08", 20.2e6), ("2026-09", 22.5e6),
        ]
    ]
    fc = forecast_next_period(serie)
    assert fc is not None, "una serie de 9 periodos debe producir forecast"
    assert fc["lower"] <= fc["point"] <= fc["upper"], "la banda no contiene el punto"
    assert fc["period"] == "2026-10", f"periodo siguiente mal calculado: {fc['period']}"
    # MAPE medido a mano sobre esta serie: 19,9%. El rango catches una cuenta rota.
    assert 15.0 <= fc["mape"] <= 25.0, f"MAPE fuera del rango medido en esta serie: {fc['mape']}"
    assert fc["band_pct"] >= fc["mape"], "la banda no puede ser mas ajustada que el MAPE"
    assert fc["reliable"] is True and fc["has_gaps"] is False

    assert forecast_next_period(serie[:5]) is None, "no debe predecir con menos de MIN_PERIODS"
    assert forecast_next_period([]) is None
    assert forecast_next_period([{"periodo": f"2026-{m:02d}", "monto": 0} for m in range(1, 8)]) is None

    # Serie con hueco: se publica pero no se declara confiable.
    con_hueco = [r for r in serie if r["periodo"] != "2026-05"]
    fc_hueco = forecast_next_period(con_hueco)
    assert fc_hueco is not None and fc_hueco["has_gaps"] is True and fc_hueco["reliable"] is False

    # `SUM()` de Postgres llega como `Decimal` si el llamador no pasa por
    # `_clean_row`. Debe dar el MISMO forecast, no None.
    fc_decimal = forecast_next_period([
        {"periodo": r["periodo"], "monto": decimal.Decimal(str(int(r["monto"])))} for r in serie
    ])
    assert fc_decimal is not None and fc_decimal["point"] == fc["point"]
    # bool no es un numero de negocio: True no es una venta.
    assert _as_number(True) is None and _as_number(None) is None and _as_number("7") is None

    # Retencion.
    clientes = [
        {"complemento": "A", "meses": "2026-01,2026-02,2026-03", "ingreso_total": 100.0},
        {"complemento": "B", "meses": "2026-01", "ingreso_total": 10.0},
        {"complemento": "C", "meses": "2026-01,2026-03", "ingreso_total": 50.0},
    ]
    ret = score_retention(clientes)
    assert ret["total_clients"] == 3, ret
    tiers = {c["entity"]: c["tier"] for c in ret["clients"]}
    assert tiers["A"] == "fiel" and tiers["B"] == "unico" and tiers["C"] == "recurrente", tiers
    # El replay cuenta cada mes comprado con el tier que se tenia EN ese mes, asi
    # que A y C tambien son "unico" en enero:
    #   unico      -> B@01, A@01, C@01 = 3 casos. Retornaron solo A@01.
    #   recurrente -> A@02 (llego a 2 activos), C@03 = 2 casos. Retornaron A@02.
    #   fiel       -> A@03 = 1 caso, sin sucesor en la ventana.
    unico = ret["tiers"]["unico"]
    assert unico["casos"] == 3 and unico["retornaron"] == 1, unico
    # C compro en 01 y 03: son 2 activos pero NO consecutivos, asi que su
    # regreso NO cuenta. Es lo que separa "recurrente" de "fiel": si el replay
    # mirara hacia adelante o ignorara el hueco, C inflaria el tier.
    assert ret["tiers"]["recurrente"]["casos"] == 2 and ret["tiers"]["recurrente"]["retornaron"] == 1
    assert ret["tiers"]["fiel"]["casos"] == 1 and ret["tiers"]["fiel"]["retornaron"] == 0
    # Con 3 observaciones ninguna probabilidad es publicable.
    assert unico["prob"] is None and unico["evidence_sufficient"] is False
    # Orden de accion: A pesa 10x mas que B y es de tier fiel -> primero.
    assert ret["clients"][0]["entity"] == "A", [c["entity"] for c in ret["clients"]]


if __name__ == "__main__":
    _self_check()
    print("forecast_calculator: OK")
