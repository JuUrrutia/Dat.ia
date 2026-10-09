# Documento 08: Especificación de Perfiles de Usuario y Matriz de Permisos RBAC

> **Documento:** 08 - Matriz de Perfiles, Roles y Gobernanza de Acceso  
> **Estado:** Aprobado tras Especificación  
> **Área:** Ciberseguridad, Gobernanza y Administración de Accesos  

---

## 1. Visión General de Perfiles

El sistema de **Democratización de Datos Corporativos** implementa un modelo determinístico de Control de Acceso Basado en Roles (RBAC). El acceso no depende de la "voluntad" del LLM, sino de un recortado dinámico de esquema (**Dynamic Schema Pruning**) y un validador sintáctico en backend (**SQL Guardrail en `sqlglot`**).

Los permisos se otorgan por **responsabilidad funcional**, no por título personal ni por antigüedad. En una organización real el permiso no es de la persona sino del área que responde por el dato: por eso existen ocho roles y no tres.

Todo usuario recién registrado recibe automáticamente el perfil **Usuario Consultor**, con lectura mínima del catálogo. Puede consultar el catálogo de productos y las encuestas, y no ve ni una tabla de negocio, de personal ni de infraestructura. Un **Administrador de Plataforma** puede promoverlo a cualquiera de los roles operativos.

```
                               ┌─────────────────────────┐
                               │   NUEVO REGISTRO EN APP │
                               └────────────┬────────────┘
                                            │ Asignación automática
                                            ▼
                               ┌─────────────────────────┐
                               │  ROL: USUARIO CONSULTOR│
                               │  Solo catalogo + surveys│
                               └────────────┬────────────┘
                                            │ El administrador asigna
                                            ▼
   ┌──────────────┬──────────────┬──────────┴───┬──────────────┬──────────────┬──────────────┐
   ▼              ▼              ▼              ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ ADMIN DE │ │DIRECTOR  │ │ANALISTA  │ │GERENTE   │ │ANALISTA  │ │INGENIERO │ │OFICIAL DE│
│PLATAFORMA│ │ EJECUTIVO │ │FINANCIERO│ │DE TALENTO│ │DE DATOS  │ │ DE       │ │CUMPLIM.  │
│          │ │          │ │& COMERCIAL│ │& OPERAC. │ │& BI      │ │INFRAESTR.│ │& SEGURID.│
│Gobierna  │ │Visión     │ │Ventas,   │ │Clima,    │ │Cruza     │ │Servidores│ │Trazabili-│
│todo      │ │macro,    │ │margenes  │ │encuestas │ │métricas  │ │incidentes│ │dad, DPO  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## 2. Los 8 Roles Corporativos

### 2.1. Administrador de Plataforma
- **Propósito:** Gobierna el producto: roles, conexiones, catálogos y auditoría.
- **Dominio:** Total. Es el único rol con bypass de la matriz de permisos.
- **Capacidades Exclusivas:**
  1. Asignar y modificar roles a usuarios registrados.
  2. Registrar, editar y probar conexiones a fuentes de datos (PostgreSQL, MSSQL, MySQL, SQLite).
  3. Configurar llaves de cifrado Fernet AES-256 para cadenas de conexión.
  4. Ejecutar el **auto-enriquecimiento con IA** sobre el Catálogo Semántico.
  5. Consultar la auditoría global y la trazabilidad de todas las consultas.
  6. Escribir consultas de referencia en la memoria de aprendizaje compartido.

---

### 2.2. Director Ejecutivo (C-Level)
- **Propósito:** Visión macro, rentabilidad consolidada, riesgo de negocio y alertas.
- **Dominio Asignado:** `Economía & Finanzas` (solo el cierre consolidado), `Operaciones & Comercial` (catálogo), `Talento & Personas`.
- **Tablas Autorizadas:** `fact_ingresos_costos`, `dim_categorias`, `dim_productos`, `dim_empleados`, encuestas.
- **Restricciones:**
  - ❌ **Sin el detalle transaccional:** no ve `fact_ventas` ni `dim_clientes`. `fact_ingresos_costos` es un cierre por mes y categoría, no una línea de venta: eso es dirigir. Auditar una operación individual es del área que responde por ella.
  - ❌ **Sin infraestructura:** no ve `dim_servidores`, `fact_incidentes_ti` ni `fact_consumo_recursos`. Un directorio ejecutivo no necesita el CPU de un servidor.
  - ⚠️ **Bypass de dominio:** el guard de dominio lo deja preguntar cualquier tema; lo que lo frena es la matriz de tablas. Si pregunta por servidores, el denegado viene de la capa 1 y no menciona dominio.
  - 🔒 **Ya no está exento de la CLS.** Antes lo estaba junto al admin y le llegaba en claro la tarjeta de crédito, el IBAN y el sueldo. Ahora es el segundo único rol sin columnas sin restringir: solo el Administrador de Plataforma las ve en claro.

---

### 2.3. Analista Financiero & Comercial
- **Propósito:** Ventas, facturación, márgenes y rentabilidad por producto y cliente.
- **Dominio Asignado:** `Economía & Finanzas`, `Operaciones & Comercial`, `Talento & Personas`.
- **Tablas Autorizadas:**
  - `fact_ventas`: facturación y volumen transaccional.
  - `fact_ingresos_costos`: estructura de ingresos y costos operacionales.
  - `dim_clientes`: cartera, con `rut_dni_cliente` enmascarado.
  - `dim_productos`, `dim_categorias`: catálogo comercial.
  - `dim_empleados`: dotación, **sin** remuneraciones.
- **Restricciones:**
  - ❌ **Bloqueo de Infraestructura:** sin servidores, incidentes ni consumo de recursos.
  - 🔒 `tarjeta_credito_token` **bloqueada**; `rut_dni_cliente` y `dim_empleados.rut_dni` **enmascarados**.
  - 🔒 `sueldo_mensual`, `salario_bruto`, `bono_anual` y `cuenta_bancaria_iban` **bloqueados**.

---

### 2.4. Gerente de Talento & Operaciones
- **Propósito:** Clima laboral, encuestas organizacionales, retención y métricas de dotación.
- **Dominio Asignado:** `Talento & Personas`.
- **Tablas Autorizadas:** `dim_empleados`, `Answer`, `Question`, `Survey` (y sus equivalentes en minúscula).
- **Restricciones:**
  - ✅ **Único rol con acceso a remuneraciones:** el guard de dominio le permite preguntar por sueldos, y la matriz no le bloquea las columnas de salario. Es el que legitimamente necesita verlas.
  - ❌ **Sin negocio:** no ve ventas, márgenes, ingresos ni costos.
  - ❌ **Sin infraestructura.**
  - 🔒 `rut_dni` del empleado enmascarado; `cuenta_bancaria_iban` bloqueada.

---

### 2.5. Analista de Datos & BI
- **Propósito:** Exploración multidimensional, cruce de métricas y correlaciones estadísticas.
- **Dominio Asignado:** `Tecnología & TI` y `Operaciones & Comercial` (catálogo).
- **Tablas Autorizadas:** `dim_servidores`, `fact_incidentes_ti`, `fact_consumo_recursos`, `dim_categorias`, `dim_productos`, `dim_empleados`, encuestas.
- **Rationale:** cruza infraestructura con catálogo y personal, y lo hace **sin ver el bloque transaccional**. Un perfil que cruza todas las áreas deja de cruzar áreas: por eso no ve `fact_ventas`, `fact_ingresos_costos` ni `dim_clientes`.
- **Restricciones:**
  - ❌ **Sin finanzas.** Es el corte que define el rol.
  - ⚠️ **El guard de dominio no lo clasifica:** `"Analista de Datos & BI"` no matchea ninguna rama de `check_domain_governance`. Su aislamiento depende por completo de la matriz de tablas. Ver §3.2.
  - 🔒 La CLS de columna le aplica igual, sin bypass de administrador.

---

### 2.6. Ingeniero de Infraestructura & TI
- **Propósito:** Salud de los conectores, consumo de cómputo, latencias e incidentes.
- **Dominio Asignado:** `Tecnología & TI`, `Talento & Personas`.
- **Tablas Autorizadas:**
  - `dim_servidores`: catálogo de servidores, CPU, RAM, datacenter.
  - `fact_incidentes_ti`: tickets, severidad, SLA y tiempos de resolución.
  - `fact_consumo_recursos`: CPU, RAM y tráfico de red.
  - `dim_empleados`: sólo para saber a quién escalar, sin remuneraciones.
- **Restricciones:**
  - ❌ **Bloqueo Financiero:** sin ventas, márgenes, ingresos ni costos. El guard de dominio además rechaza preguntas con vocabulario financiero.
  - 🔒 `api_key_servicio` **bloqueada**: una API key es una credencial contra los propios servidores, un secreto para todo rol no-admin. Que alguien sea de TI no lo hace menos técnico.

---

### 2.7. Oficial de Cumplimiento & Seguridad (DPO)
- **Propósito:** Vigilancia de trazabilidad, cumplimiento normativo y auditoría de accesos.
- **Dominio Asignado:** `Seguridad & Gobernanza`, `Tecnología & TI`, `Talento & Personas`, `Operaciones & Comercial` (catálogo).
- **Tablas Autorizadas:** `dim_servidores`, `fact_incidentes_ti`, `fact_consumo_recursos`, `dim_empleados`, `dim_categorias`, `dim_productos`, encuestas.
- **Restricciones:**
  - ❌ **Sin márgenes:** no ve `fact_ventas` ni `fact_ingresos_costos`. Auditar accesos y trazabilidad no requiere conocer la rentabilidad.
  - ⚠️ **No tiene bypass de dominio:** su cobertura la da íntegramente la matriz de tablas, que es el comportamiento correcto para un oficial de cumplimiento.

---

### 2.8. Usuario Consultor (Por Defecto)
- **Propósito:** Perfil inicial de quien se registra sin autoridad asignada.
- **Tablas Autorizadas:** `dim_categorias`, `dim_productos` y encuestas. Lectura mínima real.
- **Restricciones:**
  - ❌ Cero tablas de negocio, personal o infraestructura.
  - 🔒 Toda la CLS de columna le aplica.

> **Nota sobre el gate de "sin rol":** el corte por ausencia de rol en `/chat/query` y `/predict` verifica `not current_user.role`, **no** el nombre del rol. Antes se disparaba con `role == ROLE_USUARIO`, lo que dejaba al Consultor como un perfil que no podía hacer nada y lo convertía en un callejón sin salida.

---

## 3. Matriz Comparativa de Permisos por Dominio y Tabla

`✅` permitido · `🔒` enmascarado o bloqueado a nivel de columna · `❌` sin acceso a la tabla

| Dominio | Tabla / Recurso | Admin | Director | Financiero | Talento | BI | Ingeniero TI | Cumplimiento | Consultor |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Finanzas** | `fact_ventas` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Finanzas** | `fact_ingresos_costos` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Finanzas** | `dim_clientes` | ✅ | ❌ | 🔒 rut | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Comercial** | `dim_productos` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Comercial** | `dim_categorias` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Talento** | `dim_empleados` | ✅ | 🔒 salario | 🔒 salario | ✅ | 🔒 salario | 🔒 salario | 🔒 salario | ❌ |
| **TI** | `dim_servidores` | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **TI** | `fact_incidentes_ti` | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **TI** | `fact_consumo_recursos` | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Encuestas** | `Survey` / `Answer` / `Question` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Gobernanza** | Conexiones BD / RBAC / auditoría | ✅ Total | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 3.1. Dónde NO cruza ningún rol

`test_ningun_rol_trae_las_tablas_de_otro_area` fija, tabla por tabla, que ninguna pareja se pisa. El resultado declarado:

| Verificación | Resultado |
| :--- | :--- |
| El Analista de Datos ve el bloque transaccional (`fact_ventas`, `fact_ingresos_costos`, `dim_clientes`) | ❌ no |
| El Analista Financiero ve infraestructura (`dim_servidores`, `fact_incidentes_ti`, `fact_consumo_recursos`) | ❌ no |
| El Ingeniero de TI ve el bloque transaccional | ❌ no |
| El Gerente de Talento ve negocio o infraestructura | ❌ no |
| El Oficial de Cumplimiento ve márgenes de venta | ❌ no |
| El Director Ejecutivo ve `fact_ventas` (detalle transaccional) | ❌ no |
| El Usuario Consultor ve `dim_empleados` | ❌ no |

### 3.2. Las dos parejas que comparten tablas, y por qué

Ninguna comparte el bloque transaccional con nadie. Dos pares sí comparten tablas, y la separación está en otra capa:

- **Analista de Datos ≡ Ingeniero de TI** — ambos sobre métricas técnicas. Difieren en la **capa 2**: el nombre `"Ingeniero de Infraestructura & TI"` matchea la rama técnica de `check_domain_governance` y recibe un denegado temprano sobre preguntas financieras; `"Analista de Datos & BI"` no matchea ninguna rama, porque es un perfil transversal. Es el único punto del aislamiento que depende del *nombre* del rol, así que un cambio de nombre en `constants.py` lo puede borrar en silencio — `test_bi_y_ti_se_diferencian_en_el_guard` lo vigila.
- **Analista de Datos ≈ Oficial de Cumplimiento** — mismo alcance técnico; difieren en la capa 3 (columnas) y en el propósito: el DPO no ve el bloque transaccional.

---

## 4. Las Tres Capas de Gobernanza

Cada capa frena por su cuenta. El aislamiento no depende de ninguna en particular.

| # | Capa | Dónde | Qué frena | Modo de fallo |
| :-- | :--- | :--- | :--- | :--- |
| 1 | **Matriz de permisos** | `role_table_permissions` | Qué tablas existen para el rol. Prunea el esquema antes del prompt. | Un rol con permiso de más ve datos de otro área. |
| 2 | **Guard de dominio** | `governance_guard.check_domain_governance` | El *tema* de la pregunta, por vocabulario. Capa de defensa temprana: evita gastar una llamada al LLM. |Es coincidencia de palabras: se escapa con sinónimos, y los roles nuevos no matchean ninguna rama. |
| 3 | **Validador AST** | `ast_validator` (`sqlglot`) | El SQL generado. Rechaza tablas no autorizadas y columnas bloqueadas. | Es la única capa que ve la consulta real, no la intención. |

**Por qué las tres hacen falta.** La capa 2 es la que da el mensaje útil ("su perfil no tiene autorización para información financiera"), pero es la más débil: es coincidencia de palabras. Si un rol nuevo no matchea ninguna rama, la pregunta sigue de largo — y ahí siguen las capas 1 y 3, que no dependen de vocabulario. Verificado: el Gerente de Talento tiene bypass del guard para preguntas de negocio, pero su SQL contra `fact_ventas` lo rechaza el AST con `Gobernanza RBAC: Acceso denegado`.

---

## 5. Origen de los Datos

| Concepto | Fuente única de verdad |
| :--- | :--- |
| Nombres de los 8 roles (backend) | `backend/app/core/constants.py` |
| Tablas por rol (matriz sembrada) | `backend/app/db/init_db.py` → `role_matrix` |
| Cuentas de la demo | `backend/app/db/init_db.py` → `demo_users` |
| Badge y metadatos de rol (frontend) | `src/constants/index.ts` → `CORPORATE_ROLES` |
| Perfiles del login (frontend) | `src/pages/LoginPage.tsx` → `DEMO_PROFILES` |

El frontend toma los **nombres** de rol de `CORPORATE_ROLES` y solo mantiene localmente los usernames y contraseñas de la demo, que el backend siembra.

**Migración de alias.** Existieron cuatro roles alias (`Administrador`, `Economista`, `TI`, `Usuario`) que duplicaban un rol corporativo con otro nombre. `init_db` corre `_migrate_role_aliases` en cada arranque: reasigna usuarios y permisos al corporativo y borra la fila del alias. Es idempotente, nunca amplía acceso ante discrepancias, y si el corporativo destino no existe deja el alias intacto y avisa.

---

## 6. Restricciones Comunes (CLS)

Aplicadas a **todos** los roles salvo el **Administrador de Plataforma**. El Director Ejecutivo dejó de estar exento: antes lo estaba (`~Role.name.in_([ADMIN, DIRECTOR_EJECUTIVO])`) y por eso le llegaba en claro la tarjeta de crédito, el IBAN y el sueldo del empleado. Mirar rentabilidad global no requiere ver el instrumento de pago de un cliente ni la cuenta bancaria de una persona: un C-Level dirige sobre agregado, y el detalle identificable es del área que responde por el dato.

Único rol con acceso a remuneraciones: el **Gerente de Talento & Operaciones**, que es el área responsable.

| Columna | Veredicto | Motivo |
| :--- | :--- | :--- |
| `dim_clientes.rut_dni_cliente` | `MASKED` | Identidad del cliente: consultable en agregados, no en detalle. |
| `dim_clientes.tarjeta_credito_token` | `BLOCKED` | Instrumento de pago. |
| `dim_servidores.api_key_servicio` | `BLOCKED` | Credencial contra los propios servidores. Un secreto para todo rol no-admin, RRHH incluido. |
| `dim_empleados.rut_dni` | `MASKED` | Misma clase de dato que el del cliente. |
| `dim_empleados.sueldo_mensual`, `salario`, `salario_bruto`, `bono_anual` | `BLOCKED` | Remuneración individual. El único rol que los ve es el Gerente de Talento, por necesidad legítima. |
| `dim_empleados.cuenta_bancaria_iban` | `BLOCKED` | Cuenta bancaria. |

Se siembran **todos** los nombres de columna que usan las demos: las dos demos no coinciden entre sí (`sueldo_mensual` en PostgreSQL, `salario_bruto` en SQLite), y una lista por motor dejaba la columna sin clasificar en la otra — es decir, servida en claro a cualquier rol.

---

*Fin del Documento 08.*