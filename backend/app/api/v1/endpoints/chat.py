import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.connection import CorporateConnection
from app.schemas.query_schema import QueryRequest, QueryResponse, SuggestionsResponse
from app.services.query_engine import QueryEngine
from app.core.config import settings
from app.core.constants import ADMIN_ROLES, DEFAULT_DEMO_ROLE, ROLE_USUARIO, ROLE_ADMINISTRADOR, DEFAULT_USER_ROLE

router = APIRouter()
logger = logging.getLogger(__name__)

def _resolve_target_database(db: Session, connection_id: int) -> str:
    """Finds friendly target database name for audit log."""
    try:
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
        if conn and conn.name:
            return conn.name
    except Exception:
        pass
    return "demo_corporativa.db"

def _persist_audit_log(
    db: Session,
    user_id: Optional[int],
    username: str,
    user_role: Optional[str],
    question_prompt: str,
    sql_generated: Optional[str],
    validation_status: str,
    target_database: str,
    execution_time_ms: int = 0,
    rows_returned: int = 0,
    error_message: Optional[str] = None
):
    """Safely persists an AuditLog record in a best-effort transaction."""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            user_role=user_role,
            question_prompt=question_prompt,
            sql_generated=sql_generated,
            validation_status=validation_status,
            target_database=target_database,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            error_message=error_message
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error registrando auditoría: {e}")

@router.post("/query", response_model=QueryResponse)
async def process_chat_query(
    query_in: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Processes natural language or suggestion chip query against target database.
    Invokes Local LLM, applies RBAC permissions & AST Guardrail validation.
    Persists audit log of approval or rejection.
    """
    user_role_name = current_user.role.name if current_user.role else (ROLE_ADMINISTRADOR if current_user.is_admin else ROLE_USUARIO)
    conn_id = query_in.connection_id or 1
    target_db_name = _resolve_target_database(db, conn_id)

    try:
        response = await QueryEngine.execute_query(
            question=query_in.question,
            user_role=user_role_name,
            is_admin=current_user.is_admin,
            db=db,
            role_id=current_user.role_id,
            connection_id=conn_id
        )

        sql_gen = response.traceability.sql_executed if response.traceability else None
        v_status = response.traceability.validation_status if response.traceability else "APROBADO"
        exec_time = response.traceability.execution_time_ms if response.traceability else 0
        rows_ret = response.traceability.rows_returned if response.traceability else len(response.data_rows)
        err_msg = response.summary_text if (v_status.startswith("RECHAZADO") or response.response_type == "error") else None

        _persist_audit_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            user_role=user_role_name,
            question_prompt=query_in.question,
            sql_generated=sql_gen,
            validation_status=v_status,
            target_database=target_db_name,
            execution_time_ms=exec_time,
            rows_returned=rows_ret,
            error_message=err_msg
        )
        return response
    except Exception as e:
        _persist_audit_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            user_role=user_role_name,
            question_prompt=query_in.question,
            sql_generated=None,
            validation_status="ERROR_EJECUCION",
            target_database=target_db_name,
            execution_time_ms=0,
            rows_returned=0,
            error_message=str(e)
        )
        raise

@router.post("/query-open", response_model=QueryResponse)
async def process_chat_query_open(
    query_in: QueryRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Restricted demo/desktop endpoint.
    Disabled by default (returns 403 Forbidden).
    If explicitly enabled via settings.ALLOW_OPEN_DEMO_ENDPOINT=True, any client-specified
    user_role is strictly ignored to prevent RBAC bypass, and the least-privileged base role
    (ROLE_USUARIO) is enforced unconditionally.
    """
    if not settings.ALLOW_OPEN_DEMO_ENDPOINT:
        raise HTTPException(
            status_code=403,
            detail="Este endpoint está deshabilitado. Use /chat/query con autenticación JWT."
        )

    user_role = DEFAULT_USER_ROLE
    is_admin = False
    conn_id = query_in.connection_id or 1
    target_db_name = _resolve_target_database(db, conn_id)

    try:
        response = await QueryEngine.execute_query(
            question=query_in.question,
            user_role=user_role,
            is_admin=is_admin,
            db=db,
            connection_id=conn_id
        )

        sql_gen = response.traceability.sql_executed if response.traceability else None
        v_status = response.traceability.validation_status if response.traceability else "APROBADO"
        exec_time = response.traceability.execution_time_ms if response.traceability else 0
        rows_ret = response.traceability.rows_returned if response.traceability else len(response.data_rows)
        err_msg = response.summary_text if (v_status.startswith("RECHAZADO") or response.response_type == "error") else None

        _persist_audit_log(
            db=db,
            user_id=None,
            username=f"demo_{user_role.lower()}",
            user_role=user_role,
            question_prompt=query_in.question,
            sql_generated=sql_gen,
            validation_status=v_status,
            target_database=target_db_name,
            execution_time_ms=exec_time,
            rows_returned=rows_ret,
            error_message=err_msg
        )
        return response
    except Exception as e:
        _persist_audit_log(
            db=db,
            user_id=None,
            username=f"demo_{user_role.lower()}",
            user_role=user_role,
            question_prompt=query_in.question,
            sql_generated=None,
            validation_status="ERROR_EJECUCION",
            target_database=target_db_name,
            execution_time_ms=0,
            rows_returned=0,
            error_message=str(e)
        )
        raise

@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_dynamic_suggestions(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> SuggestionsResponse:
    """
    Returns role and table-specific question suggestions dynamically via LLM with fallback.
    - If user is authenticated: derives role directly from JWT session and returns authorized table suggestions and allowed_tables.
    - If user is unauthenticated: returns generic suggestions without invoking schema introspection or exposing table names (allowed_tables is None).
    """
    if current_user is None:
        # Unauthenticated: return generic static suggestions without table/domain introspection
        generic_suggestions = [
            "📊 Resumen de registros y métricas principales",
            "📈 Tendencias y distribución de datos acumulados",
            "📋 Listado detallado de tablas autorizadas",
            "💡 Consultas analíticas para toma de decisiones"
        ]
        return SuggestionsResponse(
            user_role=None,
            allowed_tables=None,
            suggestions=generic_suggestions
        )

    # Authenticated user: derive role from JWT session
    role_name = current_user.role.name if current_user.role else (ROLE_ADMINISTRADOR if current_user.is_admin else ROLE_USUARIO)
    is_admin = current_user.is_admin or role_name in ADMIN_ROLES

    allowed_tables = QueryEngine.get_allowed_tables_for_role(
        user_role=role_name,
        is_admin=is_admin,
        db=db
    )

    schema_prompt = ""
    try:
        from app.services.dynamic_schema import DynamicSchemaPruningService
        s_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=db,
            user_role=role_name,
            is_admin=is_admin
        )
        schema_prompt = s_info.get("schema_prompt", "")
    except Exception:
        pass

    suggestions = await QueryEngine.get_dynamic_suggestions_with_llm(
        user_role=role_name,
        allowed_tables=allowed_tables,
        schema_prompt=schema_prompt
    )

    return SuggestionsResponse(
        user_role=role_name,
        allowed_tables=list(allowed_tables),
        suggestions=suggestions
    )
