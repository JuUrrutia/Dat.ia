import os
import re
import csv
import sqlite3
from typing import List, Optional
from .base import sanitize_identifier, infer_sqlite_type, clean_cell_value

def import_csv_to_sqlite(csv_path: str, target_sqlite_path: str, table_name: Optional[str] = None) -> List[str]:
    """
    Imports a CSV file into a SQLite database with automatic delimiter detection,
    encoding recovery, and type inference.
    """
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"]
    content = None
    used_encoding = "utf-8"

    for enc in encodings:
        try:
            with open(csv_path, "r", encoding=enc) as f:
                content = f.read(65536)
                used_encoding = enc
                break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError("No se pudo decodificar el archivo CSV con los juegos de caracteres estándar.")

    sample = content[:4096]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
        delimiter = dialect.delimiter
    except Exception:
        counts = {d: sample.count(d) for d in [",", ";", "\t", "|"]}
        delimiter = max(counts, key=counts.get) if any(counts.values()) else ","

    with open(csv_path, "r", encoding=used_encoding, errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        raw_headers = None
        data_rows = []
        for row in reader:
            if not row or all(str(cell).strip() == "" for cell in row):
                continue
            if raw_headers is None:
                raw_headers = row
            else:
                data_rows.append(row)

    if not raw_headers:
        raise ValueError("El archivo CSV está vacío o no contiene encabezados legibles.")

    headers = []
    seen_cols = set()
    for idx, h in enumerate(raw_headers):
        clean_col = sanitize_identifier(h, fallback_prefix=f"col_{idx+1}")
        col_final = clean_col
        c_count = 1
        while col_final in seen_cols:
            col_final = f"{clean_col}_{c_count}"
            c_count += 1
        seen_cols.add(col_final)
        headers.append(col_final)

    if not table_name:
        base_file = os.path.splitext(os.path.basename(csv_path))[0]
        base_file = re.sub(r'^raw_\d+_', '', base_file)
        table_name = sanitize_identifier(base_file, fallback_prefix="tabla_csv")

    col_types = []
    sample_rows = data_rows[:100]
    for c_idx in range(len(headers)):
        col_samples = [r[c_idx] for r in sample_rows if c_idx < len(r)]
        col_types.append(infer_sqlite_type(col_samples))

    conn = sqlite3.connect(target_sqlite_path)
    try:
        cur = conn.cursor()
        cols_def = ", ".join([f'"{h}" {t}' for h, t in zip(headers, col_types)])
        cur.execute(f'DROP TABLE IF EXISTS "{table_name}";')
        cur.execute(f'CREATE TABLE "{table_name}" ({cols_def});')

        placeholders = ", ".join(["?"] * len(headers))
        insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders});'

        cleaned_data = []
        for r in data_rows:
            row_vals = []
            for c_idx in range(len(headers)):
                val = r[c_idx] if c_idx < len(r) else None
                row_vals.append(clean_cell_value(val))
            cleaned_data.append(row_vals)

        cur.executemany(insert_sql, cleaned_data)
        conn.commit()
    finally:
        conn.close()

    return [table_name]
