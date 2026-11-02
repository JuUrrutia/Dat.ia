# Innovación y Aporte Diferencial

> **Documento:** 25 - Innovación
> **Estado:** Vigente. Cada afirmación se ancla en una funcionalidad verificable del repositorio.
> **Última actualización:** 30 de octubre de 2026
> **Advertencia:** este documento distingue **innovación de integración** de **invención tecnológica**. Dat.ia no inventó un modelo, un algoritmo ni un protocolo.

---

## 1. Qué se entiende por innovación aquí

Innovar no es usar la tecnología más nueva. Es resolver un problema real con una combinación que antes no estaba disponible para el usuario objetivo. En Dat.ia la innovación está en **integrar** cinco piezas que normalmente viven separadas:

1. LLM local.
2. Gobernanza de datos fail-closed.
3. Catálogo semántico editable.
4. Analítica conversacional con trazabilidad.
5. Despliegue on-prem air-gapped.

Ninguna es nueva por separado. La combinación —y las decisiones de seguridad que la hacen usable en una empresa— sí es el aporte.

---

## 2. Aportes diferenciales

### 2.1 Soberanía sin renunciar al lenguaje natural

| Aspecto | Cómo está resuelto | Evidencia |
|---|---|---|
| El dato no sale de la red | LLM local (Ollama, llama.cpp, LM Studio, vLLM) | `LLMService`, `LLM_PROVIDER` |
| El modelo no se entrena con datos del cliente | Solo inferencia | `14_PRODUCT_VISION.md` §9 |
| El host del LLM se valida | Rechazo de hosts públicos cuando corresponde | `test_chat_llm_private_host.py`, `test_llm_sink_validation.py` |
| La instalación funciona sin internet | Bundle on-prem y modo air-gapped | `deploy/README.md`, `DATIA_SKIP_PULL` |

**Por qué importa:** la objeción típica a la analítica conversacional es "no puedo mandar mis ventas a OpenAI". Dat.ia elimina esa objeción por arquitectura, no por contrato.

### 2.2 Gobernanza en tres capas, no en una

| Capa | Qué impide | Dónde |
|---|---|---|
| **Dominio** | Que un rol consulte tablas de otra área | `check_domain_governance` |
| **Tabla** | Que vea una tabla no asignada | `role_table_permissions` |
| **Columna** | Que vea un dato sensible | `role_column_permissions` + `mask_rows` |
| **SQL** | Que la consulta haga algo distinto a leer | `ast_validator.py` |

**Diferencia:** la mayoría de los asistentes Text-to-SQL validan el SQL o aplican permisos, no ambas cosas en serie y con fail-closed. Aquí el LLM **nunca** decide permisos: propone SQL y el validador lo acepta o lo rechaza.

**Evidencia:** `test_governance_fail_closed.py`, `test_ast_hardening.py`, `test_masked_columns.py`, `test_cls_select_star.py`.

### 2.3 Trazabilidad que sirve para auditar, no solo para depurar

Cada respuesta incluye:

- la pregunta original,
- el SQL final ejecutado,
- la base objetivo,
- las tablas usadas,
- el estado de validación,
- el tiempo y las filas,
- el snapshot exportable.

**Diferencia:** el SQL que se muestra es el que se ejecutó, no el que el LLM "quiso" ejecutar. Si hubo auto-reparación, queda marcado `APROBADO (Auto-Corregido)`.

**Evidencia:** `test_audit_log.py`, `test_audit_log_honesty.py`, `test_traceability_target_database.py`, `test_sql_is_runnable_as_copied.py`.

### 2.4 Honestidad estadística en las proyecciones

| Regla | Comportamiento | Evidencia |
|---|---|---|
| Sin historia suficiente | Devuelve "no disponible" con motivo | `_unavailable()` en `ml_models.py` |
| Modelo que no supera al naive | `beats_naive = false` | `test_ml_honesty.py` |
| Banda por paso | Intervalo, no una línea sola | `build_projection` |
| Backtest walk-forward | Evalúa con datos que el modelo no vio | `test_ml_models_properties.py` |
| Métodos acotados | `naive`, `mean`, `ols_trend` | `METHODS` |

**Diferencia:** un dashboards de forecasting suele mostrar una línea hacia arriba sin decir si el modelo es mejor que "repetir el último valor". Aquí el veredicto contra el naive es parte de la respuesta.

### 2.5 Nulos: decidir sin romper el dato

- El chat detecta nulos y ofrece acciones.
- La remediación del chat es **en memoria**: no modifica la base.
- La escritura física existe solo en un endpoint administrativo, con `confirm=true` y auditoría.

**Diferencia:** es fácil "limpiar" datos con un `UPDATE`; es difícil hacerlo sin destruir información. La separación entre remediación conversacional y política administrativa es una decisión de producto poco común.

**Evidencia:** `test_null_manager.py`, `test_nulls_audit_api.py`, `DOCS/11` y plan 002.

### 2.6 Catálogo semántico que el LLM puede usar

- Nombres amigables, sinónimos, descripción y fórmula de negocio.
- Enriquecimiento asistido por IA por lotes, con presupuesto y timeout.
- El catálogo se poda al rol antes de construir el prompt.

**Diferencia:** el LLM no adivina que `monto_total` es "ventas netas"; lo lee del catálogo. Y no ve tablas que el rol no puede consultar.

**Evidencia:** `test_catalog_service.py`, `test_catalog_enricher_llm.py`, `test_dynamic_schema.py`.

### 2.7 Instalación on-prem real

| Requisito | Cómo se cumple |
|---|---|
| Sin Node ni Python en el host | Imágenes publicadas |
| Sin exposición de la base | Postgres sin puerto publicado |
| Sin exposición del backend en dev | Backend solo por red interna |
| Actualización sin pérdida | `deploy/upgrade.sh` |
| Respaldo y restore | `deploy/backup.sh`, `deploy/restore.sh` |
| Air-gapped | Carga manual de imágenes y modelos |
| TLS | Caddy o LB de la empresa |

**Diferencia:** muchas demos de Text-to-SQL se quedan en `npm run dev`. Aquí hay un bundle operable.

---

## 3. Comparación con el estado típico

| Capacidad | Asistente Text-to-SQL típico | Dat.ia |
|---|---|---|
| LLM | API en la nube | Local o privado |
| Permisos | A nivel de aplicación | Dominio + tabla + columna |
| Validación SQL | Parcial o ausente | AST obligatorio, un `SELECT` |
| Datos sensibles | Filtro manual | `MASKED` / `BLOCKED` + `mask_rows` |
| Auditoría | Logs de aplicación | `audit_logs` con snapshot y SQL final |
| Proyecciones | No incluye | Backtest + veredicto vs naive |
| Informes | No incluye | PDF/Excel desde snapshot auditado |
| Despliegue | Servicio cloud | On-prem / air-gapped |
| Costo de IA | Por token | Cero licencias |

> La comparación es conceptual, no un benchmark. No se midió latencia, precisión de SQL ni satisfacción contra otros productos.

---

## 4. Lo que **no** es innovación

Declararlo evita que la evaluación confunda marketing con ingeniería:

| Afirmación | Realidad |
|---|---|
| "Modelo propio" | ❌ Se usan modelos abiertos de terceros (Qwen, Llama, Mistral) |
| "Entrenamiento con datos del cliente" | ❌ No hay entrenamiento; solo inferencia |
| "RAG / base vectorial" | ❌ No hay embeddings ni búsqueda vectorial; se usa poda de esquema y catálogo |
| "Agentes autónomos" | ❌ Es un pipeline determinista con un LLM en dos puntos |
| "Auto-corrección infinita" | ❌ Una reparación acotada y revalidación |
| "Multi-tenant" | ❌ Una instalación por empresa |
| "Alta disponibilidad" | ❌ Un solo nodo; sin failover |
| "Soporte multi-motor" | ❌ Solo PostgreSQL |

---

## 5. Madurez tecnológica

| Dimensión | Nivel | Evidencia |
|---|---|---|
| Funcionalidad | Producto usable | 844 tests, build verde, bundle on-prem |
| Seguridad | Endurecida, sin certificación | Pilares + tests + auditoría |
| Operación | Documentada | `deploy/`, `DOCKER-RAPIDO.md` |
| Escalabilidad | No validada | Sin pruebas de carga |
| Accesibilidad | Parcial | Correcciones WCAG puntuales |
| Madurez comercial | Piloto | Sin clientes en producción documentados |

> No se asigna un TRL numérico: sería una precisión falsa. El estado real es **prototipo avanzado / piloto operable**.

---

## 6. Aporte académico

| Aporte | Descripción |
|---|---|
| Caso de estudio | Integración de IA local con gobernanza de datos en un contexto académico real |
| Evidencia reproducible | Suite de 844 tests y comandos documentados |
| Decisiones trazables | Planes 001–005, auditoría `DOCS/11`, retrospectivas |
| Límites declarados | Visión vs producto, deuda técnica y ausencias explícitas |
| Metodología | Scrum declarado y ejecución reconstruida desde commits |

**Lo más defendible no es la feature, es la trazabilidad de las decisiones:** por qué se retiró `holt_damped`, por qué el chat no escribe, por qué `validation_status` es nullable, por qué el admin salta el RBAC.

---

## 7. Líneas de evolución

| Línea | Valor | Esfuerzo | Estado |
|---|---|---|---|
| Specs E2E y lint bloqueante | Calidad sostenible | Bajo | Pendiente |
| Métricas de uso y latencia | Operación basada en datos | Medio | Pendiente |
| Purga y retención de auditoría | Cumplimiento | Medio | Pendiente |
| Más motores (MySQL/SQL Server) | Cobertura de clientes | Alto | No implementado |
| Multi-tenant | SaaS | Muy alto | Fuera de alcance |
| Fine-tuning local | Mejor SQL en dominios específicos | Alto | No implementado |
| RAG sobre catálogo | Mejor recuperación semántica | Medio | No implementado |

> Cada línea requiere un plan con criterio de aceptación antes de tocar código. La lista no es un compromiso.

---

## 8. Documentos relacionados

- [Product Vision](14_PRODUCT_VISION.md)
- [Visión y alcance](01_VISION_Y_ALCANCE.md)
- [SRS](19_SRS.md)
- [Requisitos no funcionales](20_REQUISITOS_NO_FUNCIONALES.md)
- [Pruebas](24_PRUEBAS.md)
