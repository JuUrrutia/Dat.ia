from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_db() -> Generator:
    """Provides a database session for requests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Decodes JWT access token and retrieves current user from PostgreSQL."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de sesión.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo.")
        
    return user

from app.core.constants import ADMIN_ROLES

def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensures current user has Administrator privileges."""
    user_role_name = current_user.role.name if current_user.role else ""
    if not (current_user.is_admin or user_role_name in ADMIN_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requieren privilegios de Administrador."
        )
    return current_user
