import logging
import io
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_admin
from app.modules.auth.models import User
from app.modules.admin_catalog.schemas import (
    SemanticCatalogCreate, SemanticCatalogUpdate, SemanticCatalogOut,
    DataDictionaryResponse, AutoEnrichRequest, AutoEnrichResponse,
    CorporateConnectionCreate, CorporateConnectionUpdate, CorporateConnectionOut,
    ConnectionTestRequest, ConnectionTestResult, MetadataDBTestRequest,
    ReportExportRequest, NullsAuditResponse, ApplyNullPolicyRequest
)
from app.modules.admin_catalog.models import CorporateConnection
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.modules.catalog.services.connector_service import ConnectorDomainService
from app.modules.catalog.services.null_manager import NullManagerService
from app.modules.reports.generator import ReportGeneratorService
from app.modules.system.health_service import HealthService
from fastapi import HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)

# =========================================================================
# SEMANTIC CATALOG ENDPOINTS (/catalog)
# =========================================================================

@router.get("/catalog", response_model=List[SemanticCatalogOut])
def list_catalog(
    connection_id: Optional[int] = Query(None, description="Filtrar por ID de conexión"),
    table_name: Optional[str] = Query(None, description="Filtrar por nombre de tabla"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Lists semantic catalog rules and data dictionary definitions."""
    return CatalogDomainService.list_catalog(db, connection_id=connection_id, table_name=table_name)

@router.post("/catalog", response_model=SemanticCatalogOut, status_code=status.HTTP_201_CREATED)
def create_catalog_item(
    item_in: SemanticCatalogCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Creates or updates a semantic catalog entry (Admin only)."""
    return CatalogDomainService.create_catalog_item(db, item_in)

@router.put("/catalog/{item_id}", response_model=SemanticCatalogOut)
def update_catalog_item(
    item_id: int,
    item_in: SemanticCatalogUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Updates an existing semantic catalog entry (Admin only)."""
    return CatalogDomainService.update_catalog_item(db, item_id, item_in)

@router.delete("/catalog/{item_id}", status_code=status.HTTP_200_OK)
def delete_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Deletes a semantic catalog entry (Admin only)."""
    return CatalogDomainService.delete_catalog_item(db, item_id)

@router.get("/catalog/data-dictionary", response_model=DataDictionaryResponse)
def get_data_dictionary(
    connection_id: Optional[int] = Query(None, description="ID de conexión a inspeccionar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Introspects target database schema dynamically."""
    # Los valores de muestra son datos reales de la BD del cliente. Antes de pasar
    # el rol, este endpoint devolvia valores de columnas BLOCKED (token de tarjeta,
    # salario) y MASKED (RUT/DNI) a cualquier usuario autenticado, esquivando el
    # validador AST porque no es SQL de usuario sino introspeccion.
    from app.core.constants import ADMIN_ROLES, ROLE_ADMINISTRADOR, ROLE_USUARIO
    from app.modules.chat_engine.governance_guard import GovernanceGuard

    role_name = current_user.role.name if current_user.role else ROLE_USUARIO
    is_admin = current_user.is_admin or role_name in ADMIN_ROLES
    if is_admin and not current_user.role:
        role_name = ROLE_ADMINISTRADOR

    target_conn_id = connection_id
    if target_conn_id is None:
        active = db.query(CorporateConnection).filter(
            CorporateConnection.is_active == True
        ).order_by(CorporateConnection.id.desc()).first()
        target_conn_id = active.id if active else 1

    blocked_columns = GovernanceGuard.get_blocked_columns_for_role(
        role_name, is_admin, db=db, role_id=current_user.role_id,
        connection_id=target_conn_id,
    )
    masked_columns = GovernanceGuard.get_masked_columns_for_role(
        role_name, is_admin, db=db, role_id=current_user.role_id,
        connection_id=target_conn_id,
    )

    return CatalogDomainService.get_data_dictionary(
        db,
        connection_id=connection_id,
        blocked_columns=blocked_columns,
        masked_columns=masked_columns,
    )

@router.post("/catalog/auto-enrich", response_model=AutoEnrichResponse)
async def auto_enrich_catalog(
    req: Optional[AutoEnrichRequest] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Intelligently inspects schema and auto-generates semantic descriptions."""
    return await CatalogDomainService.auto_enrich_catalog(db, req)

@router.get("/catalog/connections/{connection_id}/nulls-audit", response_model=NullsAuditResponse)
def audit_connection_nulls(
    connection_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Audits tables and columns for NULL values in the target connection (Admin only)."""
    conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Conexión no encontrada.")
    return NullManagerService.audit_connection_nulls(conn, db)

@router.post("/catalog/connections/{connection_id}/nulls-policy")
def apply_connection_null_policy(
    connection_id: int,
    req: ApplyNullPolicyRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Applies the selected null remediation policy (Admin only)."""
    conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Conexión no encontrada.")
    try:
        return NullManagerService.apply_null_policy(conn, req.policy, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================================================================
# CORPORATE CONNECTORS ENDPOINTS (/connectors)
# =========================================================================

@router.get("/connectors", response_model=List[CorporateConnectionOut])
def list_connectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Lists all registered corporate database connections."""
    return ConnectorDomainService.list_connectors(db)

@router.post("/connectors", response_model=CorporateConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connector(
    conn_in: CorporateConnectionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Registers a new corporate database connection (Admin only)."""
    return ConnectorDomainService.create_connector(db, conn_in)

@router.post("/connectors/upload", response_model=CorporateConnectionOut, status_code=status.HTTP_201_CREATED)
async def upload_database_file(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Uploads a SQLite, Excel, CSV or SQL dump file (Admin only)."""
    return await ConnectorDomainService.upload_database_file(db, file, name)

@router.put("/connectors/{conn_id}", response_model=CorporateConnectionOut)
def update_connector(
    conn_id: int,
    conn_in: CorporateConnectionUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Updates an existing corporate database connection (Admin only)."""
    return ConnectorDomainService.update_connector(db, conn_id, conn_in)

@router.post("/connectors/{conn_id}/toggle-active", response_model=CorporateConnectionOut)
def toggle_connector_active(
    conn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Toggles active status of a corporate database connection (Admin only)."""
    return ConnectorDomainService.toggle_connector_active(db, conn_id)

@router.delete("/connectors/{conn_id}", status_code=status.HTTP_200_OK)
def delete_connector(
    conn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Deletes a corporate database connection (Admin only)."""
    return ConnectorDomainService.delete_connector(db, conn_id)

# =========================================================================
# PERMISOS DE TABLA POR ROL (default-deny)
# =========================================================================
# Ruta `/permissions` y no `/catalog/permissions`: esta se parsea contra
# `/catalog/{item_id}` (declarado mas arriba) y FastSQL devuelve 422 por un
# item_id no numerico. Los permisos son la matriz RBAC de toda la plataforma, no
# una entrada del catalogo semantico.

@router.get("/permissions")
def list_role_table_permissions(
    connection_id: Optional[int] = Query(None, description="Filtrar por ID de conexión"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Devuelve la matriz de permisos de tabla (Admin only).

    Un dataset recien subido aparece con `detected_tables` y sin ninguna fila acá:
    eso es default-deny, no un fallo. El admin concede con el PUT de abajo.
    """
    return ConnectorDomainService.list_role_table_permissions(db, connection_id=connection_id)

@router.put("/permissions")
def set_role_table_permissions(
    connection_id: int = Query(..., description="ID de la conexión"),
    role_id: int = Query(..., description="ID del rol"),
    table_names: List[str] = Query(..., description="Tablas a conceder o revocar"),
    is_allowed: bool = Query(True, description="True concede acceso, False lo revoca"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Concede o revoca acceso de un rol a un conjunto de tablas (Admin only).

    Es la unica via de granting: al subir un dataset no se concede nada. Un rol
    sin fila para una tabla NO tiene acceso a ella, y eso lo distingue de "la tabla
    existe pero no hay datos".
    """
    perms = ConnectorDomainService.set_role_table_permissions(
        db, connection_id=connection_id, role_id=role_id,
        table_names=table_names, is_allowed=is_allowed,
    )
    return {
        "connection_id": connection_id,
        "role_id": role_id,
        "is_allowed": is_allowed,
        "permissions": [
            {"id": p.id, "table_name": p.table_name, "schema_name": p.schema_name,
             "is_allowed": bool(p.is_allowed)}
            for p in perms
        ],
    }

@router.post("/connectors/test", response_model=ConnectionTestResult)
def test_connection_connectivity(
    test_in: ConnectionTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Tests real network TCP socket or SQLite file connectivity."""
    return ConnectorDomainService.test_connection_connectivity(test_in)

@router.post("/connectors/test-metadata-db", response_model=ConnectionTestResult)
def test_metadata_db_connectivity(
    test_in: MetadataDBTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Tests real connectivity to target PostgreSQL metadata database."""
    result = HealthService.check_db_connectivity(
        host=test_in.server,
        port=test_in.port,
        timeout=3.0,
        db_type="POSTGRESQL",
        database_name=test_in.db_name
    )
    return ConnectionTestResult(
        success=result["success"],
        message=result["message"],
        latency_ms=result["latency_ms"]
    )

# =========================================================================
# REPORT EXPORT ENDPOINTS (/reports/export/pdf & /reports/export/excel)
# =========================================================================

@router.post("/reports/export/pdf")
def export_report_pdf(
    req: ReportExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    pdf_bytes, filename = ReportGeneratorService.export_pdf(db, current_user, req)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/reports/export/excel")
def export_report_excel(
    req: ReportExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    excel_bytes, filename = ReportGeneratorService.export_excel(db, current_user, req)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
