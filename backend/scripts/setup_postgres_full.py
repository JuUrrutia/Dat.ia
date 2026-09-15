"""
DATIA - Setup & Full Migration to PostgreSQL
Creates databases, initializes corporate enterprise schema with rich business data,
migrates/seeds metadata, configures PostgreSQL CorporateConnection, RBAC, and Catalog.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import random

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base, get_database_url, build_engine_for_connector
from app.core.security import encrypt_credential, get_password_hash
from app.modules.auth.models import User, Role, Domain, UserSession
from app.modules.admin_catalog.models import (
    CorporateConnection,
    DatabaseType,
    SemanticCatalog,
    RoleTablePermission,
    RoleColumnPermission,
    ColumnPermissionType
)
from app.modules.telemetry_audit.models import AuditLog

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("setup_postgres_full")

PG_HOST = settings.POSTGRES_SERVER
PG_PORT = settings.POSTGRES_PORT
PG_USER = settings.POSTGRES_USER
PG_PASSWORD = settings.POSTGRES_PASSWORD
METADATA_DB = settings.POSTGRES_DB  # democratizacion_metadatos
BUSINESS_DB = "democratizacion_empresa"

MAINTENANCE_URL = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/postgres"
METADATA_URL = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{METADATA_DB}"
BUSINESS_URL = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{BUSINESS_DB}"

def create_database_if_not_exists(dbname: str):
    """Connects to maintenance DB and creates target DB if it does not exist."""
    m_engine = create_engine(MAINTENANCE_URL, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    with m_engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": dbname}).scalar()
        if not exists:
            logger.info(f"Creando base de datos PostgreSQL '{dbname}'...")
            conn.execute(text(f'CREATE DATABASE "{dbname}" OWNER "{PG_USER}"'))
            logger.info(f"Base de datos '{dbname}' creada exitosamente.")
        else:
            logger.info(f"Base de datos '{dbname}' ya existe.")
    m_engine.dispose()

def setup_business_database():
    """Initializes schema and seeds realistic data into democratizacion_empresa."""
    logger.info(f"Configurando esquema y datos en PostgreSQL: '{BUSINESS_DB}'...")
    b_engine = create_engine(BUSINESS_URL, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

    ddl_sql = """
    CREATE TABLE IF NOT EXISTS dim_categorias (
        id_categoria SERIAL PRIMARY KEY,
        nombre_categoria VARCHAR(100) NOT NULL UNIQUE,
        descripcion TEXT
    );

    CREATE TABLE IF NOT EXISTS dim_productos (
        id_producto SERIAL PRIMARY KEY,
        nombre_producto VARCHAR(150) NOT NULL,
        id_categoria INT REFERENCES dim_categorias(id_categoria),
        precio_unitario NUMERIC(12, 2) NOT NULL,
        costo_unitario NUMERIC(12, 2) NOT NULL,
        stock_disponible INT DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS dim_clientes (
        id_cliente SERIAL PRIMARY KEY,
        nombre_empresa VARCHAR(150) NOT NULL,
        rut_dni_cliente VARCHAR(20) NOT NULL,
        email_contacto VARCHAR(150),
        telefono_contacto VARCHAR(50),
        tarjeta_credito_token VARCHAR(50),
        sector_industria VARCHAR(100),
        nivel_riesgo_crediticio VARCHAR(20) DEFAULT 'BAJO',
        fecha_alta DATE DEFAULT CURRENT_DATE
    );

    CREATE TABLE IF NOT EXISTS dim_empleados (
        id_empleado SERIAL PRIMARY KEY,
        nombre_completo VARCHAR(150) NOT NULL,
        cargo VARCHAR(100) NOT NULL,
        departamento VARCHAR(100) NOT NULL,
        sueldo_mensual NUMERIC(12, 2) NOT NULL,
        fecha_ingreso DATE NOT NULL,
        activo BOOLEAN DEFAULT TRUE
    );

    CREATE TABLE IF NOT EXISTS fact_ventas (
        id_venta SERIAL PRIMARY KEY,
        fecha_venta DATE NOT NULL,
        id_producto INT REFERENCES dim_productos(id_producto),
        id_cliente INT REFERENCES dim_clientes(id_cliente),
        cantidad INT NOT NULL,
        monto_total NUMERIC(14, 2) NOT NULL,
        costo_total NUMERIC(14, 2) NOT NULL,
        margen_ganancia NUMERIC(14, 2) NOT NULL,
        metodo_pago VARCHAR(50) DEFAULT 'TRANSFERENCIA',
        estado VARCHAR(30) DEFAULT 'COMPLETADO'
    );

    CREATE TABLE IF NOT EXISTS fact_ingresos_costos (
        id_registro SERIAL PRIMARY KEY,
        mes VARCHAR(20) NOT NULL,
        anio INT NOT NULL,
        categoria_financiera VARCHAR(100) NOT NULL,
        ingreso_bruto NUMERIC(14, 2) NOT NULL,
        costo_operativo NUMERIC(14, 2) NOT NULL,
        utilidad_neta NUMERIC(14, 2) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_servidores (
        id_servidor SERIAL PRIMARY KEY,
        nombre_host VARCHAR(100) NOT NULL UNIQUE,
        ip_interna VARCHAR(45) NOT NULL,
        sistema_operativo VARCHAR(100),
        datacenter VARCHAR(50),
        capacidad_ram_gb INT
    );

    CREATE TABLE IF NOT EXISTS fact_incidentes_ti (
        id_incidente SERIAL PRIMARY KEY,
        fecha_incidente TIMESTAMP NOT NULL,
        id_servidor INT REFERENCES dim_servidores(id_servidor),
        tipo_falla VARCHAR(100) NOT NULL,
        nivel_prioridad VARCHAR(20) CHECK (nivel_prioridad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')),
        horas_resolucion NUMERIC(6, 2),
        estado VARCHAR(30) DEFAULT 'RESUELTO'
    );

    CREATE TABLE IF NOT EXISTS fact_consumo_recursos (
        id_consumo SERIAL PRIMARY KEY,
        fecha_hora TIMESTAMP NOT NULL,
        id_servidor INT REFERENCES dim_servidores(id_servidor),
        porcentaje_cpu NUMERIC(5, 2),
        uso_ram_gb NUMERIC(6, 2),
        trafico_red_mb NUMERIC(10, 2)
    );
    """

    with b_engine.connect() as conn:
        for stmt in ddl_sql.split(";"):
            stmt_clean = stmt.strip()
            if stmt_clean:
                conn.execute(text(stmt_clean))

        # Check if already seeded
        ventas_count = conn.execute(text("SELECT COUNT(*) FROM fact_ventas")).scalar()
        if ventas_count and ventas_count > 0:
            logger.info(f"'{BUSINESS_DB}' ya contiene {ventas_count} registros en fact_ventas. Se conservan los datos.")
            b_engine.dispose()
            return

        logger.info("Insertando datos iniciales de negocio en PostgreSQL...")

        # 1. Categorias
        conn.execute(text("""
        INSERT INTO dim_categorias (id_categoria, nombre_categoria, descripcion) VALUES
        (1, 'Software Empresarial', 'Licencias de software corporativo y sistemas ERP/CRM'),
        (2, 'Hardware & Redes', 'Servidores, switches, laptops corporativas y perifericos'),
        (3, 'Servicios Cloud', 'Subscripciones a infraestructura de nube privada e híbrida'),
        (4, 'Consultoría & Soporte', 'Horas de servicios profesionales y soporte especializado')
        ON CONFLICT (id_categoria) DO NOTHING;
        """))

        # 2. Productos
        conn.execute(text("""
        INSERT INTO dim_productos (id_producto, nombre_producto, id_categoria, precio_unitario, costo_unitario, stock_disponible) VALUES
        (101, 'Licencia ERP Core Enterprise', 1, 25000.00, 12000.00, 50),
        (102, 'Servidor Rack 2U Dual Xeon', 2, 8500.00, 5800.00, 15),
        (103, 'Instancia Cloud VPC Dedicada', 3, 3200.00, 1800.00, 100),
        (104, 'Paquete 50 Hrs Consultoría BI', 4, 7500.00, 4200.00, 30),
        (105, 'Switch Gestionable 48 Puertos 10G', 2, 4200.00, 2900.00, 25),
        (106, 'Suite Ciberseguridad Endpoint EDR', 1, 15000.00, 7500.00, 80),
        (107, 'Almacenamiento SAN All-Flash 40TB', 2, 32000.00, 21000.00, 8),
        (108, 'Migración Cloud & Arquitectura AWS', 4, 18500.00, 9500.00, 20)
        ON CONFLICT (id_producto) DO NOTHING;
        """))

        # 3. Clientes
        conn.execute(text("""
        INSERT INTO dim_clientes (id_cliente, nombre_empresa, rut_dni_cliente, email_contacto, telefono_contacto, tarjeta_credito_token, sector_industria, nivel_riesgo_crediticio, fecha_alta) VALUES
        (1, 'Banco de Comercio y Crédito', '76.123.456-7', 'contacto@bancocomercio.cl', '+56911223344', 'TOK-VISA-9821-XYZ', 'Banca & Servicios Financieros', 'BAJO', '2025-01-15'),
        (2, 'Retail Corporativo Global', '78.987.654-3', 'finanzas@retailglobal.com', '+56922334455', 'TOK-MC-4412-ABC', 'Retail & Gran Consumo', 'BAJO', '2025-02-10'),
        (3, 'Logística & Transportes del Norte', '77.456.789-1', 'operaciones@logisticanorte.cl', '+56933445566', 'TOK-AMEX-1029-DEF', 'Logística & Cadena de Suministro', 'MEDIO', '2025-03-05'),
        (4, 'Clínica Salud Integral', '79.111.222-9', 'ti@saludintegral.cl', '+56944556677', 'TOK-VISA-5561-GHI', 'Salud & Salud Privada', 'BAJO', '2025-04-12'),
        (5, 'Minería Andina del Cobre', '76.555.444-K', 'abastecimiento@mineriandina.cl', '+56955667788', 'TOK-VISA-7788-JKL', 'Minería & Recursos Naturales', 'BAJO', '2025-05-20'),
        (6, 'Agroindustrias del Valle Central', '81.234.567-8', 'gerencia@agrovalle.cl', '+56966778899', 'TOK-MC-9900-MNO', 'Agricultura & Exportaciones', 'MEDIO', '2025-06-01')
        ON CONFLICT (id_cliente) DO NOTHING;
        """))

        # 4. Empleados
        conn.execute(text("""
        INSERT INTO dim_empleados (id_empleado, nombre_completo, cargo, departamento, sueldo_mensual, fecha_ingreso, activo) VALUES
        (1, 'Carlos Mendoza Rivera', 'Director de Tecnología (CTO)', 'Tecnología & TI', 6500000.00, '2023-01-10', TRUE),
        (2, 'Valentina Soto Morales', 'Gerente de Finanzas (CFO)', 'Economía & Finanzas', 6200000.00, '2023-03-15', TRUE),
        (3, 'Felipe Valenzuela Silva', 'Lead Data Scientist', 'Tecnología & TI', 4800000.00, '2023-06-01', TRUE),
        (4, 'Andrea Lagos Pizarro', 'Analista Financiero Senior', 'Economía & Finanzas', 3200000.00, '2024-02-01', TRUE),
        (5, 'Rodrigo Castro Araya', 'Ingeniero DevOps & Cloud', 'Tecnología & TI', 3600000.00, '2024-04-15', TRUE),
        (6, 'Daniela Fuentes Rojas', 'Account Executive Enterprise', 'Operaciones & Comercial', 3400000.00, '2024-05-01', TRUE)
        ON CONFLICT (id_empleado) DO NOTHING;
        """))

        # 5. Ventas (Rich dataset)
        random.seed(42)
        ventas_rows = [
            ("2026-07-05", 101, 1, 2, 50000.00, 24000.00, 26000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-07-12", 102, 3, 4, 34000.00, 23200.00, 10800.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-07-20", 103, 2, 5, 16000.00, 9000.00, 7000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-08-02", 104, 4, 2, 15000.00, 8400.00, 6600.00, "TARJETA_CREDITO", "COMPLETADO"),
            ("2026-08-10", 101, 2, 1, 25000.00, 12000.00, 13000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-08-14", 105, 1, 3, 12600.00, 8700.00, 3900.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-08-18", 106, 5, 4, 60000.00, 30000.00, 30000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-08-25", 107, 1, 1, 32000.00, 21000.00, 11000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-08-28", 108, 6, 2, 37000.00, 19000.00, 18000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-09-01", 103, 4, 8, 25600.00, 14400.00, 11200.00, "TARJETA_CREDITO", "COMPLETADO"),
            ("2026-09-03", 101, 5, 3, 75000.00, 36000.00, 39000.00, "TRANSFERENCIA", "COMPLETADO"),
            ("2026-09-05", 105, 3, 5, 21000.00, 14500.00, 6500.00, "TRANSFERENCIA", "COMPLETADO"),
        ]

        # Generate 40 more realistic sales
        base_date = datetime(2026, 1, 1)
        prods = [
            (101, 25000.0, 12000.0), (102, 8500.0, 5800.0), (103, 3200.0, 1800.0),
            (104, 7500.0, 4200.0), (105, 4200.0, 2900.0), (106, 15000.0, 7500.0),
            (107, 32000.0, 21000.0), (108, 18500.0, 9500.0)
        ]
        clients = [1, 2, 3, 4, 5, 6]
        methods = ["TRANSFERENCIA", "TRANSFERENCIA", "TARJETA_CREDITO", "ORDEN_COMPRA"]

        for i in range(40):
            d = base_date + timedelta(days=random.randint(0, 240))
            p_id, p_price, p_cost = random.choice(prods)
            c_id = random.choice(clients)
            qty = random.randint(1, 6)
            total = p_price * qty
            c_total = p_cost * qty
            margin = total - c_total
            m_pago = random.choice(methods)
            ventas_rows.append((
                d.strftime("%Y-%m-%d"), p_id, c_id, qty, total, c_total, margin, m_pago, "COMPLETADO"
            ))

        for v in ventas_rows:
            conn.execute(text("""
            INSERT INTO fact_ventas (fecha_venta, id_producto, id_cliente, cantidad, monto_total, costo_total, margen_ganancia, metodo_pago, estado)
            VALUES (:f, :p, :c, :q, :m, :ct, :mg, :mp, :st)
            """), {
                "f": v[0], "p": v[1], "c": v[2], "q": v[3], "m": v[4],
                "ct": v[5], "mg": v[6], "mp": v[7], "st": v[8]
            })

        # 6. Ingresos & Costos Mensuales
        fin_rows = [
            ('Enero', 2026, 'Ventas Software & Cloud', 180000.00, 105000.00, 75000.00),
            ('Febrero', 2026, 'Ventas Software & Cloud', 210000.00, 120000.00, 90000.00),
            ('Marzo', 2026, 'Ventas Software & Cloud', 245000.00, 135000.00, 110000.00),
            ('Abril', 2026, 'Ventas Software & Cloud', 195000.00, 115000.00, 80000.00),
            ('Mayo', 2026, 'Ventas Software & Cloud', 230000.00, 128000.00, 102000.00),
            ('Junio', 2026, 'Ventas Software & Cloud', 280000.00, 145000.00, 135000.00),
            ('Julio', 2026, 'Ventas Software & Cloud', 310000.00, 160000.00, 150000.00),
            ('Agosto', 2026, 'Ventas Software & Cloud', 295000.00, 152000.00, 143000.00),
        ]
        for f in fin_rows:
            conn.execute(text("""
            INSERT INTO fact_ingresos_costos (mes, anio, categoria_financiera, ingreso_bruto, costo_operativo, utilidad_neta)
            VALUES (:m, :a, :cat, :ing, :cost, :util)
            """), {
                "m": f[0], "a": f[1], "cat": f[2], "ing": f[3], "cost": f[4], "util": f[5]
            })

        # 7. Servidores TI
        conn.execute(text("""
        INSERT INTO dim_servidores (id_servidor, nombre_host, ip_interna, sistema_operativo, datacenter, capacidad_ram_gb) VALUES
        (1, 'srv-db-prod-01', '10.0.1.45', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Primary', 128),
        (2, 'srv-app-core-02', '10.0.1.46', 'Red Hat Enterprise Linux 9', 'DC-Santiago-Primary', 64),
        (3, 'srv-cloud-proxy-03', '10.0.2.10', 'Debian 12', 'DC-AWS-Cloud-UsEast', 32),
        (4, 'srv-backup-node-04', '10.0.3.15', 'Windows Server 2022', 'DC-Valparaiso-Backup', 256),
        (5, 'srv-analytics-ai-05', '10.0.2.25', 'Ubuntu Server 24.04 LTS', 'DC-Santiago-Primary', 512)
        ON CONFLICT (id_servidor) DO NOTHING;
        """))

        # 8. Incidentes TI
        inc_rows = [
            ('2026-08-01 04:15:00', 1, 'Alta latencia en disco SSD NVMe', 'ALTA', 2.5, 'RESUELTO'),
            ('2026-08-03 14:22:00', 2, 'Pico de consumo de memoria RAM (>95%)', 'CRITICA', 1.0, 'RESUELTO'),
            ('2026-08-08 09:10:00', 3, 'Reinicio inesperado de daemon de red BGP', 'MEDIA', 0.8, 'RESUELTO'),
            ('2026-08-12 18:45:00', 4, 'Falla en tarea cron de respaldo nocturno', 'BAJA', 4.0, 'RESUELTO'),
            ('2026-08-20 11:30:00', 5, 'Sobrecarga de GPU CUDA en pipeline de IA', 'ALTA', 1.5, 'RESUELTO'),
            ('2026-08-27 16:05:00', 2, 'Timeout en pool de conexiones de microservicio', 'MEDIA', 0.5, 'RESUELTO'),
            ('2026-09-02 08:20:00', 1, 'Degradación de réplica sincrónica PostgreSQL', 'CRITICA', 1.2, 'RESUELTO')
        ]
        for inc in inc_rows:
            conn.execute(text("""
            INSERT INTO fact_incidentes_ti (fecha_incidente, id_servidor, tipo_falla, nivel_prioridad, horas_resolucion, estado)
            VALUES (:fi, :srv, :tf, :np, :hr, :st)
            """), {
                "fi": inc[0], "srv": inc[1], "tf": inc[2], "np": inc[3], "hr": inc[4], "st": inc[5]
            })

        # 9. Consumo de Recursos TI
        recurso_rows = [
            ('2026-09-01 12:00:00', 1, 45.2, 84.5, 1250.0),
            ('2026-09-01 12:00:00', 2, 78.4, 52.1, 4500.0),
            ('2026-09-01 12:00:00', 3, 22.0, 14.2, 890.0),
            ('2026-09-01 12:00:00', 4, 12.5, 98.0, 150.0),
            ('2026-09-01 12:00:00', 5, 88.5, 420.0, 6800.0),
            ('2026-09-05 18:00:00', 1, 52.0, 92.0, 1400.0),
            ('2026-09-05 18:00:00', 2, 65.0, 48.0, 3900.0),
            ('2026-09-05 18:00:00', 5, 94.0, 480.0, 8500.0),
        ]
        for rec in recurso_rows:
            conn.execute(text("""
            INSERT INTO fact_consumo_recursos (fecha_hora, id_servidor, porcentaje_cpu, uso_ram_gb, trafico_red_mb)
            VALUES (:fh, :srv, :cpu, :ram, :net)
            """), {
                "fh": rec[0], "srv": rec[1], "cpu": rec[2], "ram": rec[3], "net": rec[4]
            })

        # Reset serial sequences for auto-increment PKs
        for tbl, pk in [
            ("dim_categorias", "id_categoria"),
            ("dim_productos", "id_producto"),
            ("dim_clientes", "id_cliente"),
            ("dim_empleados", "id_empleado"),
            ("fact_ventas", "id_venta"),
            ("fact_ingresos_costos", "id_registro"),
            ("dim_servidores", "id_servidor"),
            ("fact_incidentes_ti", "id_incidente"),
            ("fact_consumo_recursos", "id_consumo"),
        ]:
            try:
                conn.execute(text(f"""
                SELECT setval(pg_get_serial_sequence('{tbl}', '{pk}'), COALESCE((SELECT MAX({pk}) FROM {tbl}), 1));
                """))
            except Exception as seq_err:
                logger.warning(f"Aviso al actualizar secuencia {tbl}: {seq_err}")

    b_engine.dispose()
    logger.info(f"Base de datos de negocio '{BUSINESS_DB}' poblada exitosamente.")

def setup_metadata_database():
    """Initializes schemas, tables, users, roles, RBAC permissions and catalog in democratizacion_metadatos."""
    logger.info(f"Inicializando base de datos de gobernanza y metadatos: '{METADATA_DB}'...")
    m_engine = create_engine(METADATA_URL, pool_pre_ping=True)

    # 1. Create all tables defined in SQLAlchemy Base
    Base.metadata.create_all(bind=m_engine)

    Session = sessionmaker(bind=m_engine)
    db = Session()

    try:
        # Seed Domains
        domains_data = [
            {"name": "Economía & Finanzas", "description": "Ingresos, costos, presupuestos, facturación y márgenes de negocio"},
            {"name": "Tecnología & TI", "description": "Infraestructura, servidores, consumo de recursos e incidentes técnicos"},
            {"name": "Operaciones & Comercial", "description": "Ventas, clientes, almacenes y catálogo de productos"},
            {"name": "Talento & Personas", "description": "Desempeño, clima laboral, encuestas y bienestar organizacional"},
            {"name": "Seguridad & Gobernanza", "description": "Cumplimiento normativo, auditoría, accesos y trazabilidad de datos"},
        ]
        for d in domains_data:
            if not db.query(Domain).filter(Domain.name == d["name"]).first():
                db.add(Domain(name=d["name"], description=d["description"]))
        db.commit()

        # Seed Roles
        roles_data = [
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
        for r in roles_data:
            if not db.query(Role).filter(Role.name == r["name"]).first():
                db.add(Role(name=r["name"], description=r["description"]))
        db.commit()

        admin_role = db.query(Role).filter(Role.name.in_(["Administrador de Plataforma", "Administrador"])).first()
        financiero_role = db.query(Role).filter(Role.name.in_(["Analista Financiero & Comercial", "Economista"])).first()
        ti_role = db.query(Role).filter(Role.name.in_(["Ingeniero de Infraestructura & TI", "TI"])).first()

        # Seed Users
        users_data = [
            {"username": "admin", "email": "admin@empresa.com", "pwd": "admin123", "is_admin": True, "role": admin_role},
            {"username": "economista", "email": "economista@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
            {"username": "felipe_economista", "email": "felipe@empresa.com", "pwd": "economista123", "is_admin": False, "role": financiero_role},
            {"username": "ti", "email": "ti@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
            {"username": "juan_ti", "email": "juan@empresa.com", "pwd": "ti123", "is_admin": False, "role": ti_role},
        ]
        for u in users_data:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if not existing:
                db.add(User(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=get_password_hash(u["pwd"]),
                    is_admin=u["is_admin"],
                    is_active=True,
                    role_id=u["role"].id if u["role"] else None
                ))
        db.commit()

        # Seed CorporateConnection (PostgreSQL como conexión activa por defecto)
        pg_conn = db.query(CorporateConnection).filter(CorporateConnection.name == "Base de Datos Corporativa PostgreSQL").first()
        if not pg_conn:
            # Deactivate any other connections
            db.query(CorporateConnection).update({CorporateConnection.is_active: False})
            pg_conn = CorporateConnection(
                name="Base de Datos Corporativa PostgreSQL",
                db_type=DatabaseType.POSTGRESQL,
                host=PG_HOST,
                port=PG_PORT,
                database_name=BUSINESS_DB,
                username=PG_USER,
                encrypted_password=encrypt_credential(PG_PASSWORD),
                is_active=True,
                is_uploaded=False
            )
            db.add(pg_conn)
            db.commit()
            db.refresh(pg_conn)
        else:
            pg_conn.is_active = True
            pg_conn.host = PG_HOST
            pg_conn.port = PG_PORT
            pg_conn.database_name = BUSINESS_DB
            pg_conn.username = PG_USER
            pg_conn.encrypted_password = encrypt_credential(PG_PASSWORD)
            db.commit()

        connection_id = pg_conn.id

        # Seed RBAC Permissions for Business Tables in PostgreSQL
        business_tables = ["dim_categorias", "dim_productos", "dim_clientes", "dim_empleados", "fact_ventas", "fact_ingresos_costos"]
        tech_tables = ["dim_servidores", "fact_incidentes_ti", "fact_consumo_recursos", "dim_empleados"]
        all_tables = list(set(business_tables + tech_tables))

        admin_roles = db.query(Role).filter(Role.name.in_(["Administrador de Plataforma", "Administrador"])).all()
        fin_roles = db.query(Role).filter(Role.name.in_(["Analista Financiero & Comercial", "Economista"])).all()
        infra_roles = db.query(Role).filter(Role.name.in_(["Ingeniero de Infraestructura & TI", "TI"])).all()

        role_table_map = [
            (admin_roles, all_tables),
            (fin_roles, business_tables),
            (infra_roles, tech_tables),
        ]

        for r_list, tbls in role_table_map:
            for r in r_list:
                for tbl in tbls:
                    exists = db.query(RoleTablePermission).filter(
                        RoleTablePermission.role_id == r.id,
                        RoleTablePermission.connection_id == connection_id,
                        RoleTablePermission.table_name == tbl
                    ).first()
                    if not exists:
                        db.add(RoleTablePermission(
                            role_id=r.id,
                            connection_id=connection_id,
                            schema_name="public",
                            table_name=tbl,
                            is_allowed=True
                        ))
        db.commit()

        # Seed Column Permissions: Mask sensitive columns for non-admins
        for r in fin_roles + infra_roles:
            # Mask RUT / DNI
            rut_perm = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == r.id,
                RoleColumnPermission.connection_id == connection_id,
                RoleColumnPermission.table_name == "dim_clientes",
                RoleColumnPermission.column_name == "rut_dni_cliente"
            ).first()
            if not rut_perm:
                db.add(RoleColumnPermission(
                    role_id=r.id,
                    connection_id=connection_id,
                    schema_name="public",
                    table_name="dim_clientes",
                    column_name="rut_dni_cliente",
                    permission_type=ColumnPermissionType.MASKED
                ))

            # Block credit card token
            cc_perm = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == r.id,
                RoleColumnPermission.connection_id == connection_id,
                RoleColumnPermission.table_name == "dim_clientes",
                RoleColumnPermission.column_name == "tarjeta_credito_token"
            ).first()
            if not cc_perm:
                db.add(RoleColumnPermission(
                    role_id=r.id,
                    connection_id=connection_id,
                    schema_name="public",
                    table_name="dim_clientes",
                    column_name="tarjeta_credito_token",
                    permission_type=ColumnPermissionType.BLOCKED
                ))
        db.commit()

        # Seed Semantic Catalog
        catalog_items = [
            {"table": "fact_ventas", "col": None, "friendly": "Ventas y Facturación", "desc": "Registro histórico transaccional de ventas y facturación de la empresa."},
            {"table": "fact_ventas", "col": "monto_total", "friendly": "Monto Total Facturado", "desc": "Valor monetario total en pesos o dólares de la venta antes de impuestos."},
            {"table": "fact_ventas", "col": "margen_ganancia", "friendly": "Margen de Ganancia", "desc": "Utilidad bruta calculada como monto_total menos costo_total.", "formula": "monto_total - costo_total"},
            {"table": "fact_ventas", "col": "cantidad", "friendly": "Unidades Vendidas", "desc": "Número total de unidades del producto adquiridas en la transacción."},
            {"table": "fact_ventas", "col": "fecha_venta", "friendly": "Fecha de Venta", "desc": "Fecha calendario en la que se efectuó la transacción."},
            {"table": "dim_productos", "col": None, "friendly": "Catálogo de Productos", "desc": "Productos y servicios comercializados por la corporación."},
            {"table": "dim_productos", "col": "nombre_producto", "friendly": "Nombre del Producto", "desc": "Nombre comercial del ítem o servicio tecnológico."},
            {"table": "dim_productos", "col": "precio_unitario", "friendly": "Precio Unitario", "desc": "Precio de venta por unidad."},
            {"table": "dim_clientes", "col": None, "friendly": "Directorio de Clientes", "desc": "Directorio de empresas compradoras y clientes institucionales."},
            {"table": "dim_clientes", "col": "nombre_empresa", "friendly": "Razón Social o Empresa", "desc": "Nombre de la empresa cliente."},
            {"table": "dim_clientes", "col": "sector_industria", "friendly": "Sector o Industria", "desc": "Área económica a la que pertenece el cliente (Banca, Minería, Retail, etc.)."},
            {"table": "fact_ingresos_costos", "col": None, "friendly": "Resumen Financiero Mensual", "desc": "Métricas consolidadas mensuales de ingresos brutos, costos operativos y utilidad neta."},
            {"table": "fact_ingresos_costos", "col": "ingreso_bruto", "friendly": "Ingresos Brutos Mensuales", "desc": "Ingreso total bruto generado en el mes."},
            {"table": "fact_ingresos_costos", "col": "utilidad_neta", "friendly": "Utilidad Neta Mensual", "desc": "Beneficio neto mensual descontando costos operativos."},
            {"table": "dim_servidores", "col": None, "friendly": "Inventario de Servidores TI", "desc": "Servidores físicos y virtuales de los centros de datos."},
            {"table": "dim_servidores", "col": "nombre_host", "friendly": "Nombre de Host", "desc": "Identificador DNS/nombre de servidor en la red corporativa."},
            {"table": "fact_incidentes_ti", "col": None, "friendly": "Registro de Incidentes TI", "desc": "Tickets de fallas técnicas, caídas de servicio y alertas de infraestructura."},
            {"table": "fact_consumo_recursos", "col": None, "friendly": "Monitoreo de Recursos TI", "desc": "Telemetría periódica de uso de CPU, memoria RAM y tráfico de red por servidor."},
        ]

        for item in catalog_items:
            existing = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == connection_id,
                SemanticCatalog.schema_name == "public",
                SemanticCatalog.table_name == item["table"],
                SemanticCatalog.column_name == item["col"]
            ).first()
            if not existing:
                db.add(SemanticCatalog(
                    connection_id=connection_id,
                    schema_name="public",
                    table_name=item["table"],
                    column_name=item["col"],
                    friendly_name=item["friendly"],
                    description=item["desc"],
                    business_formula=item.get("formula"),
                    is_ai_generated=False
                ))
        db.commit()
        logger.info(f"Gobernanza RBAC y Catálogo Semántico en '{METADATA_DB}' configurados con éxito.")

    finally:
        db.close()
        m_engine.dispose()

def check_postgres_alive() -> bool:
    """Verifies that PostgreSQL server is reachable before attempting bootstrap."""
    try:
        m_engine = create_engine(MAINTENANCE_URL, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
        with m_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        m_engine.dispose()
        return True
    except Exception as e:
        logger.warning(f"PostgreSQL server ({PG_HOST}:{PG_PORT}) is not reachable: {e}")
        return False

def run() -> bool:
    logger.info("==================================================")
    logger.info("DATIA POSTGRESQL AUTO-BOOTSTRAP & HEALTH CHECK")
    logger.info("==================================================")
    logger.info(f"Host: {PG_HOST}:{PG_PORT} | Usuario: {PG_USER}")

    if not check_postgres_alive():
        logger.warning("No se pudo contactar al servidor PostgreSQL. Omitiendo auto-inicialización.")
        return False

    # 1. Ensure databases exist
    create_database_if_not_exists(METADATA_DB)
    create_database_if_not_exists(BUSINESS_DB)

    # 2. Setup business database with data
    setup_business_database()

    # 3. Setup metadata database with governance & active connection
    setup_metadata_database()

    logger.info("==================================================")
    logger.info("POSTGRESQL COMPLETAMENTE VERIFICADO Y SINCRONIZADO")
    logger.info("==================================================")
    return True

if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
