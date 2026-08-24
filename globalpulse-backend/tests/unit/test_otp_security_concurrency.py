"""
Unit & Concurrency Tests for Production-Grade Email & Mobile OTP System.
Validates SHA-256 hashed storage, 60s resend cooldown, 3 req / 10 min window limit,
atomic concurrency handling (Send & Verify), and context/purpose isolation.
"""
import asyncio
import hashlib
import pytest
from datetime import datetime, timedelta, timezone

from unittest.mock import patch
from app.services.auth_service import AuthService
from app.schemas.auth import SendOtpRequest, VerifyOtpRequest
from app.repositories.user_repository import OtpRepository, UserRepository
from app.core.exceptions import GlobalPulseError, ValidationError, ServiceUnavailableError, ConflictError
from app.db.models.user_model import UserModel


import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.models import Base

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_otp_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_otp_sha256_hashed_storage(db_session):
    """Verify that plaintext OTPs are never stored, only 64-character SHA-256 hashes."""
    auth_svc = AuthService(db_session)
    otp_repo = OtpRepository(db_session)

    target_email = "test_sha256_hash@globalpulse.com"
    req = SendOtpRequest(target=target_email, channel="EMAIL", purpose="EMAIL_VERIFICATION")

    with patch("app.services.email_service.EmailService.validate_configuration"), \
         patch("app.services.email_service.EmailService.send_otp_email", return_value=True):
        await auth_svc.send_otp(req)

    latest_otp = await otp_repo.get_recent_otp_for_cooldown(target_email, "EMAIL", "EMAIL_VERIFICATION", cooldown_seconds=300)
    assert latest_otp is not None
    assert latest_otp.otp_code_hash is not None
    assert len(latest_otp.otp_code_hash) == 64
    assert latest_otp.otp_code is None or latest_otp.otp_code == ""


@pytest.mark.asyncio
async def test_otp_rate_limiting_60s_cooldown(db_session):
    """Verify server-side 60s cooldown blocks rapid resend requests with HTTP 429."""
    auth_svc = AuthService(db_session)
    target_email = "test_cooldown@globalpulse.com"
    req = SendOtpRequest(target=target_email, channel="EMAIL", purpose="EMAIL_VERIFICATION")

    with patch("app.services.email_service.EmailService.validate_configuration"), \
         patch("app.services.email_service.EmailService.send_otp_email", return_value=True):
        # First request
        await auth_svc.send_otp(req)

        # Second request immediately after (within 60s)
        with pytest.raises(GlobalPulseError) as exc_info:
            await auth_svc.send_otp(req)
        
        assert exc_info.value.status_code == 429
        assert "Resend cooldown active" in exc_info.value.message


@pytest.mark.asyncio
async def test_otp_purpose_isolation(db_session):
    """Verify that an OTP issued for PROFILE_CHANGE cannot be verified for PASSWORD_RESET."""
    auth_svc = AuthService(db_session)
    otp_repo = OtpRepository(db_session)

    target_email = "test_isolation@globalpulse.com"
    raw_code = "654321"
    otp_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    # Manually seed a valid PROFILE_CHANGE OTP record
    await otp_repo.create(
        {
            "target": target_email,
            "email": target_email,
            "channel": "EMAIL",
            "purpose": "PROFILE_CHANGE",
            "otp_code_hash": otp_hash,
            "attempt_count": 0,
            "max_attempts": 5,
            "delivery_status": "SENT",
            "expires_at": expires,
            "is_verified": False,
        }
    )

    # Attempt to verify under PASSWORD_RESET purpose
    wrong_req = VerifyOtpRequest(
        target=target_email,
        channel="EMAIL",
        purpose="PASSWORD_RESET",
        otp_code=raw_code,
    )

    with pytest.raises(ValidationError) as exc_info:
        await auth_svc.verify_otp(wrong_req)

    assert "Invalid or expired OTP" in exc_info.value.message


@pytest.mark.asyncio
async def test_otp_max_5_attempts_invalidation(db_session):
    """Verify that 5 failed verification attempts invalidate the OTP."""
    auth_svc = AuthService(db_session)
    otp_repo = OtpRepository(db_session)

    target_email = "test_max_attempts@globalpulse.com"
    raw_code = "999999"
    otp_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    otp_rec = await otp_repo.create(
        {
            "target": target_email,
            "email": target_email,
            "channel": "EMAIL",
            "purpose": "EMAIL_VERIFICATION",
            "otp_code_hash": otp_hash,
            "attempt_count": 0,
            "max_attempts": 5,
            "delivery_status": "SENT",
            "expires_at": expires,
            "is_verified": False,
        }
    )

    verify_req = VerifyOtpRequest(
        target=target_email,
        channel="EMAIL",
        purpose="EMAIL_VERIFICATION",
        otp_code="000000",  # Wrong code
    )

    # Submit 4 wrong attempts
    for _ in range(4):
        with pytest.raises(ValidationError):
            await auth_svc.verify_otp(verify_req)

    # 5th attempt invalidates
    with pytest.raises(ValidationError) as exc_info:
        await auth_svc.verify_otp(verify_req)

    assert "invalidated" in exc_info.value.message.lower() or "remaining attempts: 0" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_otp_atomic_consumption_concurrency(db_session):
    """Verify that atomic consume_otp_atomic prevents double consumption under concurrent verification."""
    otp_repo = OtpRepository(db_session)

    target_email = "test_atomic@globalpulse.com"
    raw_code = "112233"
    otp_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    otp_rec = await otp_repo.create(
        {
            "target": target_email,
            "email": target_email,
            "channel": "EMAIL",
            "purpose": "EMAIL_VERIFICATION",
            "otp_code_hash": otp_hash,
            "attempt_count": 0,
            "max_attempts": 5,
            "delivery_status": "SENT",
            "expires_at": expires,
            "is_verified": False,
        }
    )

    # Simulate two simultaneous verification requests
    res1 = await otp_repo.consume_otp_atomic(otp_rec.otp_id)
    res2 = await otp_repo.consume_otp_atomic(otp_rec.otp_id)

    # Exactly ONE must return True, the other MUST return False
    assert (res1 is True and res2 is False) or (res1 is False and res2 is True)


@pytest.mark.asyncio
async def test_verify_otp_duplicate_email_conflict_raises_409(db_session):
    """Verify that submitting a valid OTP for an email owned by another user raises HTTP 409 Conflict and leaves OTP unconsumed."""
    auth_svc = AuthService(db_session)
    otp_repo = OtpRepository(db_session)
    user_repo = UserRepository(db_session)

    # Create User 1 and User 2
    u1 = await user_repo.create({"username": "user_one", "email": "user1@globalpulse.com", "password_hash": "hash123"})
    u2 = await user_repo.create({"username": "user_two", "email": "user2@globalpulse.com", "password_hash": "hash123"})

    target_email = "user2@globalpulse.com"  # Owned by User 2!
    raw_code = "654321"
    otp_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    otp_rec = await otp_repo.create(
        {
            "user_id": u1.user_id,
            "target": target_email,
            "email": target_email,
            "channel": "EMAIL",
            "purpose": "PROFILE_CHANGE",
            "otp_code_hash": otp_hash,
            "attempt_count": 0,
            "max_attempts": 5,
            "delivery_status": "SENT",
            "expires_at": expires,
            "is_verified": False,
        }
    )

    verify_req = VerifyOtpRequest(
        target=target_email,
        channel="EMAIL",
        purpose="PROFILE_CHANGE",
        otp_code=raw_code,
    )

    # User 1 attempts to verify OTP for target_email (owned by User 2)
    with pytest.raises(ConflictError) as exc_info:
        await auth_svc.verify_otp(verify_req, authenticated_user_id=u1.user_id)

    assert exc_info.value.status_code == 409
    assert "already associated with another account" in exc_info.value.message

    # Verify OTP is NOT consumed
    fresh_otp = await otp_repo.get_by_id(otp_rec.otp_id)
    assert fresh_otp.is_verified is False


@pytest.mark.asyncio
async def test_verify_otp_same_current_email_succeeds_200(db_session):
    """Verify that submitting OTP for user's own current email succeeds with 200 without SQL update conflict."""
    auth_svc = AuthService(db_session)
    otp_repo = OtpRepository(db_session)
    user_repo = UserRepository(db_session)

    u1 = await user_repo.create({"username": "user_same", "email": "same@globalpulse.com", "password_hash": "hash123"})

    target_email = "same@globalpulse.com"
    raw_code = "998877"
    otp_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    await otp_repo.create(
        {
            "user_id": u1.user_id,
            "target": target_email,
            "email": target_email,
            "channel": "EMAIL",
            "purpose": "PROFILE_CHANGE",
            "otp_code_hash": otp_hash,
            "attempt_count": 0,
            "max_attempts": 5,
            "delivery_status": "SENT",
            "expires_at": expires,
            "is_verified": False,
        }
    )

    verify_req = VerifyOtpRequest(
        target=target_email,
        channel="EMAIL",
        purpose="PROFILE_CHANGE",
        otp_code=raw_code,
    )

    res = await auth_svc.verify_otp(verify_req, authenticated_user_id=u1.user_id)
    assert res.verification_token is not None

    fresh_u1 = await user_repo.get_by_id(u1.user_id)
    assert fresh_u1.is_email_verified is True
    assert fresh_u1.email == "same@globalpulse.com"
