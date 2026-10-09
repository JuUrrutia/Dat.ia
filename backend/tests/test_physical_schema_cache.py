"""La introspeccion fisica del esquema se cachea; el prompt del LLM no.

Por que este cache existe
-------------------------
`get_physical_db_tables` y `get_physical_table_columns` abren una conexion nueva
(o un `create_engine` + `dispose()` contra el Postgres del cliente) EN CADA
llamada. Medido en un `POST /chat/query` con 10 tablas permitidas: ~30
aperturas, y todo dentro de un `async def`, o sea bloqueando el event loop.

Lo que NO se puede cachear
--------------------------
`_schema_cache` (el prompt ya armado) tiene el texto de la pregunta en la key, y
eso es intencional: el ranking de tablas depende de la pregunta. Aqui lo que se
cachea es la introscpeccion, que no depende de ella.

Lo que este test protege
------------------------
1. La entrada cacheada devuelve lo mismo que la calculada, y `include_samples`
   NO se confunde entre si (el prompt pide muestras, el ranking no).
2. `invalidate_schema_cache` limpia la introscpeccion: un DDL nuevo o una tabla
   subida tienen que verse, no esperar 10 minutos.
3. Un resultado VACIO no se cachea. Sin esto, un Postgres caido 30 s se
   convierte en 10 minutos de "esta base no tiene tablas" para todo el mundo.
   Es el mismo criterio de `SchemaIntrospectionError`: no se pudo leer != vacio.
"""

import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService as S


def _make_sqlite():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE ventas (id INTEGER, monto REAL, region TEXT)')
    conn.execute('CREATE TABLE precios (sku TEXT, valor REAL)')
    # Con filas: `include_samples=True` lee `SELECT * ... LIMIT 20`, y una tabla
    # vacia no distingue el cache de "no hay cache" porque las dos dan [].
    conn.executemany(
        'INSERT INTO ventas (id, monto, region) VALUES (?, ?, ?)',
        [(1, 100.0, "Norte"), (2, 250.5, "Sur"), (3, 75.25, "Norte")],
    )
    conn.commit()
    conn.close()
    return path


class TestPhysicalSchemaCache(unittest.TestCase):
    def setUp(self):
        self.path = _make_sqlite()
        S.invalidate_schema_cache()

    def tearDown(self):
        S.invalidate_schema_cache()

    def test_tables_cache_returns_same_result_and_invalidates(self):
        first = S.get_physical_db_tables(self.path)
        self.assertEqual(first, {"ventas", "precios"})

        # El hit de cache tiene que devolver un set NUEVO: el llamador lo usa
        # como `physical_tables` y lo deriva con operaciones de conjunto, y un
        # set cacheado mutado en el sitio envenena a todos los request
        # siguientes.
        cached = S.get_physical_db_tables(self.path)
        self.assertEqual(first, cached)
        self.assertIsNot(first, cached)
        cached.add("tabla_inventada")
        self.assertNotIn("tabla_inventada", S.get_physical_db_tables(self.path))

        # Un DDL nuevo no espera al TTL.
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE clientes (rut TEXT)")
        conn.commit()
        conn.close()
        self.assertNotIn("clientes", S.get_physical_db_tables(self.path))
        S.invalidate_schema_cache()
        self.assertIn("clientes", S.get_physical_db_tables(self.path))

    def test_columns_cache_respects_include_samples(self):
        sin_muestras = S.get_physical_table_columns("ventas", self.path, include_samples=False)
        con_muestras = S.get_physical_table_columns("ventas", self.path, include_samples=True)

        # Los nombres coinciden; el contenido de `samples` NO puede cruzarse.
        # El prompt del LLM pide muestras y el ranking de tablas no: si
        # compartieran entrada, el prompt recibiria valores que el llamador pidio
        # no leer.
        self.assertEqual([c["name"] for c in sin_muestras], ["id", "monto", "region"])
        self.assertEqual([c["name"] for c in con_muestras], ["id", "monto", "region"])
        self.assertEqual([c["samples"] for c in sin_muestras], [[], [], []])
        self.assertEqual(
            S.get_physical_table_columns("ventas", self.path, include_samples=True)[1]["samples"],
            ["100.0", "250.5", "75.25"],
        )

        # El dict de cada columna es copia propia, no la entrada del cache.
        con_muestras[0]["name"] = "CORROMPIDO"
        self.assertEqual(S.get_physical_table_columns("ventas", self.path)[0]["name"], "id")

    def test_empty_result_is_not_cached(self):
        """Una base que no se puede leer no puede quedar cacheada como vacia.

        Se cuenta el trabajo REAL (la introscpeccion) en vez de espiar
        `sqlite3.connect`, porque hay varias rutas que devuelven vacio sin
        conectar siquiera: una ruta inexistente corta en `os.path.exists` antes
        de abrir el fichero, y una `CorporateConnection` de Postgres que no
        responde traga la excepcion en el `connector_engine`. Espiar el
        `connect` solo comprobaria una de ellas.
        """
        with patch.object(S, "_introspect_tables", return_value=set()) as spy:
            self.assertEqual(S.get_physical_db_tables(self.path), set())
            self.assertEqual(S.get_physical_db_tables(self.path), set())
            # La segunda llamada VOLVIO a preguntar: un vacio cacheado habria
            # respondido sin tocar el introspector, y el Postgres caido se
            # convertiria en diez minutos de "esta base no tiene tablas".
            self.assertEqual(spy.call_count, 2)

    def test_key_ignores_orm_object_identity(self):
        """La key sale de los DATOS de la conexion, no de `id(obj)`.

        `target` es un objeto ORM detached distinto en cada request. Con
        `id(target)` en la key el cache nunca acertaria (y el id se reutiliza
        entre objetos, o sea que tampoco serviria como identidad).
        """
        from app.modules.admin_catalog.models import DatabaseType

        class ConnFalso:
            def __init__(self, host):
                self.db_type = DatabaseType.POSTGRESQL
                self.host = host
                self.port = 5432
                self.database_name = "corp"

        a, b = ConnFalso("h1"), ConnFalso("h1")
        self.assertIsNot(a, b)
        self.assertEqual(S._physical_key(a), S._physical_key(b))
        self.assertNotEqual(S._physical_key(a), S._physical_key(ConnFalso("h2")))


if __name__ == "__main__":
    unittest.main()