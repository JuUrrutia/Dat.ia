from typing import List, Optional
from .importers.base import sanitize_identifier, infer_sqlite_type, clean_cell_value
from .importers.csv_importer import import_csv_to_sqlite
from .importers.excel_importer import import_excel_to_sqlite
from .importers.sqlite_importer import import_sql_script_to_sqlite, inspect_sqlite_database
from .importers.postgres_importer import (
    infer_postgres_type,
    import_csv_to_postgres,
    import_excel_to_postgres,
    import_sqlite_to_postgres,
    import_sql_script_to_postgres,
)

__all__ = [
    "sanitize_identifier",
    "infer_sqlite_type",
    "clean_cell_value",
    "import_csv_to_sqlite",
    "import_excel_to_sqlite",
    "import_sql_script_to_sqlite",
    "inspect_sqlite_database",
    "convert_uploaded_file_to_sqlite",
    "convert_uploaded_file_to_postgres",
    "infer_postgres_type",
    "import_csv_to_postgres",
    "import_excel_to_postgres",
    "import_sqlite_to_postgres",
    "import_sql_script_to_postgres",
]

def convert_uploaded_file_to_sqlite(source_path: str, ext: str, target_sqlite_path: str, table_name: Optional[str] = None) -> List[str]:
    """
    Orchestrates the conversion of any supported file format (.csv, .xlsx, .xls, .sql, .sqlite, .db)
    into a production-ready SQLite database and returns the list of detected table names.
    """
    clean_ext = ext.lower().strip()

    if clean_ext in [".csv", ".txt", ".tsv"]:
        return import_csv_to_sqlite(source_path, target_sqlite_path, table_name=table_name)
    
    elif clean_ext in [".xlsx", ".xlsm", ".xltx", ".xls"]:
        return import_excel_to_sqlite(source_path, target_sqlite_path)
    
    elif clean_ext == ".sql":
        return import_sql_script_to_sqlite(source_path, target_sqlite_path)

    elif clean_ext in [".sqlite", ".db", ".sqlite3"]:
        return inspect_sqlite_database(target_sqlite_path)

    else:
        raise ValueError(f"Formato no soportado: {clean_ext}. Formatos permitidos: .sqlite, .db, .sqlite3, .csv, .xlsx, .xls, .sql")

def convert_uploaded_file_to_postgres(source_path: str, ext: str, target_engine, table_name: Optional[str] = None) -> List[str]:
    """
    Orchestrates the conversion and loading of any supported file format (.csv, .xlsx, .xls, .sql, .sqlite, .db)
    directly into a target PostgreSQL engine (democratizacion_empresa) and returns the created table names.
    """
    clean_ext = ext.lower().strip()

    if clean_ext in [".csv", ".txt", ".tsv"]:
        return import_csv_to_postgres(source_path, target_engine, table_name=table_name)

    elif clean_ext in [".xlsx", ".xlsm", ".xltx", ".xls"]:
        return import_excel_to_postgres(source_path, target_engine)

    elif clean_ext in [".sqlite", ".db", ".sqlite3"]:
        return import_sqlite_to_postgres(source_path, target_engine)

    elif clean_ext == ".sql":
        return import_sql_script_to_postgres(source_path, target_engine)

    else:
        raise ValueError(f"Formato no soportado: {clean_ext}. Formatos permitidos: .sqlite, .db, .sqlite3, .csv, .xlsx, .xls, .sql")
