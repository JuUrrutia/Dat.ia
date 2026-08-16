-- ============================================================================
-- BASE DE DATOS CORPORATIVA DE PRUEBA Y ENTRENAMIENTO DE IA LOCAL
-- Dominio 1: Economía & Finanzas / Comercial
-- Dominio 2: Tecnología & TI / Infraestructura
-- ============================================================================

-- DDL: Dominio Economía & Finanzas / Comercial
CREATE TABLE IF NOT EXISTS dim_categorias (
    id_categoria SERIAL PRIMARY KEY,
    nombre_categoria VARCHAR(100) NOT NULL,
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
    rut_dni_cliente VARCHAR(20) NOT NULL, -- Columna Sensible (MASKED)
    sector_industria VARCHAR(100),
    fecha_alta DATE DEFAULT CURRENT_DATE
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


-- DDL: Dominio Tecnología & TI
CREATE TABLE IF NOT EXISTS dim_servidores (
    id_servidor SERIAL PRIMARY KEY,
    nombre_host VARCHAR(100) NOT NULL,
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

-- ============================================================================
-- INSERCIÓN DE DATOS DE PRUEBA (DUMMY DATA)
-- ============================================================================

-- Categorías
INSERT INTO dim_categorias (id_categoria, nombre_categoria, descripcion) VALUES
(1, 'Software Empresarial', 'Licencias de software corporativo y sistemas ERP/CRM'),
(2, 'Hardware & Redes', 'Servidores, switches, laptops corporativas y perifericos'),
(3, 'Servicios Cloud', 'Subscripciones a infraestructura de nube privada e híbrida'),
(4, 'Consultoría & Soporte', 'Horas de servicios profesionales y soporte especializado')
ON CONFLICT DO NOTHING;

-- Productos
INSERT INTO dim_productos (id_producto, nombre_producto, id_categoria, precio_unitario, costo_unitario, stock_disponible) VALUES
(101, 'Licencia ERP Core Enterprise', 1, 25000.00, 12000.00, 50),
(102, 'Servidor Rack 2U Dual Xeon', 2, 8500.00, 5800.00, 15),
(103, 'Instancia Cloud VPC Dedicada', 3, 3200.00, 1800.00, 100),
(104, 'Paquete 50 Hrs Consultoría BI', 4, 7500.00, 4200.00, 30),
(105, 'Switch Gestionable 48 Puertos 10G', 2, 4200.00, 2900.00, 25)
ON CONFLICT DO NOTHING;

-- Clientes
INSERT INTO dim_clientes (id_cliente, nombre_empresa, rut_dni_cliente, sector_industria, fecha_alta) VALUES
(1, 'Banco de Comercio y Crédito', '76.123.456-7', 'Banca & Servicios Financieros', '2025-01-15'),
(2, 'Retail Corporativo Global', '78.987.654-3', 'Retail & Gran Consumo', '2025-02-10'),
(3, 'Logística & Transportes del Norte', '77.456.789-1', 'Logística & Cadena de Suministro', '2025-03-05'),
(4, 'Clínica Salud Integral', '79.111.222-9', 'Salud & Salud Privada', '2025-04-12')
ON CONFLICT DO NOTHING;

-- Ventas (Facturas)
INSERT INTO fact_ventas (fecha_venta, id_producto, id_cliente, cantidad, monto_total, costo_total, margen_ganancia, estado) VALUES
('2026-07-05', 101, 1, 2, 50000.00, 24000.00, 26000.00, 'COMPLETADO'),
('2026-07-12', 102, 3, 4, 34000.00, 23200.00, 10800.00, 'COMPLETADO'),
('2026-07-20', 103, 2, 5, 16000.00, 9000.00, 7000.00, 'COMPLETADO'),
('2026-08-02', 104, 4, 2, 15000.00, 8400.00, 6600.00, 'COMPLETADO'),
('2026-08-10', 101, 2, 1, 25000.00, 12000.00, 13000.00, 'COMPLETADO'),
('2026-08-14', 105, 1, 3, 12600.00, 8700.00, 3900.00, 'COMPLETADO');

-- Ingresos & Costos Financieros Mensuales
INSERT INTO fact_ingresos_costos (mes, anio, categoria_financiera, ingreso_bruto, costo_operativo, utilidad_neta) VALUES
('Enero', 2026, 'Ventas Software & Cloud', 180000.00, 105000.00, 75000.00),
('Febrero', 2026, 'Ventas Software & Cloud', 210000.00, 120000.00, 90000.00),
('Marzo', 2026, 'Ventas Software & Cloud', 245000.00, 135000.00, 110000.00),
('Abril', 2026, 'Ventas Software & Cloud', 195000.00, 115000.00, 80000.00),
('Mayo', 2026, 'Ventas Software & Cloud', 230000.00, 128000.00, 102000.00),
('Junio', 2026, 'Ventas Software & Cloud', 280000.00, 145000.00, 135000.00);

-- Servidores TI
INSERT INTO dim_servidores (id_servidor, nombre_host, ip_interna, sistema_operativo, datacenter, capacidad_ram_gb) VALUES
(1, 'srv-db-prod-01', '10.0.1.45', 'Ubuntu Server 22.04 LTS', 'DC-Santiago-Primary', 128),
(2, 'srv-app-core-02', '10.0.1.46', 'Red Hat Enterprise Linux 9', 'DC-Santiago-Primary', 64),
(3, 'srv-cloud-proxy-03', '10.0.2.10', 'Debian 12', 'DC-AWS-Cloud-UsEast', 32),
(4, 'srv-backup-node-04', '10.0.3.15', 'Windows Server 2022', 'DC-Valparaiso-Backup', 256)
ON CONFLICT DO NOTHING;

-- Incidentes TI
INSERT INTO fact_incidentes_ti (fecha_incidente, id_servidor, tipo_falla, nivel_prioridad, horas_resolucion, estado) VALUES
('2026-08-01 04:15:00', 1, 'Alta latencia en disco SSD', 'ALTA', 2.5, 'RESUELTO'),
('2026-08-03 14:22:00', 2, 'Pico de consumo de memoria RAM (>95%)', 'CRITICA', 1.0, 'RESUELTO'),
('2026-08-08 09:10:00', 3, 'Reinicio inesperado de daemon de red', 'MEDIA', 0.8, 'RESUELTO'),
('2026-08-12 18:45:00', 4, 'Falla en tarea cron de respaldo nocturno', 'BAJA', 4.0, 'RESUELTO');

-- Consumo de Recursos TI
INSERT INTO fact_consumo_recursos (fecha_hora, id_servidor, porcentaje_cpu, uso_ram_gb, trafico_red_mb) VALUES
('2026-08-15 12:00:00', 1, 45.2, 84.5, 1250.0),
('2026-08-15 12:00:00', 2, 78.4, 52.1, 4500.0),
('2026-08-15 12:00:00', 3, 22.0, 14.2, 890.0),
('2026-08-15 12:00:00', 4, 12.5, 98.0, 150.0);
