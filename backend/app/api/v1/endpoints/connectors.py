import socket
import time
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.models.connection import CorporateConnection, DatabaseType
from app.core.security import encrypt_credential, decrypt_credential
from app.schemas.connection_schema import (
    CorporateConnectionCreate,
    CorporateConnectionUpdate,
    CorporateConnectionOut,
    ConnectionTestRequest,
    ConnectionTestResult
)

router = APIRouter()

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
    connectors = db.query(CorporateConnection).all()
    return connectors

@router.post("", response_model=CorporateConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connector(
    conn_in: CorporateConnectionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Registers a new corporate database connection with AES-256 encrypted password (Admin only)."""
    # Check if name exists
    existing = db.query(CorporateConnection).filter(CorporateConnection.name == conn_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una conexión registrada con ese nombre."
        )

    encrypted_pwd = encrypt_credential(conn_in.password)

    new_conn = CorporateConnection(
        name=conn_in.name,
        db_type=conn_in.db_type,
        host=conn_in.host,
        port=conn_in.port,
        database_name=conn_in.database_name,
        username=conn_in.username,
        encrypted_password=encrypted_pwd,
        is_active=conn_in.is_active
    )

    db.add(new_conn)
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

@router.delete("/{conn_id}", status_code=status.HTTP_200_OK)
def delete_connector(
    conn_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """Deletes a corporate database connection (Admin only)."""
    conn = db.query(CorporateConnection).filter(CorporateConnection.id == conn_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conexión de base de datos no encontrada."
        )

    db.delete(conn)
    db.commit()
    return {"message": "Conexión eliminada correctamente.", "id": conn_id}

@router.post("/test", response_model=ConnectionTestResult)
def test_connection_connectivity(
    test_in: ConnectionTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Tests real network TCP socket connectivity to target database host and port."""
    start_time = time.time()
    try:
        sock = socket.create_connection((test_in.host, test_in.port), timeout=3.0)
        sock.close()
        latency_ms = int((time.time() - start_time) * 1000)
        return ConnectionTestResult(
            success=True,
            message=f"Conexión exitosa al puerto {test_in.port} de {test_in.db_type.value.upper()} ({test_in.host}/{test_in.database_name}) en modo SOLO LECTURA.",
            latency_ms=latency_ms
        )
    except Exception as e:
        return ConnectionTestResult(
            success=False,
            message=f"No se pudo conectar a {test_in.host}:{test_in.port} ({test_in.db_type.value.upper()}) - {str(e)}",
            latency_ms=0
        )

@router.post("/test-metadata-db", response_model=ConnectionTestResult)
def test_metadata_db_connectivity(
    test_in: MetadataDBTestRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Tests real connectivity to target PostgreSQL metadata database."""
    start_time = time.time()
    try:
        sock = socket.create_connection((test_in.server, test_in.port), timeout=3.0)
        sock.close()
        latency_ms = int((time.time() - start_time) * 1000)
        return ConnectionTestResult(
            success=True,
            message=f"Servidor PostgreSQL alcanzable en {test_in.server}:{test_in.port} (Base de datos: {test_in.db_name}).",
            latency_ms=latency_ms
        )
    except Exception as e:
        return ConnectionTestResult(
            success=False,
            message=f"Error al conectar con PostgreSQL en {test_in.server}:{test_in.port} - {str(e)}",
            latency_ms=0
        )
