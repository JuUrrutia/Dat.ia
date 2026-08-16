# Documento 03: Sistema de Permisos, Gobernanza y Seguridad (RBAC)

> **Documento:** 03 - Gobernanza de Datos y Seguridad de Acceso  
> **Estado:** Especificación Técnica Aprobada  
> **Área:** Ciberseguridad y Gobernanza de Datos  

---

## 1. Objetivos de Seguridad

El sistema maneja datos confidenciales y sensibles de la organización. Su arquitectura de seguridad garantiza tres principios fundamentales:
1. **Confidencialidad Estricta:** Un usuario solo puede formular preguntas y ver resultados sobre datos que su rol le autoriza explícitamente.
2. **Integridad de Datos:** Imposibilidad técnica absoluta de alterar, borrar o insertar datos en las bases de datos corporativas.
3. **Resistencia a Ataques de IA (Prompt Injection / Jailbreaks):** La seguridad no recae en que el LLM "prometa obedecer", sino en filtros determinísticos a nivel de código y base de datos.

---

## 2. Modelo de Control de Acceso Basado en Roles (RBAC)

El sistema implementa un modelo jerárquico y granular de permisos:

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO CORPORATIVO                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ Pertenece a 1 o más
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      ROL DE ACCESO                          │
│        (Ej: "Analista Financiero", "Jefe de Ventas")        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Define permisos sobre
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   DOMINIOS / MÓDULOS DE NEGOCIO             │
│        (Ej: Finanzas, Ventas, Logística, RRHH)              │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
 ┌───────────────────────────┐   ┌───────────────────────────┐
 │     TABLAS AUTORIZADAS    │   │    POLÍTICA DE COLUMNAS   │
 │ (Lista blanca de tablas   │   │ - Permitidas              │
 │  accesibles por el rol)   │   │ - Bloqueadas / Ocultas    │
 │                           │   │ - Enmascaradas (Hashing)  │
 └───────────────────────────┘   └───────────────────────────┘
```

---

## 3. Niveles de Granularidad de Seguridad

### 3.1. Nivel de Dominio / Módulo Temático
- Agrupa tablas por área de negocio (ej. Dominio *Finanzas*, Dominio *Comercial*, Dominio *Recursos Humanos*).
- Si un rol no tiene asignado el dominio *Recursos Humanos*, el sistema actúa como si dicho dominio no existiera en la empresa.

### 3.2. Nivel de Tabla
- Permite especificar dentro de un dominio qué tablas concretas puede consultar el usuario (ej. dentro de *Comercial*, puede ver `fact_ventas` y `dim_productos`, pero no `dim_comisiones_vendedores`).

### 3.3. Nivel de Columna (Enmascaramiento y Bloqueo)
- **Columnas Permitidas:** Visibles y utilizables para filtros y agregaciones.
- **Columnas Bloqueadas:** Se eliminan por completo de la definición semántica que ve el LLM. Si el SQL generado las incluye, el Validador AST aborta la consulta.
- **Columnas Enmascaradas (Masked):** Columnas que pueden usarse para contar o agrupar pero cuyo valor individual sensible no se expone (ej. `Rut/DNI`, `Número de Tarjeta`, `Correo Personal`).

---

## 4. Matriz de Permisos de Ejemplo

| Dominio | Tabla | Columna Sensible | Rol: Analista Finanzas | Rol: Ejecutivo Comercial | Rol: Gerente RRHH | Rol: Administrador |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Finanzas** | `fact_ingresos` | `monto_total` | ✅ Permitido | ❌ Bloqueado | ❌ Bloqueado | ✅ Permitido |
| **Finanzas** | `fact_costos` | `costo_operativo` | ✅ Permitido | ❌ Bloqueado | ❌ Bloqueado | ✅ Permitido |
| **Ventas** | `fact_ventas` | `margen_bruto` | ✅ Permitido | ✅ Permitido | ❌ Bloqueado | ✅ Permitido |
| **Ventas** | `dim_clientes` | `rut_dni_cliente` | 🔒 Enmascarado | 🔒 Enmascarado | ❌ Bloqueado | ✅ Permitido |
| **RRHH** | `dim_empleados` | `salario_base` | ❌ Bloqueado | ❌ Bloqueado | ✅ Permitido | ✅ Permitido |
| **RRHH** | `dim_empleados` | `cargo_area` | ❌ Bloqueado | ❌ Bloqueado | ✅ Permitido | ✅ Permitido |

---

## 5. Arquitectura de Defensa en Profundidad (Defense in Depth)

La seguridad se aplica en **3 capas consecutivas e independientes**:

```
[ Pregunta del Usuario ]
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. PRIMERA BARRERA: Dynamic Schema Pruning (Prompt LLM)     │
│    El catálogo enviado al LLM solo contiene metadatos de   │
│    las tablas/columnas permitidas. La IA desconoce que      │
│    existen tablas de RRHH si el usuario es de Finanzas.     │
└──────────────────────────┬──────────────────────────────────┘
                           │ Genera SQL candidato
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SEGUNDA BARRERA: Validador AST / Parser Sintáctico       │
│    Backend analiza el árbol sintáctico del SQL:             │
│    - ¿Inicia estrictamente con SELECT?                      │
│    - ¿Contiene tablas o columnas fuera de la lista blanca?  │
│    - ¿Intenta ejecutar subconsultas o funciones prohibidas? │
│    - Si detecta anomalías -> ABORTA la ejecución.           │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQL Aprobado
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TERCERA BARRERA: Conexión de Base de Datos Solo Lectura  │
│    El usuario de conexión en PostgreSQL / SQL Server /      │
│    Oracle tiene privilegios únicos de SELECT en BD.         │
│    Cero permisos de INSERT, UPDATE, DELETE, EXEC.           │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Especificación del Validador AST (SQL Guardrail)

El analizador sintáctico opera mediante las siguientes reglas determinísticas antes de tocar la base de datos:

1. **Sentencias Únicas:** Solo se permite una única sentencia SQL por ejecución. Bloquea el encadenamiento de comandos mediante punto y coma (`;`).
2. **Solo `SELECT`:** Cualquier token relacionado con DDL o DML de modificación (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, `EXEC`, `GRANT`, `REVOKE`) produce el rechazo inmediato de la consulta.
3. **Validación de Tablas Referenciadas:** Se extraen todos los identificadores de tablas del AST y se comparan contra `tablas_autorizadas_del_rol`.
4. **Validación de Columnas Referenciadas:** Se extraen todas las columnas presentes en `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `HAVING` y se comprueba que ninguna corresponda a una columna bloqueada.
5. **Inyección Obligatoria de Límite de Filas:** Si la consulta carece de cláusula `LIMIT` (o `TOP` en MSSQL), el validador la inyecta automáticamente con el valor máximo permitido por configuración (ej. `LIMIT 2000`).

---

## 7. Registro de Auditoría y Trazabilidad (Audit Logs)

Para cumplimiento corporativo, cada interacción se registra localmente en la base de datos de auditoría interna con la siguiente estructura:

| Campo | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `id_log` | Identificador único de auditoría | `aud_882910` |
| `timestamp` | Fecha y hora exacta local | `2026-08-15 12:30:15` |
| `user_id` | Identificador del usuario que consultó | `usr_felipe` |
| `user_role` | Rol activo durante la consulta | `analista_finanzas` |
| `user_prompt` | Pregunta formulada en lenguaje natural | "¿Cuáles fueron las ventas de julio?" |
| `sql_generated` | Sentencia SQL producida por la IA | `SELECT SUM(monto) FROM fact_ventas WHERE...` |
| `validation_status` | Resultado de la validación AST | `APROBADO` / `RECHAZADO_TABLA_NO_PERMITIDA` |
| `execution_time_ms` | Tiempo de respuesta en milisegundos | `145 ms` |
| `rows_returned` | Cantidad de filas devueltas | `1 fila` |

Este registro garantiza que los administradores puedan auditar qué usuarios consultan qué datos y detectar posibles intentos de acceso no autorizado.
