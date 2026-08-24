import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import bcrypt
from cryptography.fernet import Fernet
from jose import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_fernet_key() -> bytes:
    """Generates a valid 32-byte url-safe base64 Fernet key derived from SECRET_KEY."""
    if settings.FERNET_KEY:
        return settings.FERNET_KEY.encode()
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)

fernet = Fernet(_get_fernet_key())

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against hashed password (bcrypt / Argon2)."""
    if not plain_password or not hashed_password:
        return False
    try:
        if hashed_password.startswith("$argon2"):
            try:
                import argon2
                ph = argon2.PasswordHasher()
                return ph.verify(hashed_password, plain_password)
            except Exception:
                pass

        pwd_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.warning(f"Password verification error: {type(e).__name__}")
        return False

def get_password_hash(password: str) -> str:
    """Hashes a raw password securely using direct bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

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
    except Exception as e:
        logger.warning(f"Credential decryption error: {type(e).__name__}")
        return ""

import uuid

def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None
) -> str:
    """Creates a JWT access token with unique JTI for user session tracking."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_jti = jti or str(uuid.uuid4())
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "jti": token_jti
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token_payload(token: str) -> Optional[dict]:
    """Decodes JWT access token and returns full payload dictionary."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception as e:
        logger.warning(f"Token decoding error: {type(e).__name__}")
        return None

def decode_access_token(token: str) -> Optional[str]:
    """Decodes JWT access token and returns user_id subject."""
    payload = decode_token_payload(token)
    return payload.get("sub") if payload else None
