"""
Centralized System Constants for Roles, Domains, LLMs, and UI Charts.
"""
from app.core.config import settings

# Role Names
ADMIN_ROLES = {"Administrador", "Super Administrador", "Admin"}

ROLE_ADMINISTRADOR = "Administrador"
ROLE_ECONOMISTA = "Economista"
ROLE_TI = "TI"
ROLE_USUARIO = "Usuario"

DEFAULT_USER_ROLE = ROLE_USUARIO
DEFAULT_DEMO_ROLE = ROLE_ECONOMISTA

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
