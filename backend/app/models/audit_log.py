import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=False)
    user_role = Column(String(50), nullable=True)
    
    question_prompt = Column(Text, nullable=False)
    sql_generated = Column(Text, nullable=True)
    validation_status = Column(String(50), nullable=False) # APROBADO | RECHAZADO_TABLA_NO_PERMITIDA | ERROR_SINTAXIS
    
    target_database = Column(String(100), nullable=True)
    execution_time_ms = Column(Integer, default=0)
    rows_returned = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
