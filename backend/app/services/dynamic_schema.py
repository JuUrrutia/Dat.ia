from typing import List, Dict, Set, Any, Optional
from sqlalchemy.orm import Session
from app.models.permission import RoleTablePermission, RoleColumnPermission, ColumnPermissionType
from app.models.role import Role
from app.models.catalog import SemanticCatalog

class DynamicSchemaPruningService:
    """
    Filters database catalog definitions according to user role permissions.
    Ensures LLM context ONLY receives authorized tables and columns.
    """

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
        """
        # Admin gets full access to full database catalog
        if is_admin:
            # Fetch all catalog entries for connection
            catalog_entries = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == connection_id
            ).all()

            allowed_tables: Set[str] = set()
            blocked_columns: Set[str] = set()
            tables_map: Dict[str, List[Dict[str, str]]] = {}

            for entry in catalog_entries:
                tbl = entry.table_name.lower()
                allowed_tables.add(tbl)
                if tbl not in tables_map:
                    tables_map[tbl] = []
                if entry.column_name:
                    tables_map[tbl].append({
                        "name": entry.column_name,
                        "desc": entry.description or "",
                        "type": "ALLOWED"
                    })

            schema_text_lines = []
            for tbl, cols in tables_map.items():
                col_defs = ", ".join([f"{c['name']} ({c['desc']})" if c['desc'] else c['name'] for c in cols])
                schema_text_lines.append(f"Tabla `{tbl}`: [{col_defs}]")

            return {
                "schema_prompt": "\n".join(schema_text_lines) if schema_text_lines else "Esquema completo de la base de datos corporativa.",
                "allowed_tables": allowed_tables,
                "blocked_columns": blocked_columns
            }

        # Resolve role_id from Role model if role_id is None but user_role name is provided
        effective_role_id = role_id
        if effective_role_id is None and user_role:
            role_obj = db.query(Role).filter(Role.name == user_role).first()
            if role_obj:
                effective_role_id = role_obj.id

        # Non-admin: Query role table permissions from RoleTablePermission model
        table_perms = db.query(RoleTablePermission).filter(
            RoleTablePermission.role_id == effective_role_id,
            RoleTablePermission.connection_id == connection_id,
            RoleTablePermission.is_allowed == True
        ).all() if effective_role_id is not None else []

        allowed_tables = {tp.table_name.lower() for tp in table_perms}

        # Query role column permissions
        col_perms = db.query(RoleColumnPermission).filter(
            RoleColumnPermission.role_id == effective_role_id,
            RoleColumnPermission.connection_id == connection_id
        ).all() if effective_role_id is not None else []

        blocked_columns: Set[str] = set()
        column_perm_map: Dict[str, str] = {} # "table.column" -> ALLOWED/BLOCKED/MASKED

        for cp in col_perms:
            key = f"{cp.table_name.lower()}.{cp.column_name.lower()}"
            column_perm_map[key] = cp.permission_type.value
            if cp.permission_type == ColumnPermissionType.BLOCKED:
                blocked_columns.add(cp.column_name.lower())

        # Query catalog entries for allowed tables
        catalog_entries = db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == connection_id
        ).all()

        tables_map = {}
        for entry in catalog_entries:
            tbl = entry.table_name.lower()
            if tbl not in allowed_tables:
                continue

            col = entry.column_name.lower() if entry.column_name else None
            if col:
                perm_key = f"{tbl}.{col}"
                perm_type = column_perm_map.get(perm_key, "ALLOWED")
                if perm_type == "BLOCKED":
                    continue # Exclude from prompt

            if tbl not in tables_map:
                tables_map[tbl] = []

            if col:
                desc_str = entry.description or ""
                if perm_type == "MASKED":
                    desc_str = f"{desc_str} (VALOR ENMASCARADO - Usar solo para GROUP BY o COUNT)".strip()
                tables_map[tbl].append(f"{col}: {desc_str}" if desc_str else col)

        schema_text_lines = []
        for tbl, cols in tables_map.items():
            schema_text_lines.append(f"Tabla `{tbl}` (Campos autorizados: {', '.join(cols)})")

        return {
            "schema_prompt": "\n".join(schema_text_lines) if schema_text_lines else "No hay tablas ni campos autorizados para este rol.",
            "allowed_tables": allowed_tables,
            "blocked_columns": blocked_columns
        }
