import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

def _backend_dir() -> str:
    """Directory holding the backend package (…/backend)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _root_dir() -> str:
    """Project root holding data_sources/ and the metadata DB.

    Derived from the checkout layout normally, so a fresh clone works with no
    configuration. In Docker the backend is copied to /app, whose parent is /,
    which would put data_sources outside the mounted volume and lose every
    uploaded database on recreate — so the image pins DATIA_ROOT=/app.
    """
    return os.environ.get("DATIA_ROOT") or os.path.dirname(_backend_dir())

class Settings(BaseSettings):
    PROJECT_NAME: str = "Democratización de Datos Corporativos con IA Local"
    API_V1_STR: str = "/api/v1"
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    
    ENVIRONMENT: str = "development" # development | production
    DEFAULT_SECRET_KEY: str = "democratizacion_datos_super_secret_key_local_2026_aes256_change_in_prod"

    # Secret Key for JWT Tokens and AES Encryption
    SECRET_KEY: str = "democratizacion_datos_super_secret_key_local_2026_aes256_change_in_prod"
    FERNET_KEY: Optional[str] = None # Auto-generated if not set
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours local session
    
    # Internal Metadata Database (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "democratizacion_metadatos"
    
    # Local LLM Default Settings
    LLM_PROVIDER: str = "ollama" # ollama | openai_compatible | custom
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OPENAI_COMPATIBLE_URL: str = "http://localhost:8000/v1"
    OPENAI_COMPATIBLE_API_KEY: str = "lm-studio"

    # Ventana de contexto por request. Antes era el literal 16384 repetido en
    # tres lugares de `llm_service.py`. Qwen2.5-Coder-7B tiene 32K nativos
    # (131K con YaRN), asi que 16K desperdiciaba la mitad sin motivo.
    #
    # Honesto sobre el alcance: solo lo aplica el servidor que lo acepta por
    # request. llama.cpp lo fija al arrancar (`llama-server -c 32768`) y LM
    # Studio lo ignora; en ambos hace falta arrancar el servidor con la
    # ventana que se quiera de verdad.
    LLM_NUM_CTX: int = 32768
    
    # Security Defaults
    DEFAULT_ROW_LIMIT: int = 500
    QUERY_TIMEOUT_SECONDS: int = 15

    # Path to Dedicated Metadata Database (Users, Roles, Connectors, Sessions, Audit, Catalog)
    @property
    def METADATA_DB_PATH(self) -> str:
        return os.path.join(_root_dir(), "datia_metadata.db")

    # Path to Uploaded and Structured Data Sources
    @property
    def DATA_SOURCES_DIR(self) -> str:
        p = os.path.join(_root_dir(), "data_sources")
        os.makedirs(p, exist_ok=True)
        return p

    # Path to SQLite Demo Database (Centralized)
    @property
    def SQLITE_DB_PATH(self) -> str:
        return os.path.join(_backend_dir(), "demo_corporativa.db")


    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
