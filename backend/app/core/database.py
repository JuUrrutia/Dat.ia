import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

def get_database_url(
    server: str = settings.POSTGRES_SERVER,
    port: int = settings.POSTGRES_PORT,
    user: str = settings.POSTGRES_USER,
    password: str = settings.POSTGRES_PASSWORD,
    db_name: str = settings.POSTGRES_DB
) -> str:
    """Builds PostgreSQL database connection URL for psycopg driver."""
    return f"postgresql+psycopg://{user}:{password}@{server}:{port}/{db_name}"

# Initial Engine: Attempt PostgreSQL connection, fallback to SQLite for standalone demo mode
try:
    DATABASE_URL = get_database_url()
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )
    with engine.connect() as conn:
        pass
except Exception:
    db_path = settings.METADATA_DB_PATH
    DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def ensure_schema_migrations(eng):
    """
    Auto-migrates incremental schema columns (e.g. null_policy, is_uploaded)
    for existing SQLite and PostgreSQL metadata databases without requiring manual Alembic steps.
    """
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(eng)
        table_names = set(inspector.get_table_names())

        if "corporate_connections" in table_names:
            try:
                conn_cols = {c["name"] for c in inspector.get_columns("corporate_connections")}
                with eng.begin() as conn:
                    if "is_uploaded" not in conn_cols:
                        conn.execute(text("ALTER TABLE corporate_connections ADD COLUMN is_uploaded BOOLEAN DEFAULT 0 NOT NULL"))
                    if "null_policy" not in conn_cols:
                        conn.execute(text("ALTER TABLE corporate_connections ADD COLUMN null_policy VARCHAR(50) DEFAULT 'open'"))
            except Exception:
                pass

        if "users" in table_names:
            try:
                user_cols = {c["name"] for c in inspector.get_columns("users")}
                with eng.begin() as conn:
                    if "failed_login_attempts" not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL"))
                    if "locked_until" not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL"))
                    if "must_change_password" not in user_cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL"))
            except Exception:
                pass

        if "audit_logs" in table_names:
            try:
                audit_cols = {c["name"] for c in inspector.get_columns("audit_logs")}
                with eng.begin() as conn:
                    if "result_snapshot" not in audit_cols:
                        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN result_snapshot TEXT NULL"))
            except Exception:
                pass

        if "query_learning_memories" in table_names:
            try:
                mem_cols = {c["name"] for c in inspector.get_columns("query_learning_memories")}
                with eng.begin() as conn:
                    if "is_golden" not in mem_cols:
                        conn.execute(text("ALTER TABLE query_learning_memories ADD COLUMN is_golden BOOLEAN DEFAULT FALSE NOT NULL"))
            except Exception:
                pass
    except Exception:
        pass

ensure_schema_migrations(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """Dependency for obtaining database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_database_engine(server: str, port: int, user: str, password: str, db_name: str):
    """Updates global engine with new PostgreSQL credentials (used by Setup Wizard)."""
    global engine, SessionLocal
    try:
        new_url = get_database_url(server, port, user, password, db_name)
        new_engine = create_engine(new_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
        with new_engine.connect() as conn:
            pass
        engine = new_engine
    except Exception:
        db_path = settings.METADATA_DB_PATH
        new_url = f"sqlite:///{db_path}"
        engine = create_engine(new_url, connect_args={"check_same_thread": False})
    ensure_schema_migrations(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine

def build_engine_for_connector(conn):
    """
    Dynamically creates an isolated SQLAlchemy engine for any registered CorporateConnection.
    Supports PostgreSQL and SQLite.
    """
    from app.core.security import decrypt_credential
    from app.modules.admin_catalog.models import DatabaseType

    if conn.db_type == DatabaseType.POSTGRESQL or str(conn.db_type).lower() == "postgresql":
        pwd = decrypt_credential(conn.encrypted_password) if conn.encrypted_password else ""
        port = conn.port if conn.port and conn.port > 0 else 5432
        url = f"postgresql+psycopg://{conn.username}:{pwd}@{conn.host}:{port}/{conn.database_name}"
        return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)

    # SQLite (local file database)
    db_path = conn.host if (conn.host and os.path.exists(conn.host)) else settings.SQLITE_DB_PATH
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
