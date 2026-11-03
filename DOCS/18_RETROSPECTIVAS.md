# Retrospectivas

> **Documento:** 18 - Retrospectivas del proyecto
> **Estado:** Reconstruidas a partir de auditorías y planes reales. No son actas de reunión.
> **Última actualización:** 30 de octubre de 2026

---

## 1. Cómo leer estas retrospectivas

El equipo no levantó actas de retrospectiva en cada sprint. Este documento reconstruye las retrospectivas que **sí dejaron evidencia** en el repositorio: auditorías, planes de implementación y commits de cierre.

Cada retrospectiva responde cuatro preguntas:

1. **Contexto:** qué pasó y cuándo.
2. **Qué funcionó:** prácticas que se conservan.
3. **Qué dolió:** problemas concretos, no quejas genéricas.
4. **Acciones:** qué se hizo, con qué evidencia y en qué estado quedó.

> Las fechas son las de la auditoría o del plan que originó la retrospectiva. No se inventaron reuniones.

---

## 2. Retrospectiva 1 — La auditoría que cambió el rumbo

**Fecha:** 28 de septiembre de 2026
**Disparador:** auditoría integral [`DOCS/11`](11_AUDITORIA_INTEGRAL_Y_PLAN_DE_TRABAJO.md) sobre el commit `c5f1af4`
**Línea base de la auditoría:** 103 tests aprobados, 1 fallido

### Qué funcionó

- La suite detectó una regresión real (`test_prompt2_remediation_answers_original_question`).
- El equipo tenía trazabilidad suficiente para escribir tres planes con evidencia de archivo y línea.
- El pipeline de gobernanza (RBAC + AST) ya existía; el problema era de implementación, no de diseño.

### Qué dolió

| Hallazgo | Impacto |
|---|---|
| Crash por desempaquetado cuando la consulta devolvía cero filas | El chat caía en consultas vacías |
| `DELETE`/`UPDATE` en la base corporativa durante la remediación de nulos | Violaba el pilar de solo lectura |
| Fuga de pools de SQLAlchemy por consulta | Agotamiento de conexiones en producción |
| Mock fallback con IDs aleatorios | Ocultaba fallos de red y desincronizaba estado |
| Documentación de Electron como si estuviera implementado | Visión confundida con producto |

### Acciones

| Acción | Evidencia | Estado |
|---|---|---|
| Corregir el desempaquetado y el banner de remediación | [Plan 001](../plans/001-fix-unpack-crash-and-remediation-banner.md) | ✅ |
| Remediación de nulos solo en memoria; escritura física únicamente por endpoint admin con confirmación y auditoría | [Plan 002](../plans/002-enforce-read-only-in-memory-null-remediation.md) | ✅ |
| Cerrar el ciclo de vida del engine con `connector_engine()` y `dispose()` | [Plan 003](../plans/003-connection-engine-lifecycle-and-dispose.md) | ✅ |
| Declarar Electron como visión no implementada | README y `DOCS/01` | ✅ |

### Lección

**Una auditoría sin plan no cambia nada; un plan sin test de regresión tampoco.** Los tres planes se cerraron con tests que fallan si el bug vuelve.

---

## 3. Retrospectiva 2 — El costo de la sobreingeniería

**Fecha:** 19 de octubre de 2026
**Disparador:** [Plan 004](../plans/004-reduccion-de-sobreingenieria.md), auditoría de código muerto, duplicación y abstracciones especulativas

### Qué funcionó

- Se borró código en lugar de agregarlo: `holt_damped`, `thinking_process` y una API key inerte salieron del árbol.
- Se eliminaron **222,4 MB de dependencias** según el plan 004.
- Se unificó la resolución de la conexión del pedido: un `connection_id` inexistente devuelve 404, no un fallback silencioso.
- Se dejó un solo seeder de metadata (`init_db`).

### Qué dolió

- Había abstracciones para escenarios que nunca existieron.
- La duplicación de lógica hacía que dos archivos "coincidieran por memoria".
- El frontend tenía componentes gigantes y utilidades sin uso.
- El plan 004 quedó con un lote de Docker/deps/scripts pendiente por exigir un build limpio.

### Acciones

| Acción | Evidencia | Estado |
|---|---|---|
| Ejecutar fases 1–4 del plan 004 | Commits del 19/10 | ✅ |
| Partir `DatabaseWizardModal`, sacar `validate_and_secure_sql` del umbral C901 y extraer la rama conversacional | Plan 004, fase 5 (21–22/10) | ✅ |
| Mantener `useChatEngine`, `ChatDashboardPage`, `router.py` e `init_db.py` como deuda por demanda | `plans/README.md` | 🟡 Declarado |
| Cerrar el lote Docker/deps/scripts | Requiere build limpio | ⏳ Pendiente |

### Lección

**La deuda más cara no es la que falta, es la que sobra.** Cada abstracción especulativa se paga en cada lectura y en cada test.

---

## 4. Retrospectiva 3 — Medir antes de opinar

**Fecha:** 21 de octubre de 2026
**Disparador:** [Plan 005](../plans/005-medicion-base.md), línea base de medición

### Qué funcionó

- Se midió antes de corregir: knip, bundle, complejidad y código muerto.
- Se documentaron los números con comando y fecha, no con impresiones.
- La limpieza posterior bajó knip a 0 y el chunk de echarts a 665,26 kB (verificado en el build del 30/10/2026).

### Qué dolió

- No había una línea base anterior; el equipo discutía sobre percepciones.
- La medición se hizo con el árbol de trabajo sucio, así que no todo era atribuible a un commit.
- El plan 005 no corrió pytest: la suite se midió después, por separado.

### Acciones

| Acción | Evidencia | Estado |
|---|---|---|
| Medir knip, bundle, ruff C901 y vulture | Plan 005 | ✅ |
| Bajar exports/tipos sin uso a 0 | `npm run knip` exit 0 (reportado en `plans/README`) | ✅ |
| Reducir echarts de 1.053,95 kB a 665,26 kB | Build del 30/10/2026 | ✅ |
| Eliminar `any` de `api_client.ts` y `types/index.ts` | Plan 005 / limpieza posterior | ✅ |

### Lección

**Sin línea base no hay mejora, solo relato.** El número que no se midió antes no se puede defender después.

---

## 5. Retrospectiva 4 — El release on-prem y la deriva documental

**Fecha:** 29 de octubre de 2026
**Disparador:** cierre del release on-prem (bundle, GHCR, permisos por columna) y revisión de documentación

### Qué funcionó

- El producto se puede instalar sin Node ni Python en el host.
- El release publica imágenes multi-arquitectura y un bundle autocontenido.
- La administración de permisos por columna quedó en la UI.
- La suite quedó en **844 passed, 244 subtests** al 30/10/2026.

### Qué dolió

| Problema | Evidencia |
|---|---|
| `DOCS/README.md` usaba enlaces absolutos `file:///c:/Users/Felipe/...` | No resuelven en GitHub ni en otra máquina |
| `DOCS/07` decía `plans/001–003` | Ya existían 001–005 |
| `plans/README` decía "~500 tests en 65 archivos" | Hay 91 archivos de test backend |
| El diagrama de metadata afirmaba un fallback a SQLite | `core/database.py` dice lo contrario |
| El diagrama Docker mostraba puertos que ya no existen | El compose actual no publica el backend |
| Los PDFs de Fase 1 no eran legibles por una máquina | 10 PDFs con nombre y formato no indexable |
| El README no enlazaba a `DOCS/` | Un evaluador no encontraba la documentación |

### Acciones

| Acción | Evidencia | Estado |
|---|---|---|
| Crear un hub de documentación con los 17 entregables | `DOCS/README.md` | ✅ |
| Llevar el contenido de Fase 1 a Markdown | `DOCS/12`, `DOCS/13` | ✅ |
| Mover los PDFs a `DOCS/entregables-academicos/fase-1/` y renombrarlos | `DOCS/entregables-academicos/` | ✅ |
| Actualizar `DOCS/07`, `plans/README` y el README | Este cambio | ✅ |
| Reemplazar enlaces absolutos por relativos en documentos vigentes | Link checker | ✅ |
| Declarar los diagramas PNG desactualizados y usar Mermaid como fuente | `DOCS/22` | ✅ |

### Lección

**La documentación también se pudre.** Un enlace absoluto, un conteo viejo o un diagrama sin regenerar hacen más daño que la ausencia del documento: crean confianza falsa.

---

## 6. Lecciones transversales

1. **Verificar antes de afirmar.** El informe de un subagente o un número de memoria no es evidencia.
2. **Un test que no se ejecuta no existe.** Los "tests" de grep del frontend se reemplazaron por Vitest real.
3. **Fail-closed no es un eslogan.** Ante error de permisos, se devuelve vacío; sobre-bloquear se nota, filtrar no.
4. **La deuda de seguridad se paga a las 3 a.m.** El plan 002 nació de un `DELETE` que no debía existir.
5. **La documentación es parte del producto.** Si el README no lleva a los documentos, el trabajo no se ve.
6. **Medir antes y después.** Sin línea base, cualquier mejora es una opinión.

---

## 7. Acciones abiertas

| Acción | Prioridad | Estado |
|---|---|---|
| Cerrar el lote Docker/deps/scripts del plan 004 | Media | ⏳ |
| Agregar lint bloqueante en CI | Alta | ⏳ |
| Versionar specs E2E de Playwright | Alta | ⏳ |
| Tests de renderizado de componentes | Media | ⏳ |
| Tablero de métricas de uso y latencia | Media | ⏳ |
| Regenerar o retirar los PNG históricos de `DOCS/imagenes/` | Baja | ⏳ |

---

## 8. Documentos relacionados

- [Metodología](13_METODOLOGIA.md)
- [Sprint Backlog](16_SPRINT_BACKLOG.md)
- [Definition of Done](17_DEFINITION_OF_DONE.md)
- [Auditoría integral](11_AUDITORIA_INTEGRAL_Y_PLAN_DE_TRABAJO.md)
- [Planes](../plans/README.md)
