from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str
    connection_id: int = 1
    session_id: Optional[str] = None
    user_role: Optional[str] = "Economista"

class KPICard(BaseModel):
    title: str
    value: str
    subtitle: Optional[str] = None
    change_direction: Optional[str] = "neutral" # positive | negative | neutral

class MetricGauge(BaseModel):
    title: str
    percentage: float
    value_label: str
    target_label: str
    color: Optional[str] = "#F59E0B"

class ExecutiveReport(BaseModel):
    overview: str
    key_findings: List[str] = []
    recommendations: List[str] = []
    risk_level: Optional[str] = "BAJO" # BAJO | MEDIO | ALTO | CRITICO
    business_impact: Optional[str] = None

class TraceabilityAudit(BaseModel):
    sql_executed: str
    execution_time_ms: int
    rows_returned: int
    validation_status: str
    schema_tables_used: List[str]
    explanation: str

class PresentationHints(BaseModel):
    show_executive_report: bool = True
    show_kpis: bool = True
    show_gauges: bool = True
    show_chart: bool = True
    preferred_view: str = "studio"  # studio | report | table | assistant
    summary_style: str = "detailed"  # concise | detailed | executive

class QueryResponse(BaseModel):
    question: str
    summary_text: str
    executive_report: Optional[ExecutiveReport] = None
    kpis: List[KPICard] = []
    gauges: Optional[List[MetricGauge]] = []
    chart_type: str = "bar" # bar | line | area | pie | donut | radar | gauge | none
    chart_option: Dict[str, Any] = {} # ECharts option JSON object
    data_columns: List[str] = []
    data_rows: List[Dict[str, Any]] = []
    response_type: str = "data_analysis" # data_analysis | advisory | explanation | report | hybrid
    conversational_response: Optional[str] = None # Respuesta conversacional estructurada (advisory/explanation/hybrid)
    grounding_info: Optional[str] = None # Información de las tablas/registros reales de la BD consultados
    presentation_hints: Optional[PresentationHints] = None
    traceability: TraceabilityAudit

