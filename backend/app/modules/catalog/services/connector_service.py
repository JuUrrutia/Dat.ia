import os
import re
import shutil
import sqlite3
import time
import uuid
from typing import List, Optional, Any, Dict
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.security import encrypt_credential
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType, SemanticCatalog, RoleTablePermission
from app.modules.auth.models import Role
from app.modules.admin_catalog.schemas import (
    CorporateConnectionCreate, CorporateConnectionUpdate, CorporateConnectionOut,
    ConnectionTestRequest, ConnectionTestResult
)
from app.core.database import engine as app_engine
from app.modules.admin_catalog.tabular_importer import (
    convert_uploaded_file_to_sqlite,
    convert_uploaded_file_to_postgres,
)
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.modules.system.health_service import HealthService

class ConnectorDomainService:
    """
    Domain service for Corporate Connection lifecycle, file uploads, and connectivity health checks.
    """

    @classmethod
    def ensure_data_sources_dir(cls) -> str:
        d = settings.DATA_SOURCES_DIR
        os.makedirs(d, exist_ok=True)
        return d

    @classmethod
    def _activate_exclusively(cls, db: Session, conn_id: int) -> None:
        """Deja `conn_id` como la UNICA conexion activa.

        `is_active` es un booleano que el producto lee como un singleton: nueve
        lugares hacen `WHERE is_active = true` y tres de ellos `ORDER BY id DESC
        LIMIT 1`, o sea que "cual es la conexion activa" se responde por id, no
        por decision. Pero NINGUN sitio de escritura mantenia la exclusion:
        `upload_database_file` clavaba `is_active=True` sin tocar las demas.

        El efecto era acumulativo y por eso rompia para todos los roles a la vez.
        En la instalacion real quedaron dos conectores activos: la demo de
        plataforma (292, con las 74 filas de la matriz RBAC sembradas) y el
        dataset subido (2509, con cero permisos porque default-deny es lo
        correcto). El motor elegia 2509 por id, que es justo el que no tiene
        permisos: subir un dataset dejaba a todos los no-admin sin datos en todo
        el producto, y el sintoma se leia como "la IA no funciona con esta base".

        Por eso la exclusion vive ACA y no repetida en cada writer: todo lo que
        deje una conexion activa pasa por este metodo.

        No toca la matriz de permisos: activar un conector no concede acceso a
        nadie (default-deny, ver `upload_database_file`). Solo decide cual es la
        fuente de la consulta.
        """
        db.query(CorporateConnection).filter(
            CorporateConnection.is_active == True,
            CorporateConnection.id != conn_id,
        ).update({CorporateConnection.is_active: False}, synchronize_session=False)

    @classmethod
    def list_connectors(cls, db: Session) -> List[CorporateConnection]:
        return db.query(CorporateConnection).order_by(CorporateConnection.created_at.desc()).all()

    @classmethod
    def create_connector(cls, db: Session, conn_in: CorporateConnectionCreate) -> CorporateConnection:
        existing = db.query(CorporateConnection).filter(CorporateConnection.name == conn_in.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una conexión registrada con ese nombre."
            )

        encrypted_pwd = encrypt_credential(conn_in.password) if conn_in.password else ""

        # Ensure dedicated individual PostgreSQL database exists on host if local server
        if (conn_in.db_type == DatabaseType.POSTGRESQL or str(conn_in.db_type).lower() == "postgresql") and conn_in.host in ("localhost", "127.0.0.1", settings.POSTGRES_SERVER):
            from sqlalchemy import create_engine, text
            clean_db = re.sub(r'[^a-zA-Z0-9_]', '_', conn_in.database_name.lower()).strip('_')
            if clean_db:
                maint_url = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
                m_engine = create_engine(maint_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
                try:
                    with m_engine.connect() as m_conn:
                        exists = m_conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": clean_db}).scalar()
                        if not exists:
                            m_conn.execute(text(f'CREATE DATABASE "{clean_db}" OWNER "{settings.POSTGRES_USER}"'))
                except Exception as exc:
                    # Antes era `except: pass`: faltaba privilegio CREATEDB o el
                    # nombre chocaba, el error se tragaba sin registrar nada, y
                    # se insertaba igual un CorporateConnection apuntando a una
                    # base inexistente con respuesta 201 Created. Ademas el
                    # dispose() se saltaba en el camino de error.
                    logger.error(
                        "No se pudo crear la base '%s' del conector '%s': %s",
                        clean_db, conn_in.name, exc,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            f"No se pudo crear la base '{clean_db}' en el servidor PostgreSQL: {exc}. "
                            "Verifique que el usuario tenga privilegio CREATEDB y que el nombre no este en uso."
                        ),
                    ) from exc
                finally:
                    m_engine.dispose()

        new_conn = CorporateConnection(
            name=conn_in.name,
            db_type=conn_in.db_type,
            host=conn_in.host,
            port=conn_in.port,
            database_name=conn_in.database_name,
            username=conn_in.username or "admin",
            encrypted_password=encrypted_pwd,
            is_active=conn_in.is_active,
            is_uploaded=conn_in.is_uploaded
        )

        db.add(new_conn)
        db.commit()
        db.refresh(new_conn)

        if new_conn.is_active:
            cls._activate_exclusively(db, new_conn.id)
            db.commit()

        CatalogDomainService.seed_catalog_heuristics_for_connection(db, new_conn.id, new_conn.host)

        return new_conn

    @classmethod
    async def upload_database_file(
        cls,
        db: Session,
        file: UploadFile,
        name: Optional[str] = None
    ) -> CorporateConnectionOut:
        ds_dir = cls.ensure_data_sources_dir()
        original_filename = file.filename or "uploaded_database.sqlite"
        clean_filename = "".join(c for c in original_filename if c.isalnum() or c in (".", "_", "-"))
        ext = os.path.splitext(clean_filename)[1].lower()

        # `.sql` NO se acepta. Ejecutar un script arbitrario contra la base daba
        # DDL/DML sin pasar por ASTValidator, con el usuario del conector (que en la
        # imagen oficial es superusuario), y los errores se tragaban reportando 201.
        # Conectar a Oracle/MySQL/MSSQL es otra funcionalidad (connectors) y no
        # depende de esto.
        allowed_exts = [".sqlite", ".db", ".sqlite3", ".csv", ".xlsx", ".xls", ".tsv", ".txt"]
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato no soportado. Debe ser un archivo SQLite, Excel, CSV o volcado SQL."
            )

        # NO se le mete un uuid acá a propósito: el importador toma el nombre de la tabla
        # del nombre de este archivo temporal (`os.path.splitext(basename)[0]` en
        # postgres_importer), así que un sufijo aleatorio acá renombra las tablas
        # del dataset. La colisión de este path es latente y se reporta aparte.
        unique_raw_name = f"raw_{int(time.time())}_{clean_filename}"
        raw_target_path = os.path.join(ds_dir, unique_raw_name)

        try:
            with open(raw_target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al guardar el archivo en el servidor: {str(e)}"
            )

        base_display_name = name.strip() if (name and name.strip()) else os.path.splitext(original_filename)[0]
        final_name = base_display_name
        counter = 1
        while db.query(CorporateConnection).filter(CorporateConnection.name == final_name).first():
            final_name = f"{base_display_name}_{counter}"
            counter += 1

        is_postgres_active = app_engine.dialect.name == "postgresql"
        detected_tables = []
        target_path = None
        pg_target_db_name = None

        if is_postgres_active:
            from sqlalchemy import create_engine, text

            # Sanitize database name for PostgreSQL (lowercase alphanumeric and underscores)
            clean_db_name = re.sub(r'[^a-zA-Z0-9_]', '_', final_name.lower()).strip('_')
            if not clean_db_name or clean_db_name[0].isdigit():
                clean_db_name = f"db_{clean_db_name}"
            clean_db_name = clean_db_name[:50]
            pg_target_db_name = clean_db_name

            # Create dedicated PostgreSQL database if not exists
            maint_url = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
            m_engine = create_engine(maint_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
            try:
                with m_engine.connect() as m_conn:
                    exists = m_conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": pg_target_db_name}).scalar()
                    if not exists:
                        m_conn.execute(text(f'CREATE DATABASE "{pg_target_db_name}" OWNER "{settings.POSTGRES_USER}"'))
            finally:
                m_engine.dispose()

            business_url = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{pg_target_db_name}"
            pg_engine = create_engine(business_url, pool_pre_ping=True)
            try:
                detected_tables = convert_uploaded_file_to_postgres(
                    source_path=raw_target_path,
                    ext=ext,
                    target_engine=pg_engine
                )
            except Exception as err:
                if os.path.exists(raw_target_path):
                    try: os.remove(raw_target_path)
                    except Exception: pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error al procesar e importar archivo en PostgreSQL '{original_filename}': {str(err)}"
                )
            finally:
                pg_engine.dispose()
                if os.path.exists(raw_target_path):
                    try: os.remove(raw_target_path)
                    except Exception: pass
        else:
            sqlite_db_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{os.path.splitext(clean_filename)[0]}.sqlite"
            target_path = os.path.join(ds_dir, sqlite_db_name)

            if ext in [".sqlite", ".db", ".sqlite3"]:
                # int(time.time()) tiene granularidad de segundo: dos uploads del
                # mismo archivo en el mismo segundo producían el MISMO path, o sea
                # dos conectores (datos y datos_1) apuntando al mismo archivo. El
                # segundo import pisaba el contenido del primero, y borrar uno
                # dejaba al otro apuntando a la nada. El sufijo uuid hace el
                # nombre único de verdad. Ojo: el dedup de arriba es sobre el
                # NOMBRE del conector, no sobre la ruta.
                target_path = os.path.join(ds_dir, f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{clean_filename}")
                shutil.move(raw_target_path, target_path)

            try:
                detected_tables = convert_uploaded_file_to_sqlite(
                    source_path=target_path if ext in [".sqlite", ".db", ".sqlite3"] else raw_target_path,
                    ext=ext,
                    target_sqlite_path=target_path
                )
            except Exception as err:
                if os.path.exists(raw_target_path):
                    try: os.remove(raw_target_path)
                    except Exception: pass
                if os.path.exists(target_path):
                    try: os.remove(target_path)
                    except Exception: pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error al procesar e importar archivo '{original_filename}': {str(err)}"
                )
            finally:
                if raw_target_path != target_path and os.path.exists(raw_target_path):
                    try: os.remove(raw_target_path)
                    except Exception: pass

        if is_postgres_active:
            new_conn = CorporateConnection(
                name=final_name,
                db_type=DatabaseType.POSTGRESQL,
                host=settings.POSTGRES_SERVER,
                port=settings.POSTGRES_PORT,
                database_name=pg_target_db_name,
                username=settings.POSTGRES_USER,
                encrypted_password=encrypt_credential(settings.POSTGRES_PASSWORD),
                is_active=True,
                is_uploaded=True
            )
        else:
            new_conn = CorporateConnection(
                name=final_name,
                db_type=DatabaseType.SQLITE,
                host=target_path,
                port=0,
                database_name=original_filename,
                username="admin",
                encrypted_password="",
                is_active=True,
                is_uploaded=True
            )
        db.add(new_conn)
        db.commit()
        db.refresh(new_conn)

        # El dataset nuevo pasa a ser la unica fuente de la consulta: antes se
        # dejaba la anterior en `is_active=True` y el motor, que elige por
        # `ORDER BY id DESC`, se quedaba con este por defecto sin que nadie lo
        # hubiera pedido. Ver `_activate_exclusively`.
        cls._activate_exclusively(db, new_conn.id)
        db.commit()

        # Default-deny: subir un dataset NO concede acceso a nadie.
        #
        # Antes este bloque creaba un RoleTablePermission(is_allowed=True) por cada
        # (rol, tabla) y solo se saltaban unas cuantas tablas de la demo SAP,
        # detectadas por substring sobre el NOMBRE del rol. En cualquier dataset que
        # no fuera esa demo la lista de exclusion no excluye nada, asi que casi
        # todos los roles quedaban con las todas las tablas: la mascara por columna
        # de governance_guard seguia aplicando, pero el permiso de tabla que la
        # precede ya habia concedido el acceso. Default-allow por ausencia de
        # evidencia.
        #
        # Ahora no hay acceso hasta que un admin lo conceda con
        # PUT /api/v1/permissions (ConnectorDomainService.set_role_table_permissions).
        # `requires_permission_review=True` y `detected_tables` le dicen al admin
        # que hay tabla nueva sin nadie autorizado todavia.
        db.commit()
        db.refresh(new_conn)

        # Automatically seed heuristic semantic descriptions & data dictionary definitions
        CatalogDomainService.seed_catalog_heuristics_for_connection(
            db, new_conn.id, target_path if not is_postgres_active else None, only_tables=detected_tables
        )

        return CorporateConnectionOut(
            id=new_conn.id,
            name=new_conn.name,
            db_type=new_conn.db_type,
            host=new_conn.host,
            port=new_conn.port,
            database_name=new_conn.database_name,
            username=new_conn.username,
            is_active=new_conn.is_active,
            is_uploaded=new_conn.is_uploaded,
            requires_permission_review=True,
            detected_tables=detected_tables,
            created_at=new_conn.created_at
        )

    @classmethod
    def update_connector(cls, db: Session, conn_id: int, conn_in: CorporateConnectionUpdate) -> CorporateConnection:
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conexión de base de datos no encontrada."
            )

        if conn_in.name and conn_in.name != conn.name:
            existing = db.query(CorporateConnection).filter(CorporateConnection.name == conn_in.name).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe otra conexión registrada con ese nombre."
                )
            conn.name = conn_in.name

        if conn_in.db_type is not None:
            conn.db_type = conn_in.db_type
        if conn_in.host is not None:
            conn.host = conn_in.host
        if conn_in.port is not None:
            conn.port = conn_in.port
        if conn_in.database_name is not None:
            conn.database_name = conn_in.database_name
        if conn_in.username is not None:
            conn.username = conn_in.username
        if conn_in.password:
            conn.encrypted_password = encrypt_credential(conn_in.password)
        if conn_in.is_active is not None:
            conn.is_active = conn_in.is_active

        db.commit()
        db.refresh(conn)
        if conn.is_active:
            cls._activate_exclusively(db, conn.id)
            db.commit()
            db.refresh(conn)
        return conn

    @classmethod
    def toggle_connector_active(cls, db: Session, conn_id: int) -> CorporateConnection:
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conexión de base de datos no encontrada."
            )
        conn.is_active = not conn.is_active
        db.commit()
        db.refresh(conn)
        if conn.is_active:
            # Encender una conexion apaga las demas: el toggle de la UI es la via
            # normal para cambiar de fuente, y si no las apagara el estado
            # "hay varias activas" volveria a ser alcanzable desde el producto.
            cls._activate_exclusively(db, conn.id)
            db.commit()
            db.refresh(conn)
        return conn

    @classmethod
    def delete_connector(cls, db: Session, conn_id: int) -> Dict[str, Any]:
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conexión de base de datos no encontrada."
            )

        # Si era un dataset subido a PostgreSQL, se limpia lo que la app creo para el.
        #
        # Antes la condicion era una lista NEGRA: si el nombre NO estaba en
        # ["democratizacion_empresa", "democratizacion_metadatos", "postgres"] hacia
        # DROP DATABASE; y si ESTABA, caia en la rama else que hacia DROP TABLE sobre
        # esa misma base compartida, con nombres de tabla sacados de RoleTablePermission.
        # O sea la proteccion estaba invertida: nombrar el conector
        # "democratizacion_metadatos" no salvaba la base de la plataforma, la llevaba
        # a la rama que le borra tablas.
        #
        # Ahora es explicito: una base dedicada que creo la app se puede tirar; una
        # base de plataforma no se toca de ninguna manera.
        platform_dbs = {
            settings.POSTGRES_DB,
            # El nombre de la base de metadata es fijo, no sale de la config. El
            # `settings.METADATA_DB_PATH and "democratizacion_metadatos"` de antes
            # metia "" o None en el set cuando la ruta venia vacia, y con un
            # POSTGRES_DB distinto la base de la plataforma dejaba de protegerse,
            # con un DROP TABLE esperandola. Sin `and`, siempre protegida.
            "democratizacion_metadatos",
            "democratizacion_empresa",
            "postgres",
            "template0",
            "template1",
        }

        if conn.is_uploaded and (conn.db_type == DatabaseType.POSTGRESQL or str(conn.db_type).lower() == "postgresql"):
            is_platform_db = conn.database_name in platform_dbs
            if conn.database_name and not is_platform_db:
                try:
                    from sqlalchemy import create_engine, text
                    maint_url = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
                    m_engine = create_engine(maint_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
                    try:
                        with m_engine.connect() as m_conn:
                            m_conn.execute(text(f'DROP DATABASE IF EXISTS "{conn.database_name}" WITH (FORCE);'))
                    finally:
                        m_engine.dispose()
                except Exception as exc:
                    # Antes era `except: pass` y la respuesta decia "eliminada
                    # correctamente" igual. Borrar la fila del conector sin haber
                    # liberado la base deja una base huerfana sin forma de recuperarla.
                    logger.error(
                        "No se pudo eliminar la base %s del conector %s: %s",
                        conn.database_name, conn_id, exc,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"No se pudo eliminar la base '{conn.database_name}'. La conexión no se eliminó para no dejar datos huérfanos.",
                    ) from exc
            # Si es una base de plataforma se dejan las tablas: borrarlas seria
            # destructivo y el conector es solo una referencia administrative.

        db.query(SemanticCatalog).filter(SemanticCatalog.connection_id == conn_id).delete()
        db.query(RoleTablePermission).filter(RoleTablePermission.connection_id == conn_id).delete()

        # `conn.host` es una ruta libre que introduce el admin al registrar el
        # conector. Sin esta comprobacion, registrar un "conector SQLite" apuntando a
        # cualquier archivo del disco y borrarlo eliminaba ese archivo. Solo se borra
        # lo que vive dentro del directorio de data_sources, que es donde la app
        # sube los datasets.
        if conn.is_uploaded and conn.host and (conn.db_type == DatabaseType.SQLITE or str(conn.db_type).lower() == "sqlite"):
            try:
                if os.path.exists(conn.host):
                    target = os.path.realpath(conn.host)
                    allowed_root = os.path.realpath(settings.DATA_SOURCES_DIR)
                    if os.path.commonpath([target, allowed_root]) == allowed_root:
                        os.remove(target)
                    else:
                        logger.warning(
                            "No se borro %s: esta fuera de %s. Podria ser un archivo ajeno.",
                            target, allowed_root,
                        )
            except Exception as exc:
                logger.error("No se pudo borrar el archivo del conector %s: %s", conn_id, exc)

        db.delete(conn)
        db.commit()
        return {"message": f"Conexión '{conn.name}' eliminada correctamente.", "id": conn_id}

    @classmethod
    def set_role_table_permissions(
        cls,
        db: Session,
        connection_id: int,
        role_id: int,
        table_names: List[str],
        is_allowed: bool = True,
    ) -> List[RoleTablePermission]:
        """
        Concede o revoca acceso a tablas para un rol en una conexion. Es la unica
        via por la que un dataset obtiene acceso: el upload deja el dataset en
        default-deny y el admin decide aca, tabla por tabla.
        """
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexión no encontrada.")

        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")

        is_pg = (conn.db_type == DatabaseType.POSTGRESQL or str(conn.db_type).lower() == "postgresql")
        schema_name = "public" if is_pg else "main"

        touched = []
        for raw_name in table_names:
            tbl = (raw_name or "").strip()
            if not tbl:
                continue
            perm = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == role_id,
                RoleTablePermission.connection_id == connection_id,
                RoleTablePermission.table_name == tbl,
            ).first()
            if perm:
                perm.is_allowed = is_allowed
                # Toda fila que pasa por aqui es decision de un admin, no el
                # auto-grant: es lo que la migracion de default-deny distingue.
                perm.granted_by_admin = True
                perm.schema_name = perm.schema_name or schema_name
            else:
                perm = RoleTablePermission(
                    role_id=role_id,
                    connection_id=connection_id,
                    schema_name=schema_name,
                    table_name=tbl,
                    is_allowed=is_allowed,
                    granted_by_admin=True,
                )
                db.add(perm)
            touched.append(perm)

        db.commit()

        # El schema cacheado del DynamicSchemaPruningService dura 10 minutos: sin
        # esto el admin concede el permiso y el usuario sigue sin ver la tabla
        # hasta que expire la cache.
        try:
            from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
            DynamicSchemaPruningService.invalidate_schema_cache(connection_id)
        except Exception as exc:
            logger.warning("No se pudo invalidar el cache de esquema tras cambiar permisos: %s", exc)

        for perm in touched:
            db.refresh(perm)
        return touched

    @classmethod
    def list_role_table_permissions(cls, db: Session, connection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Matriz de permisos de tabla, para que el admin vea que concedio y que no."""
        q = db.query(RoleTablePermission)
        if connection_id is not None:
            q = q.filter(RoleTablePermission.connection_id == connection_id)
        rows = q.order_by(
            RoleTablePermission.connection_id,
            RoleTablePermission.role_id,
            RoleTablePermission.table_name,
        ).all()
        out = []
        for r in rows:
            role = db.query(Role).filter(Role.id == r.role_id).first()
            out.append({
                "id": r.id,
                "connection_id": r.connection_id,
                "role_id": r.role_id,
                "role_name": role.name if role else None,
                "schema_name": r.schema_name,
                "table_name": r.table_name,
                "is_allowed": bool(r.is_allowed),
                "granted_by_admin": bool(getattr(r, "granted_by_admin", False)),
            })
        return out

    @classmethod
    def test_connection_connectivity(cls, test_in: ConnectionTestRequest) -> ConnectionTestResult:
        if test_in.db_type == DatabaseType.SQLITE:
            path_to_check = test_in.host or test_in.database_name
            if os.path.exists(path_to_check):
                try:
                    with sqlite3.connect(path_to_check) as c:
                        c.execute("SELECT 1;").fetchone()
                    return ConnectionTestResult(
                        success=True,
                        message=f"Archivo SQLite accesible correctamente ({os.path.basename(path_to_check)}).",
                        latency_ms=1
                    )
                except Exception as e:
                    return ConnectionTestResult(
                        success=False,
                        message=f"Error al abrir archivo SQLite: {str(e)}",
                        latency_ms=0
                    )
            return ConnectionTestResult(
                success=False,
                message=f"Archivo SQLite no encontrado en la ruta: {path_to_check}",
                latency_ms=0
            )

        result = HealthService.check_db_connectivity(
            host=test_in.host,
            port=test_in.port,
            timeout=3.0,
            db_type=test_in.db_type.value.upper(),
            database_name=test_in.database_name
        )
        return ConnectionTestResult(
            success=result["success"],
            message=result["message"],
            latency_ms=result["latency_ms"]
        )
