import asyncio
import logging
import datetime
import json
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session


from app.api.deps import get_db, get_current_user, get_current_user_optional, get_current_admin
from app.core.database import SessionLocal
from app.modules.auth.models import User
from app.modules.telemetry_audit.models import AuditLog
from app.modules.admin_catalog.models import CorporateConnection
from app.modules.chat_engine.models import ChatConversation, QueryLearningMemory, DashboardWidget
from app.modules.chat_engine.schemas import (
    QueryRequest, QueryResponse, SuggestionsResponse,
    ChatThreadCreate, ChatThreadSummary, ChatThreadDetail,
    ChatFeedbackRequest, ChatFeedbackResponse,
    DashboardWidgetCreate, DashboardWidgetOut,
    GoldenQueryRequest
)
from app.modules.chat_engine.engine import QueryEngine
from app.modules.chat_engine.llm_diagnostic_router import llm_diagnostic_router

from app.core.constants import ADMIN_ROLES, ROLE_USUARIO, ROLE_ADMINISTRADOR
from app.core.database import discard_failed_transaction

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
        # Es una etiqueta para el audit log: si falla, se usa el nombre por defecto.
        # Sin rollback, la transaccion abortada hacia que TODO lo que viniera
        # despues en esta request (`QueryEngine.execute_query`) fallara con
        # `InFailedSqlTransaction`, blaming a una etiqueta de auditoria.
        discard_failed_transaction(db)
    return "demo_corporativa.db"

def _persist_audit_log(
    db: Session,
    user_id: Optional[int],
    username: str,
    user_role: Optional[str],
    question_prompt: str,
    sql_generated: Optional[str],
    # `None` = "esta consulta no tiene registro de validacion". NO es un valor
    # decorativo: el export de compliance lee esta columna de la BD y antes
    # confundia "no lo se" con "APROBADO", que es una afirmacion distinta.
    validation_status: Optional[str],
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
        # Sin trazabilidad NO se inventa un estado: se persiste `None`. Este `else
        # "APROBADO"` era la raiz del problema en cadena — escribia una validacion
        # que nadie hacia, y como `validation_status` era NOT NULL (ver
        # telemetry_audit/models.py) era la unica opcion del modelo. Los exporters
        # ya saben pintar "Sin registro de validacion" cuando el campo viene vacio,
        # pero con este `else` ese camino era inalcanzable: el valor falso nunca
        # llegaba a la BD, llegaba como "APROBADO" legal.
        v_status = response.traceability.validation_status if response.traceability else None
        exec_time = response.traceability.execution_time_ms if response.traceability else 0
        rows_ret = response.traceability.rows_returned if response.traceability else len(response.data_rows)
        err_msg = response.summary_text if (
            (v_status or "").startswith("RECHAZADO") or response.response_type == "error"
        ) else None

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


@router.post("/query/stream")
async def process_chat_query_stream(
    query_in: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Variante stremeada de `POST /chat/query`. Misma autenticacion, misma
    gobernanza, misma auditoria, misma respuesta final.

    Por que un endpoint NUEVO y no un flag en el de hoy
    ---------------------------------------------------
    `POST /chat/query` queda intacto y es la red de seguridad. Si el stream
    falla, se corta a mitad, o el navegador no soporta la lectura por chunks, el
    cliente repite por el camino de siempre y obtiene la respuesta completa. Un
    endpoint unico que ahora stremea dejaria de existir ese camino.

    Que se emite
    ------------
    Tres eventos, y solo tres:
      - `meta`   : una vez al abrir. Dice que arranco. No dice "cuanto falta".
      - `delta`  : pedazos de la NARRATIVA, texto real del LLM. Nunca SQL,
                   nunca `rows`, nunca `rows_returned`.
      - `result` : la MISMA `QueryResponse` que devuelve `POST /chat/query`.

    El evento `result` es lo que el cliente usa como verdad. Los `delta` son solo
    lectura anticipada: si el stream se corta antes, el cliente tiene texto
    parcial pero NO tiene resultado, y por lo tantoTodavia no commiteo nada al
    hilo. Esa es la garantia de que no queda media respuesta pegada en el chat.

    Autenticacion
    ------------
    `get_current_user` lee el header `Authorization`, igual que el resto de la
    API. No hay token en la query string: `EventSource` no soporta POST ni
    headers, pero el cliente no usa `EventSource` sino `fetch` + `getReader()`,
    que si los soporta. Un JWT en la URL quedaria en los logs del servidor y en
    el historial del navegador; no hace falta.
    """
    user_role_name = current_user.role.name if current_user.role else (ROLE_ADMINISTRADOR if current_user.is_admin else ROLE_USUARIO)
    conn_id = query_in.connection_id or 1

    # Los datos del usuario y la sesion se leen ANTES de abrir el stream. Durante
    # la generacion el generador corre sobre su propia sesion: `current_user`
    # queda desasociado al cerrarse la de la request, y `user_role_name` /
    # `is_admin` son valores planos que sobreviven.
    is_admin = current_user.is_admin
    user_id = current_user.id
    username = current_user.username
    role_id = current_user.role_id

    async def event_stream():
        stream_db = SessionLocal()
        queue: asyncio.Queue = asyncio.Queue()

        async def push_delta(text: str) -> None:
            await queue.put(("delta", text))

        async def run_query() -> None:
            """Corre el motor y publica el resultado. Nunca propaga excepciones."""
            try:
                target_db_name = _resolve_target_database(stream_db, conn_id)
                response = await QueryEngine.execute_query(
                    question=query_in.question,
                    user_role=user_role_name,
                    is_admin=is_admin,
                    db=stream_db,
                    role_id=role_id,
                    connection_id=conn_id,
                    conversation_history=query_in.conversation_history,
                    narrative_sink=push_delta
                )

                # La auditoria se persiste sobre la MISMA logica que usa
                # `POST /chat/query`. Un stream no puede dejar de registrar lo que
                # el usuario leyo: es el mismo dato corporativo,WER la misma
                # evidencia de compliance.
                sql_gen = response.traceability.sql_executed if response.traceability else None
                v_status = response.traceability.validation_status if response.traceability else None
                exec_time = response.traceability.execution_time_ms if response.traceability else 0
                rows_ret = response.traceability.rows_returned if response.traceability else len(response.data_rows)
                err_msg = response.summary_text if (
                    (v_status or "").startswith("RECHAZADO") or response.response_type == "error"
                ) else None
                try:
                    snapshot_json = response.model_dump_json()
                except Exception:
                    snapshot_json = None

                audit_id = _persist_audit_log(
                    db=stream_db,
                    user_id=user_id,
                    username=username,
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

                await queue.put(("result", response))
            except Exception as exc:
                logger.warning(f"Error en stream de chat: {exc}")
                await queue.put(("error", str(exc)))
            finally:
                await queue.put(("done", None))

        task = asyncio.create_task(run_query())

        try:
            yield _sse("meta", {"streaming": True})
            while True:
                kind, payload = await queue.get()
                if kind == "done":
                    break
                if kind == "delta":
                    yield _sse("delta", {"text": payload})
                elif kind == "result":
                    yield _sse("result", json.loads(payload.model_dump_json()))
                elif kind == "error":
                    # El error viaja como evento, no como HTTP status: las
                    # cabeceras ya se enviaron al empezar el stream. El cliente
                    # lo trata como "no hay resultado" y cae a `POST /chat/query`.
                    yield _sse("error", {"message": payload})
        finally:
            # El cliente se fue (cancelo o timeout). El trabajo del servidor NO se
            # deshizo: el motor local puede seguir hasta terminar. Solo se deja
            # de escribir en una conexion que ya no esta.
            if not task.done():
                task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            stream_db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # Sin buffering en proxies: `nginx` por defecto acumula la respuesta
            # y el usuario no veria los deltas hasta el final, que es justo lo
            # que este endpoint existe para evitar.
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: Any) -> str:
    """Serializa un evento SSE.

    El `data` va en una sola linea porque el parser del cliente parte por lineas.
    `json.dumps` escapa los saltos de linea reales dentro del string, asi que una
    narrativa con parrafos no rompe el framing.
    """
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


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

    # Resolve active connection when omitted
    effective_conn_id = connection_id
    if effective_conn_id is None and db is not None:
        try:
            from app.modules.admin_catalog.models import CorporateConnection
            active_c = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).order_by(CorporateConnection.id.desc()).first()
            if not active_c:
                active_c = db.query(CorporateConnection).order_by(CorporateConnection.id.desc()).first()
            if active_c:
                effective_conn_id = active_c.id
        except Exception:
            # Sin conexion resuelta, `effective_conn_id` queda None y el prompt
            # degrada. Lo que no puede pasar es devolver la sesion abortada.
            discard_failed_transaction(db)

    allowed_tables = QueryEngine.get_allowed_tables_for_role(
        user_role=role_name,
        is_admin=is_admin,
        db=db,
        role_id=current_user.role_id,
        connection_id=effective_conn_id
    )

    schema_prompt = ""
    try:
        from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
        s_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=db,
            user_role=role_name,
            role_id=current_user.role_id,
            is_admin=is_admin,
            connection_id=effective_conn_id
        )
        schema_prompt = s_info.get("schema_prompt", "")
    except Exception:
        # Sin prompt de esquema las sugerencias siguen siendo genericas: ese es el
        # best-effort. La sesion, en cambio, tiene que quedar limpia.
        discard_failed_transaction(db)

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

@router.get("/threads/shared/{thread_id}", response_model=ChatThreadDetail)
def get_shared_chat_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Gets details and all QueryResult messages for a conversation thread the owner marked as shared.

    Solo se sirve si `is_shared` es True. Antes el endpoint filtraba unicamente por
    id, asi que cualquier usuario autenticado que人要figurara un id podia leer los
    `data_rows` corporativos de otro. Los mensajes contienen filas reales de la BD
    del cliente, no un resumen.
    """
    thread = db.query(ChatConversation).filter(
        ChatConversation.id == thread_id,
        ChatConversation.is_shared.is_(True),
    ).first()
    if not thread:
        # 404 y no 403: no revelamos si el hilo existe pero es privado.
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
    # Query by (id, user_id): el id lo elige el cliente, asi que buscar solo por id
    # permitia que un usuario enviara el id de un hilo ajeno, lo sobreescribiera y
    # además se quedara con el (`thread.user_id = current_user.id` de abajo).
    thread = db.query(ChatConversation).filter(
        ChatConversation.id == thread_in.id,
        ChatConversation.user_id == current_user.id,
    ).first()

    msgs_json = json.dumps(thread_in.results)

    if thread:
        thread.title = thread_in.title
        thread.connection_id = thread_in.connection_id or 1
        thread.messages_json = msgs_json
        thread.is_shared = bool(getattr(thread_in, "is_shared", False))
        thread.updated_at = datetime.datetime.utcnow()
    else:
        thread = ChatConversation(
            id=thread_in.id,
            user_id=current_user.id,
            title=thread_in.title,
            connection_id=thread_in.connection_id or 1,
            messages_json=msgs_json,
            is_shared=bool(getattr(thread_in, "is_shared", False)),
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        db.add(thread)

    try:
        db.commit()
    except Exception:
        db.rollback()
        # Carrera real: otra peticion creo el hilo con el mismo id entre nuestro
        # SELECT y nuestro INSERT. Se recupera SOLO el hilo propio.
        #
        # Este bloque era la segunda puerta del secuestro de hilos: buscaba por id
        # sin user_id y asignaba `thread.user_id = current_user.id`, asi que un
        # INSERT con el id de otro (y el choque de primary key) terminaba
        # apropiandose del hilo ajeno. El filtro por user_id lo cierra.
        thread = db.query(ChatConversation).filter(
            ChatConversation.id == thread_in.id,
            ChatConversation.user_id == current_user.id,
        ).first()
        if thread:
            thread.title = thread_in.title
            thread.connection_id = thread_in.connection_id or 1
            thread.messages_json = msgs_json
            thread.is_shared = bool(getattr(thread_in, "is_shared", False))
            thread.updated_at = datetime.datetime.utcnow()
            db.commit()

    if thread is None or not getattr(thread, "id", None):
        # El id ya existe y es de otro usuario: es un intento de sobrescritura sobre
        # un hilo ajeno. No se revela nada mas alla del conflicto de clave primaria.
        raise HTTPException(status_code=409, detail="El identificador de hilo ya está en uso.")

    if thread:
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
    if not thread:
        # Antes devolvia success=True tambien cuando el hilo no existia (o era
        # de otro usuario), asi que el llamador no podia distinguir borrado de
        # no-hallado y un DELETE reintentado parecia haber hecho algo.
        raise HTTPException(status_code=404, detail="Hilo de conversación no encontrado.")
    db.delete(thread)
    db.commit()
    return {"success": True, "message": "Hilo eliminado correctamente"}

@router.delete("/threads")
def clear_chat_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Clears all conversation threads for the current user.

    A diferencia de `DELETE /threads/{id}`, acá NO hay 404: la semantica es "borra
    todo lo mio" y no haber nada que borrar es un no-op honesto, no un error (si no,
    un segundo click del usuario — o un retry de red — fallaria). Lo que si se hace
    es devolver `deleted_count`, para que el llamador pueda distinguir "borre 3" de
    "no habia nada" en vez de leer un `success: True` indistinguible.
    """
    deleted = db.query(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()
    if deleted:
        msg = f"{deleted} hilo(s) eliminado(s)"
    else:
        msg = "No había hilos para eliminar"
    return {"success": True, "message": msg, "deleted_count": deleted}

# =========================================================================
# QUERY FEEDBACK & SELF-LEARNING ENDPOINTS
# =========================================================================

def _is_admin(user: User) -> bool:
    """Admin segun la misma regla que `get_current_admin`, pero como predicado.

    Reutilizado por los dos endpoints de learning memory: la dependencia
    `get_current_admin` levanta 403 y sirve para todo el endpoint, pero
    `submit_query_feedback` tambien sirve para no-admin (su feedback de auditoria
    es legitimo), asi que necesita el corte por rol sin cortar el endpoint entero.
    """
    role_name = user.role.name if user.role else ""
    return bool(user.is_admin or role_name in ADMIN_ROLES)

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

    # `QueryLearningMemory` es un recurso COMPARTIDO por conexion: `sql_executor`
    # lo inyecta en el prompt de todos los usuarios de esa conexion (tag
    # "[Consulta Maestra Verificada]") y no tiene columna `user_id`, asi que no se
    # puede distinguir "mi feedback" de "la memoria de la plataforma". Un
    # "Usuario Consultor" podia POSTear aqui un SQL arbitrario con
    # `is_golden: true` y contaminar el prompt de toda la empresa (y pisar la
    # golden query curada por el admin). El SQL no se ejecuta — pasa por
    # ASTValidator y governance_guard — pero el hueco de autorizacion es real.
    #
    # Corte por rol: solo admin escribe la memoria compartida. Los demas siguen
    # pudiendo calificar su propia consulta (bloque 1, ya filtrado por
    # propietario) — lo que pierden es el refuerzo few-shot, que nunca fue suyo.
    is_admin_user = _is_admin(current_user)
    if feedback_in.is_golden and not is_admin_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Solo un Administrador puede marcar consultas maestras."
        )

    # 1. Update AuditLog if available
    if feedback_in.audit_log_id:
        # Filtro por propietario: `audit_log_id` lo elige el cliente, asi que sin
        # esto cualquier usuario autenticado reescribia el `validation_status` y el
        # `error_message` de la evidencia de auditoria de otro, y ese texto libre
        # terminaba en el CSV de compliance que abre el admin.
        audit = db.query(AuditLog).filter(
            AuditLog.id == feedback_in.audit_log_id,
            AuditLog.user_id == current_user.id,
        ).first()
        if audit:
            label = "[CALIFICADO_POSITIVO]" if is_positive else "[CALIFICADO_NEGATIVO]"
            if label not in (audit.validation_status or ""):
                audit.validation_status = f"{audit.validation_status or ''} {label}".strip()
            if feedback_in.comment:
                audit.error_message = f"{audit.error_message or ''} (Feedback: {feedback_in.comment})".strip()
            db.commit()

    # 2. If positive and SQL is present, strengthen learning memory.
    # Gate por rol: la memoria es compartida (ver nota arriba). Un no-admin puede
    # calificar su consulta pero no escribir SQL en el prompt de los demas.
    if is_positive and is_admin_user and feedback_in.sql and feedback_in.question:
        clean_q = feedback_in.question.strip().lower()
        existing_mem = db.query(QueryLearningMemory).filter(
            QueryLearningMemory.connection_id == feedback_in.connection_id,
            QueryLearningMemory.question_pattern == clean_q
        ).first()

        if existing_mem:
            existing_mem.execution_count = (existing_mem.execution_count or 1) + 5
            existing_mem.successful_sql = feedback_in.sql
            if feedback_in.is_golden:
                existing_mem.is_golden = True
        else:
            new_mem = QueryLearningMemory(
                question_pattern=clean_q,
                connection_id=feedback_in.connection_id,
                user_role=current_user.role.name if current_user.role else "Usuario",
                successful_sql=feedback_in.sql,
                execution_count=5,
                was_self_healed=False,
                is_golden=bool(feedback_in.is_golden)
            )
            db.add(new_mem)
        db.commit()
        learning_saved = True

    # El mensaje tiene que concordar con `learning_saved`: antes un no-admin recibia
    # "se reforzó en la memoria de aprendizaje" aunque no se hubiera escrito nada.
    if is_positive and learning_saved:
        msg = "¡Gracias! Esta consulta se reforzó en la memoria de aprendizaje de IA."
    elif is_positive:
        msg = "¡Gracias por tu calificación! Solo un Administrador puede reforzar la memoria compartida de consultas."
    else:
        msg = "Gracias por tu feedback. Lo utilizaremos para mejorar futuras respuestas."
    return ChatFeedbackResponse(success=True, message=msg, learning_saved=learning_saved)

@router.post("/golden-query")
def toggle_golden_query(
    item_in: GoldenQueryRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """Marks or unmarks a query as a Golden Sample (highest priority few-shot reference).

    Solo Administrador. Este endpoint ESCRIBE el recurso compartido: ademas de no
    tener `user_id` la tabla, `toggle_golden_query` hace upsert por
    `(connection_id, question_pattern)`, asi que cualquiera que llegara aca podia
    pisar la golden query curada por el admin y suplantarla con un SQL propio, que
    despues `sql_executor` le inyecta a todos los usuarios de la conexion.
    """
    clean_q = item_in.question.strip().lower()
    mem = db.query(QueryLearningMemory).filter(
        QueryLearningMemory.connection_id == item_in.connection_id,
        QueryLearningMemory.question_pattern == clean_q
    ).first()
    if mem:
        mem.is_golden = item_in.is_golden
        mem.successful_sql = item_in.sql
    else:
        mem = QueryLearningMemory(
            question_pattern=clean_q,
            connection_id=item_in.connection_id,
            user_role=current_admin.role.name if current_admin.role else "Usuario",
            successful_sql=item_in.sql,
            execution_count=10,
            was_self_healed=False,
            is_golden=item_in.is_golden
        )
        db.add(mem)
    db.commit()
    msg = "Consulta marcada como Consulta Maestra (Golden Sample)." if item_in.is_golden else "Consulta desmarcada como Consulta Maestra."
    return {"success": True, "message": msg, "is_golden": item_in.is_golden}


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
    """Unpins / deletes a widget from the user's dashboard.

    Mismo patron que ya se corrigio en `delete_chat_thread`: el filtro por
    `user_id` evita el IDOR, pero el `if w:` sin `else` hacia que un widget
    inexistente (o ajeno) respondiera `success: True` igual. Aca la semantica SI
    es "borra ESTE widget", asi que no haberlo es 404.
    """
    w = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.user_id == current_user.id
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget no encontrado")
    db.delete(w)
    db.commit()
    return {"success": True, "message": "Widget removido del tablero"}

