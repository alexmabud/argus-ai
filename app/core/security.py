"""Security utilities for password hashing and JWT token generation.

Provides functions for bcrypt password hashing, verification, and JWT token
creation/validation for authentication and authorization flows.
"""

from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Hash a password using bcrypt.

    Args:
        senha: Plain text password to hash.

    Returns:
        Hashed password string suitable for storage in database.
    """

    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    """Verify a plain text password against a bcrypt hash.

    Args:
        senha: Plain text password to verify.
        hash: Bcrypt hash from database.

    Returns:
        True if password matches hash, False otherwise.
    """

    return pwd_context.verify(senha, hash)


def criar_access_token(data: dict) -> str:
    """Create a JWT access token.

    Generates a JWT access token with the provided data and configured
    expiration (default 8 hours). Used for API authentication.

    Args:
        data: Dictionary of claims to encode (e.g., {"sub": user_id, "guarnicao_id": 1}).

    Returns:
        Encoded JWT access token string.
    """

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_refresh_token(data: dict) -> str:
    """Create a JWT refresh token.

    Generates a JWT refresh token with the provided data and configured
    expiration (default 30 days). Used to obtain new access tokens.

    Args:
        data: Dictionary of claims to encode (e.g., {"sub": user_id, "guarnicao_id": 1}).

    Returns:
        Encoded JWT refresh token string.
    """

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str, expected_type: str = "access") -> dict | None:
    """Decode and validate a JWT token.

    Decodes a JWT token and validates its signature and token type.
    Returns None if token is invalid, expired, or of wrong type.

    Args:
        token: JWT token string to decode.
        expected_type: Expected token type ("access" or "refresh").

    Returns:
        Decoded payload dictionary if valid, None otherwise.
    """

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
