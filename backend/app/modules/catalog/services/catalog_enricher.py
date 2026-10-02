import re
import json
from typing import List, Optional, Dict, Tuple
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

    SAP_COMMON_MAP = {
        "bukrs": ("Sociedad / Empresa", "Código de sociedad contable independiente (Company Code) en SAP.", "Dimensión de agrupación"),
        "belnr": ("Número de Documento Contable", "Número único de documento o asiento contable en SAP.", "Identificador de transacción"),
        "gjahr": ("Ejercicio Fiscal", "Año o ejercicio contable en el que se registra la transacción.", "DATE_PART('year', fecha)"),
        "wrbtr": ("Importe en Moneda de Documento", "Monto registrado en la moneda original de la transacción.", "SUM(wrbtr)"),
        "dmbtr": ("Importe en Moneda Local", "Monto convertido a la moneda local de la sociedad.", "SUM(dmbtr)"),
        "shkzg": ("Indicador Debe/Haber", "Indica si la posición contable es Débito/Debe ('S') o Crédito/Haber ('H').", "Filtro contable S/H"),
        "matnr": ("Código de Material", "Identificador alfanumérico único del producto o material en SAP.", "Clave foránea (MARA)"),
        "kunnr": ("Código de Cliente", "Identificador único de la cuenta de cliente en SAP.", "Clave foránea (KNA1)"),
        "lifnr": ("Código de Proveedor", "Identificador único de la cuenta de proveedor en SAP.", "Clave foránea (LFA1)"),
        "werks": ("Centro / Planta", "Unidad organizativa de producción, almacenamiento o distribución en SAP.", "Dimensión de centro"),
        "lgort": ("Almacén", "Ubicación física de almacenamiento de mercancías en SAP.", "Dimensión de almacén"),
        "vbeln": ("Documento Comercial / Factura", "Número de documento de ventas, entrega o facturación en SAP.", "Clave de documento comercial"),
        "posnr": ("Posición de Documento", "Número de renglón o ítem dentro del documento comercial o contable.", "Número de ítem"),
        "ebeln": ("Documento de Compra / Pedido", "Número de pedido de compras en SAP.", "Clave de orden de compra"),
        "ebelp": ("Posición de Pedido de Compra", "Número de posición dentro del pedido de compras en SAP.", "Número de ítem"),
        "netwr": ("Valor Neto", "Importe neto del pedido o factura sin impuestos.", "SUM(netwr)"),
        "menge": ("Cantidad", "Cantidad física de unidades de material o servicio.", "SUM(menge)"),
        "meins": ("Unidad de Medida Base", "Unidad de medida del stock o servicio (ej. KG, UN, L).", "Unidad de medida"),
        "bldat": ("Fecha de Documento", "Fecha de emisión física o legal del documento mercantil.", "DATE(bldat)"),
        "budat": ("Fecha de Contabilización", "Fecha en que se registra contablemente el impacto en el libro mayor.", "DATE(budat)"),
        "blart": ("Clase de Documento", "Tipo o clasificación contable del asiento (ej. KR, KZ, SA, DR).", "Dimensión de documento"),
        "waers": ("Moneda de Transacción", "Clave de moneda de la operación (ej. USD, EUR, CLP, MXN).", "Código ISO de moneda"),
        "mwskz": ("Indicador de Impuestos", "Código que define la alícuota o tratamiento tributario (IVA/Tax).", "Clasificación tributaria"),
        "kostl": ("Centro de Coste", "Unidad organizativa responsable del devengo de costos operativos.", "Dimensión de Controlling"),
        "prctr": ("Centro de Beneficio", "Unidad organizativa responsable de la rentabilidad y resultados.", "Dimensión de Controlling"),
        "aufnr": ("Orden de Fabricación / Trabajo", "Número de orden interna o de producción en SAP.", "Identificador de orden"),
    }

    @classmethod
    def heuristic_enrich(cls, table_name: str, col_name: str, col_type: str, samples: List[str]) -> Dict[str, str]:
        t_lower = table_name.lower()
        c_lower = col_name.lower()

        # Direct SAP acronym match
        if c_lower in cls.SAP_COMMON_MAP:
            f_name, d_text, f_formula = cls.SAP_COMMON_MAP[c_lower]
            return {
                "friendly_name": f_name,
                "description": d_text,
                "business_formula": f_formula
            }

        friendly = c_lower.replace("_", " ").title()
        desc = f"Campo '{col_name}' de la tabla {table_name}"
        formula = "Columna directa"

        if c_lower in ("id", "id_" + t_lower, t_lower + "_id", "uuid", "key") or c_lower.startswith("id_") or c_lower.endswith("_id") or c_lower.startswith("cod_") or c_lower.startswith("codigo_"):
            friendly = f"Identificador ({friendly})"
            desc = f"Clave identificadora o código único del registro en {table_name}."
            formula = "Clave Primaria / Foránea (ID)"
        elif "precio" in c_lower or "price" in c_lower:
            friendly = "Precio Unitario"
            desc = f"Valor monetario unitario asignado al elemento en {table_name} en moneda local/USD."
            formula = "ROUND(AVG(precio), 2)"
        elif "monto" in c_lower or "total" in c_lower or "amount" in c_lower or "subtotal" in c_lower:
            friendly = "Monto Total"
            desc = f"Importe financiero o suma acumulada calculada para la transacción en {table_name}."
            formula = f"SUM({col_name})"
        elif "saldo" in c_lower or "balance" in c_lower:
            friendly = "Saldo Financiero"
            desc = f"Saldo remanente o balance monetario en {table_name}."
            formula = f"SUM({col_name})"
        elif "ingreso" in c_lower or "revenue" in c_lower or "venta" in c_lower or "sales" in c_lower:
            friendly = "Ingreso Corporativo"
            desc = f"Total de ingresos o ventas devengadas registradas en {table_name}."
            formula = f"SUM({col_name})"
        elif "costo" in c_lower or "cost" in c_lower or "gasto" in c_lower or "expense" in c_lower:
            friendly = "Costo Operativo"
            desc = f"Costos directos o gastos operativos incurridos en {table_name}."
            formula = f"SUM({col_name})"
        elif "utilidad" in c_lower or "profit" in c_lower or "margen" in c_lower or "margin" in c_lower:
            friendly = "Margen de Utilidad"
            desc = f"Margen o beneficio financiero calculado en {table_name}."
            formula = "ingreso - costo"
        elif "salario" in c_lower or "salary" in c_lower or "sueldo" in c_lower:
            friendly = "Salario / Remuneración"
            desc = f"Compensación monetaria asignada al colaborador en {table_name}."
            formula = f"AVG({col_name})"
        elif "cantidad" in c_lower or "cant" in c_lower or "qty" in c_lower or "quantity" in c_lower or "stock" in c_lower or "unidades" in c_lower:
            friendly = "Cantidad / Volumen"
            desc = f"Volumen físico o unidades cuantitativas registradas en {table_name}."
            formula = f"SUM({col_name})"
        elif "fecha" in c_lower or "date" in c_lower or "timestamp" in c_lower or "dia" in c_lower or "mes" in c_lower or "anio" in c_lower or "año" in c_lower:
            friendly = "Fecha de Registro"
            desc = f"Marca temporal o fecha calendario del evento o transacción en {table_name}."
            formula = f"DATE({col_name})"
        elif "cliente" in c_lower or "customer" in c_lower or "rut" in c_lower:
            friendly = "Cliente / Cuenta"
            desc = f"Entidad o receptor comercial asociado al registro en {table_name}."
            formula = "Dimensión de cliente"
        elif "producto" in c_lower or "product" in c_lower or "articulo" in c_lower or "sku" in c_lower:
            friendly = "Producto / Ítem"
            desc = f"Bien, artículo o servicio referenciado en {table_name}."
            formula = "Dimensión de producto"
        elif "proveedor" in c_lower or "supplier" in c_lower or "vendor" in c_lower:
            friendly = "Proveedor Comercial"
            desc = f"Proveedor de insumos o servicios en {table_name}."
            formula = "Dimensión de proveedor"
        elif "categoria" in c_lower or "category" in c_lower or "segmento" in c_lower or "segment" in c_lower or "rubro" in c_lower:
            friendly = "Categoría / Segmento"
            desc = f"Segmento o clasificación temática para agrupar en {table_name}."
            formula = "Dimensión de agrupación"
        elif "estado" in c_lower or "status" in c_lower or "activo" in c_lower:
            friendly = "Estado del Registro"
            desc = f"Condición o fase en el ciclo de vida del registro en {table_name}."
            formula = "Dimensión de estado"
        elif "tipo" in c_lower or "type" in c_lower:
            friendly = "Tipo / Clasificación"
            desc = f"Tipología o naturaleza operativa en {table_name}."
            formula = "Dimensión de agrupación"
        elif "sucursal" in c_lower or "tienda" in c_lower or "branch" in c_lower or "store" in c_lower:
            friendly = "Sucursal / Tienda"
            desc = f"Punto físico o sucursal comercial en {table_name}."
            formula = "Dimensión geográfica"
        elif "ciudad" in c_lower or "city" in c_lower or "pais" in c_lower or "country" in c_lower:
            friendly = "Ubicación Geográfica"
            desc = f"Localización territorial asociada al registro en {table_name}."
            formula = "Dimensión geográfica"
        elif "nombre" in c_lower or "name" in c_lower or "razon_social" in c_lower or "titulo" in c_lower:
            friendly = f"Nombre de {table_name}"
            desc = f"Denominación comercial o nombre descriptivo en {table_name}."
            formula = "Texto literal"
        elif "descuento" in c_lower or "discount" in c_lower:
            friendly = "Descuento Comercial"
            desc = f"Rebaja o descuento aplicado sobre el monto en {table_name}."
            formula = f"SUM({col_name})"
        elif "impuesto" in c_lower or "tax" in c_lower or "iva" in c_lower:
            friendly = "Impuesto Fiscal"
            desc = f"Monto impositivo o gravamen tributario en {table_name}."
            formula = f"SUM({col_name})"
        elif samples:
            desc = f"Registro tipo {col_type} en {table_name}. Muestra: {', '.join(samples[:2])}."

        return {
            "friendly_name": friendly,
            "description": desc,
            "business_formula": formula
        }

    @classmethod
    def seed_catalog_heuristics_for_connection(
        cls,
        db: Session,
        connection_id: int,
        db_path: Optional[str] = None,
        only_tables: Optional[List[str]] = None
    ) -> int:
        """
        Inspects the physical database and automatically generates initial heuristic semantic catalog
        entries for all tables and columns that don't already have catalog entries for this connection.
        """
        conn_obj = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
        tables_meta = SchemaInspector.introspect_connection_metadata(conn_obj, db_path)
        if not tables_meta:
            return 0

        if only_tables:
            only_lower = {t.lower() for t in only_tables}
            tables_meta = [t for t in tables_meta if t["table_name"].lower() in only_lower]

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

                    # ponytail: Instant heuristic enrichment (<0.001s) replaces the O(N) sequential LLM
                    # call loop that hung the database registration wizard for 30+ minutes on local CPU inference.
                    meta = cls.heuristic_enrich(tbl, col_name, col_type, sample_vals)

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
