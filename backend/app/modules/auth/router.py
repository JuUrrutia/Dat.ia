import datetime
import math
import secrets
import uuid
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_admin
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token_payload
from app.modules.auth.models import User, Role, UserSession
from app.core.constants import (
    MAX_FAILED_LOGIN_ATTEMPTS, ACCOUNT_LOCKOUT_DURATION_MINUTES, ADMIN_ROLES
)
from app.modules.auth.schemas import (
    UserLogin, UserSelfRegister, UserOut, Token, PasswordChangeRequest,
    PasswordResetResponse, SessionOut, UserRoleUpdate, validate_password_strength
)

def _require_strong_password(raw: str) -> str:
    """Aplica la regla única de schemas.validate_password_strength como HTTP 400."""
    try:
        return validate_password_strength(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

def _has_admin_rights(user: User) -> bool:
    """
    "¿Este usuario administra?" con la MISMA regla que `get_current_admin`:
    el flag `is_admin` o el rol del catalogo que este en ADMIN_ROLES.

    No se puede usar solo `is_admin`: un usuario con rol "Administrador" pero
    `is_admin=False` entra igual a /auth/users, asi que contarlo como no-admin
    dejaria pasar el guard de "ultimo administrador" y el sistema se quedaria
    sin nadie que pueda administrarlo.
    """
    return bool(user.is_admin) or (user.role is not None and user.role.name in ADMIN_ROLES)

def _jti_from_request(request: Request) -> Optional[str]:
    """
    JTI de la sesión con la que se está haciendo el request.

    `get_current_user` solo devuelve el User, y revocar "todas menos la actual"
    necesita saber cuál es la actual para no expulsar al propio usuario de su
    sesión recién autenticada.
    """
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    payload = decode_token_payload(header.split(" ", 1)[1].strip())
    return payload.get("jti") if payload else None

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserSelfRegister,
    db: Session = Depends(get_db)
) -> Any:
    """
    Registers a new user into the system.
    By default, new users receive the 'Usuario' role pending administrator assignment.
    """
    existing_username = db.query(User).filter(User.username == user_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado."
        )

    if user_in.email:
        existing_email = db.query(User).filter(User.email == user_in.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado."
            )

    default_role = db.query(Role).filter(Role.name == "Usuario").first()
    assigned_role_id = default_role.id if default_role else None
    role_name = default_role.name if default_role else "Usuario"

    hashed_pwd = get_password_hash(_require_strong_password(user_in.password))

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pwd,
        is_admin=False,
        is_active=True,
        role_id=assigned_role_id,
        failed_login_attempts=0,
        must_change_password=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    user_out = UserOut.model_validate(new_user)
    user_out.role_name = role_name
    return user_out

@router.post("/login", response_model=Token)
def login_user(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Authenticates user, checks account lockout policy,
    tracks failed attempts, and creates an active UserSession.
    """
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos."
        )

    now = datetime.datetime.utcnow()

    # 1. Check lockout expiration or active lockout
    if user.locked_until:
        if user.locked_until > now:
            remaining_minutes = max(1, math.ceil((user.locked_until - now).total_seconds() / 60))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cuenta bloqueada temporalmente por {MAX_FAILED_LOGIN_ATTEMPTS} intentos fallidos. Intenta nuevamente en {remaining_minutes} minuto(s) o solicita a un Administrador que restablezca tu acceso."
            )
        else:
            # Lockout expired, reset counters
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

    # 2. Check credentials
    if not verify_password(login_data.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + datetime.timedelta(minutes=ACCOUNT_LOCKOUT_DURATION_MINUTES)
            user.failed_login_attempts = 0
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Has superado el límite de {MAX_FAILED_LOGIN_ATTEMPTS} intentos fallidos. Tu cuenta ha sido bloqueada por {ACCOUNT_LOCKOUT_DURATION_MINUTES} minutos."
            )
        db.commit()
        remaining_attempts = MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Usuario o contraseña incorrectos. Te quedan {remaining_attempts} intento(s) antes del bloqueo."
        )

    # 3. Account active check
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta de usuario está desactivada."
        )

    # Reset failure counter upon successful authentication
    user.failed_login_attempts = 0
    user.locked_until = None

    # 4. Generate JWT with unique JTI and persist active session
    session_jti = str(uuid.uuid4())
    access_token = create_access_token(subject=user.id, jti=session_jti)

    # Extract client IP and user-agent
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Desktop Client")

    user_session = UserSession(
        user_id=user.id,
        jti=session_jti,
        created_at=now,
        last_seen_at=now,
        ip_address=client_ip[:50] if client_ip else "127.0.0.1",
        user_agent=user_agent[:255] if user_agent else "Desktop Client",
        is_revoked=False
    )
    db.add(user_session)
    db.commit()

    role_name = user.role.name if user.role else ("Super Administrador" if user.is_admin else "Usuario")
    user_out = UserOut.model_validate(user)
    user_out.role_name = role_name

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_out
    }

@router.get("/me", response_model=UserOut)
def read_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Returns profile of currently authenticated user."""
    role_name = current_user.role.name if current_user.role else ("Super Administrador" if current_user.is_admin else "Usuario")
    user_out = UserOut.model_validate(current_user)
    user_out.role_name = role_name
    return user_out

@router.post("/change-password")
def change_user_password(
    pwd_in: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Allows authenticated user to change password and clears must_change_password flag."""
    if not verify_password(pwd_in.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual ingresada es incorrecta."
        )

    new_password = _require_strong_password(pwd_in.new_password)

    current_user.hashed_password = get_password_hash(new_password)
    current_user.must_change_password = False
    current_user.failed_login_attempts = 0
    current_user.locked_until = None

    # Revoca el resto de las sesiones del usuario, igual que hace el reset de
    # admin. Sin esto, un token robado seguia valiendo hasta expirar: el usuario
    # detectaba el robo, cambiaba la contraseña y la credencial expuesta
    # sobrevivia al cambio. Se conserva la sesión con la que se está haciendo el
    # cambio para que el cliente no quede desconectado.
    current_jti = _jti_from_request(request)
    revoke_filter = [
        UserSession.user_id == current_user.id,
        UserSession.is_revoked == False,
    ]
    if current_jti:
        revoke_filter.append(UserSession.jti != current_jti)
    revoked = db.query(UserSession).filter(*revoke_filter).update({"is_revoked": True})

    db.commit()

    return {"message": "Contraseña actualizada exitosamente.", "revoked_sessions": revoked}

# =========================================================================
# ADMIN GOVERNANCE ENDPOINTS: SESSIONS & PASSWORD RESETS
# =========================================================================

@router.get("/roles")
def list_available_roles(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """Lists available roles for administration management (Admin only)."""
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]

@router.get("/users", response_model=List[UserOut])
def list_all_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """Lists registered users from metadata database for admin governance (Admin only)."""
    users = db.query(User).all()
    out = []
    for u in users:
        role_name = u.role.name if u.role else ("Administrador" if u.is_admin else "Usuario")
        u_out = UserOut.model_validate(u)
        u_out.role_name = role_name
        out.append(u_out)
    return out

@router.get("/sessions", response_model=List[SessionOut])
def list_user_sessions(
    user_id: Optional[int] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """Lists active user sessions (Admin only)."""
    query = db.query(UserSession).filter(UserSession.is_revoked == False)
    if user_id:
        query = query.filter(UserSession.user_id == user_id)
    
    sessions = query.order_by(UserSession.last_seen_at.desc()).all()
    result = []
    for s in sessions:
        s_out = SessionOut(
            id=s.id,
            user_id=s.user_id,
            username=s.user.username if s.user else "Desconocido",
            jti=s.jti,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            is_revoked=s.is_revoked
        )
        result.append(s_out)
    return result

@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """Revokes an active session immediately (Admin only)."""
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada."
        )
    
    session.is_revoked = True
    db.commit()
    return {"message": "Sesión revocada exitosamente."}

@router.patch("/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: UserRoleUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Any:
    """
    Actualiza rol y/o `is_admin` de un usuario (Admin only).

    Devuelve el `UserOut` ya releido de la base: la UI confirma contra esta
    respuesta, no contra un estado local.

    Decisión de diseño — revoca las sesiones del usuario afectado: SÍ, y solo
    cuando el cambio le QUITA permisos de administrador. El motivo es el mismo
    que en `admin_reset_user_password`: el token es un JWT de 24h que no lleva
    el rol adentro, así que un token emitido con `is_admin=True` sigue valiendo
    hasta expirar aunque al usuario ya se le haya quitado. Bajar privilegios
    tiene que cortar las sesiones abiertas, no esperar al vencimiento.

    En los demas casos NO se revoca. Subir privilegios no deja nada peligroso
    vivo (el token viejo no podia mas de lo que ya podia), y cambiar el rol sin
    tocar `is_admin` ya surte efecto en la siguiente llamada porque
    `get_current_admin` relee el rol de la base en cada request. Revocar ahi
    botaria a usuarios a los que no se les cambio el acceso.
    """
    if payload.role is None and payload.is_admin is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indica al menos un campo a actualizar: 'role' y/o 'is_admin'.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    new_role = None
    if payload.role is not None:
        role_name = payload.role.strip()
        if not role_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol no puede ser una cadena vacía."
            )
        new_role = db.query(Role).filter(Role.name == role_name).first()
        if not new_role:
            available = [r.name for r in db.query(Role).order_by(Role.name).all()]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El rol '{role_name}' no existe en el catálogo. Roles disponibles: {', '.join(available)}."
            )

    # --- Salvaguardas de administración -----------------------------------
    # Se calculan sobre el estado RESULTANTE (rol nuevo + is_admin nuevo), no
    # solo sobre `is_admin`: un admin con rol de catálogo también administra.
    had_admin_rights = _has_admin_rights(user)

    keeps_admin_rights = bool(payload.is_admin) if payload.is_admin is not None else user.is_admin
    if new_role is not None:
        keeps_admin_rights = keeps_admin_rights or new_role.name in ADMIN_ROLES

    losing_admin_rights = had_admin_rights and not keeps_admin_rights

    if losing_admin_rights and user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes quitarte a ti mismo los permisos de administrador. Pídele el cambio a otro administrador."
        )

    if losing_admin_rights:
        remaining_admins = [
            u for u in db.query(User).filter(User.id != user.id).all()
            if u.is_active and _has_admin_rights(u)
        ]
        if not remaining_admins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede quitar los permisos de administrador al último administrador del sistema."
            )

    # --- Aplicación --------------------------------------------------------
    if new_role is not None:
        user.role_id = new_role.id
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin

    if losing_admin_rights:
        db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.is_revoked == False
        ).update({"is_revoked": True})

    db.commit()
    db.refresh(user)

    role_name = user.role.name if user.role else ("Super Administrador" if user.is_admin else "Usuario")
    user_out = UserOut.model_validate(user)
    user_out.role_name = role_name
    return user_out

@router.post("/users/{user_id}/revoke-all-sessions")
def revoke_all_user_sessions(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """Revokes all active sessions for a target user (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    count = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()

    return {"message": f"Se revocaron {count} sesión(es) activa(s) del usuario {user.username}."}

@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
def admin_reset_user_password(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Generates a secure temporary password, sets must_change_password=True,
    clears lockout state, and revokes all active sessions (Admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    temp_password = f"Datia-{secrets.token_urlsafe(6)}"
    user.hashed_password = get_password_hash(temp_password)
    user.must_change_password = True
    user.failed_login_attempts = 0
    user.locked_until = None

    # Revoke active sessions for target user
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False
    ).update({"is_revoked": True})

    db.commit()

    return PasswordResetResponse(
        message=f"Contraseña de '{user.username}' restablecida exitosamente. Comunica esta contraseña temporal al usuario.",
        username=user.username,
        temporary_password=temp_password
    )
