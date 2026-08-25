# Documento 07: Estructura de Carpetas y Arquitectura de Código

> **Documento:** 07 - Arquitectura de Carpetas y Organización del Código  
> **Estado:** Aprobado tras Alineación Técnica y Migración DDD  
> **Área:** Ingeniería de Software y Estructura Monorepo  

---

## 1. Principios de Organización

El proyecto sigue una arquitectura **Monorepo Limpia (Clean Monorepo)** orientada al dominio:

1. **Arquitectura Orientada al Dominio (Backend Domain-Driven Design):** El código Python dentro de `backend/app/modules/` agrupa las responsabilidades por dominios de negocio autosuficientes (`auth`, `chat_engine`, `admin_catalog`, `catalog`, `reports`, `telemetry_audit`, `system`).
2. **Escalabilidad Modular en Frontend (Feature-Based Architecture):** React organiza el estado global, hooks y componentes por características en `src/features/` (`auth`, `settings`, `admin`, `dashboard`, `chat`) combinados con componentes presentacionales compartidos.
3. **Aislamiento del Proceso de Escritorio (Electron Main):** El directorio `electron/` contiene únicamente la lógica nativa del proceso principal de escritorio (creación de ventanas, puente IPC y gestión del ciclo de vida del proceso secundario Python).

---

## 2. Árbol Completo de Carpetas y Archivos

```
democratizacion-de-datos/
├── .github/                       # Plantillas de CI/CD, linters y flujos automáticos
├── DOCS/                          # Documentación técnica y funcional del proyecto (01 a 10)
│   ├── 01_VISION_Y_ALCANCE.md
│   ├── 02_ARQUITECTURA_TECNICA.md
│   ├── 03_SISTEMA_DE_PERMISOS_Y_SEGURIDAD.md
│   ├── 04_MOTOR_DE_IA_Y_PIPELINE_LOCAL.md
│   ├── 05_ESPECIFICACION_DE_INTERFAZ_Y_DASHBOARDS.md
│   ├── 06_HERRAMIENTAS_Y_TECNOLOGIAS.md
│   ├── 07_ESTRUCTURA_DE_DIRECTORIOS.md
│   ├── 08_PERFILES_Y_ROLES_RBAC.md
│   ├── 09_DECISIONES_ARQUITECTONICAS_ROLES_Y_APRENDIZAJE.md
│   ├── 10_REFACTORIZACIONES_ARQUITECTONICAS_Y_DESCOMPOSICION_MODULAR.md
│   └── README.md
│
├── backend/                       # SERVICIO BACKEND LOCAL (PYTHON FASTAPI)
│   ├── alembic/                   # Migraciones de base de datos PostgreSQL de metadatos
│   ├── app/                       # Código fuente del backend Python
│   │   ├── core/                  # Configuración central, seguridad y constantes (config, database, security, logging)
│   │   ├── db/                    # Inicializadores de base de datos y migraciones
│   │   ├── db_connectors/         # Adaptadores y Pool de conexiones de BD corporativas (PostgreSQL, MSSQL, MySQL, SQLite)
│   │   ├── modules/               # ✨ DOMINIOS DE NEGOCIO (Domain-Driven Design)
│   │   │   ├── admin_catalog/     # Importación de archivos (importers/ csv, excel, sqlite), conectores y subida
│   │   │   ├── auth/              # Identidad, tokens JWT, login y gestión de usuarios/roles
│   │   │   ├── catalog/           # Catálogo semántico y auto-enriquecimiento con IA
│   │   │   ├── chat_engine/       # Motor Text-to-SQL (engine, intent_classifier, sql_executor, kpi_calculator, echarts_formatter, ast_validator)
│   │   │   ├── reports/           # Generador y exportadores de informes ejecutivos (PDF / Excel)
│   │   │   ├── system/            # Salud del sistema, diagnósticos y estado del LLM local
│   │   │   └── telemetry_audit/   # Registros de auditoría, trazabilidad y exportación CSV
│   │   ├── models/                # Modelos ORM relacionales (User, Role, Permission, Catalog, AuditLog)
│   │   └── schemas/               # DTOs y esquemas de validación Pydantic
│   ├── tests/                     # Suite de Pruebas Unitarias e Integración (Pytest - 71 tests)
│   ├── main.py                    # Punto de entrada de la aplicación FastAPI
│   └── requirements.txt           # Dependencias compiladas de Python
│
├── electron/                      # PROCESO PRINCIPAL DE ESCRITORIO (ELECTRON MAIN)
│   ├── main.ts                    # Punto de entrada Electron (Creación de ventana y ciclo de vida)
│   ├── preload.ts                 # Puente IPC seguro (ContextBridge)
│   └── pyrunner.ts                # Gestor del proceso secundario (Sidecar) FastAPI Python
│
├── src/                           # APLICACIÓN FRONTEND (REACT 18/19 + VITE + TYPESCRIPT)
│   ├── components/                # Componentes de presentación (admin, dashboard, datagrid, auth)
│   ├── features/                  # ✨ MÓDULOS DE DOMINIO Y HOOKS FRONTEND
│   │   ├── admin/hooks/           # Custom Hooks (useAdminUsers, useAdminConnectors, useAdminCatalog, useAdminAudit, useDatabaseUpload, useConnectorForm)
│   │   ├── auth/context/          # Contexto de Autenticación de Usuario (AuthContext)
│   │   ├── dashboard/components/  # Componentes modulares del dashboard (KPISection, ChartSection, OfflineAlertView, assistant/)
│   │   └── settings/context/      # Contexto de Configuración del Sistema (SettingsContext)
│   ├── services/                  # Clientes de servicio API HTTP (auth, query, catalog, connector, audit, report)
│   ├── styles/                    # Estilos CSS globales y clases utilitarias
│   ├── types/                     # Interfaces y tipos TypeScript globales
│   ├── App.tsx                    # Enrutador y proveedores raíz (SettingsProvider, AuthProvider, NotificationProvider)
│   └── main.tsx                   # Punto de entrada de React
│
├── index.html                     # HTML principal cargado por Electron
├── package.json                   # Gestión de dependencias Frontend y scripts npm
└── vite.config.ts                 # Configuración de compilación Vite
```

---

## 3. Descripción de Responsabilidades

### 3.1. `backend/app/modules/chat_engine/`
Contiene la lógica de inferencia y ejecución Text-to-SQL descompuesta:
- `engine.py`: Fachada orquestadora.
- `intent_classifier.py`: Clasificador de intenciones por patrones de lenguaje natural.
- `sql_executor.py`: Ejecutor SQLite con aislamiento `READ ONLY`.
- `kpi_calculator.py`: Calculador numérico de totales y promedios.
- `echarts_formatter.py`: Formateador dinámico para visualizaciones Apache ECharts.
- `ast_validator.py`: Validador de seguridad AST con `sqlglot`.

### 3.2. `backend/app/modules/admin_catalog/importers/`
Paquete especializado en la conversión e ingesta de datos tabulares:
- `base.py`: Sanitización e inferencia de tipos SQLite.
- `csv_importer.py`: Parsing con autodetección de delimitador y fallback de codificación.
- `excel_importer.py`: Conversión multi-hoja de libros de Excel.
- `sqlite_importer.py`: Introspección y ejecutores de dumps SQL.

### 3.3. `src/features/` (React Custom Hooks & Contexts)
Organizado por características funcionales:
- `auth/context/AuthContext.tsx`: Control exclusivo de identidad y JWT.
- `settings/context/SettingsContext.tsx`: Control de preferencias del sistema (LLM, Ollama, PostgreSQL).
- `admin/hooks/`: Custom Hooks encapsulando estado y llamadas de API para paneles de administración.
