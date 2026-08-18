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

    # Seed Default Domains
    default_domains = [
        {"name": "Economía & Finanzas", "description": "Ingresos, costos, presupuestos, facturación y márgenes de negocio"},
        {"name": "Tecnología & TI", "description": "Infraestructura, servidores, consumo de recursos e incidentes técnicos"},
        {"name": "Operaciones & Comercial", "description": "Ventas, clientes, almacenes y catálogo de productos"},
    ]

    for dom_data in default_domains:
        existing_dom = db.query(Domain).filter(Domain.name == dom_data["name"]).first()
        if not existing_dom:
            db.add(Domain(name=dom_data["name"], description=dom_data["description"]))
    db.commit()

    # Seed Default Roles (3 Core Roles + Default "Usuario")
    default_roles = [
        {"name": "Usuario", "description": "Perfil inicial por defecto sin asignación de dominios hasta aprobación por Administrador"},
        {"name": "Administrador", "description": "Acceso total a gobernanza RBAC, gestión de usuarios, conexiones BD y auditoría"},
        {"name": "Economista", "description": "Acceso a información económica, financiera, facturación, costos y márgenes de negocio"},
        {"name": "TI", "description": "Acceso a métricas de infraestructura, rendimiento de servidores e incidentes técnicos"},
    ]

    for role_data in default_roles:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            db.add(Role(name=role_data["name"], description=role_data["description"]))
    db.commit()

    # Get roles
    admin_role = db.query(Role).filter(Role.name == "Administrador").first()
    economista_role = db.query(Role).filter(Role.name == "Economista").first()
    ti_role = db.query(Role).filter(Role.name == "TI").first()

    # Seed Default Demo Users with official credentials (admin123, economista123, ti123)
    demo_users = [
        {"username": "admin", "email": "admin@empresa.com", "pwd": "admin123", "is_admin": True, "role": admin_role},
        {"username": "economista", "email": "economista@empresa.com", "pwd": "economista123", "is_admin": False, "role": economista_role},
        {"username": "felipe_economista", "email": "felipe@empresa.com", "pwd": "economista123", "is_admin": False, "role": economista_role},
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

    # Seed RoleTablePermission for Economista & TI
    economista_role = db.query(Role).filter(Role.name == "Economista").first()
    ti_role = db.query(Role).filter(Role.name == "TI").first()

    from app.models.permission import RoleTablePermission
    from app.models.catalog import SemanticCatalog

    economista_tables = [
        "dim_categorias", "dim_productos", "dim_clientes",
        "fact_ventas", "fact_ingresos_costos", "dim_empleados"
    ]
    ti_tables = [
        "dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos", "dim_empleados"
    ]

    if economista_role:
        for tbl in economista_tables:
            existing_perm = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == economista_role.id,
                RoleTablePermission.table_name == tbl
            ).first()
            if not existing_perm:
                db.add(RoleTablePermission(
                    role_id=economista_role.id,
                    connection_id=1,
                    schema_name="main",
                    table_name=tbl,
                    is_allowed=True
                ))

    if ti_role:
        for tbl in ti_tables:
            existing_perm = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == ti_role.id,
                RoleTablePermission.table_name == tbl
            ).first()
            if not existing_perm:
                db.add(RoleTablePermission(
                    role_id=ti_role.id,
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
        ("fact_consumo_recursos", "uso_ram_gb", "Memoria RAM utilizada en Gigabytes")
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
