"""
Ejecucion de las predicciones contra la base corporativa.

El SQL se ARMA ACA, no lo genera el LLM. Un modelo de 7B que tiene que
inventar el nombre de una tabla y de dos columnas para producir un forecast
introduce una fuente de error que no hace falta tener: los nombres se resuelven
por metadatos reales de la BD (`DynamicSchemaPruningService`) y por tipo de
columna. Si no se pueden resolver, se responde que no se puede y se dicen que
columnas se buscaron — no se cae a un nombre inventado.

El SQL que sale de aqui pasa por `ASTValidator` (SELECT-only, RBAC de tablas y
columnas, LIMIT) y por `SQLExecutor` (read-only a nivel de sesion, `mask_rows`).
Las predicciones no son un camino privilegiado alrededor de la gobernanza: son
el mismo camino que el chat, con el SQL escrito por codigo en vez de por el
modelo.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import mask_rows
from app.modules.admin_catalog.models import CorporateConnection
from app.modules.chat_engine.ast_validator import ASTValidator
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.chat_engine.forecast_calculator import (
    MIN_PERIODS,
    forecast_next_period,
    score_retention,
)
from app.modules.chat_engine.governance_guard import GovernanceGuard
from app.modules.chat_engine.sql_executor import SQLExecutor

# Nombres candidatos, en orden de preferencia. Se comparan en minúsculas.
DATE_CANDIDATES = ("fecha", "date", "periodo", "mes", "month", "fecha_movimiento", "fecha_venta", "created_at")
VALUE_CANDIDATES = ("monto", "total", "ingreso", "ventas", "importe", "amount", "revenue", "value", "monto_total")
ENTITY_CANDIDATES = ("complemento", "cliente", "razon_social", "razon social", "nombre_cliente", "nombre", "customer", "entity", "cliente_nombre")

_DATE_TYPES = ("date", "timestamp", "time")
_NUM_TYPES = ("int", "numeric", "decimal", "float", "double", "real", "bigint", "smallint", "money")


class ForecastUnavailable(Exception):
    """No hay forma honesta de calcular el forecast con esta base. Se explica por que."""


def _is_date_col(col: Dict[str, Any]) -> bool:
    return any(t in str(col.get("type", "")).lower() for t in _DATE_TYPES)


def _is_num_col(col: Dict[str, Any]) -> bool:
    return any(t in str(col.get("type", "")).lower() for t in _NUM_TYPES)


def _match_name(cols: Sequence[Dict[str, Any]], candidates: Sequence[str], predicate) -> Optional[str]:
    """Primer candidato presente como columna y que pase `predicate`."""
    by_lower = {str(c.get("name", "")).lower(): c for c in cols}
    for cand in candidates:
        hit = by_lower.get(cand.lower())
        if hit and predicate(hit):
            return str(hit["name"])
    return None


def resolve_columns(cols: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """Resuelve (fecha, valor, entidad) por nombre primero y por tipo despues.

    El orden importa: un nombre conocido gana siempre a un tipo generico, porque
    en una tabla con `monto` y `cantidad` las dos son numericas y elegir la
    primera seria una moneda de azar.
    """
    date_col = _match_name(cols, DATE_CANDIDATES, _is_date_col) or next(
        (str(c["name"]) for c in cols if _is_date_col(c)), None
    )

    # Excluye las columnas que `NON_METRIC_KEYWORDS` de kpi_calculator marca como
    # no-metricas (codigos, folios, ids) para no predecir sobre un correlativo.
    def looks_like_metric(c: Dict[str, Any]) -> bool:
        name = str(c.get("name", "")).lower()
        if name == "id" or name.startswith("id_") or name.endswith("_id"):
            return False
        return not any(k in name for k in ("folio", "codigo", "cod_", "numero_documento", "documento"))

    value_col = _match_name(cols, VALUE_CANDIDATES, lambda c: _is_num_col(c) and looks_like_metric(c)) or next(
        (str(c["name"]) for c in cols if _is_num_col(c) and looks_like_metric(c)), None
    )

    # La entidad NO tiene fallback por tipo: adivinar la columna de cliente entre
    # `descripcion`, `forma_pago` y `estado` no falla ruidosamente, produce un
    # score de retencion de basura que parece legitimo. Si no esta, no hay dato.
    entity_col = _match_name(cols, ENTITY_CANDIDATES, lambda c: True)

    return {"date_col": date_col, "value_col": value_col, "entity_col": entity_col}


def _quote(identifier: str, dialect: str = "postgres") -> str:
    """Comillas dobles, que SQLite y Postgres comparten para identificadores.

    `dialect` no se usa: se mantiene en la firma para que el punto de llamada
    pase el contexto explicito y quede claro que la decision es valida en los dos
    motores, no un descuido.
    """
    safe = "".join(ch for ch in identifier if ch.isalnum() or ch == "_")
    if not safe:
        raise ForecastUnavailable(f"Identificador no utilizable: {identifier!r}")
    return f'"{safe}"'


def build_series_sql(table: str, date_col: str, value_col: str, dialect: str = "postgres") -> str:
    """Serie mensual del valor. Solo montos positivos: es una serie de ingresos.

    El filtro `> 0` es una decision, no un detalle. Una serie que mezcla ingresos
    y egresos tiene un total cuyo signo depende de si el mes fue rentable, y el
    error relativo de esa serie no es interpretable. Se filtra y se declara en
    la respuesta (`income_only: True`) para que quien lee sepa que la vista es
    "ingresos", no "neto".
    """
    t, d, v = _quote(table, dialect), _quote(date_col, dialect), _quote(value_col, dialect)
    if dialect == "sqlite":
        period_expr = f"strftime('%Y-%m', {d})"
    else:
        period_expr = f"TO_CHAR({d}, 'YYYY-MM')"
    return (
        f"SELECT {period_expr} AS periodo, SUM({v}) AS valor "
        f"FROM {t} WHERE {v} > 0 GROUP BY 1 ORDER BY 1 LIMIT 500"
    )


def build_retention_sql(table: str, date_col: str, value_col: str, entity_col: str, dialect: str = "postgres") -> str:
    """Una fila por entidad con sus periodos en texto.

    Una fila por entidad-mes serian miles (315 x 9) y el `max_limit=500` del
    guardarrail las cortaria en silencio, devolviendo un subconjunto que parece
    completo. Los meses viajan dentro de la fila via `STRING_AGG`.

    El `ORDER BY` interno del `STRING_AGG` no es decorativo: `score_retention`
    parsea la lista en orden cronologico y de ahi sale la secuencia que decide
    si un cliente volvio al mes siguiente.
    """
    t, d, v, e = (_quote(table, dialect), _quote(date_col, dialect),
                  _quote(value_col, dialect), _quote(entity_col, dialect))
    if dialect == "sqlite":
        period_expr = f"strftime('%Y-%m', {d})"
        agg = "GROUP_CONCAT"
    else:
        period_expr = f"TO_CHAR({d}, 'YYYY-MM')"
        agg = "STRING_AGG"
    return (
        f"SELECT {e} AS entidad, "
        f"{agg}(DISTINCT {period_expr}, ',' ORDER BY {period_expr}) AS meses, "
        f"SUM({v}) AS valor "
        f"FROM {t} WHERE {v} > 0 AND {e} IS NOT NULL AND LENGTH({e}) > 0 "
        f"GROUP BY {e} ORDER BY valor DESC LIMIT 500"
    )


def _run_guarded_sql(
    db: Session,
    connection: CorporateConnection,
    sql: str,
    dialect: str,
    user_role: str,
    is_admin: bool,
    role_id: Optional[int],
    connection_id: int,
    table: str,
    cols: List[Dict[str, Any]],
    budget: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Valida, ejecuta y enmascara. Devuelve (filas, sql_auditable).

    `table_columns` es `Dict[str, List[str]]` indexado por TABLA, igual que lo
    arma `engine.py`. Pasarlo indexado por columna —que es lo que sale de
    `[c["name"] for c in cols]`— no rompe hoy porque estas consultas no usan
    `SELECT *`, pero deja el guardarrail mirando la tabla equivocada en el
    momento en que alguien agregue una columna mas al SELECT.
    """
    # `get_allowed_tables_for_role` ya quedo resuelto y cacheado por
    # `_load_fact_table` en el MISMO request. Volverlo a pedir aqui es la misma
    # consulta a la metadata otra vez para identical resultado.
    allowed = (budget or {}).get("allowed_tables")
    if allowed is None:
        allowed = GovernanceGuard.get_allowed_tables_for_role(
            user_role=user_role, is_admin=is_admin, db=db, role_id=role_id, connection_id=connection_id
        )
        if budget is not None:
            budget["allowed_tables"] = allowed
    blocked = GovernanceGuard.get_blocked_columns_for_role(
        user_role=user_role, is_admin=is_admin, db=db, role_id=role_id, connection_id=connection_id
    )
    table_columns = {table.lower(): [str(c["name"]) for c in cols if c.get("name")]}

    ok, secured, _ = ASTValidator.validate_and_secure_sql(
        sql,
        dialect=dialect,
        allowed_tables=allowed,
        blocked_columns=blocked,
        table_columns=table_columns,
        max_limit=500,
        is_admin=is_admin,
    )
    if not ok:
        raise ForecastUnavailable(f"La consulta no paso la validacion de seguridad: {secured}")

    rows = SQLExecutor.execute_raw_sql(connection, secured, dialect=dialect)

    # El enmascarado ocurre antes de que las filas salgan de esta capa, igual
    # que en el motor de chat: una prediccion no es una exencion del RBAC.
    masked = GovernanceGuard.get_masked_columns_for_role(
        user_role=user_role, is_admin=is_admin, db=db, role_id=role_id, connection_id=connection_id
    )
    if masked:
        rows = mask_rows(rows, masked)

    return rows, secured


def _load_fact_table(db: Session, connection: CorporateConnection, is_admin: bool, user_role: str,
                     role_id: Optional[int], connection_id: int, dialect: str,
                     budget: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Elige la tabla autorizada con mas filas: la tabla de hechos.

    Se elige por conteo, no por heuristica de nombre. "La tabla que mas filas
    tiene" es la definicion operacional de la tabla de movimientos, y con 1.645
    filas y 15 columnas un nombre como `movimientos` o `ventas` la describes
    igual de bien sin hardcodear nada.

    ponytail: son N COUNT(*) —uno por tabla autorizada— y `COUNT(*)` exacto en
    Postgres es un scan completo de cada tabla. Antes se pagaba eso TRES veces
    por request: `run_forecast`, `run_retention` y `audit_data_quality` elegian
    la tabla de hechos por separado, y con la auditoria encendida eran `3N + 3`
    scans completos para una sola peticion. `budget` es el cache de ESTA request
    (lo crea y lo pasa `run_prediction`): sharing explicito por parametro, no un
    global mutable, porque lo cacheado son los permisos de UN usuario y un
    global lo serviria a otro rol.

    Sigue siendo N COUNT(*), pero una sola vez. Si aparece latencia aun asi, la
    salida perezosa es guardar el conteo en `corporate_connections` al conectar
    y leerlo de ahi.
    """
    if budget is None:
        budget = {}
    if "fact_table" in budget:
        return budget["fact_table"]

    # Los tres bloques de `/predict` corren en paralelo (`asyncio.to_thread`),
    # asi que los tres pueden caer al cache vacio a la vez. Sin este lock los N
    # COUNT(*) se ejecutan tres veces igual y la memoizacion no arregla nada.
    lock = budget.get("lock")
    if lock is None:
        lock = budget["lock"] = threading.Lock()
    with lock:
        if "fact_table" in budget:
            return budget["fact_table"]

        allowed = budget.get("allowed_tables")
        if allowed is None:
            allowed = GovernanceGuard.get_allowed_tables_for_role(
                user_role=user_role, is_admin=is_admin, db=db, role_id=role_id, connection_id=connection_id
            )
            budget["allowed_tables"] = allowed
        if not allowed:
            raise ForecastUnavailable("El perfil no tiene tablas autorizadas en esta conexion.")

        best: Optional[Tuple[int, str]] = None
        for table in sorted(allowed):
            try:
                secured = ASTValidator.validate_and_secure_sql(
                    f"SELECT COUNT(*) AS n FROM {_quote(table, dialect)}",
                    dialect=dialect, allowed_tables=allowed, is_admin=is_admin,
                )[1]
                rows = SQLExecutor.execute_raw_sql(connection, secured, dialect=dialect)
            except Exception as exc:
                # Una tabla que no se puede contar (permisos, vista rota, dialecto) no
                # invalida la busqueda: se sigue con las demas.
                logger.debug("Tabla %s no consultable para conteo: %s", table, exc)
                continue
            if not rows:
                continue
            n = rows[0].get("n")
            if isinstance(n, (int, float)) and (best is None or n > best[0]):
                best = (int(n), table)

        if not best or best[0] == 0:
            raise ForecastUnavailable("Ninguna tabla autorizada contiene filas.")

        cols = DynamicSchemaPruningService.get_physical_table_columns(
            best[1], db_path=connection, include_samples=False
        )
        budget["fact_table"] = (best[1], cols)
        return best[1], cols


def run_forecast(
    db: Session,
    connection_id: int,
    user_role: str,
    is_admin: bool,
    role_id: Optional[int],
    budget: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Forecast del proximo periodo para la metrica principal de la fact table."""
    connection = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
    if not connection:
        raise ForecastUnavailable(f"No existe la conexion {connection_id}.")

    dialect = "sqlite" if str(getattr(connection, "db_type", "")).lower() == "sqlite" else "postgres"
    table, cols = _load_fact_table(db, connection, is_admin, user_role, role_id, connection_id, dialect, budget)
    resolved = resolve_columns(cols)

    if not resolved["date_col"]:
        raise ForecastUnavailable(
            f"La tabla '{table}' no tiene columna de fecha o periodo; no hay eje temporal sobre "
            f"el que proyectar. Columnas revisadas: {', '.join(str(c.get('name')) for c in cols)}"
        )
    if not resolved["value_col"]:
        raise ForecastUnavailable(
            f"La tabla '{table}' no tiene columna numerica de monto; no hay nada que predecir. "
            f"Columnas revisadas: {', '.join(str(c.get('name')) for c in cols)}"
        )

    sql = build_series_sql(table, resolved["date_col"], resolved["value_col"], dialect)
    rows, secured = _run_guarded_sql(
        db, connection, sql, dialect, user_role, is_admin, role_id, connection_id, table, cols, budget
    )

    # Se pasan los nombres EXPLICITOS en vez de confiar en la lista de candidatos
    # por defecto. `build_series_sql` aliasea a `periodo`/`valor`, y `valor` no
    # esta en esa lista: sin esto la serie se resuelve vacia y el forecast
    # reporta "no hay datos periodos suficientes" sobre una serie de 9 periodos
    # que es perfectamente forecastable. Un mensaje de error que culpa a los
    # datos cuando el bug es de nombre es el peor de los dos.
    forecast = forecast_next_period(
        rows, period_cols=("periodo",), value_cols=("valor",)
    )
    if not forecast:
        n = len(rows)
        return {
            "available": False,
            "reason": (
                f"La serie tiene {n} periodos y se necesitan {MIN_PERIODS} para publicar un forecast "
                f"con banda de error honesta. Con menos, la banda seria el error de un par de "
                f"observaciones y se leeria como una certeza que el dato no sostiene."
            ),
            "series_length": n,
            "min_periods_required": MIN_PERIODS,
            "table": table,
            "metric_column": resolved["value_col"],
            "date_column": resolved["date_col"],
            "income_only": True,
            "series": rows,
            "sql": secured,
        }

    forecast.update({
        "available": True,
        "table": table,
        "metric_column": resolved["value_col"],
        "date_column": resolved["date_col"],
        "income_only": True,
        "series": rows,
        "sql": secured,
    })
    return forecast


def run_retention(
    db: Session,
    connection_id: int,
    user_role: str,
    is_admin: bool,
    role_id: Optional[int],
    top_limit: int = 50,
    budget: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score de retencion por entidad, con la probabilidad medida por replay."""
    connection = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
    if not connection:
        raise ForecastUnavailable(f"No existe la conexion {connection_id}.")

    dialect = "sqlite" if str(getattr(connection, "db_type", "")).lower() == "sqlite" else "postgres"
    table, cols = _load_fact_table(db, connection, is_admin, user_role, role_id, connection_id, dialect, budget)
    resolved = resolve_columns(cols)

    missing = [k for k in ("date_col", "value_col", "entity_col") if not resolved[k]]
    if missing:
        raise ForecastUnavailable(
            f"La tabla '{table}' no tiene columna de {'/'.join(missing)}; sin una entidad identificable "
            f"no hay retencion que medir. Columnas revisadas: "
            f"{', '.join(str(c.get('name')) for c in cols)}"
        )

    sql = build_retention_sql(
        table, resolved["date_col"], resolved["value_col"], resolved["entity_col"], dialect
    )
    rows, secured = _run_guarded_sql(
        db, connection, sql, dialect, user_role, is_admin, role_id, connection_id, table, cols, budget
    )

    result = score_retention(rows, entity_cols=("entidad",), months_cols=("meses",), value_cols=("valor",))
    result.update({
        "table": table,
        "entity_column": resolved["entity_col"],
        "metric_column": resolved["value_col"],
        "date_column": resolved["date_col"],
        "income_only": True,
        "sql": secured,
        # Se recorta la lista de salida, no la calibracion: los tiers se
        # calculan sobre todas las filas que devolvio el SQL y despues se
        # muestran las primeras `top_limit` por peso en riesgo. Recortar antes
        # cambiaria los porcentajes publicados.
        "top": result["clients"][:top_limit],
        "truncated_by_limit": len(result["clients"]) > top_limit,
    })
    return result


# ----------------------------------------------------------------------------
# Calidad de datos (SOLO LECTURA)
# ----------------------------------------------------------------------------

def audit_data_quality(
    db: Session,
    connection_id: int,
    user_role: str,
    is_admin: bool,
    role_id: Optional[int],
    budget: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Defectos que contaminarian un forecast, reportados SIN modificar la base.

    Existe porque estos sesgos no se ven en un grafico y si no se nombran se
    heredan al numero: un egreso duplicado en dos periodos infla un mes y el
    forecast aprende de un error contable. La decision de corregir — y quien lo
    corrige — es del dueno del dato, no de la herramienta de analisis.

    Cada check es best-effort: si el SQL de uno falla, se omite en vez de
    tumbar el reporte entero. Un auditor que no corre por un permiso no puede
    dejar de correr por los otros.
    """
    findings: List[Dict[str, Any]] = []

    def add(check: str, severity: str, detail: str, count: Optional[int] = None) -> None:
        findings.append({"check": check, "severity": severity, "detail": detail, "count": count})

    try:
        connection = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
        if not connection:
            return findings
        dialect = "sqlite" if str(getattr(connection, "db_type", "")).lower() == "sqlite" else "postgres"
        table, cols = _load_fact_table(db, connection, is_admin, user_role, role_id, connection_id, dialect, budget)
        resolved = resolve_columns(cols)
        t = _quote(table, dialect)
        date_col, value_col = resolved["date_col"], resolved["value_col"]
    except Exception as exc:
        return [{"check": "auditoria", "severity": "BAJO", "detail": f"No se pudo inspeccionar la base: {exc}", "count": None}]

    # 1. Sin clave primaria: no hay fila que se pueda citar de forma estable.
    if not any(c.get("is_pk") for c in cols):
        add("sin_clave_primaria", "MEDIO",
            f"La tabla '{table}' no declara clave primaria. Sin ella no hay forma de identificar "
            "una fila de forma estable, y toda deduplicacion depende de comparar columna por columna.", None)

    # 2. Periodo que no cuadra con la fecha: el mismo hecho queda en dos meses.
    period_col = _match_name(cols, ("periodo", "period", "mes_periodo"), lambda c: True)
    if date_col and period_col:
        try:
            if dialect == "sqlite":
                expr = "strftime('%Y-%m', \"{d}\")".format(d=date_col)
            else:
                expr = f"TO_CHAR({_quote(date_col)}, 'YYYY-MM')"
            rows = SQLExecutor.execute_raw_sql(
                connection,
                f"SELECT COUNT(*) AS n FROM {t} WHERE {_quote(period_col)} IS NOT NULL "
                f"AND {_quote(period_col)} <> {expr}",
                dialect=dialect,
            )
            n = int(rows[0].get("n") or 0) if rows else 0
            if n:
                add("periodo_distinto_de_fecha", "ALTO",
                    f"{n} fila(s) tienen '{period_col}' distinto del mes de '{date_col}'. "
                    "Normalmente es el mismo movimiento contado en dos periodos: infla un mes y "
                    "el forecast aprende del error.", n)
        except Exception as exc:
            logger.debug("Check periodo/fecha omitido: %s", exc)

    # 3. Signo invertido: un ingreso con monto negativo.
    tipo_col = _match_name(cols, ("tipo", "tipo_movimiento", "tipo_transaccion", "clase"), lambda c: True)
    if value_col and tipo_col:
        try:
            tq = _quote(tipo_col)
            rows = SQLExecutor.execute_raw_sql(
                connection,
                f"SELECT COUNT(*) AS n FROM {t} WHERE {_quote(value_col)} < 0 "
                f"AND LOWER({tq}) NOT IN ('egreso','gasto','retiro','salida','anulacion')",
                dialect=dialect,
            )
            n = int(rows[0].get("n") or 0) if rows else 0
            if n:
                add("signo_invertido", "ALTO",
                    f"{n} fila(s) tienen '{value_col}' negativo y '{tipo_col}' que no es de salida. "
                    "Si el signo esta al reves, la serie de ingresos y la de egresos estan intercambiadas "
                    "y cualquier proyeccion sale del lado equivocado.", n)
        except Exception as exc:
            logger.debug("Check de signo omitido: %s", exc)

    # 4. Duplicados exactos sobre las columnas de negocio.
    #
    # ponytail: GROUP BY sobre ~14 columnas = sort/HashAggregate de la tabla
    # completa. Es un scan, no un indice, y por eso la auditoria completa es
    # opt-in (`include_data_quality`): no se le paga a una consulta que solo
    # queria el forecast.
    key_cols = [str(c["name"]) for c in cols
                if not c.get("is_pk") and str(c.get("name", "")).lower() != "id"]
    if len(key_cols) >= 3:
        try:
            key = ", ".join(_quote(c, dialect) for c in key_cols)
            rows = SQLExecutor.execute_raw_sql(
                connection,
                f"SELECT COUNT(*) AS n FROM (SELECT {key} FROM {t} GROUP BY {key} HAVING COUNT(*) > 1) x",
                dialect=dialect,
            )
            n = int(rows[0].get("n") or 0) if rows else 0
            if n:
                add("duplicados_exactos", "MEDIO",
                    f"{n} combinacion(es) de columnas de negocio aparecen repetidas. "
                    "Puede ser una reimportacion o dos operaciones realmente iguales; sin clave "
                    "primaria no hay forma de distinguirlas.", n)
        except Exception as exc:
            logger.debug("Check de duplicados omitido: %s", exc)

    return findings
