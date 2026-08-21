import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

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

class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    is_admin: bool = False
    role_id: Optional[int] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

Token.model_rebuild()
