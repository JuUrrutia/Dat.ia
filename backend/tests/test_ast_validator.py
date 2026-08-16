import pytest
from app.services.ast_validator import ASTValidator, ASTValidationError

def test_valid_select_query():
    sql = "SELECT id, monto, fecha FROM fact_ventas WHERE fecha >= '2026-01-01'"
    is_valid, secured_sql, meta = ASTValidator.validate_and_secure_sql(
        sql,
        dialect="postgres",
        allowed_tables={"fact_ventas"}
    )
    assert is_valid is True
    assert "LIMIT 1000" in secured_sql
    assert "fact_ventas" in meta["tables_used"]

def test_reject_dml_operation():
    sql = "DELETE FROM fact_ventas WHERE id = 1"
    with pytest.raises(ASTValidationError) as excinfo:
        ASTValidator.validate_and_secure_sql(sql, allowed_tables={"fact_ventas"})
    assert "Únicamente se permiten consultas SELECT" in str(excinfo.value)

def test_reject_semicolon_chaining():
    sql = "SELECT * FROM fact_ventas; DROP TABLE dim_clientes;"
    with pytest.raises(ASTValidationError) as excinfo:
        ASTValidator.validate_and_secure_sql(sql, allowed_tables={"fact_ventas"})
    assert "Se prohíbe el encadenamiento" in str(excinfo.value)

def test_reject_unauthorized_table():
    sql = "SELECT * FROM dim_empleados_rrhh"
    with pytest.raises(ASTValidationError) as excinfo:
        ASTValidator.validate_and_secure_sql(sql, allowed_tables={"fact_ventas", "dim_productos"})
    assert "no tiene autorización sobre la(s) tabla(s): dim_empleados_rrhh" in str(excinfo.value)

def test_reject_blocked_column():
    sql = "SELECT id, salario_base FROM fact_ventas"
    with pytest.raises(ASTValidationError) as excinfo:
        ASTValidator.validate_and_secure_sql(
            sql,
            allowed_tables={"fact_ventas"},
            blocked_columns={"salario_base"}
        )
    assert "columna(s) confidencial(es) no permitidas: salario_base" in str(excinfo.value)
