import time
import os
import datetime
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.connection import CorporateConnection, DatabaseType
from app.core.config import settings
from app.core.constants import (
    SYSTEM_STATUS_OPERATIONAL,
    SYSTEM_STATUS_DEGRADED,
    SYSTEM_STATUS_CRITICAL,
)
from app.schemas.system_schema import ComponentHealth, SystemHealthResponse
from app.services.health_service import HealthService

router = APIRouter()

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SystemHealthResponse:
    """
    Returns unified health & operational status of core system components:
    - Active local LLM engine (Ollama / llama.cpp)
    - Metadata database
    - Active registered corporate database connectors
    """
    # 1. Check LLM Engine
    llm_res = await HealthService.check_llm_connectivity(
        provider=settings.LLM_PROVIDER,
        base_url=settings.OLLAMA_BASE_URL,
        model_name=settings.OLLAMA_MODEL,
        timeout=2.5
    )
    llm_ok = llm_res["success"]
    llm_comp = ComponentHealth(
        name=f"Motor LLM ({settings.OLLAMA_MODEL})",
        type="llm",
        status=SYSTEM_STATUS_OPERATIONAL if llm_ok else SYSTEM_STATUS_CRITICAL,
        latency_ms=llm_res.get("latency_ms", 0),
        message=llm_res.get("message", ""),
        details={
            "provider": settings.LLM_PROVIDER,
            "base_url": settings.OLLAMA_BASE_URL,
            "available_models": llm_res.get("available_models", [])
        }
    )

    # 2. Check Metadata DB
    start_meta = time.time()
    try:
        db.execute(text("SELECT 1"))
        meta_latency = int((time.time() - start_meta) * 1000)
        meta_ok = True
        meta_msg = "Base de datos de metadatos operativa y respondiendo."
    except Exception as e:
        meta_latency = int((time.time() - start_meta) * 1000)
        meta_ok = False
        meta_msg = f"Error en base de datos de metadatos: {str(e)}"

    meta_comp = ComponentHealth(
        name="Metadata Store (Datia DB)",
        type="metadata_db",
        status=SYSTEM_STATUS_OPERATIONAL if meta_ok else SYSTEM_STATUS_DEGRADED,
        latency_ms=meta_latency,
        message=meta_msg
    )

    # 3. Check Active Corporate Connectors
    active_conns = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).all()
    connectors_health: List[ComponentHealth] = []
    healthy_count = 0

    for c in active_conns:
        if c.db_type == DatabaseType.SQLITE:
            # SQLite local file check
            db_path = c.database_name
            exists = os.path.exists(db_path) if db_path else True
            conn_ok = exists
            conn_msg = f"Archivo SQLite '{db_path}' verificado." if exists else f"Archivo SQLite '{db_path}' no encontrado."
            conn_latency = 1
        else:
            # Socket connectivity check for PostgreSQL, MySQL, SQL Server
            res = HealthService.check_db_connectivity(
                host=c.host,
                port=c.port,
                timeout=2.0,
                db_type=c.db_type.value,
                database_name=c.database_name
            )
            conn_ok = res["success"]
            conn_msg = res["message"]
            conn_latency = res["latency_ms"]

        if conn_ok:
            healthy_count += 1

        connectors_health.append(
            ComponentHealth(
                name=c.name,
                type="connector",
                status=SYSTEM_STATUS_OPERATIONAL if conn_ok else SYSTEM_STATUS_DEGRADED,
                latency_ms=conn_latency,
                message=conn_msg,
                details={
                    "id": c.id,
                    "db_type": c.db_type.value,
                    "host": c.host,
                    "port": c.port,
                    "database_name": c.database_name
                }
            )
        )

    # 4. Global System Status Derivation
    total_conns = len(active_conns)
    if not llm_ok:
        global_status = SYSTEM_STATUS_CRITICAL
    elif not meta_ok or (total_conns > 0 and healthy_count < total_conns):
        global_status = SYSTEM_STATUS_DEGRADED
    else:
        global_status = SYSTEM_STATUS_OPERATIONAL

    return SystemHealthResponse(
        status=global_status,
        timestamp=datetime.datetime.utcnow(),
        llm_engine=llm_comp,
        metadata_db=meta_comp,
        corporate_connectors=connectors_health,
        total_active_connectors=total_conns,
        healthy_connectors_count=healthy_count
    )
