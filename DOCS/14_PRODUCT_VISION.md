# Product Vision

> **Documento:** 14 - Visión de Producto
> **Estado:** Vigente. Deriva de `01_VISION_Y_ALCANCE.md` y del README; no reemplaza el alcance técnico.
> **Última actualización:** 30 de octubre de 2026
> **Audiencia:** equipo, docente, evaluadores y responsables de producto

---

## 1. Declaración de visión

> **Que cualquier persona de una organización pueda preguntar a sus datos en lenguaje natural y recibir una respuesta visual, explicada y auditable, sin que un solo byte salga de la infraestructura de la empresa.**

Dat.ia convierte una base de datos corporativa en un analista disponible: entiende la pregunta, genera SQL de solo lectura, lo valida, lo ejecuta y devuelve un dashboard con KPIs, gráficos, tabla y trazabilidad.

---

## 2. Elevator pitch

Las empresas tienen datos, pero no siempre tienen personas que sepan consultarlos. Contratar analistas para cada pregunta no escala, y mandar datos a una IA en la nube no es aceptable para información financiera o de personas. **Dat.ia** es una plataforma web self-hosted que ejecuta un LLM local, aplica RBAC y enmascaramiento de columnas, y entrega analítica conversacional sin conexión a internet. Se instala con Docker en una máquina de la empresa y se opera desde el navegador.

---

## 3. Problema

| Dolor | Consecuencia |
|---|---|
| Dependencia de TI para cada reporte | Semanas de espera para una respuesta que debería tomar segundos |
| Datos en silos y esquemas complejos | Usuarios de negocio no pueden explorar sin ayuda técnica |
| Herramientas de IA en la nube | Riesgo de fuga de datos financieros, de clientes y de remuneraciones |
| Reportes sin contexto | Números correctos pero decisiones mal informadas |
| Falta de trazabilidad | Nadie sabe de dónde salió una cifra ni qué consulta la produjo |

---

## 4. Usuarios

### Primarios

| Persona | Necesita | Hoy |
|---|---|---|
| Directivo / C-Level | Rentabilidad consolidada y tendencias sin pedir un informe | Depende de un analista |
| Analista financiero | Explorar ventas, clientes, márgenes y facturación | SQL o Excel manual |
| Gerente de talento | Ver plantilla y encuestas sin exponer sueldos | Reportes estáticos de RRHH |

### Secundarios

| Persona | Necesita |
|---|---|
| Analista de BI | Validar datos y construir tableros |
| Ingeniero de TI | Diagnosticar salud, servidores e incidentes |
| Oficial de cumplimiento | Auditar accesos, consultas y exportaciones |
| Administrador | Gestionar usuarios, roles, conexiones y políticas |
| Usuario consultor | Leer catálogo y encuestas sin riesgo |

---

## 5. Jobs to be done

1. **"Quiero saber qué pasó con las ventas del trimestre"** → dashboard con evolución, margen y comparación por categoría.
2. **"Quiero entender por qué cambió un indicador"** → descomposición causal, concentración Pareto y plan táctico.
3. **"Quiero proyectar los próximos 6 meses"** → serie con banda, backtest y veredicto contra el naive.
4. **"Quiero compartir un informe con dirección"** → PDF/Excel con cifras, hallazgos y SQL auditado.
5. **"No quiero que RRHH vea sueldos"** → RBAC + CLS + auditoría, sin depender de la buena voluntad del usuario.

---

## 6. Propuesta de valor

| Para | Que hoy duele | Dat.ia ofrece | Diferencia |
|---|---|---|---|
| Empresa con datos sensibles | La IA en la nube expone información | LLM local y datos on-prem | Soberanía real, no una promesa de privacidad |
| Usuario no técnico | No sabe SQL | Pregunta en español | Sin capacitación técnica |
| TI / cumplimiento | No puede probar quién vio qué | Auditoría de cada consulta y cambio de permiso | Trazabilidad operativa |
| Dirección | Reportes tardíos | Dashboard e informe en segundos | Decisión más rápida |

---

## 7. Principios de producto

1. **Offline por defecto.** La nube es una excepción administrada, no el camino normal.
2. **Fail-closed.** Ante duda de permisos, se niega. Sobre-bloquear se nota; filtrar, no.
3. **Solo lectura.** El chat nunca modifica la base del cliente.
4. **Explicabilidad.** Cada respuesta muestra la consulta y el diccionario del dato.
5. **Honestidad del dato.** Un valor no medido se muestra "—", nunca como cero.
6. **Portabilidad.** Docker y un bundle on-prem; sin dependencia de Node o Python en el host.
7. **Costo cero de IA.** Modelos abiertos y hardware de la empresa.

---

## 8. Métricas de éxito

| Métrica | Objetivo | Cómo se verifica |
|---|---|---|
| Consultas fuera de rol bloqueadas | 100% | Tests de RBAC y AST |
| Modificaciones a datos del cliente desde el chat | 0 | Plan 002 y tests de remediación en memoria |
| Tiempo de respuesta percibido | Segundos, no días | Uso real en demo |
| Cobertura de pruebas | Suite verde en CI | `pytest`, `vitest`, `tsc`, `build` |
| Costo de licencias de IA | 0 | Modelo local |
| Instalación en host limpio | Un comando | `setup.sh` / Docker Compose |

> Las métricas de latencia y satisfacción no se midieron con usuarios reales en este repositorio. Se declaran como objetivos, no como resultados.

---

## 9. No-objetivos

- No es un SaaS multi-empresa.
- No es una herramienta de ETL ni un data warehouse.
- No reemplaza al analista: lo desbloquea.
- No entrena modelos con los datos del cliente.
- No promete SQL perfecto: promete SQL validado y explicable.
- No soporta MySQL ni SQL Server en esta versión.

---

## 10. Temas de evolución

| Tema | Estado |
|---|---|
| Gobernanza y CLS | Implementado |
| Analítica conversacional | Implementado |
| Proyecciones ML | Implementado |
| Informes ejecutivos | Implementado |
| Instalación on-prem | Implementado |
| Más motores de datos | Visión (no implementado) |
| Empaquetado de escritorio | Visión (no implementado) |
| Colaboración multiusuario avanzada | Parcial (hilos compartidos) |

---

## 11. Documentos relacionados

- [Visión y alcance técnico](01_VISION_Y_ALCANCE.md)
- [Documento de inicio](12_DOCUMENTO_DE_INICIO.md)
- [Product Backlog](15_PRODUCT_BACKLOG.md)
- [Innovación](25_INNOVACION.md)
