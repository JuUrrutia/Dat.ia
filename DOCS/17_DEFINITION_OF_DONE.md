# Definition of Done (DoD)

> **Documento:** 17 - Definición de Terminado
> **Estado:** Vigente. Deriva de `AGENTS.md`, del CI y de los cuatro pilares de Datia.
> **Última actualización:** 30 de octubre de 2026

---

## 1. Principio

Una historia está **terminada** cuando el incremento es verificable por otra persona, no cuando "funciona en mi máquina". La evidencia es la salida real de un comando o un test que falla si el comportamiento se rompe.

> Si no se ejecutó, no está terminado. Si se ejecutó y falló, no está terminado. Si se ejecutó y pasó, se pega la salida.

---

## 2. Checklist general

### Código

- [ ] El cambio compila: `npx tsc --noEmit` termina con exit 0.
- [ ] El build de producción termina: `npm run build` exit 0.
- [ ] La suite de backend pasa: `cd backend; venv\Scripts\python.exe -m pytest -q`.
- [ ] La suite de frontend pasa: `npm test`.
- [ ] No se agregaron `console.log`, `print()` de depuración ni `TODO` sin dueño.
- [ ] No se agregaron dependencias sin justificar por qué una ya instalada no alcanza.
- [ ] El diff se revisó completo, no solo el archivo que se tocó.

### Seguridad (pilares)

- [ ] Todo SQL del chat pasa por `ast_validator.py`: un solo `SELECT`, sin DDL/DML.
- [ ] RBAC es fail-closed: ante error, `set()` vacío, nunca permisos.
- [ ] Toda fila que llega al usuario pasa por `mask_rows`; las columnas `BLOCKED` no se devuelven.
- [ ] Los cambios de permisos y las consultas quedan en `audit_logs`.
- [ ] El chat no modifica la base del cliente; la remediación de nulos es en memoria.
- [ ] No se agregaron secretos, claves ni rutas absolutas al repositorio.

### Datos

- [ ] Las migraciones son idempotentes y no destructivas.
- [ ] `validation_status = NULL` sigue significando "sin registro", no "APROBADO".
- [ ] Los cambios de esquema se prueban contra PostgreSQL, no solo contra mocks.
- [ ] Los datos demo siguen gateados por `DEMO_MODE`.

### Documentación

- [ ] El cambio actualiza el documento afectado (README, DOCS, plan).
- [ ] Los enlaces son relativos y resuelven.
- [ ] No se agregaron cifras sin comando que las respalde.
- [ ] Si cambió una funcionalidad, se actualizó el [Product Backlog](15_PRODUCT_BACKLOG.md) o el [SRS](19_SRS.md).
- [ ] No se declaró "implementado" algo que solo está en visión.

### Operación

- [ ] `docker compose config` es válido con las variables requeridas.
- [ ] Si cambió una variable de entorno, se actualizaron `.env.example`, README y manual.
- [ ] Si cambió el esquema o los volúmenes, se verificó backup/restore.
- [ ] El healthcheck sigue respondiendo.

---

## 3. Comandos y evidencia

| Comando | Qué prueba | Última salida verificada |
|---|---|---|
| `cd backend; venv\Scripts\python.exe -m pytest -q` | Backend completo | **844 passed, 244 subtests, 396,55 s** (30/10/2026) |
| `npm test` | Lógica del frontend | **18 archivos, 135 tests, 6,56 s** (30/10/2026) |
| `npx tsc --noEmit` | Tipos de todo el proyecto | **exit 0** (30/10/2026) |
| `npm run build` | Build de producción | **exit 0, 10,72 s; echarts 665,26 kB** (30/10/2026) |

> Las cifras se actualizan cuando cambian. Si no coinciden con la última corrida, el documento está desactualizado y la historia no está terminada.

---

## 4. DoD por tipo de cambio

### Historia de producto

1. Criterio de aceptación escrito.
2. Test que falla sin el cambio y pasa con él.
3. RBAC/CLS/auditoría verificados si toca datos.
4. Documentación y backlog actualizados.
5. Salida de los cuatro comandos pegada en el informe.

### Corrección de bug

1. Causa raíz identificada (no solo el síntoma).
2. Test de regresión que reproduce el bug.
3. Revisión de todos los callers de la función tocada.
4. Efecto diferido evaluado: ¿explota ahora o al reiniciar / con datos reales?
5. Sin cambios colaterales no pedidos.

### Cambio de documentación

1. Enlaces relativos y resolubles.
2. Afirmaciones con archivo/línea o test.
3. Cifras con fecha y comando.
4. Sin duplicar la fuente de verdad: se enlaza al documento canónico.
5. Revisión de que no contradice el código actual.

### Release

1. Suite completa verde.
2. `docker compose build` y `docker compose config` válidos.
3. Bundle on-prem generado y probado en un host limpio (o límite declarado).
4. Backup/restore verificados.
5. Notas de release con cambios y limitaciones.

---

## 5. Lo que el DoD no exige (todavía)

| Práctica | Estado | Motivo |
|---|---|---|
| Lint bloqueante | ❌ No exigido | `react-doctor` corre como advisory |
| Umbral de cobertura | ❌ No exigido | No hay `coverage` configurado como gate |
| Tests de renderizado de componentes | ❌ No exigido | Vitest corre en entorno node |
| Specs E2E versionadas | ❌ No exigido | Playwright está configurado, sin specs |
| Mutation testing | ❌ No exigido | No hay campaña configurada |
| Pruebas de carga | ❌ No exigido | No hay benchmarks de concurrencia |

Estas ausencias son deuda declarada, no un "done" implícito.

---

## 6. Documentos relacionados

- [Metodología](13_METODOLOGIA.md)
- [Sprint Backlog](16_SPRINT_BACKLOG.md)
- [Retrospectivas](18_RETROSPECTIVAS.md)
- [Pruebas](24_PRUEBAS.md)
- [README](../README.md)
