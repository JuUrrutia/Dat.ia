import datetime
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base

class DatabaseType(str, enum.Enum):
    POSTGRESQL = "postgresql"
    MSSQL = "mssql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLITE = "sqlite"

class CorporateConnection(Base):
    __tablename__ = "corporate_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    db_type = Column(SQLEnum(DatabaseType), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=0)
    database_name = Column(String(150), nullable=False)
    username = Column(String(100), nullable=False, default="admin")
    encrypted_password = Column(String(500), nullable=False, default="")
    
    is_active = Column(Boolean, default=True)
    is_uploaded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class SemanticCatalog(Base):
    __tablename__ = "semantic_catalog"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("corporate_connections.id", ondelete="CASCADE"), nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="SET NULL"), nullable=True)
    
    schema_name = Column(String(50), default="public")
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=True) # Null if description applies to whole table
    
    friendly_name = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    synonyms = Column(Text, nullable=True) # Comma-separated or JSON list
    business_formula = Column(Text, nullable=True)
    
    is_ai_generated = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("connection_id", "schema_name", "table_name", "column_name", name="uix_catalog_element"),
    )


class ColumnPermissionType(str, enum.Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    MASKED = "MASKED"


class RoleDomainLink(Base):
    __tablename__ = "role_domain_links"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)

    role = relationship("Role", back_populates="domain_links")
    domain = relationship("Domain", back_populates="role_links")


class RoleTablePermission(Base):
    __tablename__ = "role_table_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(Integer, ForeignKey("corporate_connections.id", ondelete="CASCADE"), nullable=False)
    schema_name = Column(String(50), default="public")
    table_name = Column(String(100), nullable=False)
    is_allowed = Column(Boolean, default=True)

    role = relationship("Role", back_populates="table_permissions")


class RoleColumnPermission(Base):
    __tablename__ = "role_column_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(Integer, ForeignKey("corporate_connections.id", ondelete="CASCADE"), nullable=False)
    schema_name = Column(String(50), default="public")
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=False)
    permission_type = Column(SQLEnum(ColumnPermissionType), default=ColumnPermissionType.ALLOWED)

    role = relationship("Role", back_populates="column_permissions")
