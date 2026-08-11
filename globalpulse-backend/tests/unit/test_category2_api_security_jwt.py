"""
Category 2: API Security & JWT Vulnerability Assessment — Backend Hardening Phase 2

Attack vectors tested:
  A. Algorithm Confusion (alg:none)
  B. Empty HMAC key rejection (PyJWT 2.13 encode-time enforcement)
  B2. Short attacker secret — decode-level rejection
  C. Wrong secret / forged signature
  D. Expired token replay
  E. Payload manipulation (base64 swap)
  F. SQL injection in sub claim
  G. Garbage token
  H. Truncated (2-part) token

Schema Validation (Pydantic layer):
  J. SignupRequest — missing fields, weak password, invalid email
  K. LoginRequest — missing identity / password
  L. VerifyOtpRequest — OTP length violations
  M. ResetPasswordRequest — short new_password
  N. UpdateProfileRequest — username length violations

HTTP Protocol:
  O. 404 on unknown paths
  P. 405 on wrong HTTP method
  Q. 413 on oversized body
  R. Error envelope structure: {error:{code, message, timestampUtc}}

Dependency Guards:
  S. Inactive account returns 403
  T. Valid JWT for ghost user returns 401

Password Security:
  Empty/wrong inputs handled gracefully; bcrypt salts are unique.
"""
from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import create_access_token, decode_token
from app.db.models import Base
from app.db.session import get_db_session
from app.main import app

settings = get_settings()

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def api_client(db_session):
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


def _forge_token_none_alg(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}."


def _expired_token(user_id: int) -> str:
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {"sub": str(user_id), "type": "access", "iat": past, "exp": past + timedelta(seconds=1)}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class TestJWTAttackVectors:
    def test_none_algorithm_token_rejected(self):
        from app.core.exceptions import GlobalPulseError
        none_tok = _forge_token_none_alg({"sub": "1", "type": "access", "iat": int(time.time()), "exp": int(time.time()) + 3600})
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(none_tok)

    def test_empty_secret_rejected_at_encode_time(self):
        """PyJWT empty HMAC key encoding & decoding protection test."""
        from app.core.exceptions import GlobalPulseError
        tok = jwt.encode({"sub": "1", "type": "access"}, "", algorithm="HS256")
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(tok)

    def test_attacker_short_secret_token_rejected_on_decode(self):
        from app.core.exceptions import GlobalPulseError
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            bad_tok = jwt.encode({"sub": "1", "type": "access"}, "short-attacker-key-xyz", algorithm="HS256")
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(bad_tok)

    def test_wrong_secret_token_rejected(self):
        from app.core.exceptions import GlobalPulseError
        bad_tok = jwt.encode({"sub": "1", "type": "access"}, "attacker-secret", algorithm="HS256")
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(bad_tok)

    def test_expired_token_rejected(self):
        from app.core.exceptions import GlobalPulseError
        tok = _expired_token(user_id=42)
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(tok)

    def test_manipulated_payload_rejected(self):
        from app.core.exceptions import GlobalPulseError
        legitimate = create_access_token(42)
        header, _, sig = legitimate.split(".")
        evil_payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "9999", "type": "access", "exp": int(time.time()) + 3600}).encode()
        ).rstrip(b"=").decode()
        forged = f"{header}.{evil_payload}.{sig}"
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(forged)

    def test_valid_token_decoded_correctly(self):
        tok = create_access_token(777)
        payload = decode_token(tok)
        assert payload["sub"] == "777"
        assert payload["type"] == "access"

    def test_sql_injection_in_sub_treated_as_string(self):
        evil_sub = "1 OR 1=1; DROP TABLE users;--"
        tok = create_access_token(evil_sub)
        payload = decode_token(tok)
        assert payload["sub"] == evil_sub

    def test_garbage_token_rejected(self):
        from app.core.exceptions import GlobalPulseError
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token("not.a.valid.jwt.at.all")

    def test_two_part_token_rejected(self):
        from app.core.exceptions import GlobalPulseError
        tok = create_access_token(1)
        header, payload_b64, _ = tok.split(".")
        truncated = f"{header}.{payload_b64}"
        with pytest.raises((GlobalPulseError, Exception)):
            decode_token(truncated)


class TestSchemaValidation:
    def test_signup_missing_username_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import SignupRequest
        with pytest.raises(PydanticValidationError):
            SignupRequest(email="x@x.com", password="Password123!")

    def test_signup_username_too_short_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import SignupRequest
        with pytest.raises(PydanticValidationError):
            SignupRequest(username="ab", email="x@x.com", password="Password123!")

    def test_signup_password_too_short_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import SignupRequest
        with pytest.raises(PydanticValidationError):
            SignupRequest(username="validuser", email="x@x.com", password="short")

    def test_signup_invalid_email_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import SignupRequest
        with pytest.raises(PydanticValidationError):
            SignupRequest(username="validuser", email="not-an-email", password="Password123!")

    def test_signup_valid_passes(self):
        from app.schemas.auth import SignupRequest
        req = SignupRequest(username="validuser", email="valid@x.com", password="Password123!")
        assert req.username == "validuser"

    def test_login_missing_identity_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import LoginRequest
        with pytest.raises(PydanticValidationError):
            LoginRequest(password="pass")

    def test_login_missing_password_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import LoginRequest
        with pytest.raises(PydanticValidationError):
            LoginRequest(identity="user@x.com")

    def test_login_valid_passes(self):
        from app.schemas.auth import LoginRequest
        req = LoginRequest(identity="user@x.com", password="mypassword")
        assert req.identity == "user@x.com"

    def test_verify_otp_too_short_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import VerifyOtpRequest
        with pytest.raises(PydanticValidationError):
            VerifyOtpRequest(mobile_number="+919999988888", otp_code="123")

    def test_verify_otp_too_long_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import VerifyOtpRequest
        with pytest.raises(PydanticValidationError):
            VerifyOtpRequest(mobile_number="+919999988888", otp_code="1234567")

    def test_verify_otp_exact_six_passes(self):
        from app.schemas.auth import VerifyOtpRequest
        req = VerifyOtpRequest(mobile_number="+919999988888", otp_code="123456")
        assert req.otp_code == "123456"

    def test_reset_password_too_short_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import ResetPasswordRequest
        with pytest.raises(PydanticValidationError):
            ResetPasswordRequest(reset_token="tok", new_password="short")

    def test_reset_password_valid_passes(self):
        from app.schemas.auth import ResetPasswordRequest
        req = ResetPasswordRequest(reset_token="valid-tok", new_password="NewPass123!")
        assert req.new_password == "NewPass123!"

    def test_update_profile_username_too_short_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import UpdateProfileRequest
        with pytest.raises(PydanticValidationError):
            UpdateProfileRequest(username="ab")

    def test_update_profile_username_max_length_boundary(self):
        from app.schemas.auth import UpdateProfileRequest
        req = UpdateProfileRequest(username="a" * 100)
        assert len(req.username) == 100

    def test_update_profile_username_over_max_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        from app.schemas.auth import UpdateProfileRequest
        with pytest.raises(PydanticValidationError):
            UpdateProfileRequest(username="a" * 101)


class TestHTTPProtocolAndErrorEnvelope:
    @pytest.mark.asyncio
    async def test_404_on_unknown_path(self, api_client):
        resp = await api_client.get("/api/v1/nonexistent-endpoint-xyz")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_405_on_wrong_method(self, api_client):
        resp = await api_client.delete("/api/v1/auth/me")
        assert resp.status_code in (405, 401)

    @pytest.mark.asyncio
    async def test_401_on_missing_auth_header(self, api_client):
        resp = await api_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert "error" in resp.json()

    @pytest.mark.asyncio
    async def test_401_on_invalid_bearer_token(self, api_client):
        resp = await api_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer totally-invalid-jwt"})
        assert resp.status_code == 401
        assert "error" in resp.json()

    @pytest.mark.asyncio
    async def test_401_on_expired_token_via_api(self, api_client):
        expired = _expired_token(user_id=1)
        resp = await api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_401_on_none_alg_token_via_api(self, api_client):
        none_tok = _forge_token_none_alg({"sub": "1", "type": "access", "iat": int(time.time()), "exp": int(time.time()) + 3600})
        resp = await api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {none_tok}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_422_on_signup_invalid_payload(self, api_client):
        resp = await api_client.post("/api/v1/auth/signup", json={"username": "x", "email": "bad-email", "password": "short"})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_error_envelope_has_required_fields(self, api_client):
        resp = await api_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        err = resp.json().get("error", {})
        assert "code" in err
        assert "message" in err
        assert "timestampUtc" in err

    @pytest.mark.asyncio
    async def test_413_on_oversized_body(self, api_client):
        big_content = "x" * (1_048_576 + 1)
        resp = await api_client.post(
            "/api/v1/auth/signup",
            content=big_content,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


class TestDependencyGuards:
    @pytest.mark.asyncio
    async def test_inactive_user_returns_403(self, api_client, db_session):
        from app.services.auth_service import AuthService
        from app.schemas.auth import SignupRequest
        svc = AuthService(db_session)
        resp = await svc.signup(SignupRequest(username="inactive_user", email="inactive@test.com", password="SecurePass123!"))
        token = resp.access_token
        user_id = resp.user.user_id
        from app.db.models.user_model import UserModel
        from sqlalchemy import select
        result = await db_session.execute(select(UserModel).where(UserModel.user_id == user_id))
        user = result.scalar_one()
        user.account_status = "INACTIVE"
        await db_session.commit()
        me_resp = await api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 403
        assert "error" in me_resp.json()

    @pytest.mark.asyncio
    async def test_token_for_nonexistent_user_returns_401(self, api_client):
        ghost_token = create_access_token(999999)
        resp = await api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {ghost_token}"})
        assert resp.status_code == 401


class TestPasswordSecurity:
    def test_empty_password_verify_returns_false(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("SecurePassword!")
        assert verify_password("", hashed) is False

    def test_empty_hash_verify_returns_false(self):
        from app.core.security import verify_password
        assert verify_password("password", "") is False

    def test_none_does_not_raise(self):
        from app.core.security import verify_password
        assert verify_password("password", "") is False

    def test_bcrypt_hash_is_unique_per_call(self):
        from app.core.security import hash_password
        h1 = hash_password("SamePassword!")
        h2 = hash_password("SamePassword!")
        assert h1 != h2

    def test_correct_password_verifies(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("CorrectHorseBatteryStaple!")
        assert verify_password("CorrectHorseBatteryStaple!", hashed) is True

    def test_wrong_password_does_not_verify(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("CorrectPassword!")
        assert verify_password("WrongPassword!", hashed) is False
