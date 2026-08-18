from typing import List, Set, Dict, Tuple, Optional, Any
import sqlglot
from sqlglot import exp, parse_one, transpile
from app.core.config import settings

class ASTValidationError(Exception):
    """Custom exception raised when SQL fails AST security or RBAC validation."""
    pass

class ASTValidator:
    """
    SQL Guardrail & AST Security Parser based on sqlglot.
    Enforces read-only SELECT queries, single statement execution,
    role-based table/column whitelisting, and automatic LIMIT injection.
    """

    ALLOWED_DIALECTS = {"postgres", "tsql", "mysql", "oracle", "sqlite"}

    @classmethod
    def validate_and_secure_sql(
        cls,
        raw_sql: str,
        dialect: str = "postgres",
        allowed_tables: Optional[Set[str]] = None,
        blocked_columns: Optional[Set[str]] = None,
        max_limit: int = settings.DEFAULT_ROW_LIMIT
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates raw_sql against strict security rules and returns:
        (is_valid: bool, sanitized_sql_or_error: str, metadata: dict)
        """
        if not raw_sql or not raw_sql.strip():
            raise ASTValidationError("La consulta SQL está vacía.")

        clean_sql = raw_sql.strip()

        # Rule 1: Single Statement Check (Reject semicolon chaining)
        # Strip trailing semicolon
        if clean_sql.endswith(";"):
            clean_sql = clean_sql[:-1].strip()

        if ";" in clean_sql:
            raise ASTValidationError("Seguridad: Se prohíbe el encadenamiento de múltiples sentencias SQL (;).")

        # Determine sqlglot dialect
        sqlglot_dialect = dialect.lower()
        if sqlglot_dialect not in cls.ALLOWED_DIALECTS:
            sqlglot_dialect = "postgres"

        # Rule 2: Parse AST using sqlglot
        try:
            expression = parse_one(clean_sql, read=sqlglot_dialect)
        except Exception as e:
            raise ASTValidationError(f"Error de sintaxis SQL: No se pudo analizar el árbol AST ({str(e)}).")

        if expression is None:
            raise ASTValidationError("Error sintáctico: Estructura SQL no válida.")

        # Rule 3: Strictly SELECT statements only
        if not isinstance(expression, exp.Select):
            raise ASTValidationError(
                f"Seguridad: Operación prohibida. Únicamente se permiten consultas SELECT (Lectura). "
                f"Tipo detectado: {expression.key.upper()}."
            )

        # Ensure no DDL/DML mutation keywords exist anywhere in AST
        prohibited_expressions = tuple(
            getattr(exp, name) for name in ("Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command", "Grant")
            if hasattr(exp, name)
        )
        for node in expression.walk():
            if isinstance(node, prohibited_expressions):
                raise ASTValidationError(f"Seguridad: Detectada instrucción prohibida '{node.key.upper()}'.")

        # Rule 4: Extract and Validate Tables against RBAC Whitelist
        extracted_tables = set()
        for table_node in expression.find_all(exp.Table):
            table_name = table_node.name.lower()
            if table_name:
                extracted_tables.add(table_name)

        if allowed_tables is not None:
            # Normalize allowed tables to lowercase
            allowed_set = {t.lower() for t in allowed_tables}
            unauthorized_tables = extracted_tables - allowed_set
            if unauthorized_tables:
                raise ASTValidationError(
                    "Gobernanza RBAC: Acceso denegado. No tienes permisos para acceder ni manejar estos datos."
                )

        # Rule 5: Extract and Validate Columns against Blocked List
        extracted_columns = set()
        for column_node in expression.find_all(exp.Column):
            col_name = column_node.name.lower()
            if col_name:
                extracted_columns.add(col_name)

        if blocked_columns is not None:
            blocked_set = {c.lower() for c in blocked_columns}
            attempted_blocked = extracted_columns & blocked_set
            if attempted_blocked:
                raise ASTValidationError(
                    "Gobernanza RBAC: Acceso denegado. No tienes permisos para acceder ni manejar estos datos."
                )

        # Rule 6: Inject LIMIT / TOP if not present or exceeds max_limit
        existing_limit = expression.args.get("limit")
        if existing_limit is None:
            # Attach LIMIT node
            expression = expression.limit(max_limit)
        else:
            # Ensure limit does not exceed max_limit
            try:
                current_val = int(existing_limit.expression.this)
                if current_val > max_limit:
                    expression.args["limit"].expression.this = str(max_limit)
            except Exception:
                expression.args["limit"].expression.this = str(max_limit)

        # Transpile back to target dialect string
        sanitized_sql = expression.sql(dialect=sqlglot_dialect)

        metadata = {
            "tables_used": list(extracted_tables),
            "columns_used": list(extracted_columns),
            "limit_applied": max_limit,
            "dialect": sqlglot_dialect
        }

        return True, sanitized_sql, metadata
