import json
import re
import statistics
from typing import List, Dict, Any, Tuple, Optional
from app.core.constants import DATE_COLUMN_KEYWORDS, CURRENCY_COLUMN_KEYWORDS, PERCENTAGE_COLUMN_KEYWORDS
from app.core.prompts import PromptManager
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.schemas import KPICard, ExecutiveReport

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
    ) -> Tuple[List[KPICard], str, Dict[str, Any], str, Optional[ExecutiveReport], List[Any]]:
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
        total = sum(vals)
        if total <= 0:
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
    def _sanitize_kpis(cls, kpis_raw: Any) -> List[KPICard]:
        parsed_kpis: List[KPICard] = []
        if isinstance(kpis_raw, list):
            for k in kpis_raw[:3]:
                if isinstance(k, dict) and k.get("title") and k.get("value"):
                    raw_title = str(k["title"]).strip()
                    raw_val = str(k["value"]).strip()
                    raw_sub = str(k.get("subtitle", "")).strip()

                    # Strip AI filler boilerplate from subtitle
                    raw_sub = re.sub(r'^[Ee]ste KPI (?:indica|muestra|refleja|calcula)(?: la| el| los| las)?\s*', '', raw_sub)
                    if raw_sub:
                        raw_sub = raw_sub[0].upper() + raw_sub[1:]

                    # If percentage title but raw number without %, format it
                    if any(p in raw_title.lower() for p in ('porcentaje', 'tasa', 'ratio', 'pct')) and '%' not in raw_val and '$' not in raw_val:
                        try:
                            num = float(raw_val.replace(',', '.'))
                            if 0 < num <= 1:
                                raw_val = f"{num * 100:.1f}%"
                            else:
                                raw_val = f"{num:.1f}%" if num % 1 != 0 else f"{int(num)}%"
                        except Exception:
                            raw_val = f"{raw_val}%"

                    parsed_kpis.append(KPICard(
                        title=raw_title,
                        value=raw_val,
                        subtitle=raw_sub,
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
    async def generate_unified_synthesis_with_llm(
        cls,
        question: str,
        user_role: str,
        rows: List[Dict[str, Any]],
        columns: List[str],
        secured_sql: str,
        conversation_context: str = "",
        is_llm_active: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Unified single-pass LLM inference:
        Produces conversational narrative, 3 domain-adapted KPIs, executive report,
        and 3 suggested questions in a single JSON payload.
        Implements a resilient 3-tier parser for maximum robustness.
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

            resp = await LLMService.generate_completion(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.15
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
                parsed_kpis = cls._sanitize_kpis(data.get("kpis", []))

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
                    "kpis": parsed_kpis if len(parsed_kpis) == 3 else None,
                    "executive_report": exec_report,
                    "suggested_questions": suggested_questions
                }

            # Tier 3: Resilient raw-text fallback if model returned markdown/text instead of JSON
            if clean_resp:
                return {
                    "narrative": clean_resp,
                    "kpis": None,
                    "executive_report": None,
                    "suggested_questions": None
                }

        except Exception:
            pass

        return None

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
                    parsed_kpis = cls._sanitize_kpis(data.get("kpis", []))
                    exec_report = cls._parse_executive_report_dict(data)

                    if overview and len(parsed_kpis) == 3 and exec_report:
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
                    return cls._parse_executive_report_dict(data)
        except Exception:
            pass
        return None

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

