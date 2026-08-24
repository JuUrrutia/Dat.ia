import sqlite3
from typing import List

def import_sql_script_to_sqlite(source_path: str, target_sqlite_path: str) -> List[str]:
    """
    Executes a raw SQL dump script against a target SQLite database.
    """
    with open(source_path, "r", encoding="utf-8", errors="ignore") as sql_file:
        sql_script = sql_file.read()
    conn = sqlite3.connect(target_sqlite_path)
    try:
        conn.executescript(sql_script)
        cur = conn.cursor()
        tables = [
            r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            if not r[0].startswith("sqlite_")
        ]
    finally:
        conn.close()
    return tables

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
