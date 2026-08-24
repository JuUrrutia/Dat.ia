import logging
from typing import List, Set, Dict, Tuple, Optional, Any
import sqlglot
from sqlglot import exp, parse_one, transpile
from app.core.config import settings
from app.core.logging import logger

class ASTValidationError(Exception):
    """Custom exception raised when SQL fails AST security or RBAC validation."""
    pass

class ASTValidator:
    """
    SQL Guardrail & AST Security Parser based on sqlglot.
    Enforces read-only SELECT queries, single statement execution,
    role-based table/column whitelisting, Star expansion for Column-Level Security (CLS),
    and automatic LIMIT injection.
    """

    ALLOWED_DIALECTS = {"postgres", "tsql", "mysql", "oracle", "sqlite"}

    @classmethod
    def validate_and_secure_sql(
        cls,
        raw_sql: str,
        dialect: str = "postgres",
        allowed_tables: Optional[Set[str]] = None,
        blocked_columns: Optional[Set[str]] = None,
        table_columns: Optional[Dict[str, List[str]]] = None,
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
            allowed_set = {t.lower() for t in allowed_tables}
            unauthorized_tables = extracted_tables - allowed_set
            if unauthorized_tables:
                raise ASTValidationError(
                    "Gobernanza RBAC: Acceso denegado. No tienes permisos para acceder ni manejar estos datos."
                )

        # Rule 4.5: Expand SELECT * / table.* to explicit allowed columns
        has_star = expression.find(exp.Star) is not None
        if has_star:
            if table_columns:
                norm_table_cols: Dict[str, List[str]] = {
                    t.lower(): [str(c) for c in cols]
                    for t, cols in table_columns.items()
                }
                blocked_set = {c.lower() for c in blocked_columns} if blocked_columns else set()

                for select_node in expression.find_all(exp.Select):
                    table_nodes = list(select_node.find_all(exp.Table))
                    alias_to_table: Dict[str, str] = {}
                    table_list: List[Tuple[str, str]] = []

                    for t_node in table_nodes:
                        t_name = t_node.name.lower() if t_node.name else ""
                        if t_name:
                            t_alias = t_node.alias.lower() if t_node.alias else ""
                            table_list.append((t_name, t_node.alias or ""))
                            if t_alias:
                                alias_to_table[t_alias] = t_name
                            alias_to_table[t_name] = t_name

                    new_expressions = []
                    expanded_any_star = False

                    for expr_item in select_node.expressions:
                        is_simple_star = isinstance(expr_item, exp.Star)
                        is_col_star = (
                            isinstance(expr_item, exp.Column)
                            and isinstance(expr_item.this, exp.Star)
                        )

                        if is_simple_star:
                            expanded_any_star = True
                            if not table_list:
                                target_tables = sorted(list(extracted_tables))
                                for t_name in target_tables:
                                    phys_cols = norm_table_cols.get(t_name, [])
                                    vis_cols = [c for c in phys_cols if c.lower() not in blocked_set]
                                    if not vis_cols and phys_cols:
                                        raise ASTValidationError(
                                            f"Gobernanza RBAC: Acceso denegado. No tienes columnas autorizadas para visualizar en la tabla '{t_name}'."
                                        )
                                    for c in vis_cols:
                                        new_expressions.append(exp.Column(this=exp.to_identifier(c)))
                            else:
                                for t_name, t_alias in table_list:
                                    phys_cols = norm_table_cols.get(t_name, [])
                                    vis_cols = [c for c in phys_cols if c.lower() not in blocked_set]
                                    if not vis_cols and phys_cols:
                                        raise ASTValidationError(
                                            f"Gobernanza RBAC: Acceso denegado. No tienes columnas autorizadas para visualizar en la tabla '{t_name}'."
                                        )
                                    for c in vis_cols:
                                        if len(table_list) > 1 and t_alias:
                                            new_expressions.append(
                                                exp.Column(this=exp.to_identifier(c), table=exp.to_identifier(t_alias))
                                            )
                                        elif len(table_list) > 1:
                                            new_expressions.append(
                                                exp.Column(this=exp.to_identifier(c), table=exp.to_identifier(t_name))
                                            )
                                        else:
                                            new_expressions.append(exp.Column(this=exp.to_identifier(c)))

                        elif is_col_star:
                            expanded_any_star = True
                            target_ref = expr_item.table.lower() if expr_item.table else ""
                            target_table = alias_to_table.get(target_ref, target_ref)
                            phys_cols = norm_table_cols.get(target_table, [])
                            vis_cols = [c for c in phys_cols if c.lower() not in blocked_set]
                            if not vis_cols and phys_cols:
                                raise ASTValidationError(
                                    f"Gobernanza RBAC: Acceso denegado. No tienes columnas autorizadas para visualizar en la tabla '{target_table}'."
                                )
                            for c in vis_cols:
                                if expr_item.table:
                                    new_expressions.append(
                                        exp.Column(this=exp.to_identifier(c), table=exp.to_identifier(expr_item.table))
                                    )
                                else:
                                    new_expressions.append(exp.Column(this=exp.to_identifier(c)))

                        else:
                            new_expressions.append(expr_item)

                    if expanded_any_star:
                        if not new_expressions:
                            raise ASTValidationError(
                                "Gobernanza RBAC: Acceso denegado. No tienes columnas autorizadas para visualizar en la consulta."
                            )
                        select_node.set("expressions", new_expressions)
            else:
                logger.warning("CLS: SELECT * validado sin expansión de esquema, no se puede garantizar bloqueo de columnas")

        # Rule 5: Extract and Validate Columns against Blocked List
        extracted_columns = set()
        for column_node in expression.find_all(exp.Column):
            if not isinstance(column_node.this, exp.Star):
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
            expression = expression.limit(max_limit)
        else:
            try:
                current_val = int(existing_limit.expression.this)
                if current_val > max_limit:
                    expression.args["limit"].expression.this = str(max_limit)
            except Exception:
                expression.args["limit"].expression.this = str(max_limit)

        sanitized_sql = expression.sql(dialect=sqlglot_dialect)

        metadata = {
            "tables_used": list(extracted_tables),
            "columns_used": list(extracted_columns),
            "limit_applied": max_limit,
            "dialect": sqlglot_dialect
        }

        return True, sanitized_sql, metadata
