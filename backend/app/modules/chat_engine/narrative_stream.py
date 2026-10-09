"""
Extractor incremental del campo `narrative` de la respuesta JSON del LLM.

Por que existe
--------------
La tercera llamada al LLM (`KPICalculator.generate_unified_synthesis_with_llm`)
NO devuelve prosa: devuelve un objeto JSON con `narrative`, `kpis`,
`executive_report` y `suggested_questions` (ver `kpi_calculator.py:458-479`).
Emitir los tokens crudos al navegador pintaria literally `{"narrative": "El
total de` en el chat.

Este extractor camina el texto parcial, encuentra el valor del campo
`narrative` y devuelve SOLO su contenido, ya des-escapado, a medida que llega.
El prompt (`prompts.py:411`) pide `narrative` como primer campo, asi que en la
practica aparece de inmediato.

Que NO hace, a proposito
------------------------
- No inventa texto. Si el modelo no emite el campo, no emite nada: el reloj de
  la parte 1 cubre la espera honestamente.
- No reordena ni reescribe. Lo que entrega es el mismo texto que despues viaja
  en `conversational_response` de la respuesta completa.
- No es un parser de JSON. No intenta cerrar el objeto ni validar claves: solo
  extrae una string, que es lo unico que se puede hacer sobre un stream parcial
  sin inventar.
"""

import re

# Secuencias de escape JSON dentro de una string. Es la lista de la spec, no una
# seleccion: un `\q` invalido no deberia romper la extraccion, y por eso el
# fallback de abajo devuelve el caracter tal cual.
_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "b": "\b",
    "f": "\f",
    '"': '"',
    "\\": "\\",
    "/": "/",
}

# Cuantos caracteres del buffer se retienen mientras se busca la clave. Tiene que
# ser >= len('"narrative"') = 12 para el caso de que el stream corte la clave a
# mitad; 64 da margen de sobra sin retener texto util.
_SEARCH_TAIL = 64


class NarrativeStreamExtractor:
    """Extrae el campo `narrative` de un JSON que llega por partes.

    Se usa como ``extractor.feed(chunk)``, que devuelve el texto nuevo ya
    des-escapado (posiblemente `""` si todavia no habia nada que entregar).
    ``finished`` pasa a True cuando la string del campo se cerro, y a partir de
    ahi `feed` no devuelve mas: el resto del JSON (kpis, informe, preguntas) no
    es narrativa y no le interesa a quien esta leyendo.
    """

    # Tolera espacios entre la clave, el dos puntos y la comilla inicial, y el
    # orden real de las claves del modelo (no asume que `narrative` sea la
    # primera: si aparece tercera, tambien funciona).
    _KEY_RE = re.compile(r'"narrative"\s*:\s*"')

    def __init__(self) -> None:
        self._buf = ""
        # seeking -> leyendo el cuerpo de la string -> done
        self._state = "seeking"

    @property
    def finished(self) -> bool:
        return self._state == "done"

    def feed(self, chunk: str) -> str:
        """Alimenta un fragmento y devuelve la narrativa nueva, ya des-escapada."""
        if self._state == "done":
            return ""

        self._buf += chunk

        if self._state == "seeking":
            match = self._KEY_RE.search(self._buf)
            if not match:
                # La clave puede estar partida entre chunks: se retiene una cola
                # en vez de descartar el buffer entero.
                if len(self._buf) > _SEARCH_TAIL:
                    self._buf = self._buf[-_SEARCH_TAIL:]
                return ""
            self._buf = self._buf[match.end():]
            self._state = "body"

        return self._drain_body()

    def _drain_body(self) -> str:
        buf = self._buf
        out = []
        i = 0
        n = len(buf)

        while i < n:
            ch = buf[i]

            if ch == "\\":
                rest = buf[i + 1:]
                if not rest:
                    # Escape cortado a mitad de chunk: se espera al siguiente.
                    break

                esc = rest[0]
                if esc == "u":
                    hex_digits = rest[1:5]
                    if len(hex_digits) < 4:
                        # \u incompleto todavia.
                        break
                    code = self._safe_hex(hex_digits)
                    if code is None:
                        out.append("u")
                    else:
                        char = chr(code)
                        # Un surrogate suelto (0xD800-0xDFFF) no es un caracter
                        # que se pueda mandar en JSON: son los bytes de UTF-16 de
                        # un emoji que el modelo partio en dos escapes. Se
                        # descarta en vez de romper el encoding del evento SSE.
                        if not 0xD800 <= code <= 0xDFFF:
                            out.append(char)
                    i += 6
                    continue

                out.append(_ESCAPES.get(esc, esc))
                i += 2
                continue

            if ch == '"':
                # Fin de la string del campo narrative.
                self._state = "done"
                self._buf = ""
                return "".join(out)

            out.append(ch)
            i += 1

        self._buf = buf[i:]
        return "".join(out)

    @staticmethod
    def _safe_hex(digits: str):
        try:
            return int(digits, 16)
        except ValueError:
            return None