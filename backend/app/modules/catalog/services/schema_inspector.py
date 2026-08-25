import os
import sqlite3
from typing import List, Optional, Any, Dict, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType

class SchemaInspector:
    """
    Encapsulates physical database introspection (PostgreSQL, SQLite, etc.)
    and connection database path resolution.
    """

    IGNORED_TABLES = {
        "sqlite_sequence", "roles", "domains", "corporate_connections",
        "users", "role_domain_links", "role_table_permissions",
        "role_column_permissions", "semantic_catalog", "audit_logs",
        "user_sessions", "alembic_version"
    }

    @classmethod
    def resolve_connection_db_path(cls, db: Session, connection_id: Optional[int]) -> Tuple[str, CorporateConnection]:
        """
        Resolves local file path or connection object based on connection_id.
        """
        conn = None
        if connection_id:
            conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()

        if not conn:
            conn = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).order_by(CorporateConnection.id.desc()).first()
            if not conn:
                conn = db.query(CorporateConnection).order_by(CorporateConnection.id.desc()).first()

        if conn and conn.db_type == DatabaseType.SQLITE:
            if conn.host and os.path.exists(conn.host):
                return conn.host, conn
            if conn.database_name and os.path.exists(conn.database_name):
                return conn.database_name, conn

        db_path = settings.SQLITE_DB_PATH
        if not conn:
            conn = CorporateConnection(
                id=1,
                name="Base de Datos Corporativa",
                db_type=DatabaseType.SQLITE,
                host=db_path,
                port=0,
                database_name=os.path.basename(db_path),
                username="admin",
                is_active=True
            )
        return db_path, conn

    @classmethod
    def introspect_connection_metadata(cls, conn_obj: Optional[CorporateConnection], db_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Introspects tables and columns with data types, nullability, primary keys, and sample values
        for both SQLite and PostgreSQL (or other SQLAlchemy-supported RDBMS).
        """
        tables_metadata: List[Dict[str, Any]] = []

        # 1. PostgreSQL / Remote RDBMS
        if conn_obj and conn_obj.db_type != DatabaseType.SQLITE:
            try:
                from sqlalchemy import inspect as sa_inspect, text
                from app.core.database import build_engine_for_connector
                eng = build_engine_for_connector(conn_obj)
                inspector = sa_inspect(eng)
                all_schemas = [s for s in inspector.get_schema_names() if s not in ("information_schema", "pg_catalog", "pg_toast")]
                target_schema = "public" if "public" in all_schemas else (all_schemas[0] if all_schemas else None)

                table_names = inspector.get_table_names(schema=target_schema)
                active_tables = [t for t in table_names if t.lower() not in cls.IGNORED_TABLES]

                with eng.connect() as connection:
                    for tbl in active_tables:
                        try:
                            schema_prefix = f'"{target_schema}".' if target_schema else ""
                            cnt_res = connection.execute(text(f'SELECT COUNT(*) FROM {schema_prefix}"{tbl}"')).scalar()
                            row_count = int(cnt_res or 0)
                        except Exception:
                            row_count = 0

                        cols_info = inspector.get_columns(tbl, schema=target_schema)
                        pk_info = inspector.get_pk_constraint(tbl, schema=target_schema)
                        pk_cols = set(pk_info.get("constrained_columns", [])) if pk_info else set()

                        cols_data = []
                        for col in cols_info:
                            col_name = col["name"]
                            col_type = str(col["type"])
                            is_pk = col_name in pk_cols
                            is_null = col.get("nullable", True)
                            def_val = str(col.get("default", "")) if col.get("default") is not None else None

                            sample_vals = []
                            try:
                                samples_res = connection.execute(
                                    text(f'SELECT DISTINCT "{col_name}" FROM {schema_prefix}"{tbl}" WHERE "{col_name}" IS NOT NULL LIMIT 3')
                                ).fetchall()
                                sample_vals = [str(r[0]) for r in samples_res if r[0] is not None]
                            except Exception:
                                pass

                            cols_data.append({
                                "name": col_name,
                                "data_type": col_type,
                                "is_pk": is_pk,
                                "is_nullable": is_null,
                                "default_value": def_val,
                                "sample_values": sample_vals
                            })

                        tables_metadata.append({
                            "table_name": tbl,
                            "schema_name": target_schema or "public",
                            "row_count": row_count,
                            "columns": cols_data
                        })
                return tables_metadata
            except Exception:
                return tables_metadata

        # 2. SQLite local file
        target_path = db_path or (conn_obj.host if conn_obj else None) or settings.SQLITE_DB_PATH
        if not target_path or not os.path.exists(target_path):
            return tables_metadata

        try:
            with sqlite3.connect(target_path) as sqlite_conn:
                sqlite_cursor = sqlite_conn.cursor()
                raw_tables = [
                    r[0] for r in sqlite_cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
                    ).fetchall()
                ]
                active_tables = [t for t in raw_tables if t.lower() not in cls.IGNORED_TABLES]

                for tbl in active_tables:
                    try:
                        row_count_res = sqlite_cursor.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()
                        row_count = row_count_res[0] if row_count_res else 0
                    except Exception:
                        row_count = 0

                    cols_info = sqlite_cursor.execute(f'PRAGMA table_info("{tbl}")').fetchall()
                    cols_data = []

                    for col in cols_info:
                        col_name = col[1]
                        col_type = col[2] or "TEXT"
                        not_null = bool(col[3])
                        default_val = str(col[4]) if col[4] is not None else None
                        is_pk = bool(col[5])

                        sample_vals = []
                        try:
                            samples_raw = sqlite_cursor.execute(
                                f'SELECT DISTINCT "{col_name}" FROM "{tbl}" WHERE "{col_name}" IS NOT NULL AND "{col_name}" != \'\' LIMIT 3'
                            ).fetchall()
                            sample_vals = [str(s[0]) for s in samples_raw if s[0] is not None]
                        except Exception:
                            pass

                        cols_data.append({
                            "name": col_name,
                            "data_type": col_type,
                            "is_pk": is_pk,
                            "is_nullable": not not_null,
                            "default_value": default_val,
                            "sample_values": sample_vals
                        })

                    tables_metadata.append({
                        "table_name": tbl,
                        "schema_name": "main",
                        "row_count": row_count,
                        "columns": cols_data
                    })
        except Exception:
            pass

        return tables_metadata
