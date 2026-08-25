import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class ComponentHealth(BaseModel):
    name: str
    type: str  # "llm" | "metadata_db" | "connector"
    status: str  # "OPERATIVO" | "DEGRADADO" | "CRITICO" | "ERROR"
    latency_ms: int = 0
    message: str
    details: Optional[Dict[str, Any]] = None

class SystemHealthResponse(BaseModel):
    status: str  # "OPERATIVO" | "DEGRADADO" | "CRITICO"
    timestamp: datetime.datetime
    llm_engine: ComponentHealth
    metadata_db: ComponentHealth
    corporate_connectors: List[ComponentHealth] = []
    total_active_connectors: int = 0
    healthy_connectors_count: int = 0
