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

    # Get "Administrador" role
    admin_role = db.query(Role).filter(Role.name == "Administrador").first()

    # Seed Default Admin User if no admin exists
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_pwd = get_password_hash("admin123")
        admin = User(
            username="admin",
            email="admin@empresa.com",
            hashed_password=hashed_pwd,
            is_admin=True,
            is_active=True,
            role_id=admin_role.id if admin_role else None
        )
        db.add(admin)
        db.commit()
