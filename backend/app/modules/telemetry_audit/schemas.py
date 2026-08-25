import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime.datetime
    user_id: Optional[int] = None
    username: str
    user_role: Optional[str] = None
    question_prompt: str
    sql_generated: Optional[str] = None
    validation_status: str
    target_database: Optional[str] = None
    execution_time_ms: int = 0
    rows_returned: int = 0
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AuditLogsPage(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[AuditLogOut]
