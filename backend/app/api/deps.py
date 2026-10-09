import datetime
import logging
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
from app.modules.telemetry_audit.models import AuditLog
from app.core.constants import (
    SESSION_LAST_SEEN_UPDATE_INTERVAL_MINUTES,
    ADMIN_ROLES,
    ROLE_ADMINISTRADOR,
)

logger = logging.getLogger(__name__)

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

def _persist_audit_log(
    db: Session,
    user_id: Optional[int],
    username: str,
    user_role: Optional[str],
    question_prompt: str,
    sql_generated: Optional[str],
    # `None` = "esta consulta no tiene registro de validacion". NO es un valor
    # decorativo: el export de compliance lee esta columna de la BD y antes
    # confundia "no lo se" con "APROBADO", que es una afirmacion distinta.
    validation_status: Optional[str],
    target_database: str,
    execution_time_ms: int = 0,
    rows_returned: int = 0,
    error_message: Optional[str] = None,
    result_snapshot: Optional[str] = None
) -> Optional[int]:
    """Safely persists an AuditLog record in a best-effort transaction and returns its ID."""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            user_role=user_role,
            question_prompt=question_prompt,
            sql_generated=sql_generated,
            validation_status=validation_status,
            target_database=target_database,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            error_message=error_message,
            result_snapshot=result_snapshot
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry.id
    except Exception as e:
        db.rollback()
        logger.warning(f"Error registrando auditoria: {e}")
        return None

def display_role_name(user: User) -> Optional[str]:
    """Nombre del rol para MOSTRAR, o `None` si la cuenta no tiene ninguno.

    Antes cada router se resolvia el nombre por su cuenta con un fallback:

        role_name = user.role.name if user.role else (
            "Super Administrador" if user.is_admin else "Usuario"
        )

    Ninguno de esos tres nombres existe en el catalogo de 8 roles, asi que la
    etiqueta no describia nada: era texto libre que recien despues se comparaba
    contra nombres reales. Para lo visual no era grave; para auditoria si.

    `ROLE_ADMINISTRADOR` para el admin sin fila de rol NO es inventar un nombre:
    `is_admin` es un hecho persistido en la columna y esa persona administra en
    todas las capas de auth. Le corresponde el nombre real del catalogo. Es la
    misma decision que toma `require_assigned_role` de abajo.

    `None` para la cuenta sin rol y sin `is_admin`: el rol no se sabe, y el
    contrato lo admite (`UserOut.role_name` y `AuditLog.user_role` son ambos
    `Optional`). Un nombre inventado seria un hecho falso en la evidencia.

    Vive aca y no en `auth/router.py` porque lo necesitan al menos dos modulos
    (`auth` y `reports`) y ninguno de los dos es el piso comun: `deps` ya es el
    piso que comparten, ya tiene la otra mitad de esta misma regla
    (`require_assigned_role`) y no importa a `reports`, asi que no crea ciclo.
    """
    if user.role:
        return user.role.name
    if user.is_admin:
        return ROLE_ADMINISTRADOR
    return None


def require_assigned_role(
    user: User, db: Session, question: str, target_database: str
) -> str:
    """Nombre del rol de la cuenta, o 403 si no tiene ninguno asignado.

    El corte mira el REGISTRO (`user.role`), no el nombre resuelto. Antes cada
    endpoint resolvia el nombre con un fallback:

        role_name = user.role.name if user.role else ROLE_USUARIO

    Una cuenta con `role_id = NULL` y `is_admin = False` caia en "Usuario
    Consultor", que es truthy y es un rol REAL y VALIDO del catalogo. El guard
    resuelve por nombre cuando `role_id` es None (a proposito: asi funcionan sus
    tests y el self-healing), asi que la cuenta sin rol heredaba la matriz del
    Consultor. La cuenta sin rol y el Consultor son dos hechos distintos, y el que
    decide es si existe la fila.

    Vive aca y no en `chat_engine/router.py` porque lo necesitan endpoints de
    `admin_catalog` y `system`, que no importan a `chat_engine` en module scope
    (lo hacen con imports diferidos, justo para no crear el acoplamiento). Este
    modulo es el que YA comparte `get_current_admin` con esos routers, asi que no
    crea ninguna arista nueva: `deps` es el piso comun de dependencias.

    El admin sin fila de rol NO entra por aca: `is_admin` manda y recibe el
    nombre de administrador, que es lo que el resto del pipeline espera.

    El 403 va con su registro en auditoria: una denegacion que no deja rastro
    no es una denegacion. Mismo `RECHAZADO_RBAC` que el motor escribe cuando la
    peticion llega hasta el.
    """
    if user.role:
        return user.role.name
    if user.is_admin:
        return ROLE_ADMINISTRADOR

    _persist_audit_log(
        db=db,
        user_id=user.id,
        username=user.username,
        # `None` y no un nombre inventado: la columna es nullable justamente
        # para este caso. Poner "Usuario Consultor" seria afirmar un rol que la
        # cuenta no tiene, en el registro que el compliance lee.
        user_role=None,
        question_prompt=question,
        sql_generated=None,
        validation_status="RECHAZADO_RBAC",
        target_database=target_database,
        error_message="Cuenta sin rol asignado",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Tu cuenta todavia no tiene un rol asignado. Un Administrador debe "
            "asignarte un perfil corporativo para acceder a los datos."
        ),
    )
