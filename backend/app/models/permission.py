import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
import enum
from sqlalchemy.orm import relationship
from app.core.database import Base

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
