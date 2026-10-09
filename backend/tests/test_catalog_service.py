"""CatalogDomainService: validacion de entrada y honestidad de la respuesta.

BUG 8: `get_data_dictionary` declaraba `blocked_columns: Optional[Set[str]]`
sin importar `Set`. En Python 3.14 (PEP 649, anotaciones perezosas) pasa
desapercibido; en 3.11 --el Python del CI-- las anotaciones se evaluan en el
`def` y eso es un NameError al importar, que tumbaba `admin_catalog/router.py`
y con el la app entera. Esta clase de bug ya fatality el backend cinco veces.

BUG 9: `create_catalog_item` con un `connection_id` inexistente no daba 404:
redirigia en silencio a la conexion activa mas reciente y, si ya habia una
entrada de curaduría para (tabla, columna) ahi, le pisaba `friendly_name`,
`description`, `synonyms` y `business_formula`.
"""

import typing
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.modules.admin_catalog.models import DatabaseType, SemanticCatalog
from app.modules.admin_catalog.schemas import SemanticCatalogCreate
from app.modules.catalog.services import catalog_service as cs
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.modules.catalog.services.schema_inspector import SchemaInspector, SchemaIntrospectionError


def _conn_record(cid, active=True):
    rec = MagicMock()
    rec.id = cid
    rec.db_type = DatabaseType.SQLITE
    rec.is_active = active
    rec.name = f"conn-{cid}"
    return rec


# Variante con nombre explicito (venia de test_residual_honesty.py, disuelto
# aqui): el `_conn_record` de arriba no acepta `name`, y estos tests necesitan
# distinguir dos conexiones por su nombre.
def _conn_record_named(cid, name="conn"):
    rec = MagicMock()
    rec.id = cid
    rec.name = name
    rec.db_type = DatabaseType.SQLITE
    rec.is_active = True
    return rec


class TestSetIsImported(unittest.TestCase):
    """BUG 8: el NameError que no se ve en 3.14 y tumba el CI en 3.11."""

    def test_get_data_dictionary_annotations_evaluate_eagerly(self):
        hints = typing.get_type_hints(CatalogDomainService.get_data_dictionary)
        self.assertIn("blocked_columns", hints)
        self.assertIn("masked_columns", hints)

    def test_all_three_catalog_modules_survive_eager_annotation_evaluation(self):
        """El chequeo que faltaba: `typing.get_type_hints` sobre TODAS las
        funciones publicas de los tres archivos de la zona.

        El ruido de SQLAlchemy/pydantic se filtra quedandose solo con las
        clases definidas en estos modulos.
        """
        from app.modules.catalog.services import null_manager, schema_inspector

        own = {
            null_manager: {"NullManagerService"},
            schema_inspector: {"SchemaInspector", "SchemaIntrospectionError"},
            cs: {"CatalogDomainService"},
        }

        failures = []
        for mod, classnames in own.items():
            for cname in classnames:
                cls = getattr(mod, cname)
                for attr in dir(cls):
                    fn = getattr(cls, attr)
                    if not callable(fn):
                        continue
                    try:
                        typing.get_type_hints(fn)
                    except Exception as ex:
                        failures.append(f"{cname}.{attr}: {type(ex).__name__}: {ex}")

        self.assertEqual(
            failures, [],
            "anotaciones que no resuelven en evaluacion eager (CI usa 3.11):\n"
            + "\n".join(failures),
        )

    def test_module_source_does_not_use_set_without_importing_it(self):
        import inspect as py_inspect
        src = py_inspect.getsource(cs)
        self.assertIn("Set[str]", src)
        import_line = [l for l in src.splitlines() if l.startswith("from typing import")][0]
        self.assertIn("Set", import_line, f"Set se usa pero no se importa: {import_line}")


class TestUnknownConnectionIdIsRejected(unittest.TestCase):
    """BUG 9: `connection_id=999` no debe redirigir en silencio."""

    def _explicit_item(self, conn_id):
        """Payload con `connection_id` PRESENTE en el request.

        Hace falta `model_fields_set`: el schema tiene default 1 (= "no
        especificada") y para ese caso el fallback a la conexion activa es el
        comportamiento historico y correcto.
        """
        item = SemanticCatalogCreate(
            connection_id=conn_id, table_name="ventas", column_name="monto",
            friendly_name="Monto", description="d", synonyms=None,
            business_formula=None, is_ai_generated=False,
        )
        assert "connection_id" in item.model_fields_set
        return item

    def test_unknown_connection_id_raises_404(self):
        db = MagicMock()
        # El filtro por id=999 no encuentra nada.
        db.query.return_value.filter.return_value.first.return_value = None

        item = self._explicit_item(999)

        with self.assertRaises(HTTPException) as ctx:
            CatalogDomainService.create_catalog_item(db, item)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("999", ctx.exception.detail)

    def test_unknown_connection_id_does_not_write_against_the_active_connection(self):
        """El caso grave: la curaduría del admin en la conexión activa."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        curated = MagicMock()

        def query_side_effect(model):
            q = MagicMock()
            if model.__name__ == "CorporateConnection":
                # id=999 -> None; is_active -> la conexión activa (=1)
                q.filter.return_value.first.side_effect = [None, _conn_record(1)]
            else:
                # SemanticCatalog: ya existe curaduría para (ventas, monto)
                q.filter.return_value.first.return_value = curated
            return q

        db.query.side_effect = query_side_effect

        item = self._explicit_item(999)

        with self.assertRaises(HTTPException):
            CatalogDomainService.create_catalog_item(db, item)

        self.assertFalse(
            db.commit.called,
            "se commiteo una escritura sobre la conexion equivocada",
        )
        

    def test_known_connection_id_still_creates_the_item(self):
        """El fix no puede romper el camino feliz."""
        created = MagicMock()
        created.id = 10
        db = MagicMock()

        def query_side_effect(model):
            q = MagicMock()
            if model.__name__ == "CorporateConnection":
                q.filter.return_value.first.return_value = _conn_record(5)
            else:
                q.filter.return_value.first.return_value = None
            return q

        db.query.side_effect = query_side_effect
        db.add.side_effect = lambda o: setattr(o, "id", created.id)

        item = self._explicit_item(5)
        result = CatalogDomainService.create_catalog_item(db, item)

        self.assertIsNotNone(result)
        self.assertTrue(db.commit.called)

    def test_default_connection_id_still_falls_back_to_the_active_connection(self):
        """POST /catalog sin `connection_id` (default 1) debe seguir funcionando.

        El 404 es solo para ids que el cliente mando explicitamente y no
        existen; el default significa "no especificada".
        """
        active = _conn_record(7)
        db = MagicMock()
        created = MagicMock()

        def query_side_effect(model):
            q = MagicMock()
            if model.__name__ == "CorporateConnection":
                # id=1 -> None (no existe); is_active -> la 7.
                # `order_by` encadena sobre el filtro, hay que cablear esa rama.
                ordered = MagicMock()
                ordered.first.return_value = active
                q.filter.return_value.first.side_effect = [None]
                q.filter.return_value.order_by.return_value = ordered
            else:
                q.filter.return_value.first.return_value = None
            return q

        db.query.side_effect = query_side_effect
        db.add.side_effect = lambda o: setattr(o, "id", created.id)

        item = SemanticCatalogCreate(
            table_name="ventas", column_name="monto",
            friendly_name="Monto", description="d", synonyms=None,
            business_formula=None, is_ai_generated=False,
        )
        self.assertNotIn("connection_id", item.model_fields_set)

        result = CatalogDomainService.create_catalog_item(db, item)
        self.assertEqual(result.connection_id, 7)


class TestDataDictionaryDoesNotReportAFailedConnectionAsEmpty(unittest.TestCase):
    """BUG 6: el diccionario debe responder 502, no 200 con total_tables=0."""

    def test_schema_introspection_failure_becomes_502(self):
        db = MagicMock()
        with patch.object(
            cs.SchemaInspector, "resolve_connection_db_path",
            return_value=("/tmp/x.db", _conn_record(1)),
        ):
            with patch.object(
                cs.SchemaInspector, "introspect_connection_metadata",
                side_effect=SchemaIntrospectionError("no se pudo conectar con Produccion"),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    CatalogDomainService.get_data_dictionary(db, connection_id=1)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("Produccion", ctx.exception.detail)

    def test_the_response_never_says_zero_tables_for_a_broken_connection(self):
        """Regresion del sintoma exacto que se reporto: HTTP 200 + 0 tablas."""
        db = MagicMock()
        with patch.object(
            cs.SchemaInspector, "resolve_connection_db_path",
            return_value=("/tmp/x.db", _conn_record(1)),
        ):
            with patch.object(
                cs.SchemaInspector, "introspect_connection_metadata",
                side_effect=SchemaIntrospectionError("timeout"),
            ):
                raised = None
                try:
                    CatalogDomainService.get_data_dictionary(db, connection_id=1)
                except HTTPException as ex:
                    raised = ex
                self.assertIsNotNone(raised, "la llamada deveria fallar, no devolver un diccionario vacio")
                self.assertNotEqual(raised.status_code, 200)


class TestUnknownConnectionIdIsRejectedByTheInspector(unittest.TestCase):
    """`SchemaInspector.resolve_connection_db_path` con un `connection_id` explicito
    e inexistente caia en silencio a "la conexion no-uploadada": el caller terminaba
    introspeccionando OTRA base creyendola la que pidio (mismo criterio que ya
    corrijo `create_catalog_item`)."""

    def test_explicit_unknown_id_raises_404(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            SchemaInspector.resolve_connection_db_path(db, 999)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("999", ctx.exception.detail)

    def test_it_does_not_silently_introspect_another_database(self):
        """El sintoma: pedir la 999 y terminar leyendo la base no-uploadada."""
        db = MagicMock()
        uploaded = _conn_record_named(1, name="Base de Datos Clientes Nuevos")
        uploaded.is_uploaded = False

        def query_side_effect(_model):
            q = MagicMock()
            # id=999 -> None; el fallback is_uploaded=False -> la otra base.
            q.filter.return_value.first.side_effect = [None, uploaded]
            return q

        db.query.side_effect = query_side_effect

        with self.assertRaises(HTTPException) as ctx:
            SchemaInspector.resolve_connection_db_path(db, 999)

        # Si hubiera caido en el fallback, el segundo `first` (la base
        # no-uploadada) se habria consumido y no habria raising.
        self.assertIn("999", ctx.exception.detail)
        self.assertNotEqual(uploaded.id, 999)

    def test_no_connection_id_still_resolves_the_active_one(self):
        """El camino legitimo: sin connection_id se usa la conexion activa."""
        active = _conn_record(7)
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = active

        db_path, conn = SchemaInspector.resolve_connection_db_path(db, None)

        self.assertIs(conn, active)
        self.assertTrue(db_path)

    def test_known_connection_id_still_resolves(self):
        known = _conn_record(3)
        known.db_type = DatabaseType.POSTGRESQL
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = known

        _db_path, conn = SchemaInspector.resolve_connection_db_path(db, 3)

        self.assertIs(conn, known)


# ---------------------------------------------------------------- mapa de catalogo por esquema

def _catalog_entry(table, column, schema, friendly):
    return SemanticCatalog(
        id=abs(hash((schema or "", table, column))) % 10000,
        connection_id=1,
        domain_id=None,
        schema_name=schema,
        table_name=table,
        column_name=column,
        friendly_name=friendly,
        description=f"desc de {friendly}",
        synonyms=None,
        business_formula=None,
        is_ai_generated=False,
    )


def _tables_meta(tables):
    return [
        {
            "table_name": tbl,
            "schema_name": schema,
            "row_count": 1,
            "columns": [{
                "name": col, "data_type": "TEXT", "is_pk": False,
                "is_nullable": True, "default_value": None, "sample_values": ["x"],
            }],
        }
        for schema, tbl, col in tables
    ]


def _dictionary(entries, tables):
    db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model.__name__ == "SemanticCatalog":
            q.filter.return_value.all.return_value = entries
        return q

    db.query.side_effect = query_side_effect

    with patch.object(
        cs.SchemaInspector, "resolve_connection_db_path",
        return_value=("/tmp/x.db", _conn_record(1)),
    ), patch.object(cs.SchemaInspector, "introspect_connection_metadata", return_value=tables):
        return CatalogDomainService.get_data_dictionary(db, connection_id=1)


class TestCatalogMapKey(unittest.TestCase):
    """`get_data_dictionary` armaba `catalog_map` por tabla+columna sin `schema_name`:
    columnas homonimas de `public` y `priv` colisionaban y una se llevaba la
    descripcion de la otra."""

    def test_homonymous_columns_in_two_schemas_do_not_collide(self):
        tables = [("public", "ventas", "codigo"), ("priv", "ventas", "codigo")]
        entries = [
            _catalog_entry("ventas", "codigo", "public", "Codigo publico"),
            _catalog_entry("ventas", "codigo", "priv", "Codigo privado"),
        ]

        resp = _dictionary(entries, _tables_meta(tables))
        by_schema = {t.schema_name: t.columns[0] for t in resp.tables}

        self.assertEqual(by_schema["public"].friendly_name, "Codigo publico")
        self.assertEqual(by_schema["priv"].friendly_name, "Codigo privado")

    def test_lookup_is_case_insensitive(self):
        """Postgres devuelve la tabla en minuscula y la curaduría la guardo en mayuscula."""
        tables = [("public", "ventas", "codigo")]
        entries = [_catalog_entry("VENTAS", "CODIGO", "PUBLIC", "Codigo curado")]

        resp = _dictionary(entries, _tables_meta(tables))

        self.assertEqual(resp.tables[0].columns[0].friendly_name, "Codigo curado")

    def test_legacy_row_without_schema_still_matches(self):
        """Filas sembradas antes de existir `schema_name` (NULL o "") no desaparecen."""
        for legacy_schema in (None, ""):
            with self.subTest(schema=legacy_schema):
                tables = [("public", "ventas", "codigo")]
                entries = [_catalog_entry("ventas", "codigo", legacy_schema, "Codigo legado")]

                resp = _dictionary(entries, _tables_meta(tables))

                self.assertEqual(resp.tables[0].columns[0].friendly_name, "Codigo legado")

    def test_specific_schema_wins_over_the_legacy_wildcard(self):
        tables = [("public", "ventas", "codigo")]
        entries = [
            _catalog_entry("ventas", "codigo", None, "Codigo legado"),
            _catalog_entry("ventas", "codigo", "public", "Codigo publico"),
        ]

        resp = _dictionary(entries, _tables_meta(tables))

        self.assertEqual(resp.tables[0].columns[0].friendly_name, "Codigo publico")

    def test_table_level_description_also_respects_the_schema(self):
        entries = [
            SemanticCatalog(
                id=1, connection_id=1, domain_id=None, schema_name="public",
                table_name="ventas", column_name=None, friendly_name="Ventas",
                description="Tabla de ventas publicas", is_ai_generated=False,
            ),
            SemanticCatalog(
                id=2, connection_id=1, domain_id=None, schema_name="priv",
                table_name="ventas", column_name=None, friendly_name="Ventas",
                description="Tabla de ventas privadas", is_ai_generated=False,
            ),
        ]

        resp = _dictionary(entries, _tables_meta([("public", "ventas", "codigo"), ("priv", "ventas", "codigo")]))
        by_schema = {t.schema_name: t.description for t in resp.tables}

        self.assertEqual(by_schema["public"], "Tabla de ventas publicas")
        self.assertEqual(by_schema["priv"], "Tabla de ventas privadas")


if __name__ == "__main__":
    unittest.main()