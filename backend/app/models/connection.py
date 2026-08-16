import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
import enum
from app.core.database import Base

class DatabaseType(str, enum.Enum):
    POSTGRESQL = "postgresql"
    MSSQL = "mssql"
    MYSQL = "mysql"
    ORACLE = "oracle"

class CorporateConnection(Base):
    __tablename__ = "corporate_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    db_type = Column(SQLEnum(DatabaseType), nullable=False)
    host = Column(String(150), nullable=False)
    port = Column(Integer, nullable=False)
    database_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(String(500), nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
