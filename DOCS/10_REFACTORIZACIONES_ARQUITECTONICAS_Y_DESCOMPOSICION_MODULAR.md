# Documento 10: Refactorizaciones Arquitectónicas y Descomposición Modular

> **Documento:** 10 - Refactorizaciones Arquitectónicas, Domain-Driven Design y Descomposición de God Objects  
> **Estado:** Aprobado e Implementado en la Base de Código  
> **Área:** Ingeniería de Software, Frontend & Backend Architecture  

---

## 1. Resumen Ejecutivo de la Evolución Arquitectónica

Para garantizar que el sistema DATIA sea mantenible, escalable y resistente a regresiones a medida que crece, se realizó un proceso sistemático de refactorización divido en **4 Fases de Reestructuración**. 

Este proceso transformó la arquitectura original desde un esquema monolítico/tipo de archivo (*Flat Architecture by Type*) y archivos gigantes con múltiples responsabilidades (*God Objects*) hacia una arquitectura basada en **Domain-Driven Design (DDD)** en el Backend y **Módulos Basados en Features/Hooks** en el Frontend.

---

## 2. Fases de Refactorización Ejecutadas

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   HISTORIAL DE REFACTORIZACIÓN ARQUITECTÓNICA                          │
├───────────────────────────────────┬────────────────────────────────────────────────────┤
│ Fase 1: Descomposición de Engine  │ Splitting del QueryEngine (1,281 líns) en 5        │
│                                   │ módulos especializados.                            │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ Fase 2: Migración Backend a DDD   │ Reestructuración de backend/app/ a módulos por     │
│                                   │ Dominio de Negocio y eliminación de endpoints.     │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ Fase 3: Descomposición UI Frontend│ Divisón de vistas ejecutivas gigantes en           │
│                                   │ subcomponentes y reducers.                         │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ Fase 4: Modularización & Modales  │ Separación Auth/Settings, Hooks de Admin y         │
│                                   │ paquete de importación de datos backend.           │
└───────────────────────────────────┴────────────────────────────────────────────────────┘
```

---

## 3. Desglose Detallado por Componente y Dominio

### 3.1. Backend: Migración a Domain-Driven Design (DDD)

El código backend en `backend/app/` pasó de estar agrupado por "tipo de archivo" (`models/`, `schemas/`, `api/v1/endpoints/`) a una estructura donde cada dominio de negocio es un micro-ecosistema autosuficiente:

```
backend/app/
├── core/                        # Infraestructura agnóstica (config, database, security)
├── db/                          # Migraciones Alembic e inicialización de esquemas
└── modules/                     # ✨ DOMINIOS DE NEGOCIO (DDD)
    ├── auth/                    # Identidad, tokens JWT, roles y sesiones
    ├── chat_engine/             # Motor Text-to-SQL, AST Guardrail, Prompts e Inferencia
    ├── admin_catalog/           # Carga de archivos (CSV, Excel, SQLite), parsing y conectores
    ├── catalog/                 # Catálogo semántico y auto-enriquecimiento con IA
    ├── reports/                 # Generación y exportación de informes ejecutivos (PDF / Excel)
    ├── telemetry_audit/         # Registros de auditoría, trazabilidad y filtros
    └── system/                  # Monitor de salud del sistema y estado del LLM local
```

#### Eliminación de Código Muerto Legado:
- Se eliminó la carpeta obsoleta `backend/app/api/v1/endpoints/` (~2,100 líneas de código duplicado) garantizando que todo el tráfico transite exclusivamente a través de los enrutadores modulares en `backend/app/modules/`.

---

### 3.2. Descomposición del Motor Analítico (`chat_engine`)

El archivo original `query_engine.py` (1,281 líneas) concentraba clasificación de preguntas, ejecución SQL, cálculo métrico, generación de ECharts y autoreparación con LLM. Fue dividido en:

1. **[engine.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py)** (Orquestador ligero Facade).
2. **[intent_classifier.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/intent_classifier.py)**: Clasificación conversacional y detecciones por Regex.
3. **[sql_executor.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/sql_executor.py)**: Conexión SQLite segura en modo Solo Lectura y manejo de excepciones relacionales.
4. **[kpi_calculator.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/kpi_calculator.py)**: Cálculo de totales, máximos, mínimos y tarjetas KPI.
5. **[echarts_formatter.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/echarts_formatter.py)**: Construcción de opciones Apache ECharts (Barra, Línea, Donas, Gauges).

---

### 3.3. Importación Tabular Backend (`importers/`)

El módulo `tabular_importer.py` (297 líneas) gestionaba el procesamiento de 4 formatos distintos en una sola clase. Se modularizó en el paquete `backend/app/modules/admin_catalog/importers/`:

- **[base.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/admin_catalog/importers/base.py)**: Funciones agnósticas de sanitización de identificadores SQLite e inferencia de tipos (`INTEGER`, `REAL`, `TEXT`).
- **[csv_importer.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/admin_catalog/importers/csv_importer.py)**: Detección automática de delimitadores (`,`, `;`, `\t`, `|`) y fallbacks de codificación (`UTF-8`, `Latin-1`, `CP1252`).
- **[excel_importer.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/admin_catalog/importers/excel_importer.py)**: Conversión multi-hoja de libros de Excel (`.xlsx`, `.xlsm`).
- **[sqlite_importer.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/admin_catalog/importers/sqlite_importer.py)**: Introspección de bases de datos SQLite `.db` y ejecutor de scripts `.sql`.
- **[tabular_importer.py](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/admin_catalog/tabular_importer.py)**: Fachada limpia que exporta `convert_uploaded_file_to_sqlite`.

---

### 3.4. Frontend: Descomposición de Vistas y Custom Hooks

El Frontend de React fue reestructurado para desacoplar componentes UI de la lógica de estado y llamadas API mediante **Custom Hooks**:

#### 1. Separación de Autenticación y Configuración:
- **[SettingsContext.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/settings/context/SettingsContext.tsx)**: Manejo dedicado de `AppSettings` (endpoints LLM, Ollama, PostgreSQL).
- **[AuthContext.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/auth/context/AuthContext.tsx)**: Enfocado estrictamente en la identidad del usuario, tokens JWT y modal de clave obligatoria.

#### 2. Vistas Ejecutivas en Componentes Livianos:
- **`ExecutiveDashboardView.tsx`** (471 -> 175 líneas): Refactorizado delegando a [KPISection.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/dashboard/components/KPISection.tsx), [ChartSection.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/dashboard/components/ChartSection.tsx) y [OfflineAlertView.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/dashboard/components/OfflineAlertView.tsx).
- **`ExecutiveAssistantView.tsx`** (428 -> 90 líneas): Refactorizado delegando a [AssistantMarkdownBody.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/dashboard/components/assistant/AssistantMarkdownBody.tsx), [AssistantSupportData.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/dashboard/components/assistant/AssistantSupportData.tsx) y [AssistantHeader.tsx](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/dashboard/components/assistant/AssistantHeader.tsx).

#### 3. Pestañas y Modales de Administración (`src/features/admin/hooks/`):
- **[useAdminUsers.ts](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/admin/hooks/useAdminUsers.ts)**: Estado de usuarios y matriz RBAC para `AdminUsersTab.tsx`.
- **[useAdminConnectors.ts](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/admin/hooks/useAdminConnectors.ts)**: Pruebas de conectividad TCP y filtros para `AdminConnectorsTab.tsx`.
- **[useAdminCatalog.ts](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/admin/hooks/useAdminCatalog.ts)**: Reglas semánticas y auto-enriquecimiento para `AdminCatalogTab.tsx`.
- **[useAdminAudit.ts](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/admin/hooks/useAdminAudit.ts)**: Paginación, filtros y exportación CSV para `AdminAuditTab.tsx`.
- **[useDatabaseUpload.ts](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/admin/hooks/useDatabaseUpload.ts)**: Drag & Drop y carga Multipart para `DatabaseUploadModal.tsx`.
- **[useConnectorForm.ts](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/src/features/admin/hooks/useConnectorForm.ts)**: Reducer de formulario y tests de red para `ConnectorModal.tsx`.

---

## 4. Métricas de Impacto en la Mantenibilidad

| Módulo / Componente | Estado Inicial (Líneas) | Estado Actual (Líneas) | Reducción de Complejidad |
| :--- | :---: | :---: | :---: |
| `query_engine.py` (Engine backend) | 1,281 | 572 | ✂️ 55% de reducción (dividido en 5 módulos) |
| `ExecutiveDashboardView.tsx` | 471 | 175 | ✂️ 63% de reducción |
| `ExecutiveAssistantView.tsx` | 428 | 90 | ✂️ 79% de reducción |
| `tabular_importer.py` | 297 | 37 | ✂️ 87% de reducción (delegando en `importers/`) |
| `backend/app/api/v1/endpoints/` | 2,100 | 0 | 🗑️ 100% eliminado (Migrado a DDD) |

---

## 5. Garantía de Calidad y Pruebas

Toda la reestructuración fue validada de extremo a extremo:
- **TypeScript**: `npx tsc --noEmit` arroja **0 errores de compilación**.
- **Pytest**: `py -m pytest backend/tests/` completa con **71/71 pruebas pasando exitosamente (100% de éxito)**.
