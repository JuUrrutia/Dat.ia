from typing import List, Dict, Any, Optional
from pydantic import BaseModel

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
