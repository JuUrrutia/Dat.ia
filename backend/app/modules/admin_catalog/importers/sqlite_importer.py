import sqlite3
from typing import List

def import_sql_script_to_sqlite(source_path: str, target_sqlite_path: str) -> List[str]:
    """REMOVIDO a proposito: ejecutar un .sql arbitrario queda fuera del producto.

    Antes hacia `conn.executescript(sql_script)`: DDL/DML arbitrario sin pasar por el
    validador AST. Se conserva la firma para que una llamada directa no tenga un
    camino alternativo.
    """
    raise ValueError(
        "La importacion de scripts .sql fue retirada: ejecuta SQL arbitrario sin pasar "
        "por el validador AST. Sube el dataset como .csv, .xlsx o .sqlite."
    )

def inspect_sqlite_database(target_sqlite_path: str) -> List[str]:
    """
    Inspects an uploaded SQLite file and returns its active user tables.
    """
    conn = sqlite3.connect(target_sqlite_path)
    try:
        cur = conn.cursor()
        tables = [
            r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            if not r[0].startswith("sqlite_")
        ]
    finally:
        conn.close()
    if not tables:
        raise ValueError("El archivo SQLite subido no contiene tablas válidas.")
    return tables
