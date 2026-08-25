from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

from app.core.config import get_settings

_settings = get_settings()

def get_secret_key() -> str:
    return _settings.JWT_SECRET_KEY or os.getenv("SECRET_KEY", "super-secret-key-change-in-production-min-32-chars")

def get_algorithm() -> str:
    return _settings.JWT_ALGORITHM or os.getenv("ALGORITHM", "HS256")

import bcrypt

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ------------------------------------
# Password Hashing
# ------------------------------------

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


# ------------------------------------
# Password Verification
# ------------------------------------

def verify_password(password: str, hashed_password: str) -> bool:
    if not password or not hashed_password:
        return False
    try:
        pwd_bytes = password.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        try:
            return password_context.verify(password, hashed_password)
        except Exception:
            return False


# ------------------------------------
# JWT Token
# ------------------------------------

def create_access_token(
    data: dict | str | int | None = None,
    expires_minutes: int = 60,
    subject: str | int | None = None,
    extra_claims: dict | None = None,
) -> str:
    payload: dict = {}
    if isinstance(data, dict):
        payload = data.copy()
    elif data is not None:
        payload["sub"] = str(data)
        if isinstance(data, int) or (isinstance(data, str) and data.isdigit()):
            try:
                payload["user_id"] = int(data)
            except ValueError:
                pass

    if subject is not None:
        payload["sub"] = str(subject)

    if extra_claims and isinstance(extra_claims, dict):
        payload.update(extra_claims)

    if "user_id" in payload and "sub" not in payload:
        payload["sub"] = str(payload["user_id"])
    elif "sub" in payload and "user_id" not in payload:
        try:
            payload["user_id"] = int(payload["sub"])
        except (ValueError, TypeError):
            pass

    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload["exp"] = expire

    token = jwt.encode(
        payload,
        get_secret_key(),
        algorithm=get_algorithm()
    )
    return token


# ------------------------------------
# Firebase Security Dependency
# ------------------------------------

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.firebase_config import verify_firebase_token





# Security dependency for extracting and verifying Firebase Bearer Token from HTTP Authorization Header
security = HTTPBearer(auto_error=False)

def get_current_firebase_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    FastAPI Security Dependency that extracts and verifies Firebase Bearer Token from HTTP Authorization Header.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        decoded_token = verify_firebase_token(credentials.credentials)
        return decoded_token
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"},
        )
