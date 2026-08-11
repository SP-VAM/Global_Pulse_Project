"""
Unit and integration tests for Authentication & Authorization Module.
Tests JWT token creation, password hashing, user registration, OTP generation/verification, and FastAPI auth endpoints.
"""
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.models import Base
from app.db.session import get_db_session
from app.main import app
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, SendOtpRequest, SignupRequest, VerifyOtpRequest

# Isolated test DB setup
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_auth_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


def test_password_hashing():
    """Verify bcrypt password hashing and verification."""
    password = "SecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_lifecycle():
    """Verify JWT access and refresh token encoding/decoding."""
    user_id = 42
    token = create_access_token(user_id, {"username": "testuser"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert payload["username"] == "testuser"

    refresh = create_refresh_token(user_id, session_id=101)
    ref_payload = decode_token(refresh)
    assert ref_payload["sub"] == "42"
    assert ref_payload["type"] == "refresh"
    assert ref_payload["sid"] == 101


@pytest.mark.asyncio
async def test_auth_service_signup_and_login(db_session: AsyncSession):
    """Test AuthService full registration and login flow."""
    auth_service = AuthService(db_session)

    # Signup
    signup_req = SignupRequest(
        username="john_doe",
        email="john@globalpulse.io",
        password="SecurePassword123!",
        mobile_number="+919876543210",
    )
    token_resp = await auth_service.signup(signup_req)
    assert token_resp.access_token is not None
    assert token_resp.user.username == "john_doe"

    # Login
    login_req = LoginRequest(identity="john_doe", password="SecurePassword123!")
    login_resp = await auth_service.login(login_req)
    assert login_resp.access_token is not None
    assert login_resp.user.email == "john@globalpulse.io"


@pytest.mark.asyncio
async def test_auth_service_otp_flow(db_session: AsyncSession):
    """Test OTP generation and verification flow."""
    auth_service = AuthService(db_session)

    # Send OTP
    send_resp = await auth_service.send_otp(SendOtpRequest(mobile_number="+919999988888"))
    otp_code = send_resp["otpCode"]
    assert len(otp_code) == 6

    # Verify OTP
    ver_resp = await auth_service.verify_otp(VerifyOtpRequest(mobile_number="+919999988888", otp_code=otp_code))
    assert ver_resp.verification_token is not None


@pytest.mark.asyncio
async def test_auth_api_endpoints(db_session: AsyncSession):
    """Test FastAPI auth API routes over HTTP client with injected DB session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Signup API
            resp = await client.post(
                "/api/v1/auth/signup",
                json={
                    "username": "api_user",
                    "email": "api@globalpulse.io",
                    "password": "Password123!",
                    "mobileNumber": "+918888877777",
                },
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "accessToken" in data
            assert data["user"]["username"] == "api_user"

            token = data["accessToken"]

            # Get Me API
            me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me_resp.status_code == 200
            me_data = me_resp.json()
            assert me_data["username"] == "api_user"
    finally:
        app.dependency_overrides.clear()
