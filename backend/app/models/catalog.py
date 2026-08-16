import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.core.database import Base

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
