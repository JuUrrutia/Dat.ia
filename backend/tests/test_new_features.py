import unittest
import time
from app.modules.chat_engine.kpi_calculator import KPICalculator
from app.modules.chat_engine.intent_classifier import IntentClassifier
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.core.prompts import PromptManager

class TestNewFeatures(unittest.TestCase):

    def test_detect_statistical_anomalies_and_causes(self):
        # 10 rows, one extreme outlier
        rows = [
            {"sucursal": "Centro", "monto": 100},
            {"sucursal": "Norte", "monto": 105},
            {"sucursal": "Sur", "monto": 98},
            {"sucursal": "Este", "monto": 102},
            {"sucursal": "Oeste", "monto": 101},
            {"sucursal": "Aeropuerto", "monto": 99},
            {"sucursal": "Puerto", "monto": 103},
            {"sucursal": "Mall", "monto": 1000},  # Extreme spike
            {"sucursal": "Plaza", "monto": 97},
            {"sucursal": "Parque", "monto": 102}
        ]
        columns = ["sucursal", "monto"]

        anomalies = KPICalculator.detect_statistical_anomalies(rows, columns)
        self.assertGreaterEqual(len(anomalies), 1)
        spike = anomalies[0]
        self.assertEqual(spike["column"], "monto")
        self.assertEqual(spike["entity"], "Mall")
        self.assertEqual(spike["value"], 1000)
        self.assertEqual(spike["direction"], "spike")
        self.assertIn("Mall", spike["description"])
        self.assertIn("Desviación atípica", spike["probable_cause"])

    def test_detect_ambiguity_and_options(self):
        # Broad ambiguous query
        options = IntentClassifier.detect_ambiguity_and_options("ventas")
        self.assertGreaterEqual(len(options), 3)
        self.assertTrue(any("total" in opt.lower() for opt in options))

        options_clients = IntentClassifier.detect_ambiguity_and_options("clientes")
        self.assertGreaterEqual(len(options_clients), 3)

        # Specific query should NOT be ambiguous
        specific_options = IntentClassifier.detect_ambiguity_and_options("ventas totales de enero 2026 en sucursal centro")
        self.assertEqual(len(specific_options), 0)

    def test_schema_cache_ttl_and_invalidation(self):
        # Clear cache first
        DynamicSchemaPruningService.invalidate_schema_cache()
        self.assertEqual(len(DynamicSchemaPruningService._schema_cache), 0)

        # Manually seed a dummy cache entry
        key = "1:1:Economista:False"
        dummy_result = {"schema_prompt": "Prompt Test", "allowed_tables": {"fact_ventas"}, "blocked_columns": set()}
        DynamicSchemaPruningService._schema_cache[key] = (time.time(), dummy_result)

        self.assertIn(key, DynamicSchemaPruningService._schema_cache)
        
        # Test selective invalidation
        DynamicSchemaPruningService.invalidate_schema_cache(connection_id=1)
        self.assertNotIn(key, DynamicSchemaPruningService._schema_cache)

    def test_prompts_have_pyramid_and_badges(self):
        prompt = PromptManager.get_data_analysis_conversational_system_prompt("Economista")
        self.assertIn("PIRAMIDAL", prompt.upper())
        self.assertIn("[OPORTUNIDAD]", prompt)
        self.assertIn("[RIESGO]", prompt)
        self.assertIn("[ESTABLE]", prompt)
        self.assertIn("<preguntas_sugeridas>", prompt)

if __name__ == "__main__":
    unittest.main()
