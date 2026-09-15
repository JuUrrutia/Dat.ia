from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class QueryRequest(BaseModel):
    question: str
    connection_id: int = 1
    session_id: Optional[str] = None
    user_role: Optional[str] = "Economista"
    conversation_history: Optional[List[Dict[str, Any]]] = None

class KPICard(BaseModel):
    title: str
    value: str
    subtitle: Optional[str] = None
    change_direction: Optional[str] = "neutral" # positive | negative | neutral

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
    audit_log_id: Optional[int] = None

class PresentationHints(BaseModel):
    show_executive_report: bool = True
    show_kpis: bool = True
    show_chart: bool = True
    preferred_view: str = "assistant"  # assistant | report | table
    summary_style: str = "detailed"  # concise | detailed | executive

class QueryResponse(BaseModel):
    question: str
    summary_text: str
    executive_report: Optional[ExecutiveReport] = None
    kpis: List[KPICard] = []
    chart_type: str = "bar" # bar | line | area | pie | donut | none
    chart_option: Dict[str, Any] = {} # ECharts option JSON object
    data_columns: List[str] = []
    data_rows: List[Dict[str, Any]] = []
    response_type: str = "data_analysis" # data_analysis | advisory | explanation | report | hybrid
    conversational_response: Optional[str] = None # Respuesta conversacional estructurada
    grounding_info: Optional[str] = None # Información de las tablas/registros reales de la BD consultados
    presentation_hints: Optional[PresentationHints] = None
    traceability: TraceabilityAudit
    audit_log_id: Optional[int] = None

class SuggestionsResponse(BaseModel):
    user_role: Optional[str] = None
    allowed_tables: Optional[List[str]] = None
    suggestions: List[str] = []

class ChatThreadCreate(BaseModel):
    id: str
    title: str
    connection_id: Optional[int] = 1
    results: List[Dict[str, Any]] = []

class ChatThreadSummary(BaseModel):
    id: str
    title: str
    connection_id: Optional[int] = 1
    message_count: int
    updated_at: str

class ChatThreadDetail(BaseModel):
    id: str
    title: str
    connection_id: Optional[int] = 1
    results: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str

class ChatFeedbackRequest(BaseModel):
    audit_log_id: Optional[int] = None
    question: str
    sql: Optional[str] = None
    connection_id: int = 1
    rating: str  # positive | negative
    comment: Optional[str] = None
    is_golden: Optional[bool] = False

class GoldenQueryRequest(BaseModel):
    question: str
    sql: str
    connection_id: int = 1
    is_golden: bool = True

class ChatFeedbackResponse(BaseModel):
    success: bool
    message: str
    learning_saved: bool = False

class DashboardWidgetCreate(BaseModel):
    title: str
    connection_id: Optional[int] = 1
    chart_type: str = "bar"
    chart_option_json: str
    kpis_json: Optional[str] = None
    query_text: Optional[str] = None

class DashboardWidgetOut(BaseModel):
    id: int
    user_id: int
    title: str
    connection_id: Optional[int] = 1
    chart_type: str = "bar"
    chart_option_json: str
    kpis_json: Optional[str] = None
    query_text: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

