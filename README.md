# 🌌 Datia - Democratización de Datos Corporativos con IA Local 100% Offline

Plataforma empresarial de analítica conversacional y **Executive Analytics Studio** que permite a usuarios no técnicos (Economistas, Directivos, Analistas) y equipos de TI realizar consultas complejas sobre bases de datos corporativas en **lenguaje natural**, garantizando privacidad absoluta mediante **IA Local (Qwen2.5-Coder / llama.cpp)** y gobernanza con **AST Guardrails & Column-Level Security (CLS)**.

---

## 🚀 Características Principales

* 🧠 **IA Local 100% Offline (Zero Data Leakage):** Sin dependencias de APIs en la nube. Compatible con `llama.cpp` y `Ollama` ejecutando modelos GGUF cuantizados (`Qwen2.5-Coder-7B`).
* 📊 **Executive Analytics Studio:** Visualizador interactivo con cambio en vivo de gráficos (Barras con esquinas redondeadas, Áreas con Glow, Donut concéntrico 3D, Líneas y Velocímetros/Gauges), selector de paletas de color y ordenamiento dinámico.
* 📑 **Informes Ejecutivos Cuantitativos:** Generación automática de diagnósticos estratégicos C-Level con cifras exactas, márgenes porcentuales, hallazgos clave, recomendaciones accionables y dictamen de nivel de riesgo.
* 🛡️ **Gobernanza & AST Guardrail (`sqlglot`):** Análisis del árbol de sintaxis abstracta para forzar consultas de solo lectura (`SELECT` único), bloqueando cualquier comando destructivo (`DROP`, `DELETE`, `UPDATE`, `INSERT`).
* 🔐 **Seguridad por Rol (RBAC) & Column-Level Security:** Enmascaramiento y bloqueo de columnas confidenciales (tokens de pago, API keys, RUTs, IBANs) según el perfil del usuario (`Economista`, `TI`, `Administrador`).
* ⚡ **Arquitectura Standalone Híbrida:** Frontend de alta gama desarrollado en **React 18 + TypeScript + Vite + TailwindCSS + Apache ECharts** conectado a un backend de alto rendimiento en **Python FastAPI + SQLAlchemy + SQLite/PostgreSQL**.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnologías |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Framer Motion, Apache ECharts (`echarts-for-react`) |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2, sqlglot (AST Security), SQLite3 |
| **IA Local** | llama.cpp / Ollama, `Qwen2.5-Coder-7B-Instruct-GGUF` |
| **Escritorio** | Electron 33 (Empaquetado Standalone Offline) |

---

## 📦 Puesta en Marcha

### 1. Requisitos Previos
* Node.js v18+ y npm
* Python 3.10+
* (Opcional para IA Local) `llama.cpp` o `Ollama` con el modelo `Qwen2.5-Coder-7B-Instruct`

### 2. Instalación de Dependencias en 2 Pasos

```bash
# 1. Instalar dependencias del Frontend
npm install

# 2. Configurar entorno virtual e instalar Backend
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Iniciar la Aplicación (Frontend + Backend Concurrente)

```bash
npm run dev
```

La base de datos y los usuarios demo se inicializan **automáticamente** al arrancar.

* **Frontend:** `http://localhost:5173/`
* **Backend API Docs:** `http://localhost:8000/docs`

---

## 🔑 Credenciales de Acceso Demo

| Rol | Usuario | Contraseña | Acceso de Datos |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin` | `admin123` | Control total RBAC, conexiones y auditoría |
| **Economista** | `economista` | `economista123` | Finanzas, ventas, clientes, facturación y encuestas |
| **TI** | `ti` | `ti123` | Infraestructura, servidores, incidentes y encuestas |

---

## 📐 Casos de Uso y Gobernanza

El sistema incluye separación estricta de dominios:
* **Economía & Finanzas:** Acceso a `dim_categorias`, `dim_productos`, `dim_clientes`, `fact_ventas`, `fact_ingresos_costos`, `dim_empleados`.
* **Tecnología & TI:** Acceso a `dim_servidores`, `fact_incidentes_ti`, `fact_consumo_recursos`.
* **Column-Level Security:** `tarjeta_credito_token` y `api_key_servicio` restringidos exclusivamente a superadministradores.

---

## 📄 Licencia

Desarrollado con fines corporativos y de investigación en democratización de datos seguros con modelos de lenguaje locales.
