# 📋 Planes de Implementación - Proyecto Datia

**Origen:** auditoría del commit `c5f1af4` (25 de Septiembre de 2026)  
**Estado revisado:** contra el árbol actual, no contra `c5f1af4`.

> Las cifras de línea base del documento de auditoría (`103 passed, 1 failed`)
> quedaron desactualizadas: la suite de `backend/tests/` tiene hoy del orden de
> 500 tests en 65 archivos. Verificar con `cd backend && pytest` antes de
> fiarse de cualquier plan.

---

## 📊 Estado de cada plan

| ID | Plan | Estado | Qué dice el código hoy |
|---|---|---|---|
| **001** | [`001-fix-unpack-crash-and-remediation-banner.md`](001-fix-unpack-crash-and-remediation-banner.md) | ✅ **Implementado** | `build_dynamic_visualization` devuelve 5 elementos también con `rows`/`columns` vacíos (`kpi_calculator.py:155-168`); `engine.py:25` importa `logger`; el banner se antepone con `if is_remediation:` y no depende de que `conversational` sea truthy (`engine.py:530-532`). |
| **002** | [`002-enforce-read-only-in-memory-null-remediation.md`](002-enforce-read-only-in-memory-null-remediation.md) | ⛔ **NO implementado** | `engine.py:230` sigue llamando `NullManagerService.apply_null_policy(...)`, que ejecuta `DELETE`/`UPDATE` contra la base corporativa y hace `commit` (`null_manager.py:218-333`). La vía en memoria (`apply_in_memory_remediation`) existe y se usa, pero convive con la mutación física: el pilar de solo lectura sigue roto. |
| **003** | [`003-connection-engine-lifecycle-and-dispose.md`](003-connection-engine-lifecycle-and-dispose.md) | ✅ **Implementado con otro diseño** | El plan pedía un `ConnectorEngineRegistry` con caché. Lo que hay es `connector_engine()` (`core/database.py:276-292`), un contextmanager que hace `dispose()` al salir, y `sql_executor.py:39-41` lo usa con `with`. Sin caché, a propósito (ver el docstring). El fallo que motiva el plan —pools huérfanos— está resuelto. |

---

## 📌 Único plan pendiente

**002** es el que queda. Antes de tocarlo, tener en cuenta:

- Es el único hallazgo de la auditoría que sigue siendo un problema de
  **seguridad de datos**, no de estabilidad ni de rendimiento.
- `apply_null_policy` tiene ya un contrato de resultado (`status`,
  `rows_affected`, `message`) y revierte la política si falla; el trabajo es
  quitar la rama que escribe en la base de origen, no reescribir el servicio.
- Las pruebas que lo cubren están en
  `backend/tests/test_null_policy_and_visualizations.py`.

---

## 📖 Instrucciones para el Ejecutor

1. Comprueba `git rev-parse --short HEAD` para detectar posible deriva (`drift`).
2. Ejecuta `cd backend && pytest` para tener la línea base real.
3. Sigue estrictamente los límites de alcance y los criterios de aceptación
   especificados en el documento del plan.