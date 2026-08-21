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

import datetime
from app.core.security import decode_token_payload
from app.models.session import UserSession
from app.core.constants import SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Decodes JWT access token, retrieves user, and validates active session."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de sesión.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token_payload(token)
    if not payload:
        raise credentials_exception
        
    user_id = payload.get("sub")
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

    # Validate active session via JTI if claim is present
    jti = payload.get("jti")
    if jti:
        session = db.query(UserSession).filter(UserSession.jti == jti).first()
        if session:
            if session.is_revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="La sesión ha sido revocada o cerrada. Inicia sesión nuevamente.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Throttled update of last_seen_at
            now = datetime.datetime.utcnow()
            if (now - session.last_seen_at).total_seconds() > (SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES * 60):
                session.last_seen_at = now
                try:
                    db.commit()
                except Exception:
                    db.rollback()

    return user

from app.core.constants import ADMIN_ROLES

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user_optional(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    """
    Safely retrieves authenticated user if a valid JWT token is provided.
    Returns None if token is absent, invalid, expired or revoked, without raising HTTP 401.
    """
    if not token:
        return None

    payload = decode_token_payload(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None

    if user is None or not user.is_active:
        return None

    jti = payload.get("jti")
    if jti:
        session = db.query(UserSession).filter(UserSession.jti == jti).first()
        if session:
            if session.is_revoked:
                return None
            now = datetime.datetime.utcnow()
            if (now - session.last_seen_at).total_seconds() > (SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES * 60):
                session.last_seen_at = now
                try:
                    db.commit()
                except Exception:
                    db.rollback()

    return user

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
