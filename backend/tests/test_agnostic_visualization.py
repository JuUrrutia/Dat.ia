import unittest
from app.services.query_engine import QueryEngine

class TestAgnosticVisualization(unittest.TestCase):

    def test_logistics_arbitrary_schema(self):
        """Verifica que el motor visualice esquemas totalmente arbitrarios (ej. logística) sin condicionales hardcodeadas."""
        columns = ["centro_distribucion", "toneladas_despachadas", "eficiencia_ruta_pct"]
        rows = [
            {"centro_distribucion": "CD Norte", "toneladas_despachadas": 1500.5, "eficiencia_ruta_pct": 92.4},
            {"centro_distribucion": "CD Sur", "toneladas_despachadas": 2100.0, "eficiencia_ruta_pct": 88.1},
            {"centro_distribucion": "CD Este", "toneladas_despachadas": 980.2, "eficiencia_ruta_pct": 95.0},
        ]

        kpis, chart_type, chart_option, summary, exec_rep, gauges = QueryEngine._build_dynamic_visualization(
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

        kpis, chart_type, chart_option, summary, exec_rep, gauges = QueryEngine._build_dynamic_visualization(
            question="Evolución de pacientes atendidos por mes",
            columns=columns,
            rows=rows,
            user_role="Salud"
        )

        self.assertEqual(chart_type, "line")
        self.assertEqual(len(kpis), 3)
        self.assertIn("180", kpis[1].value)  # Valor Máximo
        self.assertIn("2026-03", kpis[1].subtitle)

if __name__ == "__main__":
    unittest.main()
