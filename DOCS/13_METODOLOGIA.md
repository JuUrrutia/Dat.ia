# Metodología de Trabajo

> **Documento:** 13 - Metodología declarada y justificada
> **Estado:** Vigente. Declaración de Fase 1 contrastada con la ejecución real del repositorio.
> **Última actualización:** 30 de octubre de 2026
> **Fuente primaria:** [`entregables-academicos/fase-1/grupal/guia-estudiante-definicion-proyecto.pdf`](entregables-academicos/fase-1/grupal/guia-estudiante-definicion-proyecto.pdf)

---

## 1. Declaración

El equipo desarrolló Dat.ia con **Scrum**, una metodología ágil iterativa e incremental. La decisión está declarada en la guía de definición del proyecto y en los informes de Fase 1:

> "Como equipo, desarrollaremos Dat.ia utilizando la metodología ágil Scrum, lo que nos permitirá organizar el trabajo en etapas, asignar responsabilidades claras y dar seguimiento constante al avance del proyecto."

La metodología se eligió **antes** de construir el producto, no se adoptó después para justificar el resultado.

---

## 2. Roles

| Rol | Integrante | Responsabilidad |
|---|---|---|
| Líder Técnico | Felipe Ruiz | Arquitectura, decisiones técnicas, recursos y métodos |
| Scrum Master | Catalina Cortés | Coordinación, historias de usuario, seguimiento y bloqueos |
| Desarrollador | Juan Urrutia | Implementación e integración de componentes |
| Stakeholder / validador | Docente de la asignatura | Retroalimentación de alcance y entregables |

El equipo no documentó un **Product Owner** separado. Las decisiones de producto se tomaron en conjunto y se validaron con el docente. Esta es una desviación consciente respecto del marco Scrum completo y se declara para no atribuir al proyecto una formalidad que no tuvo.

---

## 3. Artefactos

| Artefacto Scrum | Dónde vive en este repositorio |
|---|---|
| Product Backlog | [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) |
| Sprint Backlog | [`16_SPRINT_BACKLOG.md`](16_SPRINT_BACKLOG.md) |
| Incremento | Commits, PRs y releases del repositorio |
| Definition of Done | [`17_DEFINITION_OF_DONE.md`](17_DEFINITION_OF_DONE.md) |
| Retrospectivas | [`18_RETROSPECTIVAS.md`](18_RETROSPECTIVAS.md) |
| Planes de implementación | [`../plans/`](../plans/README.md) |
| Evidencias de calidad | [`24_PRUEBAS.md`](24_PRUEBAS.md) y CI |

---

## 4. Ceremonias

| Ceremonia | Cómo se aplicó |
|---|---|
| Planificación de iteración | Definición de objetivos y planes en `plans/001–005` antes de tocar código |
| Reuniones de avance | Reuniones periódicas para revisar avances, resolver bloqueos y dar seguimiento a épicas e historias |
| Revisión | Verificación contra criterios de aceptación y suite de tests antes de cerrar cada plan |
| Retrospectiva | Documentada al cierre de auditorías y planes (ver `18_RETROSPECTIVAS.md`) |

La presentación de Fase 1 declara explícitamente "reuniones periódicas para revisar avances, resolver bloqueos y dar seguimiento a las épicas e historias de usuario".

---

## 5. Justificación

Scrum encaja con las condiciones reales del proyecto:

1. **Equipo pequeño (3 personas):** permite ciclos cortos y comunicación directa sin una capa de coordinación pesada.
2. **Requisitos cambiantes:** el alcance evolucionó de "consultas en lenguaje natural" a gobernanza, proyecciones, informes y despliegue on-prem. Iterar permitió incorporar hallazgos sin rehacer todo.
3. **Riesgo técnico alto:** la calidad del SQL generado por el LLM y la seguridad de los datos exigían validación frecuente, no un big bang final.
4. **Retroalimentación académica:** las entregas de Fase 1 y las revisiones del docente pedían incrementos demostrables.
5. **Calidad verificable:** CI con pytest, vitest, typecheck y build convierte cada incremento en algo comprobable.

---

## 6. Cómo se aplicó realmente

La ejecución se puede reconstruir desde el repositorio:

| Iteración | Periodo | Evidencia |
|---|---|---|
| Sprint 0 | 16–25 ago 2026 | Commit inicial, RBAC, autenticación, auditoría, informes, Docker/PostgreSQL |
| Sprint 1 | 4–21 sep 2026 | Entregables Fase 1, ingesta PostgreSQL, CI, UX/WCAG |
| Sprint 2 | 28 sep–5 oct 2026 | Auditoría integral (`DOCS/11`), planes 001–003, endurecimiento RBAC/AST/CLS |
| Sprint 3 | 8–19 oct 2026 | Proyecciones ML, informes, plan 004 (sobreingeniería) |
| Sprint 4 | 22–29 oct 2026 | Permisos por columna, release on-prem, correcciones finales |

El detalle de cada iteración, con historias y resultados, está en [`16_SPRINT_BACKLOG.md`](16_SPRINT_BACKLOG.md).

### Lo que no se formalizó

- No hubo tablero Jira/Trello ni historias estimadas con story points.
- No se registró velocity ni un burn-down chart.
- No hubo daily logs; las reuniones fueron periódicas y el seguimiento quedó en commits y planes.
- La cadencia no fue estrictamente de dos semanas: las iteraciones se agruparon por hitos de producto y auditorías.

Estas ausencias no invalidan la metodología, pero deben declararse. La rúbrica de evaluación puede verificar **artefactos y evidencia**, no una ceremonia que no dejó registro.

---

## 7. Trazabilidad metodológica

| Principio Scrum | Evidencia en el repositorio |
|---|---|
| Incremento potencialmente entregable | `npm run build`, imágenes Docker y bundle on-prem |
| Transparencia | README, DOCS 01–26, planes y auditorías |
| Inspección | Suite de tests y CI en cada push/PR |
| Adaptación | Planes 001–005 y retrospectivas |
| Auto-organización | Roles definidos y decisiones registradas en ADRs |

---

## 8. Límites declarados

- La metodología se declara en Fase 1; la reconstrucción de sprints se hizo **a posteriori** desde commits y planes, no desde un tablero.
- Las fechas de las iteraciones son agrupaciones de commits reales, no actas de planificación.
- Las retrospectivas son reconstruidas desde auditorías y planes, y así se marcan.
- El equipo no usó un Product Owner externo; el docente actuó como validador.

---

## 9. Documentos relacionados

- [Documento de inicio](12_DOCUMENTO_DE_INICIO.md)
- [Product Backlog](15_PRODUCT_BACKLOG.md)
- [Sprint Backlog](16_SPRINT_BACKLOG.md)
- [Definition of Done](17_DEFINITION_OF_DONE.md)
- [Retrospectivas](18_RETROSPECTIVAS.md)
