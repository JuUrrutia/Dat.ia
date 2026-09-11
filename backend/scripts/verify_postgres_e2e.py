import sys
import os
import asyncio

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, build_engine_for_connector
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType, RoleTablePermission, SemanticCatalog
from app.modules.auth.models import User, Role
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.chat_engine.sql_executor import SQLExecutor
from app.modules.chat_engine.engine import QueryEngine

async def main():
    print("==================================================")
    print("VERIFICACIÓN END-TO-END POSTGRESQL (DATIA)")
    print("==================================================")

    # 1. Engine Check
    print(f"1. Engine Dialect: {engine.dialect.name}")
    assert engine.dialect.name == "postgresql", f"Expected postgresql, got {engine.dialect.name}"
    print("   [OK] Conectado a PostgreSQL como motor principal.")

    db = SessionLocal()
    try:
        # 2. Corporate Connection Check
        conn = db.query(CorporateConnection).filter(
            CorporateConnection.is_active == True,
            CorporateConnection.db_type == DatabaseType.POSTGRESQL
        ).first()

        if not conn:
            conn = db.query(CorporateConnection).filter(
                CorporateConnection.db_type == DatabaseType.POSTGRESQL
            ).first()
            if conn:
                db.query(CorporateConnection).update({CorporateConnection.is_active: False})
                conn.is_active = True
                db.commit()
                db.refresh(conn)
                print(f"   [INFO] Se activó la conexión PostgreSQL existente: '{conn.name}'.")
            else:
                print("   [INFO] No se encontró conexión PostgreSQL en la BD. Ejecutando bootstrap...")
                from scripts.setup_postgres_full import run as run_setup
                run_setup()
                conn = db.query(CorporateConnection).filter(
                    CorporateConnection.db_type == DatabaseType.POSTGRESQL,
                    CorporateConnection.is_active == True
                ).first()

        assert conn is not None, "No active CorporateConnection found for PostgreSQL!"
        print(f"2. Conexión Activa: '{conn.name}' | Tipo: {conn.db_type} | Base de Datos: {conn.database_name}")
        assert conn.db_type == DatabaseType.POSTGRESQL or str(conn.db_type).lower() == "postgresql", "Active connection is not PostgreSQL!"
        print("   [OK] Conector activo apunta a PostgreSQL corporativo.")

        # 3. Dynamic Schema Pruning
        schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
            db=db,
            user_role="Economista",
            connection_id=conn.id,
            is_admin=False
        )
        allowed_tables = schema_info.get("allowed_tables", set())
        print(f"3. Tablas permitidas para Economista: {allowed_tables}")
        assert "fact_ventas" in allowed_tables, "fact_ventas not in allowed tables!"
        print("   [OK] DynamicSchemaPruningService inspeccionó PostgreSQL correctamente.")

        # 4. Direct SQL Execution on Corporate PostgreSQL
        sql = "SELECT count(*) as total_ventas, round(sum(monto_total)::numeric, 2) as monto_total_facturado FROM fact_ventas;"
        rows = SQLExecutor.execute_raw_sql(conn, sql, dialect="postgres")
        print(f"4. Consulta directa en fact_ventas (PostgreSQL): {rows}")
        assert len(rows) > 0 and rows[0]["total_ventas"] > 0, "No rows returned from PostgreSQL!"
        print("   [OK] Ejecución SQL directa en PostgreSQL verificada con éxito.")

        # 5. Full QueryEngine Execution (Natural Language / SQL)
        test_query = "SELECT count(*) as total, sum(monto_total) as monto FROM fact_ventas"
        resp = await QueryEngine.execute_query(
            question=test_query,
            user_role="Economista",
            is_admin=False,
            db=db,
            connection_id=conn.id
        )
        print(f"5. QueryEngine execute_query: Filas retornadas: {len(resp.data_rows)} | Tiempo: {resp.traceability.execution_time_ms}ms")
        assert len(resp.data_rows) > 0, "QueryEngine did not return data!"
        print(f"   SQL Ejecutado: {resp.traceability.sql_executed}")
        print(f"   Muestra de datos de respuesta: {resp.data_rows}")
        print("   [OK] QueryEngine completó la consulta de forma exitosa usando PostgreSQL.")

        print("==================================================")
        print("TODAS LAS VERIFICACIONES PASARON EXITOSAMENTE (100% POSTGRESQL)")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
