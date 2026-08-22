"""
Centralized System Constants for Roles, Domains, LLMs, and UI Charts.
"""
from app.core.config import settings

# Corporate Enterprise Roles
ROLE_ADMINISTRADOR = "Administrador de Plataforma"
ROLE_DIRECTOR_EJECUTIVO = "Director Ejecutivo (C-Level)"
ROLE_ANALISTA_FINANCIERO = "Analista Financiero & Comercial"
ROLE_GERENTE_TALENTO = "Gerente de Talento & Operaciones"
ROLE_ANALISTA_BI = "Analista de Datos & BI"
ROLE_INGENIERO_TI = "Ingeniero de Infraestructura & TI"
ROLE_OFICIAL_SEGURIDAD = "Oficial de Cumplimiento & Seguridad"
ROLE_USUARIO = "Usuario Consultor"

# Backward compatibility aliases
ROLE_ECONOMISTA = "Economista"
ROLE_TI = "TI"

ADMIN_ROLES = {
    ROLE_ADMINISTRADOR,
    "Administrador",
    "Super Administrador",
    "Admin",
    "Data Platform Admin"
}

DEFAULT_USER_ROLE = ROLE_USUARIO
DEFAULT_DEMO_ROLE = ROLE_ANALISTA_FINANCIERO

# Security & Authentication Policies
MAX_FAILED_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_DURATION_MINUTES = 15
SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES = 5

# System Health Status Thresholds & States
SYSTEM_STATUS_OPERATIONAL = "OPERATIVO"
SYSTEM_STATUS_DEGRADED = "DEGRADADO"
SYSTEM_STATUS_CRITICAL = "CRITICO"

# Standard Domain Names
DOMAIN_FINANZAS = "Economía & Finanzas"
DOMAIN_TI = "Tecnología & TI"
DOMAIN_OPERACIONES = "Operaciones & Comercial"

# Default Local LLM Model
DEFAULT_LLM_MODEL = settings.OLLAMA_MODEL

# ECharts Theme Colors
CHART_COLOR_RED = "#EF4444"
CHART_COLOR_AMBER = "#F59E0B"
CHART_COLOR_EMERALD = "#10B981"
CHART_COLOR_CYAN = "#06B6D4"
CHART_COLOR_BLUE = "#3B82F6"
CHART_COLOR_PURPLE = "#8B5CF6"
CHART_COLOR_TEXT_MUTED = "#9CA3AF"
CHART_COLOR_TEXT_LIGHT = "#F3F4F6"

# Intent Classification Keywords Taxonomy
DATA_REQUEST_KEYWORDS = [
    "resumen", "resumen de datos", "resumen general", "resumen de", 
    "datos", "registros", "cuántos", "cuantos", "cuántas", "cuantas", 
    "mostrar", "muestra", "muéstrame", "muestrame", "tabla", "tablas", 
    "listado", "lista", "top", "promedio", "total", "distribución", 
    "distribucion", "gráfica", "grafica", "gráfico", "grafico",
    "ventas", "encuestas", "respuestas", "usuarios", "clientes", "incidentes", "servidores"
]

GREETING_KEYWORDS = [
    "hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", 
    "hey", "saludos", "quien eres", "quién eres", "que eres", "qué eres", 
    "que haces", "qué haces", "como estas", "cómo estás", "gracias", 
    "ayuda general", "qué puedes hacer", "que puedes hacer", "cómo funciona", "como funciona"
]

ADVISORY_KEYWORDS = [
    "idea", "ideas", "recomienda", "recomendacion", "recomendaciones", 
    "sugerencia", "sugerencias", "estrategia", "estrategias", "consejo", "consejos",
    "cómo mejorar", "como mejorar", "qué puedo hacer", "que puedo hacer", 
    "propuesta", "propuestas", "iniciativa", "iniciativas", "mejores prácticas", "mejores practicas",
    "opinión", "opinion", "qué opinas", "que opinas", "productividad", "productivo",
    "optimizar", "optimización", "optimizacion", "ayuda", "solución", "solucion", "soluciones", 
    "resolver", "pasos para", "guía para", "guia para", "tips", "consejos para", "cómo puedo"
]

EXPLANATION_KEYWORDS = [
    "qué es", "que es", "qué significa", "que significa", "explícame", "explicame", 
    "explica", "cómo funciona", "como funciona", "define", "definición", "definicion", 
    "para qué sirve", "para que sirve", "concepto", "diferencia entre"
]

HYBRID_KEYWORDS = [
    "analiza y recomienda", "evalúa y sugiere", "evalua y sugiere", 
    "diagnóstico y recomendaciones", "diagnostico y recomendaciones", 
    "análisis con recomendaciones", "analisis con recomendaciones"
]

REPORT_KEYWORDS = [
    "informe ejecutivo", "reporte ejecutivo", "informe formal", 
    "balance ejecutivo", "auditoría general", "auditoria general", "diagnóstico general"
]

# Presentation Format Keywords
LIST_KEYWORDS = [
    "lista", "listado", "muestra", "muéstrame", "muestrame", "ver ", 
    "dame los", "dame las", "cuáles son", "cuales son"
]

COUNT_KEYWORDS = [
    "cuántos", "cuantos", "cuántas", "cuantas", "total de", 
    "cantidad de", "número de", "numero de"
]

# Column Data Type & Metric Heuristic Keywords
DATE_COLUMN_KEYWORDS = [
    "fecha", "mes", "date", "time", "created_at", "updated_at", 
    "timestamp", "anio", "year", "periodo"
]

CURRENCY_COLUMN_KEYWORDS = [
    "usd", "monto", "ingreso", "costo", "precio", "utilidad", 
    "margen", "salario", "sueldo", "ganancia", "presupuesto", "gasto"
]

PERCENTAGE_COLUMN_KEYWORDS = [
    "pct", "porcentaje", "porcentual", "rate", "tasa", 
    "cumplimiento", "cpu"
]
