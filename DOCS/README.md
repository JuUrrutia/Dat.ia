# Documentación Central - Proyecto Democratización de Datos

Bienvenido al repositorio de documentación técnica y funcional del proyecto **Democratización de Datos Corporativos con IA Local**.

---

## 🎯 Objetivo de la Documentación
Servir como la única fuente de verdad (Single Source of Truth) para el diseño, arquitectura, gobernanza, seguridad, interfaz y desarrollo del sistema.

---

## 📚 Índice de Documentos

1. **[01 - Visión, Alcance y Requisitos Base](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/01_VISION_Y_ALCANCE.md)**  
   *Visión ejecutiva, objetivos del proyecto, pilares no negociables (100% offline, LLM local gratuito, privacidad), matriz de compatibilidad y casos de uso.*  
   `Estado: ✅ Completado y Aprobado`

2. **[02 - Arquitectura Técnica y Componentes](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/02_ARQUITECTURA_TECNICA.md)**  
   *Diseño de la aplicación de escritorio standalone, capas de software, pool de conectores relacionales (PostgreSQL, MSSQL, MySQL, SQLite), pipeline de procesamiento y adaptación CPU/GPU.*  
   `Estado: ✅ Completado y Aprobado`

3. **[03 - Gobernanza, Seguridad y Sistema de Permisos (RBAC)](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/03_SISTEMA_DE_PERMISOS_Y_SEGURIDAD.md)**  
   *Matriz de roles, control granular a nivel de dominio/tabla/columna sensible (enmascaramiento), inyección de esquema dinámico filtrado, validador AST (SQL Guardrail) y auditoría local.*  
   `Estado: ✅ Completado y Aprobado`

4. **[04 - Motor de IA Local y Pipeline Text-to-SQL](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/04_MOTOR_DE_IA_Y_PIPELINE_LOCAL.md)**  
   *Conector local agnóstico (Ollama / OpenAI API local), catálogo semántico enriquecido, ingeniería de prompts, ciclo de autocorrección y selección de modelos Open Source (Qwen 2.5 Coder, Llama 3.1).*  
   `Estado: ✅ Completado y Aprobado`

5. **[05 - Especificación de UI y Generador de Dashboards](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/05_ESPECIFICACION_DE_INTERFAZ_Y_DASHBOARDS.md)**  
   *Experiencia de usuario conversacional (Desktop UI), tarjetas de KPI, gráficos interactivos dinámicos, resumen ejecutivo de negocio, tabla de datos interactiva, panel de trazabilidad y vistas de administración.*  
   `Estado: ✅ Completado y Aprobado`

6. **[06 - Especificación de Herramientas y Tecnologías](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/06_HERRAMIENTAS_Y_TECNOLOGIAS.md)**  
   *Stack tecnológico seleccionado (Electron, React, Vite, TypeScript, FastAPI, sqlglot, ECharts, PostgreSQL, Ollama), justificación detallada (el porqué) y propósito de uso (el para qué).*  
   `Estado: ✅ Completado y Aprobado`

7. **[07 - Estructura de Carpetas y Arquitectura de Código](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/07_ESTRUCTURA_DE_DIRECTORIOS.md)**  
   *Árbol completo de directorios y archivos del Monorepo (Electron, React Vite, Python FastAPI), con separación limpia de capas, componentes, servicios y conectores.*  
   `Estado: ✅ Completado y Aprobado`

8. **[08 - Especificación de Perfiles de Usuario y Matriz de Permisos RBAC](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/DOCS/08_PERFILES_Y_ROLES_RBAC.md)**  
   *Definición de los 3 perfiles principales (Administrador, Economista, TI) y perfil inicial por defecto (Usuario), asignación de dominios, tablas permitidas y reglas de enmascaramiento.*  
   `Estado: ✅ Completado y Aprobado`

---

## 🔒 Reglas Principales del Proyecto
- **100% Offline (Standalone):** Ningún dato sensible, esquema ni telemetría sale de la máquina local.
- **LLM Local Gratuito:** Sin costos recurrentes ni suscripciones a APIs en la nube.
- **Gobernanza y RBAC Estricto:** Esquema dinámico filtrado + Validador AST + Conexiones de base de datos en modo Solo Lectura (`READ ONLY`).
- **Transparencia y Explicabilidad:** Cada respuesta entrega visualización interactiva, resumen de negocio y panel de auditoría de la consulta ejecutada.
