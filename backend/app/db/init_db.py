from sqlalchemy.orm import Session
from app.core.database import Base, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import Role, Domain

def init_db(db: Session):
    """
    Creates all database tables in PostgreSQL and seeds initial default roles and admin.
    """
    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)

    # Safe schema evolution check for existing deployments
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
    except Exception:
        pass

    # Seed Default Domains
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

    # Seed Corporate Enterprise Roles (with backwards compatibility aliases)
    default_roles = [
        {"name": "Administrador de Plataforma", "description": "Acceso total a gobernanza RBAC, gestión de usuarios, conexiones BD y auditoría"},
        {"name": "Director Ejecutivo (C-Level)", "description": "Visión macro estratégica, rentabilidad global, indicadores clave de negocio y alertas de riesgo"},
        {"name": "Analista Financiero & Comercial", "description": "Evaluación de ventas, facturación, márgenes, rentabilidad por producto/cliente y proyección de ingresos"},
        {"name": "Gerente de Talento & Operaciones", "description": "Gestión de clima laboral, encuestas organizacionales, retención y métricas operacionales"},
        {"name": "Analista de Datos & BI", "description": "Exploración multidimensional de datos, cruce de métricas y correlaciones estadísticas"},
        {"name": "Ingeniero de Infraestructura & TI", "description": "Monitoreo de salud de conectores, consumo de servidores, rendimiento de consultas e incidentes técnicos"},
        {"name": "Oficial de Cumplimiento & Seguridad", "description": "Vigilancia de trazabilidad, cumplimiento de normativas de datos y auditoría de accesos"},
        {"name": "Usuario Consultor", "description": "Perfil inicial por defecto con acceso de solo lectura restringida"},
        # Legacy Aliases
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

    # Retrieve role references
    admin_role = db.query(Role).filter(Role.name.in_(["Administrador de Plataforma", "Administrador"])).first()
    c_level_role = db.query(Role).filter(Role.name == "Director Ejecutivo (C-Level)").first()
    financiero_role = db.query(Role).filter(Role.name.in_(["Analista Financiero & Comercial", "Economista"])).first()
    talento_role = db.query(Role).filter(Role.name == "Gerente de Talento & Operaciones").first()
    bi_role = db.query(Role).filter(Role.name == "Analista de Datos & BI").first()
    ti_role = db.query(Role).filter(Role.name.in_(["Ingeniero de Infraestructura & TI", "TI"])).first()
    dpo_role = db.query(Role).filter(Role.name == "Oficial de Cumplimiento & Seguridad").first()

    # Seed Default Demo Users with official credentials
    demo_users = [
        {"username": "admin", "email": "admin@empresa.com", "pwd": "admin123", "is_admin": True, "role": admin_role},
        {"username": "economista", "email": "economista@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
        {"username": "felipe_economista", "email": "felipe@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
        {"username": "ti", "email": "ti@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
        {"username": "juan_ti", "email": "juan@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
    ]

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
    db.commit()

    # Seed RoleTablePermission for Corporate Roles
    from app.models.permission import RoleTablePermission
    from app.models.catalog import SemanticCatalog
    from app.models.connection import CorporateConnection, DatabaseType
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

    role_table_mappings = [
        (c_level_role, all_combined_tables),
        (financiero_role, all_business_tables),
        (talento_role, ["dim_empleados", "dim_clientes", "dim_categorias", "Answer", "Question", "Survey", "answer", "question", "survey"]),
        (bi_role, all_combined_tables),
        (ti_role, all_tech_tables),
        (dpo_role, ["dim_empleados", "dim_servidores", "fact_incidentes_ti", "Answer", "Question", "Survey", "answer", "question", "survey"]),
    ]

    # Also map legacy roles if present separately
    legacy_econ = db.query(Role).filter(Role.name == "Economista").first()
    if legacy_econ:
        role_table_mappings.append((legacy_econ, all_business_tables))
    legacy_ti = db.query(Role).filter(Role.name == "TI").first()
    if legacy_ti:
        role_table_mappings.append((legacy_ti, all_tech_tables))

    for r_obj, tbl_list in role_table_mappings:
        if r_obj:
            for tbl in tbl_list:
                existing_perm = db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == r_obj.id,
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

    db.commit()

    # Seed SemanticCatalog entries for connection 1 if not present
    all_demo_tables = [
        ("dim_categorias", "nombre_categoria", "Nombre de la categoría de productos o servicios"),
        ("dim_productos", "nombre_producto", "Nombre comercial del producto o licencia"),
        ("dim_productos", "precio_unitario", "Precio unitario de venta en USD"),
        ("dim_clientes", "nombre_empresa", "Razón social del cliente corporativo"),
        ("fact_ventas", "monto_total", "Monto total transaccionado en la venta"),
        ("fact_ventas", "fecha_venta", "Fecha de realización de la venta"),
        ("fact_ingresos_costos", "ingreso_bruto", "Ingreso bruto mensual consolidado"),
        ("fact_ingresos_costos", "utilidad_neta", "Utilidad neta mensual consolidada"),
        ("dim_empleados", "salario_bruto", "Salario bruto mensual del colaborador"),
        ("dim_empleados", "evaluacion_desempeno", "Puntaje de evaluación de desempeño"),
        ("dim_servidores", "nombre_host", "Nombre del servidor o nodo de infraestructura"),
        ("dim_servidores", "datacenter", "Ubicación del datacenter"),
        ("fact_incidentes_ti", "tipo_falla", "Tipo o clasificación de la falla de TI"),
        ("fact_incidentes_ti", "horas_resolucion", "Horas tomadas para resolver el incidente SLA"),
        ("fact_consumo_recursos", "porcentaje_cpu", "Porcentaje de uso de CPU del servidor"),
        ("fact_consumo_recursos", "uso_ram_gb", "Memoria RAM utilizada en Gigabytes"),
        
        # Mental Health Survey Tables
        ("Answer", "AnswerText", "Texto de la respuesta dada por el encuestado (ej. Yes, No, Male, Female, United States)"),
        ("Answer", "SurveyID", "Año de la encuesta OSMI (2014, 2016, 2017, 2018, 2019)"),
        ("Answer", "UserID", "ID de usuario anónimo del encuestado"),
        ("Answer", "QuestionID", "ID numérico de la pregunta de la encuesta"),
        ("Question", "questiontext", "Texto descriptivo de la pregunta de la encuesta de salud mental"),
        ("Question", "questionid", "ID numérico único de la pregunta"),
        ("Survey", "SurveyID", "Año de realización de la encuesta (2014-2019)"),
        ("Survey", "Description", "Descripción de la edición de la encuesta")
    ]


    for tbl, col, desc in all_demo_tables:
        existing_cat = db.query(SemanticCatalog).filter(
            SemanticCatalog.connection_id == 1,
            SemanticCatalog.table_name == tbl,
            SemanticCatalog.column_name == col
        ).first()
        if not existing_cat:
            db.add(SemanticCatalog(
                connection_id=1,
                table_name=tbl,
                column_name=col,
                description=desc
            ))

    db.commit()

    # Auto-register and preserve any existing uploaded databases in data_sources/
    try:
        import sqlite3
        ds_dir = settings.DATA_SOURCES_DIR
        if os.path.exists(ds_dir):
            for fname in os.listdir(ds_dir):
                if fname.startswith("raw_") or not (fname.endswith(".sqlite") or fname.endswith(".db")):
                    continue
                file_full_path = os.path.abspath(os.path.join(ds_dir, fname))
                existing_uploaded_conn = db.query(CorporateConnection).filter(
                    CorporateConnection.host == file_full_path
                ).first()
                if not existing_uploaded_conn:
                    sq_conn = sqlite3.connect(file_full_path)
                    cur = sq_conn.cursor()
                    tables = [
                        r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                        if not r[0].startswith("sqlite_")
                    ]
                    sq_conn.close()
                    if tables:
                        # Clean display name removing timestamp prefix
                        import re
                        clean_disp_name = re.sub(r'^\d+_', '', fname)
                        clean_disp_name = clean_disp_name.replace(".sqlite", "").replace(".db", "").replace("_", " ").upper()
                        new_c = CorporateConnection(
                            name=clean_disp_name,
                            db_type=DatabaseType.SQLITE,
                            host=file_full_path,
                            port=0,
                            database_name=fname,
                            username="admin",
                            encrypted_password="",
                            is_active=True,
                            is_uploaded=True
                        )
                        db.add(new_c)
                        db.commit()
                        db.refresh(new_c)

                        for role in db.query(Role).all():
                            is_admin = (
                                role.name in [ROLE_ADMINISTRADOR, "Administrador", "Super Administrador", "Admin"]
                                or "admin" in role.name.lower()
                            )
                            if not is_admin:
                                continue
                            for t in tables:
                                if not db.query(RoleTablePermission).filter(
                                    RoleTablePermission.role_id == role.id,
                                    RoleTablePermission.connection_id == new_c.id,
                                    RoleTablePermission.table_name == t
                                ).first():
                                    db.add(RoleTablePermission(
                                        role_id=role.id,
                                        connection_id=new_c.id,
                                        schema_name="main",
                                        table_name=t,
                                        is_allowed=True
                                    ))
                        db.commit()
    except Exception:
        pass
