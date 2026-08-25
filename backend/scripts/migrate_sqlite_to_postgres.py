"""
DATIA - SQLite to PostgreSQL Automated Migration Tool
Transfers all governance metadata, users, roles, RBAC permissions,
corporate connections, semantic catalogs, and audit logs into PostgreSQL.
"""

import os
import sys
import logging

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base, get_database_url
from app.modules.auth.models import User, Role, Domain, UserSession
from app.modules.admin_catalog.models import (
    CorporateConnection,
    SemanticCatalog,
    RoleTablePermission,
    RoleColumnPermission,
)
from app.modules.telemetry_audit.models import AuditLog

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("sqlite_to_postgres_migration")

MODELS_IN_ORDER = [
    Domain,
    Role,
    User,
    CorporateConnection,
    RoleTablePermission,
    RoleColumnPermission,
    SemanticCatalog,
    AuditLog,
    UserSession,
]

def migrate():
    sqlite_path = settings.METADATA_DB_PATH
    if not os.path.exists(sqlite_path):
        logger.warning(f"SQLite metadata file '{sqlite_path}' does not exist. Nothing to migrate.")
        return

    sqlite_url = f"sqlite:///{sqlite_path}"
    pg_url = get_database_url()

    logger.info(f"Source (SQLite): {sqlite_url}")
    logger.info(f"Target (PostgreSQL): {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

    # Create engines
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    try:
        pg_engine = create_engine(pg_url, pool_pre_ping=True)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        logger.info("Successfully connected to target PostgreSQL server.")
    except Exception as e:
        logger.error(f"Cannot connect to PostgreSQL at {pg_url}: {e}")
        logger.error("Make sure PostgreSQL is running (e.g., via 'docker compose up -d').")
        sys.exit(1)

    # Create all schema tables in PostgreSQL
    logger.info("Creating schema and tables in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    sqlite_db = SqliteSession()
    pg_db = PgSession()

    try:
        total_migrated = 0

        for model in MODELS_IN_ORDER:
            table_name = model.__tablename__
            rows = sqlite_db.query(model).all()
            if not rows:
                logger.info(f"Table '{table_name}': 0 rows (skipped)")
                continue

            logger.info(f"Migrating table '{table_name}' ({len(rows)} rows)...")

            for row in rows:
                # Convert model instance to dictionary
                row_data = {
                    c.name: getattr(row, c.name)
                    for c in model.__table__.columns
                }

                # Check if row already exists in target
                pk_name = model.__table__.primary_key.columns.values()[0].name
                pk_val = row_data.get(pk_name)
                existing = pg_db.query(model).filter(getattr(model, pk_name) == pk_val).first()

                if not existing:
                    new_obj = model(**row_data)
                    pg_db.add(new_obj)
                    total_migrated += 1

            pg_db.commit()

            # Reset PostgreSQL serial sequence for auto-increment PKs
            try:
                with pg_engine.begin() as conn:
                    conn.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_name}'), "
                        f"COALESCE((SELECT MAX({pk_name}) FROM {table_name}), 1));"
                    ))
            except Exception:
                pass

        logger.info(f"Migration completed successfully! Total rows transferred: {total_migrated}")

    except Exception as e:
        pg_db.rollback()
        logger.error(f"Migration failed with error: {e}")
        raise
    finally:
        sqlite_db.close()
        pg_db.close()

if __name__ == "__main__":
    migrate()
