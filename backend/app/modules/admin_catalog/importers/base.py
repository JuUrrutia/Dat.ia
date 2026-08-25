import re
import datetime
from typing import List, Any

def sanitize_identifier(name: str, fallback_prefix: str = "col") -> str:
    """
    Sanitizes table or column names to be valid SQLite identifiers.
    Replaces accents, spaces, and special characters with underscores.
    """
    if not name:
        return fallback_prefix
    
    clean = str(name).strip().lower()
    clean = (
        clean.replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('ú', 'u')
        .replace('ñ', 'n')
    )
    clean = re.sub(r'[^a-zA-Z0-9_]+', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip('_')
    
    if not clean or clean[0].isdigit():
        clean = f"{fallback_prefix}_{clean}"
    return clean

def infer_sqlite_type(values: List[Any]) -> str:
    """
    Infers the most appropriate SQLite column type from a sample of non-null values.
    """
    non_empty = [v for v in values if v is not None and str(v).strip() != ""]
    if not non_empty:
        return "TEXT"
    
    is_int = True
    is_float = True
    for v in non_empty:
        s = str(v).strip().replace("$", "").replace("€", "").replace("%", "")
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        try:
            int(s)
        except ValueError:
            is_int = False
            try:
                float(s)
            except ValueError:
                is_float = False
                break
    
    if is_int:
        return "INTEGER"
    if is_float:
        return "REAL"
    return "TEXT"

def clean_cell_value(val: Any) -> Any:
    """
    Cleans and formats cell values for SQLite insertion.
    """
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val).strip()
    return s if s != "" else None
