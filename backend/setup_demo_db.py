import sqlite3
import os
import random
from datetime import datetime, timedelta

def setup_demo_sqlite():
    db_path = os.path.join(os.path.dirname(__file__), "demo_corporativa.db")
    
    # Remove existing demo DB to ensure fresh load
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # DDL with Realistic Enterprise Schema + Sensitive & Private Columns
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS dim_categorias (
        id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_categoria TEXT NOT NULL,
        descripcion TEXT
    );

    CREATE TABLE IF NOT EXISTS dim_productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_producto TEXT NOT NULL,
        id_categoria INTEGER,
        precio_unitario REAL NOT NULL,
        costo_unitario REAL NOT NULL,
        stock_disponible INTEGER DEFAULT 0,
        FOREIGN KEY (id_categoria) REFERENCES dim_categorias(id_categoria)
    );

    CREATE TABLE IF NOT EXISTS dim_clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_empresa TEXT NOT NULL,
        rut_dni_cliente TEXT NOT NULL,
        email_contacto TEXT,
        telefono_contacto TEXT,
        tarjeta_credito_token TEXT,
        sector_industria TEXT,
        nivel_riesgo_crediticio TEXT DEFAULT 'BAJO',
        fecha_alta TEXT DEFAULT '2025-01-01'
    );

    CREATE TABLE IF NOT EXISTS fact_ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_venta TEXT NOT NULL,
        id_producto INTEGER,
        id_cliente INTEGER,
        cantidad INTEGER NOT NULL,
        monto_total REAL NOT NULL,
        costo_total REAL NOT NULL,
        margen_ganancia REAL NOT NULL,
        metodo_pago TEXT DEFAULT 'TRANSFERENCIA',
        estado TEXT DEFAULT 'COMPLETADO',
        FOREIGN KEY (id_producto) REFERENCES dim_productos(id_producto),
        FOREIGN KEY (id_cliente) REFERENCES dim_clientes(id_cliente)
    );

    CREATE TABLE IF NOT EXISTS fact_ingresos_costos (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
        mes TEXT NOT NULL,
        anio INTEGER NOT NULL,
        categoria_financiera TEXT NOT NULL,
        ingreso_bruto REAL NOT NULL,
        costo_operativo REAL NOT NULL,
        impuestos_retenidos REAL NOT NULL,
        utilidad_neta REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_empleados (
        id_empleado INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_completo TEXT NOT NULL,
        rut_dni TEXT NOT NULL,
        cargo TEXT NOT NULL,
        departamento TEXT NOT NULL,
        email_corporativo TEXT,
        salario_bruto REAL NOT NULL,
        bono_anual REAL DEFAULT 0,
        cuenta_bancaria_iban TEXT NOT NULL,
        evaluacion_desempeno REAL DEFAULT 4.5,
        fecha_contratacion TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_servidores (
        id_servidor INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_host TEXT NOT NULL,
        ip_interna TEXT NOT NULL,
        ip_publica TEXT,
        api_key_servicio TEXT,
        sistema_operativo TEXT,
        datacenter TEXT,
        capacidad_ram_gb INTEGER,
        responsable_admin TEXT
    );

    CREATE TABLE IF NOT EXISTS fact_incidentes_ti (
        id_incidente INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_incidente TEXT NOT NULL,
        id_servidor INTEGER,
        tipo_falla TEXT NOT NULL,
        nivel_prioridad TEXT,
        horas_resolucion REAL,
        costo_impacto_usd REAL DEFAULT 0,
        estado TEXT DEFAULT 'RESUELTO',
        FOREIGN KEY (id_servidor) REFERENCES dim_servidores(id_servidor)
    );

    CREATE TABLE IF NOT EXISTS fact_consumo_recursos (
        id_consumo INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT NOT NULL,
        id_servidor INTEGER,
        porcentaje_cpu REAL,
        uso_ram_gb REAL,
        trafico_red_mb REAL,
        FOREIGN KEY (id_servidor) REFERENCES dim_servidores(id_servidor)
    );
    """)

    # -------------------------------------------------------------
    # 1. SEED: dim_categorias (8 categorías)
    # -------------------------------------------------------------
    categorias = [
        (1, 'Software Empresarial', 'Licencias corporativas, ERP, CRM y suites ofimáticas'),
        (2, 'Hardware & Redes', 'Servidores físicos, switches gestionables, firewalls y routers'),
        (3, 'Servicios Cloud', 'Instancias IaaS, buckets de almacenamiento y VPC dedicada'),
        (4, 'Consultoría & BI', 'Horas de arquitectura de datos, dashboards PowerBI y machine learning'),
        (5, 'Ciberseguridad & SOC', 'Monitoreo EDR, análisis de vulnerabilidades y servicios de pentesting'),
        (6, 'Infraestructura Crítica', 'UPS de alta densidad, generadores de respaldo y refrigeración datacenter'),
        (7, 'Licenciamiento SaaS', 'Suscripciones mensuales de correo seguro, videoconferencia y colaboración'),
        (8, 'Soporte 24/7', 'Contratos de mesa de ayuda empresarial con SLA menor a 1 hora')
    ]
    cursor.executemany("INSERT INTO dim_categorias VALUES (?, ?, ?)", categorias)

    # -------------------------------------------------------------
    # 2. SEED: dim_productos (30 productos con stocks realistas)
    # -------------------------------------------------------------
    productos_base = [
        # Software
        (101, 'Licencia ERP Core Enterprise', 1, 25000.0, 12000.0, 50),
        (102, 'Suscripción CRM Pro 50 Usuarios', 1, 14500.0, 7200.0, 35),
        (103, 'Motor Base de Datos High Availability', 1, 18000.0, 9500.0, 20),
        (104, 'Suite Analítica BI Predictiva', 1, 12000.0, 6000.0, 45),
        # Hardware
        (105, 'Servidor Rack 2U Dual Xeon Silver', 2, 8500.0, 5800.0, 15), # < 30
        (106, 'Switch Gestionable 48 Puertos 10G', 2, 4200.0, 2900.0, 25), # < 30
        (107, 'Firewall Next-Gen 10Gbps Enterprise', 2, 9800.0, 6700.0, 8), # < 30
        (108, 'Router BGP Redundante para Datacenter', 2, 7500.0, 4800.0, 12), # < 30
        (109, 'Storage All-Flash Array 50TB NVMe', 2, 32000.0, 22000.0, 6), # < 30
        (110, 'Patch Panel Blindado Cat6A 24P', 2, 450.0, 220.0, 120),
        # Cloud
        (111, 'Instancia Cloud VPC Dedicada 32C/128GB', 3, 3200.0, 1800.0, 100),
        (112, 'Cluster Kubernetes Gestionado HA', 3, 4500.0, 2600.0, 80),
        (113, 'Bucket Object Storage 100TB Multiregión', 3, 1800.0, 950.0, 150),
        (114, 'Balanceador de Carga Global Anycast', 3, 1200.0, 600.0, 90),
        # Consultoría
        (115, 'Paquete 50 Hrs Consultoría BI & SQL', 4, 7500.0, 4200.0, 30),
        (116, 'Auditoría Arquitectura de Datos Big Data', 4, 15000.0, 8500.0, 18), # < 30
        (117, 'Migración Cloud Zero-Downtime', 4, 22000.0, 13000.0, 10), # < 30
        (118, 'Diseño Gobernanza RBAC & Compliance', 4, 9500.0, 5100.0, 22), # < 30
        # Ciberseguridad
        (119, 'Licencia EDR Endpoint Protection 200 Nodes', 5, 8400.0, 4300.0, 40),
        (120, 'Servicio SOC Gestionado 24/7 Trimestral', 5, 28000.0, 16000.0, 14), # < 30
        (121, 'Simulación Ataques Ransomware & Pentesting', 5, 11000.0, 6200.0, 16), # < 30
        (122, 'Certificado SSL Wildcard EV Multi-Dominio', 5, 850.0, 380.0, 95),
        # Infraestructura
        (123, 'UPS Modular 40kVA Doble Conversión', 6, 16500.0, 11200.0, 9), # < 30
        (124, 'Sensor IoT Temperatura & Humedad Rack', 6, 320.0, 140.0, 140),
        (125, 'Unidad PDU Monitoreable IP 32A', 6, 1400.0, 850.0, 35),
        # SaaS
        (126, 'Plataforma Firma Electrónica Avanzada', 7, 5200.0, 2400.0, 75),
        (127, 'Gateway Correo Seguro Anti-Phishing', 7, 3600.0, 1800.0, 60),
        (128, 'Gestor Contraseñas Empresarial 100 Licencias', 7, 2400.0, 1100.0, 85),
        # Soporte
        (129, 'Póliza Soporte Gold 24/7 Anual', 8, 36000.0, 19500.0, 11), # < 30
        (130, 'Bolsa 100 Horas Soporte Nivel 3', 8, 14000.0, 8200.0, 28)  # < 30
    ]
    cursor.executemany("INSERT INTO dim_productos VALUES (?, ?, ?, ?, ?, ?)", productos_base)

    # -------------------------------------------------------------
    # 3. SEED: dim_clientes (50 clientes con datos PII / sensibles)
    # -------------------------------------------------------------
    sectores = ['Banca & Servicios Financieros', 'Retail & Gran Consumo', 'Logística & Transporte', 'Salud & Clínicas', 'Telecomunicaciones', 'Minería & Energía', 'Seguros & Previsión', 'Gobierno & Sector Público']
    clientes_data = []
    
    nombres_empresas = [
        "Banco de Comercio y Crédito", "Retail Corporativo Global", "Logística & Transportes del Norte", "Clínica Salud Integral",
        "Telecomunicaciones Andinas", "Minera Cobre del Sur", "Seguros & Vida Protección", "Distribuidora Nacional de Alimentos",
        "Farmacéutica BioSalud", "Constructora Metrópolis", "Energías Renovables del Pacífico", "Aseguradora del Valle",
        "Grupo Financiero Santanderino", "Supermercados El Ahorro", "Courier Express Sudamérica", "Hospital Clínico Central",
        "Operadora Móvil Conecta", "Consorcio Portuario Valparaíso", "Inversiones Capital Ventures", "Agroindustria Exportadora",
        "Cadena Hotelera Real", "Automotriz del Pacífico", "Consultora Estratégica Global", "Textil Industrial de Chile",
        "Laboratorios Químicos del Maule", "Fondo Mutuo Futuro Seguro", "E-commerce Express Chile", "Naviera Transoceánica",
        "Servicios Médicos RedSaludable", "Empresa Eléctrica Central", "Caja Compensación Familiar", "Retail Mayorista Austral",
        "Industria Plástica Nacional", "Servicios Financieros Coopeuch", "Clínica Dental Sonrisas", "Televisión Digital Interactiva",
        "Pesquera Austral del Sur", "Siderúrgica del Biobío", "Viña Valle Central", "Corredora de Bolsa Libertad",
        "Distribuidora Eléctrica Norte", "Transportes Interurbanos Cóndor", "Plataforma Logística Biobío", "Red Hospitalaria Privada",
        "Operador Datacenter Edge", "Comercializadora de Granos", "Inmobiliaria Costanera", "Banca Privada Internacional",
        "Cadena Restaurantes Gourmet", "Agencia de Aduanas Unida"
    ]

    random.seed(42)
    for i, emp in enumerate(nombres_empresas, 1):
        rut_num = random.randint(70000000, 99000000)
        dv = random.choice(['0','1','2','3','4','5','6','7','8','9','K'])
        rut_str = f"{rut_num:,}-{dv}".replace(',', '.')
        
        slug = emp.lower().replace(' ', '').replace('&', '').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')[:12]
        email = f"contacto.finanzas@{slug}.corp.cl"
        fono = f"+56 9 {random.randint(4000, 9999)} {random.randint(1000, 9999)}"
        token_cc = f"TOKEN-CC-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-XXXX"
        sector = random.choice(sectores)
        riesgo = random.choice(['BAJO', 'BAJO', 'MEDIO', 'BAJO', 'ALTO'])
        fecha_alta = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 450))).strftime('%Y-%m-%d')
        
        clientes_data.append((i, emp, rut_str, email, fono, token_cc, sector, riesgo, fecha_alta))

    cursor.executemany("INSERT INTO dim_clientes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", clientes_data)

    # -------------------------------------------------------------
    # 4. SEED: fact_ventas (250 transacciones)
    # -------------------------------------------------------------
    ventas_data = []
    metodos_pago = ['TRANSFERENCIA_BANCARIA', 'LINEA_CREDITO_30D', 'ORDEN_COMPRA_60D', 'TARJETA_CORPORATIVA']
    start_date = datetime(2025, 6, 1)

    for v_id in range(1, 251):
        prod = random.choice(productos_base)
        p_id = prod[0]
        precio_u = prod[3]
        costo_u = prod[4]
        
        c_id = random.randint(1, len(nombres_empresas))
        qty = random.randint(1, 8) if precio_u > 5000 else random.randint(3, 20)
        monto = round(qty * precio_u, 2)
        costo = round(qty * costo_u, 2)
        margen = round(monto - costo, 2)
        
        f_venta = (start_date + timedelta(days=random.randint(0, 430), hours=random.randint(8, 18))).strftime('%Y-%m-%d %H:%M:%S')
        metodo = random.choice(metodos_pago)
        estado = 'COMPLETADO' if random.random() > 0.04 else 'EN_PROCESO'
        
        ventas_data.append((v_id, f_venta, p_id, c_id, qty, monto, costo, margen, metodo, estado))

    cursor.executemany("INSERT INTO fact_ventas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ventas_data)

    # -------------------------------------------------------------
    # 5. SEED: fact_ingresos_costos (24 balances mensuales)
    # -------------------------------------------------------------
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    ingresos_costos_data = []
    reg_id = 1
    
    for anio in [2025, 2026]:
        for mes_idx, mes in enumerate(meses, 1):
            ingreso_bruto = round(random.uniform(180000.0, 320000.0) + (mes_idx * 4500), 2)
            costo_op = round(ingreso_bruto * random.uniform(0.52, 0.62), 2)
            impuestos = round(ingreso_bruto * 0.19, 2)
            utilidad_neta = round(ingreso_bruto - costo_op - (impuestos * 0.4), 2)
            
            ingresos_costos_data.append((reg_id, mes, anio, 'Consolidado Corporativo IT & Cloud', ingreso_bruto, costo_op, impuestos, utilidad_neta))
            reg_id += 1

    cursor.executemany("INSERT INTO fact_ingresos_costos VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ingresos_costos_data)

    # -------------------------------------------------------------
    # 6. SEED: dim_empleados (30 empleados con datos confidenciales)
    # -------------------------------------------------------------
    empleados_base = [
        ("Roberto Silva Valenzuela", "Gerente General (CEO)", "Dirección Ejecutiva", 12500.0, 45000.0),
        ("Camila Morales Henríquez", "Directora de Finanzas (CFO)", "Economía & Finanzas", 9800.0, 28000.0),
        ("Felipe Arancibia Lagos", "Director de Tecnología (CTO)", "Tecnología & TI", 9800.0, 28000.0),
        ("Ignacio Vergara Bravo", "Chief Information Security Officer (CISO)", "Tecnología & TI", 8200.0, 18000.0),
        ("Daniela Pizarro Soto", "Gerente Comercial B2B", "Ventas & Clientes", 7500.0, 22000.0),
        ("Matías Castro Fuentes", "Arquitecto Cloud Principal", "Tecnología & TI", 6800.0, 12000.0),
        ("Valentina Rojas Rivas", "Lead Data Scientist", "Economía & Finanzas", 6200.0, 10000.0),
        ("Esteban Muñoz Toro", "Senior Database Administrator (DBA)", "Tecnología & TI", 5500.0, 8000.0),
        ("Sofía Navarrete Peña", "Analista Senior de Riesgo Financiero", "Economía & Finanzas", 4800.0, 6500.0),
        ("Javier Espinoza Carrasco", "Ingeniero DevOps Senior", "Tecnología & TI", 5200.0, 7500.0),
        ("Catalina Herrera Godoy", "Auditora Interna y Compliance", "Economía & Finanzas", 4900.0, 6000.0),
        ("Rodrigo Valdés Miranda", "Senior Backend Engineer", "Tecnología & TI", 4900.0, 6000.0),
        ("Marcela Contreras Pino", "Account Executive Enterprise", "Ventas & Clientes", 4200.0, 15000.0),
        ("Nicolás Farías Leiva", "Especialista Ciberseguridad SOC", "Tecnología & TI", 4600.0, 5500.0),
        ("Patricia San Martín Cruz", "Contadora General Corporativa", "Economía & Finanzas", 4300.0, 5000.0),
        ("Álvaro Araya Olmedo", "Administrador Infraestructura TI", "Tecnología & TI", 4100.0, 4500.0),
        ("Francisca Bustos Riquelme", "Analista Business Intelligence", "Economía & Finanzas", 3800.0, 4000.0),
        ("Gonzalo Oyarzún Vera", "Ingeniero de Redes & Telecom", "Tecnología & TI", 4000.0, 4200.0),
        ("Loreto Salgado Guzmán", "Especialista en Facturación y Cobranza", "Economía & Finanzas", 3200.0, 3000.0),
        ("Gabriel Zúñiga Paredes", "Soporte Técnico Nivel 3", "Tecnología & TI", 3100.0, 2800.0),
        ("Constanza Palma Figueroa", "Ejecutiva Post-Venta y Retención", "Ventas & Clientes", 3000.0, 5000.0),
        ("Cristián Meneses Alarcón", "Ingeniero QA y Automatización", "Tecnología & TI", 3600.0, 3200.0),
        ("Paulina Villegas Cordero", "Analista de Tesorería", "Economía & Finanzas", 3400.0, 3000.0),
        ("Tomás Aguilera Sepúlveda", "Técnico Datacenter Operacional", "Tecnología & TI", 2800.0, 2200.0),
        ("Claudia Donoso Benítez", "Especialista RRHH y Nómina", "Economía & Finanzas", 3300.0, 2900.0),
        ("Alejandro Cárcamo Venegas", "Desarrollador FullStack Jr", "Tecnología & TI", 2900.0, 2000.0),
        ("Bárbara Meza Garrido", "Asistente de Contabilidad", "Economía & Finanzas", 2200.0, 1500.0),
        ("Diego Carvallo Ibáñez", "Operador NOC Turno Noche", "Tecnología & TI", 2600.0, 2400.0),
        ("Fernanda Mellado Campos", "Analista Comercial Jr", "Ventas & Clientes", 2400.0, 3000.0),
        ("Sebastián Lagos Pardo", "Practicante TI & Soporte", "Tecnología & TI", 1200.0, 500.0)
    ]

    empleados_data = []
    for idx, (nom, cargo, depto, sal, bono) in enumerate(empleados_base, 1):
        rut_num = random.randint(11000000, 22000000)
        dv = random.choice(['0','1','2','3','4','5','6','7','8','9','K'])
        rut_emp = f"{rut_num:,}-{dv}".replace(',', '.')
        
        email_emp = f"{nom.split()[0].lower()}.{nom.split()[1].lower()}@corporativo.cl"
        iban = f"CL-BCH-{random.randint(1000,9999)}-{random.randint(10000000,99999999)}"
        score = round(random.uniform(3.8, 5.0), 1)
        f_ing = (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime('%Y-%m-%d')
        
        empleados_data.append((idx, nom, rut_emp, cargo, depto, email_emp, sal, bono, iban, score, f_ing))

    cursor.executemany("INSERT INTO dim_empleados VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", empleados_data)

    # -------------------------------------------------------------
    # 7. SEED: dim_servidores (15 servidores)
    # -------------------------------------------------------------
    servidores_base = [
        (1, 'srv-db-prod-01', '10.0.1.45', '190.114.22.45', 'SECRET-KEY-PROD-DB01', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Primary', 128, 'Esteban Muñoz'),
        (2, 'srv-app-core-02', '10.0.1.46', '190.114.22.46', 'SECRET-KEY-CORE-APP02', 'Red Hat Enterprise Linux 9', 'DC-Santiago-Primary', 64, 'Rodrigo Valdés'),
        (3, 'srv-cloud-proxy-03', '10.0.2.10', '54.232.18.99', 'SECRET-KEY-AWS-PRX03', 'Debian 12', 'DC-AWS-Cloud-UsEast', 32, 'Javier Espinoza'),
        (4, 'srv-backup-node-04', '10.0.3.15', None, 'SECRET-KEY-BKP-VALP04', 'Windows Server 2022', 'DC-Valparaiso-Backup', 256, 'Álvaro Araya'),
        (5, 'srv-k8s-master-01', '10.0.1.50', '190.114.22.50', 'SECRET-KEY-K8S-MST01', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Primary', 64, 'Matías Castro'),
        (6, 'srv-k8s-worker-01', '10.0.1.51', None, 'SECRET-KEY-K8S-WRK01', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Primary', 128, 'Matías Castro'),
        (7, 'srv-k8s-worker-02', '10.0.1.52', None, 'SECRET-KEY-K8S-WRK02', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Primary', 128, 'Matías Castro'),
        (8, 'srv-redis-cache-01', '10.0.1.60', None, 'SECRET-KEY-REDIS-01', 'Alpine Linux 3.19', 'DC-Santiago-Primary', 32, 'Rodrigo Valdés'),
        (9, 'srv-soc-siem-01', '10.0.4.10', '190.114.23.10', 'SECRET-KEY-SOC-SIEM01', 'Rocky Linux 9', 'DC-Santiago-Security', 96, 'Nicolás Farías'),
        (10, 'srv-bi-analytics-01', '10.0.1.75', None, 'SECRET-KEY-BI-ANL01', 'Windows Server 2022', 'DC-Santiago-Primary', 128, 'Valentina Rojas'),
        (11, 'srv-mail-gateway-01', '10.0.2.25', '54.232.19.12', 'SECRET-KEY-MAIL-GTW01', 'Debian 12', 'DC-AWS-Cloud-UsEast', 16, 'Gonzalo Oyarzún'),
        (12, 'srv-storage-san-01', '10.0.3.5', None, 'SECRET-KEY-SAN-STG01', 'FreeBSD 14', 'DC-Valparaiso-Backup', 64, 'Álvaro Araya'),
        (13, 'srv-vpn-corporate-01', '10.0.4.20', '190.114.23.20', 'SECRET-KEY-VPN-CORP01', 'OpenBSD 7.4', 'DC-Santiago-Security', 16, 'Gonzalo Oyarzún'),
        (14, 'srv-auth-keycloak-01', '10.0.1.80', None, 'SECRET-KEY-AUTH-KC01', 'Red Hat Enterprise Linux 9', 'DC-Santiago-Primary', 32, 'Ignacio Vergara'),
        (15, 'srv-monitoring-zabbix', '10.0.4.30', '190.114.23.30', 'SECRET-KEY-MON-ZBX01', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Security', 32, 'Diego Carvallo')
    ]
    cursor.executemany("INSERT INTO dim_servidores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", servidores_base)

    # -------------------------------------------------------------
    # 8. SEED: fact_incidentes_ti (50 incidentes)
    # -------------------------------------------------------------
    fallas_tipos = [
        ('Alta latencia en disco SSD NVMe', 'ALTA', 2.5, 3500.0),
        ('Pico de consumo de memoria RAM (>95%)', 'CRITICA', 1.0, 7500.0),
        ('Reinicio inesperado de daemon de red', 'MEDIA', 0.8, 1200.0),
        ('Falla en tarea cron de respaldo nocturno', 'BAJA', 4.0, 500.0),
        ('Ataque de fuerza bruta SSH mitigado por Fail2ban', 'MEDIA', 0.5, 800.0),
        ('Certificado SSL expirado en subdominio', 'ALTA', 1.5, 4200.0),
        ('Desconexión de nodo en Cluster Kubernetes', 'CRITICA', 0.9, 9000.0),
        ('Espacio en disco /var/log superior al 90%', 'MEDIA', 1.2, 950.0),
        ('Timeout en réplica de base de datos standby', 'ALTA', 2.0, 5100.0),
        ('Pérdida de paquetes en enlace BGP primario', 'CRITICA', 1.8, 12000.0)
    ]

    incidentes_data = []
    for inc_id in range(1, 51):
        falla = random.choice(fallas_tipos)
        srv_id = random.randint(1, 15)
        f_inc = (datetime(2025, 8, 1) + timedelta(days=random.randint(0, 380), hours=random.randint(0, 23))).strftime('%Y-%m-%d %H:%M:%S')
        hrs = round(falla[2] * random.uniform(0.7, 1.4), 1)
        costo_imp = round(falla[3] * random.uniform(0.8, 1.3), 2)
        estado_inc = 'RESUELTO' if random.random() > 0.08 else 'EN_ANALISIS'
        
        incidentes_data.append((inc_id, f_inc, srv_id, falla[0], falla[1], hrs, costo_imp, estado_inc))

    cursor.executemany("INSERT INTO fact_incidentes_ti VALUES (?, ?, ?, ?, ?, ?, ?, ?)", incidentes_data)

    # -------------------------------------------------------------
    # 9. SEED: fact_consumo_recursos (100 mediciones)
    # -------------------------------------------------------------
    consumos_data = []
    base_time = datetime(2026, 8, 10, 8, 0, 0)

    for c_id in range(1, 101):
        srv_id = random.randint(1, 15)
        # Server max ram
        max_ram = next((s[7] for s in servidores_base if s[0] == srv_id), 64)
        
        f_hora = (base_time + timedelta(hours=c_id * 2, minutes=random.randint(0, 50))).strftime('%Y-%m-%d %H:%M:%S')
        cpu = round(random.uniform(15.0, 92.5), 1)
        ram_used = round(max_ram * random.uniform(0.35, 0.88), 1)
        net_mb = round(random.uniform(120.0, 5400.0), 1)
        
        consumos_data.append((c_id, f_hora, srv_id, cpu, ram_used, net_mb))

    cursor.executemany("INSERT INTO fact_consumo_recursos VALUES (?, ?, ?, ?, ?, ?)", consumos_data)

    conn.commit()
    
    # Verify counts
    table_queries = {
        'dim_categorias': "SELECT COUNT(*) FROM dim_categorias",
        'dim_productos': "SELECT COUNT(*) FROM dim_productos",
        'dim_clientes': "SELECT COUNT(*) FROM dim_clientes",
        'fact_ventas': "SELECT COUNT(*) FROM fact_ventas",
        'fact_ingresos_costos': "SELECT COUNT(*) FROM fact_ingresos_costos",
        'dim_empleados': "SELECT COUNT(*) FROM dim_empleados",
        'dim_servidores': "SELECT COUNT(*) FROM dim_servidores",
        'fact_incidentes_ti': "SELECT COUNT(*) FROM fact_incidentes_ti",
        'fact_consumo_recursos': "SELECT COUNT(*) FROM fact_consumo_recursos",
    }
    print("=== BASE DE DATOS CORPORATIVA GENERADA EXITOSAMENTE ===")
    total_recs = 0
    for t, query in table_queries.items():
        count = cursor.execute(query).fetchone()[0]
        total_recs += count
        print(f"-> {t}: {count} registros")
    print(f"TOTAL TOTAL: {total_recs} registros en demo_corporativa.db")
    
    conn.close()

if __name__ == "__main__":
    setup_demo_sqlite()
