import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

MIN_PASSWORD_LENGTH = 6

def validate_password_strength(raw: str) -> str:
    """
    Única regla de contraseña de la aplicación.

    Vive acá y no en cada router porque /auth/register (público) aceptaba
    `password="a"` con 201 mientras /auth/change-password exigía 6 caracteres a
    cuatro líneas de distancia: quedaba una credencial de 1 carácter que
    después ni podía normalizarse.
    """
    cleaned = (raw or "").strip()
    if len(cleaned) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    return cleaned

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    jti: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserSelfRegister(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str

class UserCreateByAdmin(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    is_admin: bool = False
    role_id: Optional[int] = None

# Backward compatibility alias
UserCreate = UserCreateByAdmin

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserRoleUpdate(BaseModel):
    """
    Body de `PATCH /auth/users/{user_id}` (admin only).

    Los dos campos son opcionales para poder cambiar solo uno, y `None` significa
    "no lo toques". Por eso `{}` NO es un cambio: el router lo rechaza con 400 en vez
    de devolver 200 sin haber modificado nada. `role` es el NOMBRE del rol del
    catalogo (`/auth/roles`), no un id suelto: un string que no matchea ningun rol
    no debe poder guardarse.
    """
    role: Optional[str] = None
    is_admin: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool
    is_active: bool
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    must_change_password: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class PasswordResetResponse(BaseModel):
    message: str
    username: str
    temporary_password: str

class SessionOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    jti: str
    created_at: datetime.datetime
    last_seen_at: datetime.datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool

    model_config = ConfigDict(from_attributes=True)

Token.model_rebuild()
