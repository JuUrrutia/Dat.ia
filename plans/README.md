# 📋 Planes de Implementación - Proyecto Datia

**Generado contra commit:** `c5f1af4`  
**Fecha:** 25 de Septiembre de 2026  
**Línea base de verificación:**
- Frontend: `npx tsc --noEmit` (0 errores)
- Backend: `py -m pytest` (103 passed, 1 failed, 253 warnings)

---

## 🗺️ Grafo de Dependencias de Ejecución

```
[001-fix-unpack-crash-and-remediation-banner]
                     │
                     ▼
[002-enforce-read-only-in-memory-null-remediation]
                     │
                     ▼
[003-connection-engine-lifecycle-and-dispose]
```

---

## 📊 Tabla de Estado y Prioridad

| ID | Plan | Impacto | Esfuerzo | Riesgo | Estado | Archivos Principales |
|---|---|---|---|---|---|---|
| **001** | [`001-fix-unpack-crash-and-remediation-banner.md`](001-fix-unpack-crash-and-remediation-banner.md) | ALTO | S | BAJO | `TODO` | `backend/app/modules/chat_engine/kpi_calculator.py`, `backend/app/modules/chat_engine/engine.py` |
| **002** | [`002-enforce-read-only-in-memory-null-remediation.md`](002-enforce-read-only-in-memory-null-remediation.md) | CRÍTICO | M | MEDIO | `TODO` | `backend/app/modules/chat_engine/engine.py`, `backend/app/modules/catalog/services/null_manager.py` |
| **003** | [`003-connection-engine-lifecycle-and-dispose.md`](003-connection-engine-lifecycle-and-dispose.md) | ALTO | M | MEDIO | `TODO` | `backend/app/modules/chat_engine/sql_executor.py`, `backend/app/core/database.py` |

---

## 📖 Instrucciones para el Ejecutor
Cada plan es completamente autocontenido. Antes de implementar:
1. Comprueba `git rev-parse --short HEAD` para detectar posible deriva (`drift`).
2. Ejecuta los comandos de verificación de línea base (`py -m pytest`).
3. Sigue estrictamente los límites de alcance y los criterios de aceptación especificados en cada documento.
