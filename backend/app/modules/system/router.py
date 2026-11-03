import time
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_db, get_current_user
from app.core.database import discard_failed_transaction
from app.modules.auth.models import User
from app.modules.admin_catalog.models import CorporateConnection
from app.core.config import settings
from app.core.constants import (
    SYSTEM_STATUS_OPERATIONAL,
    SYSTEM_STATUS_DEGRADED,
    SYSTEM_STATUS_CRITICAL,
    ADMIN_ROLES,
    ROLE_ADMINISTRADOR,
    ROLE_USUARIO,
)
from app.modules.system.schemas import ComponentHealth, SystemHealthResponse
from app.modules.system.health_service import HealthService
# Misma validacion que /llm/test-connection y /llm/test-completion. Este endpoint
# es la SEGUNDA puerta al mismo sink: `base_url` venia de un query param y
# llegaba crudo a HealthService.check_llm_connectivity, que emite httpx GET a
# donde el usuario dijera. Con ?base_url=http://169.254.169.254 cualquier
# usuario autenticado hacia GET a la red interna. Se importa la funcion en vez
# de copiar el allowlist para que las dos entradas compartan una sola
# implementacion y la proxima puerta que se abra herede la proteccion.
from app.modules.chat_engine.llm_diagnostic_router import _resolve_llm_base_url

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
    # Si el cliente manda base_url, se valida ANTES de tocar la red: host fuera
    # del loopback -> 400 y ni una request sale. Sin base_url se usa la
    # configuracion del servidor, que es de confianza y no necesita validacion.
    effective_base_url = _resolve_llm_base_url(base_url) if base_url else settings.OLLAMA_BASE_URL
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
        # El `except` se traga el error pero la transaccion queda ABORTADA: el
        # `db.query(CorporateConnection)` de abajo fallaria con
        # `InFailedSqlTransaction`, un error que no tiene nada que ver con la BD de
        # metadatos. Se devuelve la sesion a un estado usable antes de seguir.
        discard_failed_transaction(db)

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
        res = HealthService.check_db_connectivity(
            host=c.host,
            port=c.port,
            timeout=2.0,
            db_type=c.db_type.value if hasattr(c.db_type, 'value') else str(c.db_type),
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


@router.get("/anomalies")
async def get_system_anomalies(
    connection_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scans for proactive operational and analytical anomalies:
    1. Active connection reachability and status
    2. Connection-specific AST security blocks in the last 24h
    3. Connection-specific slow queries (>4000ms)
    4. Proactive data anomalies (outliers in key metrics)
    5. Connections requiring permission review
    """
    from app.modules.telemetry_audit.models import AuditLog
    from app.modules.admin_catalog.models import SemanticCatalog, DatabaseType
    from sqlalchemy import func

    anomalies = []

    # Resolve target connection
    target_conn = None
    if connection_id:
        target_conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
    if not target_conn:
        target_conn = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).order_by(CorporateConnection.id.desc()).first()
    if not target_conn:
        target_conn = db.query(CorporateConnection).order_by(CorporateConnection.id.desc()).first()

    is_reachable = True
    if target_conn:
        # 1. Proactive reachability & health check
        try:
            res = HealthService.check_db_connectivity(
                host=target_conn.host,
                port=target_conn.port,
                timeout=1.5,
                db_type=target_conn.db_type.value if hasattr(target_conn.db_type, 'value') else str(target_conn.db_type),
                database_name=target_conn.database_name
            )
            is_reachable = res.get("success", False)
            conn_err = res.get("message", "")
        except Exception as e:
            is_reachable = False
            conn_err = str(e)

        if not is_reachable:
            anomalies.append({
                "id": f"conn-offline-{target_conn.id}",
                "type": "connectivity",
                "severity": "critical",
                "title": f"Conexión inaccesible: {target_conn.name}",
                "description": f"No se pudo establecer conexión con '{target_conn.database_name}' ({conn_err}).",
                "action_label": "Verificar en Admin",
                "action_route": "/admin"
            })

    # 2. Bloqueos de seguridad AST en últimas 24h (específicos de la conexión si aplica)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    audit_query = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff)
    if target_conn and target_conn.database_name:
        audit_query = audit_query.filter(AuditLog.target_database == target_conn.database_name)

    recent_blocked = audit_query.filter(AuditLog.validation_status.like("RECHAZADO%")).count()
    if recent_blocked > 0:
        anomalies.append({
            "id": f"audit-blocked-{target_conn.id if target_conn else 'all'}",
            "type": "security",
            "severity": "critical" if recent_blocked >= 5 else "warning",
            "title": f"{recent_blocked} consultas bloqueadas por seguridad",
            "description": f"Se registraron {recent_blocked} intentos de consulta rechazados por validación AST en las últimas 24h para {target_conn.name if target_conn else 'el sistema'}.",
            "action_label": "Investigar Bloqueos",
            "query_prompt": f"¿Cuáles fueron las consultas bloqueadas por seguridad en {target_conn.name if target_conn else 'el sistema'} y qué usuarios las ejecutaron?",
            "action_route": "/admin/audit" if current_user.is_admin else None
        })

    # 3. Consultas lentas (>4s)
    slow_queries = audit_query.filter(AuditLog.execution_time_ms > 4000).count()
    if slow_queries > 0:
        anomalies.append({
            "id": f"audit-slow-{target_conn.id if target_conn else 'all'}",
            "type": "performance",
            "severity": "info",
            "title": f"{slow_queries} consultas lentas detectadas",
            "description": f"Se detectaron ejecuciones con tiempos superiores a 4s en {target_conn.name if target_conn else 'la base de datos'}. Podría requerirse optimización de índices.",
            "action_label": "Investigar Rendimiento",
            "query_prompt": f"¿Cuáles son las consultas más lentas ejecutadas recientemente y qué tablas involucran?",
            "action_route": "/admin/audit" if current_user.is_admin else None
        })

    # 4. Escaneo proactivo de datos reales en la base activa (outliers estadísticos)
    if target_conn and is_reachable:
        try:
            from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
            from app.modules.chat_engine.sql_executor import SQLExecutor
            from app.modules.chat_engine.kpi_calculator import KPICalculator
            from app.modules.chat_engine.governance_guard import GovernanceGuard

            is_pg = (target_conn.db_type == DatabaseType.POSTGRESQL or str(target_conn.db_type).lower() == "postgresql")
            engine_dialect = "postgres" if is_pg else "sqlite"
            target_exec = target_conn if is_pg else DynamicSchemaPruningService.resolve_db_path(db, target_conn.id)

            # El escaneo no puede mirar una tabla que el perfil no puede ver. Antes
            # elegia la primera tabla fact_ alfabetica del servidor y hacia SELECT *,
            # devolviendo en crudo columnas BLOCKED y MASKED a cualquier usuario
            # autenticado, sin importar su rol.
            role_name = current_user.role.name if current_user.role else ROLE_USUARIO
            is_admin = current_user.is_admin or role_name in ADMIN_ROLES
            if is_admin and not current_user.role:
                role_name = ROLE_ADMINISTRADOR
            allowed_tables = GovernanceGuard.get_allowed_tables_for_role(
                role_name, is_admin, db=db, role_id=current_user.role_id, connection_id=target_conn.id
            )
            allowed_lower = {t.lower() for t in (allowed_tables or set())}

            physical_tables = DynamicSchemaPruningService.get_physical_db_tables(target_exec)
            visible_tables = sorted(
                t for t in physical_tables if is_admin or t.lower() in allowed_lower
            )
            fact_tables = [t for t in visible_tables if t.lower().startswith("fact_")]
            chosen_table = fact_tables[0] if fact_tables else (visible_tables[0] if visible_tables else None)

            if chosen_table:
                cols_info = DynamicSchemaPruningService.get_physical_table_columns(chosen_table, db_path=target_exec)
                num_cols = [
                    c["name"] for c in cols_info
                    if any(it in c.get("type", "").lower() for it in ["int", "real", "float", "numeric", "decimal", "double"])
                    and not c["name"].lower().endswith("_id") and c["name"].lower() != "id"
                ]

                if num_cols:
                    metric = num_cols[0]
                    # Proyectar SOLO la metrica numerica. SELECT * tambien traia
                    # columnas sensibles y las metia en las descripciones de
                    # anomalias que se devuelven al cliente.
                    quoted_table = f'"{chosen_table}"' if is_pg else f'`{chosen_table}`'
                    quoted_metric = f'"{metric}"' if is_pg else f'`{metric}`'
                    scan_sql = f"SELECT {quoted_metric} FROM {quoted_table} LIMIT 60"
                    rows = SQLExecutor.execute_raw_sql(target_exec, scan_sql, dialect=engine_dialect)
                    if rows and len(rows) >= 4:
                        data_anomalies = KPICalculator.detect_statistical_anomalies(rows, list(rows[0].keys()))
                        if data_anomalies:
                            top_anom = data_anomalies[0]
                            anomalies.append({
                                "id": f"data-anom-{target_conn.id}-{chosen_table}",
                                "type": "data_quality",
                                "severity": "warning",
                                "title": f"Anomalía estadística en {chosen_table}",
                                "description": top_anom.get("description", f"Valores atípicos detectados en la métrica '{metric}'."),
                                "query_prompt": f"Investiga en profundidad los valores atípicos detectados en {chosen_table} sobre la métrica {metric}. ¿Cuáles registros lo explican?",
                                "action_label": "Investigar en Chat"
                            })
        except Exception:
            pass
        # El bloque anterior se traga su error con `pass` y el escaneo es
        # best-effort por diseño: no debe tumbar el endpoint. Pero al tragarse el
        # error puede dejar la sesion con la transaccion ABORTADA, y entonces la
        # consulta de la seccion 5 (y cualquier otra de este request) muere con
        # `InFailedSqlTransaction`. Ese error si tumbaba el endpoint, y sin
        # relacion con lo que falló: por eso la sesión se devuelve usable.
        discard_failed_transaction(db)

    # 5. Conexiones con revisión de permisos pendiente o tablas sin dominio asignado
    unassigned_counts = dict(
        db.query(SemanticCatalog.connection_id, func.count(SemanticCatalog.id))
        .filter(SemanticCatalog.domain_id == None)
        .group_by(SemanticCatalog.connection_id)
        .all()
    )
    for c in db.query(CorporateConnection).filter(CorporateConnection.is_uploaded == True).all():
        pending = unassigned_counts.get(c.id, 0)
        if pending > 0 and (target_conn is None or target_conn.id == c.id):
            anomalies.append({
                "id": f"conn-rev-{c.id}",
                "type": "security",
                "severity": "warning",
                "title": f"Revisión requerida: {c.name}",
                "description": f"La base de datos '{c.database_name}' tiene {pending} elemento(s) pendientes de asignar a un dominio RBAC.",
                "action_label": "Ir a Administración" if current_user.is_admin else "Revisar Catálogo",
                "action_route": "/admin" if current_user.is_admin else None,
                "query_prompt": f"¿Cuáles son las tablas y columnas pendientes de clasificar en la base de datos {c.name}?"
            })

    return {
        "count": len(anomalies),
        "anomalies": anomalies,
        "has_critical": any(a["severity"] == "critical" for a in anomalies)
    }

