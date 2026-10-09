import app.modules.auth.models
import app.modules.admin_catalog.models
import app.modules.telemetry_audit.models
import app.modules.chat_engine.models
from sqlalchemy.orm import Session
from app.core.database import Base, engine, ensure_schema_migrations
from app.core.constants import (
    ROLE_ADMINISTRADOR, ROLE_DIRECTOR_EJECUTIVO, ROLE_ANALISTA_FINANCIERO,
    ROLE_GERENTE_TALENTO, ROLE_ANALISTA_BI, ROLE_INGENIERO_TI,
    ROLE_OFICIAL_SEGURIDAD, ROLE_USUARIO,
)
from app.core.security import get_password_hash
from app.modules.auth.models import User, Role, Domain
from app.modules.admin_catalog.models import (
    CorporateConnection, DatabaseType, SemanticCatalog, RoleTablePermission,
    RoleColumnPermission, ColumnPermissionType
)

# Que tan restrictivo es cada veredicto de columna. Cuando el alias y su
# corporativo discrepan sobre la misma columna gana el mas restrictivo: es el
# criterio fail-closed que ya usa el resto de la gobernanza, y la unica
# alternativa seria ampliar el acceso de un rol sin que nadie lo decidiera.
_COLUMN_SEVERITY = {
    ColumnPermissionType.ALLOWED: 0,
    ColumnPermissionType.MASKED: 1,
    ColumnPermissionType.BLOCKED: 2,
}

# Roles alias que la matriz corporativa de `constants.py` veio a reemplazar.
# Literal y no constante: a esta migracion le toca justamente porque van a
# dejar de existir. El destino si se lee de la constante, que es la unica
# fuente de verdad.
_ALIAS_ROLES = {
    "Administrador": ROLE_ADMINISTRADOR,
    "Economista": ROLE_ANALISTA_FINANCIERO,
    "TI": ROLE_INGENIERO_TI,
    "Usuario": ROLE_USUARIO,
}


def _role(db: Session, name: str):
    """Resuelve un rol por nombre. Un solo nombre: la migracion de alias ya no
    deja filas alternativas entre las que elegir."""
    return db.query(Role).filter(Role.name == name).first()


def _migrate_role_aliases(db: Session) -> None:
    """Reasigna los roles alias a su corporativo y borra la fila del alias.

    Que decide: reasignar, nunca borrar a ciegas. Los `users`, los permisos de
    tabla y columna y los links de dominio que apuntan al alias se mueven al
    corporativo recien ahi se borra la fila. Al reves, el `DELETE` deja al
    usuario con `role_id = NULL` (`User.role_id` es `ondelete="SET NULL"`) y
    pierde la matriz de permisos sin avisar.

    Sin duplicar filas: los alias no eran solo una segunda etiqueta, el bloque de
    permisos de mas abajo sembraba LA MISMA matriz para el corporativo y su
    alias. Reasignar a ciegas dejaria dos filas para el mismo par
    (rol, conexion, tabla) y el panel de gobernanza contaria permisos de mas.

    Todo por UPDATE/DELETE masivo, nunca por atributo de objeto. La ORM anula el
    FK de los hijos cuando borra al padre (`Role.users` no declara cascade, asi que
    la fila terminaba con `role_id = NULL` igual, por mucho que se le hubiera
    asignado el corporativo antes): el `db.delete(alias)` de la version anterior
    reportaba "2 referencias reasignadas" y dejaba al usuario sin rol. Las
    operaciones masivas no pasan por esa cascada, y el orden importa: primero se
    mueven los permisos (ON DELETE CASCADE se los llevaria), despues la fila.

    Idempotente: la segunda pasada no encuentra alias y no hace nada.
    """
    from app.modules.admin_catalog.models import RoleDomainLink

    for alias_name, target_name in _ALIAS_ROLES.items():
        alias_id = db.query(Role.id).filter(Role.name == alias_name).scalar()
        if alias_id is None:
            continue

        target_id = db.query(Role.id).filter(Role.name == target_name).scalar()
        if target_id is None:
            # Sin destino no hay adonde moverlo. Se deja el alias intacto y se
            # avisa: perder una matriz de permisos en silencio es peor que
            # quedar con un rol de mas.
            print(
                f"[migracion roles alias] '{alias_name}' no encuentra su equivalente "
                f"corporativo '{target_name}'. Se conserva sin tocar: reasignalo desde "
                f"el panel de administracion."
            )
            continue

        movidos = 0

        # 1. Permisos de tabla. Si el corporativo ya tiene la fila, el alias no
        #    aporta nada y la suya se descarta. Ante una discrepancia gana el
        #    corporativo, que es el veredicto de una decision de admin y el mas
        #    reciente: migrar puede PRESERVAR o RESTRINGIR, nunca conceder. La
        #    fila del alias era un residuo del seed viejo, no una autorizacion.
        # Se leen como tuplas, no como objetos mapeados: si la fila entra en la
        # sesion con identidad ORM y despues la muevo con un UPDATE masivo, al
        # borrar el rol la cascada `delete-orphan` de `Role` intenta borrarla otra
        # vez (SQLAlchemy avisa "expected to delete N rows; 0 were matched") y el
        # estado en memoria deja de coincidir con la base. Sin identidad no hay
        # cascada que opinionar.
        for pid, conn_id, table in db.query(
            RoleTablePermission.id,
            RoleTablePermission.connection_id,
            RoleTablePermission.table_name,
        ).filter(RoleTablePermission.role_id == alias_id).all():
            dup = db.query(RoleTablePermission.id).filter(
                RoleTablePermission.role_id == target_id,
                RoleTablePermission.connection_id == conn_id,
                RoleTablePermission.table_name == table,
            ).first()
            if dup:
                db.query(RoleTablePermission).filter(
                    RoleTablePermission.id == pid
                ).delete(synchronize_session=False)
            else:
                db.query(RoleTablePermission).filter(
                    RoleTablePermission.id == pid
                ).update({RoleTablePermission.role_id: target_id},
                         synchronize_session=False)
                movidos += 1

        # 2. Permisos de columna, mismo criterio con la severidad.
        for pid, conn_id, table, column, ptype in db.query(
            RoleColumnPermission.id,
            RoleColumnPermission.connection_id,
            RoleColumnPermission.table_name,
            RoleColumnPermission.column_name,
            RoleColumnPermission.permission_type,
        ).filter(RoleColumnPermission.role_id == alias_id).all():
            dup_id, dup_type = db.query(
                RoleColumnPermission.id, RoleColumnPermission.permission_type
            ).filter(
                RoleColumnPermission.role_id == target_id,
                RoleColumnPermission.connection_id == conn_id,
                RoleColumnPermission.table_name == table,
                RoleColumnPermission.column_name == column,
            ).first() or (None, None)
            if dup_id is not None:
                if _COLUMN_SEVERITY.get(ptype, 0) > _COLUMN_SEVERITY.get(dup_type, 0):
                    db.query(RoleColumnPermission).filter(
                        RoleColumnPermission.id == dup_id
                    ).update({RoleColumnPermission.permission_type: ptype},
                             synchronize_session=False)
                db.query(RoleColumnPermission).filter(
                    RoleColumnPermission.id == pid
                ).delete(synchronize_session=False)
            else:
                db.query(RoleColumnPermission).filter(
                    RoleColumnPermission.id == pid
                ).update({RoleColumnPermission.role_id: target_id},
                         synchronize_session=False)
                movidos += 1

        # 3. Links de dominio. Nadie los lee todavia (el filtro de autorizacion
        #    va por `role_id` sobre permisos de tabla), pero el FK es ON DELETE
        #    CASCADE: lo que no se mueva aqui desaparece con la fila.
        for link_id, domain_id in db.query(
            RoleDomainLink.id, RoleDomainLink.domain_id
        ).filter(RoleDomainLink.role_id == alias_id).all():
            dup = db.query(RoleDomainLink.id).filter(
                RoleDomainLink.role_id == target_id,
                RoleDomainLink.domain_id == domain_id,
            ).first()
            if dup:
                db.query(RoleDomainLink).filter(
                    RoleDomainLink.id == link_id
                ).delete(synchronize_session=False)
            else:
                db.query(RoleDomainLink).filter(
                    RoleDomainLink.id == link_id
                ).update({RoleDomainLink.role_id: target_id},
                         synchronize_session=False)
                movidos += 1

        # 4. Usuarios, ULTIMO. `User.role_id` es ON DELETE SET NULL, asi que hasta
        #    que la fila del alias esta borrada este UPDATE es el que decide si la
        #    cuenta conserva su rol.
        movidos += db.query(User).filter(
            User.role_id == alias_id
        ).update({User.role_id: target_id}, synchronize_session=False)

        # 5. Ahora si, la fila del alias. Los permisos ya no la apuntan.
        db.query(Role).filter(Role.id == alias_id).delete(
            synchronize_session=False
        )
        db.commit()
        print(
            f"[migracion roles alias] '{alias_name}' -> '{target_name}': "
            f"{movidos} referencia(s) reasignadas, fila del alias borrada."
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
    ]

    for role_data in default_roles:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            db.add(Role(name=role_data["name"], description=role_data["description"]))
    db.commit()

    # Va DESPUES del seed de roles (necesita que los corporativos existan para
    # tener adonde reasignar) y ANTES de resolver los roles de los usuarios demo,
    # para que un usuario que aun apunta a un alias quede en el corporativo y no
    # en una fila que esta misma pasada va a borrar.
    _migrate_role_aliases(db)

    admin_role = _role(db, ROLE_ADMINISTRADOR)
    financiero_role = _role(db, ROLE_ANALISTA_FINANCIERO)
    ti_role = _role(db, ROLE_INGENIERO_TI)

    # Un usuario por rol corporativo: es lo que hace que la matriz RBAC se pueda
    # DEMOSTRAR en el login, no solo leer. `economista` y `ti` conservan el
    # username aunque su rol ya no se llame asi, porque los tests y las capturas
    # los buscan por ahi.
    demo_users = [
        {"username": "admin", "email": "admin@empresa.com", "pwd": "admin123", "is_admin": True, "role": admin_role},
        {"username": "director", "email": "director@empresa.com", "pwd": "director123", "is_admin": False, "role": _role(db, ROLE_DIRECTOR_EJECUTIVO)},
        {"username": "economista", "email": "economista@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
        {"username": "felipe_economista", "email": "felipe@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
        {"username": "talento", "email": "talento@empresa.com", "pwd": "talento123", "is_admin": False, "role": _role(db, ROLE_GERENTE_TALENTO)},
        {"username": "bi", "email": "bi@empresa.com", "pwd": "bi123", "is_admin": False, "role": _role(db, ROLE_ANALISTA_BI)},
        {"username": "ti", "email": "ti@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
        {"username": "juan_ti", "email": "juan@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
        {"username": "seguridad", "email": "seguridad@empresa.com", "pwd": "seguridad123", "is_admin": False, "role": _role(db, ROLE_OFICIAL_SEGURIDAD)},
        {"username": "consultor", "email": "consultor@empresa.com", "pwd": "consultor123", "is_admin": False, "role": _role(db, ROLE_USUARIO)},
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

    negocio_tables = [
        "dim_categorias", "dim_productos", "dim_clientes",
        "fact_ventas", "fact_ingresos_costos",
    ]
    tech_tables = [
        "dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos",
    ]
    personal_tables = ["dim_empleados"]
    # Las encuestas de clima (OSMI) viven en `setup_mental_health_db.py`, que es
    # opcional: si ese dataset no se cargo, sembrar permisos sobre tablas
    # inexistentes es una fila muerta, no un fallo. Van a TODOS los roles porque
    # clima laboral no es dato de finanzas ni de infraestructura.
    survey_tables = ["Answer", "Question", "Survey", "answer", "question", "survey"]
    catalogo_tables = ["dim_categorias", "dim_productos"]

    all_tables = negocio_tables + tech_tables + personal_tables + survey_tables

    # `negocio_tables` mezcla dos cosas de confidencialidad distinta: el detalle
    # transaccional y el catalogo comercial. `dim_categorias` y `dim_productos` son
    # una lista de precios que cualquiera puede consultar; `fact_ventas` y
    # `dim_clientes` son la operacion.
    #
    # Por eso los perfiles que no tocan finanzas reciben el catalogo pero no el
    # bloque transaccional. Con una sola lista, revocar "negocio" al Analista de
    # Datos le borraba tambien el catalogo y lo dejaba identico al Ingeniero de TI:
    # dos roles con la misma matriz hacen que la gobernanza no demuestre nada.
    negocio_transaccional = ["dim_clientes", "fact_ventas", "fact_ingresos_costos"]

    # El C-Level NO ve las tablas transaccionales. Ve rentabilidad consolidada
    # (`fact_ingresos_costos` es un cierre por mes y categoria, no una linea de
    # venta) y la cartera de clientes, pero no el detalle transaccional: esa es
    # exactamente la diferencia entre dirigir y auditar una operacion. Con
    # `negocio_tables` completo era indistinguible del Analista Financiero, y dos
    # perfiles que ven lo mismo no demuestran nada en una demo de gobernanza.
    #
    # El Analista de Datos NO ve finanzas. Antes la matriz le daba las nueve
    # tablas para que pudiera correlacionar ventas con consumo de CPU, pero eso
    # contradice el aislamiento por area: un perfil que cruza areas deja de
    # cruzar areas. Sigue siendo el unico rol que ve negocio, tecnica Y personal a
    # la vez (sueltas y sin remuneraciones), que es lo que lo distingue.
    role_matrix = {
        ROLE_ADMINISTRADOR: all_tables,
        ROLE_DIRECTOR_EJECUTIVO: ["fact_ingresos_costos"] + catalogo_tables + personal_tables + survey_tables,
        ROLE_ANALISTA_FINANCIERO: negocio_tables + personal_tables + survey_tables,
        ROLE_GERENTE_TALENTO: personal_tables + survey_tables,
        # Catálogo + técnica + personal: cruza áreas sin tocar el bloque
        # transaccional. Es lo que lo distingue del Ingeniero de TI.
        #
        # NO lleva `catalogo_tables`: el DPO sí, porque para auditar a quién se le
        # vendió qué necesita el catálogo comercial, y sin esa diferencia el
        # Analista de Datos y el Oficial de Cumplimiento quedaban con la misma
        # matriz. Un perfil que no se distingue de otro no agrega nada.
        ROLE_ANALISTA_BI: tech_tables + personal_tables + survey_tables,
        ROLE_INGENIERO_TI: tech_tables + personal_tables + survey_tables,
        ROLE_OFICIAL_SEGURIDAD: tech_tables + catalogo_tables + personal_tables + survey_tables,
        ROLE_USUARIO: catalogo_tables + survey_tables,
    }

    role_table_mappings = []
    for role_name, tbl_list in role_matrix.items():
        r_obj = _role(db, role_name)
        if r_obj:
            role_table_mappings.append((r_obj, tbl_list))

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
                        # 8 roles y las tablas declaradas arriba), asi que las
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
    # Commit antes de revocar. Los DELETE de abajo y los INSERT de arriba harian
    # flush en el mismo orden de la sesion, y el borrado podria alcanzar filas que
    # el propio seed de este arranque acaba de sembrar: el `in_` de la revocacion
    # matchea por nombre de tabla, no por origen.
    db.commit()

    # Los roles por area NO ven las tablas del area que no es la suya.
    #
    # La matriz de arriba solo CONCEDE; esto REVOCA. Hace falta por los roles que
    # copiaban la matriz de otro en una version anterior: un despliegue que ya
    # tenia permisos de mas los conserva, y sin este corte quedaria un Analista
    # Financiero viendo `dim_servidores`. Se listan los roles de verdad, no los
    # nombres de alias que ya no existen.
    #
    # Las tablas SAP (`vbak_*`, `ekko_*`, `kna1_*`) se conservan en la lista del
    # Ingeniero de TI: son nombres de un ERP que la demo no carga, pero si un
    # datasetUploaded las trae, el area de finanzas no debe verlas.
    # Cada lista es lo que EXCEDE a ese rol. No se escribe la matriz entera como
    # "prohibido": el Consultor tiene lectura minima del CATALOGO, que es un
    # subconjunto de `negocio_tables`, y revocar `negocio_tables` le borraba las
    # dos tablas que el paso de arriba le concedia.
    #
    # SAP (`vbak_*`, `ekko_*`, `kna1_*`) queda en la lista del Ingeniero de TI y
    # del resto: son nombres de un ERP que la demo no carga, pero si un dataset
    # subido las trae, ningun rol que no sea de finanzas debe verlas.
    sap_tables = [
        "vbak_cabpedidoventa", "vbap_pospedidoventa",
        "ekko_cabpedidocompra", "ekpo_pospedidocompra", "kna1_clientes",
    ]
    # Lo que se revoca aca es lo que NO tiene procedencia demostrable, o sea
    # `granted_by_admin == False`: el residuo del seed viejo que copiaba la
    # matriz de otro rol. Es el mismo criterio, y por el mismo motivo, que usa la
    # migracion de default-deny mas abajo: una fila que nadie concedio a proposito
    # no se presume concedida.
    #
    # Sin ese filtro esta pasada se llevaba tambien lo que un admin concedio con
    # PUT /api/v1/permissions. El caso reproducido: `dim_servidores` al Analista
    # Financiero, que el reinicio siguiente borraba porque `dim_servidores` esta en
    # `tech_tables` y el `in_` matchea por nombre de tabla, no por origen. Eso
    # deja al producto sin forma de recuperar el acceso, y lo hace sin avisar.
    #
    # NO se filtra por `connection_id` a proposito: la procedencia ya discrimina.
    # En las conexiones de plataforma (is_uploaded == False) esta pasada es lo
    # unico que limpia el residuo, porque la migracion de default-deny no las
    # toca -- ahi vive la matriz declarada de arriba y borrarla dejaria el
    # producto sin acceso. En las subidas esa migracion ya borra TODAS las False,
    # tabla sea cual sea, asi que aqui no queda nada que anadir.
    for r_name, prohibido in (
        # El Analista Financiero es el dueno del bloque transaccional.
        (ROLE_ANALISTA_FINANCIERO, tech_tables),
        # El C-Level ve rentabilidad consolidada, no la cartera ni el detalle.
        (ROLE_DIRECTOR_EJECUTIVO, tech_tables + ["dim_clientes", "fact_ventas"]),
        # El Analista de Datos no toca finanzas: es el corte que pidió el área.
        (ROLE_ANALISTA_BI, negocio_transaccional),
        (ROLE_INGENIERO_TI, negocio_transaccional),
        (ROLE_GERENTE_TALENTO, tech_tables + negocio_tables),
        (ROLE_USUARIO, tech_tables + personal_tables + negocio_transaccional),
        # El DPO audita accesos y trazabilidad, no rentabilidad.
        (ROLE_OFICIAL_SEGURIDAD, negocio_transaccional),
    ):
        prohibido = list(set(prohibido) | set(sap_tables))
        r_obj = _role(db, r_name)
        if not r_obj:
            continue
        db.query(RoleTablePermission).filter(
            RoleTablePermission.role_id == r_obj.id,
            RoleTablePermission.granted_by_admin == False,  # noqa: E712
            RoleTablePermission.table_name.in_(list(set(prohibido)))
        ).delete(synchronize_session=False)
    db.commit()

    # Seed column-level security permissions (CLS) for standard connections
    for s_conn in standard_connections:
        s_schema = "public" if (s_conn.db_type == DatabaseType.POSTGRESQL or str(s_conn.db_type).lower() == "postgresql") else "main"
        # SOLO el Administrador de Plataforma queda fuera de la CLS.
        #
        # Antes el Director Ejecutivo tambien, y por eso le llegaba en claro la
        # tarjeta de crédito, el IBAN y el sueldo del empleado: mirar rentabilidad
        # global no requiere ver el instrumento de pago de un cliente ni la cuenta
        # bancaria de una persona. Un C-Level dirige sobre agregar; el detalle
        # identificable es del area que responde por el dato.
        non_admin_roles = db.query(Role).filter(
            ~Role.name.in_([ROLE_ADMINISTRADOR])
        ).all()
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

            # 3. Block the service API key
            #
            # Va aqui, junto al token de tarjeta, y NO con los sueldos: ese bloque
            # esta dentro de `if not is_hr_role` porque un sueldo es un dato que
            # RRHH legitimamente necesita ver. Una API key no esta en ese caso: es
            # una credencial que se autentica contra los propios servidores, o sea
            # un secreto para todo rol no-admin, RRHH incluido -- que alguien sea de
            # RRHH no lo hace menos tecnico.
            #
            # Sin esta fila la columna quedaba sin clasificar en la matriz y
            # `GET /catalog/data-dictionary` le devolvia `SECRET-KEY-PROD-DB01` en
            # claro a `economista`: la misma fuga que el IBAN o el sueldo, un nivel
            # mas arriba porque la credencial abre la infraestructura.
            existing_api_key = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == r_obj.id,
                RoleColumnPermission.connection_id == s_conn.id,
                RoleColumnPermission.table_name == "dim_servidores",
                RoleColumnPermission.column_name == "api_key_servicio"
            ).first()
            if not existing_api_key:
                db.add(RoleColumnPermission(
                    role_id=r_obj.id,
                    connection_id=s_conn.id,
                    schema_name=s_schema,
                    table_name="dim_servidores",
                    column_name="api_key_servicio",
                    permission_type=ColumnPermissionType.BLOCKED
                ))

            # 4. Block salary and compensation for non-HR roles
            #
            # Los nombres de las dos demos no coinciden: la de PostgreSQL tiene
            # `sueldo_mensual` y la demo SQLite `salario_bruto`. Con una lista por
            # motor, la demo sin PostgreSQL (el arranque de serie cuando no hay servidor)
            # se quedaba con el sueldo y el IBAN sin clasificar: el diccionario y
            # el chat los servian en claro a cualquier rol. Se siembran TODOS los
            # nombres; los que la conexion no tiene no son mas que una fila muerta.
            is_hr_role = "talento" in r_obj.name.lower() or "rrhh" in r_obj.name.lower()
            if not is_hr_role:
                for col in ["sueldo_mensual", "salario", "salario_bruto", "bono_anual",
                            "cuenta_bancaria_iban"]:
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

            # 5. El RUT/DNI del empleado es la misma clase de dato que el del
            # cliente: se consulta pero se enmascara. Sin esta fila, la demo SQLite
            # lo expone en claro (la de PostgreSQL no tiene la columna).
            existing_emp_rut = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == r_obj.id,
                RoleColumnPermission.connection_id == s_conn.id,
                RoleColumnPermission.table_name == "dim_empleados",
                RoleColumnPermission.column_name == "rut_dni"
            ).first()
            if not existing_emp_rut:
                db.add(RoleColumnPermission(
                    role_id=r_obj.id,
                    connection_id=s_conn.id,
                    schema_name=s_schema,
                    table_name="dim_empleados",
                    column_name="rut_dni",
                    permission_type=ColumnPermissionType.MASKED
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
