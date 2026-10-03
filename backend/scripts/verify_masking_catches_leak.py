"""Comprobacion manual: el test end-to-end detecta la fuga si el enmascarado no corre.

Simula el estado previo al fix (masked_columns vacio) y confirma que el RUT
aparece en claro. No es parte de la suite; es una verificacion del propio test.
"""
import asyncio
import os
import sqlite3
import sys
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401,E402
from app.modules.admin_catalog.models import DatabaseType  # noqa: E402
from app.modules.chat_engine.engine import QueryEngine  # noqa: E402

LEAKED = None


def run(mask_enabled: bool):
    global LEAKED
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    con = sqlite3.connect(tmp.name)
    con.execute("CREATE TABLE clientes (nombre TEXT, rut_dni_cliente TEXT)")
    con.execute("INSERT INTO clientes VALUES ('Ana Perez', '12.345.678-9')")
    con.commit()
    con.close()

    mock_conn = MagicMock()
    mock_conn.id = 1
    mock_conn.db_type = DatabaseType.SQLITE
    mock_conn.host = tmp.name
    mock_conn.database_name = tmp.name
    mock_conn.null_policy = "open"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_conn
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_conn
    mock_db.query.return_value.order_by.return_value.first.return_value = mock_conn

    masked = {"rut_dni_cliente"} if mask_enabled else set()
    with patch.object(QueryEngine, "get_masked_columns_for_role", classmethod(lambda c, *a, **k: masked)), \
         patch.object(QueryEngine, "get_blocked_columns_for_role", classmethod(lambda c, *a, **k: set())), \
         patch.object(QueryEngine, "get_allowed_tables_for_role", classmethod(lambda c, *a, **k: {"clientes"})):
        response = asyncio.run(QueryEngine.execute_query(
            question="SELECT nombre, rut_dni_cliente FROM clientes",
            user_role="Economista", is_admin=False, db=mock_db, connection_id=1,
        ))

    rows = getattr(response, "data_rows", None) or []
    value = rows[0].get("rut_dni_cliente") if rows else None
    os.unlink(tmp.name)
    return value


enmascarado = run(True)
sin_enmascarar = run(False)

print(f"  con enmascarado : {enmascarado!r}")
print(f"  sin enmascarado : {sin_enmascarar!r}")
print()

ok = (
    enmascarado is not None and enmascarado.startswith("*")
    and sin_enmascarar == "12.345.678-9"
)
if ok:
    print("OK: el test end-to-end distingue los dos estados -> sirve como regresion.")
    sys.exit(0)
print("FALLO: el test NO distingue los dos estados -> no sirve como regresion.")
sys.exit(1)
