import os
import re
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from app.core.logging import logger

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
        echo=False,
        connect_args={"connect_timeout": 5},
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
    Uses lock_timeout on PostgreSQL to avoid deadlocks with abandoned sessions.
    """
    try:
        from sqlalchemy import inspect, text
        is_pg = "postgresql" in str(eng.url)

        table_names = set(inspect(eng).get_table_names())

        def _cols(table):
            """Columnas ACTUALES de `table`.

            Reinspecciona en cada llamada a propósito. El inspector se creó
            antes de los ALTER, así que reutilizar sus decisiones hace que el
            bloque de `audit_logs` (que primero añade `result_snapshot` y luego
            reconstruye la tabla) decida sobre columnas que ya cambiaron.
            """
            return {c["name"] for c in inspect(eng).get_columns(table)}

        def _safe_alter(conn, stmts):
            """Execute ALTER stmts with a short lock timeout on PG."""
            if is_pg:
                conn.execute(text("SET lock_timeout = '3s'"))
            for s in stmts:
                conn.execute(text(s))

        # Indices de las tablas que el motor de chat consulta en CADA request.
        # SQLAlchemy no crea indices en columnas FK, asi que los `Index(...)` de
        # los modelos solo valen para bases creadas desde cero: una instalacion
        # existente se los tiene que crear aqui. `IF NOT EXISTS` funciona igual
        # en PostgreSQL y en SQLite, y hace que esto sea idempotente.
        #
        # Sin esto, `get_authorized_schema_prompt` (3 veces por query, via
        # `governance_guard`) hace un seq scan de las tablas de permisos.
        #
        # ponytail: se crean al arrancar, no hay migracion incremental; con
        # tablas de permisos de miles de filas el CREATE INDEX bloquea la
        # escritura en PostgreSQL durante unos segundos. Si eso molestara,
        # crear con CONCURRENTLY fuera de la transaccion.
        _indexes = [
            ("role_table_permissions", "ix_role_table_perm_lookup",
             "CREATE INDEX IF NOT EXISTS ix_role_table_perm_lookup ON role_table_permissions (role_id, connection_id, is_allowed)"),
            ("role_column_permissions", "ix_role_column_perm_lookup",
             "CREATE INDEX IF NOT EXISTS ix_role_column_perm_lookup ON role_column_permissions (role_id, connection_id)"),
            ("semantic_catalog", "ix_semantic_catalog_connection",
             "CREATE INDEX IF NOT EXISTS ix_semantic_catalog_connection ON semantic_catalog (connection_id)"),
        ]
        pending_indexes = [sql for tbl, _name, sql in _indexes if tbl in table_names]
        if pending_indexes:
            try:
                with eng.begin() as conn:
                    _safe_alter(conn, pending_indexes)
            except Exception as e:
                logger.warning(f"Migración: no se pudieron crear los índices de permisos: {e}")

        if "corporate_connections" in table_names:
            pending = []
            try:
                conn_cols = _cols("corporate_connections")
                if "is_uploaded" not in conn_cols:
                    pending.append("ALTER TABLE corporate_connections ADD COLUMN is_uploaded BOOLEAN DEFAULT 0 NOT NULL")
                if "null_policy" not in conn_cols:
                    pending.append("ALTER TABLE corporate_connections ADD COLUMN null_policy VARCHAR(50) DEFAULT 'open'")
                if pending:
                    with eng.begin() as conn:
                        _safe_alter(conn, pending)
            except Exception as e:
                logger.warning(f"Migración: corporate_connections quedó sin migrar ({'; '.join(pending)}): {e}")

        if "users" in table_names:
            pending = []
            try:
                user_cols = _cols("users")
                if "failed_login_attempts" not in user_cols:
                    pending.append("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL")
                if "locked_until" not in user_cols:
                    pending.append("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL")
                if "must_change_password" not in user_cols:
                    pending.append("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL")
                if pending:
                    with eng.begin() as conn:
                        _safe_alter(conn, pending)
            except Exception as e:
                logger.warning(f"Migración: users quedó sin migrar ({'; '.join(pending)}): {e}")

        if "audit_logs" in table_names:
            try:
                audit_cols = _cols("audit_logs")
                if "result_snapshot" not in audit_cols:
                    with eng.begin() as conn:
                        _safe_alter(conn, ["ALTER TABLE audit_logs ADD COLUMN result_snapshot TEXT NULL"])
            except Exception as e:
                logger.warning(f"Migración: audit_logs.result_snapshot no se añadió: {e}")

            # `validation_status` era NOT NULL. Eso no era una garantia de dato, era
            # la causa de que el router inventara "APROBADO" cuando la respuesta no
            # traia trazabilidad: en el CSV de compliance que abre el admin, "" y
            # "APROBADO" tienen que significar cosas distintas (no lo se / validado).
            # Se abre la columna en vez de meter un centinela "DESCONOCIDO" porque el
            # proyecto ya tiene el valor honesto para eso: None.
            try:
                vs = next(
                    (c for c in inspect(eng).get_columns("audit_logs") if c["name"] == "validation_status"),
                    None,
                )
                if vs is not None and not vs.get("nullable", True):
                    if is_pg:
                        with eng.begin() as conn:
                            _safe_alter(conn, [
                                "ALTER TABLE audit_logs ALTER COLUMN validation_status DROP NOT NULL"
                            ])
                    else:
                        # Antes de abrir la transacción: `_cols` abre su propia
                        # conexión y un segundo lector contra un write lock
                        # abierto en SQLite da "database is locked".
                        cols = ", ".join('"%s"' % c for c in _cols("audit_logs"))
                        # SQLite no tiene ALTER COLUMN. Se reconstruye la tabla
                        # desde su propio DDL en sqlite_master quitando el NOT NULL
                        # de ESA columna: no hay DDL hardcodeado que pueda quedar
                        # desfasado del modelo.
                        with eng.begin() as conn:
                            row = conn.execute(text(
                                "SELECT sql FROM sqlite_master WHERE type='table' AND name='audit_logs'"
                            )).scalar()
                            new_ddl = re.sub(
                                r"(\bvalidation_status\b[^,\n]*?)\s+NOT\s+NULL",
                                r"\1",
                                row,
                                count=1,
                                flags=re.IGNORECASE,
                            )
                            idx = [r[0] for r in conn.execute(text(
                                "SELECT sql FROM sqlite_master WHERE type='index' "
                                "AND tbl_name='audit_logs' AND sql IS NOT NULL"
                            )).fetchall()]
                            # PRAGMA fuera de transaccion: SQLite la ignora dentro de BEGIN.
                            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
                            conn.execute(text("ALTER TABLE audit_logs RENAME TO audit_logs__old"))
                            conn.execute(text(new_ddl.replace("audit_logs", "audit_logs__new", 1)))
                            conn.execute(text(
                                f"INSERT INTO audit_logs__new ({cols}) SELECT {cols} FROM audit_logs__old"
                            ))
                            conn.execute(text("DROP TABLE audit_logs__old"))
                            conn.execute(text("ALTER TABLE audit_logs__new RENAME TO audit_logs"))
                            # Los indices se recreationan con su SQL original: la tabla
                            # ya volvio a llamarse audit_logs y el DROP del "__old" libero
                            # los nombres.
                            for sql in idx:
                                conn.execute(text(sql))
                            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            except Exception as e:
                logger.warning(f"Migración: audit_logs.validation_status sigue NOT NULL: {e}")

        if "query_learning_memories" in table_names:
            try:
                mem_cols = _cols("query_learning_memories")
                if "is_golden" not in mem_cols:
                    with eng.begin() as conn:
                        _safe_alter(conn, ["ALTER TABLE query_learning_memories ADD COLUMN is_golden BOOLEAN DEFAULT FALSE NOT NULL"])
            except Exception as e:
                logger.warning(f"Migración: query_learning_memories.is_golden no se añadió: {e}")

        if "chat_conversations" in table_names:
            try:
                conv_cols = _cols("chat_conversations")
                if "is_shared" not in conv_cols:
                    # Los hilos existentes NO se marcan como compartidos: el valor
                    # por defecto falla cerrado, asi que un despliegue que actualice
                    # no expone historiales que antes eran privados por accidente.
                    with eng.begin() as conn:
                        _safe_alter(conn, ["ALTER TABLE chat_conversations ADD COLUMN is_shared BOOLEAN DEFAULT FALSE NOT NULL"])
            except Exception as e:
                logger.warning(f"Migración: chat_conversations.is_shared no se añadió: {e}")
    except Exception as e:
        # Sin esto, una migración a medias se descubre cuando una consulta
        # muere con UndefinedColumn, sin rastro de qué la dejó a medias.
        logger.warning(f"Migración de esquema incompleta: {e}")

ensure_schema_migrations(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """Dependency for obtaining database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def discard_failed_transaction(db) -> None:
    """Deja la sesión utilizable después de un error que el código se tragó.

    En PostgreSQL una sentencia fallida ABORTA la transacción: todo lo que se
    ejecute después en esa misma sesión responde `InFailedSqlTransaction` hasta que
    se hace rollback. Los handlers "best-effort" (guardas de esquema, memoria de
    aprendizaje, Lookups de conexion) se tragan su excepción y seguían usando la
    sesión de la request, así que el query siguiente moría con un error sin
    relación con lo que estaba haciendo. El caso reportado: `GET /system/anomalies`
    devolvía 500 desde su propio `except Exception: pass`, en la línea siguiente.

    Deliberadamente NO va en el `finally` de `get_db`. Medido contra PostgreSQL: una
    sesión sucia NO contamina a la request siguiente, porque `Session.close()`
    devuelve la conexión al pool con rollback. El defecto es siempre intra-request.
    """
    try:
        db.rollback()
    except Exception:
        pass

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


@contextmanager
def connector_engine(conn):
    """Engine del conector, liberado siempre al salir del bloque.

    `with eng.connect()` cierra la CONEXION pero no el ENGINE: el pool de sockets
    (pool_size=5 + max_overflow=10) queda abierto. Como cada consulta del chat
    creaba su propio engine y ninguno hacia dispose(), se acumulaban pools
    huerfanos contra el Postgres del cliente hasta "too many clients already".

    No se cachean engines a proposito: reconectar cuesta ~100 ms contra un LLM que
    tarda 8-25 s, asi que un registro de engines seria complejidad sin beneficio.
    """
    eng = build_engine_for_connector(conn)
    try:
        yield eng
    finally:
        eng.dispose()
