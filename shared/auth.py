"""Authentication and Token Management for Custodian AI.

Implements password hashing with direct bcrypt and signed JWT token creation/validation
for mock login and role-based access control.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import bcrypt
import jwt

from shared.config import get_settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    # Truncate to 72 bytes per bcrypt standard specification
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta_minutes: Optional[int] = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    expire_minutes = expires_delta_minutes or settings.access_token_expire_minutes
    expire_timestamp = time.time() + (expire_minutes * 60)
    to_encode.update({"exp": expire_timestamp, "iat": time.time()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise ValueError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise ValueError("Invalid authentication token") from e
