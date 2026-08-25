import logging
import io
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.modules.admin_catalog.schemas import (
    SemanticCatalogCreate, SemanticCatalogUpdate, SemanticCatalogOut,
    DataDictionaryResponse, AutoEnrichRequest, AutoEnrichResponse,
    CorporateConnectionCreate, CorporateConnectionUpdate, CorporateConnectionOut,
    ConnectionTestRequest, ConnectionTestResult,
    ReportExportRequest
)
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.modules.catalog.services.connector_service import ConnectorDomainService
from app.modules.reports.generator import ReportGeneratorService
from app.services.health_service import HealthService

router = APIRouter()
logger = logging.getLogger(__name__)

class MetadataDBTestRequest(BaseModel):
    server: str
    port: int
    db_name: str
    user: Optional[str] = None
    password: Optional[str] = None

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
    return CatalogDomainService.get_data_dictionary(db, connection_id=connection_id)

@router.post("/catalog/auto-enrich", response_model=AutoEnrichResponse)
async def auto_enrich_catalog(
    req: Optional[AutoEnrichRequest] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Intelligently inspects schema and auto-generates semantic descriptions."""
    return await CatalogDomainService.auto_enrich_catalog(db, req)

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
