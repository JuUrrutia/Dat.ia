import os
import sqlite3
from typing import List, Dict, Set, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.permission import RoleTablePermission, RoleColumnPermission, ColumnPermissionType
from app.models.role import Role
from app.models.catalog import SemanticCatalog

class DynamicSchemaPruningService:
    """
    Filters database catalog definitions according to user role permissions
    and physically available tables in the active database engine.
    Ensures LLM context ONLY receives authorized & active physical tables.
    """

    @classmethod
    def resolve_db_path(cls, db: Optional[Session] = None, connection_id: Optional[int] = None) -> str:
        """Resolves target physical SQLite database path for active connection."""
        if db is not None:
            try:
                from app.models.connection import CorporateConnection, DatabaseType
                conn = None
                if connection_id:
                    conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
                if not conn:
                    conn = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).first()
                if conn and conn.db_type == DatabaseType.SQLITE:
                    if conn.host and os.path.exists(conn.host):
                        return conn.host
                    if conn.database_name and os.path.exists(conn.database_name):
                        return conn.database_name
            except Exception:
                pass
        return settings.SQLITE_DB_PATH

    @classmethod
    def get_physical_db_tables(cls, db_path: Optional[str] = None) -> Set[str]:
        """Inspects active SQLite database file to retrieve physically existing data tables."""
        try:
            target_path = db_path or settings.SQLITE_DB_PATH
            if not target_path or not os.path.exists(target_path):
                return set()
            conn = sqlite3.connect(target_path)
            cursor = conn.cursor()
            raw_tables = [r[0].lower() for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            conn.close()
            ignored_metadata = {
                "sqlite_sequence", "roles", "domains", "corporate_connections",
                "users", "role_domain_links", "role_table_permissions",
                "role_column_permissions", "semantic_catalog", "audit_logs"
            }
            return {t for t in raw_tables if t not in ignored_metadata}
        except Exception:
            return set()

    @classmethod
    def get_physical_table_columns(cls, table_name: str, db_path: Optional[str] = None, include_samples: bool = True) -> List[Dict[str, Any]]:
        """
        Inspects active SQLite database file to retrieve real physical columns, data types,
        and representative sample values for automatic profiling of cryptic/numbered tables.
        """
        try:
            target_path = db_path or settings.SQLITE_DB_PATH
            if not target_path or not os.path.exists(target_path):
                return []
            conn = sqlite3.connect(target_path)
            cursor = conn.cursor()
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            clean_table = "".join(c for c in table_name if c.isalnum() or c == "_")
            if not clean_table:
                return []
            rows = cursor.execute(
                "SELECT cid, name, type, [notnull], dflt_value, pk FROM pragma_table_info(?)",
                (clean_table,)
            ).fetchall()

            col_samples_map: Dict[str, List[str]] = {}
            if include_samples:
                try:
                    conn.row_factory = sqlite3.Row
                    s_cursor = conn.cursor()
                    s_cursor.execute("SELECT * FROM " + clean_table + " LIMIT 20")
                    for row in s_cursor.fetchall():
                        for k in row.keys():
                            val = row[k]
                            if val is not None and str(val).strip():
                                s_list = col_samples_map.setdefault(k, [])
                                val_str = str(val)[:35]
                                if val_str not in s_list and len(s_list) < 3:
                                    s_list.append(val_str)
                except Exception:
                    pass

            result = []
            for r in rows:
                col_name = r[1]
                col_type = r[2] or "TEXT"
                is_pk = bool(r[5])
                samples = col_samples_map.get(col_name, [])

                result.append({
                    "name": col_name,
                    "type": col_type,
                    "is_pk": is_pk,
                    "samples": samples
                })

            conn.close()
            return result
        except Exception:
            return []

    @classmethod
    def get_authorized_schema_prompt(
        cls,
        db: Session,
        role_id: Optional[int] = None,
        connection_id: int = 1,
        is_admin: bool = False,
        user_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Returns compact prompt text containing schema definition for allowed tables/columns
        plus semantic descriptions, and sets of allowed_tables & blocked_columns for AST validation.
        Prunes tables that do not exist physically in the currently active database.
        """
        target_db_path = cls.resolve_db_path(db, connection_id)
        physical_tables = cls.get_physical_db_tables(target_db_path)

        # Determine effective role_id and permissions
        effective_role_id = role_id
        if effective_role_id is None and user_role:
            role_obj = db.query(Role).filter(Role.name == user_role).first()
            if role_obj:
                effective_role_id = role_obj.id

        blocked_columns: Set[str] = set()
        column_perm_map: Dict[str, str] = {}

        if is_admin:
            catalog_entries = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == connection_id
            ).all()

            raw_catalog_tables = {e.table_name.lower() for e in catalog_entries if e.table_name}
            if physical_tables and raw_catalog_tables:
                overlap = {t for t in raw_catalog_tables if t in physical_tables}
                allowed_tables = overlap if overlap else raw_catalog_tables
            elif raw_catalog_tables:
                allowed_tables = raw_catalog_tables
            elif physical_tables:
                allowed_tables = set(physical_tables)
            else:
                allowed_tables = set()
        else:
            table_perms = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == effective_role_id,
                RoleTablePermission.connection_id == connection_id,
                RoleTablePermission.is_allowed == True
            ).all() if effective_role_id is not None else []

            raw_allowed = {tp.table_name.lower() for tp in table_perms}
            if physical_tables:
                overlap = {t for t in raw_allowed if t in physical_tables}
                allowed_tables = overlap if overlap else raw_allowed
            else:
                allowed_tables = raw_allowed

            col_perms = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == effective_role_id,
                RoleColumnPermission.connection_id == connection_id
            ).all() if effective_role_id is not None else []

            for cp in col_perms:
                key = f"{cp.table_name.lower()}.{cp.column_name.lower()}"
                column_perm_map[key] = cp.permission_type.value
                if cp.permission_type == ColumnPermissionType.BLOCKED:
                    blocked_columns.add(cp.column_name.lower())

            catalog_entries = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == connection_id
            ).all()

        catalog_desc_map: Dict[str, str] = {}
        for entry in catalog_entries:
            key = f"{entry.table_name.lower()}.{entry.column_name.lower() if entry.column_name else '*'}"
            catalog_desc_map[key] = entry.description or entry.business_formula or ""

        # Build comprehensive schema definition from physical database inspection
        schema_text_lines = []
        table_columns_map: Dict[str, List[str]] = {}

        for tbl in sorted(list(allowed_tables)):
            phys_cols = cls.get_physical_table_columns(tbl, target_db_path)
            table_columns_map[tbl] = []

            col_lines = []
            if phys_cols:
                for pc in phys_cols:
                    c_name = pc["name"]
                    c_lower = c_name.lower()
                    if c_lower in blocked_columns or column_perm_map.get(f"{tbl}.{c_lower}") == "BLOCKED":
                        continue

                    table_columns_map[tbl].append(c_name)
                    desc = catalog_desc_map.get(f"{tbl}.{c_lower}", "")
                    is_masked = column_perm_map.get(f"{tbl}.{c_lower}") == "MASKED"
                    samples = pc.get("samples", [])
                    sample_str = f", ej: {', '.join([repr(s) if not s.replace('.', '', 1).isdigit() else s for s in samples])}" if samples else ""
                    
                    details = f"{c_name} ({pc['type']}{sample_str})"
                    if desc:
                        details += f" - {desc}"
                    if is_masked:
                        details += " [ENMASCARADO]"
                    col_lines.append(details)
            else:
                # Fallback if SQLite introspection is unavailable
                for entry in catalog_entries:
                    if entry.table_name.lower() == tbl and entry.column_name:
                        c_name = entry.column_name
                        c_lower = c_name.lower()
                        if c_lower not in blocked_columns and column_perm_map.get(f"{tbl}.{c_lower}") != "BLOCKED":
                            col_lines.append(f"{c_name} - {entry.description or ''}".strip())
                            table_columns_map[tbl].append(c_name)

            if col_lines:
                schema_text_lines.append(f"Tabla `{tbl}`:\n  - " + "\n  - ".join(col_lines))
            else:
                schema_text_lines.append(f"Tabla `{tbl}` (Columnas de solo lectura)")

        # Auto-detect foreign key / join relationships
        relationships = []
        tables_list = list(table_columns_map.keys())
        for i in range(len(tables_list)):
            for j in range(i + 1, len(tables_list)):
                t1, t2 = tables_list[i], tables_list[j]
                cols1 = {c.lower(): c for c in table_columns_map[t1]}
                cols2 = {c.lower(): c for c in table_columns_map[t2]}
                common = set(cols1.keys()).intersection(set(cols2.keys()))
                for c in common:
                    if c.endswith("id") or c == "id" or "key" in c:
                        relationships.append(f"{t1}.{cols1[c]} = {t2}.{cols2[c]}")

        if relationships:
            schema_text_lines.append("\nRelaciones (JOIN) detectadas entre tablas:\n  - " + "\n  - ".join(relationships))

        return {
            "schema_prompt": "\n\n".join(schema_text_lines) if schema_text_lines else "Esquema de la base de datos activa.",
            "allowed_tables": allowed_tables,
            "blocked_columns": blocked_columns
        }
