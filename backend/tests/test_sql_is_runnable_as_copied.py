"""El SQL que el producto entrega tiene que ser ejecutable tal cual.

Bug: `sqlglot` emite la sentencia sin terminador. El panel de trazabilidad la
muestra y la deja copiar, y al pegarla en un psql interactivo queda en bucle
esperando `;`: no imprime filas, ni `(0 rows)`, ni error, solo el prompt de
vuelta. Se lee como "no hay datos" cuando en realidad la consulta nunca corrio.

Se fija en el validador (no en el boton de copiar) porque la verificacion a mano
ocurre sobre `audit_logs`, la trazabilidad y los exports, y los tresorterian el
mismo texto.
"""
import unittest

from app.modules.chat_engine.ast_validator import ASTValidator


class TestSqlIsExecutableAsCopied(unittest.TestCase):

    def _secure(self, sql, tables, dialect="postgres"):
        ok, secured, meta = ASTValidator.validate_and_secure_sql(
            sql, dialect=dialect, allowed_tables=tables,
            blocked_columns=set(), table_columns={t: [] for t in tables},
            is_admin=False,
        )
        self.assertTrue(ok)
        return secured

    # ------------------------------------------------------------------
    def test_generated_sql_ends_with_terminator(self):
        secured = self._secure(
            "SELECT periodo, COUNT(*) FROM movimientos GROUP BY periodo LIMIT 500",
            {"movimientos"},
        )
        self.assertTrue(
            secured.rstrip().endswith(";"),
            f"El SQL copiado tiene que terminar en ';': {secured!r}",
        )

    def test_existing_terminator_is_not_doubled(self):
        secured = self._secure(
            "SELECT periodo FROM movimientos LIMIT 500;",
            {"movimientos"},
        )
        self.assertFalse(secured.rstrip().endswith(";;"), secured)
        self.assertEqual(secured.count(";"), 1)

    def test_sqlite_dialect_also_terminated(self):
        secured = self._secure(
            "SELECT valor FROM datos LIMIT 500",
            {"datos"},
            dialect="sqlite",
        )
        self.assertTrue(secured.rstrip().endswith(";"), secured)

    def test_terminator_survives_trailing_whitespace(self):
        secured = self._secure(
            "SELECT periodo FROM movimientos LIMIT 500",
            {"movimientos"},
        )
        self.assertNotIn("; ", secured[-3:], f"espacio despues del ';': {secured!r}")
        self.assertEqual(secured, secured.rstrip())


if __name__ == "__main__":
    unittest.main()