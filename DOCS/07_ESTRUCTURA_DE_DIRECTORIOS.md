# Documento 07: Estructura de Carpetas y Arquitectura de Código

> **Documento:** 07 - Arquitectura de Carpetas y Organización del Código  
> **Estado:** Aprobado tras Alineación Técnica y Migración DDD  
> **Área:** Ingeniería de Software y Estructura Monorepo  

> **Árbol verificado contra el filesystem.** No describe estructura planeada ni
> directorios de una versión anterior (Electron, `alembic/`, `app/models/`,
> `app/schemas/`, `app/db_connectors/` ya no existen en el repositorio).

---

## 1. Principios de Organización

1. **Arquitectura Orientada al Dominio (Backend Domain-Driven Design):** el código Python dentro de `backend/app/modules/` agrupa las responsabilidades por dominios de negocio autosuficientes (`auth`, `chat_engine`, `admin_catalog`, `catalog`, `reports`, `telemetry_audit`, `system`).
2. **Escalabilidad Modular en Frontend (Feature-Based Architecture):** React separa páginas en `src/pages/`, componentes presentacionales en `src/components/` y estado/hooks/servicios por característica en `src/features/` (`auth`, `settings`, `admin`, `dashboard`, `chat`).
3. **Un solo proceso Python por ejecución:** no hay proceso de escritorio. El backend es un servicio FastAPI que se sirve por HTTP (`:8000`) y el frontend se sirve como SPA con Vite en dev o Nginx en Docker. No existe directorio `electron/`.

---

## 2. Árbol de directorios y archivos

```
democratizacion-de-datos/
├── .github/workflows/ci.yml     # pytest + tsc + npm run build
├── DOCS/                        # Documentación técnica y funcional (01 a 11)
├── plans/                       # Planes de implementación (001-003) + README
├── data_sources/                # Bases de datos subidas por el usuario (NO versionado)
├── public/                      # Assets estáticos copiados tal cual por Vite
├── scripts/                     # Utilidades Node de dev (run-backend, init-db, checks)
│
├── src/                         # APLICACIÓN FRONTEND (React 18 + Vite + TS)
│   ├── App.tsx                  # Proveedores raíz y rutas
│   ├── main.tsx                 # Punto de entrada de React
│   ├── vite-env.d.ts
│   ├── app/router/              # AppRouter.tsx (tabla de rutas)
│   ├── pages/                   # Login, ChatDashboard, Admin, Settings (+ logos)
│   ├── components/              # Presentacionales por área
│   │   ├── admin/               # Tabs de usuarios, permisos, catálogo, conectores, auditoría
│   │   │   ├── catalog/         # SemanticCatalogSection, DataDictionarySection
│   │   │   └── upload/          # UploadDropzone
│   │   ├── auth/                # MandatoryPasswordChangeModal
│   │   ├── chat/                # Mensajes, prompt, historial lateral, estado vacío
│   │   ├── dashboard/           # ExecutiveDashboardView, ExecutiveAssistantView, report/
│   │   ├── datagrid/            # DataGridTable
│   │   ├── settings/            # Secciones LLM, inferencia y PostgreSQL
│   │   ├── shared/              # ToastContainer
│   │   └── traceability/        # TraceabilityModal
│   ├── features/                # MÓDULOS DE DOMINIO, HOOKS Y CLIENTES DE API
│   │   ├── admin/hooks/         # useAdminUsers/Catalog/Connectors/Permissions/Audit, useConnectorForm
│   │   ├── admin/services/      # audit, catalog, connector, permission
│   │   ├── auth/context/        # AuthContext.tsx
│   │   ├── auth/services/       # auth_service.ts
│   │   ├── chat/hooks/          # useChatEngine.ts
│   │   ├── chat/services/       # llm_service, query_service
│   │   ├── dashboard/components/# KPISection, ChartSection, OfflineAlertView, PredictionPanel
│   │   │   ├── assistant/       # AssistantHeader, AssistantMarkdownBody, AssistantSupportData
│   │   │   └── charts/          # Configuraciones bar/line/pie/extra + theme
│   │   ├── dashboard/services/  # report_service.ts
│   │   ├── settings/context/    # SettingsContext.tsx
│   │   └── settings/hooks/      # useSettingsDiagnostics.ts
│   ├── shared/                  # api/api_client.ts, layout/, clipboard.ts
│   ├── hooks/                   # useModalA11y, useSystemHealth
│   ├── context/                 # NotificationContext.tsx
│   ├── constants/               # Constantes globales
│   ├── types/                   # Interfaces TypeScript
│   └── styles/                  # globals.css
│
├── backend/                     # SERVICIO BACKEND (FastAPI)
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # Dependencias de auth y sesión
│   │   │   └── v1/router.py     # Ensamblado de routers por dominio
│   │   ├── core/                # config, database, security, logging, constants, prompts
│   │   ├── db/                  # init_db.py (usuarios, roles, RBAC, conectores)
│   │   └── modules/             # ✨ DOMINIOS DE NEGOCIO (DDD)
│   │       ├── auth/            # models, schemas, router (JWT, login, usuarios/roles)
│   │       ├── chat_engine/     # engine, sql_generator, sql_executor, ast_validator,
│   │       │                    # governance_guard, intent_classifier, dynamic_schema,
│   │       │                    # kpi_calculator, forecast_calculator, forecast_service,
│   │       │                    # llm_service, llm_diagnostic_router, null_handler,
│   │       │                    # response_builder, narrative_stream, suggestions_service,
│   │       │                    # models, schemas, router
│   │       ├── admin_catalog/   # models, schemas, router, tabular_importer
│   │       │   └── importers/   # base, csv, excel, postgres, sqlite
│   │       ├── catalog/services/# catalog_service, catalog_enricher, connector_service,
│   │       │                    # null_manager, schema_inspector
│   │       ├── reports/         # generator, data_compiler, pdf_exporter, excel_exporter, schemas
│   │       ├── telemetry_audit/ # models, schemas, router (auditoría y compliance)
│   │       └── system/          # health_service, router, schemas
│   ├── tests/                   # Suite pytest (~500 tests, cambia casi cada semana)
│   ├── scripts/                 # Utilidades de operación (PostgreSQL, credenciales, RBAC)
│   ├── main.py                  # Punto de entrada FastAPI (app, CORS, startup, /health)
│   ├── setup_demo_db.py         # Genera demo_corporativa.db
│   ├── setup_mental_health_db.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── Dockerfile                   # Build multi-stage: Vite -> Nginx
├── docker-compose.yml           # postgres + backend + frontend
├── nginx.conf                   # SPA estática + proxy /api/ al backend
├── index.html
├── package.json / package-lock.json
├── .env / .env.example          # Configuración (copiar .env.example → .env)
└── vite.config.ts, tsconfig.json, tailwind.config.js, postcss.config.js
```

---

## 3. Descripción de Responsabilidades

### 3.1. `backend/app/modules/chat_engine/`
Lógica de inferencia y ejecución Text-to-SQL descompuesta:
- `engine.py`: Fachada orquestadora (pipeline completo de una consulta).
- `sql_generator.py` / `sql_executor.py`: Generación y ejecución en modo solo lectura.
- `ast_validator.py`: Guardrail de sintaxis con `sqlglot` (solo `SELECT`).
- `governance_guard.py`: Aplica permisos de tabla y columna al prompt y al SQL.
- `dynamic_schema.py`: Podado del esquema físico por rol.
- `intent_classifier.py`, `kpi_calculator.py`, `forecast_calculator.py`, `forecast_service.py`.
- `null_handler.py`, `response_builder.py`, `narrative_stream.py`, `suggestions_service.py`.

### 3.2. `backend/app/modules/admin_catalog/importers/`
Conversión e ingesta de datos tabulares:
- `base.py`: Sanitización e inferencia de tipos SQLite.
- `csv_importer.py`, `excel_importer.py`, `sqlite_importer.py`, `postgres_importer.py`.

### 3.3. `backend/app/core/database.py`
Motor de metadatos (PostgreSQL con fallback a SQLite), `ensure_schema_migrations()` para
migraciones incrementales de columnas, y el contextmanager `connector_engine()` que
libera el pool del conector al salir del bloque.

### 3.4. `src/features/` (Hooks & Contexts)
- `auth/context/AuthContext.tsx`: identidad y JWT.
- `settings/context/SettingsContext.tsx`: preferencias de LLM y PostgreSQL.
- `dashboard/components/`: KPIs, gráficos, panel de predicción y asistente ejecutivo.
- `*/services/`: clientes HTTP de la API. El cliente base es `src/shared/api/api_client.ts`.

### 3.5. `src/pages/` vs `src/components/`
`pages/` enruta (Login, Chat, Admin, Settings). `components/` es presentacional y no
conoce el router. Los hooks que hablan con el backend viven en `src/features/`.