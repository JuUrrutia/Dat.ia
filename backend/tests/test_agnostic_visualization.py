import unittest
from app.modules.chat_engine.engine import QueryEngine

class TestAgnosticVisualization(unittest.TestCase):

    def test_logistics_arbitrary_schema(self):
        """Verifica que el motor visualice esquemas totalmente arbitrarios (ej. logística) sin condicionales hardcodeadas."""
        columns = ["centro_distribucion", "toneladas_despachadas", "eficiencia_ruta_pct"]
        rows = [
            {"centro_distribucion": "CD Norte", "toneladas_despachadas": 1500.5, "eficiencia_ruta_pct": 92.4},
            {"centro_distribucion": "CD Sur", "toneladas_despachadas": 2100.0, "eficiencia_ruta_pct": 88.1},
            {"centro_distribucion": "CD Este", "toneladas_despachadas": 980.2, "eficiencia_ruta_pct": 95.0},
        ]

        kpis, chart_type, chart_option, summary, exec_rep = QueryEngine._build_dynamic_visualization(
            question="¿Cuál es el volumen despachado por centro de distribución?",
            columns=columns,
            rows=rows,
            user_role="Logística"
        )

        # Check KPIs were calculated dynamically
        self.assertEqual(len(kpis), 3)
        self.assertIn("Toneladas Despachadas", kpis[0].title)
        self.assertEqual(chart_type, "pie")  # <= 6 rows -> Pie Chart
        self.assertIn("series", chart_option)
        self.assertIsNotNone(exec_rep)
        self.assertEqual(exec_rep.risk_level, "MEDIO")  # Max CD Sur = 2100 / 4580.7 = ~45.8% -> MEDIO

    def test_time_series_arbitrary_schema(self):
        """Verifica que si existen columnas temporales, el gráfico seleccionado sea 'line'."""
        columns = ["mes", "pacientes_atendidos"]
        rows = [
            {"mes": "2026-01", "pacientes_atendidos": 120},
            {"mes": "2026-02", "pacientes_atendidos": 145},
            {"mes": "2026-03", "pacientes_atendidos": 180},
        ]

        kpis, chart_type, chart_option, summary, exec_rep = QueryEngine._build_dynamic_visualization(
            question="Evolución de pacientes atendidos por mes",
            columns=columns,
            rows=rows,
            user_role="Salud"
        )

        self.assertEqual(chart_type, "line")
        self.assertEqual(len(kpis), 3)
        self.assertIn("180", kpis[1].value)  # Valor Máximo
        self.assertIn("2026-03", kpis[1].subtitle)

    def test_kpi_sanitization_and_units(self):
        """Verifica que los KPIs limpien frases de relleno de IA y garanticen unidades.

        El modelo elige la metrica (`column` + `agg`) y el sistema calcula el
        valor, asi que la columna de porcentaje trae su '%' porque el formateo la
        reconoce, no porque el modelo lo haya escrito.
        """
        import asyncio
        from unittest.mock import patch, AsyncMock
        from app.modules.chat_engine.kpi_calculator import KPICalculator

        mock_llm_json = """{
            "overview": "Resumen ejecutivo de prueba.",
            "kpis": [
                {"title": "Toneladas Totales", "column": "toneladas_despachadas", "agg": "total", "subtitle": "Este KPI indica la cantidad total.", "change_direction": "neutral"},
                {"title": "Eficiencia Promedio", "column": "eficiencia_ruta_pct", "agg": "avg", "subtitle": "Este KPI muestra la proporción observada.", "change_direction": "neutral"},
                {"title": "Despacho Máximo", "column": "toneladas_despachadas", "agg": "max", "subtitle": "Este KPI calcula el pico de la serie.", "change_direction": "positive"}
            ],
            "key_findings": ["Hallazgo 1"],
            "recommendations": ["Recomendación 1"],
            "risk_level": "BAJO",
            "business_impact": "Impacto bajo"
        }"""

        # Sufijo `_pct` a proposito: el formateo decide la unidad leyendo el
        # NOMBRE de la columna contra PERCENTAGE_COLUMN_KEYWORDS, que es la
        # convencion que el resto del codebase ya usa. Una columna de
        # porcentajes llamada `eficiencia` se publicaria como 0.9, no como 92%.
        rows = [
            {"toneladas_despachadas": 1500.5, "eficiencia_ruta_pct": 92.4},
            {"toneladas_despachadas": 2100.0, "eficiencia_ruta_pct": 88.1},
            {"toneladas_despachadas": 980.2, "eficiencia_ruta_pct": 95.0},
        ]

        with patch("app.modules.chat_engine.llm_service.LLMService.generate_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_json
            result = asyncio.run(KPICalculator.generate_unified_synthesis_with_llm(
                question="¿Cuál es el volumen despachado?",
                user_role="Admin",
                rows=rows,
                columns=["toneladas_despachadas", "eficiencia_ruta_pct"],
                secured_sql="SELECT 1",
                is_llm_active=True
            ))
            self.assertIsNotNone(result)
            parsed_kpis = result["kpis"]
            self.assertEqual(len(parsed_kpis), 3)

            # Subtitles must be sanitized from AI filler
            self.assertNotIn("Este KPI indica", parsed_kpis[0].subtitle)
            self.assertNotIn("Este KPI muestra", parsed_kpis[1].subtitle)
            self.assertNotIn("Este KPI calcula", parsed_kpis[2].subtitle)

            # Values come from the rows: 1500.5 + 2100 + 980.2 = 4580.7
            self.assertEqual(parsed_kpis[0].value, "4,580.7")
            self.assertEqual(parsed_kpis[2].value, "2,100.0")

            # The % comes from the formatter reading the column name, not from
            # the model: it was never asked for a value at all.
            self.assertTrue(
                parsed_kpis[1].value.endswith("%"),
                f"la columna de porcentaje salio sin %: {parsed_kpis[1].value}",
            )
            self.assertEqual(parsed_kpis[1].value, "91.8%")

if __name__ == "__main__":
    unittest.main()
