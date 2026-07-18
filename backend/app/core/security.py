"""Core security utilities.

Provides JWT token creation/validation, password hashing, and authentication helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Hashed password string.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hash.

    Args:
        plain_password: Plain text password.
        hashed_password: Hashed password.

    Returns:
        True if passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The token subject (user ID).
        role: User role for claims.
        expires_delta: Custom expiration delta.

    Returns:
        Encoded JWT token string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    role: str = "user",
) -> str:
    """Create a JWT refresh token.

    Args:
        subject: The token subject (user ID).
        role: User role for claims.

    Returns:
        Encoded JWT refresh token string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Args:
        token: Encoded JWT token string.

    Returns:
        Decoded payload dict or None if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def create_token_pair(
    user_id: str,
    role: str = "user",
) -> dict:
    """Create both access and refresh token pair.

    Args:
        user_id: The user's ID.
        role: User role.

    Returns:
        Dict with access_token, refresh_token, and token_type.
    """
    access_token = create_access_token(subject=user_id, role=role)
    refresh_token = create_refresh_token(subject=user_id, role=role)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
