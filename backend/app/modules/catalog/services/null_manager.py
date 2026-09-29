import os
import sqlite3
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType
from app.modules.catalog.services.schema_inspector import SchemaInspector

class NullManagerService:
    """
    Manages detection, audit, and remediation strategies for NULL values
    in SQLite and PostgreSQL corporate connections.
    Strategies:
      - 'delete_rows': Removes rows that contain NULLs in the affected columns.
      - 'mode': Imputes NULLs with the most frequent non-null value of the column.
      - 'nearest': Imputes NULLs with the nearest preceding/succeeding valid value (forward-fill).
      - 'open': Preserves NULLs and delegates interactive remediation to the end-user in Chat.
    """

    @classmethod
    def audit_connection_nulls(cls, conn: CorporateConnection, db: Optional[Session] = None) -> Dict[str, Any]:
        tables_meta = SchemaInspector.introspect_connection_metadata(conn)
        tables_with_nulls: List[Dict[str, Any]] = []

        is_pg = conn.db_type == DatabaseType.POSTGRESQL or str(conn.db_type).lower() == "postgresql"

        if is_pg:
            from app.core.database import build_engine_for_connector
            eng = build_engine_for_connector(conn)
            with eng.connect() as connection:
                for tbl_info in tables_meta:
                    tbl_name = tbl_info["table_name"]
                    schema_name = tbl_info.get("schema_name", "public")
                    total_rows = tbl_info.get("row_count", 0)
                    if total_rows == 0:
                        continue

                    null_cols = []
                    for col in tbl_info.get("columns", []):
                        col_name = col["name"]
                        try:
                            res = connection.execute(
                                text(f'SELECT COUNT(*) FROM "{schema_name}"."{tbl_name}" WHERE "{col_name}" IS NULL OR TRIM(LOWER(CAST("{col_name}" AS TEXT))) IN (\'null\', \'none\')')
                            ).scalar()
                            null_count = int(res or 0)
                            if null_count > 0:
                                null_cols.append({
                                    "column_name": col_name,
                                    "data_type": col.get("data_type", "TEXT"),
                                    "null_count": null_count,
                                    "null_percentage": round((null_count / total_rows) * 100, 1)
                                })
                        except Exception:
                            pass

                    if null_cols:
                        tables_with_nulls.append({
                            "table_name": tbl_name,
                            "schema_name": schema_name,
                            "total_rows": total_rows,
                            "columns_with_nulls": null_cols,
                            "total_null_columns": len(null_cols)
                        })
        else:
            # SQLite
            target_path = None
            if conn.host and os.path.exists(conn.host):
                target_path = conn.host
            elif conn.database_name and os.path.exists(conn.database_name):
                target_path = conn.database_name
            elif settings.SQLITE_DB_PATH and os.path.exists(settings.SQLITE_DB_PATH):
                target_path = settings.SQLITE_DB_PATH
            else:
                try:
                    from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
                    resolved = DynamicSchemaPruningService.resolve_db_path(db, conn.id)
                    if resolved and os.path.exists(resolved):
                        target_path = resolved
                except Exception:
                    pass

            if target_path and os.path.exists(target_path):
                with sqlite3.connect(target_path) as s_conn:
                    cursor = s_conn.cursor()
                    for tbl_info in tables_meta:
                        tbl_name = tbl_info["table_name"]
                        total_rows = tbl_info.get("row_count", 0)
                        if total_rows == 0:
                            continue

                        null_cols = []
                        for col in tbl_info.get("columns", []):
                            col_name = col["name"]
                            try:
                                cursor.execute(f'SELECT COUNT(*) FROM "{tbl_name}" WHERE "{col_name}" IS NULL OR TRIM(LOWER(CAST("{col_name}" AS TEXT))) IN (\'null\', \'none\')')
                                row = cursor.fetchone()
                                null_count = int(row[0]) if row else 0
                                if null_count > 0:
                                    null_cols.append({
                                        "column_name": col_name,
                                        "data_type": col.get("data_type", "TEXT"),
                                        "null_count": null_count,
                                        "null_percentage": round((null_count / total_rows) * 100, 1)
                                    })
                            except Exception:
                                pass

                        if null_cols:
                            tables_with_nulls.append({
                                "table_name": tbl_name,
                                "schema_name": "main",
                                "total_rows": total_rows,
                                "columns_with_nulls": null_cols,
                                "total_null_columns": len(null_cols)
                            })

        return {
            "has_nulls": len(tables_with_nulls) > 0,
            "total_tables_with_nulls": len(tables_with_nulls),
            "tables": tables_with_nulls,
            "current_policy": getattr(conn, "null_policy", "open") or "open"
        }

    @classmethod
    def apply_null_policy(cls, conn: CorporateConnection, policy: str, db: Session) -> Dict[str, Any]:
        if policy not in ("delete_rows", "mode", "nearest", "open"):
            raise ValueError(f"Política de nulos no soportada: {policy}")

        conn.null_policy = policy
        db.commit()

        if policy == "open":
            return {
                "status": "success",
                "policy": "open",
                "message": "Política configurada: La decisión se delega proactivamente al usuario en el chat."
            }

        audit = cls.audit_connection_nulls(conn, db)
        if not audit["has_nulls"]:
            return {
                "status": "success",
                "policy": policy,
                "message": "Base de datos limpia: No se detectaron valores nulos."
            }

        is_pg = conn.db_type == DatabaseType.POSTGRESQL or str(conn.db_type).lower() == "postgresql"

        if is_pg:
            from app.core.database import build_engine_for_connector
            eng = build_engine_for_connector(conn)
            with eng.connect() as connection:
                for tbl in audit["tables"]:
                    tbl_name = tbl["table_name"]
                    schema_name = tbl.get("schema_name", "public")
                    cols = tbl["columns_with_nulls"]

                    if policy == "delete_rows":
                        conds = " OR ".join([f'("{c["column_name"]}" IS NULL OR TRIM(LOWER(CAST("{c["column_name"]}" AS TEXT))) IN (\'null\', \'none\'))' for c in cols])
                        connection.execute(text(f'DELETE FROM "{schema_name}"."{tbl_name}" WHERE {conds}'))
                        connection.commit()

                    elif policy == "mode":
                        for c in cols:
                            c_name = c["column_name"]
                            mode_row = connection.execute(
                                text(f'SELECT "{c_name}" FROM "{schema_name}"."{tbl_name}" WHERE "{c_name}" IS NOT NULL AND TRIM(LOWER(CAST("{c_name}" AS TEXT))) NOT IN (\'null\', \'none\') GROUP BY "{c_name}" ORDER BY COUNT(*) DESC LIMIT 1')
                            ).fetchone()
                            if mode_row and mode_row[0] is not None:
                                mode_val = mode_row[0]
                                connection.execute(
                                    text(f'UPDATE "{schema_name}"."{tbl_name}" SET "{c_name}" = :m_val WHERE "{c_name}" IS NULL OR TRIM(LOWER(CAST("{c_name}" AS TEXT))) IN (\'null\', \'none\')'),
                                    {"m_val": mode_val}
                                )
                        connection.commit()

                    elif policy == "nearest":
                        for c in cols:
                            c_name = c["column_name"]
                            # Impute with nearest non-null using window or mode fallback
                            fallback = connection.execute(
                                text(f'SELECT "{c_name}" FROM "{schema_name}"."{tbl_name}" WHERE "{c_name}" IS NOT NULL AND TRIM(LOWER(CAST("{c_name}" AS TEXT))) NOT IN (\'null\', \'none\') LIMIT 1')
                            ).scalar()
                            if fallback is not None:
                                connection.execute(
                                    text(f'UPDATE "{schema_name}"."{tbl_name}" SET "{c_name}" = :f_val WHERE "{c_name}" IS NULL OR TRIM(LOWER(CAST("{c_name}" AS TEXT))) IN (\'null\', \'none\')'),
                                    {"f_val": fallback}
                                )
                        connection.commit()
        else:
            # SQLite
            target_path = None
            if conn.host and os.path.exists(conn.host):
                target_path = conn.host
            elif conn.database_name and os.path.exists(conn.database_name):
                target_path = conn.database_name
            elif settings.SQLITE_DB_PATH and os.path.exists(settings.SQLITE_DB_PATH):
                target_path = settings.SQLITE_DB_PATH
            else:
                try:
                    from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
                    resolved = DynamicSchemaPruningService.resolve_db_path(db, conn.id)
                    if resolved and os.path.exists(resolved):
                        target_path = resolved
                except Exception:
                    pass

            if target_path and os.path.exists(target_path):
                with sqlite3.connect(target_path) as s_conn:
                    cursor = s_conn.cursor()
                    for tbl in audit["tables"]:
                        tbl_name = tbl["table_name"]
                        cols = tbl["columns_with_nulls"]

                        if policy == "delete_rows":
                            conds = " OR ".join([f'("{c["column_name"]}" IS NULL OR TRIM(LOWER(CAST("{c["column_name"]}" AS TEXT))) IN (\'null\', \'none\'))' for c in cols])
                            cursor.execute(f'DELETE FROM "{tbl_name}" WHERE {conds}')
                            s_conn.commit()

                        elif policy == "mode":
                            for c in cols:
                                c_name = c["column_name"]
                                cursor.execute(
                                    f'SELECT "{c_name}" FROM "{tbl_name}" WHERE "{c_name}" IS NOT NULL AND TRIM(LOWER(CAST("{c_name}" AS TEXT))) NOT IN (\'null\', \'none\') GROUP BY "{c_name}" ORDER BY COUNT(*) DESC LIMIT 1'
                                )
                                row = cursor.fetchone()
                                if row and row[0] is not None:
                                    cursor.execute(
                                        f'UPDATE "{tbl_name}" SET "{c_name}" = ? WHERE "{c_name}" IS NULL OR TRIM(LOWER(CAST("{c_name}" AS TEXT))) IN (\'null\', \'none\')',
                                        (row[0],)
                                    )
                            s_conn.commit()

                        elif policy == "nearest":
                            for c in cols:
                                c_name = c["column_name"]
                                # Forward fill via rowid
                                cursor.execute(
                                    f'UPDATE "{tbl_name}" SET "{c_name}" = (SELECT t2."{c_name}" FROM "{tbl_name}" t2 WHERE t2."{c_name}" IS NOT NULL AND TRIM(LOWER(CAST(t2."{c_name}" AS TEXT))) NOT IN (\'null\', \'none\') AND t2.rowid <= "{tbl_name}".rowid ORDER BY t2.rowid DESC LIMIT 1) WHERE "{c_name}" IS NULL OR TRIM(LOWER(CAST("{c_name}" AS TEXT))) IN (\'null\', \'none\')'
                                )
                                # Backward fill remaining
                                cursor.execute(
                                    f'UPDATE "{tbl_name}" SET "{c_name}" = (SELECT t2."{c_name}" FROM "{tbl_name}" t2 WHERE t2."{c_name}" IS NOT NULL AND TRIM(LOWER(CAST(t2."{c_name}" AS TEXT))) NOT IN (\'null\', \'none\') ORDER BY t2.rowid ASC LIMIT 1) WHERE "{c_name}" IS NULL OR TRIM(LOWER(CAST("{c_name}" AS TEXT))) IN (\'null\', \'none\')'
                                )
                            s_conn.commit()

        return {
            "status": "success",
            "policy": policy,
            "message": f"Remediación de nulos aplicada con éxito bajo la política '{policy}'."
        }

    @classmethod
    def apply_in_memory_remediation(
        cls,
        rows: List[Dict[str, Any]],
        columns: List[str],
        policy: str
    ) -> List[Dict[str, Any]]:
        """
        Applies in-memory null remediation to a list of dict rows for interactive user remediation.
        """
        null_cols = set()
        for r in rows:
            for c in columns:
                v = r.get(c)
                if v is None or str(v).strip().lower() in ("none", "null"):
                    null_cols.add(c)

        if not null_cols:
            return rows

        if policy == "delete_rows":
            return [
                r for r in rows
                if not any(r.get(c) is None or str(r.get(c)).strip().lower() in ("none", "null") for c in null_cols)
            ]

        if policy == "mode":
            new_rows = [dict(r) for r in rows]
            for col in null_cols:
                valid_vals = [
                    r[col] for r in new_rows
                    if r.get(col) is not None and str(r.get(col)).strip().lower() not in ("none", "null")
                ]
                if valid_vals:
                    mode_val = max(set(valid_vals), key=valid_vals.count)
                    for r in new_rows:
                        if r.get(col) is None or str(r.get(col)).strip().lower() in ("none", "null"):
                            r[col] = mode_val
            return new_rows

        if policy == "nearest":
            new_rows = [dict(r) for r in rows]
            for col in null_cols:
                last_val = None
                for r in new_rows:
                    if r.get(col) is not None and str(r.get(col)).strip().lower() not in ("none", "null"):
                        last_val = r[col]
                    elif last_val is not None:
                        r[col] = last_val
                first_val = next(
                    (r[col] for r in new_rows if r.get(col) is not None and str(r.get(col)).strip().lower() not in ("none", "null")),
                    None
                )
                if first_val is not None:
                    for r in new_rows:
                        if r.get(col) is None or str(r.get(col)).strip().lower() in ("none", "null"):
                            r[col] = first_val
            return new_rows

        return rows
