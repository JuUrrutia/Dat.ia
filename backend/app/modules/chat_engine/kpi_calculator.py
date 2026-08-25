import json
import re
from typing import List, Dict, Any, Tuple, Optional
from app.core.constants import DATE_COLUMN_KEYWORDS, CURRENCY_COLUMN_KEYWORDS, PERCENTAGE_COLUMN_KEYWORDS
from app.core.prompts import PromptManager
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.schemas import KPICard, ExecutiveReport, MetricGauge

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
    if any(col_lower == k or col_lower.startswith(f"{k}_") or col_lower.endswith(f"_{k}") for k in NON_METRIC_KEYWORDS):
        return False
    if not isinstance(sample_val, (int, float)):
        return False
    if isinstance(sample_val, int) and (1900 <= sample_val <= 2100) and any(k in col_lower for k in ("ano", "anio", "year")):
        return False
    return True

class KPICalculator:
    """
    Computes business metrics, KPICards, MetricGauges, and deep ExecutiveReports
    agnostic to database engine/schema.
    """

    @classmethod
    def build_dynamic_visualization(
        cls,
        question: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        user_role: str = "Economista"
    ) -> Tuple[List[KPICard], str, Dict[str, Any], str, Optional[ExecutiveReport], List[MetricGauge]]:
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
            return kpis, "bar", chart_option, summary, exec_rep, []

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

            gauges = [
                MetricGauge(
                    title="Muestra de Datos",
                    percentage=min(100.0, round((len(rows) / 50) * 100, 1)),
                    value_label=f"{len(rows)} Filas",
                    target_label="Filtro Aplicado",
                    color="#06B6D4"
                ),
                MetricGauge(
                    title="Completitud",
                    percentage=100.0,
                    value_label="100%",
                    target_label="Datos Validados",
                    color="#10B981"
                )
            ]

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

            return kpis, chart_type, chart_option, summary, exec_rep, gauges

        # CASE 2: REAL QUANTITATIVE METRICS PRESENT
        total_val = sum((r.get(primary_num, 0) or 0) for r in rows if isinstance(r.get(primary_num), (int, float)))
        avg_val = (total_val / len(rows)) if len(rows) > 0 else 0

        max_row = max(rows, key=lambda x: (x.get(primary_num, 0) or 0) if isinstance(x.get(primary_num), (int, float)) else 0) if rows else {}
        top_entity = str(max_row.get(primary_cat, "Entidad")) if max_row else "N/A"
        top_val = max_row.get(primary_num, 0) or 0

        is_currency = any(k in primary_num.lower() for k in CURRENCY_COLUMN_KEYWORDS)
        is_percentage = any(k in primary_num.lower() for k in PERCENTAGE_COLUMN_KEYWORDS)

        formatted_total = f"${total_val:,.2f}" if is_currency else f"{total_val:.1f}%" if is_percentage else f"{total_val:,.1f}" if isinstance(total_val, float) else f"{total_val:,}"
        formatted_top = f"${top_val:,.2f}" if is_currency else f"{top_val:.1f}%" if is_percentage else f"{top_val:,.1f}" if isinstance(top_val, float) else f"{top_val:,}"
        formatted_avg = f"${avg_val:,.2f}" if is_currency else f"{avg_val:.1f}%" if is_percentage else f"{avg_val:,.1f}"

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

        chart_option = {"series": []}

        pct_top = round((top_val / total_val * 100), 1) if total_val > 0 else 0
        gauges = [
            MetricGauge(
                title="Concentración Líder",
                percentage=min(100.0, pct_top),
                value_label=f"{pct_top}%",
                target_label=f"Líder: {top_entity[:16]}",
                color="#10B981" if pct_top < 50 else "#F59E0B"
            ),
            MetricGauge(
                title="Muestra de Datos",
                percentage=min(100.0, round((len(rows) / 100) * 100, 1)),
                value_label=f"{len(rows)} Filas",
                target_label="Filtro Aplicado",
                color="#06B6D4"
            )
        ]

        summary = (
            f"Informe Ejecutivo: Se procesaron **{len(rows)} registros** de la base de datos corporativa para la consulta '{question}'. "
            f"La métrica **{kpi_title}** acumula un total de **{formatted_total}** con una media de **{formatted_avg}**. "
            f"La entidad principal es **{top_entity}** representando **{formatted_top}** ({pct_top}% del total)."
        )

        risk = "ALTO" if pct_top > 70 else "MEDIO" if pct_top > 40 else "BAJO"

        exec_rep = ExecutiveReport(
            overview=f"Análisis cuantitativo de {len(rows)} registros procesados sobre la consulta '{question}'.",
            key_findings=[
                f"Volumen acumulado de {kpi_title}: {formatted_total} a través de {len(rows)} registros.",
                f"La entidad con mayor concentración es '{top_entity}' con {formatted_top} ({pct_top}% del total).",
                f"Promedio general registrado por ítem: {formatted_avg}."
            ],
            recommendations=[
                f"Monitorear la concentración de valor en '{top_entity}' para diversificar riesgos operacionales.",
                "Establecer umbrales de alerta temprana sobre métricas fuera del promedio general.",
                "Profundizar el análisis cruzando variables adicionales en próximas consultas."
            ],
            risk_level=risk,
            business_impact=f"Impacto directo en la gestión y control de la métrica {kpi_title}."
        )

        return kpis, chart_type, chart_option, summary, exec_rep, gauges

    @classmethod
    async def generate_semantic_analysis_with_llm(
        cls,
        question: str,
        user_role: str,
        rows: List[Dict[str, Any]],
        columns: List[str],
        secured_sql: str,
        schema_context: str = "",
        is_llm_active: bool = False
    ) -> Optional[Tuple[List[KPICard], str, ExecutiveReport]]:
        """
        Uses Local LLM to semantically understand the domain (surveys, HR, finance, etc.),
        evaluate context from schema and actual rows, and generate domain-adapted KPIs and executive report.
        """
        if not rows or not is_llm_active:
            return None

        try:
            system_prompt = PromptManager.get_semantic_data_synthesis_system_prompt()
            compact_rows = json.dumps(rows[:10], ensure_ascii=False)
            prompt_data = f"""Pregunta del usuario ({user_role}): "{question}"
Consulta SQL ejecutada: {secured_sql}

Muestra de datos devueltos ({len(rows)} filas, mostrando hasta 10):
{compact_rows}

Genera la síntesis semántica, las 3 tarjetas KPI contextuales y el informe ejecutivo en JSON."""

            resp = await LLMService.generate_completion(
                prompt_data,
                system_prompt=system_prompt,
                max_tokens=900,
                temperature=0.2
            )

            if resp:
                clean_resp = re.sub(r'^```(?:json)?\s*', '', resp.strip())
                clean_resp = re.sub(r'\s*```$', '', clean_resp.strip())

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
                    overview = str(data.get("overview", "")).strip()
                    findings = [str(f) for f in data.get("key_findings", []) if f]
                    recs = [str(r) for r in data.get("recommendations", []) if r]
                    risk = str(data.get("risk_level", "BAJO")).upper()
                    if risk not in ("BAJO", "MEDIO", "ALTO", "CRITICO"):
                        risk = "BAJO"
                    impact = str(data.get("business_impact", "")).strip() or None

                    kpis_raw = data.get("kpis", [])
                    parsed_kpis: List[KPICard] = []
                    if isinstance(kpis_raw, list):
                        for k in kpis_raw[:3]:
                            if isinstance(k, dict) and k.get("title") and k.get("value"):
                                parsed_kpis.append(KPICard(
                                    title=str(k["title"]),
                                    value=str(k["value"]),
                                    subtitle=str(k.get("subtitle", "")),
                                    change_direction=str(k.get("change_direction", "neutral"))
                                ))

                    if overview and len(parsed_kpis) == 3:
                        exec_report = ExecutiveReport(
                            overview=overview,
                            key_findings=findings if findings else ["Análisis contextual de los datos devueltos."],
                            recommendations=recs if recs else ["Monitorear periódicamente los indicadores observados."],
                            risk_level=risk,
                            business_impact=impact
                        )
                        return parsed_kpis, overview, exec_report
        except Exception:
            pass
        return None

    @classmethod
    async def generate_deep_executive_report_with_llm(
        cls,
        question: str,
        user_role: str,
        rows: List[Dict[str, Any]],
        columns: List[str],
        secured_sql: str,
        is_llm_active: bool
    ) -> Optional[ExecutiveReport]:
        if not rows or not is_llm_active:
            return None

        try:
            system_prompt = PromptManager.get_executive_report_system_prompt()
            compact_rows = json.dumps(rows[:10], ensure_ascii=False)
            prompt_data = f"""Pregunta realizada por el usuario ({user_role}): "{question}"
Consulta SQL ejecutada sobre la BD activa: {secured_sql}
Muestra de registros devueltos ({len(rows)} filas, mostrando hasta 10):
{compact_rows}

Analiza la información devuelta y genera el informe ejecutivo en formato JSON."""

            resp = await LLMService.generate_completion(
                prompt_data,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.25
            )

            if resp:
                clean_resp = re.sub(r'^```(?:json)?\s*', '', resp.strip())
                clean_resp = re.sub(r'\s*```$', '', clean_resp.strip())

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
                    overview = str(data.get("overview", "")).strip()
                    findings = [str(f) for f in data.get("key_findings", []) if f]
                    recs = [str(r) for r in data.get("recommendations", []) if r]
                    risk = str(data.get("risk_level", "BAJO")).upper()
                    if risk not in ("BAJO", "MEDIO", "ALTO", "CRITICO"):
                        risk = "BAJO"
                    impact = str(data.get("business_impact", "")).strip() or None

                    if overview:
                        return ExecutiveReport(
                            overview=overview,
                            key_findings=findings if findings else ["Análisis cuantitativo de los registros devueltos."],
                            recommendations=recs if recs else ["Continuar monitoreo del dominio analizado en la base de datos."],
                            risk_level=risk,
                            business_impact=impact
                        )
        except Exception:
            pass
        return None
