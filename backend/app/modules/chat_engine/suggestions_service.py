import re
from typing import List, Set
from app.core.prompts import PromptManager
from app.modules.chat_engine.llm_service import LLMService

class SuggestionsService:
    """
    Generates role-tailored, schema-aware natural language question suggestions
    for citizen data democratization.
    """

    @classmethod
    async def get_dynamic_suggestions_with_llm(
        cls,
        user_role: str,
        allowed_tables: Set[str],
        schema_prompt: str = ""
    ) -> List[str]:
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        try:
            system_prompt = PromptManager.get_suggestions_system_prompt()
            tables_str = ", ".join(sorted(allowed_tables))
            prompt_llm = f"""Perfil del usuario: {user_role}
Base de datos activa ({tables_str}):

{schema_prompt}

Genera 4 sugerencias simples y breves de preguntas sobre ESTA base de datos activa."""

            llm_text = await LLMService.generate_completion(
                prompt_llm,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=150
            )

            if llm_text:
                lines = [line.strip() for line in llm_text.split('\n') if line.strip()]
                clean_suggestions = []
                for line in lines:
                    line_clean = re.sub(r'^[\d\.\-\*\•\>\s]+', '', line).strip()
                    line_clean = line_clean.strip('"\'')
                    if len(line_clean) > 8 and ('?' in line_clean or '¿' in line_clean or any(k in line_clean.lower() for k in ['cuál', 'cuanto', 'mostrar', 'total', 'ventas', 'resumen', 'promedio', 'ingreso', 'costo', 'listar'])):
                        clean_suggestions.append(line_clean)
                if len(clean_suggestions) >= 2:
                    return clean_suggestions[:4]
        except Exception:
            pass

        return cls.get_dynamic_suggestions(user_role, allowed_tables, schema_prompt=schema_prompt)

    @classmethod
    def get_dynamic_suggestions(
        cls,
        user_role: str,
        allowed_tables: Set[str],
        schema_prompt: str = ""
    ) -> List[str]:
        if not allowed_tables:
            return [
                "¿Qué información puedo consultar con mi perfil?",
                "¿Cómo solicito acceso a tablas adicionales de la base de datos?"
            ]

        suggestions = []
        sorted_tables = sorted(list(allowed_tables), key=lambda t: (0 if t.lower().startswith("fact_") else 1, t.lower()))

        # Extract physical metrics & dimensions from schema_prompt
        extracted_metrics = []
        extracted_categories = []
        extracted_dates = []

        if schema_prompt:
            col_matches = re.findall(r'^\s*-\s*([a-zA-Z0-9_]+)\s*\(([^)]+)\)', schema_prompt, re.MULTILINE)
            for c_name, c_type in col_matches:
                c_low = c_name.lower()
                t_low = c_type.lower()
                if c_low in {"id", "id_tabla"} or c_low.endswith("_id") or c_low.endswith("_key"):
                    continue
                if any(m in c_low for m in ["monto", "total", "precio", "ingreso", "costo", "venta", "salario", "sueldo", "cantidad", "consumo", "cpu", "ram", "incidente", "unidades", "horas", "duracion"]) or any(it in t_low for it in ["int", "real", "float", "numeric", "decimal", "double"]):
                    extracted_metrics.append(c_name)
                elif any(d in c_low for d in ["fecha", "mes", "anio", "date", "periodo", "created_at", "timestamp"]):
                    extracted_dates.append(c_name)
                elif any(cat in c_low for cat in ["categoria", "producto", "cliente", "departamento", "region", "sucursal", "canal", "tipo", "estado", "ciudad", "pais", "marca", "servidor", "usuario", "proveedor"]):
                    extracted_categories.append(c_name)

        clean_table_names = []
        for tbl in sorted_tables:
            clean_name = tbl
            for prefix in ["fact_", "dim_", "tbl_", "table_"]:
                if clean_name.lower().startswith(prefix):
                    clean_name = clean_name[len(prefix):]
                    break
            clean_table_names.append((tbl, clean_name.replace("_", " ").strip()))

        # If metrics and categories exist
        if extracted_metrics and (extracted_categories or clean_table_names):
            best_metric = extracted_metrics[0].replace("_", " ").strip()
            best_cat = (extracted_categories[0].replace("_", " ").strip()) if extracted_categories else clean_table_names[0][1]
            primary_tbl = clean_table_names[0][1]

            suggestions.append(f"📊 ¿Cuál es el total de {best_metric} agrupado por {best_cat}?")
            suggestions.append(f"📈 Top 5 {best_cat} con mayor {best_metric}")
            if extracted_dates:
                best_date = extracted_dates[0].replace("_", " ").strip()
                suggestions.append(f"📅 Evolución temporal de {best_metric} por {best_date}")
            elif len(extracted_metrics) > 1:
                sec_metric = extracted_metrics[1].replace("_", " ").strip()
                suggestions.append(f"⚡ Comparativa de {best_metric} y {sec_metric} en {primary_tbl}")
            else:
                suggestions.append(f"🔍 Promedio y registros destacados de {best_metric} en {primary_tbl}")

            if len(clean_table_names) > 1:
                sec_tbl = clean_table_names[1][1]
                suggestions.append(f"💡 Resumen consolidado y principales indicadores de {sec_tbl}")
            else:
                suggestions.append(f"📋 Desglose detallado y análisis de {primary_tbl}")

        # Fallback table-based templates
        if len(suggestions) < 4:
            templates = [
                "📊 Distribución y resumen de registros en {name}",
                "📈 Métricas acumuladas y evolución en {name}",
                "📋 Listado detallado y consulta de {name}",
                "💡 Indicadores clave y registros principales de {name}"
            ]

            for i, (orig_tbl, clean_spaced) in enumerate(clean_table_names):
                tmpl = templates[i % len(templates)]
                suggestions.append(tmpl.format(name=clean_spaced))

                if len(clean_table_names) == 1:
                    suggestions.append(f"🔍 Top registros con mayores valores en {clean_spaced}")
                    suggestions.append(f"⚡ Totales agregados y promedio general de {clean_spaced}")

        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique[:4]
