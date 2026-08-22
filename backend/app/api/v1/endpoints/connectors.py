import os
import shutil
import sqlite3
import time
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.health_service import HealthService
from app.services.tabular_importer import convert_uploaded_file_to_sqlite
from app.api.deps import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.models.connection import CorporateConnection, DatabaseType
from app.models.catalog import SemanticCatalog
from app.models.permission import RoleTablePermission
from app.models.role import Role
from app.core.config import settings
from app.core.security import encrypt_credential, decrypt_credential
from app.schemas.connection_schema import (
    CorporateConnectionCreate,
    CorporateConnectionUpdate,
    CorporateConnectionOut,
    ConnectionTestRequest,
    ConnectionTestResult
)

router = APIRouter()

def _ensure_data_sources_dir() -> str:
    """Creates and returns the permanent data_sources directory."""
    d = settings.DATA_SOURCES_DIR
    os.makedirs(d, exist_ok=True)
    return d

class MetadataDBTestRequest(BaseModel):
    server: str
    port: int
    db_name: str
    user: Optional[str] = None
    password: Optional[str] = None

@router.get("", response_model=List[CorporateConnectionOut])
def list_connectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Lists all registered corporate database connections."""
    connectors = db.query(CorporateConnection).order_by(CorporateConnection.created_at.desc()).all()
    return connectors

@router.post("", response_model=CorporateConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connector(
    conn_in: CorporateConnectionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Registers a new corporate database connection with AES-256 encrypted password (Admin only)."""
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
    return new_conn

@router.post("/upload", response_model=CorporateConnectionOut, status_code=status.HTTP_201_CREATED)
async def upload_database_file(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """
    Uploads a SQLite (.db, .sqlite), Excel (.xlsx, .xls), CSV (.csv) or SQL dump (.sql) file,
    converts it to a structured SQLite database in data_sources/, registers it with full RBAC permissions
    and initializes its semantic catalog (Admin only).
    """
    ds_dir = _ensure_data_sources_dir()
    original_filename = file.filename or "uploaded_database.sqlite"
    clean_filename = "".join(c for c in original_filename if c.isalnum() or c in (".", "_", "-"))
    ext = os.path.splitext(clean_filename)[1].lower()

    allowed_exts = [".sqlite", ".db", ".sqlite3", ".sql", ".csv", ".xlsx", ".xls", ".tsv", ".txt"]
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Debe ser un archivo SQLite (.sqlite, .db, .sqlite3), Excel (.xlsx, .xls), CSV (.csv) o volcado SQL (.sql)."
        )

    unique_raw_name = f"raw_{int(time.time())}_{clean_filename}"
    raw_target_path = os.path.join(ds_dir, unique_raw_name)

    # Save uploaded file
    try:
        with open(raw_target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo en el servidor: {str(e)}"
        )

    # Target SQLite database path
    sqlite_db_name = f"{int(time.time())}_{os.path.splitext(clean_filename)[0]}.sqlite"
    target_path = os.path.join(ds_dir, sqlite_db_name)

    if ext in [".sqlite", ".db", ".sqlite3"]:
        # Direct SQLite database
        target_path = os.path.join(ds_dir, f"{int(time.time())}_{clean_filename}")
        shutil.move(raw_target_path, target_path)

    # Convert or inspect tables
    detected_tables = []
    try:
        detected_tables = convert_uploaded_file_to_sqlite(
            source_path=target_path if ext in [".sqlite", ".db", ".sqlite3"] else raw_target_path,
            ext=ext,
            target_sqlite_path=target_path
        )
    except Exception as err:
        if os.path.exists(raw_target_path):
            try:
                os.remove(raw_target_path)
            except Exception:
                pass
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al procesar e importar archivo '{original_filename}': {str(err)}"
        )
    finally:
        # Clean up temporary raw file if different from target SQLite
        if raw_target_path != target_path and os.path.exists(raw_target_path):
            try:
                os.remove(raw_target_path)
            except Exception:
                pass

    # Determine unique connection display name
    base_display_name = name.strip() if (name and name.strip()) else os.path.splitext(original_filename)[0]
    final_name = base_display_name
    counter = 1
    while db.query(CorporateConnection).filter(CorporateConnection.name == final_name).first():
        final_name = f"{base_display_name}_{counter}"
        counter += 1

    # Create connection record
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

    # Auto-grant read permissions for all detected tables to active roles (Economista, TI)
    all_roles = db.query(Role).all()
    for role in all_roles:
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

    # Initialize basic catalog entries for detected tables and columns
    try:
        sqlite_conn = sqlite3.connect(target_path)
        cur = sqlite_conn.cursor()
        for tbl in detected_tables:
            cols = cur.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            for c in cols:
                c_name = c[1]
                c_type = c[2] or "TEXT"
                existing_cat = db.query(SemanticCatalog).filter(
                    SemanticCatalog.connection_id == new_conn.id,
                    SemanticCatalog.schema_name == "main",
                    SemanticCatalog.table_name == tbl,
                    SemanticCatalog.column_name == c_name
                ).first()
                if not existing_cat:
                    db.add(SemanticCatalog(
                        connection_id=new_conn.id,
                        schema_name="main",
                        table_name=tbl,
                        column_name=c_name,
                        friendly_name=c_name.replace("_", " ").title(),
                        description=f"Columna '{c_name}' ({c_type}) de la tabla '{tbl}'.",
                        business_formula="Columna directa",
                        is_ai_generated=True
                    ))
        cur.close()
        sqlite_conn.close()
    except Exception:
        pass

    db.commit()
    db.refresh(new_conn)
    return new_conn

@router.put("/{conn_id}", response_model=CorporateConnectionOut)
def update_connector(
    conn_id: int,
    conn_in: CorporateConnectionUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Updates an existing corporate database connection (Admin only)."""
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

@router.post("/{conn_id}/toggle-active", response_model=CorporateConnectionOut)
def toggle_connector_active(
    conn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Toggles active status of a corporate database connection (Admin only)."""
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

@router.delete("/{conn_id}", status_code=status.HTTP_200_OK)
def delete_connector(
    conn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """
    Deletes a corporate database connection, cascading the deletion of its semantic catalog entries,
    role permissions, and permanently removing the physical database file if it was uploaded (Admin only).
    """
    conn = db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conexión de base de datos no encontrada."
        )

    # Cascade delete semantic catalog entries
    db.query(SemanticCatalog).filter(SemanticCatalog.connection_id == conn_id).delete()

    # Cascade delete role table and column permissions
    db.query(RoleTablePermission).filter(RoleTablePermission.connection_id == conn_id).delete()

    # If physical uploaded file, delete safely from disk
    if conn.is_uploaded and conn.host and os.path.exists(conn.host):
        try:
            os.remove(conn.host)
        except Exception:
            pass

    db.delete(conn)
    db.commit()
    return {"message": f"Conexión '{conn.name}' y sus datos asociados eliminados correctamente.", "id": conn_id}

@router.post("/test", response_model=ConnectionTestResult)
def test_connection_connectivity(
    test_in: ConnectionTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Tests real network TCP socket or SQLite file connectivity."""
    if test_in.db_type == DatabaseType.SQLITE:
        path_to_check = test_in.host or test_in.database_name
        if os.path.exists(path_to_check):
            try:
                c = sqlite3.connect(path_to_check)
                c.execute("SELECT 1;").fetchone()
                c.close()
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

@router.post("/test-metadata-db", response_model=ConnectionTestResult)
def test_metadata_db_connectivity(
    test_in: MetadataDBTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Tests real connectivity to target PostgreSQL metadata database."""
    result = HealthService.check_db_connectivity(
        host=test_in.server,
        port=test_in.port,
        timeout=3.0,
        db_type="PostgreSQL",
        database_name=test_in.db_name
    )
    msg = (
        f"Servidor PostgreSQL alcanzable en {test_in.server}:{test_in.port} (Base de datos: {test_in.db_name})."
        if result["success"]
        else f"Error al conectar con PostgreSQL en {test_in.server}:{test_in.port} - {result['message']}"
    )
    return ConnectionTestResult(
        success=result["success"],
        message=msg,
        latency_ms=result["latency_ms"]
    )
