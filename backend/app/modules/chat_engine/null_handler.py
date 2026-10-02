from typing import List, Dict, Any, Optional, Set, Tuple

class NullHandler:
    """
    Handles null detection, interactive user remediation options,
    and remediation banner formatting.
    """

    @classmethod
    def detect_remediation_intent(cls, text: str) -> Optional[str]:
        if not text:
            return None
        t_low = text.lower()
        if any(k in t_low for k in ["eliminar filas", "eliminar registros", "eliminar nulos", "quitar nulos", "delete_rows"]):
            return "delete_rows"
        if any(k in t_low for k in ["adaptar a la moda", "moda estadística", "imputar moda", "tratar nulos: moda", "a la moda"]) or ("moda" in t_low and ("nulo" in t_low or "tratar" in t_low)):
            return "mode"
        if any(k in t_low for k in ["adaptar al más cercano", "más cercano", "mas cercano", "nearest", "imputar cercano"]) or (("cercano" in t_low or "nearest" in t_low) and ("nulo" in t_low or "tratar" in t_low)):
            return "nearest"
        return None

    @classmethod
    def inspect_nulls(cls, rows: List[Dict[str, Any]]) -> Tuple[Set[str], int]:
        null_cols_in_rows = set()
        null_rows_count = 0
        for r in rows:
            row_has_null = False
            for c_name, val in r.items():
                if val is None or str(val).strip().lower() in ("none", "null"):
                    null_cols_in_rows.add(c_name)
                    row_has_null = True
            if row_has_null:
                null_rows_count += 1
        return null_cols_in_rows, null_rows_count

    @classmethod
    def build_null_alert_payload(
        cls,
        rows: List[Dict[str, Any]],
        null_cols: Set[str],
        null_rows_count: int,
        primary_table: str,
        question: str
    ) -> Tuple[Dict[str, Any], str]:
        cols_sorted = sorted(list(null_cols))
        cols_text = ", ".join(f"`{c}`" for c in cols_sorted)
        nulls_detected = {
            "has_nulls": True,
            "table_name": primary_table,
            "columns_with_nulls": cols_sorted,
            "null_rows_count": null_rows_count,
            "total_rows": len(rows),
            "options": [
                {
                    "action": "delete_rows",
                    "label": "Eliminar registros con nulos",
                    "prompt": f"Tratar nulos en {primary_table} (eliminar registros con nulos) para la consulta: {question}"
                },
                {
                    "action": "mode",
                    "label": "Adaptar a la moda",
                    "prompt": f"Tratar nulos en {primary_table} (adaptar a la moda) para la consulta: {question}"
                },
                {
                    "action": "nearest",
                    "label": "Adaptar al más cercano",
                    "prompt": f"Tratar nulos en {primary_table} (adaptar al más cercano) para la consulta: {question}"
                }
            ]
        }

        conversational = (
            f"⚠️ **Valores nulos detectados en la consulta**\n\n"
            f"Se detectaron valores nulos en la tabla `{primary_table}` (columnas: {cols_text}), "
            f"afectando a {null_rows_count} de {len(rows)} registros analizados.\n\n"
            f"Para entregarte un análisis confiable y evitar distorsiones en los resultados o gráficos "
            f"(como considerar los valores nulos como una categoría de datos), "
            f"por favor selecciona cómo deseas procesar estos registros antes de calcular la respuesta definitiva:"
        )
        return nulls_detected, conversational

    @classmethod
    def format_remediation_banner(cls, action: str, question: str) -> str:
        action_labels = {
            "delete_rows": "Eliminación de registros con nulos",
            "mode": "Adaptación a la moda estadística",
            "nearest": "Adaptación al valor más cercano"
        }
        lbl = action_labels.get(action, action)
        return f"✅ **Tratamiento de nulos ({lbl}) aplicado para responder a:** *\"{question}\"*\n\n"
