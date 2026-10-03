import json
import re
import inspect
import statistics
from typing import Any, Callable, List, Dict, Optional, Tuple
from app.core.constants import DATE_COLUMN_KEYWORDS, CURRENCY_COLUMN_KEYWORDS, PERCENTAGE_COLUMN_KEYWORDS
from app.core.logging import logger
from app.core.prompts import PromptManager
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.schemas import KPICard, ExecutiveReport

# Parametros de generacion de la sintesis unificada, en un solo lugar.
#
# `SYNTHESIS_MAX_TOKENS` estaba en 1000 y el JSON que pide el prompt se estima en
# 850-950 tokens: narrativa de 2-3 parrafos + 3 KPIs + overview + 2-3 hallazgos +
# 3 recomendaciones + business_impact + 3 preguntas + el andamiaje JSON. Sin
# margen, y sin margen no hay margen: basta un acento de mas en una cadena y el
# cierre se cae.
#
# El techo NO se sube mucho mas a proposito. El cliente corta la espera a 90 s
# (`useChatEngine.ts`) y un Q4_K_M en CPU va a ~5 tok/s, asi que cada token de
# mas son ~200 ms de espera visible. Subir el limite sin aligerar el payload
# compra JSON truncado a cambio de mas timeout.
SYNTHESIS_MAX_TOKENS = 1200
SYNTHESIS_TEMPERATURE = 0.15

NON_METRIC_KEYWORDS = {
    "ano", "anio", "year", "mes", "month", "dia", "day", "fecha", "date",
    "periodo", "period", "trimestre", "quarter", "semestre", "codigo", "code",
    "cod", "zip", "postal", "rut", "dni", "telefono", "phone", "celular",
    "orden", "order", "num_orden", "numero", "version", "id", "rut_empresa"
}

def is_true_numeric_metric(col_name: str, sample_val: Any) -> bool:
    col_lower = col_name.lower().strip()
    if col_lower.startswith("id_") or col_lower.endswith("_id") or col_lower == "id":
        return False
    if col_lower.startswith("campo_") or col_lower.startswith("col_") or col_lower.startswith("columna_") or col_lower.startswith("field_"):
        return False
    if any(k in col_lower for k in ("folio", "rut", "codigo", "cod_", "numero_doc", "num_doc", "documento", "doc_")):
        return False
    if any(col_lower == k or col_lower.startswith(f"{k}_") or col_lower.endswith(f"_{k}") for k in NON_METRIC_KEYWORDS):
        return False
    if not isinstance(sample_val, (int, float)):
        return False
    if isinstance(sample_val, int) and (1900 <= sample_val <= 2100) and any(k in col_lower for k in ("ano", "anio", "year")):
        return False
    return True

# Agregaciones que el backend sabe calcular sobre las filas reales. El modelo
# elige UNA de estas y la columna; el numero sale de aca, no de el.
#
# `count` es COUNT(*) semantica — el numero de filas — y no la cantidad de
# valores no nulos: si el usuario pregunta "cuantos clientes hay" sobre 10 filas
# donde solo 3 traen monto, responder "3" seria una lectura equivocada de la
# pregunta, no una aproximacion.
KPI_AGGREGATIONS = ("total", "avg", "max", "min", "count")


def format_metric_value(col_name: str, value: Any) -> str:
    """Formatea un valor de metrica segun el TIPO de la columna.

    Se extrajo de `build_dynamic_visualization`, que hacia esta misma cuenta
    inline tres veces (total, maximo, promedio). Ahora la misma cuenta decide
    tambien el valor de los KPIs que elige el modelo, y dos copias de un
    formateo divergen en el primer caso raro que aparezca.
    """
    col_lower = (col_name or "").lower()
    is_currency = any(k in col_lower for k in CURRENCY_COLUMN_KEYWORDS)
    is_percentage = any(k in col_lower for k in PERCENTAGE_COLUMN_KEYWORDS)
    if is_currency:
        return f"${value:,.2f}"
    if is_percentage:
        return f"{value:.1f}%"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return f"{value:,}"


def aggregate_column(rows: List[Dict[str, Any]], col: str, agg: str) -> Optional[Any]:
    """Calcula `agg` sobre `col` en `rows`. Devuelve None si no se puede calcular.

    El divisor de `avg` es la cantidad de valores NUMERICOS, no la de filas: es
    el mismo criterio de `build_dynamic_visualization` y por el mismo motivo.
    Dividir por `len(rows)` con filas sin valor publica un promedio que no es el
    promedio, y no se puede marcar como error porque sale un numero plausible.

    No se exige que la columna pase `is_true_numeric_metric`: el modelo ya dijo
    que esa es la metrica de la pregunta y ese es el trabajo que le toca. Lo unico
    que se exige es que los valores **sean** numeros — si no hay ninguno, se
    devuelve None y el KPI se descarta en vez de publicar un 0 inventado.
    """
    if agg == "count":
        return len(rows)
    if agg not in KPI_AGGREGATIONS:
        return None
    values = [
        r.get(col)
        for r in rows
        if isinstance(r.get(col), (int, float)) and not isinstance(r.get(col), bool)
    ]
    if not values:
        return None
    if agg == "total":
        return sum(values)
    if agg == "avg":
        return sum(values) / len(values)
    if agg == "max":
        return max(values)
    return min(values)


def normalize_llm_number(text: str) -> str:
    """Convierte a float() un numero escrito por el LLM, sinoidal su separador.

    El LLM mezcla convenciones: "1,234" (miles en ingles), "1.234" (miles en
    espanol), "0,5" (decimal en espanol), "0.5" (decimal en ingles). El codigo
    hacia replace(',', '.') sobre TODO, asi que "1,234" -> "1.234" -> se
    publicaba como "1.2%": una corrupcion de 1000x en el informe ejecutivo.

    HOY NO LA USA NINGUN CAMINO DEL PIPELINE. El LLM ya no escribe los valores de
    los KPIs: elige la columna y la agregacion (`column` + `agg`), y el numero lo
    calcula `aggregate_column` y lo formatea `format_metric_value`. Con el valor
    calculado aca no hay separador que interpretar, asi que el bug que reparaba
    esta funcion ya no es representable.

    Se conserva como especificacion del criterio para cuando algo vuelva a parsear
    un numero escrito en texto libre.

    REGLA: un separador seguido de EXACTAMENTE 3 digitos y con mas de un digito
    antes es de miles (1,234 -> 1234). Con 1 o 2 digitos despues es decimal
    (0,5 -> 0.5). "1,234" es ambiguo entre locales, pero leido como miles el
    error es 1000x y leido como decimal casi nunca ocurre en un KPI.
    """
    stripped = str(text).strip()
    if re.fullmatch(r'-?\d{1,3}(?:[.,]\d{3})+(?:\.\d+)?', stripped):
        # Todos los grupos de 3 son separadores de miles.
        return re.sub(r'(?<=\d)[.,](?=\d{3}(?!\d))', '', stripped)
    return stripped.replace(',', '.')


class KPICalculator:
    """
    Computes business metrics, KPICards, and deep ExecutiveReports
    agnostic to database engine/schema.
    """

    @classmethod
    def build_dynamic_visualization(
        cls,
        question: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        user_role: str = "Economista"
    ) -> Tuple[List[KPICard], str, Dict[str, Any], str, Optional[ExecutiveReport]]:
        if not rows or not columns:
            kpis = [
                KPICard(title="Registros Obtenidos", value="0 Registros", subtitle="Sin coincidencia en BD", change_direction="neutral")
            ]
            chart_option = {"series": []}
            summary = f"Informe de Negocio: La consulta fue ejecutada pero no devolvió registros coincidentes para la pregunta '{question}'."
            exec_rep = ExecutiveReport(
                overview=f"No se encontraron registros para la consulta '{question}'.",
                key_findings=["Cero registros coincidentes con los criterios de búsqueda."],
                recommendations=["Verificar los parámetros de búsqueda o ampliar el rango de fechas/categorías."],
                risk_level="BAJO"
            )
            return kpis, "bar", chart_option, summary, exec_rep

        num_cols = []
        date_cols = []
        cat_cols = []

        for col in columns:
            col_lower = col.lower().strip()
            val = rows[0].get(col)

            if is_true_numeric_metric(col, val):
                num_cols.append(col)
            elif any(dk in col_lower for dk in DATE_COLUMN_KEYWORDS) or any(col_lower == k or col_lower.startswith(f"{k}_") for k in ("ano", "anio", "year", "mes", "dia", "periodo", "fecha")):
                date_cols.append(col)
            elif not col_lower.startswith("id_") and not col_lower.endswith("_id") and col_lower != "id":
                cat_cols.append(col)

        if not cat_cols and not date_cols:
            cat_cols = [c for c in columns if not isinstance(rows[0].get(c), (int, float))] or [columns[0]]

        primary_cat = cat_cols[0] if cat_cols else (date_cols[0] if date_cols else columns[0])
        primary_num = num_cols[0] if num_cols else None

        # CASE 1: NO QUANTITATIVE METRIC COLUMNS (Descriptive / Categorical / Survey data)
        if not primary_num:
            first_row = rows[0]
            top_entity = str(first_row.get(primary_cat, "Registro 1"))
            cat_title = primary_cat.replace('_', ' ').title()

            kpis = [
                KPICard(
                    title="Total Registros",
                    value=f"{len(rows)} Registros",
                    subtitle="Muestra analizada en BD",
                    change_direction="neutral"
                ),
                KPICard(
                    title=f"Campo: {cat_title}",
                    value=top_entity[:24],
                    subtitle="Primer registro representativo",
                    change_direction="neutral"
                ),
                KPICard(
                    title="Estructura de Datos",
                    value=f"{len(columns)} Columnas",
                    subtitle=f"{', '.join(columns[:3])}...",
                    change_direction="neutral"
                )
            ]

            chart_type = "none"
            chart_option = {"series": []}

            summary = (
                f"Informe de Consulta: Se recuperaron **{len(rows)} registros** de la base de datos para '{question}'. "
                f"La información se clasifica por **{cat_title}** con **{len(columns)} atributos** de detalle disponibles."
            )

            exec_rep = ExecutiveReport(
                overview=f"Análisis descriptivo de {len(rows)} registros procesados sobre la consulta '{question}' en la base de datos activa.",
                key_findings=[
                    f"Se recuperaron {len(rows)} registros descriptivos organizados en {len(columns)} columnas de información.",
                    f"Dimensión representativa observada: '{top_entity}' ({cat_title}).",
                    f"Consulta validada y auditada bajo el perfil {user_role}."
                ],
                recommendations=[
                    "Consultar el detalle completo de cada fila en la pestaña de Datos.",
                    "Cruzar con métricas numéricas o filtros adicionales para profundizar el análisis analítico."
                ],
                risk_level="BAJO",
                business_impact=f"Información disponible para seguimiento y consulta de {cat_title}."
            )

            return kpis, chart_type, chart_option, summary, exec_rep

        # CASE 2: REAL QUANTITATIVE METRICS PRESENT
        # El divisor tiene que ser la cantidad de valores NUMERICOS, no la cantidad
        # de filas. Antes dividia el sumatorio (que ya filtra las no numericas) por
        # len(rows): con 10 filas donde solo 5 tienen valor, el promedio salia la
        # mitad del real y se publicaba en la tarjeta KPI y en el informe ejecutivo.
        numeric_vals = [
            (r.get(primary_num, 0) or 0)
            for r in rows
            if isinstance(r.get(primary_num), (int, float))
        ]
        total_val = sum(numeric_vals)
        avg_val = (total_val / len(numeric_vals)) if numeric_vals else 0

        max_row = max(rows, key=lambda x: (x.get(primary_num, 0) or 0) if isinstance(x.get(primary_num), (int, float)) else 0) if rows else {}
        top_entity = str(max_row.get(primary_cat, "Entidad")) if max_row else "N/A"
        top_val = max_row.get(primary_num, 0) or 0

        formatted_total = format_metric_value(primary_num, total_val)
        formatted_top = format_metric_value(primary_num, top_val)
        formatted_avg = format_metric_value(primary_num, avg_val)

        kpi_title = primary_num.replace('_', ' ').title()
        kpis = [
            KPICard(
                title=f"Total {kpi_title}",
                value=formatted_total,
                subtitle=f"Acumulado ({len(rows)} filas)",
                change_direction="positive"
            ),
            KPICard(
                title="Valor Máximo",
                value=formatted_top,
                subtitle=top_entity[:24],
                change_direction="positive"
            ),
            KPICard(
                title="Promedio por Registro",
                value=formatted_avg,
                subtitle=f"Muestra de {len(rows)} ítems",
                change_direction="neutral"
            )
        ]

        if date_cols and primary_num:
            chart_type = "line"
        elif len(rows) <= 6 and primary_cat and primary_num:
            chart_type = "pie"
        else:
            chart_type = "bar"

        categories = [str(r.get(primary_cat, f'Item {i+1}')) for i, r in enumerate(rows[:20])]
        values = [(float(r.get(primary_num, 0)) if isinstance(r.get(primary_num), (int, float)) else 0) for r in rows[:20]]

        if chart_type == "pie":
            pie_data = [{"name": str(r.get(primary_cat, f'Item {i+1}')), "value": float(r.get(primary_num, 0)) if isinstance(r.get(primary_num), (int, float)) else 0} for i, r in enumerate(rows[:8])]
            chart_option = {
                "tooltip": {"trigger": "item"},
                "series": [{
                    "name": kpi_title,
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "data": pie_data
                }]
            }
        elif chart_type == "line":
            chart_option = {
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": categories},
                "yAxis": {"type": "value"},
                "series": [{
                    "name": kpi_title,
                    "type": "line",
                    "smooth": True,
                    "data": values
                }]
            }
        else:
            chart_option = {
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": categories},
                "yAxis": {"type": "value"},
                "series": [{
                    "name": kpi_title,
                    "type": "bar",
                    "data": values
                }]
            }

        pct_top = round((top_val / total_val * 100), 1) if total_val > 0 else 0

        summary = (
            f"Informe Ejecutivo: Se procesaron **{len(rows)} registros** de la base de datos corporativa para la consulta '{question}'. "
            f"La métrica **{kpi_title}** acumula un total de **{formatted_total}** con una media de **{formatted_avg}**. "
            f"La entidad principal es **{top_entity}** representando **{formatted_top}** ({pct_top}% del total)."
        )

        risk = "ALTO" if pct_top > 70 else "MEDIO" if pct_top > 40 else "BAJO"

        exec_rep = ExecutiveReport(
            overview=f"Diagnóstico cuantitativo sobre '{question}': se procesaron {len(rows)} registros con un acumulado de {formatted_total} en {kpi_title}.",
            key_findings=[
                f"Volumen y dispersión: {len(rows)} registros evaluados con un promedio de {formatted_avg} por ítem.",
                f"Concentración principal: '{top_entity}' representa {formatted_top} ({pct_top}% del total acumulado).",
                f"Métrica de referencia: {kpi_title} acumula {formatted_total} con riesgo de dependencia {risk}."
            ],
            recommendations=[
                f"Paso 1 (Corto plazo, 1-15 días): Auditar las transacciones y condiciones comerciales asociadas a '{top_entity}'.",
                f"Paso 2 (Mediano plazo, 30-60 días): Establecer un plan de diversificación para equilibrar la concentración de {pct_top}% en {kpi_title}.",
                f"Paso 3 (Métrica de control): Monitorear que ningún ítem individual supere el 30% del volumen agregado en el próximo ciclo."
            ],
            risk_level=risk,
            business_impact=f"Proyección What-If: Diversificar la dependencia de '{top_entity}' reduce la exposición a caídas abruptas en {kpi_title}."
        )

        return kpis, chart_type, chart_option, summary, exec_rep

    @classmethod
    def compute_pareto_concentration(
        cls,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates Pareto concentration and top-entity share across the primary numeric column.
        Zero external dependencies, 0ms execution.
        """
        if not rows or len(rows) < 3 or not columns:
            return None

        num_col = None
        for col in columns:
            if is_true_numeric_metric(col, rows[0].get(col)):
                num_col = col
                break
        if not num_col:
            return None

        vals = sorted([float(r.get(num_col, 0) or 0) for r in rows if isinstance(r.get(num_col), (int, float))], reverse=True)
        if len(vals) < 3:
            return None
        # Una metrica admite negativos (EBITDA, variacion, profit). Si se acumulan
        # valores negativos, `top_20_sum / total` puede superar 100%: con
        # [100, -10, -10] daba 125%, y ese porcentaje imposible se escribia en el
        # informe como "concentra el 125%" con riesgo ALTO. Cuando hay negativos la
        # proporcion no es interpretable, asi que no se informa en vez de inventar.
        has_negatives = any(v < 0 for v in vals)
        total = sum(vals)
        if total <= 0 or has_negatives:
            return None

        top_20_count = max(1, int(len(vals) * 0.2))
        top_20_sum = sum(vals[:top_20_count])
        top_20_share = round((top_20_sum / total) * 100, 1)
        top_entity_share = round((vals[0] / total) * 100, 1)

        return {
            "column": num_col,
            "total": total,
            "count": len(vals),
            "top_20_count": top_20_count,
            "top_20_share": top_20_share,
            "is_concentrated": top_20_share >= 60.0,
            "top_entity_share": top_entity_share
        }

    @classmethod
    def _sanitize_kpis(
        cls,
        kpis_raw: Any,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> List[KPICard]:
        """Convierte los KPIs del modelo en tarjetas, con el VALOR calculado aca.

        Que decide el modelo y que decide el backend
        ---------------------------------------------
        El modelo elige la METRICA: que columna resume la pregunta y como se
        agrega (`column` + `agg`), mas el titulo y el subtitulo, que es donde
        aporta la lectura semantica. El valor NO lo decide el modelo: sale de las
        filas reales.

        Por que se cambio
        ----------------
        Antes el modelo escribia el numero y el backend lo publicaba tal cual. Con
        un 7B cuantizado eso produjo dos fallos que costaron codigo de
        reparacion: `normalize_llm_number` existe porque "1,234" se publicaba como
        "1.2%" (error de 1000x), y el bloque de porcentajes de este mismo metodo
        tenia que reformatear a mano los valores. Ese damage ya no es
        representable: el numero no pasa por el modelo.

        Un KPI sin `column` reconocible o sin `agg` valido se DESCARTA. No cae al
        `value` que el modelo pueda haber mandado: ese es justamente el numero
        que no se puede verificar. Si no queda ninguno, el motor conserva las
        tarjetas deterministas de `build_dynamic_visualization`, que salen de las
        mismas filas.
        """
        if not isinstance(kpis_raw, list):
            return []

        by_lower = {str(c).lower(): c for c in (columns or [])}
        parsed_kpis: List[KPICard] = []

        for k in kpis_raw[:3]:
            if not isinstance(k, dict):
                continue

            title = str(k.get("title") or "").strip()
            if not title:
                continue

            col = by_lower.get(str(k.get("column") or "").strip().lower())
            agg = str(k.get("agg") or "").strip().lower()
            if not col or agg not in KPI_AGGREGATIONS:
                continue

            value = aggregate_column(rows, col, agg)
            if value is None:
                continue

            subtitle = str(k.get("subtitle", "")).strip()
            subtitle = re.sub(
                r'^[Ee]ste KPI (?:indica|muestra|refleja|calcula)(?: la| el| los| las)?\s*',
                '', subtitle
            )
            if subtitle:
                subtitle = subtitle[0].upper() + subtitle[1:]

            parsed_kpis.append(KPICard(
                title=title,
                value=format_metric_value(col, value),
                subtitle=subtitle,
                change_direction=str(k.get("change_direction", "neutral"))
            ))

        return parsed_kpis

    @classmethod
    def _parse_executive_report_dict(cls, data: Dict[str, Any]) -> Optional[ExecutiveReport]:
        overview = str(data.get("overview", "")).strip()
        if not overview:
            return None
        findings = [str(f) for f in data.get("key_findings", []) if f]
        recs = [str(r) for r in data.get("recommendations", []) if r]
        risk = str(data.get("risk_level", "BAJO")).upper()
        if risk not in ("BAJO", "MEDIO", "ALTO", "CRITICO"):
            risk = "BAJO"
        impact = str(data.get("business_impact", "")).strip() or None
        return ExecutiveReport(
            overview=overview,
            key_findings=findings if findings else ["Análisis contextual de los datos devueltos."],
            recommendations=recs if recs else ["Monitorear periódicamente los indicadores observados."],
            risk_level=risk,
            business_impact=impact
        )

    @classmethod
    async def _generate(cls, user_prompt: str, system_prompt: str) -> str:
        """La llamada NO-stream de la sintesis, en un solo lugar.

        Existia cuatro veces identica dentro de `_run_synthesis_llm` (el camino
        normal, el stream vacio, el stream caido y el stream sin soporte). Cuatro
        copias de los mismos cuatro argumentos es la forma de que cambiar uno
        deje tres caminos con otro limite de tokens sin que nadie lo note.
        """
        return await LLMService.generate_completion(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=SYNTHESIS_MAX_TOKENS,
            temperature=SYNTHESIS_TEMPERATURE
        )

    @classmethod
    async def _run_synthesis_llm(
        cls,
        user_prompt: str,
        system_prompt: str,
        narrative_sink: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        Corre la llamada al LLM de la sintesis, con o sin stream.

        Sin `narrative_sink` es exactamente `generate_completion`: el camino que
        ya existe y que la suite cubre.

        Con `narrative_sink`, pide el texto por partes, le entrega al sink los
        pedazos de la NARRATIVA (no del JSON entero: ver `narrative_stream.py`) y
        devuelve el texto completo, que se parsea con el mismo parser de siempre.

        Si el stream se corta o no hay endpoint que lo soporte, se cae a
        `generate_completion`. El texto ya emitido se descarta porque el sink es
        "append-only hasta que llega el resultado final": el cliente reemplaza
        todo lo parcial cuando recibe la respuesta completa (ver el cliente). No
        se intenta pegar el resto del stream con una respuesta no-stream: seria
        inventar la continuacion de algo que el modelo no escribio.
        """
        if narrative_sink is None:
            return await cls._generate(user_prompt, system_prompt)

        from app.modules.chat_engine.narrative_stream import NarrativeStreamExtractor

        extractor = NarrativeStreamExtractor()
        accumulated: List[str] = []

        try:
            async for piece in LLMService.stream_completion(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=SYNTHESIS_MAX_TOKENS,
                temperature=SYNTHESIS_TEMPERATURE
            ):
                accumulated.append(piece)
                if extractor.finished:
                    continue
                delta = extractor.feed(piece)
                if delta:
                    result = narrative_sink(delta)
                    if inspect.isawaitable(result):
                        await result

            text = LLMService._clean_thinking_tags("".join(accumulated))
            if text.strip():
                return text

            # El stream sirvio una respuesta vacia: se trata como no-stream.
            return await cls._generate(user_prompt, system_prompt)
        except Exception as exc:
            # Un stream caido NO es un fallo de la consulta: el motor sigue
            # pudiendo responder por el camino que ya funcionaba. Se avisa y se
            # reintenta sin stream.
            logger.warning("Stream de sintesis interrumpido, se reintenta sin stream: %s", exc)
            return await cls._generate(user_prompt, system_prompt)

    @classmethod
    async def generate_unified_synthesis_with_llm(
        cls,
        question: str,
        user_role: str,
        rows: List[Dict[str, Any]],
        columns: List[str],
        secured_sql: str,
        conversation_context: str = "",
        is_llm_active: bool = False,
        narrative_sink: Optional[Callable[[str], Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Unified single-pass LLM inference:
        Produces conversational narrative, 3 domain-adapted KPIs, executive report,
        and 3 suggested questions in a single JSON payload.
        Implements a resilient 3-tier parser for maximum robustness.

        `narrative_sink` es opcional y, cuando viene, habilita el streaming de la
        narrativa. Es la MISMA llamada con el MISMO prompt y el MISMO parser: lo
        unico que cambia es que el texto del LLM se pide por partes y se entrega
        en crudo a `narrative_sink` a medida que llega. El texto acumulado se
        parsea igual que siempre, asi que la respuesta final es identica con o
        sin stream.

        Que no se rompa si el stream falla: cualquier excepcion cae al
        `generate_completion` de siempre. El stream es una mejora de latencia,
        nunca una condicion para poder responder.
        """
        if not rows or not is_llm_active:
            return None

        try:
            pareto_info = cls.compute_pareto_concentration(rows, columns)
            pareto_hint = ""
            if pareto_info:
                if pareto_info["is_concentrated"]:
                    pareto_hint = (
                        f"[ANÁLISIS PARETO / RIESGO CONCENTRACIÓN: El top 20% ({pareto_info['top_20_count']} de {pareto_info['count']} entidades) "
                        f"concentra el {pareto_info['top_20_share']}% de '{pareto_info['column']}'. "
                        f"La entidad principal representa el {pareto_info['top_entity_share']}%. "
                        f"Destaca esta concentración en key_findings y orienta el plan táctico a mitigar este riesgo de dependencia.]"
                    )
                else:
                    pareto_hint = (
                        f"[DISTRIBUCIÓN EQUILIBRADA: El top 20% representa el {pareto_info['top_20_share']}% de '{pareto_info['column']}'. "
                        f"Baja concentración o dependencia en entidades individuales.]"
                    )

            effective_context = f"{conversation_context}\n\n{pareto_hint}".strip() if pareto_hint else conversation_context
            system_prompt = PromptManager.get_unified_synthesis_system_prompt(user_role)
            user_prompt = PromptManager.get_unified_synthesis_user_prompt(
                question=question,
                user_role=user_role,
                rows=rows,
                columns=columns,
                secured_sql=secured_sql,
                conversation_context=effective_context
            )

            resp = await cls._run_synthesis_llm(
                user_prompt,
                system_prompt,
                narrative_sink,
            )

            if not resp:
                return None

            clean_resp = re.sub(r'^```(?:json)?\s*', '', resp.strip())
            clean_resp = re.sub(r'\s*```$', '', clean_resp.strip())

            # Tier 1 & 2: Regex JSON extraction & trailing comma cleanup
            data = None
            json_match = re.search(r'\{[\s\S]*\}', clean_resp)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except Exception:
                    cleaned_str = re.sub(r',\s*([\}\]])', r'\1', json_match.group(0))
                    try:
                        data = json.loads(cleaned_str)
                    except Exception:
                        pass

            if data and isinstance(data, dict):
                narrative = str(data.get("narrative", "")).strip() or None
                parsed_kpis = cls._sanitize_kpis(data.get("kpis", []), rows, columns)

                exec_data = data.get("executive_report")
                if isinstance(exec_data, dict):
                    exec_report = cls._parse_executive_report_dict(exec_data)
                else:
                    exec_report = cls._parse_executive_report_dict(data)

                suggested_raw = data.get("suggested_questions", [])
                suggested_questions = None
                if isinstance(suggested_raw, list):
                    clean_suggs = [re.sub(r'^[-*0-9.)\s]+', '', str(q)).strip() for q in suggested_raw if str(q).strip()]
                    suggested_questions = clean_suggs[:3] if clean_suggs else None

                return {
                    "narrative": narrative,
                    "kpis": parsed_kpis if parsed_kpis else None,
                    "executive_report": exec_report,
                    "suggested_questions": suggested_questions
                }

            # Tier 3: Resilient raw-text fallback if model returned markdown/text instead of JSON
            #
            # Con un guardia antes. Un texto que EMPEZA por `{` o por un fence
            # ```json no es prosa: es el JSON del prompt que se corto y por eso
            # no parseo. Publicarlo como `narrative` pinta en el chat
            # `{"narrative": "El total de` — literalmente media sintaxis — que es
            # peor que no tener respuesta. `None` hace que el motor caiga al
            # camino de `generate_conversational_response` (engine.py), que es
            # prosa corta y legible.
            if clean_resp and not cls._looks_like_truncated_json(clean_resp):
                return {
                    "narrative": clean_resp,
                    "kpis": None,
                    "executive_report": None,
                    "suggested_questions": None
                }

        except Exception:
            pass

        return None

    @staticmethod
    def _looks_like_truncated_json(text: str) -> bool:
        """True si el texto es un intento de JSON que no llego a cerrarse.

        El criterio es el prefijo, no la validez: si ya fuera JSON valido no
        habria llegado a este metodo. Lo que se detecta es la INTENCION de
        emitir JSON, que es lo que el prompt pide.
        """
        stripped = text.lstrip()
        return stripped.startswith("{") or stripped.startswith("```json") or stripped.startswith("```{")

    @classmethod
    def detect_statistical_anomalies(
        cls,
        rows: List[Dict[str, Any]],
        columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detects statistical outliers (|z| >= 2.0) across numeric columns using stdlib statistics,
        providing diagnostic causal notes without adding third-party dependencies (Ideas #13 & #14).
        """
        if not rows or len(rows) < 4 or not columns:
            return []

        # Find descriptive column for labeling rows (e.g. name, date, category)
        label_col = None
        for col in columns:
            col_l = col.lower()
            if not is_true_numeric_metric(col, rows[0].get(col)):
                if not col_l.startswith("id") and not col_l.endswith("_id"):
                    label_col = col
                    break
        if not label_col:
            label_col = columns[0]

        anomalies = []

        EXPLICIT_METRIC_KEYWORDS = (
            "monto", "precio", "total", "costo", "ingreso", "venta", "revenue", "price",
            "amount", "salario", "sueldo", "ganancia", "margen", "volumen", "consumo",
            "uptime", "downtime", "duracion", "tiempo", "cantidad", "score", "rating",
            "pct", "porcentaje", "toneladas", "pacientes", "visitas", "usuarios", "tasa",
            "eficiencia", "despachadas", "atendidos"
        )

        for col in columns:
            col_l = col.lower()
            if not any(k in col_l for k in EXPLICIT_METRIC_KEYWORDS):
                continue
            sample_val = rows[0].get(col)
            if not is_true_numeric_metric(col, sample_val):
                continue

            # Collect valid numeric values
            num_data = []
            for i, r in enumerate(rows):
                val = r.get(col)
                if val is not None and isinstance(val, (int, float)):
                    num_data.append((i, val, r.get(label_col, f"Fila {i+1}")))

            if len(num_data) < 4:
                continue

            values_only = [item[1] for item in num_data]
            try:
                mean_val = statistics.mean(values_only)
                stdev_val = statistics.stdev(values_only)
            except Exception:
                continue

            if stdev_val <= 0:
                continue

            for idx, val, entity_label in num_data:
                z_score = (val - mean_val) / stdev_val
                if abs(z_score) >= 2.0:
                    is_spike = z_score > 0
                    dir_str = "superior" if is_spike else "inferior"
                    anomalies.append({
                        "column": col,
                        "row_index": idx,
                        "entity": str(entity_label),
                        "value": val,
                        "mean": round(mean_val, 2),
                        "stdev": round(stdev_val, 2),
                        "z_score": round(z_score, 2),
                        "direction": "spike" if is_spike else "drop",
                        "description": (
                            f"El valor {val:,} en '{col}' ({entity_label}) es significativamente "
                            f"{dir_str} al promedio ({mean_val:,.1f})."
                        ),
                        "probable_cause": (
                            f"Desviación atípica de {abs(round(z_score, 1))}σ respecto a la media. "
                            f"Posible {'pico inusual de demanda o registro concentrado' if is_spike else 'caída crítica o interrupción de actividad'}."
                        )
                    })

        # Return top 3 most extreme anomalies
        anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)
        return anomalies[:3]

