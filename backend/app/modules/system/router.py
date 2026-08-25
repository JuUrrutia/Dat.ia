import time
import os
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType
from app.core.config import settings
from app.core.constants import (
    SYSTEM_STATUS_OPERATIONAL,
    SYSTEM_STATUS_DEGRADED,
    SYSTEM_STATUS_CRITICAL,
)
from app.modules.system.schemas import ComponentHealth, SystemHealthResponse
from app.modules.system.health_service import HealthService

router = APIRouter()

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    provider: Optional[str] = Query(None),
    base_url: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SystemHealthResponse:
    """
    Returns unified health & operational status of core system components:
    - Active local LLM engine (Ollama / llama.cpp / LM Studio)
    - Metadata database
    - Active registered corporate database connectors
    """
    effective_provider = provider or settings.LLM_PROVIDER
    effective_base_url = base_url or settings.OLLAMA_BASE_URL
    effective_model = model_name or settings.OLLAMA_MODEL

    llm_res = await HealthService.check_llm_connectivity(
        provider=effective_provider,
        base_url=effective_base_url,
        model_name=effective_model,
        timeout=2.0
    )
    llm_ok = llm_res["success"]
    detected_models = llm_res.get("available_models", [])
    display_model = detected_models[0] if detected_models else effective_model
    detected_prov = llm_res.get("provider", effective_provider)
    prov_title = "llama.cpp" if detected_prov == "llama_cpp" else ("Ollama" if detected_prov == "ollama" else "IA Local")

    llm_comp = ComponentHealth(
        name=f"Motor LLM {prov_title} ({display_model})",
        type="llm",
        status=SYSTEM_STATUS_OPERATIONAL if llm_ok else SYSTEM_STATUS_CRITICAL,
        latency_ms=llm_res.get("latency_ms", 0),
        message=llm_res.get("message", ""),
        details={
            "provider": detected_prov,
            "base_url": llm_res.get("active_url", effective_base_url),
            "available_models": detected_models
        }
    )

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

    active_conns = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).all()
    connectors_health: List[ComponentHealth] = []
    healthy_count = 0

    for c in active_conns:
        if c.db_type == DatabaseType.SQLITE:
            db_path = c.database_name
            exists = os.path.exists(db_path) if db_path else True
            conn_ok = exists
            conn_msg = f"Archivo SQLite '{db_path}' verificado." if exists else f"Archivo SQLite '{db_path}' no encontrado."
            conn_latency = 1
        else:
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
