# Documento 07: Estructura de Carpetas y Arquitectura de Código

> **Documento:** 07 - Arquitectura de Carpetas y Organización del Código  
> **Estado:** Aprobado tras Alineación Técnica  
> **Área:** Ingeniería de Software y Estructura Monorepo  

---

## 1. Principios de Organización

El proyecto sigue una arquitectura **Monorepo Limpia (Clean Monorepo)** que separa de forma estricta las responsabilidades de la interfaz de usuario de escritorio (Electron + React Vite) y el motor de procesamiento backend (Python FastAPI):

1. **Separación Estricta de Capas (Backend Clean Architecture):** El código Python dentro de `backend/app/` sigue la separación en `core`, `api`, `models`, `schemas`, `services` y `db_connectors`.
2. **Escalabilidad Modular en Frontend:** React utiliza una estructura basada en componentes modulares (`components/`), páginas independientes (`pages/`), hooks personalizados (`hooks/`) y servicios API centralizados (`services/`).
3. **Aislamiento del Proceso de Escritorio (Electron Main):** El directorio `electron/` contiene únicamente la lógica nativa del proceso principal de escritorio (creación de ventanas, puente IPC y gestión del ciclo de vida del proceso secundario Python).

---

## 2. Árbol Completo de Carpetas y Archivos

```
democratizacion-de-datos/
├── .github/                       # Plantillas de CI/CD, linters y flujos automáticos
├── DOCS/                          # Documentación técnica y funcional del proyecto (01 a 07)
│   ├── 01_VISION_Y_ALCANCE.md
│   ├── 02_ARQUITECTURA_TECNICA.md
│   ├── 03_SISTEMA_DE_PERMISOS_Y_SEGURIDAD.md
│   ├── 04_MOTOR_DE_IA_Y_PIPELINE_LOCAL.md
│   ├── 05_ESPECIFICACION_DE_INTERFAZ_Y_DASHBOARDS.md
│   ├── 06_HERRAMIENTAS_Y_TECNOLOGIAS.md
│   ├── 07_ESTRUCTURA_DE_DIRECTORIOS.md
│   └── README.md
│
├── backend/                       # SERVICIO BACKEND LOCAL (PYTHON FASTAPI)
│   ├── alembic/                   # Migraciones de base de datos PostgreSQL de metadatos
│   │   ├── versions/              # Archivos de migración de esquema generados
│   │   └── env.py                 # Configuración de conexión de Alembic
│   ├── app/                       # Código fuente del backend Python
│   │   ├── api/                   # Router de APIs (Controladores HTTP)
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py            # Login local, tokens JWT y sesiones
│   │   │   │   │   ├── chat.py            # Endpoint conversacional, Text-to-SQL y ejecutor
│   │   │   │   │   ├── connect.py         # Registro y prueba de fuentes BD corporativas
│   │   │   │   │   ├── rbac.py            # Administración de usuarios, roles y permisos RBAC
│   │   │   │   │   ├── catalog.py         # Catálogo semántico y auto-enriquecimiento IA
│   │   │   │   │   ├── settings.py        # Configuración de LLM local, endpoints y wizard
│   │   │   │   │   └── audit.py           # Registros de auditoría y trazabilidad
│   │   │   │   └── router.py              # Enrutador consolidado v1
│   │   │   └── deps.py                    # Inyección de dependencias (Sesión DB, usuario activo)
│   │   ├── core/                  # Configuración central, seguridad y constantes
│   │   │   ├── config.py                  # Configuración Pydantic basada en entorno
│   │   │   ├── database.py                # Conexión SQLAlchemy a PostgreSQL de metadatos
│   │   │   ├── security.py                # Hashing Argon2/bcrypt, Fernet AES-256 y JWT
│   │   │   └── logging.py                 # Logger estructurado local
│   │   ├── db_connectors/         # Adaptadores y Pool de conexiones de BD corporativas
│   │   │   ├── base.py                    # Interfaz abstracta para conectores relacionales
│   │   │   ├── postgres_connector.py      # Conector psycopg3 (Solo Lectura)
│   │   │   ├── mssql_connector.py         # Conector SQLAlchemy / pymssql (Solo Lectura)
│   │   │   └── mysql_connector.py         # Conector pymysql (Solo Lectura)
│   │   ├── models/                # Modelos de datos relacionales (SQLAlchemy / SQLModel)
│   │   │   ├── user.py                    # Entidad Usuario
│   │   │   ├── role.py                    # Entidades Rol y Dominio
│   │   │   ├── permission.py              # Permisos granulares a nivel de Tabla y Columna
│   │   │   ├── connection.py              # Cadenas de conexión cifradas
│   │   │   ├── catalog.py                 # Metadatos del Catálogo Semántico
│   │   │   └── audit_log.py               # Trazabilidad y Logs de Auditoría
│   │   ├── schemas/               # DTOs y validación de entrada/salida (Pydantic)
│   │   │   ├── user_schema.py
│   │   │   ├── query_schema.py
│   │   │   ├── rbac_schema.py
│   │   │   ├── catalog_schema.py
│   │   │   └── dashboard_schema.py
│   │   ├── services/              # Capa de Lógica de Negocio y Pipelines
│   │   │   ├── ast_validator.py           # SQL Guardrail (sqlglot AST validator: SELECT, RBAC & LIMIT)
│   │   │   ├── dynamic_schema.py          # Schema Pruning filtrado por rol
│   │   │   ├── llm_service.py             # Cliente HTTP agnóstico para IA Local (Ollama / Local API)
│   │   │   ├── text_to_sql_pipeline.py    # Pipeline de inferencia SQL + Retry Loop de autocorrección
│   │   │   ├── text_to_viz_pipeline.py    # Generador de gráficos ECharts + Resumen de negocio
│   │   │   └── auto_catalog_enricher.py   # Asistente de auto-enriquecimiento del catálogo con IA
│   │   └── utils/                 # Funciones auxiliares
│   │       ├── sql_formatter.py           # Formateador de SQL para auditoría
│   │       └── data_sanitizer.py          # Enmascarador de datos sensibles
│   ├── tests/                     # Suite de Pruebas Unitarias e Integración (Pytest)
│   ├── alembic.ini                # Archivo de configuración Alembic
│   ├── main.py                    # Punto de entrada de la aplicación FastAPI
│   ├── pyproject.toml             # Configuración de dependencias Python
│   └── requirements.txt           # Lista compilada de paquetes de Python
│
├── electron/                      # PROCESO PRINCIPAL DE ESCRITORIO (ELECTRON MAIN)
│   ├── main.ts                    # Punto de entrada Electron (Creación de ventana y ciclo de vida)
│   ├── preload.ts                 # Puente IPC seguro (ContextBridge)
│   ├── pyrunner.ts                # Gestor del proceso secundario (Sidecar) FastAPI Python
│   └── tsconfig.json              # Configuración TypeScript para Electron
│
├── src/                           # APLICACIÓN FRONTEND (REACT 18/19 + VITE + TYPESCRIPT)
│   ├── assets/                    # Imágenes, logotipos, fuentes e íconos locales
│   ├── components/                # Componentes React de Interfaz de Usuario
│   │   ├── ui/                    # Componentes base (Botones, Inputs, Modales, Tarjetas, Badges)
│   │   ├── chat/                  # Input de preguntas conversacionales y burbujas de respuesta
│   │   ├── dashboard/             # Contenedor de dashboards, gráficos ECharts y tarjetas KPI
│   │   ├── datagrid/              # Tabla de datos interactiva (paginación, filtros, ordenamiento)
│   │   ├── traceability/          # Modal/Acordeón de trazabilidad y visor de SQL auditado
│   │   └── admin/                 # Componentes del panel admin (RBAC, Catálogo, Conexiones, Auditoría)
│   ├── context/                   # Contextos de React para Estado Global (Sesión Auth, Tema, Config)
│   ├── hooks/                     # Custom Hooks de React (useChat, useECharts, usePermissions)
│   ├── layouts/                   # Diseños de envolvente de página (MainLayout, AdminLayout)
│   ├── pages/                     # Páginas / Vistas Principales de la Aplicación
│   │   ├── SetupWizardPage.tsx        # Wizard de configuración inicial en primera ejecución
│   │   ├── LoginPage.tsx              # Pantalla de inicio de sesión local
│   │   ├── ChatDashboardPage.tsx      # Vista principal de consulta conversacional y dashboards
│   │   ├── AdminUsersPage.tsx         # Administración de usuarios y roles RBAC
│   │   ├── AdminCatalogPage.tsx       # Catálogo Semántico y auto-enriquecimiento IA
│   │   ├── AdminConnectorsPage.tsx    # Gestión de fuentes de datos corporativas
│   │   ├── AdminSettingsPage.tsx      # Ajustes del motor LLM local y PostgreSQL
│   │   └── AdminAuditPage.tsx         # Visor de Trazabilidad y Logs de Auditoría
│   ├── services/                  # Clientes de servicio API HTTP (Axios / Fetch a FastAPI local)
│   │   ├── api_client.ts              # Configuración base del cliente HTTP local
│   │   ├── auth_service.ts            # Peticiones de autenticación y sesión
│   │   ├── query_service.ts           # Envío de preguntas y recepción de visualizaciones
│   │   ├── catalog_service.ts         # Operaciones sobre el catálogo semántico
│   │   └── admin_service.ts           # Operaciones de administración y RBAC
│   ├── styles/                    # Estilos CSS globales y tokens Tailwind
│   │   └── globals.css
│   ├── types/                     # Interfaces y tipos TypeScript globales
│   │   ├── chat.d.ts
│   │   ├── dashboard.d.ts
│   │   ├── rbac.d.ts
│   │   └── catalog.d.ts
│   ├── App.tsx                    # Enrutador y componentes raíz de React
│   ├── main.tsx                   # Punto de entrada del cliente React
│   └── vite-env.d.ts
│
├── index.html                     # HTML principal cargado por Electron
├── package.json                   # Gestión de dependencias Frontend y scripts npm
├── tailwind.config.js             # Configuración del sistema de diseño Tailwind CSS
├── tsconfig.json                  # Configuración TypeScript raíz
├── vite.config.ts                 # Configuración de compilación Vite
└── README.md                      # Documento descriptivo principal del repositorio
```

---

## 3. Descripción de Responsabilidades de los Subdirectorios Principales

### 3.1. `backend/app/services/`
Contiene la lógica de negocio central del sistema:
- `ast_validator.py`: Validador de seguridad con `sqlglot` (Analiza el AST de la consulta SQL generada por el LLM, verifica que sea solo `SELECT`, valida tablas/columnas autorizadas por rol e inyecta límites).
- `dynamic_schema.py`: Recorta el catálogo semántico dejando en el contexto del prompt únicamente las tablas y columnas autorizadas para el usuario en sesión.
- `llm_service.py`: Cliente agnóstico que efectúa llamadas HTTP al servidor local de IA (Ollama en `http://localhost:11434` o servidores compatibles OpenAI en `http://localhost:8000/v1`).
- `text_to_sql_pipeline.py`: Pipeline que envía la pregunta al LLM y ejecuta el ciclo de reintentos (retry loop de hasta 2 intentos) si el SQL falla la validación sintáctica o de ejecución.
- `text_to_viz_pipeline.py`: Ejecuta un segundo paso de inferencia ligero sobre los datos devueltos para seleccionar la mejor plantilla de gráfico ECharts, asignar ejes y generar el resumen ejecutivo de negocio.

### 3.2. `backend/app/db_connectors/`
Pool de conectores relacionales nativos en modo **Solo Lectura**:
- Implementa adaptadores para **PostgreSQL**, **Microsoft SQL Server**, **MySQL** y **SQLite**.
- Aplica configuraciones estrictas de `READ ONLY`, límites de tiempo de respuesta (timeouts) y límites de filas devueltas.

### 3.3. `electron/`
Contiene el código exclusivo del entorno de escritorio:
- `main.ts`: Crea la ventana nativa de la aplicación con configuraciones de seguridad (Context Isolation activado, Node Integration desactivado en el renderer).
- `pyrunner.ts`: Se encarga de iniciar el ejecutable/script de Python FastAPI en un puerto libre en `127.0.0.1` y monitorear su salud, cerrándolo limpiamente al salir de Electron.
- `preload.ts`: Expone métodos seguros a través de `window.electronAPI` para comunicación entre React y Electron.

### 3.4. `src/` (React Frontend)
- `components/dashboard/`: Renderiza dinámicamente las tarjetas KPI, resúmenes ejecutivos y contenedores de gráficos **Apache ECharts** (`echarts-for-react`).
- `components/traceability/`: Renderiza el panel desplegable de auditoría que desglosa el cálculo, el SQL ejecutado con botón de copiar y el estado de validación AST.
- `pages/SetupWizardPage.tsx`: Vista especial de primera ejecución para configurar el usuario Administrador y la conexión a la base de datos PostgreSQL de metadatos.
