from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.modules.admin_catalog.models import DatabaseType

# --- Semantic Catalog Schemas ---
class SemanticCatalogBase(BaseModel):
    connection_id: int = 1
    domain_id: Optional[int] = None
    schema_name: str = "main"
    table_name: str
    column_name: Optional[str] = None
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    synonyms: Optional[str] = None
    business_formula: Optional[str] = None
    is_ai_generated: bool = False

class SemanticCatalogCreate(SemanticCatalogBase):
    pass

class SemanticCatalogUpdate(BaseModel):
    domain_id: Optional[int] = None
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    synonyms: Optional[str] = None
    business_formula: Optional[str] = None
    is_ai_generated: Optional[bool] = None

class SemanticCatalogOut(SemanticCatalogBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DataDictionaryColumn(BaseModel):
    name: str
    data_type: str
    is_pk: bool = False
    is_nullable: bool = True
    default_value: Optional[str] = None
    sample_values: List[str] = []
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    business_formula: Optional[str] = None
    is_ai_generated: bool = False

class DataDictionaryTable(BaseModel):
    table_name: str
    schema_name: str = "main"
    row_count: int = 0
    column_count: int = 0
    description: Optional[str] = None
    columns: List[DataDictionaryColumn] = []

class DataDictionaryResponse(BaseModel):
    connection_id: int
    connection_name: str
    db_type: str
    tables: List[DataDictionaryTable]
    total_tables: int
    total_columns: int

class AutoEnrichRequest(BaseModel):
    connection_id: Optional[int] = None
    table_name: Optional[str] = None

class AutoEnrichResponse(BaseModel):
    success: bool
    message: str
    enriched_count: int
    catalog_items: List[SemanticCatalogOut]

# --- Connection Schemas ---
class CorporateConnectionCreate(BaseModel):
    name: str
    db_type: DatabaseType
    host: str
    port: int = 0
    database_name: str
    username: str = "admin"
    password: str = ""
    is_active: bool = True
    is_uploaded: bool = False

class CorporateConnectionUpdate(BaseModel):
    name: Optional[str] = None
    db_type: Optional[DatabaseType] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class CorporateConnectionOut(BaseModel):
    id: int
    name: str
    db_type: DatabaseType
    host: str
    port: int
    database_name: str
    username: str
    is_active: bool
    is_uploaded: bool = False
    requires_permission_review: bool = False
    detected_tables: Optional[List[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConnectionTestRequest(BaseModel):
    db_type: DatabaseType
    host: str
    port: int
    database_name: str
    username: str
    password: str

class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int = 0

# --- Report Schemas ---
class KPICardData(BaseModel):
    title: str
    value: str
    subtitle: Optional[str] = None
    change_direction: Optional[str] = None

class MetricGaugeData(BaseModel):
    title: str
    percentage: float = 0.0
    value_label: str = ""
    target_label: str = ""
    color: Optional[str] = None

class ExecutiveReportData(BaseModel):
    overview: Optional[str] = ""
    key_findings: List[str] = []
    recommendations: List[str] = []
    risk_level: Optional[str] = None
    business_impact: Optional[str] = None

class TraceabilityAuditData(BaseModel):
    sql_executed: Optional[str] = ""
    execution_time_ms: Optional[int] = 0
    rows_returned: Optional[int] = 0
    validation_status: Optional[str] = "APROBADO"
    schema_tables_used: List[str] = []
    explanation: Optional[str] = None

class ReportExportRequest(BaseModel):
    audit_log_id: int
    chart_image_base64: Optional[str] = None
    custom_notes: Optional[str] = None

class ReportExportData(BaseModel):
    question: str
    summary_text: Optional[str] = None
    executive_report: Optional[ExecutiveReportData] = None
    kpis: List[KPICardData] = []
    gauges: List[MetricGaugeData] = []
    data_columns: List[str] = []
    data_rows: List[Dict[str, Any]] = []
    traceability: Optional[TraceabilityAuditData] = None
    chart_image_base64: Optional[str] = None
    target_database: Optional[str] = None
