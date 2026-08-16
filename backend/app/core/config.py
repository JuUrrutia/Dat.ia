import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Democratización de Datos Corporativos con IA Local"
    API_V1_STR: str = "/api/v1"
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    
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
    
    # Security Defaults
    DEFAULT_ROW_LIMIT: int = 1000
    QUERY_TIMEOUT_SECONDS: int = 15

    # Path to SQLite Demo Database (Centralized)
    @property
    def SQLITE_DB_PATH(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "demo_corporativa.db"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
