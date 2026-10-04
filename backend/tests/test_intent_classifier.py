import unittest

from app.modules.chat_engine.intent_classifier import IntentClassifier


class TestGreetingBeforeDataRequest(unittest.IsolatedAsyncioTestCase):
    """Los saludos/agradecimientos no pueden disparar el pipeline SQL."""

    async def test_thanks_with_data_word_is_not_data_analysis(self):
        for q in [
            "Gracias, ya tengo los datos",
            "Perfecto, esos registros me sirven",
            "Gracias, revisaré el total después",
        ]:
            with self.subTest(q=q):
                self.assertNotEqual(
                    await IntentClassifier.classify_intent(q), "data_analysis"
                )

    async def test_greeting_with_real_request_is_still_data_analysis(self):
        for q in [
            "Hola, ¿cuántas ventas hubo?",
            "Hola, quiero ver las ventas de enero",
            "Hola, muéstrame el total de clientes",
        ]:
            with self.subTest(q=q):
                self.assertEqual(
                    await IntentClassifier.classify_intent(q), "data_analysis"
                )

    async def test_plain_greetings_still_greeting(self):
        for q in ["Hola", "Hola DATIA, buenos días", "Gracias!", "qué puedes hacer"]:
            with self.subTest(q=q):
                self.assertEqual(
                    await IntentClassifier.classify_intent(q), "greeting"
                )

    async def test_explanation_still_wins_over_greeting(self):
        self.assertEqual(
            await IntentClassifier.classify_intent("Hola, explícame qué es el margen"),
            "explanation",
        )


class TestChipsRespectAllowedTables(unittest.TestCase):
    """No se sugieren consultas que el rol no puede ejecutar."""

    def test_salary_chip_blocked_without_dim_empleados(self):
        opts = IntentClassifier.detect_ambiguity_and_options(
            "empleados", {"fact_ventas", "dim_clientes"}
        )
        self.assertEqual(opts, [])

    def test_no_chip_mentions_salary_for_any_role(self):
        for tables in (None, set(), {"dim_empleados"}, {"dim_empleados", "fact_ventas"}):
            with self.subTest(tables=tables):
                opts = IntentClassifier.detect_ambiguity_and_options("empleados", tables)
                self.assertFalse([o for o in opts if "salar" in o.lower()], opts)

    def test_employee_chips_returned_for_roles_with_dim_empleados(self):
        opts = IntentClassifier.detect_ambiguity_and_options(
            "personal", {"dim_empleados", "fact_ventas"}
        )
        self.assertGreaterEqual(len(opts), 3)

    def test_cross_table_chips_filtered(self):
        # fact_ventas sola no alcanza para el chip que cruza dim_clientes
        opts = IntentClassifier.detect_ambiguity_and_options("ventas", {"fact_ventas"})
        self.assertTrue(opts)
        self.assertFalse([o for o in opts if "clientes" in o.lower() or "productos" in o.lower()], opts)

    def test_missing_allowed_tables_does_not_break(self):
        self.assertGreaterEqual(len(IntentClassifier.detect_ambiguity_and_options("ventas")), 3)
        self.assertGreaterEqual(len(IntentClassifier.detect_ambiguity_and_options("ventas", set())), 3)
        self.assertGreaterEqual(len(IntentClassifier.detect_ambiguity_and_options("clientes")), 3)
        self.assertEqual(IntentClassifier.detect_ambiguity_and_options("ventas de enero 2026"), [])

    def test_detect_ambiguity_and_options(self):
        # Consulta amplia y ambigua: tiene que ofrecer el desglose de "total"
        # y las preguntas de desambiguacion.
        options = IntentClassifier.detect_ambiguity_and_options("ventas")
        self.assertGreaterEqual(len(options), 3)
        self.assertTrue(any("total" in opt.lower() for opt in options))

        options_clients = IntentClassifier.detect_ambiguity_and_options("clientes")
        self.assertGreaterEqual(len(options_clients), 3)

        # Una consulta ya especifica NO es ambigua.
        specific_options = IntentClassifier.detect_ambiguity_and_options("ventas totales de enero 2026 en sucursal centro")
        self.assertEqual(len(specific_options), 0)


if __name__ == "__main__":
    unittest.main()