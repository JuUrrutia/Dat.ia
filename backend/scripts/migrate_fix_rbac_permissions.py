"""
Database migration script to sanitize and enforce strict RBAC domain boundaries in role_table_permissions.
Purges business/financial tables from TI roles and tech/infrastructure tables from financial roles.
"""
import sys
import os

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.modules.auth.models import Role
from app.modules.admin_catalog.models import RoleTablePermission

BUSINESS_TABLES = [
    "fact_ventas", "fact_ingresos_costos", "dim_clientes", 
    "dim_productos", "dim_categorias", "vbak_cabpedidoventa", 
    "vbap_pospedidoventa", "ekko_cabpedidocompra", "ekpo_pospedidocompra", 
    "kna1_clientes"
]

TECH_TABLES = [
    "dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos"
]

def sanitize_rbac_permissions():
    db = SessionLocal()
    try:
        print("=== INICIANDO SANEAMIENTO DE PERMISOS RBAC ===")

        # 1. Purge business tables from all TI roles
        all_ti_roles = db.query(Role).filter(
            Role.name.in_(["Ingeniero de Infraestructura & TI", "TI"])
        ).all()
        ti_deleted_count = 0
        for r in all_ti_roles:
            del_rows = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == r.id,
                RoleTablePermission.table_name.in_(BUSINESS_TABLES)
            ).delete(synchronize_session=False)
            ti_deleted_count += del_rows
            print(f"Rol TI '{r.name}' (ID={r.id}): {del_rows} permisos de tablas financieras/comerciales eliminados.")

        # 2. Purge tech tables from all financial roles
        all_fin_roles = db.query(Role).filter(
            Role.name.in_(["Analista Financiero & Comercial", "Economista"])
        ).all()
        fin_deleted_count = 0
        for r in all_fin_roles:
            del_rows = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == r.id,
                RoleTablePermission.table_name.in_(TECH_TABLES)
            ).delete(synchronize_session=False)
            fin_deleted_count += del_rows
            print(f"Rol Financiero '{r.name}' (ID={r.id}): {del_rows} permisos de tablas de infraestructura eliminados.")

        db.commit()
        print(f"=== SANEAMIENTO COMPLETADO EXITOSAMENTE ===")
        print(f"Total registros eliminados: {ti_deleted_count + fin_deleted_count} (TI: {ti_deleted_count}, Financiero: {fin_deleted_count})")

        # 3. Print verified table permissions for both roles
        print("\n=== PERMISOS VERIFICADOS ===")
        for r in all_ti_roles + all_fin_roles:
            perms = db.query(RoleTablePermission).filter(RoleTablePermission.role_id == r.id).all()
            allowed_tables = sorted(list({p.table_name for p in perms if p.is_allowed}))
            print(f"Rol '{r.name}': {allowed_tables}")

    except Exception as e:
        db.rollback()
        print(f"ERROR durante el saneamiento: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    sanitize_rbac_permissions()
