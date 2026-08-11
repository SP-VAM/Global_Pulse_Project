"""
Security Utilities: Password Hashing, JWT Token Generation & Validation.
Uses direct bcrypt for password hashing and PyJWT for token signatures.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import get_settings
from app.core.exceptions import GlobalPulseError

logger = logging.getLogger(__name__)

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash raw password using bcrypt."""
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against stored bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception as exc:
        logger.warning("Password verification failed: %s", exc)
        return False


def create_access_token(subject: str | int, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generate short-lived JWT Access Token."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expires,
    }
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | int, session_id: int) -> str:
    """Generate long-lived JWT Refresh Token."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    claims = {
        "sub": str(subject),
        "sid": session_id,
        "type": "refresh",
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT signature and expiration.
    Raises GlobalPulseError if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise GlobalPulseError("Authentication token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise GlobalPulseError("Invalid authentication token.") from exc
