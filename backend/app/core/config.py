import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Democratización de Datos Corporativos con IA Local"
    API_V1_STR: str = "/api/v1"
    
    # Secret Key for JWT Tokens and AES Encryption
    SECRET_KEY: str = os.getenv("SECRET_KEY", "democratizacion_datos_super_secret_key_local_2026_aes256_change_in_prod")
    FERNET_KEY: Optional[str] = os.getenv("FERNET_KEY", None) # Auto-generated if not set
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours local session
    
    # Internal Metadata Database (PostgreSQL)
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "democratizacion_metadatos")
    
    # Local LLM Default Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama") # ollama | openai_compatible | custom
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    OPENAI_COMPATIBLE_URL: str = os.getenv("OPENAI_COMPATIBLE_URL", "http://localhost:8000/v1")
    OPENAI_COMPATIBLE_API_KEY: str = os.getenv("OPENAI_COMPATIBLE_API_KEY", "lm-studio")
    
    # Security Defaults
    DEFAULT_ROW_LIMIT: int = 1000
    QUERY_TIMEOUT_SECONDS: int = 15

    class Config:
        case_sensitive = True

settings = Settings()
