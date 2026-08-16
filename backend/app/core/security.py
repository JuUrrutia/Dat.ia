import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password hashing context (bcrypt + argon2)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def _get_fernet_key() -> bytes:
    """Generates a valid 32-byte url-safe base64 Fernet key derived from SECRET_KEY."""
    if settings.FERNET_KEY:
        return settings.FERNET_KEY.encode()
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)

fernet = Fernet(_get_fernet_key())

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a raw password securely using Argon2 / bcrypt."""
    return pwd_context.hash(password)

def encrypt_credential(plain_text: str) -> str:
    """Encrypts sensitive database connection passwords or tokens using AES-256 (Fernet)."""
    if not plain_text:
        return ""
    encrypted_bytes = fernet.encrypt(plain_text.encode())
    return encrypted_bytes.decode()

def decrypt_credential(encrypted_text: str) -> str:
    """Decrypts AES-256 Fernet encrypted credentials."""
    if not encrypted_text:
        return ""
    try:
        decrypted_bytes = fernet.decrypt(encrypted_text.encode())
        return decrypted_bytes.decode()
    except Exception:
        return ""

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token for local user sessions."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    """Decodes JWT access token and returns user_id subject."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None
