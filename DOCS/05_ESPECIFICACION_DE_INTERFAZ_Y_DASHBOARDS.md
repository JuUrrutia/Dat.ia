# Documento 05: Especificación de Interfaz de Usuario y Dashboards

> **Documento:** 05 - Especificación de UI/UX, Componentes y Visualizaciones  
> **Estado:** Especificación Técnica Aprobada  
> **Área:** Diseño de Producto, Frontend y Experiencia de Usuario  

---

## 1. Filosofía de Diseño y Experiencia de Usuario (UI/UX)

La interfaz de la **Aplicación de Escritorio** está diseñada bajo el concepto de **"Conversational Analytics"**:
- **Simplicidad para no técnicos:** Sin necesidad de aprender constructores complejos de dashboards (drag-and-drop complicado ni fórmulas).
- **Inmediatez Visual:** Cada respuesta incluye un paquete completo compuesto por **Métricas clave + Gráficos interactivos + Explicación ejecutiva + Datos tabulares**.
- **Aestética Premium y Profesional:** Paleta de colores sobria y moderna, tipografía clara optimizada para lectura de datos (Inter / Roboto), soporte para Modo Oscuro y Claro, y gráficos fluidos con animaciones sutiles.

---

## 2. Estructura General del Layout de la Aplicación

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] Democratizador de Datos AI                  [Rol: Finanzas] [Usuario: Felipe] [⚙]│
├─────────────────┬──────────────────────────────────────────────────────────────────────┤
│ 📁 NAVEGACIÓN   │ 💬 ESPACIO DE CONSULTA Y DASHBOARDS                                  │
│                 │                                                                      │
│ ➕ Nueva Consulta│ ┌──────────────────────────────────────────────────────────────────┐ │
│                 │ │ 🧑 Felipe: "¿Cuáles fueron las ventas y margen mensual del 2025?"│ │
│ 🕒 HISTORIAL    │ └──────────────────────────────────────────────────────────────────┘ │
│ • Ventas Q3     │                                                                      │
│ • Margen 2025   │ ┌──────────────────────────────────────────────────────────────────┐ │
│ • Top Clientes  │ │ 🤖 ASISTENTE DE DATOS:                                           │ │
│                 │ │                                                                  │ │
│ 📚 CATÁLOGO     │ │ [ KPI 1: $1.420M Total ]  [ KPI 2: 23.4% Margen ]  [ KPI 3: +8% ]│ │
│ • Ver Diccionario│ │                                                                  │ │
│                 │ │ ┌────────────────────────┐  ┌──────────────────────────────────┐ │ │
│ 🔒 ADMIN (Solo  │ │ │ [ Gráfico de Barras /  │  │ 📝 RESUMEN EJECUTIVO             │ │ │
│    con rol)     │ │ │   Líneas Interactivo ] │  │ Durante el 2025, las ventas      │ │ │
│ • Usuarios/Roles│ │ │                        │  │ alcanzaron su pico en noviembre  │ │ │
│ • Conexiones BD │ │ └────────────────────────┘  │ con un margen promedio de 23.4%..│ │ │
│ • Auditoría     │ │                             └──────────────────────────────────┘ │ │
│                 │ │                                                                  │ │
│                 │ │ 📊 TABLA INTERACTIVA (12 registros) [Buscar...] [🔽 Filtros]     │ │
│                 │ │ ┌──────────┬─────────────┬─────────────┬──────────┐              │ │
│                 │ │ │ Mes      │ Ventas Brutas│ Costo Total │ Margen % │              │ │
│                 │ │ ├──────────┼─────────────┼─────────────┼──────────┤              │ │
│                 │ │ │ Enero    │ $110.000.000│ $85.000.000 │ 22.7%    │              │ │
│                 │ │ └──────────┴─────────────┴─────────────┴──────────┘              │ │
│                 │ │                                                                  │ │
│                 │ │ ▶ 🔍 VER TRAZABILIDAD Y CONSULTA SQL AUDITADA (Desplegable)      │ │
│                 │ └──────────────────────────────────────────────────────────────────┘ │
│                 │                                                                      │
│                 │ ┌──────────────────────────────────────────────────┬───────────────┐ │
│                 │ │ Escribe tu pregunta sobre los datos aquí...      │ [ Enviar 🚀 ] │ │
│                 │ └──────────────────────────────────────────────────┴───────────────┘ │
└─────────────────┴──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes del Entregable Analítico

Cada respuesta generada por el sistema contiene 4 secciones organizadas jerárquicamente:

### 3.1. Tarjetas de Métricas Clave (KPI Cards)
- Ubicadas en la cabecera de la respuesta.
- Muestran las cifras consolidadas principales (ej. *Ingresos Totales*, *Margen Promedio*, *Variación Porcentual*, *Conteo de Casos*).
- Formato adaptado automáticamente (moneda `$`, porcentaje `%`, unidades enteras con separadores de miles).

### 3.2. Gráficos Interactivos Dinámicos
El motor Text-to-Viz selecciona y configura el gráfico óptimo según la dimensionalidad del resultado:

| Tipo de Gráfico | Caso de Uso Principal |
| :--- | :--- |
| **Gráfico de Barras / Columnas** | Comparativas entre categorías, sucursales, productos o departamentos. |
| **Gráfico de Líneas / Área** | Evolución temporal de métricas (diaria, mensual, trimestral, anual). |
| **Gráfico de Dona / Torta** | Distribución porcentual y composición de un total (máximo 6 categorías). |
| **Gráfico Mixto (Barras + Línea)** | Relación de volumen (ventas en barras) vs porcentaje (margen en línea). |

**Capacidades Interactivas:**
- Tooltips flotantes con valores exactos y porcentajes calculados.
- Filtro interactivo al hacer clic en elementos de la leyenda.
- Zoom y paneo en series temporales extensas.

### 3.3. Resumen Ejecutivo e Insights Clave
- Texto redactado en lenguaje natural que explica el comportamiento del negocio.
- Destaca variaciones significativas, picos, caídas anómalas o patrones relevantes sin usar jerga técnica de SQL.

### 3.4. Tabla Interactiva de Datos Subyacentes
- Visualización de las filas y columnas devueltas por la consulta.
- Funcionalidades integradas:
  - Ordenamiento ascendente/descendente al hacer clic en cualquier encabezado de columna.
  - Buscador rápido en tiempo real para filtrar filas.
  - Paginación automática (10, 25, 50 filas por página).

### 3.5. Panel Desplegable de Trazabilidad y Auditoría
Diseñado para dar total transparencia y confianza a los analistas y auditores:
- **Explicación del cálculo:** Descripción paso a paso de las fórmulas y tablas unidas (`JOINs`).
- **Diccionario de datos utilizado:** Definición de cada columna según el Catálogo Semántico.
- **SQL Generado y Auditado:** Visualización del código SQL exacto que se ejecutó de forma segura en la base de datos con resaltado de sintaxis.

---

## 4. Vistas del Panel de Administración (Solo Perfiles con Rol Administrador)

### 4.1. Gestión de Usuarios y Asignación de Roles
- Creación, edición y desactivación de usuarios locales.
- Asignación de uno o más roles a cada usuario (ej. *Finanzas*, *Comercial*, *Operaciones*).

### 4.2. Matriz de Permisos por Rol
- Selector de Dominios de Negocio habilitados por rol.
- Lista de tablas autorizadas con casillas de verificación.
- Selector de columnas sensibles por tabla:
  - `Visible`: Acceso normal.
  - `Bloqueada`: Inaccesible (eliminada del contexto de la IA).
  - `Enmascarada`: Valor sustituido por hash o asteriscos (ej. `****-1234`).

### 4.3. Asistente de Conexión a Base de Datos y Catálogo Semántico
- **Paso 1: Conexión:** Formulario para ingresar credenciales locales de la BD (Motor, Host, Puerto, Base de datos, Usuario y Contraseña).
- **Paso 2: Inspección Automática:** El sistema escanea esquemas, tablas, columnas y tipos de datos automáticamente.
- **Paso 3: Enriquecimiento Semántico:** El administrador añade descripciones en español, sinónimos populares y reglas de negocio para que la IA comprenda la terminología de la empresa.

### 4.4. Monitor de Auditoría y Trazabilidad
- Tabla con el historial completo de consultas realizadas por todos los usuarios.
- Filtros por fecha, usuario, rol y estado de validación (`APROBADA` vs `RECHAZADA`).
- Detalle de la pregunta formulada y el SQL ejecutado.

---

## 5. Accesibilidad y Ergonomía Visual

- **Paleta de Colores de Datos:** Colores accesibles con contraste optimizado (cumplimiento WCAG AA) para diferenciar series de datos sin depender exclusivamente del color.
- **Tipografía Corporativa:** Fuentes modernas del sistema sin requerir descargas web externas (`system-ui`, `Segoe UI`, `Roboto`, `Inter`).
- **Feedback Inmediato:** Indicadores visuales de estado (Cargando datos, analizando pregunta, generando gráficos) con micro-animaciones suaves.
