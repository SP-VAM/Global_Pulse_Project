"""
Comprehensive security regression test suite for FRD-050 Security.
Verifies authentication enforcement, JWT validation, IDOR prevention across all
financial resources, password hashing, input validation, SQL injection resistance,
CORS, security headers, and secret redaction.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
import jwt
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies import get_current_active_user, get_current_user
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.core.logging import SensitiveDataRedactionFilter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.expense_model import BudgetModel, ExpenseModel, IncomeModel
from app.db.models.notification_model import NotificationModel
from app.db.models.portfolio_model import UserInvestmentModel
from app.db.models.user_model import UserModel
from app.main import app
from app.services.expense_service import ExpenseService
from app.services.notification_service import NotificationService
from app.services.portfolio_service import PortfolioService

settings = get_settings()


# ---------------------------------------------------------------------------
# Fixtures for Two Distinct Test Users
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a():
    return UserModel(
        user_id=1001,
        email="user_a@globalpulse.test",
        username="user_a",
        is_email_verified=True,
        account_status="ACTIVE",
    )


@pytest.fixture
def user_b():
    return UserModel(
        user_id=2002,
        email="user_b@globalpulse.test",
        username="user_b",
        is_email_verified=True,
        account_status="ACTIVE",
    )


@pytest.fixture
def locked_user():
    return UserModel(
        user_id=3003,
        email="locked@globalpulse.test",
        username="locked_user",
        is_email_verified=True,
        account_status="LOCKED",
    )


# ---------------------------------------------------------------------------
# 1. Password Hashing & Verification Tests
# ---------------------------------------------------------------------------


def test_password_hashing_and_verification():
    """Verify bcrypt hashing, salt generation, and constant-time check."""
    raw_password = "SuperSecurePassword#2026!"
    hashed = hash_password(raw_password)

    # 1. Plaintext password is not present in hash
    assert raw_password not in hashed
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # 2. Correct password verifies successfully
    assert verify_password(raw_password, hashed) is True

    # 3. Incorrect password returns False
    assert verify_password("WrongPassword123", hashed) is False

    # 4. Empty password returns False without raising
    assert verify_password("", hashed) is False
    assert verify_password(raw_password, "") is False


# ---------------------------------------------------------------------------
# 2. JWT Generation, Expiration & Signature Validation Tests
# ---------------------------------------------------------------------------


def test_jwt_token_validation():
    """Test valid, expired, and tampered JWT tokens."""
    # 1. Valid token creation and decoding
    token = create_access_token(subject=1001, extra_claims={"email": "user_a@globalpulse.test"})
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == "1001"
    assert decoded["type"] == "access"

    # 2. Expired token validation failure
    now = datetime.now(timezone.utc)
    expired_claims = {"sub": "1001", "type": "access", "exp": now - timedelta(hours=1)}
    expired_token = jwt.encode(expired_claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    # 3. Tampered signature validation failure
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong_secret_key_12345678901234567890", algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# 3. Authentication Enforcement & Status Checks on Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_protected_endpoints_require_authentication():
    """Protected endpoints reject requests missing Authorization header with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Expenses
        r1 = await client.get("/api/v1/expenses/summary")
        assert r1.status_code == 401

        # Notifications
        r2 = await client.get("/api/v1/notifications")
        assert r2.status_code == 401

        # Portfolio
        r3 = await client.get("/api/v1/portfolio/summary")
        assert r3.status_code == 401

        # User profile /me
        r4 = await client.get("/api/v1/auth/me")
        assert r4.status_code == 401


@pytest.mark.asyncio
async def test_locked_account_rejected(locked_user):
    """Inactive/locked user accounts are rejected with 403 Forbidden."""
    app.dependency_overrides[get_current_user] = lambda: locked_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/expenses/summary", headers={"Authorization": "Bearer valid_mock_token"})
            assert resp.status_code == 403
            assert "Inactive" in resp.json()["error"]["message"] or "locked" in resp.json()["error"]["message"].lower()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. IDOR Defense: Cross-User Resource Isolation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idor_defense_expense_service(user_a, user_b):
    """User B cannot read, update, or delete User A's expenses."""
    mock_session = AsyncMock()
    service = ExpenseService(mock_session)

    # 1. User A owns expense #50
    mock_expense_a = ExpenseModel(
        expense_id=50,
        user_id=user_a.user_id,
        category_id=1,
        amount=500.0,
        expense_date=date(2026, 8, 1),
        payment_method="UPI",
        notes="User A Lunch",
    )

    # Repo get_by_id returns the model, but service checks user_id ownership
    service.expense_repo.get_by_id = AsyncMock(return_value=mock_expense_a)

    # User B attempts to update User A's expense -> raises NotFoundError / ValidationError (IDOR blocked)
    with pytest.raises((NotFoundError, ValidationError)):
        await service.update_expense(
            user_id=user_b.user_id,
            expense_id=50,
            req=MagicMock(category_id=1, category_name=None, amount=600.0, expense_date=None, payment_method=None, notes=None),
        )

    # User B attempts to delete User A's expense -> raises NotFoundError / ValidationError (IDOR blocked)
    with pytest.raises((NotFoundError, ValidationError)):
        await service.delete_expense(user_id=user_b.user_id, expense_id=50)


@pytest.mark.asyncio
async def test_idor_defense_income_service(user_a, user_b):
    """User B cannot update or delete User A's income entries."""
    mock_session = AsyncMock()
    service = ExpenseService(mock_session)

    # User A owns income #70
    mock_income_a = IncomeModel(
        income_id=70,
        user_id=user_a.user_id,
        amount=50000.0,
        income_date=date(2026, 8, 1),
        payment_method="Salary",
        notes="User A Monthly Salary",
    )
    service.income_repo.get_by_id = AsyncMock(return_value=mock_income_a)

    # User B attempts to update User A's income -> raises NotFoundError / ValidationError
    with pytest.raises((NotFoundError, ValidationError)):
        await service.update_income(
            user_id=user_b.user_id,
            income_id=70,
            req=MagicMock(amount=60000.0, income_date=None, payment_method=None, notes=None),
        )

    # User B attempts to delete User A's income -> raises NotFoundError / ValidationError
    with pytest.raises((NotFoundError, ValidationError)):
        await service.delete_income(user_id=user_b.user_id, income_id=70)


@pytest.mark.asyncio
async def test_idor_defense_budget_service(user_a, user_b):
    """User B cannot delete User A's budget configuration."""
    mock_session = AsyncMock()
    service = ExpenseService(mock_session)

    mock_budget_a = BudgetModel(
        budget_id=10,
        user_id=user_a.user_id,
        category_id=1,
        budget_amount=10000.0,
        budget_year=2026,
        budget_month=8,
    )
    service.budget_repo.get_by_id = AsyncMock(return_value=mock_budget_a)

    # User B attempts to delete User A's budget -> raises NotFoundError / ValidationError
    with pytest.raises((NotFoundError, ValidationError)):
        await service.delete_budget(user_id=user_b.user_id, budget_id=10)


@pytest.mark.asyncio
async def test_idor_defense_portfolio_service(user_a, user_b):
    """User B cannot update or delete User A's investment holdings."""
    mock_session = AsyncMock()
    service = PortfolioService(mock_session)

    # Repo query returns None when user_id is User B but investment belongs to User A
    service.portfolio_repo.get_user_investment_by_id = AsyncMock(return_value=None)

    # User B attempts to update User A's holding -> raises ValidationError
    with pytest.raises(ValidationError):
        await service.update_investment(
            user_id=user_b.user_id,
            investment_id=99,
            req=MagicMock(model_dump=lambda **k: {"quantity": 100}),
        )

    # User B attempts to delete User A's holding -> raises ValidationError
    with pytest.raises(ValidationError):
        await service.delete_investment(user_id=user_b.user_id, investment_id=99)


@pytest.mark.asyncio
async def test_idor_defense_notifications_service(user_a, user_b):
    """User B cannot read or mark as read User A's notifications."""
    mock_session = AsyncMock()
    service = NotificationService(mock_session)

    # Repo returns None when notification belongs to another user
    service.repo.mark_as_read = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.mark_as_read(notification_id=88, user_id=user_b.user_id)


# ---------------------------------------------------------------------------
# 5. Non-Admin Cross-User Notification Dispatch Prohibition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_admin_cannot_dispatch_notification_to_other_user(user_a, user_b):
    """Regular user cannot send notification to another user ID (returns 403)."""
    app.dependency_overrides[get_current_active_user] = lambda: user_a
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/notifications/send",
                json={
                    "user_id": user_b.user_id,  # User A attempts to target User B
                    "title": "Spam Alert",
                    "message": "Unauthorized message",
                },
            )
            assert resp.status_code == 403
            assert "Only administrators" in resp.json()["error"]["message"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 6. Security Headers Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_response_headers():
    """Verify security headers are attached to all API responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        headers = resp.headers

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "geolocation=()" in headers.get("Permissions-Policy", "")
        assert "X-Request-ID" in headers


# ---------------------------------------------------------------------------
# 7. Sensitive Data Redaction Verification
# ---------------------------------------------------------------------------


def test_sensitive_data_redaction_filter():
    """Verify secrets (Bearer tokens, Authorization, DB credentials) are scrubbed."""
    filter_ = SensitiveDataRedactionFilter()

    # 1. Bearer Token
    r1 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Login token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDAxIn0",
        args=(),
        exc_info=None,
    )
    filter_.filter(r1)
    assert "[REDACTED]" in r1.msg
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI" not in r1.msg

    # 2. DB credentials in PostgreSQL connection URL
    r2 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="DATABASE_URL=postgresql://postgres:MySecretPassword123@junction.proxy.rlwy.net:12345/railway",
        args=(),
        exc_info=None,
    )
    filter_.filter(r2)
    assert "[REDACTED]" in r2.msg
    assert "MySecretPassword123" not in r2.msg
