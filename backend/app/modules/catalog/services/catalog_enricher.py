import re
import json
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.admin_catalog.models import SemanticCatalog, CorporateConnection
from app.modules.admin_catalog.schemas import AutoEnrichRequest, AutoEnrichResponse
from app.modules.chat_engine.llm_service import LLMService
from app.modules.catalog.services.schema_inspector import SchemaInspector

class CatalogEnricher:
    """
    Encapsulates heuristic inference and LLM-powered semantic enrichment
    for databases and columns.
    """

    @classmethod
    def heuristic_enrich(cls, table_name: str, col_name: str, col_type: str, samples: List[str]) -> Dict[str, str]:
        t_lower = table_name.lower()
        c_lower = col_name.lower()

        friendly = c_lower.replace("_", " ").title()
        desc = f"Campo '{col_name}' de la tabla {table_name}"
        formula = "Columna directa"

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
        elif samples:
            desc = f"Registro de datos tipo {col_type}. Valores de ejemplo: {', '.join(samples[:2])}."

        return {
            "friendly_name": friendly,
            "description": desc,
            "business_formula": formula
        }

    @classmethod
    def seed_catalog_heuristics_for_connection(cls, db: Session, connection_id: int, db_path: Optional[str] = None) -> int:
        """
        Inspects the physical database and automatically generates initial heuristic semantic catalog
        entries for all tables and columns that don't already have catalog entries for this connection.
        """
        conn_obj = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
        tables_meta = SchemaInspector.introspect_connection_metadata(conn_obj, db_path)
        if not tables_meta:
            return 0

        seeded_count = 0
        for tbl_info in tables_meta:
            tbl = tbl_info["table_name"]
            schema_name = tbl_info["schema_name"]
            for col in tbl_info["columns"]:
                col_name = col["name"]
                col_type = col["data_type"]
                sample_vals = col["sample_values"]

                existing = db.query(SemanticCatalog).filter(
                    SemanticCatalog.connection_id == connection_id,
                    SemanticCatalog.table_name == tbl,
                    SemanticCatalog.column_name == col_name
                ).first()

                if not existing:
                    meta = cls.heuristic_enrich(tbl, col_name, col_type, sample_vals)
                    new_cat = SemanticCatalog(
                        connection_id=connection_id,
                        schema_name=schema_name,
                        table_name=tbl,
                        column_name=col_name,
                        friendly_name=meta["friendly_name"],
                        description=meta["description"],
                        business_formula=meta["business_formula"],
                        is_ai_generated=True
                    )
                    db.add(new_cat)
                    seeded_count += 1

        if seeded_count > 0:
            db.commit()

        return seeded_count

    @classmethod
    async def auto_enrich_catalog(cls, db: Session, req: Optional[AutoEnrichRequest] = None) -> AutoEnrichResponse:
        conn_req_id = req.connection_id if req else None

        targets: List[Tuple[CorporateConnection, str]] = []
        if conn_req_id:
            conn_obj = db.query(CorporateConnection).filter(CorporateConnection.id == conn_req_id).first()
            if conn_obj:
                db_path, _ = SchemaInspector.resolve_connection_db_path(db, conn_req_id)
                targets.append((conn_obj, db_path))
        else:
            active_conns = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).all()
            if not active_conns:
                active_conns = db.query(CorporateConnection).all()
            for c_obj in active_conns:
                db_path, _ = SchemaInspector.resolve_connection_db_path(db, c_obj.id)
                targets.append((c_obj, db_path))

        if not targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontró una base de datos activa para auto-enriquecer."
            )

        total_enriched_count = 0
        last_conn_id = targets[0][0].id

        for conn_obj, db_path in targets:
            conn_id = conn_obj.id
            last_conn_id = conn_id
            tables_meta = SchemaInspector.introspect_connection_metadata(conn_obj, db_path)
            if req and req.table_name:
                tables_meta = [t for t in tables_meta if t["table_name"].lower() == req.table_name.lower()]

            for tbl_info in tables_meta:
                tbl = tbl_info["table_name"]
                schema_name = tbl_info["schema_name"]
                for col_info in tbl_info["columns"]:
                    col_name = col_info["name"]
                    col_type = col_info["data_type"]
                    sample_vals = col_info["sample_values"]

                    existing = db.query(SemanticCatalog).filter(
                        SemanticCatalog.connection_id == conn_id,
                        SemanticCatalog.table_name == tbl,
                        SemanticCatalog.column_name == col_name
                    ).first()

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

                    meta = llm_enriched if (llm_enriched and llm_enriched.get("description")) else cls.heuristic_enrich(tbl, col_name, col_type, sample_vals)

                    if existing:
                        if not existing.description or existing.is_ai_generated:
                            existing.friendly_name = meta["friendly_name"]
                            existing.description = meta["description"]
                            existing.business_formula = meta["business_formula"]
                            existing.is_ai_generated = True
                            total_enriched_count += 1
                    else:
                        new_cat = SemanticCatalog(
                            connection_id=conn_id,
                            schema_name=schema_name,
                            table_name=tbl,
                            column_name=col_name,
                            friendly_name=meta["friendly_name"],
                            description=meta["description"],
                            business_formula=meta["business_formula"],
                            is_ai_generated=True
                        )
                        db.add(new_cat)
                        total_enriched_count += 1

        db.commit()

        # Query all items for the target connection(s)
        query = db.query(SemanticCatalog)
        if conn_req_id:
            query = query.filter(SemanticCatalog.connection_id == conn_req_id)
        elif len(targets) == 1:
            query = query.filter(SemanticCatalog.connection_id == last_conn_id)

        all_items = query.order_by(SemanticCatalog.table_name, SemanticCatalog.column_name).all()

        return AutoEnrichResponse(
            success=True,
            message=f"Catálogo semántico enriquecido exitosamente: {total_enriched_count} campos procesados y guardados en la base de datos.",
            enriched_count=total_enriched_count,
            catalog_items=all_items
        )
