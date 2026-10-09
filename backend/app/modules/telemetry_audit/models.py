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
    # Nullable A PROPOSITO: `NULL` significa "no se registro validacion para esta
    # consulta". Antes la columna era NOT NULL y eso obligaba al router a inventar
    # "APROBADO" cuando la respuesta no traia trazabilidad, asi que el CSV de
    # En un CSV de compliance exportado, "" y "APROBADO" NO pueden significar lo
    # mismo: uno es "no lo se", el otro es "validado". La migracion que abre la
    # columna esta en core/database.py.
    validation_status = Column(String(50), nullable=True) # APROBADO | RECHAZADO_TABLA_NO_PERMITIDA | ERROR_SINTAXIS | NULL (sin registro)
    
    target_database = Column(String(100), nullable=True)
    execution_time_ms = Column(Integer, default=0)
    rows_returned = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    result_snapshot = Column(Text, nullable=True)
