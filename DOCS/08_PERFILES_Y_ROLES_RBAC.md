# Documento 08: Especificación de Perfiles de Usuario y Matriz de Permisos RBAC

> **Documento:** 08 - Matriz de Perfiles, Roles y Gobernanza de Acceso  
> **Estado:** Aprobado tras Especificación  
> **Área:** Ciberseguridad, Gobernanza y Administración de Accesos  

---

## 1. Visión General de Perfiles

El sistema de **Democratización de Datos Corporativos** implementa un modelo determinístico de Control de Acceso Basado en Roles (RBAC). El acceso no depende de la "voluntad" del LLM, sino de un recortado dinámico de esquema (**Dynamic Schema Pruning**) y un validador sintáctico en backend (**SQL Guardrail en `sqlglot`**).

Todo usuario recién registrado recibe automáticamente el perfil inicial **Usuario** y carece de acceso a datos de la empresa hasta que un **Administrador** le otorgue explícitamente uno de los perfiles operativos autorizados:

```
                               ┌─────────────────────────┐
                               │   NUEVO REGISTRO EN APP │
                               └────────────┬────────────┘
                                            │ Asignación Automática
                                            ▼
                               ┌─────────────────────────┐
                               │     ROL: USUARIO        │
                               │ (Sin acceso a dominios) │
                               └────────────┬────────────┘
                                            │ Evaluación por Administrador
                                            ▼
         ┌──────────────────────────────────┼──────────────────────────────────┐
         │                                  │                                  │
         ▼                                  ▼                                  ▼
┌─────────────────┐                ┌─────────────────┐                ┌─────────────────┐
│ ROL: ECONOMISTA │                │     ROL: TI     │                │ROL: ADMINISTRADOR│
│ • Economía/Finanzas             │ • Infraestructura TI             │ • Gobernanza Total│
│ • Ventas y Márgenes              │ • Servidores & Consumo           │ • Gestión Conexiones│
│ • Facturación                    │ • Tickets & Incidentes           │ • Enriquecimiento IA│
└─────────────────┘                └─────────────────┘                └─────────────────┘
```

---

## 2. Detalle de los 3 Perfiles Principales

### 2.1. Perfil 1: Administrador
- **Propósito:** Gestión global del sistema, gobernanza de datos, administración de usuarios y seguridad.
- **Alcance de Dominio:** Acceso total a todas las herramientas administrativas del sistema.
- **Capacidades Exclusivas:**
  1. Asignar y modificar roles a usuarios registrados.
  2. Registrar, editar y probar conexiones a fuentes de datos corporativas relacionales (PostgreSQL, MSSQL, MySQL, SQLite).
  3. Configurar llaves de cifrado Fernet AES-256 para cadenas de conexión.
  4. Ejecutar la función de **Auto-enriquecimiento con IA** sobre el Catálogo Semántico.
  5. Consultar los registros de auditoría global y trazabilidad de todas las consultas realizadas por los colaboradores.

---

### 2.2. Perfil 2: Economista
- **Propósito:** Explotación de datos analíticos financieros, contables, presupuestarios, comerciales y macro-económicos.
- **Dominio Asignado:** `Economía & Finanzas` y `Operaciones & Comercial`.
- **Tablas Autorizadas:**
  - `fact_ventas`: Registros de facturación y volumen transaccional.
  - `fact_ingresos_costos`: Desglose de ingresos directos y estructura de costos operacionales.
  - `fact_presupuestos`: Comparativas de presupuesto ejecutado vs asignado.
  - `dim_productos` y `dim_categorias`: Catálogo comercial de bienes y servicios.
- **Restricciones & Bloqueos Estrictos:**
  - ❌ **Bloqueo de Infraestructura:** No tiene acceso a tablas de rendimiento de servidores, logs de sistema o incidentes de TI (`fact_incidentes_ti`, `dim_servidores`).
  - 🔒 **Enmascaramiento de Datos Sensibles:** La columna `rut_dni_cliente` y `tarjeta_credito` se presentan enmascaradas (`MASKED`) por lo que solo pueden utilizarse en funciones de agrupación (`COUNT`, `GROUP BY`), impidiendo ver el dato personal individual.

---

### 2.3. Perfil 3: TI (Tecnología de la Información)
- **Propósito:** Monitoreo del estado de salud de la infraestructura tecnológica, consumo de recursos de cómputo, tiempos de respuesta de servidores y gestión de soporte.
- **Dominio Asignado:** `Tecnología & TI`.
- **Tablas Autorizadas:**
  - `fact_incidentes_ti`: Registro de tickets de soporte, severidad, SLA y tiempos de resolución.
  - `dim_servidores`: Catálogo de servidores locales y en nube corporativa, CPU, RAM y almacenamiento.
  - `fact_consumo_recursos`: Métricas periódicas de consumo de ancho de banda, CPU y memoria.
  - `logs_sistema`: Registros de eventos técnicos y alertas.
- **Restricciones & Bloqueos Estrictos:**
  - ❌ **Bloqueo Financiero:** No tiene acceso a estados de resultados, ingresos de negocio, costos operacionales, márgenes de ganancia ni presupuestos (`fact_ingresos_costos`, `fact_presupuestos`).
  - 🔒 **Enmascaramiento de Credenciales:** Las columnas de claves de acceso o firmas hash están totalmente excluidas del árbol sintáctico.

---

### 2.4. Perfil de Bienvenida: Usuario (Por Defecto)
- **Propósito:** Estado inicial de seguridad asignado inmediatamente tras la creación de una cuenta en el sistema.
- **Permisos:** 
  - Puede iniciar sesión y acceder a la interfaz.
  - **Cero tablas autorizadas** en el prompt del LLM. Si intenta formular una pregunta, el sistema le informará amigablemente que su perfil aún no cuenta con un dominio asignado por el Administrador.

---

## 3. Matriz Comparativa de Permisos por Dominio y Tabla

| Dominio | Tabla / Recurso | Rol: Economista | Rol: TI | Rol: Administrador | Rol: Usuario (Inicial) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Finanzas** | `fact_ventas` | ✅ Permitido | ❌ Bloqueado | ✅ Permitido | ❌ Bloqueado |
| **Finanzas** | `fact_ingresos_costos` | ✅ Permitido | ❌ Bloqueado | ✅ Permitido | ❌ Bloqueado |
| **Finanzas** | `fact_presupuestos` | ✅ Permitido | ❌ Bloqueado | ✅ Permitido | ❌ Bloqueado |
| **Comercial** | `dim_productos` | ✅ Permitido | ❌ Bloqueado | ✅ Permitido | ❌ Bloqueado |
| **Comercial** | `dim_clientes` (`rut_dni`) | 🔒 Enmascarado | ❌ Bloqueado | ✅ Permitido | ❌ Bloqueado |
| **TI** | `fact_incidentes_ti` | ❌ Bloqueado | ✅ Permitido | ✅ Permitido | ❌ Bloqueado |
| **TI** | `dim_servidores` | ❌ Bloqueado | ✅ Permitido | ✅ Permitido | ❌ Bloqueado |
| **TI** | `fact_consumo_recursos` | ❌ Bloqueado | ✅ Permitido | ✅ Permitido | ❌ Bloqueado |
| **Gobernanza** | Conexiones BD / RBAC | ❌ Sin acceso | ❌ Sin acceso | ✅ Control Total | ❌ Sin acceso |
