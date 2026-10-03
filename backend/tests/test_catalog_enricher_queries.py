"""El AutoEnrichment no hace un SELECT por columna.

Por que este test
-----------------
`auto_enrich_catalog` y `seed_catalog_heuristics_for_connection` recorren
tabla por tabla y columna por columna. Antes de este cambio cada columna
disparaba su propio `_find_existing_item`, que es un SELECT con
`func.lower(...)` en ambos lados: 50 columnas eran 50 round-trips para leer
una tabla que cabe en un solo SELECT. Peor todavia, el predicado con `lower()`
no lo puede usar ningun indice, asi que ademas era un seq scan por columna.

Este test mide la QUERIES, no el resultado: porque el enriquecimiento por
heuristica ya es instantaneo, una version que hiciera 50 SELECTS por 50
columnas seria "rapida" igual en un test de tiempo. Lo que se verifica es que
la consulta crezca con el numero de CONEXIONES, no con el de columnas.

Lo que protege ademas
---------------------
`_register_new` mete cada fila creada en el indice: sin eso, una segunda pasada
sobre la misma columna no la encontraria e insertaria un duplicado, que revienta
el `UniqueConstraint(connection_id, schema_name, table_name, column_name)`.
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.modules.admin_catalog.models import DatabaseType
from app.modules.catalog.services.catalog_enricher import CatalogEnricher


class TestCatalogEnricherNoNPlusOne(unittest.TestCase):
    # Alto y fijo: un id que ninguna conexion real use, para no pisar el
    # catalogo de nadie. El rango de ids demo es chico.
    CONN_ID = 999001

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        # 3 tablas x 6 columnas = 18 columnas: con el N+1 serian 18 SELECTs
        # de `_find_existing_item`, ahora 1.
        conn = sqlite3.connect(self.path)
        for t in range(1, 4):
            cols = ", ".join(f"col{j} REAL" for j in range(1, 7))
            conn.execute(f"CREATE TABLE tabla{t} ({cols})")
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def _meta_falsa(self):
        return [
            {
                "table_name": f"tabla{t}",
                "schema_name": "main",
                "columns": [
                    {"name": f"col{j}", "data_type": "REAL", "sample_values": []}
                    for j in range(1, 7)
                ],
            }
            for t in range(1, 4)
        ]

    def _contar_queries(self, fn):
        """Cuenta los SELECT via el engine de SQLAlchemy.

        No se espia `sqlite3.Connection.execute`: en Python 3.14 ese tipo es
        inmutable y `patch.object` revienta con
        "cannot set 'execute' attribute of immutable type". El evento de
        SQLAlchemy ve lo mismo y ademas cubre el dialecto que se este usando.
        """
        import app.core.database as core_db
        from sqlalchemy import event

        counted = []

        def antes_execute(conn, cursor, statement, parameters, context, executemany):
            counted.append(statement)

        event.listen(core_db.engine, "before_cursor_execute", antes_execute)
        try:
            fn()
        finally:
            event.remove(core_db.engine, "before_cursor_execute", antes_execute)
        return counted

    def test_seed_does_one_query_per_connection_not_per_column(self):
        db = self._session()
        try:
            def correr():
                with patch(
                    "app.modules.catalog.services.catalog_enricher.SchemaInspector.introspect_connection_metadata",
                    return_value=self._meta_falsa(),
                ):
                    CatalogEnricher.seed_catalog_heuristics_for_connection(db, self.CONN_ID, self.path)

            queries = self._contar_queries(correr)
            # Se cuentan solo las de `semantic_catalog`: el lookup de
            # `corporate_connections` lo hace el propio metodo y no es el N+1
            # que se esta persiguiendo.
            selects = [q for q in queries if "FROM semantic_catalog" in q]
            # Antes: 18 (una por columna). Ahora: 1, la precarga del indice.
            self.assertEqual(
                len(selects), 1,
                f"se esperaba 1 SELECT de precarga, hubo {len(selects)}",
            )
        finally:
            self._limpiar(db)

    def test_does_not_duplicate_rows_on_second_pass(self):
        """La fila creada en la primera pasada tiene que ser visible en la segunda.

        Sin `_register_new` el indice no la ve, se inserta otra y el
        `UniqueConstraint` revienta con un error de integridad en vez de
        decir "ya estaba enriquecido".
        """
        db = self._session()
        try:
            with patch(
                "app.modules.catalog.services.catalog_enricher.SchemaInspector.introspect_connection_metadata",
                return_value=self._meta_falsa(),
            ):
                primero = CatalogEnricher.seed_catalog_heuristics_for_connection(db, self.CONN_ID, self.path)
                segundo = CatalogEnricher.seed_catalog_heuristics_for_connection(db, self.CONN_ID, self.path)

            self.assertEqual(primero, 18)
            self.assertEqual(segundo, 0, "la segunda pasada volvio a insertar filas")

            from app.modules.admin_catalog.models import SemanticCatalog
            total = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == self.CONN_ID
            ).count()
            self.assertEqual(total, 18, f"quedaron {total} filas en vez de 18")
        finally:
            self._limpiar(db)

    def _session(self):
        """Sesion propia, sobre una conexion DEDICADA, y que se limpia sola.

        Este test no puede usar una conexion real del entorno: sembrarla exige
        borrar su catalogo, y `corporate_connections` / `semantic_catalog` son
        estado COMPARTIDO con el resto de la suite. Borrar el catalogo de la
        conexion 1 para medir el numero de SELECTs deja el arbol de tests
        dependingo del orden -- exactamente lo que el docstring de `conftest.py`
        dice que no se debe hacer. Un `connection_id` propio, borrado en
        `tearDown`, no le pisa el catalogo a nadie.
        """
        import app.core.database as core_db
        from app.modules.admin_catalog.models import CorporateConnection, SemanticCatalog

        db = core_db.SessionLocal()
        db.query(SemanticCatalog).filter(SemanticCatalog.connection_id == self.CONN_ID).delete(
            synchronize_session=False
        )
        db.query(CorporateConnection).filter(CorporateConnection.id == self.CONN_ID).delete(
            synchronize_session=False
        )
        db.add(CorporateConnection(
            id=self.CONN_ID, name="Prueba N+1", db_type=DatabaseType.SQLITE, host=self.path,
            port=0, database_name=os.path.basename(self.path), username="admin",
            is_active=False,
        ))
        db.commit()
        return db

    def _limpiar(self, db):
        from app.modules.admin_catalog.models import CorporateConnection, SemanticCatalog
        db.query(SemanticCatalog).filter(SemanticCatalog.connection_id == self.CONN_ID).delete(
            synchronize_session=False
        )
        db.query(CorporateConnection).filter(CorporateConnection.id == self.CONN_ID).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()


if __name__ == "__main__":
    unittest.main()