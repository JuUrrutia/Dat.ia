# Estrategia y Evidencia de Pruebas

> **Documento:** 24 - Pruebas
> **Estado:** Vigente. Cifras medidas el 30/10/2026 sobre el árbol de trabajo.
> **Última actualización:** 30 de octubre de 2026
> **Alcance:** backend (pytest), frontend (Vitest), verificación estática y CI

---

## 1. Principio

Una prueba existe si **falla cuando el comportamiento se rompe**. No cuenta un `grep` que busca una cadena, ni un test que solo verifica que una función fue llamada. El proyecto ya pagó ese error: los 138 asserts de `grep` del frontend se reemplazaron por 34 tests reales (hoy 135).

> **Regla:** si no se ejecutó en esta sesión, no se reporta como verde. Las cifras de este documento salen de comandos ejecutados, no de la memoria del equipo.

---

## 2. Línea base medida

| Comando | Resultado | Duración | Fecha |
|---|---|---|---|
| `cd backend; venv\Scripts\python.exe -m pytest -q` | **844 passed, 244 subtests, 0 failed** | 396,55 s (6:36) | 30/10/2026 |
| `npm test` | **18 archivos, 135 tests, 0 failed** | 6,56 s | 30/10/2026 |
| `npx tsc --noEmit` | **exit 0** | ~9 s | 30/10/2026 |
| `npm run build` | **exit 0** | 10,72 s | 30/10/2026 |

**Composición del backend:**

- **91 archivos** `backend/tests/test_*.py` + `conftest.py`.
- **844 funciones `test_`** (una por caso reportado por pytest).
- **244 subtests** de `unittest.subTest` (variantes dentro de un mismo test).

> `844` es el número de casos, no de asserts ni de líneas cubiertas. No hay medición de cobertura.

---

## 3. Backend (pytest)

### 3.1 Aislamiento

- La suite usa `democratizacion_metadatos_test`, no la base de desarrollo.
- Fuerza `DEMO_MODE=true` sin tocar `.env`.
- Crea bases PostgreSQL temporales reales; no hay fallback a SQLite.
- Sin PostgreSQL en `localhost:5432` la suite **no arranca**.
- `conftest.py` siembra la demo y crea la conexión corporativa que apunta a `democratizacion_empresa`.

> **Límite declarado:** el aislamiento es la intención documentada; no está verificado que ningún test escriba en la base de desarrollo. La revisión se apoya en el nombre de la base y en el fixture, no en un sandbox de sistema.

### 3.2 Tipos de prueba

| Tipo | Qué cubre | Ejemplos |
|---|---|---|
| **Seguridad AST** | Solo `SELECT`, un statement, tablas y columnas | `test_ast_hardening.py` (40 casos), `test_ast_validator.py`, `test_cls_select_star.py` |
| **RBAC / CLS** | Fail-closed, máscaras, colisión de políticas | `test_governance_fail_closed.py`, `test_masked_columns.py` (23), `test_rbac_governance.py` (22), `test_table_permissions_default_deny.py` |
| **Autenticación** | Login, lockout, clave temporal, revocación | `test_password_lockout.py`, `test_sessions.py`, `test_auth_temp_password_lifecycle.py`, `test_password_change_revocation.py` |
| **Nulos** | Auditoría, remediación en memoria, política física | `test_null_manager.py` (24), `test_nulls_audit_api.py`, `test_null_policy_and_visualizations.py` |
| **ML** | Modelos, backtest, honestidad, RBAC | `test_ml_models.py` (21), `test_ml_honesty.py` (32), `test_prediction_honesty.py` (26), `test_forecast_properties.py`, `test_ml_models_properties.py` |
| **Informes** | PDF, Excel, snapshot, permisos | `test_reports_export.py` (24) |
| **Catálogo** | Conexiones, importación, enriquecimiento | `test_catalog_and_connectors.py`, `test_catalog_enricher_llm.py`, `test_upload_dataset_least_privilege.py` |
| **Infraestructura** | Migraciones, índices, timezone, transacciones | `test_database_autocreate.py`, `test_permission_indexes_migration.py`, `test_transaction_hygiene.py`, `test_time_utc.py` |
| **Contrato de API** | Errores, 404, autorización de recursos compartidos | `test_chat_shared_resource_authz.py`, `test_chat_thread_isolation.py`, `test_admin_endpoint_auth.py` |
| **Propiedades** | Invariantes con Hypothesis | `test_forecast_properties.py`, `test_ml_models_properties.py` |

### 3.3 Tests que sostienen los pilares

| Pilar | Tests que fallan si se rompe |
|---|---|
| Solo lectura | `test_ast_hardening.py`, `test_ast_validator.py`, `test_cls_select_star.py` |
| RBAC fail-closed | `test_governance_fail_closed.py`, `test_rbac_governance.py`, `test_admin_endpoint_auth.py` |
| CLS / masking | `test_masked_columns.py`, `test_masked_conversational_branch.py`, `test_cls_anomalies_forecast_prompt.py` |
| Trazabilidad | `test_audit_log.py`, `test_audit_log_honesty.py`, `test_validation_status_nullable_migration.py` |

> Si un cambio toca estos archivos y no se agrega un test, la revisión debe rechazarlo. No por proceso, sino porque son los únicos que impiden que un bug de seguridad llegue a producción.

### 3.4 Cómo correr un subconjunto

```bash
cd backend

# Un archivo
venv\Scripts\python.exe -m pytest tests/test_ast_hardening.py -q

# Un test
venv\Scripts\python.exe -m pytest tests/test_password_lockout.py::TestPasswordLockout::test_five_failed_attempts_locks_account -q

# Los que tocan un módulo
venv\Scripts\python.exe -m pytest tests -q -k "rbac or mask or ast"
```

> Los nombres de clase y test cambian; si el ejemplo no coincide, usar `--collect-only` para listar.

---

## 4. Frontend (Vitest)

### 4.1 Alcance real

Vitest corre en **entorno node**: prueba lógica pura, no renderiza componentes.

| Archivo | Qué cubre |
|---|---|
| `api_client.test.ts` | Cliente HTTP, errores y tipos |
| `auth` (`temp_password.test.ts`, `password_strength.test.ts`) | Reglas de clave temporal y fortaleza |
| `chat_engine_projection_offer.test.ts` | Oferta de proyección desde el chat |
| `connectors_refresh.test.ts` | Refresco del selector de conectores |
| `catalog_service.test.ts`, `permission_service.test.ts` | Servicios de catálogo y permisos |
| `echarts_setup.test.ts`, `extra_charts.test.ts` | Registro de gráficos ECharts |
| `layout_state_navigation.test.ts` | Estado de navegación |
| `llm_service.test.ts` | Servicio LLM del frontend |
| `projections_page.test.ts`, `projection_service.test.ts`, `projection_suggestion_card.test.ts` | Proyecciones |
| `query_service.test.ts`, `stream_buffer.test.ts` | Consulta y buffer de streaming |
| `CatalogAddModal.test.ts` | Lógica del modal de alta de catálogo (sin DOM) |
| `role_label.test.ts` | Etiquetas de rol |

### 4.2 Lo que no cubre

- Renderizado de componentes React.
- Interacción real con el DOM.
- Flujos completos de usuario.
- Accesibilidad.

> `CatalogAddModal.test.ts` prueba la lógica extraída del modal, no el modal montado. No confundir "test de componente" con "test de render".

---

## 5. Verificación estática y build

| Comando | Qué detecta | ¿Bloquea CI? |
|---|---|---|
| `npx tsc --noEmit` | Errores de tipo | ✅ (dentro de `npm run build`) |
| `npm run build` | Tipos + bundle de producción | ✅ |
| `npm run knip` | Exports y tipos sin uso | ❌ advisory |
| `npm run analyze` | Tamaño de chunks | ❌ advisory |
| `ruff check --select C901` | Complejidad | ❌ advisory |
| `npm run doctor` | `react-doctor` | ❌ advisory (corre en PRs) |

---

## 6. Integración continua

`.github/workflows/ci.yml` tiene dos jobs:

### `backend-tests`

1. Servicio `postgres:16-alpine` con health check `pg_isready`.
2. Python 3.11.
3. `pip install -r backend/requirements.txt`.
4. `python scripts/setup_postgres_full.py` (siembra demo, idempotente).
5. `pytest -v`.

> El seed escribe en `democratizacion_metadatos`; pytest usa `democratizacion_metadatos_test`. Son bases distintas a propósito.

### `frontend`

1. Node 24.
2. `npm ci --no-audit --prefer-offline` (sin fallback a `npm install`).
3. `npm test`.
4. `npm run build` (incluye `tsc`).

### Lo que CI no hace

| Ausencia | Consecuencia |
|---|---|
| Lint bloqueante | Estilo no verificado |
| Cobertura mínima | No se sabe qué falta |
| Specs E2E | Flujos completos no cubiertos |
| Tests de render | UI no verificada |
| Escaneo de dependencias | Vulnerabilidades no bloquean |
| Pruebas de carga | Capacidad no medida |

> Estas ausencias están declaradas en [`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md) §6 y en [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) §4. No se presentan como "done".

---

## 7. Cómo agregar una prueba

### Backend

1. Elegir el archivo por comportamiento, no por módulo: `test_<comportamiento>.py`.
2. Un test = un comportamiento.
3. Usar PostgreSQL real si toca SQL, RBAC o migraciones.
4. Nombrar el test con el síntoma que previene: `test_blocked_column_is_rejected_even_with_select_star`.
5. Verificar que **falla** sin el cambio y pasa con él.
6. Si es una propiedad, usar Hypothesis (`test_*_properties.py`).

### Frontend

1. Extraer la lógica pura del componente si está acoplada al DOM.
2. Probar la función, no el framework.
3. Un archivo por dominio; nombre `*.test.ts`.
4. No usar `grep` ni leer el código fuente como aserción.

---

## 8. Evidencia de la última corrida

```text
844 passed, 1 warning, 244 subtests passed in 396.55s (0:06:36)
```

```text
Test Files  18 passed (18)
     Tests  135 passed (135)
  Duration  6.56s
```

```text
npx tsc --noEmit   -> exit 0
npm run build      -> exit 0 (10.72s)
dist/assets/echarts-*.js  ~665.26 kB  (warning esperado)
```

> El warning de `echarts` es conocido y está documentado en `vite.config.ts`. No es una regresión.

---

## 9. Deuda de pruebas

| Deuda | Riesgo | Prioridad |
|---|---|---|
| Specs E2E | Un flujo roto pasa CI | Alta |
| Tests de render | Errores de UI no detectados | Media |
| Cobertura medida | No se sabe qué falta | Media |
| Lint bloqueante | Estilo inconsistente | Alta |
| Pruebas de carga | Capacidad desconocida | Baja |
| Mutation testing | Tests que no matan mutantes | Baja |

---

## 10. Documentos relacionados

- [Definition of Done](17_DEFINITION_OF_DONE.md)
- [SRS](19_SRS.md)
- [Requisitos no funcionales](20_REQUISITOS_NO_FUNCIONALES.md)
- [Manual técnico](23_MANUAL_TECNICO.md)
- [CI](../.github/workflows/ci.yml)
