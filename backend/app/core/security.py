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
    """Verifies plain password against hashed password (bcrypt)."""
    if not plain_password or not hashed_password:
        return False
    try:
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


# Cuantos DIGITOS al final quedan visibles al enmascar una columna MASKED.
# Regla acordada: un RUT 12.345.678-9 se ve como *******678-9. Suficiente para que
# una persona compare dos registros a ojo, insuficiente para reconstruir el dato.
MASK_KEEP_LAST_DIGITS = 4


def mask_value(value, keep_last_digits: int = MASK_KEEP_LAST_DIGITS):
    """Enmascara un valor conservando los ultimos `keep_last_digits` DIGITOS.

    Se cuentan digitos, no caracteres: en "12.345.678-9" los ultimos 4 caracteres
    son "78-9" (pierde el 6), mientras que los ultimos 4 digitos son "678-9". La
    regla acordada es que el verificador y el cuerpo final queden visibles.
    Los separadores que quedan a la derecha del primer digito conservado se
    mantienen, para que el formato siga siendo reconocible.

    Se aplica DESPUES de ejecutar la consulta, en Python, y no reescribiendo el SQL:
    SQLite no tiene REGEXP y las funciones de cadena varian por dialecto, asi que
    hacerlo en SQL hacia el enmascaramiento dialecto-dependiente y capaz de romper la
    consulta. Aquí no hay dialecto y no se puede romper nada.

    La columna sigue existiendo en el SELECT (por eso MASKED no se agrega a
    blocked_columns): la consulta funciona, el dato no sale.
    """
    if value is None:
        return None
    text = str(value)
    if keep_last_digits <= 0:
        return "*" * len(text)

    digit_positions = [i for i, ch in enumerate(text) if ch.isdigit()]
    if len(digit_positions) < keep_last_digits:
        # Fail-closed. Si no hay digitos suficientes no se puede aplicar la regla
        # acordada, y conservar los ultimos caracteres equivaldria a revelar el
        # final del dato en una columna marcada como sensible. Se tapa entero.
        return "*" * len(text)

    cut = digit_positions[-keep_last_digits]
    return "*" * cut + text[cut:]


# Prefijos que Excel/Sheets/LibreOffice interpretan como inicio de formula.
# Un valor de texto de la base del cliente que empieza por '=' se convierte en una
# formula al abrir el archivo, y ahi se puede meter HYPERLINK, WEBSERVICE o una
# referencia a otro archivo. Se antepone un apostrofo, que es el escape estandar
# de estos formatos y no altera el texto que ve el usuario.
SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_spreadsheet_value(value):
    """Neutraliza inyeccion de formulas al exportar a Excel o CSV.

    Aplicarlo SIEMPRE a datos que vienen de la base del cliente, no solo a
    entrada de usuario: basta con que una columna de texto (nombre_cliente,
    observaciones, comentario) empiece por '=' para que se convierta en formula
    cuando un C-Level abre el .xlsx.
    """
    if isinstance(value, str) and value[:1] in SPREADSHEET_FORMULA_PREFIXES:
        return "'" + value
    return value


def mask_rows(rows, masked_columns) -> int:
    """Enmascara in-place las columnas MASKED de una lista de filas. Devuelve cuantas toco.

    `masked_columns` es un set de nombres de columna en minuscula, igual que
    `blocked_columns`. Se compara sin distinguir mayusculas porque el motor puede
    devolver las claves con el casing con el que estan escritas en la consulta.
    """
    if not masked_columns or not rows:
        return 0
    lowered = {c.lower() for c in masked_columns}
    touched = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in list(row.keys()):
            if key.lower() in lowered:
                row[key] = mask_value(row[key])
                touched += 1
    return touched
