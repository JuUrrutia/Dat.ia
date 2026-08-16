import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="role")
    domain_links = relationship("RoleDomainLink", back_populates="role", cascade="all, delete-orphan")
    table_permissions = relationship("RoleTablePermission", back_populates="role", cascade="all, delete-orphan")
    column_permissions = relationship("RoleColumnPermission", back_populates="role", cascade="all, delete-orphan")

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    role_links = relationship("RoleDomainLink", back_populates="domain", cascade="all, delete-orphan")
