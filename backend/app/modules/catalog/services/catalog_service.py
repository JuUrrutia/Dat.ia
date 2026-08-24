from typing import List, Optional, Any, Dict, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.admin_catalog.models import SemanticCatalog, CorporateConnection
from app.modules.admin_catalog.schemas import (
    SemanticCatalogCreate, SemanticCatalogUpdate,
    DataDictionaryResponse, DataDictionaryTable, DataDictionaryColumn,
    AutoEnrichRequest, AutoEnrichResponse
)
from app.modules.catalog.services.schema_inspector import SchemaInspector
from app.modules.catalog.services.catalog_enricher import CatalogEnricher

class CatalogDomainService:
    """
    Domain service isolating database query logic and business rules for the Semantic Catalog.
    Delegates physical introspection to SchemaInspector and enrichment to CatalogEnricher.
    """

    @classmethod
    def resolve_connection_db_path(cls, db: Session, connection_id: Optional[int]) -> Tuple[str, CorporateConnection]:
        return SchemaInspector.resolve_connection_db_path(db, connection_id)

    @classmethod
    def _introspect_connection_metadata(cls, conn_obj: Optional[CorporateConnection], db_path: Optional[str] = None) -> List[Dict[str, Any]]:
        return SchemaInspector.introspect_connection_metadata(conn_obj, db_path)

    @classmethod
    def _heuristic_enrich(cls, table_name: str, col_name: str, col_type: str, samples: List[str]) -> Dict[str, str]:
        return CatalogEnricher.heuristic_enrich(table_name, col_name, col_type, samples)

    @classmethod
    def seed_catalog_heuristics_for_connection(cls, db: Session, connection_id: int, db_path: Optional[str] = None) -> int:
        return CatalogEnricher.seed_catalog_heuristics_for_connection(db, connection_id, db_path)

    @classmethod
    def list_catalog(
        cls,
        db: Session,
        connection_id: Optional[int] = None,
        table_name: Optional[str] = None
    ) -> List[SemanticCatalog]:
        query = db.query(SemanticCatalog)
        if connection_id is not None:
            query = query.filter(SemanticCatalog.connection_id == connection_id)
        if table_name:
            query = query.filter(SemanticCatalog.table_name == table_name)
        return query.order_by(SemanticCatalog.table_name, SemanticCatalog.column_name).all()

    @classmethod
    def create_catalog_item(cls, db: Session, item_in: SemanticCatalogCreate) -> SemanticCatalog:
        existing = db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == item_in.connection_id,
            SemanticCatalog.schema_name == item_in.schema_name,
            SemanticCatalog.table_name == item_in.table_name,
            SemanticCatalog.column_name == item_in.column_name
        ).first()

        if existing:
            existing.friendly_name = item_in.friendly_name
            existing.description = item_in.description
            existing.synonyms = item_in.synonyms
            existing.business_formula = item_in.business_formula
            existing.is_ai_generated = item_in.is_ai_generated
            db.commit()
            db.refresh(existing)
            return existing

        new_item = SemanticCatalog(
            connection_id=item_in.connection_id,
            domain_id=item_in.domain_id,
            schema_name=item_in.schema_name,
            table_name=item_in.table_name,
            column_name=item_in.column_name,
            friendly_name=item_in.friendly_name,
            description=item_in.description,
            synonyms=item_in.synonyms,
            business_formula=item_in.business_formula,
            is_ai_generated=item_in.is_ai_generated
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item

    @classmethod
    def update_catalog_item(cls, db: Session, item_id: int, item_in: SemanticCatalogUpdate) -> SemanticCatalog:
        item = db.query(SemanticCatalog).filter(SemanticCatalog.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrada de catálogo semántico no encontrada."
            )

        if item_in.domain_id is not None:
            item.domain_id = item_in.domain_id
        if item_in.friendly_name is not None:
            item.friendly_name = item_in.friendly_name
        if item_in.description is not None:
            item.description = item_in.description
        if item_in.synonyms is not None:
            item.synonyms = item_in.synonyms
        if item_in.business_formula is not None:
            item.business_formula = item_in.business_formula
        if item_in.is_ai_generated is not None:
            item.is_ai_generated = item_in.is_ai_generated

        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def delete_catalog_item(cls, db: Session, item_id: int) -> Dict[str, Any]:
        item = db.query(SemanticCatalog).filter(SemanticCatalog.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrada de catálogo semántico no encontrada."
            )
        db.delete(item)
        db.commit()
        return {"message": "Entrada de catálogo semántico eliminada.", "id": item_id}

    @classmethod
    def get_data_dictionary(cls, db: Session, connection_id: Optional[int] = None) -> DataDictionaryResponse:
        db_path, conn_obj = SchemaInspector.resolve_connection_db_path(db, connection_id)
        tables_meta = SchemaInspector.introspect_connection_metadata(conn_obj, db_path)

        catalog_entries = db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == (conn_obj.id if conn_obj else 1)
        ).all()

        catalog_map: Dict[str, SemanticCatalog] = {}
        for entry in catalog_entries:
            col = entry.column_name or "*"
            key = f"{entry.table_name.lower()}.{col.lower()}"
            catalog_map[key] = entry

        tables_result: List[DataDictionaryTable] = []
        total_cols = 0

        for t_info in tables_meta:
            tbl = t_info["table_name"]
            schema_name = t_info["schema_name"]
            row_count = t_info["row_count"]
            table_cat = catalog_map.get(f"{tbl.lower()}.*")
            table_desc = table_cat.description if table_cat else None

            cols_result: List[DataDictionaryColumn] = []
            for c_info in t_info["columns"]:
                col_name = c_info["name"]
                cat_entry = catalog_map.get(f"{tbl.lower()}.{col_name.lower()}")

                cols_result.append(DataDictionaryColumn(
                    name=col_name,
                    data_type=c_info["data_type"],
                    is_pk=c_info["is_pk"],
                    is_nullable=c_info["is_nullable"],
                    default_value=c_info["default_value"],
                    sample_values=c_info["sample_values"],
                    friendly_name=cat_entry.friendly_name if cat_entry else None,
                    description=cat_entry.description if cat_entry else None,
                    business_formula=cat_entry.business_formula if cat_entry else None,
                    is_ai_generated=cat_entry.is_ai_generated if cat_entry else False
                ))

            total_cols += len(cols_result)
            tables_result.append(DataDictionaryTable(
                table_name=tbl,
                schema_name=schema_name,
                row_count=row_count,
                column_count=len(cols_result),
                description=table_desc,
                columns=cols_result
            ))

        return DataDictionaryResponse(
            connection_id=conn_obj.id if conn_obj else 1,
            connection_name=conn_obj.name if conn_obj else "Base de Datos",
            db_type=str(conn_obj.db_type.value if hasattr(conn_obj.db_type, 'value') else conn_obj.db_type) if conn_obj else "sqlite",
            tables=tables_result,
            total_tables=len(tables_result),
            total_columns=total_cols
        )

    @classmethod
    async def auto_enrich_catalog(cls, db: Session, req: Optional[AutoEnrichRequest] = None) -> AutoEnrichResponse:
        return await CatalogEnricher.auto_enrich_catalog(db, req)
