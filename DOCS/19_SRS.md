# Especificación de Requisitos de Software (SRS)

> **Documento:** 19 - SRS
> **Estado:** Vigente. Requisitos derivados del código y verificados contra la suite.
> **Última actualización:** 30 de octubre de 2026
> **Estándar de referencia:** IEEE 830 (adaptado; no se certifica cumplimiento formal)
> **Alcance:** plataforma Dat.ia 1.0.0 — backend FastAPI, frontend React, PostgreSQL, LLM local y despliegue Docker

---

## 1. Introducción

### 1.1 Propósito

Definir los requisitos funcionales y las interfaces del sistema Dat.ia de forma verificable: cada requisito tiene un identificador, un criterio de aceptación y una evidencia ejecutable. Este documento no repite la visión ([`14_PRODUCT_VISION.md`](14_PRODUCT_VISION.md)) ni los requisitos no funcionales ([`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md)).

### 1.2 Alcance del sistema

Dat.ia es una aplicación web self-hosted que permite:

1. Conectar una base PostgreSQL corporativa en modo solo lectura.
2. Traducir preguntas en español a SQL mediante un LLM local.
3. Validar el SQL antes de ejecutarlo (un solo `SELECT`, tablas y columnas autorizadas).
4. Devolver un dashboard con KPIs, gráficos, tabla y trazabilidad.
5. Aplicar RBAC por dominio, tabla y columna, con enmascaramiento.
6. Proyectar series temporales con backtest y reglas de honestidad.
7. Exportar informes PDF/Excel desde el snapshot auditado.
8. Registrar consultas, permisos, exportaciones y errores en `audit_logs`.
9. Instalarse con Docker Compose o bundle on-prem, incluso air-gapped.

### 1.3 Definiciones

| Término | Significado |
|---|---|
| **RBAC** | Control de acceso basado en roles |
| **CLS** | Seguridad a nivel de columna (`ALLOWED`, `MASKED`, `BLOCKED`) |
| **AST** | Árbol de sintaxis abstracta; se usa para validar el SQL |
| **Fail-closed** | Ante error o duda, se niega el acceso |
| **Golden query** | Consulta exitosa registrada como ejemplo para el LLM |
| **Snapshot auditado** | Conjunto de datos y metadatos congelado para generar un informe |
| **Conector** | Registro de una base de datos corporativa o de un dataset importado |
| **Dominio** | Agrupación lógica de tablas (Finanzas, RRHH, TI…) |

### 1.4 Actores

| Actor | Descripción | Rol base |
|---|---|---|
| Usuario consultor | Consulta datos según sus permisos | `Usuario Consultor` |
| Analista financiero | Explora ventas, clientes y márgenes | `Analista Financiero & Comercial` |
| Director ejecutivo | Consume KPIs e informes consolidados | `Director Ejecutivo (C-Level)` |
| Gerente de talento | Consulta plantilla y encuestas sin ver sueldos | `Gerente de Talento & Operaciones` |
| Analista de BI | Explora infraestructura y datos operativos | `Analista de Datos & BI` |
| Ingeniero de TI | Diagnostica salud, servidores e incidentes | `Ingeniero de Infraestructura & TI` |
| Oficial de cumplimiento | Audita accesos, consultas y exportaciones | `Oficial de Cumplimiento & Seguridad` |
| Administrador | Gestiona usuarios, roles, conexiones y políticas | `Administrador de Plataforma` |
| Sistema LLM | Genera SQL y narrativa; no decide permisos | Servicio local |
| Operador | Instala, respalda y actualiza el stack | Fuera de la aplicación |

> Los ocho roles están definidos en `backend/app/core/constants.py:6-13`. `ADMIN_ROLES` contiene solo `Administrador de Plataforma` (`constants.py:15-17`).

---

## 2. Requisitos funcionales

### 2.1 Convenciones

- **ID:** `RF-<módulo>-<nn>`.
- **Prioridad:** `Must` / `Should` / `Could`.
- **Estado:** ✅ implementado · 🟡 parcial · ⏳ pendiente · ❌ fuera de alcance.
- **Verificación:** test, archivo o comando que respalda el estado. Si la evidencia es un test, el nombre es el archivo real en `backend/tests/`.

---

### 2.2 Módulo AUTH — Autenticación y sesiones

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-AUTH-01 | El sistema debe autenticar con usuario y contraseña y emitir un JWT con vigencia de 24 horas | Must | ✅ | `test_sessions.py`; `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24` (`config.py:78`) |
| RF-AUTH-02 | El sistema debe bloquear la cuenta tras 5 intentos fallidos durante 15 minutos | Must | ✅ | `test_password_lockout.py`; `constants.py:23-24` |
| RF-AUTH-03 | El administrador debe poder crear usuarios con contraseña temporal de 7 días | Must | ✅ | `test_auth_temp_password_lifecycle.py`; `TEMP_PASSWORD_TTL_DAYS` (`config.py:84`) |
| RF-AUTH-04 | Un usuario con contraseña temporal debe cambiarla antes de operar | Must | ✅ | `test_auth_temp_password_lifecycle.py`, `MandatoryPasswordChangeModal` |
| RF-AUTH-05 | El sistema debe registrar cada sesión y actualizar `last_seen` cada 5 minutos | Should | ✅ | `test_sessions.py`; `SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES` (`constants.py:25`) |
| RF-AUTH-06 | El administrador debe poder revocar una sesión o todas las de un usuario | Must | ✅ | `test_password_change_revocation.py`; `/auth/sessions/{id}/revoke`, `/auth/users/{id}/revoke-all-sessions` |
| RF-AUTH-07 | El usuario debe poder cambiar su propia contraseña y las sesiones previas deben quedar invalidadas | Must | ✅ | `test_password_change_revocation.py` |
| RF-AUTH-08 | El administrador debe poder restablecer la contraseña de un usuario | Should | ✅ | `/auth/users/{user_id}/reset-password`, `test_create_admin_password.py` |
| RF-AUTH-09 | Un usuario desactivado no debe poder autenticarse ni conservar sesiones | Must | ✅ | `test_auth_deactivation.py` |

**Criterio de aceptación AUTH:** con credenciales válidas se obtiene un token usable en `/auth/me`; con 5 fallos la cuenta responde bloqueada; al cambiar contraseña, el token anterior deja de servir.

---

### 2.3 Módulo RBAC — Autorización y gobernanza

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-RBAC-01 | El administrador debe poder crear, editar y eliminar roles y dominios | Must | ✅ | `test_admin_roles_domains_crud.py` |
| RF-RBAC-02 | El sistema debe decidir qué tablas ve cada rol; sin permiso, la tabla no es visible | Must | ✅ | `test_rbac_governance.py`, `test_table_permissions_default_deny.py` |
| RF-RBAC-03 | El sistema debe clasificar cada columna como `ALLOWED`, `MASKED` o `BLOCKED` por rol | Must | ✅ | `test_column_permissions.py` |
| RF-RBAC-04 | Si dos tablas comparten una columna con políticas distintas, debe aplicarse la más restrictiva | Must | ✅ | `test_masked_columns.py` |
| RF-RBAC-05 | Ante un error al resolver permisos, el sistema debe devolver `set()` vacío, nunca permisos | Must | ✅ | `test_governance_fail_closed.py` |
| RF-RBAC-06 | El sistema debe informar cobertura de permisos y tablas sin ningún rol | Should | ✅ | `test_governance_coverage.py`; `/permissions/coverage` |
| RF-RBAC-07 | El catálogo y las anomalías no deben revelar datos fuera del rol | Must | ✅ | `test_no_role_catalog_and_anomalies.py`, `test_anomalies_rbac.py` |
| RF-RBAC-08 | Los endpoints administrativos deben exigir rol administrador | Must | ✅ | `test_admin_endpoint_auth.py` |
| RF-RBAC-09 | `SELECT *` no debe poder evadir columnas bloqueadas | Must | ✅ | `test_cls_select_star.py` |

**Criterio de aceptación RBAC:** un rol sin permiso sobre `empleados` no ve la tabla en el catálogo ni puede consultarla; una columna `BLOCKED` no aparece en la respuesta ni en el SQL final; un error de base de permisos devuelve vacío.

---

### 2.4 Módulo CAT — Conexiones, ingesta y catálogo

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-CAT-01 | El administrador debe poder registrar una conexión PostgreSQL con credenciales cifradas | Must | ✅ | `test_catalog_and_connectors.py`; `corporate_connections` (`admin_catalog/models.py`) |
| RF-CAT-02 | El sistema debe probar la conexión antes de guardarla | Should | ✅ | `test_connector_integrity.py`; `/connectors/test` |
| RF-CAT-03 | Solo puede haber una conexión activa a la vez | Must | ✅ | `test_single_active_connector.py`; `/connectors/{id}/toggle-active` |
| RF-CAT-04 | El sistema debe importar CSV, Excel, SQLite y SQL a PostgreSQL con privilegios mínimos | Must | ✅ | `test_upload_dataset_least_privilege.py`; `admin_catalog/importers/` |
| RF-CAT-05 | El catálogo semántico debe admitir nombre amigable, sinónimos, descripción y fórmula | Must | ✅ | `test_catalog_service.py`; `semantic_catalog` |
| RF-CAT-06 | El enriquecimiento con IA debe ejecutarse por lotes con presupuesto y timeout | Should | ✅ | `test_catalog_enricher_llm.py`, `test_catalog_enricher_honesty.py`; `LLM_ENRICH_*` (`config.py:118-120`) |
| RF-CAT-07 | El sistema debe auditar nulos y permitir una política por conexión | Should | ✅ | `test_nulls_audit_api.py`, `test_null_policy_and_visualizations.py` |
| RF-CAT-08 | La remediación de nulos del chat debe ser en memoria; la escritura física solo por endpoint admin con `confirm=true` y auditoría | Must | ✅ | `test_null_manager.py`; `catalog/services/null_manager.py` |
| RF-CAT-09 | El sistema debe exponer el diccionario de datos respetando RBAC | Should | ✅ | `test_data_dictionary_rbac.py`; `/catalog/data-dictionary` |
| RF-CAT-10 | El sistema debe validar que el host del LLM sea privado cuando corresponda | Must | ✅ | `test_chat_llm_private_host.py`, `test_llm_sink_validation.py` |

**Criterio de aceptación CAT:** una conexión con credenciales incorrectas no se guarda como activa; un CSV importado queda consultable; una política de nulos no puede ejecutarse sin `confirm=true` y sin rol administrador.

---

### 2.5 Módulo CHAT — Consulta en lenguaje natural

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-CHAT-01 | El usuario debe poder enviar una pregunta en español y recibir un dashboard | Must | ✅ | `test_chat_security.py`; `/chat/query` |
| RF-CHAT-02 | El sistema debe generar SQL con el LLM local a partir del esquema autorizado | Must | ✅ | `sql_generator.py`; `test_dynamic_schema.py` |
| RF-CHAT-03 | Todo SQL debe pasar por el validador AST: un solo `SELECT`, sin DDL/DML ni múltiples sentencias | Must | ✅ | `test_ast_validator.py`, `test_ast_hardening.py` |
| RF-CHAT-04 | El validador debe rechazar tablas no permitidas y columnas bloqueadas | Must | ✅ | `test_ast_hardening.py`; `ast_validator.py` |
| RF-CHAT-05 | Si la ejecución falla por un error no estructural, el sistema debe intentar una reparación con el LLM y revalidar el SQL | Should | ✅ | `test_self_healing_and_roles.py`; `sql_executor.py` (`execute_with_self_healing`) |
| RF-CHAT-06 | Si la tabla no existe en la fuente activa, el sistema debe fallar sin gastar minutos en reparaciones | Should | ✅ | `sql_executor.py` (pre-flight de tablas físicas) |
| RF-CHAT-07 | La respuesta debe poder emitirse en streaming | Should | ✅ | `test_chat_streaming.py`, `test_stream_interruption_e2e.py`; `/chat/query/stream` |
| RF-CHAT-08 | El usuario debe poder conservar y retomar hilos de conversación | Should | ✅ | `test_chat_threads_and_context.py`, `test_chat_thread_isolation.py` |
| RF-CHAT-09 | Un hilo solo debe ser visible para otro usuario si fue marcado como compartido | Must | ✅ | `test_chat_shared_resource_authz.py`, `test_chat_thread_isolation.py` |
| RF-CHAT-10 | El sistema debe sugerir preguntas según el rol | Could | ✅ | `test_suggestions_endpoint.py`; `/chat/suggestions` |
| RF-CHAT-11 | El sistema debe clasificar preguntas fuera de alcance y rechazarlas con explicación | Should | ✅ | `test_out_of_scope.py`, `test_intent_classifier.py` |
| RF-CHAT-12 | El sistema debe soportar `LLM_MODE=central`, `external` y `user` | Should | ✅ | `test_llm_managed_engine.py`, `test_chat_llm_settings.py` |
| RF-CHAT-13 | El usuario debe poder registrar feedback y golden queries | Could | ✅ | `test_learning_memory_governance.py`; `/chat/feedback`, `/chat/golden-query` |
| RF-CHAT-14 | El sistema debe aislar el prompt de instrucciones inyectadas en los datos | Must | ✅ | `test_prompt_isolation.py` |
| RF-CHAT-15 | El sistema debe podar el esquema a las tablas relevantes antes de prompting | Should | ✅ | `test_dynamic_schema.py`, `test_physical_schema_cache.py` |

**Criterio de aceptación CHAT:** una pregunta sobre una tabla permitida devuelve filas y SQL; un `DELETE`, un `DROP`, un `;` múltiple o una tabla prohibida se rechazan antes de tocar la base; un error de sintaxis no estructural se repara una vez y se revalida.

---

### 2.6 Módulo VIZ — Visualización y análisis

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-VIZ-01 | El sistema debe calcular KPIs a partir de las filas devueltas | Must | ✅ | `test_kpi_arithmetic.py`; `kpi_calculator.py` |
| RF-VIZ-02 | El sistema debe elegir el gráfico según el tipo y cardinalidad de los datos | Must | ✅ | `test_agnostic_visualization.py`; `src/features/dashboard/charts/` |
| RF-VIZ-03 | El usuario debe ver una tabla ordenable, paginable y buscable | Must | ✅ | `DataGridTable.tsx` |
| RF-VIZ-04 | El usuario debe ver el SQL ejecutado, la base objetivo y el diccionario del dato | Must | ✅ | `test_traceability_defaults.py`, `test_traceability_target_database.py`; `TraceabilityModal.tsx` |
| RF-VIZ-05 | El usuario debe poder fijar widgets en un dashboard | Could | ✅ | `/chat/widgets`; `dashboard_widgets` |
| RF-VIZ-06 | La exportación CSV debe neutralizar fórmulas inyectadas | Must | ✅ | `test_spreadsheet_injection.py` |
| RF-VIZ-07 | Un valor no medido debe mostrarse como ausente, nunca como cero | Must | ✅ | `test_prediction_honesty.py`, `test_ml_honesty.py` |
| RF-VIZ-08 | El sistema debe detectar consultas lentas y anomalías operativas | Should | ✅ | `test_anomalies_rbac.py`; `SLOW_QUERY_THRESHOLD_MS = 4000` (`constants.py:35`) |

**Criterio de aceptación VIZ:** una consulta de ventas por mes muestra línea o barras con KPI; el modal de trazabilidad permite copiar un SQL ejecutable; un campo sin dato se muestra "—".

---

### 2.7 Módulo ML — Proyecciones

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-ML-01 | El usuario debe poder proyectar una métrica a 3, 6 o 12 pasos | Should | ✅ | `test_ml_service_rbac.py`; `/ml/projections/run` |
| RF-ML-02 | El sistema debe ofrecer los métodos `naive`, `mean` y `ols_trend` | Should | ✅ | `test_ml_models.py`; `METHODS` (`ml_models.py:59`) |
| RF-ML-03 | El sistema debe hacer backtest walk-forward y reportar MAPE y banda | Must | ✅ | `test_ml_models_properties.py`, `test_forecast_properties.py` |
| RF-ML-04 | El sistema debe declarar si el modelo le gana al naive (`beats_naive`) | Must | ✅ | `test_ml_honesty.py` |
| RF-ML-05 | Si no hay historia suficiente, el sistema debe devolver "no disponible", no un número inventado | Must | ✅ | `test_prediction_honesty.py`; `_unavailable()` (`ml_models.py:112`) |
| RF-ML-06 | Las proyecciones deben respetar el RBAC de la tabla consultada | Must | ✅ | `test_ml_service_rbac.py`; `test_predict_rbac_and_budget.py` |
| RF-ML-07 | El usuario debe poder ver el historial y ajustar overrides | Could | ✅ | `/ml/projections/history`, `ProjectionResults` |
| RF-ML-08 | La proyección debe poder incorporarse al informe ejecutivo | Could | ✅ | `test_reports_export.py`; `pdf_exporter.py` |

**Criterio de aceptación ML:** con 24 meses de historia, la proyección devuelve banda y MAPE; con 3 puntos, devuelve `disponible=false` con motivo; si el modelo no supera al naive, `beats_naive=false` y la UI no lo presenta como mejora.

---

### 2.8 Módulo REP — Informes ejecutivos

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-REP-01 | El usuario debe poder exportar el informe a PDF | Should | ✅ | `test_reports_export.py`; `/reports/export/pdf` |
| RF-REP-02 | El usuario debe poder exportar el informe a Excel | Should | ✅ | `test_reports_export.py`; `/reports/export/excel` |
| RF-REP-03 | El informe debe compilarse desde el snapshot auditado, no desde una consulta nueva | Should | ✅ | `data_compiler.py`, `test_reports_export.py` |
| RF-REP-04 | El informe debe incluir cifras, hallazgos, recomendaciones y SQL auditado | Should | ✅ | `pdf_exporter.py`, `excel_exporter.py` |
| RF-REP-05 | La exportación debe partir del snapshot ya enmascarado y revalidar que el usuario sea dueño del registro o administrador | Must | ✅ | `generator.py:105-121` (403/404); `test_reports_export.py` |

---

### 2.9 Módulo ADM — Administración

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-ADM-01 | El administrador debe gestionar usuarios, roles y dominios desde la UI | Must | ✅ | `src/components/admin/`, `useAdminUsers`, `test_admin_roles_domains_crud.py` |
| RF-ADM-02 | El administrador debe gestionar conexiones y catálogo desde la UI | Must | ✅ | `AdminConnectorsTab`, `AdminCatalogTab` |
| RF-ADM-03 | El administrador debe editar la política de columnas por conexión | Must | ✅ | `AdminPermissionsTab`, `test_column_permissions.py` |
| RF-ADM-04 | El administrador debe revisar y exportar la auditoría desde la UI | Should | ✅ | `AdminAuditTab`, `/audit/export` |
| RF-ADM-05 | El administrador debe ver el estado de la política LLM | Should | ✅ | `/system/llm-policy`, `test_chat_llm_settings.py` |
| RF-ADM-06 | Cambiar el rol de un usuario debe respetar el catálogo de roles | Must | ✅ | `test_user_role_update.py`, `test_role_label_is_catalog_or_nothing.py` |

---

### 2.10 Módulo OPS — Operación y despliegue

| ID | Requisito | Prioridad | Estado | Verificación |
|---|---|---|---|---|
| RF-OPS-01 | El sistema debe exponer un health check con estado de base y LLM | Must | ✅ | `test_system_health.py`; `/health` |
| RF-OPS-02 | El stack debe levantarse con Docker Compose sin publicar la base ni el backend | Must | ✅ | `docker-compose.yml`; `DOCKER-RAPIDO.md` |
| RF-OPS-03 | El cliente debe poder instalar con un bundle on-prem sin Node ni Python en el host | Should | ✅ | `deploy/setup.sh`, `deploy/README.md` |
| RF-OPS-04 | El operador debe poder respaldar, restaurar y actualizar sin perder datos | Should | ✅ | `deploy/backup.sh`, `deploy/restore.sh`, `deploy/upgrade.sh` |
| RF-OPS-05 | El operador air-gapped debe poder cargar imágenes y modelos sin internet | Could | ✅ | `DATIA_SKIP_PULL`, `DATIA_SKIP_MODEL_PULL` |
| RF-OPS-06 | El sistema debe funcionar detrás de TLS y proxy confiable | Could | ✅ | `deploy/Caddyfile`, `TRUSTED_PROXY_CIDR` |
| RF-OPS-07 | El CI debe correr backend, frontend, typecheck y build en cada PR | Must | ✅ | `.github/workflows/ci.yml` |
| RF-OPS-08 | El release debe publicar imágenes multi-arquitectura y bundle | Should | ✅ | `.github/workflows/release.yml` |
| RF-OPS-09 | La auditoría debe exportarse con un tope de 50.000 filas | Should | ✅ | `/audit/export`; `test_audit_log.py` |
| RF-OPS-10 | La base de metadatos debe crearse al arrancar si no existe | Must | ✅ | `test_database_autocreate.py`; `init_db` |
| RF-OPS-11 | El modo demo debe estar gateado por `DEMO_MODE` | Must | ✅ | `test_demo_mode_gating.py` |

---

## 3. Requisitos de interfaz

### 3.1 Interfaz de usuario

| Elemento | Requisito |
|---|---|
| Navegación | Rutas protegidas por sesión; `/login` público; redirección a login sin token |
| Cambio de clave temporal | Modal obligatorio no dismissible hasta completar el cambio |
| Dashboard | KPIs, gráficos, tabla y trazabilidad en una sola vista |
| Administración | Pestañas de usuarios, roles, dominios, conectores, catálogo, permisos y auditoría |
| Accesibilidad | Contraste WCAG 2.2 AA en los componentes revisados (no hay auditoría formal) |
| Idioma | Español |

### 3.2 Interfaz de programación

- Prefijo: `/api/v1`.
- Autenticación: `Authorization: Bearer <JWT>`.
- Formato: JSON; errores con `detail`.
- Endpoints por módulo: auth, admin_catalog, chat_engine, ml_forecast, system, telemetry_audit.
- Documentación OpenAPI en `/docs` solo si `ENABLE_API_DOCS=true`; en producción está apagada por defecto.

### 3.3 Interfaces externas

| Interfaz | Uso | Configuración |
|---|---|---|
| PostgreSQL | Metadatos y datos corporativos | `POSTGRES_*`; conexión corporativa cifrada con Fernet |
| LLM local | Generación de SQL y narrativa | `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OPENAI_COMPATIBLE_URL` |
| Sistema de archivos | Datasets subidos | `data_sources/` (volumen en Docker) |
| Navegador | Cliente web | `VITE_API_BASE_URL` (build-time) |

### 3.4 Interfaz de datos

El modelo completo está en [`21_MODELO_DE_DATOS.md`](21_MODELO_DE_DATOS.md). Resumen:

- 13 tablas de metadatos de la plataforma.
- 9 tablas demo (4 dimensiones, 5 hechos) creadas por `setup_postgres_full.py`.
- `audit_logs.validation_status` es nullable: `NULL` = sin registro, no "APROBADO".

---

## 4. Matriz de trazabilidad

### 4.1 Historias → requisitos

| Historia | Requisito |
|---|---|
| US-01, US-05 | RF-AUTH-01, RF-AUTH-06 |
| US-02, US-03 | RF-AUTH-03, RF-AUTH-04 |
| US-04 | RF-AUTH-02 |
| US-06 | RF-RBAC-01 |
| US-07, US-09 | RF-CAT-01, RF-CAT-02 |
| US-08 | RF-CAT-04 |
| US-10 | RF-CAT-05 |
| US-11 | RF-CAT-06 |
| US-12 | RF-CAT-07, RF-CAT-08 |
| US-13 | RF-CAT-03 |
| US-14 | RF-CHAT-01 |
| US-15, US-16 | RF-CHAT-02, RF-CHAT-03, RF-CHAT-04 |
| US-17 | RF-CHAT-05, RF-CHAT-06 |
| US-18 | RF-CHAT-07 |
| US-19, US-20 | RF-CHAT-08, RF-CHAT-09 |
| US-21 | RF-CHAT-10 |
| US-22 | RF-CHAT-11 |
| US-23 | RF-CHAT-12 |
| US-24 | RF-CHAT-13 |
| US-25, US-26 | RF-VIZ-01, RF-VIZ-02 |
| US-27 | RF-VIZ-03 |
| US-28 | RF-VIZ-04 |
| US-29 | RF-VIZ-05 |
| US-30 | RF-VIZ-06 |
| US-31, US-32, US-33, US-34 | RF-RBAC-02, RF-RBAC-03, RF-RBAC-04, RF-RBAC-05 |
| US-35, US-36 | RF-OPS-09; `audit_logs` |
| US-37, US-38, US-39, US-40 | RF-ML-01 a RF-ML-08 |
| US-41, US-42, US-43 | RF-REP-01 a RF-REP-05 |
| US-44, US-45, US-46, US-47, US-48 | RF-ADM-01 a RF-ADM-05 |
| US-49 a US-57 | RF-OPS-01 a RF-OPS-08 |

### 4.2 Requisitos sin historia (de soporte)

| Requisito | Motivo |
|---|---|
| RF-AUTH-07, RF-AUTH-08, RF-AUTH-09 | Endurecimiento posterior al backlog inicial |
| RF-RBAC-06, RF-RBAC-07, RF-RBAC-08, RF-RBAC-09 | Hallazgos de auditoría y CLS |
| RF-CAT-09, RF-CAT-10 | Diccionario y validación de host LLM |
| RF-CHAT-14, RF-CHAT-15 | Aislamiento de prompt y poda de esquema |
| RF-VIZ-07, RF-VIZ-08 | Honestidad del dato y anomalías |
| RF-OPS-10, RF-OPS-11 | Arranque y gating de demo |

### 4.3 Cobertura

| Módulo | Requisitos | Implementados | Parciales | Pendientes |
|---|---:|---:|---:|---:|
| AUTH | 9 | 9 | 0 | 0 |
| RBAC | 9 | 9 | 0 | 0 |
| CAT | 10 | 10 | 0 | 0 |
| CHAT | 15 | 15 | 0 | 0 |
| VIZ | 8 | 8 | 0 | 0 |
| ML | 8 | 8 | 0 | 0 |
| REP | 5 | 5 | 0 | 0 |
| ADM | 6 | 6 | 0 | 0 |
| OPS | 11 | 11 | 0 | 0 |
| **Total** | **81** | **81** | **0** | **0** |

> Los requisitos "parcial" y "pendiente" del proyecto son de **calidad y proceso**, no funcionales: cobertura de componentes React, lint bloqueante, specs E2E, métricas de uso y curaduría de aprendizaje. Están en [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) §4 y en [`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md).

---

## 5. Requisitos funcionales fuera de alcance

| Requisito | Estado | Motivo |
|---|---|---|
| Conectar MySQL/MariaDB | ❌ | Sin driver ni rama en `build_engine_for_connector` |
| Conectar SQL Server | ❌ | Sin driver ni valor en `DatabaseType` |
| App de escritorio Electron/Tauri | ❌ | Sin paquete ni entrypoint |
| SaaS multi-empresa | ❌ | Diseño on-prem por empresa |
| App móvil nativa | ❌ | Interfaz web responsive |
| Entrenamiento de modelos con datos del cliente | ❌ | El LLM es de inferencia, no se entrena |

---

## 6. Supuestos y dependencias

- El host tiene PostgreSQL 16+ disponible en el puerto 5432.
- El LLM corre localmente o en un endpoint privado alcanzable.
- El navegador soporta ES2020 y `fetch` con streaming.
- El operador provee `SECRET_KEY`, `FERNET_KEY` y `POSTGRES_PASSWORD` en Docker.
- Los datos demo solo se cargan con `DEMO_MODE=true`.
- La ventana de contexto del LLM se fija al arrancar; cambiarla exige reiniciar el servidor.

---

## 7. Trazabilidad con otros documentos

| Documento | Relación |
|---|---|
| [`01_VISION_Y_ALCANCE.md`](01_VISION_Y_ALCANCE.md) | Visión y alcance original |
| [`02_ARQUITECTURA_TECNICA.md`](02_ARQUITECTURA_TECNICA.md) | Arquitectura que implementa estos requisitos |
| [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) | Historias de usuario |
| [`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md) | RNF |
| [`21_MODELO_DE_DATOS.md`](21_MODELO_DE_DATOS.md) | Modelo de datos |
| [`22_DIAGRAMAS_UML.md`](22_DIAGRAMAS_UML.md) | Casos de uso y secuencias |
| [`24_PRUEBAS.md`](24_PRUEBAS.md) | Cómo se verifica cada requisito |

---

## 8. Historial de cambios

| Fecha | Cambio |
|---|---|
| 30/10/2026 | Versión inicial del SRS a partir del código y la suite de 844 tests |
