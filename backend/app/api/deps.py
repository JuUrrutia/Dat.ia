import datetime
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import app.modules.auth.models
import app.modules.admin_catalog.models
import app.modules.telemetry_audit.models
import app.modules.chat_engine.models
from app.core.database import SessionLocal
from app.core.security import decode_token_payload
from app.modules.auth.models import User, UserSession
from app.core.constants import SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES, ADMIN_ROLES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_db() -> Generator:
    """Provides a database session for requests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _password_change_pending_allowed(request: Request) -> bool:
    """
    Rutas que siguen accesibles con `must_change_password=True`.

    Sin las dos primeras el usuario queda atrapado: no puede ni ver su propio flag
    (`/auth/me`) ni limpiarlo (`/auth/change-password`), porque ambas pasan por acá.
    """
    path = request.url.path.rstrip("/")
    return path.endswith("/auth/change-password") or path.endswith("/auth/me")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Decodes JWT access token, retrieves user, validates active session, and blocks
    the API while a temporary password is pending.
    """
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
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            last_seen = session.last_seen_at
            if isinstance(last_seen, str):
                try:
                    last_seen = datetime.datetime.fromisoformat(last_seen).replace(tzinfo=None)
                except Exception:
                    last_seen = now
            elif hasattr(last_seen, 'tzinfo') and last_seen.tzinfo is not None:
                last_seen = last_seen.replace(tzinfo=None)

            if last_seen and (now - last_seen).total_seconds() > (SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES * 60):
                session.last_seen_at = now
                try:
                    db.commit()
                except Exception:
                    db.rollback()

    # Una credencial temporal que el usuario puede ignorar para siempre no es una
    # credencial: `admin_reset_user_password` ponía el flag en True y
    # `change_user_password` lo limpiaba, pero nada impedía usar el token con la
    # contraseña temporal indefinidamente. Va acá, y no en cada router, porque esta
    # es la ÚNICA dependencia por la que pasan todos los endpoints autenticados:
    # `get_current_admin` cuelga de acá y cubre los endpoints de administración.
    if user.must_change_password and not _password_change_pending_allowed(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Debes cambiar tu contraseña temporal antes de continuar. "
                "Usa POST /api/v1/auth/change-password."
            )
        )

    return user

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
            # `utcnow()` esta deprecado desde 3.12. Mismo patron que el de arriba:
            # UTC naive. `last_seen_at` se compara y se escribe, no se usa para
            # validar el token (eso es `decode_token_payload`, en core/security.py,
            # que ya usa `datetime.now(timezone.utc)`), asi que el valor es
            # bit-identico al de antes: ningun token emitido antes queda invalido.
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
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
