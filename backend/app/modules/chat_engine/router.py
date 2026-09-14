import logging
import datetime
import json
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session


from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.modules.auth.models import User
from app.modules.telemetry_audit.models import AuditLog
from app.modules.admin_catalog.models import CorporateConnection
from app.modules.chat_engine.models import ChatConversation, QueryLearningMemory, DashboardWidget
from app.modules.chat_engine.schemas import (
    QueryRequest, QueryResponse, SuggestionsResponse,
    ChatThreadCreate, ChatThreadSummary, ChatThreadDetail,
    ChatFeedbackRequest, ChatFeedbackResponse,
    DashboardWidgetCreate, DashboardWidgetOut
)
from app.modules.chat_engine.engine import QueryEngine
from app.modules.chat_engine.llm_diagnostic_router import llm_diagnostic_router

from app.core.constants import ADMIN_ROLES, ROLE_USUARIO, ROLE_ADMINISTRADOR

router = APIRouter()
logger = logging.getLogger(__name__)

# Mount LLM diagnostic and testing routes
router.include_router(llm_diagnostic_router)

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
    error_message: Optional[str] = None,
    result_snapshot: Optional[str] = None
) -> Optional[int]:
    """Safely persists an AuditLog record in a best-effort transaction and returns its ID."""
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
            error_message=error_message,
            result_snapshot=result_snapshot
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry.id
    except Exception as e:
        db.rollback()
        logger.warning(f"Error registrando auditoría: {e}")
        return None

@router.post("/query", response_model=QueryResponse)
async def process_chat_query(
    query_in: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Processes natural language or suggestion chip query against target database.
    Invokes Local LLM, applies RBAC permissions & AST Guardrail validation.
    Persists audit log of approval or rejection with result snapshot.
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
            connection_id=conn_id,
            conversation_history=query_in.conversation_history
        )


        sql_gen = response.traceability.sql_executed if response.traceability else None
        v_status = response.traceability.validation_status if response.traceability else "APROBADO"
        exec_time = response.traceability.execution_time_ms if response.traceability else 0
        rows_ret = response.traceability.rows_returned if response.traceability else len(response.data_rows)
        err_msg = response.summary_text if (v_status.startswith("RECHAZADO") or response.response_type == "error") else None

        try:
            snapshot_json = response.model_dump_json()
        except Exception:
            snapshot_json = None

        audit_id = _persist_audit_log(
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
            error_message=err_msg,
            result_snapshot=snapshot_json
        )

        if audit_id:
            if response.traceability:
                response.traceability.audit_log_id = audit_id
            response.audit_log_id = audit_id

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
            error_message=str(e),
            result_snapshot=None
        )
        raise


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_dynamic_suggestions(
    connection_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> SuggestionsResponse:
    """
    Returns role and table-specific question suggestions dynamically via LLM with fallback.
    """
    if current_user is None:
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

    role_name = current_user.role.name if current_user.role else (ROLE_ADMINISTRADOR if current_user.is_admin else ROLE_USUARIO)
    is_admin = current_user.is_admin or role_name in ADMIN_ROLES

    allowed_tables = QueryEngine.get_allowed_tables_for_role(
        user_role=role_name,
        is_admin=is_admin,
        db=db,
        connection_id=connection_id
    )

    schema_prompt = ""
    try:
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
        s_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=db,
            user_role=role_name,
            is_admin=is_admin,
            connection_id=connection_id
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

# =========================================================================
# CHAT THREADS PERSISTENCE & HISTORY ENDPOINTS
# =========================================================================

@router.get("/threads", response_model=List[ChatThreadSummary])
def list_chat_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Lists saved chat conversation threads for the current authenticated user."""
    threads = db.query(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).order_by(ChatConversation.updated_at.desc()).all()

    summaries = []
    for t in threads:
        try:
            msgs = json.loads(t.messages_json or "[]")
            msg_count = len(msgs)
        except Exception:
            msg_count = 0
        summaries.append(ChatThreadSummary(
            id=t.id,
            title=t.title,
            connection_id=t.connection_id or 1,
            message_count=msg_count,
            updated_at=t.updated_at.isoformat() if t.updated_at else ""
        ))
    return summaries

@router.get("/threads/{thread_id}", response_model=ChatThreadDetail)
def get_chat_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Gets details and all QueryResult messages for a specific conversation thread."""
    thread = db.query(ChatConversation).filter(
        ChatConversation.id == thread_id,
        ChatConversation.user_id == current_user.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo de conversación no encontrado")
    try:
        results = json.loads(thread.messages_json or "[]")
    except Exception:
        results = []
    return ChatThreadDetail(
        id=thread.id,
        title=thread.title,
        connection_id=thread.connection_id or 1,
        results=results,
        created_at=thread.created_at.isoformat() if thread.created_at else "",
        updated_at=thread.updated_at.isoformat() if thread.updated_at else ""
    )

@router.post("/threads", response_model=ChatThreadDetail)
def save_chat_thread(
    thread_in: ChatThreadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Creates or updates a persistent chat thread with its full results stream."""
    thread = db.query(ChatConversation).filter(
        ChatConversation.id == thread_in.id,
        ChatConversation.user_id == current_user.id
    ).first()

    msgs_json = json.dumps(thread_in.results)

    if thread:
        thread.title = thread_in.title
        thread.connection_id = thread_in.connection_id or 1
        thread.messages_json = msgs_json
        thread.updated_at = datetime.datetime.utcnow()
    else:
        thread = ChatConversation(
            id=thread_in.id,
            user_id=current_user.id,
            title=thread_in.title,
            connection_id=thread_in.connection_id or 1,
            messages_json=msgs_json,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        db.add(thread)
    db.commit()
    db.refresh(thread)

    return ChatThreadDetail(
        id=thread.id,
        title=thread.title,
        connection_id=thread.connection_id or 1,
        results=thread_in.results,
        created_at=thread.created_at.isoformat() if thread.created_at else "",
        updated_at=thread.updated_at.isoformat() if thread.updated_at else ""
    )

@router.delete("/threads/{thread_id}")
def delete_chat_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Deletes a single chat conversation thread."""
    thread = db.query(ChatConversation).filter(
        ChatConversation.id == thread_id,
        ChatConversation.user_id == current_user.id
    ).first()
    if thread:
        db.delete(thread)
        db.commit()
    return {"success": True, "message": "Hilo eliminado correctamente"}

@router.delete("/threads")
def clear_chat_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Clears all conversation threads for the current user."""
    db.query(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).delete()
    db.commit()
    return {"success": True, "message": "Todos los hilos han sido eliminados"}

# =========================================================================
# QUERY FEEDBACK & SELF-LEARNING ENDPOINTS
# =========================================================================

@router.post("/feedback", response_model=ChatFeedbackResponse)
def submit_query_feedback(
    feedback_in: ChatFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Records explicit user feedback (👍 / 👎) for a query and reinforces or demotes
    in few-shot learning memory.
    """
    learning_saved = False
    is_positive = feedback_in.rating.lower() == "positive"
    
    # 1. Update AuditLog if available
    if feedback_in.audit_log_id:
        audit = db.query(AuditLog).filter(AuditLog.id == feedback_in.audit_log_id).first()
        if audit:
            label = "[CALIFICADO_POSITIVO]" if is_positive else "[CALIFICADO_NEGATIVO]"
            if label not in audit.validation_status:
                audit.validation_status = f"{audit.validation_status} {label}"
            if feedback_in.comment:
                audit.error_message = f"{audit.error_message or ''} (Feedback: {feedback_in.comment})".strip()
            db.commit()

    # 2. If positive and SQL is present, strengthen learning memory
    if is_positive and feedback_in.sql and feedback_in.question:
        clean_q = feedback_in.question.strip().lower()
        existing_mem = db.query(QueryLearningMemory).filter(
            QueryLearningMemory.connection_id == feedback_in.connection_id,
            QueryLearningMemory.question_pattern == clean_q
        ).first()

        if existing_mem:
            existing_mem.execution_count = (existing_mem.execution_count or 1) + 5
            existing_mem.successful_sql = feedback_in.sql
        else:
            new_mem = QueryLearningMemory(
                question_pattern=clean_q,
                connection_id=feedback_in.connection_id,
                user_role=current_user.role.name if current_user.role else "Usuario",
                successful_sql=feedback_in.sql,
                execution_count=5,
                was_self_healed=False
            )
            db.add(new_mem)
        db.commit()
        learning_saved = True

    msg = (
        "¡Gracias! Esta consulta se reforzó en la memoria de aprendizaje de IA."
        if is_positive
        else "Gracias por tu feedback. Lo utilizaremos para mejorar futuras respuestas."
    )
    return ChatFeedbackResponse(success=True, message=msg, learning_saved=learning_saved)


# =========================================================================
# DASHBOARD WIDGETS (PIN TO DASHBOARD) ENDPOINTS
# =========================================================================

@router.get("/widgets", response_model=List[DashboardWidgetOut])
def list_dashboard_widgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Lists all pinned dashboard widgets for the current user."""
    widgets = db.query(DashboardWidget).filter(
        DashboardWidget.user_id == current_user.id
    ).order_by(DashboardWidget.created_at.desc()).all()
    
    return [
        DashboardWidgetOut(
            id=w.id,
            user_id=w.user_id,
            title=w.title,
            connection_id=w.connection_id,
            chart_type=w.chart_type,
            chart_option_json=w.chart_option_json,
            kpis_json=w.kpis_json,
            query_text=w.query_text,
            created_at=w.created_at.isoformat() if w.created_at else ""
        )
        for w in widgets
    ]

@router.post("/widgets", response_model=DashboardWidgetOut, status_code=status.HTTP_201_CREATED)
def pin_dashboard_widget(
    widget_in: DashboardWidgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Pins a new analytics widget to the user's executive dashboard."""
    new_widget = DashboardWidget(
        user_id=current_user.id,
        title=widget_in.title,
        connection_id=widget_in.connection_id or 1,
        chart_type=widget_in.chart_type,
        chart_option_json=widget_in.chart_option_json,
        kpis_json=widget_in.kpis_json,
        query_text=widget_in.query_text,
        created_at=datetime.datetime.utcnow()
    )
    db.add(new_widget)
    db.commit()
    db.refresh(new_widget)
    return DashboardWidgetOut(
        id=new_widget.id,
        user_id=new_widget.user_id,
        title=new_widget.title,
        connection_id=new_widget.connection_id,
        chart_type=new_widget.chart_type,
        chart_option_json=new_widget.chart_option_json,
        kpis_json=new_widget.kpis_json,
        query_text=new_widget.query_text,
        created_at=new_widget.created_at.isoformat()
    )

@router.delete("/widgets/{widget_id}")
def unpin_dashboard_widget(
    widget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Unpins / deletes a widget from the user's dashboard."""
    w = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.user_id == current_user.id
    ).first()
    if w:
        db.delete(w)
        db.commit()
    return {"success": True, "message": "Widget removido del tablero"}

