# Product Backlog

> **Documento:** 15 - Product Backlog
> **Estado:** Vigente. Historias derivadas de las funcionalidades implementadas y de los planes del repositorio.
> **Última actualización:** 30 de octubre de 2026
> **Prioridad:** MoSCoW (`Must`, `Should`, `Could`, `Won't`)

---

## 1. Cómo leer este backlog

- **ID:** `US-xx` identifica la historia; `EP-xx` la épica.
- **Estado:** ✅ Hecho · 🟡 Parcial · ⏳ Pendiente · ❌ No implementado (visión).
- **Evidencia:** archivo, endpoint o test que respalda el estado. Si no hay evidencia, la historia no se marca como hecha.
- Las historias no implementadas se conservan para que la evaluación distinga **visión** de **producto entregado**.

### Resumen

| Estado | Historias |
|---|---|
| ✅ Hecho | 57 |
| 🟡 Parcial | 3 |
| ⏳ Pendiente | 3 |
| ❌ No implementado (visión) | 3 |

---

## 2. Épicas

| ID | Épica | Objetivo | Estado |
|---|---|---|---|
| EP-01 | Acceso y seguridad | Autenticar, autorizar y proteger la sesión | ✅ |
| EP-02 | Conexiones y catálogo | Conectar datos y hacerlos comprensibles | ✅ |
| EP-03 | Consulta en lenguaje natural | Convertir preguntas en SQL seguro | ✅ |
| EP-04 | Visualización y análisis | Entregar dashboards, KPIs y trazabilidad | ✅ |
| EP-05 | Gobernanza y auditoría | RBAC, CLS y registro de todo | ✅ |
| EP-06 | Proyecciones ML | Pronosticar con evidencia y honestidad | ✅ |
| EP-07 | Informes ejecutivos | Exportar decisiones en PDF/Excel | ✅ |
| EP-08 | Administración | Gestionar usuarios, roles y políticas | ✅ |
| EP-09 | Despliegue y operación | Instalar, actualizar y respaldar | ✅ |
| EP-10 | Visión no implementada | Documentar lo que falta | ❌ |

---

## 3. Historias por épica

### EP-01 · Acceso y seguridad

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-01 | Como usuario quiero iniciar sesión con usuario y contraseña para acceder a mis datos | Must | ✅ | `backend/app/modules/auth/router.py`, `test_sessions.py` |
| US-02 | Como administrador quiero crear usuarios con clave temporal para entregar accesos sin compartir contraseñas | Must | ✅ | `test_auth_temp_password_lifecycle.py`, `TEMP_PASSWORD_TTL_DAYS` |
| US-03 | Como usuario con clave temporal quiero cambiarla en el primer login para asegurar mi cuenta | Must | ✅ | `MandatoryPasswordChangeModal`, `test_auth_temp_password_lifecycle.py` |
| US-04 | Como sistema quiero bloquear la cuenta tras 5 intentos fallidos para frenar fuerza bruta | Must | ✅ | `MAX_FAILED_LOGIN_ATTEMPTS`, `test_password_lockout.py` |
| US-05 | Como administrador quiero revocar sesiones activas para cortar accesos comprometidos | Should | ✅ | `/auth/sessions/{id}/revoke`, `test_sessions.py` |
| US-06 | Como administrador quiero gestionar roles y dominios para reflejar la estructura de la empresa | Must | ✅ | `test_admin_roles_domains_crud.py` |

### EP-02 · Conexiones y catálogo

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-07 | Como administrador quiero registrar una conexión PostgreSQL de solo lectura para consultar datos corporativos | Must | ✅ | `corporate_connections`, `test_catalog_and_connectors.py` |
| US-08 | Como administrador quiero subir CSV, Excel, SQLite o SQL para convertirlos en una base PostgreSQL | Must | ✅ | `admin_catalog/importers/`, `test_upload_dataset_least_privilege.py` |
| US-09 | Como administrador quiero probar una conexión antes de guardarla para no romper el chat | Should | ✅ | `/connectors/test`, `test_connector_integrity.py` |
| US-10 | Como usuario quiero un catálogo semántico con nombres amigables, sinónimos y fórmulas para entender los datos | Must | ✅ | `semantic_catalog`, `test_catalog_service.py` |
| US-11 | Como administrador quiero enriquecer el catálogo con IA por lotes para acelerar la documentación | Should | ✅ | `test_catalog_enricher_llm.py`, `LLM_ENRICH_*` |
| US-12 | Como administrador quiero auditar nulos y definir una política para tratar datos incompletos | Should | ✅ | `/catalog/connections/{id}/nulls-audit`, `test_nulls_audit_api.py` |
| US-13 | Como sistema quiero una sola conexión activa para que el chat no mezcle bases | Must | ✅ | `test_single_active_connector.py` |

### EP-03 · Consulta en lenguaje natural

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-14 | Como usuario quiero preguntar en español y recibir un dashboard para no escribir SQL | Must | ✅ | `/chat/query`, `engine.py` |
| US-15 | Como sistema quiero generar SQL con el LLM local y validarlo antes de ejecutarlo para no romper la base | Must | ✅ | `sql_generator.py`, `ast_validator.py` |
| US-16 | Como sistema quiero rechazar cualquier sentencia que no sea un único `SELECT` para garantizar solo lectura | Must | ✅ | `test_ast_hardening.py`, `test_ast_validator.py` |
| US-17 | Como sistema quiero reparar una vez el SQL fallido con el LLM y volver a validarlo, sin bucles | Should | ✅ | `sql_executor.py` (`execute_with_self_healing`), `test_self_healing_and_roles.py` |
| US-18 | Como usuario quiero ver la respuesta en streaming para percibir rapidez | Should | ✅ | `/chat/query/stream`, `test_chat_streaming.py` |
| US-19 | Como usuario quiero conservar hilos de conversación para retomar una consulta | Should | ✅ | `chat_conversations`, `test_chat_threads_and_context.py` |
| US-20 | Como usuario quiero compartir un hilo solo si lo marco como compartido | Could | ✅ | `is_shared`, `test_chat_shared_resource_authz.py` |
| US-21 | Como usuario quiero sugerencias de preguntas según mi rol para saber qué puedo consultar | Could | ✅ | `/chat/suggestions`, `test_suggestions_endpoint.py` |
| US-22 | Como usuario quiero que el sistema me diga cuando una pregunta está fuera de alcance | Should | ✅ | `intent_classifier.py`, `test_out_of_scope.py` |
| US-23 | Como empresa quiero elegir entre LLM central, externo o por usuario para adaptar la instalación | Should | ✅ | `LLM_MODE`, `test_llm_managed_engine.py` |
| US-24 | Como administrador quiero registrar consultas exitosas como golden queries para mejorar el contexto | Could | ✅ | `/chat/golden-query`, `test_learning_memory_governance.py` |

### EP-04 · Visualización y análisis

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-25 | Como usuario quiero gráficos adecuados al tipo de dato para entender sin leer una tabla | Must | ✅ | `kpi_calculator.py`, `src/features/dashboard/charts/` |
| US-26 | Como usuario quiero KPIs y un resumen ejecutivo para tener la conclusión primero | Must | ✅ | `response_builder.py`, `ExecutiveDashboardView` |
| US-27 | Como usuario quiero una tabla ordenable y paginada para inspeccionar el detalle | Must | ✅ | `DataGridTable.tsx` |
| US-28 | Como usuario quiero ver el SQL y el diccionario del dato para confiar en la respuesta | Must | ✅ | `TraceabilityModal.tsx`, `test_traceability_defaults.py` |
| US-29 | Como usuario quiero fijar widgets en un dashboard para volver a verlos | Could | ✅ | `dashboard_widgets`, `/chat/widgets` |
| US-30 | Como usuario quiero exportar la tabla a CSV sin fórmulas inyectadas | Should | ✅ | `test_spreadsheet_injection.py` |

### EP-05 · Gobernanza y auditoría

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-31 | Como administrador quiero definir qué tablas ve cada rol para aislar dominios | Must | ✅ | `role_table_permissions`, `test_rbac_governance.py` |
| US-32 | Como administrador quiero clasificar columnas como Permitida, Enmascarada o Bloqueada para proteger datos sensibles | Must | ✅ | `role_column_permissions`, `test_column_permissions.py` |
| US-33 | Como sistema quiero aplicar la política más restrictiva cuando dos tablas comparten columna | Must | ✅ | `test_masked_columns.py`, `governance_guard.py` |
| US-34 | Como sistema quiero que un error de permisos devuelva `set()` vacío y nunca permisos | Must | ✅ | `test_governance_fail_closed.py` |
| US-35 | Como cumplimiento quiero auditar consultas, permisos, exportaciones y errores | Must | ✅ | `audit_logs`, `test_audit_log.py`, `test_audit_log_honesty.py` |
| US-36 | Como cumplimiento quiero exportar la auditoría sin arrastrar snapshots gigantes | Should | ✅ | `/audit/export`, tope 50.000 filas |

### EP-06 · Proyecciones ML

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-37 | Como usuario quiero proyectar una métrica a 3, 6 o 12 pasos | Should | ✅ | `/ml/projections/run`, `test_ml_service_rbac.py` |
| US-38 | Como usuario quiero ver la banda, el MAPE y si le ganó al naive para no confiar en un número inventado | Must | ✅ | `test_ml_honesty.py`, `test_prediction_honesty.py` |
| US-39 | Como usuario quiero ver el historial de proyecciones y ajustar overrides | Could | ✅ | `/ml/projections/history`, `ProjectionResults` |
| US-40 | Como usuario quiero exportar la proyección al informe ejecutivo | Could | ✅ | `reports/pdf_exporter.py`, `test_reports_export.py` |

### EP-07 · Informes ejecutivos

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-41 | Como directivo quiero un informe PDF con cifras, hallazgos y recomendaciones | Should | ✅ | `/reports/export/pdf`, `pdf_exporter.py` |
| US-42 | Como analista quiero exportar el informe a Excel para seguir trabajando | Should | ✅ | `/reports/export/excel`, `excel_exporter.py` |
| US-43 | Como auditor quiero que el informe se compile desde el snapshot auditado | Should | ✅ | `data_compiler.py`, `test_reports_export.py` |

### EP-08 · Administración

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-44 | Como administrador quiero gestionar usuarios, roles y dominios desde la UI | Must | ✅ | `src/components/admin/`, `useAdminUsers` |
| US-45 | Como administrador quiero gestionar conexiones y catálogo desde la UI | Must | ✅ | `AdminConnectorsTab`, `AdminCatalogTab` |
| US-46 | Como administrador quiero ver cobertura de permisos y tablas sin ningún rol | Should | ✅ | `/permissions/coverage`, `test_governance_coverage.py` |
| US-47 | Como administrador quiero editar la política de columnas por conexión | Must | ✅ | `AdminPermissionsTab`, `test_column_permissions.py` |
| US-48 | Como administrador quiero revisar la auditoría desde la UI y exportarla | Should | ✅ | `AdminAuditTab`, `/audit/export` |

### EP-09 · Despliegue y operación

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-49 | Como operador quiero levantar el stack con Docker Compose | Must | ✅ | `docker-compose.yml`, `Dockerfile`, `backend/Dockerfile` |
| US-50 | Como cliente quiero instalar con un bundle on-prem sin Node ni Python en el host | Should | ✅ | `deploy/setup.sh`, `../DOCKER-RAPIDO.md` |
| US-51 | Como operador quiero respaldar y restaurar metadata y datos subidos | Should | ✅ | `deploy/backup.sh`, `deploy/restore.sh` |
| US-52 | Como operador quiero actualizar la versión sin perder datos | Should | ✅ | `deploy/upgrade.sh` |
| US-53 | Como operador air-gapped quiero cargar imágenes y modelos sin internet | Could | ✅ | `DATIA_SKIP_PULL`, `DATIA_SKIP_MODEL_PULL` |
| US-54 | Como operador quiero TLS y proxy confiable | Could | ✅ | `deploy/Caddyfile`, `TRUSTED_PROXY_CIDR` |
| US-55 | Como equipo quiero CI que corra tests, typecheck y build en cada PR | Must | ✅ | `.github/workflows/ci.yml` |
| US-56 | Como equipo quiero publicar imágenes multi-arquitectura y bundle en un release | Should | ✅ | `.github/workflows/release.yml` |
| US-57 | Como operador quiero healthchecks para saber si el stack está sano | Should | ✅ | `/health`, healthchecks de compose |

### EP-10 · Visión no implementada

| ID | Historia | Prioridad | Estado | Evidencia |
|---|---|---|---|---|
| US-58 | Como empresa quiero conectar MySQL/MariaDB | Won't (esta versión) | ❌ | Sin driver ni rama en `build_engine_for_connector` |
| US-59 | Como empresa quiero conectar SQL Server | Won't (esta versión) | ❌ | Sin driver ni valor en `DatabaseType` |
| US-60 | Como usuario quiero una app de escritorio (Electron/Tauri) | Won't (esta versión) | ❌ | Sin paquete ni entrypoint de escritorio |

---

## 4. Historias parciales y pendientes

| ID | Historia | Estado | Qué falta |
|---|---|---|---|
| US-61 | Como usuario quiero que el sistema aprenda de consultas exitosas | 🟡 Parcial | Memoria de aprendizaje existe; la curaduría es manual |
| US-62 | Como equipo quiero cobertura de tests de componentes React | 🟡 Parcial | Vitest cubre lógica pura; no hay renderizado de componentes |
| US-63 | Como equipo quiero lint bloqueante en CI | ⏳ Pendiente | `react-doctor` corre como advisory |
| US-64 | Como usuario quiero una evaluación de accesibilidad completa | 🟡 Parcial | Hay correcciones WCAG 2.2 AA, no una auditoría formal |
| US-65 | Como operador quiero métricas de uso y latencia | ⏳ Pendiente | Health y auditoría existen; no hay dashboard de métricas |
| US-66 | Como equipo quiero pruebas E2E versionadas | ⏳ Pendiente | `playwright.config.ts` existe; no hay specs `.spec.ts` |

---

## 5. Criterios de priorización

- **Must:** sin esto el producto no cumple su propuesta de valor o rompe un pilar de seguridad.
- **Should:** mejora sustancial de uso u operación, pero el producto funciona sin ello.
- **Could:** deseable, se posterga si compromete la entrega.
- **Won't (esta versión):** se documenta para no confundir visión con alcance.

---

## 6. Trazabilidad

Cada historia tiene un requisito funcional asociado en el [SRS](19_SRS.md). La relación inversa está en la matriz de trazabilidad de ese documento.

---

## 7. Documentos relacionados

- [Product Vision](14_PRODUCT_VISION.md)
- [Sprint Backlog](16_SPRINT_BACKLOG.md)
- [SRS](19_SRS.md)
- [Pruebas](24_PRUEBAS.md)
