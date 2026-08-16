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
except Exception:
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "demo_corporativa.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

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
        engine = create_engine(new_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
    except Exception:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "demo_corporativa.db")
        new_url = f"sqlite:///{db_path}"
        engine = create_engine(new_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine
