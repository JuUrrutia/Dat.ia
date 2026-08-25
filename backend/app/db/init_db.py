import app.models  # Ensures all SQLAlchemy models are registered
from sqlalchemy.orm import Session
from app.core.database import Base, engine
from app.core.security import get_password_hash
from app.modules.auth.models import User, Role, Domain
from app.modules.admin_catalog.models import (
    CorporateConnection, DatabaseType, SemanticCatalog, RoleTablePermission
)
from app.core.constants import ROLE_ADMINISTRADOR

def init_db(db: Session):
    """
    Creates all database tables in PostgreSQL/SQLite and seeds initial default roles and admin.
    """
    Base.metadata.create_all(bind=engine)

    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            with engine.begin() as conn:
                if "failed_login_attempts" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL"))
                if "locked_until" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL"))
                if "must_change_password" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL"))

        if "corporate_connections" in inspector.get_table_names():
            conn_cols = {c["name"] for c in inspector.get_columns("corporate_connections")}
            with engine.begin() as conn:
                if "is_uploaded" not in conn_cols:
                    conn.execute(text("ALTER TABLE corporate_connections ADD COLUMN is_uploaded BOOLEAN DEFAULT 0 NOT NULL"))

        if "audit_logs" in inspector.get_table_names():
            audit_cols = {c["name"] for c in inspector.get_columns("audit_logs")}
            with engine.begin() as conn:
                if "result_snapshot" not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN result_snapshot TEXT NULL"))
    except Exception:
        pass

    default_domains = [
        {"name": "Economía & Finanzas", "description": "Ingresos, costos, presupuestos, facturación y márgenes de negocio"},
        {"name": "Tecnología & TI", "description": "Infraestructura, servidores, consumo de recursos e incidentes técnicos"},
        {"name": "Operaciones & Comercial", "description": "Ventas, clientes, almacenes y catálogo de productos"},
        {"name": "Talento & Personas", "description": "Desempeño, clima laboral, encuestas y bienestar organizacional"},
        {"name": "Seguridad & Gobernanza", "description": "Cumplimiento normativo, auditoría, accesos y trazabilidad de datos"},
    ]

    for dom_data in default_domains:
        existing_dom = db.query(Domain).filter(Domain.name == dom_data["name"]).first()
        if not existing_dom:
            db.add(Domain(name=dom_data["name"], description=dom_data["description"]))
    db.commit()

    default_roles = [
        {"name": "Administrador de Plataforma", "description": "Acceso total a gobernanza RBAC, gestión de usuarios, conexiones BD y auditoría"},
        {"name": "Director Ejecutivo (C-Level)", "description": "Visión macro estratégica, rentabilidad global, indicadores clave de negocio y alertas de riesgo"},
        {"name": "Analista Financiero & Comercial", "description": "Evaluación de ventas, facturación, márgenes, rentabilidad por producto/cliente y proyección de ingresos"},
        {"name": "Gerente de Talento & Operaciones", "description": "Gestión de clima laboral, encuestas organizacionales, retención y métricas operacionales"},
        {"name": "Analista de Datos & BI", "description": "Exploración multidimensional de datos, cruce de métricas y correlaciones estadísticas"},
        {"name": "Ingeniero de Infraestructura & TI", "description": "Monitoreo de salud de conectores, consumo de servidores, rendimiento de consultas e incidentes técnicos"},
        {"name": "Oficial de Cumplimiento & Seguridad", "description": "Vigilancia de trazabilidad, cumplimiento de normativas de datos y auditoría de accesos"},
        {"name": "Usuario Consultor", "description": "Perfil inicial por defecto con acceso de solo lectura restringida"},
        {"name": "Administrador", "description": "Alias de Administrador de Plataforma"},
        {"name": "Economista", "description": "Alias de Analista Financiero & Comercial"},
        {"name": "TI", "description": "Alias de Ingeniero de Infraestructura & TI"},
        {"name": "Usuario", "description": "Alias de Usuario Consultor"},
    ]

    for role_data in default_roles:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            db.add(Role(name=role_data["name"], description=role_data["description"]))
    db.commit()

    admin_role = db.query(Role).filter(Role.name.in_(["Administrador de Plataforma", "Administrador"])).first()
    financiero_role = db.query(Role).filter(Role.name.in_(["Analista Financiero & Comercial", "Economista"])).first()
    ti_role = db.query(Role).filter(Role.name.in_(["Ingeniero de Infraestructura & TI", "TI"])).first()

    demo_users = [
        {"username": "admin", "email": "admin@empresa.com", "pwd": "admin123", "is_admin": True, "role": admin_role},
        {"username": "economista", "email": "economista@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
        {"username": "felipe_economista", "email": "felipe@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
        {"username": "ti", "email": "ti@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
        {"username": "juan_ti", "email": "juan@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
    ]

    from app.core.security import verify_password

    for u_info in demo_users:
        existing_user = db.query(User).filter(User.username == u_info["username"]).first()
        if not existing_user:
            hashed_pwd = get_password_hash(u_info["pwd"])
            new_user = User(
                username=u_info["username"],
                email=u_info["email"],
                hashed_password=hashed_pwd,
                is_admin=u_info["is_admin"],
                is_active=True,
                role_id=u_info["role"].id if u_info["role"] else None
            )
            db.add(new_user)
        else:
            # Ensure demo accounts always have functional passwords and valid roles
            if not verify_password(u_info["pwd"], existing_user.hashed_password):
                existing_user.hashed_password = get_password_hash(u_info["pwd"])
            if u_info["role"] and existing_user.role_id is None:
                existing_user.role_id = u_info["role"].id
            existing_user.is_active = True
            existing_user.failed_login_attempts = 0
            existing_user.locked_until = None
    db.commit()

    import os
    from app.core.config import settings

    existing_conn = db.query(CorporateConnection).first()
    if not existing_conn:
        db_path = settings.SQLITE_DB_PATH
        db_name = os.path.basename(db_path)
        default_conn = CorporateConnection(
            name="BD Corporativa Local",
            db_type=DatabaseType.SQLITE,
            host=db_path,
            port=0,
            database_name=db_name,
            username="admin",
            encrypted_password="",
            is_active=True,
            is_uploaded=False
        )
        db.add(default_conn)
        db.commit()

    all_business_tables = [
        "dim_categorias", "dim_productos", "dim_clientes",
        "fact_ventas", "fact_ingresos_costos", "dim_empleados",
        "Answer", "Question", "Survey", "answer", "question", "survey"
    ]
    all_tech_tables = [
        "dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos", "dim_empleados",
        "Answer", "Question", "Survey", "answer", "question", "survey"
    ]
    all_combined_tables = list(set(all_business_tables + all_tech_tables))

    all_admin_roles = db.query(Role).filter(Role.name.in_(["Administrador de Plataforma", "Administrador"])).all()
    all_financiero_roles = db.query(Role).filter(Role.name.in_(["Analista Financiero & Comercial", "Economista"])).all()
    all_ti_roles = db.query(Role).filter(Role.name.in_(["Ingeniero de Infraestructura & TI", "TI"])).all()

    role_table_mappings = []
    for r in all_admin_roles:
        role_table_mappings.append((r, all_combined_tables))
    for r in all_financiero_roles:
        role_table_mappings.append((r, all_business_tables))
    for r in all_ti_roles:
        role_table_mappings.append((r, all_tech_tables))

    for r_obj, tbl_list in role_table_mappings:
        if r_obj:
            for tbl in tbl_list:
                existing_perm = db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == r_obj.id,
                    RoleTablePermission.connection_id == 1,
                    RoleTablePermission.table_name == tbl
                ).first()
                if not existing_perm:
                    db.add(RoleTablePermission(
                        role_id=r_obj.id,
                        connection_id=1,
                        schema_name="main",
                        table_name=tbl,
                        is_allowed=True
                    ))

    # Also seed permissions for all other registered connections (e.g. uploaded datasets)
    from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
    other_connections = db.query(CorporateConnection).filter(CorporateConnection.id != 1).all()
    operational_roles = db.query(Role).filter(~Role.name.in_(["Usuario", "Usuario Consultor"])).all()

    for o_conn in other_connections:
        db_path = o_conn.host if (o_conn.host and os.path.exists(o_conn.host)) else (
            o_conn.database_name if (o_conn.database_name and os.path.exists(o_conn.database_name)) else None
        )
        phys_tables = DynamicSchemaPruningService.get_physical_db_tables(db_path) if db_path else set()
        if not phys_tables:
            cat_entries = db.query(SemanticCatalog).filter(SemanticCatalog.connection_id == o_conn.id).all()
            phys_tables = {e.table_name for e in cat_entries if e.table_name}
        for r_obj in operational_roles:
            for tbl in phys_tables:
                existing_perm = db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == r_obj.id,
                    RoleTablePermission.connection_id == o_conn.id,
                    RoleTablePermission.table_name.ilike(tbl)
                ).first()
                if not existing_perm:
                    db.add(RoleTablePermission(
                        role_id=r_obj.id,
                        connection_id=o_conn.id,
                        schema_name="main",
                        table_name=tbl,
                        is_allowed=True
                    ))

    db.commit()

    try:
        from app.modules.catalog.services.catalog_service import CatalogDomainService
        first_conn = db.query(CorporateConnection).first()
        if first_conn:
            CatalogDomainService.seed_catalog_heuristics_for_connection(db, first_conn.id, first_conn.host)
    except Exception:
        pass
