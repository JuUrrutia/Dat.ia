import datetime
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, Enum as SQLEnum, text
from sqlalchemy.orm import relationship
from app.core.database import Base

class DatabaseType(str, enum.Enum):
    POSTGRESQL = "postgresql"
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
    null_policy = Column(String(50), default="open")
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
        # Todo el catalogo semantico se lee por `connection_id`: el prompt del
        # LLM lo entero en cada query, y el AutoEnrichment lo entero una vez por
        # columna. El UniqueConstraint de arriba empieza por `connection_id`
        # pero MySQL/Postgres no lo usan para filtrar: en cuanto se agrega o
        # ordena sobre las otras columnas, el indice deja de servir.
        Index("ix_semantic_catalog_connection", "connection_id"),
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

    # Procedencia de la fila: True = alguien la concedio a proposito (seeder de la
    # demo o endpoint de administracion). False = la heredo del auto-grant que
    # existia al subir un dataset, que concedia todo sin decision de nadie.
    #
    # El default es False a proposito: una fila que no se puede probar como
    # decision explicita no se presume concedida. Es el mismo mecanismo fail-closed
    # que uso la migracion de `chat_conversations.is_shared`. La migracion de
    # default-deny borra las False de los datasets subidos, una sola vez; a partir
    # de ahi toda fila viva tiene granted_by_admin=True y sobrevive a los
    # reinicios.
    granted_by_admin = Column(Boolean, nullable=False, default=False, server_default=text("FALSE"))

    role = relationship("Role", back_populates="table_permissions")

    # El chat consulta esta tabla en CADA request, y siempre por el mismo par:
    # `role_id == X AND connection_id == Y AND is_allowed == True`
    # (`governance_guard` -> `get_authorized_schema_prompt`, tres veces por
    # pregunta). SQLAlchemy NO crea indices en columnas FK, asi que sin esto es
    # un seq scan de la tabla de permisos por cada query de chat.
    __table_args__ = (
        Index("ix_role_table_perm_lookup", "role_id", "connection_id", "is_allowed"),
    )


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

    # Mismo criterio que `RoleTablePermission`: el filtro del chat es
    # `role_id == X AND connection_id == Y`.
    __table_args__ = (
        Index("ix_role_column_perm_lookup", "role_id", "connection_id"),
    )
