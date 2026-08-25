import os
import shutil
import sqlite3
import time
from typing import List, Optional, Any, Dict
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ADMIN_ROLES
from app.core.security import encrypt_credential
from app.modules.admin_catalog.models import CorporateConnection, DatabaseType, SemanticCatalog, RoleTablePermission
from app.modules.auth.models import Role
from app.modules.admin_catalog.schemas import (
    CorporateConnectionCreate, CorporateConnectionUpdate, CorporateConnectionOut,
    ConnectionTestRequest, ConnectionTestResult
)
from app.modules.admin_catalog.tabular_importer import convert_uploaded_file_to_sqlite
from app.modules.catalog.services.catalog_service import CatalogDomainService
from app.services.health_service import HealthService

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

        allowed_exts = [".sqlite", ".db", ".sqlite3", ".sql", ".csv", ".xlsx", ".xls", ".tsv", ".txt"]
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato no soportado. Debe ser un archivo SQLite, Excel, CSV o volcado SQL."
            )

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

        sqlite_db_name = f"{int(time.time())}_{os.path.splitext(clean_filename)[0]}.sqlite"
        target_path = os.path.join(ds_dir, sqlite_db_name)

        if ext in [".sqlite", ".db", ".sqlite3"]:
            target_path = os.path.join(ds_dir, f"{int(time.time())}_{clean_filename}")
            shutil.move(raw_target_path, target_path)

        detected_tables = []
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

        base_display_name = name.strip() if (name and name.strip()) else os.path.splitext(original_filename)[0]
        final_name = base_display_name
        counter = 1
        while db.query(CorporateConnection).filter(CorporateConnection.name == final_name).first():
            final_name = f"{base_display_name}_{counter}"
            counter += 1

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

        all_roles = db.query(Role).all()
        for role in all_roles:
            # Exclude unassigned/restricted base user roles
            is_unassigned = (
                role.name in ["Usuario", "Usuario Consultor"]
                or role.name.lower() == "usuario"
            )
            if is_unassigned:
                continue
            for tbl in detected_tables:
                existing_perm = db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == role.id,
                    RoleTablePermission.connection_id == new_conn.id,
                    RoleTablePermission.table_name == tbl
                ).first()
                if not existing_perm:
                    db.add(RoleTablePermission(
                        role_id=role.id,
                        connection_id=new_conn.id,
                        schema_name="main",
                        table_name=tbl,
                        is_allowed=True
                    ))

        db.commit()
        db.refresh(new_conn)

        # Automatically seed heuristic semantic descriptions & data dictionary definitions
        CatalogDomainService.seed_catalog_heuristics_for_connection(db, new_conn.id, target_path)

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
        return conn

    @classmethod
    def delete_connector(cls, db: Session, conn_id: int) -> Dict[str, Any]:
        conn = db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conexión de base de datos no encontrada."
            )

        db.query(SemanticCatalog).filter(SemanticCatalog.connection_id == conn_id).delete()
        db.query(RoleTablePermission).filter(RoleTablePermission.connection_id == conn_id).delete()

        if conn.is_uploaded and conn.host and os.path.exists(conn.host):
            try: os.remove(conn.host)
            except Exception: pass

        db.delete(conn)
        db.commit()
        return {"message": f"Conexión '{conn.name}' eliminada correctamente.", "id": conn_id}

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
