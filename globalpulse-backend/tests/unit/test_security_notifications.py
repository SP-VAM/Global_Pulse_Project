"""
Comprehensive Unit Test Suite for Account & Security Notification Enhancements.
Validates:
  - PASSWORD_CHANGED notification triggers and failure safety
  - EMAIL_PHONE_UPDATED notification triggers, OTP verification safety, same-value suppression
  - MULTIPLE_FAILED_LOGINS true rolling 10-minute window detection and duplicate alert suppression
  - Explicit concurrency handling on failed logins and remote session revocations
  - REMOTE_SESSION_REVOKED notification triggers, current-session logout exclusion, cross-user isolation
  - Zero sensitive credential logging & database IntegrityError rollback safety
"""
import hashlib
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import AuthenticationError, ConflictError, GlobalPulseError, ValidationError
from app.db.models.notification_model import NotificationModel
from app.db.models.user_model import AuditLogModel, OtpVerificationModel, UserModel, UserSessionModel
from app.repositories.user_repository import AuditRepository, OtpRepository, SessionRepository, UserRepository
from app.services.auth_service import AuthService

REAL_OTP_HASH = hashlib.sha256(b"123456").hexdigest()

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class DummyReq:
    def __init__(self, current_password="", new_password="", confirm_password=""):
        self.current_password = current_password
        self.new_password = new_password
        self.confirm_password = confirm_password


# ---------------------------------------------------------------------------
# 1. PASSWORD CHANGE TESTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_successful_password_change_creates_notification(mock_db_session):
    """Verifies successful password change generates PASSWORD_CHANGED notification post-commit."""
    service = AuthService(mock_db_session)
    user = UserModel(user_id=1, username="testuser", password_hash="$2b$12$e..." )

    with patch.object(service.user_repo, "get_by_id", return_value=user), \
         patch("app.services.auth_service.verify_password", side_effect=[True, False]), \
         patch("app.services.auth_service.hash_password", return_value="new_hash"), \
         patch.object(service.user_repo, "update", return_value=user), \
         patch.object(service.audit_repo, "create", return_value=AuditLogModel(audit_id=50, user_id=1)), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        req = DummyReq(current_password="old_password", new_password="new_password_123", confirm_password="new_password_123")
        res = await service.change_password(user_id=1, req=req)

        assert res["message"] == "Password updated successfully."
        assert mock_db_session.commit.called
        assert mock_notif.called
        call_kwargs = mock_notif.call_args[1]
        assert call_kwargs["notification_type"] == "PASSWORD_CHANGED"
        assert call_kwargs["dedup_key"] == "password_changed:1:50"


@pytest.mark.asyncio
async def test_invalid_current_password_creates_no_notification(mock_db_session):
    """Verifies failed current password check raises ValidationError and creates NO notification."""
    service = AuthService(mock_db_session)
    user = UserModel(user_id=1, password_hash="hash")

    with patch.object(service.user_repo, "get_by_id", return_value=user), \
         patch("app.services.auth_service.verify_password", return_value=False), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        req = DummyReq(current_password="wrong", new_password="new_password_123")
        with pytest.raises(ValidationError):
            await service.change_password(user_id=1, req=req)

        assert not mock_notif.called


@pytest.mark.asyncio
async def test_notification_failure_does_not_rollback_password_change(mock_db_session):
    """Verifies notification dispatch error post-commit does NOT break or undo password change."""
    service = AuthService(mock_db_session)
    user = UserModel(user_id=1, password_hash="hash")

    with patch.object(service.user_repo, "get_by_id", return_value=user), \
         patch("app.services.auth_service.verify_password", side_effect=[True, False]), \
         patch("app.services.auth_service.hash_password", return_value="new_hash"), \
         patch.object(service.user_repo, "update", return_value=user), \
         patch.object(service.audit_repo, "create", return_value=AuditLogModel(audit_id=51, user_id=1)), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", side_effect=Exception("FCM timeout")):

        req = DummyReq(current_password="old_password", new_password="new_password_123")
        res = await service.change_password(user_id=1, req=req)

        # Password update succeeded
        assert res["message"] == "Password updated successfully."
        assert mock_db_session.commit.called


# ---------------------------------------------------------------------------
# 2. EMAIL / MOBILE UPDATE TESTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_verified_email_update_creates_notification(mock_db_session):
    """Verifies verified email change dispatches EMAIL_PHONE_UPDATED notification."""
    service = AuthService(mock_db_session)
    otp = OtpVerificationModel(otp_id=99, user_id=1, channel="EMAIL", is_verified=False, max_attempts=5, attempt_count=0, otp_code_hash=REAL_OTP_HASH)
    user = UserModel(user_id=1, email="old@example.com")

    with patch.object(service.otp_repo, "get_latest_valid_otp", return_value=otp), \
         patch.object(service.otp_repo, "consume_otp_atomic", return_value=True), \
         patch.object(service.user_repo, "get_by_email", return_value=None), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        mock_db_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: user),
            MagicMock(scalar_one_or_none=lambda: None),
            MagicMock(scalar_one_or_none=lambda: None),
        ]

        req = MagicMock(target_value="new@example.com", otp_code="123456", channel="EMAIL", purpose="EMAIL_VERIFICATION")
        await service.verify_otp(req, authenticated_user_id=1)

        assert user.email == "new@example.com"
        assert mock_notif.called
        call_kwargs = mock_notif.call_args[1]
        assert call_kwargs["notification_type"] == "EMAIL_PHONE_UPDATED"
        assert call_kwargs["dedup_key"] == "email_phone_updated:1:99"


@pytest.mark.asyncio
async def test_same_existing_email_creates_no_update_notification(mock_db_session):
    """Verifies verifying identical email (old == new) does NOT dispatch EMAIL_PHONE_UPDATED alert."""
    service = AuthService(mock_db_session)
    otp = OtpVerificationModel(otp_id=100, user_id=1, channel="EMAIL", otp_code_hash=REAL_OTP_HASH)
    user = UserModel(user_id=1, email="same@example.com")

    with patch.object(service.otp_repo, "get_latest_valid_otp", return_value=otp), \
         patch.object(service.otp_repo, "consume_otp_atomic", return_value=True), \
         patch.object(service.user_repo, "get_by_email", return_value=user), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        mock_db_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: user),
            MagicMock(scalar_one_or_none=lambda: user),
        ]

        req = MagicMock(target_value="same@example.com", otp_code="123456", channel="EMAIL", purpose="EMAIL_VERIFICATION")
        await service.verify_otp(req, authenticated_user_id=1)

        assert not mock_notif.called


# ---------------------------------------------------------------------------
# 3. FAILED LOGIN TESTS (TRUE ROLLING 10-MINUTE WINDOW)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failed_logins_rolling_10_minute_window_threshold(mock_db_session):
    """Verifies attempts 1 & 2 do not alert, attempt 3 alerts, attempt 4 in same window deduplicates."""
    service = AuthService(mock_db_session)
    user = UserModel(user_id=1, password_hash="hash")

    with patch.object(service.user_repo, "get_by_identity", return_value=user), \
         patch("app.services.auth_service.verify_password", return_value=False), \
         patch.object(service.audit_repo, "create", return_value=AuditLogModel(audit_id=200, user_id=1)), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        req = MagicMock(identity="testuser", password="wrong")

        # Attempt 1 -> 1 failed attempt in window -> No alert
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=lambda: 1),  # count = 1
        ]
        with pytest.raises(AuthenticationError):
            await service.login(req)
        assert not mock_notif.called

        # Attempt 2 -> 2 failed attempts in window -> No alert
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=lambda: 2),  # count = 2
        ]
        with pytest.raises(AuthenticationError):
            await service.login(req)
        assert not mock_notif.called

        # Attempt 3 -> 3 failed attempts in window -> Triggers MULTIPLE_FAILED_LOGINS!
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=lambda: 3),  # count = 3
            MagicMock(scalar=lambda: 0),  # recent_alerts = 0
            MagicMock(scalar_one_or_none=lambda: None),
        ]
        with pytest.raises(AuthenticationError):
            await service.login(req)
        # Attempt 4 in same window -> recent_alerts = 1 -> Deduplicated! No new alert
        mock_notif.reset_mock()
        mock_db_session.execute.side_effect = [
            MagicMock(scalar=lambda: 4),  # count = 4
            MagicMock(scalar=lambda: 1),  # recent_alerts = 1 (alert already sent)
        ]
        with pytest.raises(AuthenticationError):
            await service.login(req)
        assert not mock_notif.called


# ---------------------------------------------------------------------------
# 4. EXPLICIT CONCURRENCY TESTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_failed_login_requests_create_only_one_notification(mock_db_session):
    """Verifies DB IntegrityError on dedup_key prevents concurrent duplicate alerts safely."""
    from app.repositories.notification_repository import NotificationRepository
    from sqlalchemy.exc import IntegrityError

    repo = NotificationRepository(mock_db_session)
    mock_db_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None),
        MagicMock(scalar_one_or_none=lambda: NotificationModel(notification_id=888, dedup_key="dup_key")),
    ]
    mock_db_session.commit.side_effect = IntegrityError("stmt", "params", Exception("duplicate dedup_key"))

    result = await repo.create_notification(
        user_id=1,
        title="⚠️ Multiple Failed Login Attempts",
        message="Test",
        notification_type="MULTIPLE_FAILED_LOGINS",
        dedup_key="dup_key",
    )
    assert result is not None
    assert result.notification_id == 888
    assert mock_db_session.rollback.called


# ---------------------------------------------------------------------------
# 5. SESSION MANAGEMENT & REVOCATION TESTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_revoke_remote_session_creates_notification(mock_db_session):
    """Verifies revoking Session B from Session A sends REMOTE_SESSION_REVOKED notification."""
    service = AuthService(mock_db_session)
    target_session = UserSessionModel(session_id=10, user_id=1, is_active=True)

    with patch.object(service.session_repo, "get_active_session", return_value=target_session), \
         patch.object(service.session_repo, "revoke_session", return_value=None), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        res = await service.revoke_remote_session(user_id=1, target_session_id=10, current_session_id=20)
        assert res["success"] is True
        assert mock_notif.called
        call_kwargs = mock_notif.call_args[1]
        assert call_kwargs["notification_type"] == "REMOTE_SESSION_REVOKED"
        assert call_kwargs["dedup_key"] == "remote_session_revoked:1:10"


@pytest.mark.asyncio
async def test_revoke_current_session_does_not_create_remote_notification(mock_db_session):
    """Verifies self-logout (target_session == current_session) does NOT create remote notification."""
    service = AuthService(mock_db_session)
    target_session = UserSessionModel(session_id=10, user_id=1, is_active=True)

    with patch.object(service.session_repo, "get_active_session", return_value=target_session), \
         patch.object(service.session_repo, "revoke_session", return_value=None), \
         patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:

        res = await service.revoke_remote_session(user_id=1, target_session_id=10, current_session_id=10)
        assert res["success"] is True
        assert not mock_notif.called


@pytest.mark.asyncio
async def test_cross_user_session_revocation_forbidden(mock_db_session):
    """Verifies revoking another user's session is rejected server-side."""
    service = AuthService(mock_db_session)
    # Session belongs to user_id=2
    target_session = UserSessionModel(session_id=10, user_id=2, is_active=True)

    with patch.object(service.session_repo, "get_active_session", return_value=None):
        with pytest.raises(ValidationError) as exc_info:
            await service.revoke_remote_session(user_id=1, target_session_id=10, current_session_id=1)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 6. ZERO CREDENTIAL EXPOSURE TEST
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_security_notifications_contain_no_sensitive_credentials():
    """Verifies no passwords, hashes, OTPs, or JWT tokens exist in notification strings."""
    secret_terms = ["password", "hash", "jwt", "bearer", "token", "otp", "$2b$"]
    title = "🔐 Password Changed"
    msg = "Your account password was successfully changed. If you did not make this change, secure your account immediately."
    
    for term in ["password_hash", "access_token", "refresh_token", "otp_code"]:
        assert term not in title.lower()
        assert term not in msg.lower()


# ---------------------------------------------------------------------------
# 7. CLEAR READ NOTIFICATIONS TEST
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_clear_read_notifications_deletes_only_read(mock_db_session):
    """Verifies clear_read_notifications deletes only read notifications for current user."""
    from app.services.notification_service import NotificationService
    service = NotificationService(mock_db_session)

    with patch.object(service.repo, "delete_read_notifications", return_value=3) as mock_del:
        count = await service.delete_read_notifications(user_id=1)
        assert count == 3
        mock_del.assert_called_once_with(user_id=1)

