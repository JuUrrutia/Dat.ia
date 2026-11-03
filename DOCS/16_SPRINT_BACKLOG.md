# Sprint Backlog

> **Documento:** 16 - Sprint Backlog e historial de iteraciones
> **Estado:** Reconstruido a partir de commits, planes y auditorías. No hubo tablero formal.
> **Última actualización:** 30 de octubre de 2026
> **Fuente:** `git log` del repositorio (144 commits entre el 16/08/2026 y el 29/10/2026) y `plans/001–005`

---

## 1. Cómo se reconstruyó

El equipo declaró Scrum en Fase 1, pero no usó Jira, Trello ni un tablero con story points. Para no inventar un historial, este documento agrupa los **commits reales** por hitos de producto y los cruza con las historias del [Product Backlog](15_PRODUCT_BACKLOG.md).

- Las fechas son el rango real de commits.
- Las historias asignadas son las que esos commits implementaron o tocaron; una historia puede cruzar iteraciones.
- Los "resultados" se verifican contra la suite de tests y el estado actual, no contra una promesa de planificación.
- **No se declara velocity ni capacidad en puntos.** No existe ese registro.

---

## 2. Resumen

| Sprint | Periodo | Commits | Objetivo | Estado |
|---|---|---:|---|---|
| Sprint 0 | 16–25 ago 2026 | 42 | Fundación y MVP web | ✅ Cerrado |
| Sprint 1 | 4–21 sep 2026 | 8 | Entregables Fase 1 y estabilización | ✅ Cerrado |
| Sprint 2 | 28 sep–5 oct 2026 | 32 | Auditoría y gobernanza | ✅ Cerrado |
| Sprint 3 | 8–19 oct 2026 | 40 | Proyecciones, informes y reducción de deuda | ✅ Cerrado |
| Sprint 4 | 22–29 oct 2026 | 22 | Permisos por columna y entrega on-prem | ✅ Cerrado |

---

## 3. Sprint 0 — Fundación y MVP

| Campo | Valor |
|---|---|
| **Periodo** | 16–25 de agosto de 2026 |
| **Objetivo** | Tener una aplicación web que autentique, consulte PostgreSQL y devuelva un dashboard con gobernanza básica |
| **Historias** | US-01, US-02, US-04, US-07, US-14, US-25, US-26, US-27, US-31, US-35, US-44, US-49, US-55 |
| **Resultado** | Commit inicial, RBAC fail-closed, autenticación, auditoría, informes, migración a PostgreSQL, Docker full-stack y visualizaciones dinámicas |

Evidencia principal:

- `9019e19` — commit inicial.
- `6d34472` — RBAC fail-closed y tests de gobernanza.
- `feat: migracion completa a PostgreSQL, dockerizacion full-stack...` (24/08).
- `feat: suite avanzada de visualizaciones dinamicas...` (21/08).
- `feat(reports): add PDF and Excel export...` (21/08).
- `feat(governance): add audit logging, active sessions management...` (21/08).

**Cierre:** la aplicación arranca con Docker, autentica y responde consultas. La deuda principal es que la documentación y los tests todavía no acompañan el ritmo de features.

---

## 4. Sprint 1 — Entregables Fase 1 y estabilización

| Campo | Valor |
|---|---|
| **Periodo** | 4–21 de septiembre de 2026 |
| **Objetivo** | Formalizar la definición del proyecto y estabilizar ingesta, CI y experiencia de uso |
| **Historias** | US-08, US-10, US-18, US-22, US-30, US-61 |
| **Resultado** | PDFs de Fase 1 versionados; ingesta universal a PostgreSQL; CI con PostgreSQL; sinónimos semánticos; correcciones WCAG; refactor modular |

Evidencia principal:

- `Documentación Fase 1` (04/09) — guía, informes y presentación.
- `feat(postgres): ingesta universal a PostgreSQL...` (10/09).
- `feat: mejoras de seguridad en BD, copiado TSV, sinonimos semanticos...` (14/09).
- `feat: optimizacion de UX/UI... contraste WCAG 2.2 AA` (21/09).
- `.github/workflows/ci.yml` con servicio PostgreSQL.

**Cierre:** la definición académica queda alineada con el producto; la suite empieza a correr en CI con PostgreSQL real.

---

## 5. Sprint 2 — Auditoría y gobernanza

| Campo | Valor |
|---|---|
| **Periodo** | 28 de septiembre – 5 de octubre de 2026 |
| **Objetivo** | Cerrar los hallazgos críticos de la auditoría y endurecer RBAC, AST y CLS |
| **Historias** | US-15, US-16, US-17, US-31, US-32, US-33, US-34, US-35, US-55 |
| **Resultado** | `DOCS/11` y planes 001–003; RBAC fail-closed en `/chat/predict`; enmascarado en rama conversacional; tests reales en lugar de greps; CI con build; optimización de health |

Evidencia principal:

- `feat: auditoria integral, planes de trabajo...` (28/09).
- `fix(rbac): enforce fail-closed cross-domain isolation...` (01/10).
- `refactor(chat-engine): modularize QueryEngine...` (01/10).
- `test(frontend): sustituir 138 asserts de grep por 34 tests...` (03/10).
- `perf(health): 61 s -> 3,7 s...` (03/10).
- Planes [001](../plans/001-fix-unpack-crash-and-remediation-banner.md), [002](../plans/002-enforce-read-only-in-memory-null-remediation.md) y [003](../plans/003-connection-engine-lifecycle-and-dispose.md).

**Cierre:** los hallazgos críticos de la auditoría quedan corregidos y verificados. La deuda se traslada a sobreingeniería y cobertura.

---

## 6. Sprint 3 — Proyecciones, informes y deuda

| Campo | Valor |
|---|---|
| **Periodo** | 8–19 de octubre de 2026 |
| **Objetivo** | Entregar proyecciones ML honestas, informe ejecutivo y reducir sobreingeniería |
| **Historias** | US-37, US-38, US-39, US-40, US-41, US-42, US-43, US-49, US-50, US-56 |
| **Resultado** | Motor ML con backtest, sección Proyecciones, export PDF/Excel, plan 004 fases 1–4, imágenes Docker partner, scripts `setup.bat`/`setup.ps1` |

Evidencia principal:

- `Proyecciones ML (fase 2): ml_models.py puro + tests de backtest...` (17/10).
- `Proyecciones ML (fase 3): servicio, endpoints y tests...` (17/10).
- `Mejora: el Informe ejecutivo exporta proyecciones ML...` (18/10).
- `Mejora: reducción de sobreingeniería (plan 004, fases 1-3)...` (19/10).
- `fix(docker): que el compose del compañero se pueda correr solo` (11/10).
- [Plan 004](../plans/004-reduccion-de-sobreingenieria.md).

**Cierre:** el producto ya no solo responde: proyecta, exporta y se instala en una máquina partner.

---

## 7. Sprint 4 — Permisos por columna y on-prem

| Campo | Valor |
|---|---|
| **Periodo** | 22–29 de octubre de 2026 |
| **Objetivo** | Cerrar la administración de columnas, el release on-prem y las correcciones de la última milla |
| **Historias** | US-32, US-44, US-45, US-46, US-47, US-48, US-50, US-51, US-52, US-57 |
| **Resultado** | Permisos por columna, roles/dominios administrables, bundle GHCR, política LLM por empresa, historial de proyecciones, fixes de selector de conectores y arranque de metadata |

Evidencia principal:

- `Mejora: permisos por columna, roles/dominios y administración de conectores` (26/10).
- `Nuevo: instalación on-prem con bundle, imágenes GHCR y política LLM por empresa` (24/10).
- `Mejora: historial, métricas y overrides de proyecciones (frontend)` (23/10).
- `Mejora: validação AST, enmascarado y métricas de pronóstico (backend)` (23/10).
- `Mejora: crea la base de metadatos al arrancar si no existe` (29/10).
- `Mejora: refresca el selector de conectores del chat tras mutaciones` (29/10).

**Cierre:** el release on-prem queda documentado y el modelo de permisos cubre tabla y columna.

---

## 8. Sprint actual

Al 30 de octubre de 2026 **no hay un sprint activo**. El repositorio está en estado de cierre de documentación y verificación.

Candidatos para el próximo ciclo, tomados de las historias pendientes:

| Prioridad | Historia | Por qué |
|---|---|---|
| Alta | US-63 — lint bloqueante | `react-doctor` hoy es advisory |
| Alta | US-66 — specs E2E | La configuración de Playwright existe sin specs |
| Media | US-62 — tests de componentes | Vitest solo cubre lógica pura |
| Media | US-65 — métricas de uso | Hay health y auditoría, no un tablero de métricas |
| Baja | US-61 — curaduría de aprendizaje | La memoria existe, la curaduría es manual |

---

## 9. Límites declarados

- No hubo velocity, burn-down ni actas de planificación.
- La agrupación es una reconstrucción; un commit puede pertenecer a más de un objetivo.
- Las fechas son de commit, no de cierre de sprint.
- La asignación de historias es inferida del contenido del commit, no de un tablero.

---

## 10. Documentos relacionados

- [Metodología](13_METODOLOGIA.md)
- [Product Backlog](15_PRODUCT_BACKLOG.md)
- [Definition of Done](17_DEFINITION_OF_DONE.md)
- [Retrospectivas](18_RETROSPECTIVAS.md)
- [Planes de implementación](../plans/README.md)
