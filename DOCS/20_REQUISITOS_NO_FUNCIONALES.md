# Requisitos No Funcionales (RNF)

> **Documento:** 20 - Requisitos No Funcionales
> **Estado:** Vigente. Cada RNF tiene un valor real medido o una constante del código.
> **Última actualización:** 30 de octubre de 2026
> **Referencia:** ISO/IEC 25010 (adaptado)

---

## 1. Cómo se leen

- **ID:** `RNF-<categoría>-<nn>`.
- **Objetivo:** el valor que el sistema debe cumplir.
- **Verificación:** cómo se comprueba; si no hay medición, se declara.
- **Estado:** ✅ cumplido · 🟡 parcial · ⏳ no verificado.

> Las cifras de tiempo de suite y build corresponden a la corrida del **30/10/2026** en el equipo de desarrollo. No son un SLA de producción.

---

## 2. Rendimiento y eficiencia

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-PERF-01 | Tiempo máximo de una consulta SQL | 15 s | `QUERY_TIMEOUT_SECONDS = 15` (`config.py:124`) | ✅ |
| RNF-PERF-02 | Filas máximas devueltas por consulta | 500 | `DEFAULT_ROW_LIMIT = 500` (`config.py:123`); se aplica en el prompt (`prompts.py:185`) | ✅ |
| RNF-PERF-03 | Health check | < 5 s | Medición registrada en el commit `perf(health): 61 s -> 3,7 s` (03/10/2026); no re-medida en esta sesión | ✅ documentado |
| RNF-PERF-04 | Consulta lenta marcada como anomalía | > 4.000 ms | `SLOW_QUERY_THRESHOLD_MS = 4000` (`constants.py:35`) | ✅ |
| RNF-PERF-05 | Suite backend completa | < 10 min | **396,55 s** (6:36) el 30/10/2026 | ✅ |
| RNF-PERF-06 | Suite frontend | < 30 s | **6,56 s**, 18 archivos, 135 tests | ✅ |
| RNF-PERF-07 | Typecheck | < 30 s | **~9 s**, exit 0 | ✅ |
| RNF-PERF-08 | Build de producción | < 60 s | **10,72 s**, exit 0 | ✅ |
| RNF-PERF-09 | Chunk principal de gráficos | < 700 kB | `echarts` **665,26 kB** (warning esperado de Vite) | ✅ |
| RNF-PERF-10 | Enriquecimiento de catálogo por lote | 6 columnas por llamada; 120 s por tabla; 360 s total | `LLM_ENRICH_COLUMNS_PER_CALL`, `LLM_ENRICH_TABLE_TIMEOUT_S`, `LLM_ENRICH_TOTAL_BUDGET_S` (`config.py:118-120`) | ✅ |
| RNF-PERF-11 | Pool de conexiones a metadata | 10 + 20 overflow | `pool_size=10`, `max_overflow=20` (`database.py:85-86`) | ✅ |
| RNF-PERF-12 | Pool de conexiones corporativas | 5 + 10 overflow | `pool_size=5`, `max_overflow=10` (`database.py:352-353`) | ✅ |
| RNF-PERF-13 | Carga máxima de subida | 512 MB | `client_max_body_size 512m` (`nginx.conf:31`) | ✅ |
| RNF-PERF-14 | Rate limit de autenticación | 10 req/min por IP | `limit_req_zone ... datia_auth rate=10r/m` (`nginx.conf:7`) | ✅ |
| RNF-PERF-15 | Rate limit de API | 20 req/s por IP | `datia_api rate=20r/s` (`nginx.conf:8`) | ✅ |

> **Límite declarado:** no se ejecutaron pruebas de carga ni benchmarks de concurrencia. Los valores de pool y rate limit son configuración, no capacidad medida.

---

## 3. Seguridad

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-SEC-01 | Solo lectura sobre datos del cliente | 100% de las consultas del chat | `ast_validator.py`; `test_ast_hardening.py` | ✅ |
| RNF-SEC-02 | RBAC fail-closed | Ante error, `set()` vacío | `test_governance_fail_closed.py` | ✅ |
| RNF-SEC-03 | Enmascaramiento de columnas | `BLOCKED` nunca llega al usuario | `mask_rows`; `test_masked_columns.py`, `test_masked_conversational_branch.py` | ✅ |
| RNF-SEC-04 | Sesión | 24 h de vigencia | `ACCESS_TOKEN_EXPIRE_MINUTES = 1440` (`config.py:78`) | ✅ |
| RNF-SEC-05 | Bloqueo por fuerza bruta | 5 intentos / 15 min | `constants.py:23-24`; `test_password_lockout.py` | ✅ |
| RNF-SEC-06 | Contraseña temporal | 7 días | `TEMP_PASSWORD_TTL_DAYS = 7` (`config.py:84`) | ✅ |
| RNF-SEC-07 | Credenciales de conexión | Cifradas con Fernet | `security.py`; `FERNET_KEY` | ✅ |
| RNF-SEC-08 | Cabeceras de seguridad | CSP, `nosniff`, `DENY`, `no-referrer`, `Permissions-Policy` | `nginx.conf:47-51` | ✅ |
| RNF-SEC-09 | Superficie expuesta | Solo el frontend publica puerto; backend y base en red interna | `docker-compose.yml` (backend sin `ports`, Postgres con `ports` comentado) | ✅ |
| RNF-SEC-10 | Contenedores sin root | Backend UID 10001; frontend nginx unprivileged (8080) | `backend/Dockerfile:55`, `Dockerfile:27` | ✅ |
| RNF-SEC-11 | LLM local o privado | Sin llamadas a APIs públicas por defecto | `test_chat_llm_private_host.py`, `test_llm_sink_validation.py` | ✅ |
| RNF-SEC-12 | Inyección de prompt | Los datos no deben convertirse en instrucciones | `test_prompt_isolation.py` | ✅ |
| RNF-SEC-13 | Inyección de fórmulas en CSV | Neutralizada | `test_spreadsheet_injection.py` | ✅ |
| RNF-SEC-14 | Multi-tenant | No aplica: una instalación por empresa | `14_PRODUCT_VISION.md` §9 | ✅ por diseño |
| RNF-SEC-15 | Auditoría | Toda consulta, permiso y exportación registrada | `audit_logs`; `test_audit_log.py`, `test_audit_log_honesty.py` | ✅ |

> **Límite declarado:** no hay pentest externo ni escaneo de dependencias bloqueante en CI. La seguridad se sostiene en tests y revisión, no en una certificación.

---

## 4. Fiabilidad y disponibilidad

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-REL-01 | Health check | Reporta estado de base y LLM | `/health`; `test_system_health.py` | ✅ |
| RNF-REL-02 | Reinicio de contenedores | `unless-stopped` en los tres servicios | `docker-compose.yml:8,35,100` | ✅ |
| RNF-REL-03 | Conexiones muertas | `pool_pre_ping=True` | `database.py:323` | ✅ |
| RNF-REL-04 | Host que no responde | Corte a los 5–10 s, no 130 s | `connect_timeout` (`database.py:51,88,358`) | ✅ |
| RNF-REL-05 | Migraciones | Idempotentes, con `lock_timeout=3s` | `database.py:124-125`; `test_database_autocreate.py` | ✅ |
| RNF-REL-06 | Backup y restore | Scripts provistos y documentados | `deploy/backup.sh`, `deploy/restore.sh` | ✅ documentado |
| RNF-REL-07 | Actualización sin pérdida | `deploy/upgrade.sh` | `deploy/README.md` | ✅ documentado |
| RNF-REL-08 | Corrupción de snapshot | Responde 409, no un documento a medias | `generator.py:118-133` | ✅ |
| RNF-REL-09 | Error de permisos al exportar | 403 antes de generar el archivo | `generator.py:109-115`; `test_reports_export.py` | ✅ |
| RNF-REL-10 | Disponibilidad objetivo | No medida | Sin SLO ni monitoreo externo | ⏳ |

> **Límite declarado:** no hay alta disponibilidad, réplica ni failover. El diseño es una instalación on-prem única.

---

## 5. Usabilidad y accesibilidad

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-USE-01 | Idioma de la interfaz | Español | UI y mensajes de error | ✅ |
| RNF-USE-02 | Curva de uso | Un usuario no técnico pregunta en lenguaje natural | Flujo `/chat` sin SQL visible por defecto | ✅ |
| RNF-USE-03 | Explicabilidad | SQL, base objetivo y diccionario a un clic | `TraceabilityModal.tsx`; `test_traceability_target_database.py` | ✅ |
| RNF-USE-04 | Contraste | WCAG 2.2 AA en componentes revisados | Commit de UX/UI (21/09/2026) | 🟡 parcial |
| RNF-USE-05 | Navegación por teclado | Componentes interactivos alcanzables | Revisión manual; sin auditoría formal | 🟡 parcial |
| RNF-USE-06 | Mensajes de error | Explican la causa y la acción | `detail` en API y toasts en UI | ✅ |
| RNF-USE-07 | Cambio de clave temporal | Modal obligatorio, no dismissible | `MandatoryPasswordChangeModal.tsx` | ✅ |
| RNF-USE-08 | Responsive | Uso en laptop y monitor externo | Layout con breakpoints | ✅ |
| RNF-USE-09 | Estados vacíos | "Sin datos" no es un error | Componentes de dashboard | ✅ |

> **Límite declarado:** no hay auditoría de accesibilidad formal (axe, lector de pantalla) ni tests de renderizado. Las correcciones WCAG son puntuales.

---

## 6. Mantenibilidad y calidad

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-MAIN-01 | Suite backend | 844 tests, 244 subtests, 0 fallos | `pytest -q` del 30/10/2026 | ✅ |
| RNF-MAIN-02 | Suite frontend | 135 tests en 18 archivos, 0 fallos | `npm test` del 30/10/2026 | ✅ |
| RNF-MAIN-03 | Tipado | `tsc --noEmit` exit 0 | 30/10/2026 | ✅ |
| RNF-MAIN-04 | Build | `npm run build` exit 0 | 30/10/2026 | ✅ |
| RNF-MAIN-05 | CI | Backend, frontend, typecheck y build en cada PR | `.github/workflows/ci.yml` | ✅ |
| RNF-MAIN-06 | Código muerto | 0 exports y 0 tipos sin uso | `npm run knip` (advisory) | ✅ medido |
| RNF-MAIN-07 | Complejidad | Sin funciones sobre C901 | `ruff check backend/app --select C901` (advisory) | ✅ medido |
| RNF-MAIN-08 | Lint bloqueante | Debería bloquear el merge | `react-doctor` corre como advisory | ⏳ |
| RNF-MAIN-09 | Cobertura | Umbral mínimo | No hay gate de cobertura configurado | ⏳ |
| RNF-MAIN-10 | Tests de componentes | Renderizado React | Vitest corre en entorno node | ⏳ |
| RNF-MAIN-11 | Specs E2E | Versionadas | `playwright.config.ts` sin `.spec.ts` | ⏳ |
| RNF-MAIN-12 | Documentación | Cada cambio actualiza su documento | DoD (`17_DEFINITION_OF_DONE.md`) | ✅ proceso |

> **Límite declarado:** "844 tests" es el número de casos, no de asserts ni de cobertura de líneas. No se midió cobertura.

---

## 7. Portabilidad y compatibilidad

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-PORT-01 | Instalación en host limpio | Sin Node ni Python | `deploy/setup.sh`; bundle on-prem | ✅ |
| RNF-PORT-02 | Contenedores multi-etapa | Imágenes slim/alpine | `Dockerfile`, `backend/Dockerfile` | ✅ |
| RNF-PORT-03 | Multi-arquitectura | `amd64` y `arm64` | `.github/workflows/release.yml` | ✅ |
| RNF-PORT-04 | Air-gapped | Carga de imágenes y modelos sin internet | `DATIA_SKIP_PULL`, `DATIA_SKIP_MODEL_PULL` | ✅ |
| RNF-PORT-05 | Base de datos | PostgreSQL 16 | `postgres:16.15-alpine` | ✅ |
| RNF-PORT-06 | Runtime backend | Python 3.13 | `python:3.13-slim` | ✅ |
| RNF-PORT-07 | Runtime frontend | Node 24 (build) + nginx 1.31 | `node:24.22.1-alpine`, `nginxinc/nginx-unprivileged:1.31.7-alpine` | ✅ |
| RNF-PORT-08 | Navegadores | Chrome, Edge y Firefox recientes | Sin matriz formal de pruebas | 🟡 parcial |
| RNF-PORT-09 | Sistema operativo del host | Linux (producción) y Windows (desarrollo) | Scripts `.sh` y `.bat/.ps1` | ✅ |
| RNF-PORT-10 | Otros motores | MySQL / SQL Server / Oracle | No implementado | ❌ fuera de alcance |

---

## 8. Escalabilidad y límites

| ID | Requisito | Objetivo | Realidad |
|---|---|---|---|
| RNF-SCA-01 | Usuarios concurrentes | No medido | Un proceso Uvicorn; sin benchmark |
| RNF-SCA-02 | Tamaño de dataset | No medido | Depende de PostgreSQL y del hardware |
| RNF-SCA-03 | Conexiones activas | Una por instalación | `test_single_active_connector.py` (decisión de producto) |
| RNF-SCA-04 | Escalado horizontal | Fuera de alcance | Sin réplica ni sesiones compartidas |

> **Decisión consciente:** Dat.ia prioriza soberanía y simplicidad sobre escala horizontal. Una empresa que necesite multi-tenant o HA requiere otro diseño, no un flag.

---

## 9. Privacidad y cumplimiento

| ID | Requisito | Objetivo | Verificación | Estado |
|---|---|---|---|---|
| RNF-PRIV-01 | Soberanía | El dato no sale de la infraestructura | LLM local/privado; sin telemetría | ✅ |
| RNF-PRIV-02 | Minimización | El LLM solo ve tablas y columnas autorizadas | Poda de esquema; `test_dynamic_schema.py` | ✅ |
| RNF-PRIV-03 | Trazabilidad | Saber quién consultó qué y cuándo | `audit_logs` | ✅ |
| RNF-PRIV-04 | Retención | Política de borrado | No hay purga automática configurada | ⏳ |
| RNF-PRIV-05 | Datos personales | Enmascarar columnas sensibles | `MASKED`/`BLOCKED` | ✅ |
| RNF-PRIV-06 | Exportación | Solo el dueño o un admin | `generator.py:109-115` | ✅ |

> **Límite declarado:** no se certifica cumplimiento de GDPR, Ley 19.628 ni normativa sectorial. Se proveen los mecanismos (RBAC, CLS, auditoría); la configuración y el cumplimiento son responsabilidad del operador.

---

## 10. Resumen de cumplimiento

| Categoría | Requisitos | ✅ | 🟡 | ⏳ | ❌ |
|---|---:|---:|---:|---:|---:|
| Rendimiento | 15 | 15 | 0 | 0 | 0 |
| Seguridad | 15 | 15 | 0 | 0 | 0 |
| Fiabilidad | 10 | 9 | 0 | 1 | 0 |
| Usabilidad | 9 | 7 | 2 | 0 | 0 |
| Mantenibilidad | 12 | 8 | 0 | 4 | 0 |
| Portabilidad | 10 | 8 | 1 | 0 | 1 |
| Privacidad | 6 | 5 | 0 | 1 | 0 |
| **Total** | **77** | **67** | **3** | **6** | **1** |

> Escalabilidad no se marca ✅/⏳ porque sus cuatro filas son **límites declarados**, no requisitos con objetivo medible. Se excluye del total.

### Deuda no funcional abierta

| Deuda | Impacto | Cuándo pagarla |
|---|---|---|
| Lint bloqueante | Un error de estilo puede entrar a `main` | Antes del próximo release |
| Specs E2E | Regresiones de flujo completo no detectadas | Al estabilizar la UI |
| Tests de componentes | Errores de render no cubiertos | Al agregar features de UI |
| Métricas de uso y latencia | No hay evidencia operativa | Al primer cliente en producción |
| Purga de auditoría | Crecimiento indefinido de `audit_logs` | Al definir política de retención |
| Accesibilidad formal | Riesgo de incumplimiento | Antes de despliegue público |

---

## 11. Documentos relacionados

- [SRS](19_SRS.md)
- [Pruebas](24_PRUEBAS.md)
- [Manual técnico](23_MANUAL_TECNICO.md)
- [Docker](26_DOCKER.md)
- [Definition of Done](17_DEFINITION_OF_DONE.md)
