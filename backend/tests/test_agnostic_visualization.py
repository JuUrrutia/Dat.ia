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
        """Verifica que los KPIs limpien frases de relleno de IA y garanticen unidades como %."""
        import asyncio
        from unittest.mock import patch, AsyncMock
        from app.modules.chat_engine.kpi_calculator import KPICalculator

        mock_llm_json = """{
            "overview": "Resumen ejecutivo de prueba.",
            "kpis": [
                {"title": "Número Total de Registros", "value": "36.4K", "subtitle": "Este KPI indica la cantidad de registros evaluados.", "change_direction": "neutral"},
                {"title": "Porcentaje de Registros", "value": "24", "subtitle": "Este KPI muestra la proporción sobre el total.", "change_direction": "neutral"},
                {"title": "Densidad de Registros", "value": "1.42M", "subtitle": "Este KPI calcula la densidad observada.", "change_direction": "positive"}
            ],
            "key_findings": ["Hallazgo 1"],
            "recommendations": ["Recomendación 1"],
            "risk_level": "BAJO",
            "business_impact": "Impacto bajo"
        }"""

        with patch("app.modules.chat_engine.llm_service.LLMService.generate_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_json
            result = asyncio.run(KPICalculator.generate_semantic_analysis_with_llm(
                question="¿Cuál es el conteo?",
                user_role="Admin",
                rows=[{"campo": 1}],
                columns=["campo"],
                secured_sql="SELECT 1",
                is_llm_active=True
            ))
            self.assertIsNotNone(result)
            parsed_kpis, overview, exec_rep = result
            self.assertEqual(len(parsed_kpis), 3)

            # Subtitles must be sanitized from AI filler
            self.assertNotIn("Este KPI indica", parsed_kpis[0].subtitle)
            self.assertNotIn("Este KPI muestra", parsed_kpis[1].subtitle)
            self.assertNotIn("Este KPI calcula", parsed_kpis[2].subtitle)

            # Percentage must have % symbol
            self.assertTrue(parsed_kpis[1].value.endswith("%"))
            self.assertEqual(parsed_kpis[1].value, "24%")

if __name__ == "__main__":
    unittest.main()
