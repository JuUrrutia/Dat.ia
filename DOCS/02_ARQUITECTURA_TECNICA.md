# Documento 02: Arquitectura Técnica y Componentes

> **Documento:** 02 - Arquitectura Técnica del Sistema Standalone  
> **Estado:** Especificación Técnica Base  
> **Área:** Ingeniería de Software e Infraestructura  

---

## 1. Visión General de la Arquitectura

El sistema está concebido como una **Aplicación de Escritorio Standalone (Desktop App)** que corre íntegramente de manera local en el equipo o estación de trabajo del usuario. No depende de servidores en la nube ni de servicios externos en internet.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                      APLICACIÓN DE ESCRITORIO STANDALONE                      │
├───────────────────────────────────────────────────────────────────────────────┤
│ 1. CAPA DE INTERFAZ DE USUARIO (DESKTOP UI)                                   │
│    - Panel de Conversación en Lenguaje Natural                                │
│    - Renderizador de Dashboards (Gráficos interactivos + KPIs)                │
│    - Visor de Tablas de Datos Dinámicas                                       │
│    - Panel de Trazabilidad, Auditoría y Diccionario del Dato                  │
│    - Módulo de Administración (Usuarios, Roles, Permisos y Catálogo)          │
├───────────────────────────────────────────────────────────────────────────────┤
│ 2. CAPA DE CONTROL, SEGURIDAD Y GOBERNANZA (BACKEND CORE)                     │
│    - Gestor de Sesiones y Autenticación Local                                 │
│    - Motor de RBAC y Filtrado de Esquemas por Rol                             │
│    - Analizador AST / SQL Guardrail (Parser sintáctico de Solo Lectura)       │
│    - Catálogo Semántico de Datos (Metadatos, Sinónimos, Reglas de Negocio)    │
│    - Base de Datos Local de Configuración (SQLite cifrada / protegida)        │
├───────────────────────────────────────────────────────────────────────────────┤
│ 3. CAPA DE INTELIGENCIA LOCAL (LOCAL LLM ADAPTER)                             │
│    - Conector Agnóstico HTTP/Local (Ollama / llama.cpp / LM Studio / vLLM)    │
│    - Orquestador de Prompts (Inyección dinámica de esquema autorizado)        │
│    - Generador Text-to-SQL + Ciclo de Autocorrección                          │
│    - Generador de Resumen Ejecutivo y Recomendación de Gráficos (Text-to-Viz) │
├───────────────────────────────────────────────────────────────────────────────┤
│ 4. CAPA DE ACCESO A DATOS CORPORATIVOS (DB CONNECTORS POOL)                   │
│    - Conectores Relacionales Nativos: PostgreSQL, MSSQL, MySQL, Oracle        │
│    - Conexiones de Solo Lectura (`READ ONLY`) con Pool de Conexiones          │
│    - Mecanismo de Límites de Filas (Row Limits) y Tiempos de Espera (Timeouts)│
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Descripción Detallada de Capas y Componentes

### 2.1. Capa de Presentación (Desktop UI)
- **Tecnología recomendada:** Framework de escritorio moderno (ej. **Tauri** con frontend web ligero y ultra-rápido en Rust/Webview, o **Electron** / **PyQt**) que garantice una interfaz moderna, fluida y con bajo consumo de memoria RAM.
- **Librerías de Visualización:** Motores de gráficos interactivos ligeros y 100% offline (ej. **Apache ECharts**, **Chart.js** o **Plotly.js**) que no requieren descargas de CDN.
- **Componentes Clave:**
  - **Chat de Consulta:** Entrada de texto con sugerencias de preguntas frecuentes según el rol del usuario.
  - **Dashboard Canvas:** Renderizado dinámico de tarjetas KPI, gráficos temporales/categóricos y comparativas.
  - **Data Grid:** Tabla con ordenamiento, filtrado y paginación rápida para grandes volúmenes de registros devueltos.
  - **Inspector de Trazabilidad:** Modal/Acordeón con la explicación metodológica, descripción de campos y visualización del SQL auditado.

### 2.2. Capa de Backend Core y Gobernanza
- **Gestión de Identidades:** Almacén de credenciales locales (hashing seguro con Argon2/Bcrypt) con caducidad de sesiones locales.
- **Almacén Local de Metadatos:** Base de datos SQLite embebida que guarda:
  - Definición de usuarios y asignación de roles.
  - Matriz de permisos (dominios temáticos, tablas permitidas, columnas enmascaradas).
  - Catálogo semántico (descripción de tablas, nombres amigables de columnas, sinónimos y fórmulas).
  - Historial de auditoría y consultas ejecutadas localmente.
- **Motor SQL Guard (AST Parser):**
  - Utiliza un analizador sintáctico de SQL (ej. `sqlglot` / `sqlparse`).
  - Inspecciona el árbol sintáctico del SQL generado por la IA antes de enviarlo a la base de datos.
  - **Reglas duras:**
    1. Solo permite sentencias que inicien con `SELECT`.
    2. Prohíbe de forma tajante `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `CREATE`, `GRANT`, `REVOKE`.
    3. Extrae todas las tablas y columnas referenciadas en el query y verifica que todas pertenezcan a la lista blanca del rol del usuario.
    4. Inyecta automáticamente límites (`LIMIT` / `TOP`) para evitar desbordes de memoria.

### 2.3. Capa de Inteligencia Local (LLM Adapter)
- **Conector Local Agnóstico:**
  - Conexión vía cliente HTTP local a endpoints como `http://localhost:11434` (Ollama) o `http://localhost:8000/v1` (OpenAI-compatible local server).
  - Soporte para alternar modelos fácilmente desde la configuración (ej. `qwen2.5-coder:7b/14b/32b`, `llama3.3:70b`, `llama3.1:8b`, `deepseek-coder`).
- **Pipeline de Inferencia:**
  1. **Schema Pruning Dinámico:** El backend filtra el catálogo semántico y genera una definición compacta en formato DDL o JSON semántico **únicamente con las tablas y columnas autorizadas para el usuario en sesión**.
  2. **Prompt de Generación SQL:** Se envía la pregunta del usuario + esquema filtrado + reglas de dialecto SQL específico del motor (Postgres, MSSQL, MySQL, Oracle).
  3. **Validación y Retry Loop:** Si el SQL falla la validación AST o la ejecución en BD, el error se realimenta localmente al LLM con un máximo de 2 reintentos para autocorrección.
  4. **Text-to-Viz & Síntesis:** Una vez obtenidos los datos tabulares, un segundo prompt ligero pide al LLM:
     - Tipo de gráfico más idóneo (barras, líneas, dona, KPI).
     - Asignación de ejes (X, Y, serie).
     - Resumen ejecutivo explicando qué revelan los datos en lenguaje de negocio.

### 2.4. Capa de Conectores de Bases de Datos Corporativas
- **Controladores Nativos:**
  - PostgreSQL: `psycopg` / `asyncpg`
  - Microsoft SQL Server: `pyodbc` / `pymssql`
  - MySQL / MariaDB: `pymysql` / `aiomysql`
  - Oracle: `python-oracledb` (modo Thin, sin cliente Oracle pesado)
- **Seguridad en la Conexión:**
  - Usuario de base de datos configurado con privilegios estrictos de solo lectura (`GRANT SELECT`).
  - Timeout de consulta obligatorio (ej. máximo 15 segundos por query para evitar bloqueos en bases de datos productivas).
  - Límite estricto de filas devueltas (ej. máximo 1,000 - 5,000 filas por consulta para visualización en cliente).

---

## 3. Diagrama de Flujo del Pipeline de Consulta

```mermaid
flowchart TD
    A[Usuario ingresa pregunta en lenguaje natural] --> B[Obtener Usuario Activo y Rol]
    B --> C[Filtrar Catálogo Semántico según Permisos de Rol]
    C --> D[Construir Prompt con Esquema Autorizado]
    D --> E[Inferencia LLM Local - Generar SQL]
    E --> F{Validador AST / SQL Guard}
    F -- ¿Consulta No Válida / No Permitida? --> G[Rechazar / Reintento de Autocorrección]
    G --> E
    F -- ¿Consulta Válida y Autorizada? --> H[Ejecutar SQL en BD Corporativa (Solo Lectura)]
    H --> I[Obtener Dataset de Resultados]
    I --> J[Generar Configuración de Gráfico + Resumen de Negocio con LLM]
    J --> K[Renderizar en UI: Dashboard + KPIs + Resumen + Tabla + Trazabilidad]
```

---

## 4. Estrategia de Rendimiento: Soporte Modular CPU vs GPU

| Escenario de Hardware | Configuración de Inferencia | Modelo Recomendado | Rendimiento Esperado |
| :--- | :--- | :--- | :--- |
| **PC / Laptop solo CPU** (8-16 GB RAM) | Ollama / llama.cpp con cuantización `GGUF Q4_K_M` | `qwen2.5-coder:7b-q4` o `llama3.1:8b-instruct-q4` | 8 - 18 tokens/seg (Respuesta en 3-7 seg) |
| **Estación con GPU Media** (RTX 3060/4060 8-12 GB VRAM) | Ollama / llama.cpp con GPU Offloading 100% | `qwen2.5-coder:7b/14b` o `llama3.1:8b` (FP16 / Q8) | 40 - 70 tokens/seg (Respuesta en 1-2 seg) |
| **Servidor con GPU Alta** (RTX 4090 / A5000 / A100 24-80 GB) | vLLM / Ollama con soporte multi-usuario | `qwen2.5-coder:32b`, `deepseek-coder-33b`, `llama3.3:70b-q4` | 60 - 100+ tokens/seg (Alta precisión en SQL complejo) |

---

## 5. Resumen de Seguridad de la Arquitectura

1. **Aislamiento de Red:** Todas las llamadas HTTP de inferencia van a `localhost` o IP de intranet corporativa. Cero tráfico a internet.
2. **Cifrado de Credenciales Locales:** Las cadenas de conexión a las bases de datos corporativas se almacenan cifradas en la base local con clave derivada del sistema (DPAPI en Windows / Secret Service en Linux).
3. **Principio de Mínimo Privilegio:** Ningún componente tiene permisos de escritura sobre las bases de datos de negocio.
