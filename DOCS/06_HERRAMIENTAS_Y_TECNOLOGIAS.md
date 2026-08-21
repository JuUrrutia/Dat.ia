# Documento 06: Especificación de Herramientas y Tecnologías

> **Documento:** 06 - Stack Tecnológico, Justificación y Propósito  
> **Estado:** Aprobado tras Alineación Técnica (`/grill-me`)  
> **Área:** Arquitectura de Software e Infraestructura  

---

## 1. Visión General del Stack Tecnológico

El sistema se ha diseñado bajo la premisa no negociable de **operación 100% offline (standalone), costo cero en licencias de IA y máxima seguridad/gobernanza**. A continuación se detallan las herramientas seleccionadas, justificando en cada caso **el porqué** de su elección y **el para qué** dentro del ecosistema.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            STACK TECNOLÓGICO                                │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ FRONTEND & DESKTOP SHELL             │ BACKEND & ENGINE DE SEGURIDAD        │
│ • Electron + React + Vite + TS       │ • Python 3.11/3.12 + FastAPI         │
│ • Apache ECharts + Tailwind CSS      │ • SQLGlot (AST Security Guardrail)   │
│ • Lucide Icons                       │ • SQLAlchemy 2.0 + PyPika/Pydantic   │
│                                      │ • Cryptography (Fernet AES-256)      │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ MOTOR DE IA & CONECTORES BD          │ BASE DE DATOS DE METADATOS           │
│ • Conector HTTP (Ollama / Local API) │ • PostgreSQL / SQLite (Persistencia) │
│ • Drivers BD: psycopg (binary),      │ • Argon2 / bcrypt (Hashing Auth)     │
│   pymysql, sqlite3, pymssql          │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Capa de Presentación y Escritorio (Frontend & Desktop Shell)

### 2.1. Electron
- **¿Qué es?:** Framework de código abierto que permite crear aplicaciones de escritorio multiplataforma (Windows, macOS, Linux) combinando el motor Chromium (UI) y Node.js.
- **¿Por qué se eligió?:** 
  - Permite empaquetar una aplicación web moderna como un ejecutable nativo standalone 100% offline.
  - Ofrece integración nativa con el sistema operativo para gestionar ventanas, IPC (Inter-Process Communication) seguro y la ejecución controlada de subprocesos secundarios (Sidecar).
- **¿Para qué se usa en el proyecto?:**
  - Actúa como la envoltura de escritorio principal (Desktop Shell).
  - Lanza, supervisa y detiene de forma transparente el servidor backend local en Python (FastAPI).
  - Garantiza que la aplicación funcione aislada de internet sin depender de un navegador externo.

### 2.2. React 18 / 19 & TypeScript
- **¿Qué es?:** React es la librería declarativa basada en componentes líder para la construcción de interfaces. TypeScript es un superconjunto de JavaScript que añade tipado estático.
- **¿Por qué se eligieron?:**
  - **React:** Facilita la creación de componentes reactivos reutilizables (chat conversacional, tablas dinámicas, modales de trazabilidad) y garantiza una actualización eficiente del DOM.
  - **TypeScript:** Elimina errores en tiempo de desarrollo al definir interfaces estrictas para los payloads API, datos de consultas y respuestas del LLM.
- **¿Para qué se usan en el proyecto?:**
  - Desarrollar la interfaz gráfica de usuario completa (panel de chat, renderizador de dashboards, visor de datos y panel de administración RBAC).

### 2.3. Vite
- **¿Qué es?:** Herramienta de compilación y servidor de desarrollo frontend de nueva generación, impulsado por esbuild.
- **¿Por qué se eligió?:**
  - Ofrece recarga en caliente instantánea (HMR) durante la fase de desarrollo y una empaquetación de producción ligera y optimizada.
- **¿Para qué se usa en el proyecto?:**
  - Orquestar la compilación del código React/TypeScript hacia los archivos estáticos consumidos por Electron.

### 2.4. Apache ECharts (`echarts-for-react`)
- **¿Qué es?:** Potente librería de visualización de datos interactiva renderizada mediante Canvas/SVG.
- **¿Por qué se eligió?:**
  - **100% Offline:** No requiere conexión a CDNs ni descarga de fuentes o scripts externos.
  - **Alto Rendimiento:** Renderiza miles de puntos de datos con fluidez, soportando zoom, leyendas dinámicas y animaciones fluidas.
  - **Exportación Local:** Permite al usuario exportar cualquier gráfico renderizado a formato PNG o SVG con un clic.
- **¿Para qué se usa en el proyecto?:**
  - Renderizar los gráficos analíticos dinámicos (barras, líneas, donas, áreas, métricas KPI) recomendados por la IA en cada consulta.

### 2.5. Tailwind CSS & Lucide Icons
- **¿Qué es?:** Tailwind CSS es un framework CSS orientado a clases utilitarias. Lucide es una colección de íconos vectoriales limpios y consistentes.
- **¿Por qué se eligieron?:**
  - Permiten construir una interfaz ejecutiva elegante en modo oscuro (Dark Mode), con efectos de cristal (glassmorphism) y alta densidad de información sin lidiar con hojas de estilo desordenadas.
- **¿Para qué se usan en el proyecto?:**
  - Diseñar la identidad visual, tipografía, paleta de colores, tarjetas KPI y botones interactivos de toda la aplicación.

---

## 3. Capa de Backend y Motor de Gobernanza (Python FastAPI Core)

### 3.1. Python 3.11 / 3.12 & FastAPI
- **¿Qué es?:** Python es un lenguaje de programación de alto nivel. FastAPI es un framework web asíncrono de alto rendimiento basado en estándares abiertos (OpenAPI y JSON Schema).
- **¿Por qué se eligieron?:**
  - **Python:** Es el ecosistema estándar para análisis sintáctico de SQL (`sqlglot`), manipulación de datos y conectividad con modelos de IA.
  - **FastAPI:** Ofrece validación automática de datos con Pydantic, soporte asíncrono (`async/await`) nativo y latencia extremadamente baja en comunicación `localhost`.
- **¿Para qué se usan en el proyecto?:**
  - Crear el servidor local Sidecar que atiende las peticiones del frontend Electron.
  - Orquestar la autenticación, la consulta de datos corporativos, el filtrado RBAC y el pipeline de inferencia LLM.

### 3.2. `sqlglot` (SQL AST Guardrail & Parser)
- **¿Qué es?:** Analizador sintáctico (AST Parser), transpilador y evaluador de expresiones SQL en Python.
- **¿Por qué se eligió?:**
  - Es infinitamente superior a las expresiones regulares (Regex) frágiles. Comprende la gramática real de múltiples dialectos SQL (PostgreSQL, T-SQL/MSSQL, MySQL, Oracle).
  - Permite manipular programáticamente el árbol de sintaxis abstracta (AST) para validar o alterar consultas antes de su ejecución.
- **¿Para qué se usa en el proyecto?:**
  - **Inspección de Seguridad:** Verifica que la consulta generada por el LLM sea estrictamente de tipo `SELECT`.
  - **Filtrado RBAC:** Comprueba que todas las tablas y columnas en la consulta pertenezcan a la lista blanca del rol del usuario.
  - **Inyección Automática:** Agrega la cláusula de límite de filas (`LIMIT` o `TOP`) adecuada según el motor de base de datos para evitar desbordes de memoria.

### 3.3. SQLAlchemy 2.0 & SQLModel
- **¿Qué es?:** SQLAlchemy es el ORM (Object-Relational Mapper) y SQL Toolkit estándar de Python. SQLModel combina SQLAlchemy con Pydantic.
- **¿Por qué se eligieron?:**
  - Proporcionan una abstracción segura y tipada para la interacción con la base de datos relacional de metadatos, evitando inyecciones SQL en la gestión interna de la app.
- **¿Para qué se usan en el proyecto?:**
  - Administrar la estructura y consultas sobre la base de datos de metadatos del sistema (usuarios, roles, permisos, catálogo semántico y auditoría).

### 3.4. Drivers Nativos de Base de Datos Corporativas
- **Librerías:**
  - **PostgreSQL:** `psycopg[binary]` (v3)
  - **SQLite:** `sqlite3` (Librería estándar nativa de Python)
  - **MySQL / MariaDB:** `pymysql` (Conector puro Python sin dependencias C complejas)
  - **Microsoft SQL Server:** `pymssql` / `pyodbc`
- **¿Por qué se eligieron?:**
  - Son los conectores certificados de mejor rendimiento y máxima portabilidad multiplataforma aprobados para cada motor relacional soportado.
- **¿Para qué se usan en el proyecto?:**
  - Establecer conexiones seguras en modo **Solo Lectura (`READ ONLY`)** a las fuentes de datos corporativas para extraer únicamente los datasets requeridos por las preguntas del usuario.

### 3.5. Registro de Decisión de Arquitectura: Exclusión Deliberada de Oracle (ADR-001)

> **ADR-001: Exclusión Deliberada del Driver Oracle (`python-oracledb` / `oracledb`)**
> 
> * **Estado:** Decisión Aprobada y Aplicada
> * **Contexto:** En el diseño inicial se contempló `python-oracledb`. Al evaluar la distribución de la aplicación como un ejecutable de escritorio standalone 100% offline para usuarios corporativos en Windows, macOS y Linux, se analizó el impacto de las dependencias nativas.
> * **Decisión:** Excluir intencionalmente `python-oracledb` de `requirements.txt` y del scope de drivers activos del instalador standalone.
> * **Justificación Técnica:**
>   1. **Portabilidad y Despliegue Zero-Config:** `python-oracledb` y Oracle Instant Client requieren librerías de enlace dinámico nativas (`.dll`, `.so`, `.dylib`) y configuraciones de entorno (`ORACLE_HOME`, `PATH`) que frecuentemente provocan fallos de instalación en entornos desktop sin privilegios de administrador.
>   2. **Garantía de Binarios Universales (Universal Wheels):** Los motores soportados (**PostgreSQL**, **SQLite**, **MySQL/MariaDB**, **SQL Server**) cuentan con ruedas precompiladas autónomas (`psycopg[binary]`, `pymysql`, `sqlite3`) que no requieren compiladores C++ ni runtimes externos en la máquina del usuario final.
>   3. **Costo de Mantenimiento y Cobertura de Mercado:** El 95%+ de las necesidades de democratización de datos analíticos se satisfacen con PostgreSQL, MySQL, SQL Server y SQLite, manteniendo la base de código ligera y libre de librerías propietarias pesadas.

### 3.6. Cryptography (Fernet AES-256) & Argon2
- **¿Qué es?:** Módulos estándar de ciberseguridad para cifrado simétrico y hashing seguro de contraseñas.
- **¿Por qué se eligieron?:**
  - Garantizan que las contraseñas de los usuarios no se puedan revertir y que las credenciales de conexión a las BDs de la empresa estén protegidas contra lectura no autorizada en el almacenamiento local.
- **¿Para qué se usan en el proyecto?:**
  - **Argon2 / bcrypt:** Hash de contraseñas de inicio de sesión de usuarios.
  - **Fernet (AES-256):** Cifrado de cadenas de conexión y claves de base de datos almacenadas en la base de metadatos PostgreSQL.

---

## 4. Persistencia Interna y Motor de IA Local

### 4.1. Base de Datos PostgreSQL / SQLite (Persistencia de Metadatos)
- **¿Qué es?:** Sistema de gestión de bases de datos relacional robusto y de alta confiabilidad.
- **¿Por qué se eligió?:**
  - Ofrece soporte avanzado para tipos de datos JSON, excelente rendimiento en concurrencia y estricto cumplimiento ACID.
  - Permite almacenar estructuras complejas como la matriz RBAC por columna y grandes volúmenes de registros de auditoría sin degradación.
- **¿Para qué se usa en el proyecto?:**
  - Servir como la **Base de Datos Interna del Sistema**, almacenando:
    1. Cuentas de usuarios y hashes de contraseñas.
    2. Roles y Matriz de Permisos RBAC.
    3. Cadenas de conexión cifradas a bases de datos corporativas.
    4. Catálogo Semántico de Datos (descripciones, sinónimos, fórmulas de negocio).
    5. Historial y Logs de Auditoría (preguntas, SQL auditado, latencia, resultados).

### 4.2. Conector HTTP Agnóstico de IA Local (Ollama / Local API)
- **¿Qué es?:** Módulo cliente HTTP de Python (`httpx` / `requests`) que interactúa con endpoints de inferencia local (`http://localhost:11434` o `http://localhost:8000/v1`).
- **¿Por qué se eligió?:**
  - **Agnóstico y Desacoplado:** No amarra la aplicación a un software o modelo en particular. El usuario puede correr **Ollama**, **LM Studio**, **llama.cpp server** o **vLLM**.
  - Permite alternar con facilidad entre modelos abiertos de vanguardia (*Qwen 2.5 Coder*, *Llama 3.1*, *DeepSeek*) según la capacidad de hardware del equipo (CPU vs GPU).
- **¿Para qué se usa en el proyecto?:**
  - Inferencia Text-to-SQL (traducción de lenguaje natural a consulta SQL autorizada).
  - Inferencia Text-to-Viz (recomendación de gráfico y redacción del resumen ejecutivo de negocio).
  - Auto-enriquecimiento inteligente de descripciones y sinónimos en el Catálogo Semántico.

---

## 5. Cuadro Resumen de Herramientas

| Herramienta | Capa | ¿Por qué? (Justificación) | ¿Para qué? (Propósito) |
| :--- | :--- | :--- | :--- |
| **Electron** | Desktop Shell | Multiplataforma, empaqueta app web 100% offline y gestiona subprocesos. | Ejecutable standalone de escritorio y gestor del backend Python. |
| **React + TS** | Frontend UI | Componentes reactivos, rico ecosistema y tipado seguro. | Construcción de la interfaz de chat, dashboards y paneles admin. |
| **Vite** | Build Tool | Compilación y bundler ultra-rápido impulsado por esbuild. | Empaquetado optimizado del código frontend para Electron. |
| **ECharts** | Visualización | 100% offline, alto rendimiento, animaciones y exportación a PNG/SVG. | Renderizado interactivo de gráficos analíticos y KPIs. |
| **Tailwind CSS**| Estilos UI | Clases utilitarias modernas, soporte nativo de Dark Mode y glassmorphism. | Diseño visual premium, responsive y ejecutivo. |
| **FastAPI** | Backend Core | Asíncrono, ultra-rápido, validación Pydantic e integración Python. | Servidor API local Sidecar para el procesamiento de negocio. |
| **`sqlglot`** | Seguridad | Parser AST real de múltiples dialectos SQL (Postgres, MSSQL, MySQL, SQLite). | Validador AST (SQL Guardrail), filtrado RBAC e inyección de LIMIT. |
| **SQLAlchemy** | ORM | Estándar de acceso tipado y seguro a bases de datos relacionales en Python. | Gestión y consultas sobre la base de metadatos del sistema. |
| **Drivers BD** | Conectividad | Conectores nativos certificados (`psycopg[binary]`, `pymysql`, `sqlite3`, `pymssql`). | Conexiones `READ ONLY` a bases de datos corporativas. |
| **PostgreSQL / SQLite**| Persistencia | Robusto, ACID, manejo eficiente de JSON y registros de auditoría. | Almacenamiento interno de usuarios, RBAC, catálogo y logs. |
| **Ollama API** | IA Local | API HTTP local estándar en `localhost:11434` 100% offline. | Inferencia Text-to-SQL, síntesis de negocio y auto-enriquecimiento. |
