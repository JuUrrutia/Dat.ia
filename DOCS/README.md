# Documentación de Dat.ia

> **Documento:** Hub de documentación
> **Estado:** Vigente
> **Última actualización:** 30 de octubre de 2026
> **Producto:** Dat.ia 1.0.0 — plataforma de analítica conversacional con IA local

Punto de entrada único a la documentación del proyecto. Todos los enlaces son **relativos** y resuelven desde este archivo o desde el repositorio.

---

## 1. Los 17 entregables

| # | Entregable | Documento | Estado |
|---:|---|---|---|
| 1 | Documento de inicio | [`12_DOCUMENTO_DE_INICIO.md`](12_DOCUMENTO_DE_INICIO.md) | ✅ Vigente |
| 2 | Metodología | [`13_METODOLOGIA.md`](13_METODOLOGIA.md) | ✅ Vigente |
| 3 | Product Vision | [`14_PRODUCT_VISION.md`](14_PRODUCT_VISION.md) | ✅ Vigente |
| 4 | Product Backlog | [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) | ✅ Vigente |
| 5 | Sprint Backlog | [`16_SPRINT_BACKLOG.md`](16_SPRINT_BACKLOG.md) | ✅ Reconstruido |
| 6 | Definition of Done | [`17_DEFINITION_OF_DONE.md`](17_DEFINITION_OF_DONE.md) | ✅ Vigente |
| 7 | Retrospectivas | [`18_RETROSPECTIVAS.md`](18_RETROSPECTIVAS.md) | ✅ Reconstruidas |
| 8 | SRS | [`19_SRS.md`](19_SRS.md) | ✅ Vigente |
| 9 | README del proyecto | [`../README.md`](../README.md) | ✅ Vigente |
| 10 | Arquitectura | [`02_ARQUITECTURA_TECNICA.md`](02_ARQUITECTURA_TECNICA.md) | 🟡 Visión + implementado |
| 11 | Modelo de datos | [`21_MODELO_DE_DATOS.md`](21_MODELO_DE_DATOS.md) | ✅ Vigente |
| 12 | Diagramas UML | [`22_DIAGRAMAS_UML.md`](22_DIAGRAMAS_UML.md) | ✅ Vigente (Mermaid) |
| 13 | Requisitos no funcionales | [`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md) | ✅ Vigente |
| 14 | Docker y despliegue | [`26_DOCKER.md`](26_DOCKER.md) | ✅ Vigente |
| 15 | Pruebas | [`24_PRUEBAS.md`](24_PRUEBAS.md) | ✅ Vigente |
| 16 | Manual técnico | [`23_MANUAL_TECNICO.md`](23_MANUAL_TECNICO.md) | ✅ Vigente |
| 17 | Innovación | [`25_INNOVACION.md`](25_INNOVACION.md) | ✅ Vigente |

> **Estados:** ✅ vigente y verificado · 🟡 parcial o con secciones de visión · ⚠️ histórico con cifras desactualizadas.

---

## 2. Rutas de lectura

### Para evaluar el proyecto

1. [`../README.md`](../README.md) — qué es y cómo se levanta.
2. [`12_DOCUMENTO_DE_INICIO.md`](12_DOCUMENTO_DE_INICIO.md) — problema, alcance, equipo.
3. [`14_PRODUCT_VISION.md`](14_PRODUCT_VISION.md) — propuesta de valor.
4. [`19_SRS.md`](19_SRS.md) — requisitos verificables.
5. [`22_DIAGRAMAS_UML.md`](22_DIAGRAMAS_UML.md) — cómo funciona.
6. [`24_PRUEBAS.md`](24_PRUEBAS.md) — cómo se comprueba.
7. [`25_INNOVACION.md`](25_INNOVACION.md) — qué aporta.

### Para desarrollar

1. [`23_MANUAL_TECNICO.md`](23_MANUAL_TECNICO.md) — instalación y comandos.
2. [`21_MODELO_DE_DATOS.md`](21_MODELO_DE_DATOS.md) — tablas y relaciones.
3. [`02_ARQUITECTURA_TECNICA.md`](02_ARQUITECTURA_TECNICA.md) — capas.
4. [`24_PRUEBAS.md`](24_PRUEBAS.md) — suite y cómo agregar tests.
5. [`../plans/README.md`](../plans/README.md) — planes de implementación.

### Para operar

1. [`26_DOCKER.md`](26_DOCKER.md) — compose, puertos y troubleshooting.
2. [`../DOCKER-RAPIDO.md`](../DOCKER-RAPIDO.md) — instalación sin Node ni Python.
3. [`../deploy/README.md`](../deploy/README.md) — on-prem, TLS, backup y upgrade.

### Para gestionar el proyecto

1. [`13_METODOLOGIA.md`](13_METODOLOGIA.md) — Scrum y cómo se aplicó.
2. [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) — historias y estados.
3. [`16_SPRINT_BACKLOG.md`](16_SPRINT_BACKLOG.md) — iteraciones reconstruidas.
4. [`17_DEFINITION_OF_DONE.md`](17_DEFINITION_OF_DONE.md) — criterio de terminado.
5. [`18_RETROSPECTIVAS.md`](18_RETROSPECTIVAS.md) — qué se aprendió.

---

## 3. Índice completo

### 3.1 Documentos base (01–11)

| Documento | Contenido | Estado |
|---|---|---|
| [`01_VISION_Y_ALCANCE.md`](01_VISION_Y_ALCANCE.md) | Visión, alcance, pilares y requisitos base | 🟡 incluye visión no implementada |
| [`02_ARQUITECTURA_TECNICA.md`](02_ARQUITECTURA_TECNICA.md) | Arquitectura, capas y componentes | 🟡 parcialmente actualizado |
| [`03_SISTEMA_DE_PERMISOS_Y_SEGURIDAD.md`](03_SISTEMA_DE_PERMISOS_Y_SEGURIDAD.md) | RBAC, CLS, AST y auditoría | 🟡 diseño base |
| [`04_MOTOR_DE_IA_Y_PIPELINE_LOCAL.md`](04_MOTOR_DE_IA_Y_PIPELINE_LOCAL.md) | Pipeline Text-to-SQL y LLM local | 🟡 diseño base |
| [`05_ESPECIFICACION_DE_INTERFAZ_Y_DASHBOARDS.md`](05_ESPECIFICACION_DE_INTERFAZ_Y_DASHBOARDS.md) | UI, KPIs, gráficos y trazabilidad | 🟡 diseño base |
| [`06_HERRAMIENTAS_Y_TECNOLOGIAS.md`](06_HERRAMIENTAS_Y_TECNOLOGIAS.md) | Stack y justificación | ⚠️ menciona Electron como visión |
| [`07_ESTRUCTURA_DE_DIRECTORIOS.md`](07_ESTRUCTURA_DE_DIRECTORIOS.md) | Árbol del repositorio | ✅ actualizado el 30/10/2026 |
| [`08_PERFILES_Y_ROLES_RBAC.md`](08_PERFILES_Y_ROLES_RBAC.md) | Perfiles y matriz de permisos | 🟡 diseño base |
| [`09_DECISIONES_ARQUITECTONICAS_ROLES_Y_APRENDIZAJE.md`](09_DECISIONES_ARQUITECTONICAS_ROLES_Y_APRENDIZAJE.md) | ADR de roles y aprendizaje | 🟡 histórico |
| [`10_REFACTORIZACIONES_ARQUITECTONICAS_Y_DESCOMPOSICION_MODULAR.md`](10_REFACTORIZACIONES_ARQUITECTONICAS_Y_DESCOMPOSICION_MODULAR.md) | Refactorizaciones DDD y frontend | 🟡 histórico |
| [`11_AUDITORIA_INTEGRAL_Y_PLAN_DE_TRABAJO.md`](11_AUDITORIA_INTEGRAL_Y_PLAN_DE_TRABAJO.md) | Auditoría que originó los planes 001–003 | ⚠️ cifras del commit `c5f1af4` |

> Los documentos 01–11 son la base de diseño y auditoría. Cuando contradicen el código, **gana el código**; los documentos 12–26 son la referencia vigente.

### 3.2 Documentos de gestión y producto (12–19)

| Documento | Contenido |
|---|---|
| [`12_DOCUMENTO_DE_INICIO.md`](12_DOCUMENTO_DE_INICIO.md) | Acta de inicio, objetivos, alcance, riesgos y plan de Fase 1 |
| [`13_METODOLOGIA.md`](13_METODOLOGIA.md) | Scrum, roles, ceremonias y límites de aplicación |
| [`14_PRODUCT_VISION.md`](14_PRODUCT_VISION.md) | Visión, usuarios, propuesta de valor y métricas |
| [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md) | 66 historias en 10 épicas, con evidencia y estado |
| [`16_SPRINT_BACKLOG.md`](16_SPRINT_BACKLOG.md) | 5 iteraciones reconstruidas desde 144 commits |
| [`17_DEFINITION_OF_DONE.md`](17_DEFINITION_OF_DONE.md) | Checklist de terminado y comandos de evidencia |
| [`18_RETROSPECTIVAS.md`](18_RETROSPECTIVAS.md) | 4 retrospectivas y acciones abiertas |
| [`19_SRS.md`](19_SRS.md) | 81 requisitos funcionales, criterios y trazabilidad |

### 3.3 Documentos técnicos (20–26)

| Documento | Contenido |
|---|---|
| [`20_REQUISITOS_NO_FUNCIONALES.md`](20_REQUISITOS_NO_FUNCIONALES.md) | 77 RNF con objetivo, verificación y estado |
| [`21_MODELO_DE_DATOS.md`](21_MODELO_DE_DATOS.md) | 13 tablas de metadata + 9 demo, ER, diccionario y cascadas |
| [`22_DIAGRAMAS_UML.md`](22_DIAGRAMAS_UML.md) | Casos de uso, componentes, clases, 4 secuencias, estados y despliegue |
| [`23_MANUAL_TECNICO.md`](23_MANUAL_TECNICO.md) | Instalación, API, tareas frecuentes, troubleshooting |
| [`24_PRUEBAS.md`](24_PRUEBAS.md) | 844 tests backend, 135 frontend, CI y deuda |
| [`25_INNOVACION.md`](25_INNOVACION.md) | Aportes diferenciales y lo que no es innovación |
| [`26_DOCKER.md`](26_DOCKER.md) | Tres compose, imágenes, puertos, backup y seguridad |

### 3.4 Evidencias académicas

| Ruta | Contenido |
|---|---|
| [`entregables-academicos/fase-1/`](entregables-academicos/fase-1/) | PDFs de Fase 1 renombrados y organizados |
| [`entregables-academicos/fase-1/grupal/`](entregables-academicos/fase-1/grupal/) | Guía, autoevaluación y informe formativo |
| [`entregables-academicos/fase-1/individual/`](entregables-academicos/fase-1/individual/) | Autoevaluaciones y diarios de reflexión |

---

## 4. Cifras de referencia

Medidas el **30/10/2026** sobre el árbol de trabajo:

| Comando | Resultado |
|---|---|
| `pytest -q` | **844 passed, 244 subtests, 0 failed** (396,55 s) |
| `npm test` | **18 archivos, 135 tests** (6,56 s) |
| `npx tsc --noEmit` | exit 0 |
| `npm run build` | exit 0 (10,72 s; echarts 665,26 kB) |

Si una cifra no coincide, el documento que la cita está desactualizado. La fuente de verdad es la salida del comando, no este número.

---

## 5. Convenciones

| Convención | Regla |
|---|---|
| Idioma | Español |
| Enlaces | Relativos; nunca `file:///` ni rutas absolutas |
| Diagramas | Mermaid embebido; los PNG de `DOCS/imagenes/` son históricos y no se citan |
| Estados | ✅ vigente · 🟡 parcial · ⏳ pendiente · ❌ no implementado · ⚠️ histórico |
| Afirmaciones | Con archivo, test o comando que las respalde |
| Cifras | Con fecha y comando |
| Visión vs producto | Lo no implementado se marca; no se presenta como hecho |

---

## 6. Qué no vive aquí

| Contenido | Dónde |
|---|---|
| Planes de implementación | [`../plans/`](../plans/README.md) |
| Guía rápida Docker | [`../DOCKER-RAPIDO.md`](../DOCKER-RAPIDO.md) |
| Instalación on-prem | [`../deploy/README.md`](../deploy/README.md) |
| CI y release | [`../.github/workflows/`](../.github/workflows/) |
| Código | `../backend/` y `../src/` |

---

## 7. Mantenimiento

1. Si cambia una funcionalidad, se actualiza el documento que la describe y el backlog o SRS.
2. Si cambia una cifra, se actualiza la tabla de §4 y la fecha.
3. Si se agrega un documento, se registra en §3 y, si es un entregable, en §1.
4. Si un documento contradice el código, se corrige el documento o se declara la deuda; no se dejan ambos como verdad.
5. Los enlaces se verifican antes de cerrar un cambio.

---

**Volver al [README del repositorio](../README.md).**
