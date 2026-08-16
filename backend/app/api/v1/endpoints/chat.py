from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.query_schema import QueryRequest, QueryResponse
from app.services.query_engine import QueryEngine
from app.core.constants import ADMIN_ROLES, DEFAULT_DEMO_ROLE, ROLE_USUARIO, ROLE_ADMINISTRADOR

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def process_chat_query(
    query_in: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Processes natural language or suggestion chip query against demo_corporativa.db.
    Invokes Local LLM (llama.exe serve / Ollama), applies RBAC permissions & AST Guardrail validation.
    """
    user_role_name = current_user.role.name if current_user.role else (ROLE_ADMINISTRADOR if current_user.is_admin else ROLE_USUARIO)
    
    response = await QueryEngine.execute_query(
        question=query_in.question,
        user_role=user_role_name,
        is_admin=current_user.is_admin,
        db=db,
        role_id=current_user.role_id,
        connection_id=query_in.connection_id or 1
    )
    return response

@router.post("/query-open", response_model=QueryResponse)
async def process_chat_query_open(
    query_in: QueryRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Open endpoint (no JWT required) for demo/desktop mode.
    Receives user_role directly from the request body.
    Still applies RBAC rules and AST validation against demo_corporativa.db.
    """
    user_role = query_in.user_role or DEFAULT_DEMO_ROLE
    is_admin = user_role in ADMIN_ROLES

    response = await QueryEngine.execute_query(
        question=query_in.question,
        user_role=user_role,
        is_admin=is_admin,
        db=db,
        connection_id=query_in.connection_id or 1
    )
    return response
