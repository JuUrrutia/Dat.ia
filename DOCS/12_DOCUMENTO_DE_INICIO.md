# Documento de Inicio del Proyecto

> **Documento:** 12 - Acta de Inicio (Project Charter)
> **Estado:** Vigente. Reconstruido desde los entregables de Fase 1 y verificado contra el repositorio.
> **Fecha de inicio del proyecto:** 16 de agosto de 2026
> **Última actualización:** 30 de octubre de 2026
> **Fuente primaria:** [`entregables-academicos/fase-1/`](entregables-academicos/fase-1/) (PDFs de la asignatura Capstone APT122)

---

## 1. Identificación

| Campo | Valor |
|---|---|
| Nombre del proyecto | **Dat.ia — Transformando datos en decisiones** |
| Nombre técnico del repositorio | `democratizacion de datos` |
| Asignatura | Capstone APT122 |
| Sección | 003D |
| Docente | Aníbal Sotelo Becerra |
| Institución | Duoc UC — Ingeniería en Informática |
| Equipo | Catalina Cortés Hernández, Felipe Ruiz Mejias, Juan Urrutia Morales |
| Fecha de definición | Fase 1, septiembre de 2026 |
| Versión del producto | 1.0.0 (repositorio, octubre de 2026) |

### Roles del equipo

Los roles están declarados en la presentación de Fase 1 y en la guía de definición del proyecto:

| Integrante | Rol | Responsabilidad principal |
|---|---|---|
| Felipe Ruiz | Líder Técnico | Decisiones de arquitectura, recursos y métodos de desarrollo |
| Catalina Cortés | Scrum Master | Coordinación, gestión de historias de usuario y seguimiento |
| Juan Urrutia | Desarrollador | Desarrollo e integración de componentes |

> No se documentó un Product Owner separado. El alcance y las prioridades se validaron con el docente de la asignatura; el equipo asumió la conversación de producto.

---

## 2. Problema y oportunidad

Las organizaciones generan y almacenan grandes volúmenes de datos, pero las personas que necesitan decidir no siempre tienen conocimientos de SQL, modelado o análisis avanzado. El resultado es dependencia de TI, reportes que llegan tarde y silos de información.

Al mismo tiempo, usar asistentes de IA en la nube para consultar datos corporativos expone esquemas, ventas, remuneraciones y datos personales fuera de la red de la empresa. Dat.ia ataca ambos problemas a la vez:

- **Acceso:** consultas en lenguaje natural sobre datos corporativos.
- **Soberanía:** el modelo de lenguaje y los datos se quedan en la infraestructura de la empresa.
- **Gobernanza:** RBAC, enmascaramiento de columnas y validación AST antes de ejecutar SQL.

---

## 3. Objetivos

### 3.1 Objetivo general

> Diseñar una plataforma web de análisis de datos basada en inteligencia artificial que permita a los usuarios consultar, interpretar y visualizar información contenida en datasets mediante lenguaje natural, funcionando en modo offline y pudiendo ejecutarse mediante contenedores Docker para facilitar su despliegue local.

### 3.2 Objetivos específicos

1. Implementar un sistema de clasificación y análisis automático de datos.
2. Integrar un modelo de inteligencia artificial local capaz de interpretar consultas en lenguaje natural.
3. Desarrollar dashboards y visualizaciones automáticas para facilitar la comprensión de la información.
4. Permitir el funcionamiento de la plataforma web en un entorno offline, sin dependencia obligatoria de servicios externos o conexión a Internet.
5. Configurar la ejecución de Dat.ia mediante contenedores Docker para facilitar su instalación, portabilidad y despliegue local.
6. Evaluar la capacidad de la solución para apoyar la toma de decisiones de usuarios no técnicos.

---

## 4. Alcance

### 4.1 Dentro del alcance (implementado)

- Aplicación web self-hosted: React 18 + TypeScript + Vite en el frontend, FastAPI en el backend.
- PostgreSQL como motor de datos corporativo y de metadatos.
- Consultas en lenguaje natural con LLM local (Ollama, llama.cpp, LM Studio o endpoint compatible con OpenAI).
- Catálogo semántico editable, enriquecimiento asistido por IA y política de nulos.
- Gobernanza en tres capas: matriz RBAC, guard de dominio y validador AST de solo lectura.
- Seguridad a nivel de columna: `ALLOWED`, `MASKED`, `BLOCKED`.
- Dashboards con KPIs, gráficos interactivos, tabla de datos y panel de trazabilidad.
- Proyecciones ML con backtest walk-forward y reglas de honestidad.
- Informes ejecutivos exportables a PDF y Excel desde el snapshot auditado.
- Administración de usuarios, roles, dominios, conexiones, catálogo y auditoría.
- Despliegue con Docker Compose, bundle on-prem, backup/restore/upgrade y modo air-gapped.

### 4.2 Fuera del alcance (visión no implementada)

| Elemento | Estado | Motivo |
|---|---|---|
| Empaquetado de escritorio (Electron/Tauri) | ❌ No implementado | La entrega real es web en Docker; no hay paquete ni entrypoint de escritorio |
| MySQL / MariaDB | ❌ No implementado | Sin driver en `backend/requirements.txt` ni rama en `build_engine_for_connector` |
| Microsoft SQL Server | ❌ No implementado | Misma razón: sin driver y sin valor en `DatabaseType` |
| Oracle Database | ❌ Excluido por ADR-001 | Dependencias nativas y portabilidad |
| SaaS multi-empresa | ❌ No implementado | El diseño es una instalación on-prem por empresa |
| App móvil nativa | ❌ No implementado | La interfaz es web responsive |

La comparación completa está en [`01_VISION_Y_ALCANCE.md`](01_VISION_Y_ALCANCE.md) y en el [README](../README.md#fuentes-de-datos-implementado-vs-planificado).

---

## 5. Interesados

| Interesado | Necesidad |
|---|---|
| Dirección / C-Level | Rentabilidad consolidada y decisiones sin depender de reportes manuales |
| Analista financiero | Consultar ventas, clientes, facturación y márgenes con autonomía |
| Gerente de talento | Ver plantilla y encuestas sin exponer remuneraciones a otros roles |
| Analista de BI | Explorar infraestructura y datos operativos con permisos acotados |
| Ingeniero de TI | Diagnosticar salud del sistema, servidores e incidentes |
| Oficial de cumplimiento | Auditar consultas, permisos y exportaciones |
| Administrador de plataforma | Gestionar usuarios, roles, conexiones, catálogo y políticas |
| Docente / evaluador | Verificar metodología, alcance, arquitectura y evidencias |

---

## 6. Factibilidad

| Dimensión | Evaluación |
|---|---|
| **Técnica** | Stack open source, LLM local cuantizado y Docker. El equipo ya trabajó con React, FastAPI, PostgreSQL y Docker. |
| **Económica** | Sin licencias de IA por token ni APIs en la nube. El costo es el hardware del host. |
| **Operativa** | Instalación on-prem con bundle y scripts; no requiere Node ni Python en el host del cliente. |
| **Legal / privacidad** | Los datos y el modelo no salen de la infraestructura de la empresa. |
| **Académica** | Alcance acotado al semestre; el plan de Fase 1 cabe en ~12 semanas de trabajo. |

### Restricciones

- El LLM debe correr localmente o en un endpoint privado de la empresa.
- La base corporativa se consulta en modo solo lectura.
- El producto se entrega como instalación on-prem, no como SaaS.
- La ventana de contexto del LLM se fija al arrancar el servidor, no por request.

---

## 7. Riesgos iniciales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Hardware insuficiente para el modelo | Alto | Modelos 7B cuantizados, modo CPU/GPU y guía de requisitos mínimos |
| Calidad del SQL generado por el LLM | Alto | Validación AST, reintentos acotados y catálogo semántico |
| Fuga de datos por prompts o endpoints | Crítico | LLM local, `LLM_MODE`, validación de URL privada y RBAC fail-closed |
| Cambios de alcance durante el semestre | Medio | Backlog priorizado y planes de implementación versionados |
| Deriva entre documentación y código | Medio | DoD con verificación y auditorías (`DOCS/11`, planes 004/005) |
| Dependencia de un solo developer para un módulo | Medio | Repositorio, tests y documentación de arquitectura |

---

## 8. Plan inicial declarado en Fase 1

| # | Actividad | Duración | Responsable |
|---|---|---|---|
| 1 | Levantamiento de requerimientos | 1 semana | Equipo |
| 2 | Diseño de arquitectura y modelo de datos | 1 semana | Felipe Ruiz |
| 3 | Carga y procesamiento de datasets | 2 semanas | Juan Urrutia |
| 4 | Análisis y clasificación automática | 2 semanas | Juan Urrutia / Felipe Ruiz |
| 5 | Integración de IA y consultas en lenguaje natural | 2 semanas | Felipe Ruiz / Juan Urrutia |
| 6 | Dashboards y visualizaciones | 2 semanas | Catalina Cortés / Juan Urrutia |
| 7 | Integración, Docker, offline y pruebas | 2 semanas | Equipo |
| 8 | Documentación y presentación final | 1 semana | Equipo |

> El plan es el declarado en la guía de Fase 1. La ejecución real se reconstruye en [`16_SPRINT_BACKLOG.md`](16_SPRINT_BACKLOG.md) a partir de commits y planes.

---

## 9. Criterios de éxito

| Criterio | Meta |
|---|---|
| Soberanía y privacidad | 100% offline; cero telemetría a terceros |
| Seguridad de acceso | 100% de consultas fuera del rol bloqueadas |
| Seguridad de la base | Cero modificaciones a datos del cliente desde el chat |
| Facilidad de uso | Usuarios no técnicos obtienen respuesta visual y explicada |
| Costo operativo | Cero costo de licencias o APIs de IA por token |
| Calidad | Suite de tests verde y build reproducible |

---

## 10. Evidencias de origen

| Evidencia | Archivo |
|---|---|
| Guía de definición del proyecto | [`grupal/guia-estudiante-definicion-proyecto.pdf`](entregables-academicos/fase-1/grupal/guia-estudiante-definicion-proyecto.pdf) |
| Informe de autoevaluación Fase 1 | [`grupal/informe-1.3-autoevaluacion.pdf`](entregables-academicos/fase-1/grupal/informe-1.3-autoevaluacion.pdf) |
| Informe formativo Fase 1 | [`grupal/informe-1.4-formativa.pdf`](entregables-academicos/fase-1/grupal/informe-1.4-formativa.pdf) |
| Presentación Fase 1 | [`presentacion-fase-1.pdf`](entregables-academicos/fase-1/presentacion-fase-1.pdf) |
| Autoevaluaciones individuales | [`individual/`](entregables-academicos/fase-1/individual/) |

---

## 11. Estado actual

El proyecto **no se quedó en la definición**: el repositorio tiene la plataforma implementada y verificable. La comparación entre lo declarado y lo construido está en:

- [README del repositorio](../README.md)
- [`01_VISION_Y_ALCANCE.md`](01_VISION_Y_ALCANCE.md)
- [`15_PRODUCT_BACKLOG.md`](15_PRODUCT_BACKLOG.md)
- [`24_PRUEBAS.md`](24_PRUEBAS.md)

---

## 12. Documentos relacionados

- [Metodología](13_METODOLOGIA.md)
- [Product Vision](14_PRODUCT_VISION.md)
- [Product Backlog](15_PRODUCT_BACKLOG.md)
- [Sprint Backlog](16_SPRINT_BACKLOG.md)
- [Definition of Done](17_DEFINITION_OF_DONE.md)
- [SRS](19_SRS.md)
