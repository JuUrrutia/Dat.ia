from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.connection import DatabaseType

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

    class Config:
        from_attributes = True

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
