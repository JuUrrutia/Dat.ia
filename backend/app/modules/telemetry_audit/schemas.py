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
    # Optional: la columna admite NULL desde la migracion de core/database.py, asi
    # que hay registros sin validacion registrada. Con `str` required, uno solo de
    # esos registros hacia fallar el listado de auditoria del admin con un 500.
    validation_status: Optional[str] = None
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
