from typing import List, Optional
from .importers.base import sanitize_identifier, infer_sqlite_type, clean_cell_value
from .importers.csv_importer import import_csv_to_sqlite
from .importers.excel_importer import import_excel_to_sqlite
from .importers.sqlite_importer import import_sql_script_to_sqlite, inspect_sqlite_database

__all__ = [
    "sanitize_identifier",
    "infer_sqlite_type",
    "clean_cell_value",
    "import_csv_to_sqlite",
    "import_excel_to_sqlite",
    "import_sql_script_to_sqlite",
    "inspect_sqlite_database",
    "convert_uploaded_file_to_sqlite",
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
