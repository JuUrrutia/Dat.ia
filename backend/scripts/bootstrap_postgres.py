"""
DATIA - PostgreSQL Database Bootstrapper
Checks if PostgreSQL database and tables exist.
Creates database, schemas, tables, and seeds initial data idempotently.
"""

import os
import sys
import logging

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base, get_database_url
from app.db.init_db import init_db

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("bootstrap_postgres")

def ensure_postgres_database():
    """
    Connects to PostgreSQL maintenance database to check if target POSTGRES_DB exists.
    If not, creates it.
    """
    server = settings.POSTGRES_SERVER
    port = settings.POSTGRES_PORT
    user = settings.POSTGRES_USER
    pwd = settings.POSTGRES_PASSWORD
    target_db = settings.POSTGRES_DB

    # Maintenance connection to 'postgres' database with autocommit isolation
    maintenance_url = f"postgresql+psycopg://{user}:{pwd}@{server}:{port}/postgres"
    
    try:
        m_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
        with m_engine.connect() as conn:
            check_sql = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
            result = conn.execute(check_sql, {"dbname": target_db}).scalar()
            if not result:
                logger.info(f"Database '{target_db}' does not exist on {server}:{port}. Creating database...")
                conn.execute(text(f'CREATE DATABASE "{target_db}" OWNER "{user}"'))
                logger.info(f"Database '{target_db}' created successfully.")
            else:
                logger.info(f"Database '{target_db}' already exists on {server}:{port}.")
        m_engine.dispose()
        return True
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL maintenance database at {server}:{port}: {e}")
        return False

def ensure_tables_and_seed_data():
    """
    Connects to the target POSTGRES_DB, creates any missing tables, and seeds initial data.
    """
    pg_url = get_database_url()
    try:
        engine = create_engine(pg_url, pool_pre_ping=True)
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = set(Base.metadata.tables.keys())

        missing = expected_tables - existing_tables
        if missing:
            logger.info(f"Creating {len(missing)} missing tables in '{settings.POSTGRES_DB}': {', '.join(sorted(missing))}...")
        else:
            logger.info(f"All {len(expected_tables)} governance tables already exist in '{settings.POSTGRES_DB}'.")

        # Create all tables (idempotent)
        Base.metadata.create_all(bind=engine)

        # Seed default data
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            init_db(db)
            logger.info(f"Initial seed data (roles, users, domains, permissions, catalog) verified successfully.")
        finally:
            db.close()
        
        engine.dispose()
        return True
    except Exception as e:
        logger.error(f"Error initializing tables in '{settings.POSTGRES_DB}': {e}")
        return False

def bootstrap():
    logger.info("==========================================")
    logger.info("DATIA POSTGRESQL BOOTSTRAP CHECK")
    logger.info("==========================================")
    logger.info(f"Target: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

    db_ready = ensure_postgres_database()
    if not db_ready:
        logger.warning(
            f"PostgreSQL server ({settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}) is currently not reachable. "
            "Skipping offline bootstrap. The backend will automatically bootstrap when PostgreSQL is running."
        )
        return False

    tables_ready = ensure_tables_and_seed_data()
    if tables_ready:
        logger.info("PostgreSQL initialization & validation complete!")
        return True
    return False

if __name__ == "__main__":
    success = bootstrap()
    # Exit with 0 so build pipeline proceeds smoothly even if PostgreSQL is offline
    sys.exit(0)
