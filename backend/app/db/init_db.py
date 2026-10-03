import app.modules.auth.models
import app.modules.admin_catalog.models
import app.modules.telemetry_audit.models
import app.modules.chat_engine.models
from sqlalchemy.orm import Session
from app.core.database import Base, engine, ensure_schema_migrations
from app.core.security import get_password_hash
from app.modules.auth.models import User, Role, Domain
from app.modules.admin_catalog.models import (
    CorporateConnection, DatabaseType, SemanticCatalog, RoleTablePermission,
    RoleColumnPermission, ColumnPermissionType
)

def init_db(db: Session):
    """
    Creates all database tables in PostgreSQL/SQLite and seeds initial default roles and admin.
    """
    Base.metadata.create_all(bind=engine)
    ensure_schema_migrations(engine)

    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        if "users" in table_names:
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            with engine.begin() as conn:
                if "failed_login_attempts" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL"))
                if "locked_until" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL"))
                if "must_change_password" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL"))

        if "corporate_connections" in table_names:
            conn_cols = {c["name"] for c in inspector.get_columns("corporate_connections")}
            with engine.begin() as conn:
                if "is_uploaded" not in conn_cols:
                    conn.execute(text("ALTER TABLE corporate_connections ADD COLUMN is_uploaded BOOLEAN DEFAULT 0 NOT NULL"))
                if "null_policy" not in conn_cols:
                    conn.execute(text("ALTER TABLE corporate_connections ADD COLUMN null_policy VARCHAR(50) DEFAULT 'open'"))

        if "audit_logs" in table_names:
            audit_cols = {c["name"] for c in inspector.get_columns("audit_logs")}
            with engine.begin() as conn:
                if "result_snapshot" not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN result_snapshot TEXT NULL"))

        if "query_learning_memories" in table_names:
            mem_cols = {c["name"] for c in inspector.get_columns("query_learning_memories")}
            with engine.begin() as conn:
                if "is_golden" not in mem_cols:
                    conn.execute(text("ALTER TABLE query_learning_memories ADD COLUMN is_golden BOOLEAN DEFAULT FALSE NOT NULL"))

        # Procedencia del permiso de tabla. Mismo mecanismo que `is_shared`: se
        # agrega la columna con el default que falla cerrado. Las filas existentes
        # quedan en False (o sea "nadie lo concedio a proposito"), que es
        # justamente lo que la migracion de default-deny de mas abajo revoca.
        if "role_table_permissions" in table_names:
            perm_cols = {c["name"] for c in inspector.get_columns("role_table_permissions")}
            with engine.begin() as conn:
                if "granted_by_admin" not in perm_cols:
                    conn.execute(text("ALTER TABLE role_table_permissions ADD COLUMN granted_by_admin BOOLEAN DEFAULT FALSE NOT NULL"))
                    # No se marca nada como concedido: el default FALSE deja a todas
                    # las filas existentes sin procedencia demostrable, que es
                    # exactamente lo que la migracion de default-deny de mas abajo
                    # revoca en los datasets subidos. La matriz de la demo no pasa
                    # por aca: vive en las conexiones de plataforma (is_uploaded
                    # == False), que la migracion no toca, y el seeder declarativo
                    # la (re)marca como concedida fila por fila.
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
        elif u_info["role"] and existing_user.role_id is None:
            # Solo backfill de rol. Una cuenta existente NO se toca mas: revertir
            # su contrasena en cada arranque deshacia los cambios del admin,
            # reactivaba cuentas desactivadas y ponia el lockout en cero, con lo
            # que un reinicio de Docker hacia la fuerza bruta infinitamente
            # reutilizable.
            existing_user.role_id = u_info["role"].id
    db.commit()

    import os
    from app.core.config import settings
    from app.core.security import encrypt_credential

    if engine.dialect.name != "postgresql":
        db_path = settings.SQLITE_DB_PATH
        if not os.path.exists(db_path):
            try:
                import sys
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                from setup_demo_db import setup_demo_sqlite
                setup_demo_sqlite()
            except Exception:
                pass

    std_conn = db.query(CorporateConnection).filter(CorporateConnection.is_uploaded == False).first()
    if not std_conn:
        if engine.dialect.name == "postgresql":
            std_conn = CorporateConnection(
                name="Base de Datos Corporativa (Demo)",
                db_type=DatabaseType.POSTGRESQL,
                host=settings.POSTGRES_SERVER,
                port=settings.POSTGRES_PORT,
                database_name="democratizacion_empresa",
                username=settings.POSTGRES_USER,
                encrypted_password=encrypt_credential(settings.POSTGRES_PASSWORD),
                is_active=True,
                is_uploaded=False
            )
        else:
            db_path = settings.SQLITE_DB_PATH
            db_name = os.path.basename(db_path)
            std_conn = CorporateConnection(
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
        db.add(std_conn)
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

    primary_conn = None
    standard_connections = db.query(CorporateConnection).filter(CorporateConnection.is_uploaded == False).all()
    for s_conn in standard_connections:
        s_schema = "public" if (s_conn.db_type == DatabaseType.POSTGRESQL or str(s_conn.db_type).lower() == "postgresql") else "main"
        for r_obj, tbl_list in role_table_mappings:
            if r_obj:
                for tbl in tbl_list:
                    existing_perm = db.query(RoleTablePermission).filter(
                        RoleTablePermission.role_id == r_obj.id,
                        RoleTablePermission.connection_id == s_conn.id,
                        RoleTablePermission.table_name == tbl
                    ).first()
                    if existing_perm:
                        existing_perm.granted_by_admin = True
                    else:
                        # Esta matriz SI es una decision explicita de la demo (los
                        # 12 roles y las tablas SAP declaradas arriba), asi que las
                        # filas se marcan como concedidas por un admin: es lo que
                        # las distingue del auto-grant y las protege de la
                        # migracion de default-deny.
                        db.add(RoleTablePermission(
                            role_id=r_obj.id,
                            connection_id=s_conn.id,
                            schema_name=s_schema,
                            table_name=tbl,
                            is_allowed=True,
                            granted_by_admin=True
                        ))

    # Ensure financial roles strictly do NOT have access to tech/server infrastructure tables
    for r_obj in all_financiero_roles:
        db.query(RoleTablePermission).filter(
            RoleTablePermission.role_id == r_obj.id,
            RoleTablePermission.table_name.in_(["dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos"])
        ).delete(synchronize_session=False)

    # Ensure TI roles strictly do NOT have access to financial/business tables
    for r_obj in all_ti_roles:
        db.query(RoleTablePermission).filter(
            RoleTablePermission.role_id == r_obj.id,
            RoleTablePermission.table_name.in_([
                "fact_ventas", "fact_ingresos_costos", "dim_clientes", 
                "dim_productos", "dim_categorias", "vbak_cabpedidoventa",
                "vbap_pospedidoventa", "ekko_cabpedidocompra", "ekpo_pospedidocompra", "kna1_clientes"
            ])
        ).delete(synchronize_session=False)

    # Seed column-level security permissions (CLS) for standard connections
    for s_conn in standard_connections:
        s_schema = "public" if (s_conn.db_type == DatabaseType.POSTGRESQL or str(s_conn.db_type).lower() == "postgresql") else "main"
        non_admin_roles = db.query(Role).filter(~Role.name.in_(["Administrador de Plataforma", "Administrador", "Director Ejecutivo (C-Level)"])).all()
        for r_obj in non_admin_roles:
            # 1. Mask customer national ID / RUT
            existing_rut = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == r_obj.id,
                RoleColumnPermission.connection_id == s_conn.id,
                RoleColumnPermission.table_name == "dim_clientes",
                RoleColumnPermission.column_name == "rut_dni_cliente"
            ).first()
            if not existing_rut:
                db.add(RoleColumnPermission(
                    role_id=r_obj.id,
                    connection_id=s_conn.id,
                    schema_name=s_schema,
                    table_name="dim_clientes",
                    column_name="rut_dni_cliente",
                    permission_type=ColumnPermissionType.MASKED
                ))

            # 2. Block credit card token
            existing_cc = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == r_obj.id,
                RoleColumnPermission.connection_id == s_conn.id,
                RoleColumnPermission.table_name == "dim_clientes",
                RoleColumnPermission.column_name == "tarjeta_credito_token"
            ).first()
            if not existing_cc:
                db.add(RoleColumnPermission(
                    role_id=r_obj.id,
                    connection_id=s_conn.id,
                    schema_name=s_schema,
                    table_name="dim_clientes",
                    column_name="tarjeta_credito_token",
                    permission_type=ColumnPermissionType.BLOCKED
                ))

            # 3. Block salary and compensation for non-HR roles
            is_hr_role = "talento" in r_obj.name.lower() or "rrhh" in r_obj.name.lower()
            if not is_hr_role:
                for col in ["sueldo_mensual", "salario"]:
                    existing_sal = db.query(RoleColumnPermission).filter(
                        RoleColumnPermission.role_id == r_obj.id,
                        RoleColumnPermission.connection_id == s_conn.id,
                        RoleColumnPermission.table_name == "dim_empleados",
                        RoleColumnPermission.column_name == col
                    ).first()
                    if not existing_sal:
                        db.add(RoleColumnPermission(
                            role_id=r_obj.id,
                            connection_id=s_conn.id,
                            schema_name=s_schema,
                            table_name="dim_empleados",
                            column_name=col,
                            permission_type=ColumnPermissionType.BLOCKED
                        ))

    # MIGRACION default-deny: los datasets ya cargados.
    #
    # Antes, el bloque que vivia aqui (y `upload_database_file`) creaba un
    # RoleTablePermission(is_allowed=True) por cada (rol, tabla) de cada conexion
    # subida, saltandose solo unas tablas de la demo SAP por substring sobre el
    # nombre del rol. En cualquier dataset real la exclusion no excluye nada y
    # queda over-grant para casi todos los roles.
    #
    # Que decide esta migracion: revocar, nunca conceder. Las filas que no son
    # decision de un admin (granted_by_admin = False, que es el default y por eso
    # cubre tanto las del auto-grant viejo como cualquier fila sin procedencia
    # demostrable) se borran de las conexiones SUBIDAS. Las conexiones de
    # plataforma (is_uploaded == False) NO se tocan: ahi esta la matriz de la demo
    # declarada arriba, y borrarla dejaria el producto sin acceso.
    #
    # Consecuencia asumida: un dataset preexistente queda sin acceso hasta que el
    # admin re-asigne con PUT /api/v1/permissions. Es el trade correcto:
    # revocar de mas es recuperable en un click; dejar el over-grant no lo es.
    #
    # Idempotente: corre en cada arranque, y la segunda vez no hay nada que borrar.
    uploaded_ids = [
        c[0] for c in db.query(CorporateConnection.id)
        .filter(CorporateConnection.is_uploaded == True).all()
    ]
    if uploaded_ids:
        revoked = db.query(RoleTablePermission).filter(
            RoleTablePermission.connection_id.in_(uploaded_ids),
            RoleTablePermission.granted_by_admin == False,
        ).delete(synchronize_session=False)
        db.commit()
        if revoked:
            print(f"[migracion default-deny] {revoked} permisos de tabla no decisions por un admin fueron revocados de {len(uploaded_ids)} dataset(s) subido(s). Re-asignalos desde el panel de permisos.")

    # MIGRACION conector unico: `is_active` se leia como un singleton (los
    # lectores hacen `ORDER BY id DESC LIMIT 1`) pero las escrituras no lo
    # trataban como tal, asi que se acumularon varias conexiones activas. Con la
    # demo de plataforma y un dataset subido los dos marcados, el motor respondia
    # contra el dataset (id mas alto), que por default-deny no tiene permisos:
    # todos los no-admin se quedaban sin datos en todo el producto.
    #
    # Gana la de id mas alto, que es exactamente lo que el motor ya elegia: la
    # migracion quita el estado incoherente sin cambiar cual es la fuente que
    # estaba en uso. Idempotente: la segunda vez no hay nada que apagar.
    active_ids = [
        c[0] for c in db.query(CorporateConnection.id)
        .filter(CorporateConnection.is_active == True)
        .order_by(CorporateConnection.id.desc()).all()
    ]
    if len(active_ids) > 1:
        db.query(CorporateConnection).filter(
            CorporateConnection.id.in_(active_ids[1:])
        ).update({CorporateConnection.is_active: False}, synchronize_session=False)
        db.commit()
        print(
            f"[migracion conector unico] {len(active_ids) - 1} conexion(es) "
            f"activa(s) extra(s) apagadas. Queda activa la {active_ids[0]}."
        )

    db.commit()

    try:
        from app.modules.catalog.services.catalog_service import CatalogDomainService
        first_conn = db.query(CorporateConnection).first()
        if first_conn:
            CatalogDomainService.seed_catalog_heuristics_for_connection(db, first_conn.id, first_conn.host)
    except Exception:
        pass
