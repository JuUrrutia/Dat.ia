import os
import sqlite3
import json
import re
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.models.catalog import SemanticCatalog
from app.models.connection import CorporateConnection, DatabaseType
from app.core.config import settings
from app.services.llm_service import LLMService
from app.schemas.catalog_schema import (
    SemanticCatalogCreate,
    SemanticCatalogUpdate,
    SemanticCatalogOut,
    DataDictionaryResponse,
    DataDictionaryTable,
    DataDictionaryColumn,
    AutoEnrichRequest,
    AutoEnrichResponse
)

router = APIRouter()

def _resolve_connection_db_path(db: Session, connection_id: Optional[int]) -> tuple[str, CorporateConnection]:
    """Finds physical database path and connection record."""
    conn = None
    if connection_id:
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
    
    if not conn:
        conn = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).first()
        if not conn:
            conn = db.query(CorporateConnection).first()

    # Determine SQLite file path
    if conn and conn.db_type == DatabaseType.SQLITE:
        if conn.host and os.path.exists(conn.host):
            return conn.host, conn
        if conn.database_name and os.path.exists(conn.database_name):
            return conn.database_name, conn

    # Fallback to configured settings SQLite path
    db_path = settings.SQLITE_DB_PATH
    if not conn:
        # Create a mock or default connection object
        conn = CorporateConnection(
            id=1,
            name="Base de Datos Corporativa",
            db_type=DatabaseType.SQLITE,
            host=db_path,
            port=0,
            database_name=os.path.basename(db_path),
            username="admin",
            is_active=True
        )
    return db_path, conn

@router.get("", response_model=List[SemanticCatalogOut])
def list_catalog(
    connection_id: Optional[int] = Query(None, description="Filtrar por ID de conexión"),
    table_name: Optional[str] = Query(None, description="Filtrar por nombre de tabla"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Lists semantic catalog rules and data dictionary definitions."""
    query = db.query(SemanticCatalog)
    if connection_id is not None:
        query = query.filter(SemanticCatalog.connection_id == connection_id)
    if table_name:
        query = query.filter(SemanticCatalog.table_name == table_name)
    return query.order_by(SemanticCatalog.table_name, SemanticCatalog.column_name).all()

@router.post("", response_model=SemanticCatalogOut, status_code=status.HTTP_201_CREATED)
def create_catalog_item(
    item_in: SemanticCatalogCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Creates or updates a semantic catalog entry (Admin only)."""
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

@router.put("/{item_id}", response_model=SemanticCatalogOut)
def update_catalog_item(
    item_id: int,
    item_in: SemanticCatalogUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Updates an existing semantic catalog entry (Admin only)."""
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

@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
def delete_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Deletes a semantic catalog entry (Admin only)."""
    item = db.query(SemanticCatalog).filter(SemanticCatalog.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrada de catálogo semántico no encontrada."
        )
    db.delete(item)
    db.commit()
    return {"message": "Entrada de catálogo semántico eliminada.", "id": item_id}

@router.get("/data-dictionary", response_model=DataDictionaryResponse)
def get_data_dictionary(
    connection_id: Optional[int] = Query(None, description="ID de conexión a inspeccionar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Introspects the real schema of the target database dynamically, returning technical details
    (data types, PKs, row counts, sample data) combined with semantic descriptions.
    """
    db_path, conn_obj = _resolve_connection_db_path(db, connection_id)
    
    if not db_path or not os.path.exists(db_path):
        return DataDictionaryResponse(
            connection_id=conn_obj.id if conn_obj else 1,
            connection_name=conn_obj.name if conn_obj else "Base de Datos",
            db_type=conn_obj.db_type if conn_obj else "sqlite",
            tables=[],
            total_tables=0,
            total_columns=0
        )

    # Fetch existing catalog mappings from DB
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

    try:
        sqlite_conn = sqlite3.connect(db_path)
        sqlite_cursor = sqlite_conn.cursor()

        # Get all physical tables (excluding metadata tables)
        ignored_tables = {
            "sqlite_sequence", "roles", "domains", "corporate_connections",
            "users", "role_domain_links", "role_table_permissions",
            "role_column_permissions", "semantic_catalog", "audit_logs"
        }
        
        raw_tables = [
            r[0] for r in sqlite_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            ).fetchall()
        ]
        active_tables = [t for t in raw_tables if t.lower() not in ignored_tables]

        for tbl in active_tables:
            # Row count
            try:
                row_count_res = sqlite_cursor.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()
                row_count = row_count_res[0] if row_count_res else 0
            except Exception:
                row_count = 0

            # Column info: cid, name, type, notnull, dflt_value, pk
            cols_info = sqlite_cursor.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            
            table_cat = catalog_map.get(f"{tbl.lower()}.*")
            table_desc = table_cat.description if table_cat else None

            cols_result: List[DataDictionaryColumn] = []

            for col in cols_info:
                col_name = col[1]
                col_type = col[2] or "TEXT"
                not_null = bool(col[3])
                default_val = str(col[4]) if col[4] is not None else None
                is_pk = bool(col[5])

                # Get sample values (up to 3 distinct non-null)
                sample_vals = []
                try:
                    samples_raw = sqlite_cursor.execute(
                        f'SELECT DISTINCT "{col_name}" FROM "{tbl}" WHERE "{col_name}" IS NOT NULL AND "{col_name}" != \'\' LIMIT 3'
                    ).fetchall()
                    sample_vals = [str(s[0]) for s in samples_raw if s[0] is not None]
                except Exception:
                    pass

                cat_entry = catalog_map.get(f"{tbl.lower()}.{col_name.lower()}")

                cols_result.append(DataDictionaryColumn(
                    name=col_name,
                    data_type=col_type,
                    is_pk=is_pk,
                    is_nullable=not not_null,
                    default_value=default_val,
                    sample_values=sample_vals,
                    friendly_name=cat_entry.friendly_name if cat_entry else None,
                    description=cat_entry.description if cat_entry else None,
                    business_formula=cat_entry.business_formula if cat_entry else None,
                    is_ai_generated=cat_entry.is_ai_generated if cat_entry else False
                ))

            total_cols += len(cols_result)
            tables_result.append(DataDictionaryTable(
                table_name=tbl,
                schema_name="main",
                row_count=row_count,
                column_count=len(cols_result),
                description=table_desc,
                columns=cols_result
            ))

        sqlite_conn.close()
    except Exception as e:
        pass

    return DataDictionaryResponse(
        connection_id=conn_obj.id if conn_obj else 1,
        connection_name=conn_obj.name if conn_obj else "Base de Datos",
        db_type=str(conn_obj.db_type) if conn_obj else "sqlite",
        tables=tables_result,
        total_tables=len(tables_result),
        total_columns=total_cols
    )

def _heuristic_enrich(table_name: str, col_name: str, col_type: str, samples: List[str]) -> Dict[str, str]:
    """Generates intelligent semantic description and formula based on naming conventions."""
    t_lower = table_name.lower()
    c_lower = col_name.lower()

    friendly = c_lower.replace("_", " ").title()
    desc = f"Campo '{col_name}' de la tabla {table_name}"
    formula = "Columna directa"

    # Common pattern recognition
    if c_lower in ("id", "id_" + t_lower, t_lower + "_id", "uuid", "key"):
        friendly = f"Identificador de {table_name}"
        desc = f"Clave primaria o identificador único del registro en {table_name}."
        formula = "Clave Primaria (PK)"
    elif "precio" in c_lower or "price" in c_lower:
        friendly = "Precio Unitario"
        desc = f"Valor monetario unitario asignado al elemento en {table_name} en USD/moneda local."
        formula = "ROUND(monto, 2)"
    elif "monto" in c_lower or "total" in c_lower or "amount" in c_lower:
        friendly = "Monto Total"
        desc = f"Importe financiero o suma acumulada calculada para la transacción en {table_name}."
        formula = "SUM(monto_total)"
    elif "ingreso" in c_lower or "revenue" in c_lower:
        friendly = "Ingreso Corporativo"
        desc = "Total de ingresos brutos o devengados registrados en el periodo fiscal."
        formula = "SUM(ingreso_bruto)"
    elif "costo" in c_lower or "cost" in c_lower:
        friendly = "Costo Operativo"
        desc = "Costos directos e indirectos incurridos durante la operación del negocio."
        formula = "SUM(costo_total)"
    elif "utilidad" in c_lower or "profit" in c_lower or "margen" in c_lower:
        friendly = "Margen de Utilidad"
        desc = "Utilidad neta calculada deduciendo costos operativos de los ingresos totales."
        formula = "ingreso_bruto - costo_total"
    elif "salario" in c_lower or "salary" in c_lower:
        friendly = "Salario Mensual"
        desc = "Remuneración bruta asignada al colaborador por periodo contractual."
        formula = "AVG(salario_bruto)"
    elif "fecha" in c_lower or "date" in c_lower or "timestamp" in c_lower:
        friendly = "Fecha de Registro"
        desc = "Marca temporal o fecha calendario en la que ocurrió el evento o transacción."
        formula = "DATE(fecha)"
    elif "nombre" in c_lower or "name" in c_lower or "title" in c_lower:
        friendly = f"Nombre de {table_name}"
        desc = f"Denominación o nombre comercial descriptivo asociado al registro de {table_name}."
        formula = "Texto literal"
    elif "categoria" in c_lower or "category" in c_lower:
        friendly = "Categoría de Clasificación"
        desc = "Segmento o clasificación temática para agrupar los registros correspondientes."
        formula = "Dimensión de agrupación"
    elif "cpu" in c_lower:
        friendly = "Uso de CPU"
        desc = "Porcentaje de capacidad de procesamiento de CPU utilizado por la infraestructura."
        formula = "AVG(porcentaje_cpu)"
    elif "ram" in c_lower or "memoria" in c_lower:
        friendly = "Consumo de RAM (GB)"
        desc = "Capacidad de memoria RAM consumida en Gigabytes por el servidor o servicio."
        formula = "AVG(uso_ram_gb)"
    elif "falla" in c_lower or "error" in c_lower or "incidente" in c_lower:
        friendly = "Tipo de Incidente"
        desc = "Tipificación técnica o severidad del error reportado en la infraestructura de TI."
        formula = "COUNT(incidentes)"
    elif "horas" in c_lower or "hours" in c_lower or "tiempo" in c_lower:
        friendly = "Tiempo de Resolución (Horas)"
        desc = "Tiempo total transcurrido desde la detección hasta la resolución definitiva del caso (SLA)."
        formula = "AVG(horas_resolucion)"
    elif "answer" in c_lower:
        friendly = "Texto de Respuesta"
        desc = "Respuesta textual proporcionada por el encuestado a la pregunta correspondiente."
        formula = "Respuesta cualitativa/categórica"
    elif "question" in c_lower:
        friendly = "Pregunta de Encuesta"
        desc = "Enunciado o pregunta formulada en el estudio corporativo."
        formula = "Texto de encuesta"
    elif "survey" in c_lower:
        friendly = "Edición de Encuesta"
        desc = "Identificador o año correspondiente a la edición de la encuesta realizada."
        formula = "Año / Edición"
    elif samples:
        desc = f"Registro de datos tipo {col_type}. Valores de ejemplo: {', '.join(samples[:2])}."

    return {
        "friendly_name": friendly,
        "description": desc,
        "business_formula": formula
    }

@router.post("/auto-enrich", response_model=AutoEnrichResponse)
async def auto_enrich_catalog(
    req: Optional[AutoEnrichRequest] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """
    Intelligently inspects the database schema and automatically generates rich semantic descriptions,
    business formulas, and friendly names using the Local LLM (or heuristic metadata analysis),
    persisting everything to the semantic_catalog table.
    """
    conn_req_id = req.connection_id if req else None
    db_path, conn_obj = _resolve_connection_db_path(db, conn_req_id)
    conn_id = conn_obj.id if conn_obj else 1

    if not db_path or not os.path.exists(db_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontró una base de datos activa para auto-enriquecer."
        )

    # Introspect SQLite tables and columns
    sqlite_conn = sqlite3.connect(db_path)
    sqlite_cursor = sqlite_conn.cursor()

    ignored_tables = {
        "sqlite_sequence", "roles", "domains", "corporate_connections",
        "users", "role_domain_links", "role_table_permissions",
        "role_column_permissions", "semantic_catalog", "audit_logs"
    }

    raw_tables = [
        r[0] for r in sqlite_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    active_tables = [t for t in raw_tables if t.lower() not in ignored_tables]
    if req.table_name:
        active_tables = [t for t in active_tables if t.lower() == req.table_name.lower()]

    enriched_count = 0

    for tbl in active_tables:
        cols_info = sqlite_cursor.execute(f'PRAGMA table_info("{tbl}")').fetchall()

        for col in cols_info:
            col_name = col[1]
            col_type = col[2] or "TEXT"

            # Check if entry already exists
            existing = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == conn_id,
                SemanticCatalog.table_name == tbl,
                SemanticCatalog.column_name == col_name
            ).first()

            # Sample values
            sample_vals = []
            try:
                samples_raw = sqlite_cursor.execute(
                    f'SELECT DISTINCT "{col_name}" FROM "{tbl}" WHERE "{col_name}" IS NOT NULL AND "{col_name}" != \'\' LIMIT 3'
                ).fetchall()
                sample_vals = [str(s[0]) for s in samples_raw if s[0] is not None]
            except Exception:
                pass

            # Try LLM enrichment first if available
            llm_enriched = None
            try:
                system_prompt = (
                    "Eres un especialista en gobernanza de datos y catálogos semánticos empresariales. "
                    "Responde ÚNICAMENTE con un JSON con los campos 'friendly_name', 'description' y 'business_formula' en español."
                )
                prompt = (
                    f"Tabla: '{tbl}', Columna: '{col_name}', Tipo SQL: '{col_type}', Valores muestra: {sample_vals}.\n"
                    "Genera el nombre amigable de negocio, descripción funcional clara y fórmula o regla de cálculo sugerida."
                )
                llm_resp = await LLMService.generate_completion(
                    prompt,
                    system_prompt=system_prompt,
                    max_tokens=150,
                    temperature=0.2
                )
                if llm_resp:
                    json_match = re.search(r'\{[\s\S]*\}', llm_resp)
                    if json_match:
                        llm_data = json.loads(json_match.group(0))
                        llm_enriched = {
                            "friendly_name": str(llm_data.get("friendly_name", "")).strip(),
                            "description": str(llm_data.get("description", "")).strip(),
                            "business_formula": str(llm_data.get("business_formula", "")).strip(),
                        }
            except Exception:
                pass

            # Fallback to heuristic
            meta = llm_enriched if (llm_enriched and llm_enriched.get("description")) else _heuristic_enrich(tbl, col_name, col_type, sample_vals)

            if existing:
                if not existing.description or existing.is_ai_generated:
                    existing.friendly_name = meta["friendly_name"]
                    existing.description = meta["description"]
                    existing.business_formula = meta["business_formula"]
                    existing.is_ai_generated = True
                    enriched_count += 1
            else:
                new_cat = SemanticCatalog(
                    connection_id=conn_id,
                    schema_name="main",
                    table_name=tbl,
                    column_name=col_name,
                    friendly_name=meta["friendly_name"],
                    description=meta["description"],
                    business_formula=meta["business_formula"],
                    is_ai_generated=True
                )
                db.add(new_cat)
                enriched_count += 1

    sqlite_conn.close()
    db.commit()

    all_items = db.query(SemanticCatalog).filter(
        SemanticCatalog.connection_id == conn_id
    ).order_by(SemanticCatalog.table_name, SemanticCatalog.column_name).all()

    return AutoEnrichResponse(
        success=True,
        message=f"Catálogo semántico enriquecido exitosamente: {enriched_count} campos procesados y guardados en la base de datos.",
        enriched_count=enriched_count,
        catalog_items=all_items
    )
