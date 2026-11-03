# Manual Técnico

> **Documento:** 23 - Manual técnico
> **Estado:** Vigente. Comandos verificados contra el repositorio.
> **Última actualización:** 30 de octubre de 2026
> **Audiencia:** desarrolladores, operadores y evaluadores técnicos

---

## 1. Requisitos

| Componente | Versión | Obligatorio |
|---|---|---|
| Node.js | 18+ | Sí (desarrollo y build) |
| npm | 9+ | Sí |
| Python | 3.10+ (Docker usa 3.13) | Sí |
| PostgreSQL | 16 | Sí |
| Ollama / llama.cpp / LM Studio | Reciente | No (sin LLM el chat responde "IA no disponible") |
| Docker | 24+ | Solo para despliegue |
| Git | Reciente | Sí |

> La suite de backend **no arranca sin PostgreSQL** en `localhost:5432`. No es un mock: crea bases temporales reales (`backend/tests/conftest.py`).

---

## 2. Instalación para desarrollo

```bash
# 1. Dependencias del frontend
npm install

# 2. Entorno virtual y dependencias del backend
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 2.1 Variables de entorno

```bash
cp .env.example .env
```

Mínimo para arrancar:

| Variable | Obligatoria | Nota |
|---|---|---|
| `SECRET_KEY` | Sí en producción | En desarrollo hay un default; en `ENVIRONMENT=production` se rechaza |
| `FERNET_KEY` | Sí en Docker | Cifra credenciales de conexión; **no rotable sin recifrar** |
| `POSTGRES_PASSWORD` | Sí | Compose se niega a arrancar sin ella |
| `POSTGRES_SERVER` | No | Default `localhost`; en Docker es `postgres` |
| `OLLAMA_BASE_URL` | No | Default `http://localhost:11434`; en Docker `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | No | Default `qwen2.5-coder:7b` |
| `LLM_MODE` | No | `central`, `external` o `user` |
| `DEMO_MODE` | No | `true` solo en máquinas de demostración |
| `VITE_API_BASE_URL` | Build-time | Usar `http://127.0.0.1:8000/api/v1` en local; `/api/v1` en Docker |

> `VITE_*` se hornea al construir el frontend. Cambiarla exige rebuild, no solo reiniciar.

### 2.2 Datos demo

```bash
# desde la raíz, con el venv activo o usando su python
python backend/scripts/setup_postgres_full.py
```

Crea y siembra:

- `democratizacion_metadatos` (13 tablas de plataforma).
- `democratizacion_empresa` (9 tablas demo: 4 dimensiones + 5 hechos).

`app/db/init_db.py` repite el seed al arrancar si `DEMO_MODE=true`.

### 2.3 Arranque

```bash
npm run dev
```

| Servicio | URL |
|---|---|
| Frontend | `http://localhost:5173/` |
| API | `http://127.0.0.1:8000/api/v1` |
| OpenAPI | `http://127.0.0.1:8000/docs` (si `ENABLE_API_DOCS=true`) |

> Usar `127.0.0.1`, no `localhost`, en URLs del backend: `localhost` puede resolver a IPv6 y el backend escucha IPv4. El síntoma es `TypeError: Failed to fetch` sin código HTTP.

---

## 3. Estructura del código

```
backend/
  app/
    api/            # routers agregados
    core/           # config, database, security, constants, prompts, time
    db/             # init_db y seed
    modules/
      auth/         # usuarios, roles, dominios, sesiones
      admin_catalog/# conexiones, catálogo, permisos, importadores
      catalog/      # servicios de catálogo y null_manager
      chat_engine/  # motor de consulta, AST, gobernanza, LLM
      ml_forecast/  # proyecciones y backtest
      reports/      # PDF y Excel
      system/       # health, política LLM, anomalías
      telemetry_audit/ # audit_logs y exportación
  tests/            # 91 archivos de test + conftest
  scripts/          # setup, unlock, verificación
  main.py
src/
  pages/            # Login, ChatDashboard, Settings, Admin, Projections
  components/       # UI por dominio
  features/         # auth, chat, dashboard
  hooks/            # hooks compartidos
  shared/           # layout, utilidades
  types/            # tipos TS
  __tests__/        # 18 archivos Vitest
plans/              # planes 001–005 y tabla de estado
DOCS/               # documentación 01–26
deploy/             # bundle on-prem, backup, restore, upgrade, Caddy
scripts/            # run-backend.js, init-db.js
```

Detalle completo en [`07_ESTRUCTURA_DE_DIRECTORIOS.md`](07_ESTRUCTURA_DE_DIRECTORIOS.md).

---

## 4. Comandos de verificación

| Comando | Qué verifica | Tiempo normal |
|---|---|---|
| `cd backend; venv\Scripts\python.exe -m pytest -q` | Backend completo (PostgreSQL real) | 6–9 min |
| `npm test` | Lógica del frontend (Vitest) | ~10 s |
| `npx tsc --noEmit` | Tipos de todo el proyecto | ~9 s |
| `npm run build` | Build de producción | ~12–25 s |
| `docker compose config` | Sintaxis y variables del compose | instantáneo |

### Comandos de medición (advisory)

```bash
npm run knip          # exports y tipos sin uso
npm run analyze       # tamaño del bundle
ruff check backend/app --select C901   # complejidad ciclomática
vulture backend/app   # código muerto (si está instalado)
```

> Ninguno de estos bloquea CI. El detalle está en [`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md) §6.

---

## 5. API

- Prefijo: `/api/v1`.
- Auth: `Authorization: Bearer <JWT>`.
- Errores: JSON con `detail`.

| Módulo | Endpoints principales |
|---|---|
| auth | `/auth/login`, `/auth/me`, `/auth/logout`, `/auth/change-password`, `/auth/users`, `/auth/roles`, `/auth/domains`, `/auth/sessions` |
| catálogo | `/catalog`, `/catalog/data-dictionary`, `/catalog/auto-enrich`, `/connectors`, `/connectors/upload`, `/connectors/test`, `/permissions`, `/permissions/columns`, `/permissions/coverage` |
| chat | `/chat/query`, `/chat/query/stream`, `/chat/predict`, `/chat/suggestions`, `/chat/threads`, `/chat/widgets`, `/chat/feedback`, `/chat/golden-query` |
| ML | `/ml/projections/estimate`, `/ml/projections/run`, `/ml/projections/context`, `/ml/projections/history` |
| sistema | `/health`, `/system/llm-policy`, `/system/anomalies` |
| auditoría | `/audit/export` |
| informes | `/reports/export/pdf`, `/reports/export/excel` |

> El inventario exacto se obtiene de los decoradores en `backend/app/modules/*/router.py`. Si un endpoint no está ahí, no existe, aunque aparezca en un documento viejo.

---

## 6. Flujo de una consulta (para depurar)

1. `POST /chat/query` recibe pregunta, `connection_id` e historial.
2. `GovernanceGuard` resuelve tablas, columnas bloqueadas y enmascaradas. Si falla, devuelve `set()` y la consulta se deniega.
3. `IntentClassifier` separa saludo, fuera de alcance, conversacional y análisis.
4. `SQLGenerator` poda el esquema y pide SQL al LLM.
5. `ASTValidator` exige un único `SELECT` y reescribe el SQL seguro.
6. `SQLExecutor.execute_with_self_healing` ejecuta; si falla por un error no estructural, pide **una** reparación al LLM, revalida y reintenta.
7. `mask_query_rows` enmascara columnas `MASKED`.
8. `NullHandler` detecta nulos; la remediación es en memoria.
9. `KpiCalculator` y `ResponseBuilder` arman KPIs, gráfico, narrativa y trazabilidad.
10. Se escribe `audit_logs` con SQL, estado, tiempo, filas y snapshot.

**Punto de seguridad:** si se mueve el enmascarado después de los KPIs o del snapshot, el dato sensible se filtra. El orden no es cosmético.

---

## 7. Tareas frecuentes

### 7.1 Agregar una tabla al catálogo de un rol

1. Crear la conexión desde `/admin` o el endpoint `/connectors`.
2. Sincronizar el catálogo (`/catalog`).
3. En permisos, habilitar la tabla para el rol (`role_table_permissions`).
4. Verificar que el rol no vea tablas de otro dominio.

### 7.2 Marcar una columna como enmascarada o bloqueada

1. Entrar a Administración → Permisos → Columnas.
2. Elegir conexión, tabla y columna.
3. Seleccionar `MASKED` o `BLOCKED`.
4. Verificar con una consulta real de un usuario de ese rol:
   - `MASKED`: el valor aparece enmascarado.
   - `BLOCKED`: la columna no aparece y el SQL que la pide se rechaza.

> Si dos tablas comparten la columna, se aplica la política más restrictiva. No alcanza con cambiar una fila.

### 7.3 Agregar un endpoint

1. Crear la ruta en el router del módulo.
2. Declarar el permiso: `Depends(get_current_user)` o `Depends(get_current_admin)`.
3. Si devuelve filas, pasar por `mask_rows`.
4. Si ejecuta SQL, pasar por `ASTValidator`.
5. Escribir el test antes de tocar la UI.
6. Actualizar [`19_SRS.md`](19_SRS.md) y [`24_PRUEBAS.md`](24_PRUEBAS.md).

### 7.4 Agregar una columna a una tabla de metadata

1. Editar el modelo SQLAlchemy.
2. Agregar la migración idempotente en `ensure_schema_migrations()` (`database.py`).
3. Agregar el test de migración (ver `test_validation_status_nullable_migration.py`).
4. Verificar en una base existente, no solo en una creada desde cero.

### 7.5 Agregar una variable de entorno

1. Declararla en `config.py` con default seguro.
2. Documentarla en `.env.example` y en [`26_DOCKER.md`](26_DOCKER.md) si afecta el compose.
3. Si es obligatoria en producción, usar `:?` en compose.
4. Agregar el test que falla si falta o si tiene un valor inseguro.

---

## 8. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `TypeError: Failed to fetch` sin HTTP | `localhost` resolvió a IPv6 | Usar `127.0.0.1` en `VITE_API_BASE_URL` |
| El backend arranca y rechaza la clave | `ENVIRONMENT=production` con `SECRET_KEY` default | Generar una clave nueva |
| Credenciales guardadas ilegibles | Se cambió `FERNET_KEY` | Restaurar la clave anterior o recargar credenciales |
| El chat dice "IA local no disponible" | Ollama en `localhost` dentro de Docker | Usar `host.docker.internal:11434` |
| El LLM ignora el contexto largo | Ventana fijada al arrancar (`LLM_NUM_CTX`) | Reiniciar el servidor con otra ventana |
| Se pierden los datasets subidos | El backend corre fuera del layout del repo | Mantener `data_sources/` o el volumen `data_sources_data` |
| `/docs` no aparece en producción | `ENABLE_API_DOCS` apagado | Poner `ENABLE_API_DOCS=true` solo si se necesita |
| El compose no arranca | Falta `SECRET_KEY`, `FERNET_KEY` o `POSTGRES_PASSWORD` | Completar `.env`; compose usa `:?` |
| `pytest` falla al conectar | PostgreSQL no está en 5432 | Levantar PostgreSQL local |
| El frontend muestra datos viejos | Build-time `VITE_*` | Rebuild de la imagen |

---

## 9. Seguridad operativa

### 9.1 Pilares que no se tocan

| Pilar | Archivo | Regla |
|---|---|---|
| Solo lectura | `chat_engine/ast_validator.py` | Un `SELECT`, un statement |
| RBAC fail-closed | `chat_engine/governance_guard.py` | Error → `set()` vacío |
| CLS | `governance_guard.py` + `mask_rows` | Toda fila pasa por enmascarado |
| Trazabilidad | `telemetry_audit/models.py` | `validation_status = NULL` no es aprobación |

### 9.2 Única escritura física

`catalog/services/null_manager.py` ejecuta `DELETE`/`UPDATE` **solo** desde `/catalog/connections/{id}/nulls-policy`, con:

- rol administrador,
- `confirm=true`,
- auditoría.

El chat remedia en memoria. Cualquier otro camino que escriba en la base corporativa es un bug.

### 9.3 Secretos

- `SECRET_KEY`: firma JWT.
- `FERNET_KEY`: cifra credenciales de conexión. **No rotable sin recifrar.**
- `POSTGRES_PASSWORD`: base de metadata.
- Las credenciales de conexiones corporativas se guardan cifradas, no en texto plano.

---

## 10. Depuración

```bash
# ¿Qué versión corre?
git rev-parse --short HEAD

# ¿Qué tablas hay en metadata?
psql -h localhost -U postgres -d democratizacion_metadatos -c "\dt"

# ¿Qué permisos tiene un rol?
psql -h localhost -U postgres -d democratizacion_metadatos -c \
  "SELECT r.name, p.table_name, p.is_allowed FROM roles r
   JOIN role_table_permissions p ON p.role_id = r.id ORDER BY 1,2;"

# ¿Qué columnas están bloqueadas?
psql -h localhost -U postgres -d democratizacion_metadatos -c \
  "SELECT table_name, column_name FROM role_column_permissions
   WHERE permission_type = 'BLOCKED';"

# Últimas consultas auditadas
psql -h localhost -U postgres -d democratizacion_metadatos -c \
  "SELECT timestamp, username, validation_status, rows_returned
   FROM audit_logs ORDER BY timestamp DESC LIMIT 20;"
```

> En Windows, `psql` debe estar en el PATH o usar la ruta completa de PostgreSQL.

---

## 11. Deuda técnica declarada

| Deuda | Impacto | Documento |
|---|---|---|
| Sin lint bloqueante | Estilo no verificado en CI | `20_REQUISITOS_NO_FUNCIONALES.md` §6 |
| Sin specs E2E | Flujos completos no cubiertos | `24_PRUEBAS.md` §6 |
| Sin tests de render | Componentes no verificados visualmente | `24_PRUEBAS.md` §6 |
| Sin cobertura medida | No se sabe qué líneas faltan | `20_REQUISITOS_NO_FUNCIONALES.md` §6 |
| Sin purga de auditoría | Crecimiento indefinido | `21_MODELO_DE_DATOS.md` §8 |
| Sin Alembic | No hay downgrade | `21_MODELO_DE_DATOS.md` §7 |
| `useChatEngine` y páginas grandes | Mantenibilidad | `plans/README.md` |

---

## 12. Documentos relacionados

- [Arquitectura técnica](02_ARQUITECTURA_TECNICA.md)
- [Modelo de datos](21_MODELO_DE_DATOS.md)
- [Diagramas UML](22_DIAGRAMAS_UML.md)
- [Pruebas](24_PRUEBAS.md)
- [Docker](26_DOCKER.md)
- [Estructura de directorios](07_ESTRUCTURA_DE_DIRECTORIOS.md)
