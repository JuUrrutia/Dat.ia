from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel

class SemanticCatalogBase(BaseModel):
    connection_id: int = 1
    domain_id: Optional[int] = None
    schema_name: str = "main"
    table_name: str
    column_name: Optional[str] = None
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    synonyms: Optional[str] = None
    business_formula: Optional[str] = None
    is_ai_generated: bool = False

class SemanticCatalogCreate(SemanticCatalogBase):
    pass

class SemanticCatalogUpdate(BaseModel):
    domain_id: Optional[int] = None
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    synonyms: Optional[str] = None
    business_formula: Optional[str] = None
    is_ai_generated: Optional[bool] = None

class SemanticCatalogOut(SemanticCatalogBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class DataDictionaryColumn(BaseModel):
    name: str
    data_type: str
    is_pk: bool = False
    is_nullable: bool = True
    default_value: Optional[str] = None
    sample_values: List[str] = []
    friendly_name: Optional[str] = None
    description: Optional[str] = None
    business_formula: Optional[str] = None
    is_ai_generated: bool = False

class DataDictionaryTable(BaseModel):
    table_name: str
    schema_name: str = "main"
    row_count: int = 0
    column_count: int = 0
    description: Optional[str] = None
    columns: List[DataDictionaryColumn] = []

class DataDictionaryResponse(BaseModel):
    connection_id: int
    connection_name: str
    db_type: str
    tables: List[DataDictionaryTable]
    total_tables: int
    total_columns: int

class AutoEnrichRequest(BaseModel):
    connection_id: Optional[int] = None
    table_name: Optional[str] = None

class AutoEnrichResponse(BaseModel):
    success: bool
    message: str
    enriched_count: int
    catalog_items: List[SemanticCatalogOut]
