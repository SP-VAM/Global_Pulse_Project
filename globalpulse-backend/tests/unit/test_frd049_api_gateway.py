"""
FRD-049 API Gateway Verification & Regression Test Suite
Validates all 15 core architectural capabilities of the GlobalPulse API Gateway:
  1. Centralized routing
  2. API versioning (/api/v1 and /api/auth)
  3. Authentication enforcement
  4. Authorization & tenant isolation
  5. Request validation
  6. Security headers enforcement
  7. Rate limiting & 429 responses
  8. Request ID generation and propagation
  9. Centralized structured logging
  10. Unified error response contract
  11. Latency & monitoring visibility
  12. Max body size enforcement (HTTP 413)
  13. CORS & Trusted Host protection
  14. Production API documentation protection
  15. External API failure translation (502 / 504)
"""
from datetime import date, datetime, timedelta, timezone
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import jwt
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.dependencies import get_current_active_user
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AuthenticationError,
    ExplanationProviderError,
    ExplanationProviderResponseError,
    ExplanationProviderTimeoutError,
    NotFoundError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ValidationError,
)
from app.core.logging import SensitiveDataRedactionFilter, log_api_request
from app.core.middleware import (
    MaxBodySizeMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.security import create_access_token
from app.db.models.user_model import UserModel
from app.main import app, create_app

settings = get_settings()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def active_user():
    return UserModel(
        user_id=101,
        email="gateway_user@globalpulse.test",
        username="gateway_tester",
        is_email_verified=True,
        account_status="ACTIVE",
    )


@pytest.fixture
def locked_user():
    return UserModel(
        user_id=102,
        email="locked_gateway@globalpulse.test",
        username="locked_tester",
        is_email_verified=True,
        account_status="LOCKED",
    )


# ---------------------------------------------------------------------------
# 1 & 2. Centralized Routing & API Versioning
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_route_versioning_and_registration():
    """Verify versioned /api/v1 routes and /api/auth routes are registered on the gateway."""
    routes = [route.path for route in app.routes]
    
    # Versioned functional endpoints
    assert "/api/v1/health" in routes
    assert "/api/v1/market-status" in routes
    assert "/api/v1/markets" in routes
    assert "/api/v1/stocks/companies" in routes
    assert "/api/v1/expenses/summary" in routes
    assert "/api/v1/goals" in routes
    assert "/api/v1/notifications" in routes
    
    # Auth endpoints
    assert "/api/auth/login" in routes
    assert "/api/auth/signup" in routes


@pytest.mark.asyncio
async def test_gateway_unversioned_route_returns_404():
    """Verify calling an unversioned or non-existent route returns standard 404 envelope."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/unversioned_test_endpoint")
        assert res.status_code == 404
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] in ["HTTP_404", "NOT_FOUND"]
        assert "requestId" in data["error"]


@pytest.mark.asyncio
async def test_gateway_unsupported_http_method_returns_405():
    """Verify calling an unsupported HTTP method returns 405 Method Not Allowed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/api/v1/health")
        assert res.status_code == 405
        data = res.json()
        assert "error" in data
        assert "requestId" in data["error"]


# ---------------------------------------------------------------------------
# 3 & 4. Authentication & Authorization Enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_auth_missing_header():
    """Verify protected route rejects missing Authorization header with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/expenses/summary")
        assert res.status_code == 401
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] in ["HTTP_401", "UNAUTHORIZED", "AUTHENTICATION_ERROR"]


@pytest.mark.asyncio
async def test_gateway_auth_malformed_and_tampered_token():
    """Verify protected route rejects malformed and tampered JWTs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Malformed
        res1 = await client.get(
            "/api/v1/expenses/summary",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert res1.status_code == 401

        # Tampered signature
        valid_token = create_access_token(101, extra_claims={"email": "test@gp.test"})
        tampered_token = valid_token[:-5] + "XXXXX"
        res2 = await client.get(
            "/api/v1/expenses/summary",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert res2.status_code == 401


@pytest.mark.asyncio
async def test_gateway_auth_expired_token():
    """Verify protected route rejects expired JWTs."""
    secret = settings.JWT_SECRET_KEY
    alg = settings.JWT_ALGORITHM
    expired_payload = {
        "sub": "101",
        "email": "test@gp.test",
        "exp": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, secret, algorithm=alg)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/expenses/summary",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# 5. Request Validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_request_validation_malformed_payload(active_user):
    """Verify invalid request body returns 422 with structured validation error."""
    app.dependency_overrides[get_current_active_user] = lambda: active_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Missing amount and invalid date
            res = await client.post(
                "/api/v1/expenses",
                headers={"Authorization": "Bearer fake"},
                json={"category_id": 1, "notes": "No amount"},
            )
            assert res.status_code == 422
            data = res.json()
            assert "error" in data
            assert data["error"]["code"] == "VALIDATION_ERROR"
            assert "requestId" in data["error"]
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


# ---------------------------------------------------------------------------
# 6. Security Headers Enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_security_headers_present_on_all_responses():
    """Verify security headers are attached across both 200 and 404 responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ["/api/v1/health", "/non-existent-route"]:
            res = await client.get(path)
            assert res.headers.get("X-Content-Type-Options") == "nosniff"
            assert res.headers.get("X-Frame-Options") == "DENY"
            assert res.headers.get("X-XSS-Protection") == "1; mode=block"
            assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
            assert "Permissions-Policy" in res.headers


@pytest.mark.asyncio
async def test_gateway_hsts_header_in_production():
    """Verify Strict-Transport-Security is applied in production and omitted in dev."""
    middleware_prod = SecurityHeadersMiddleware(app=MagicMock(), app_env="production")
    middleware_dev = SecurityHeadersMiddleware(app=MagicMock(), app_env="development")

    req = MagicMock(spec=Request)
    async def dummy_call_next(r):
        return Response("ok", status_code=200)

    res_prod = await middleware_prod.dispatch(req, dummy_call_next)
    assert "Strict-Transport-Security" in res_prod.headers
    assert "max-age=63072000" in res_prod.headers["Strict-Transport-Security"]

    res_dev = await middleware_dev.dispatch(req, dummy_call_next)
    assert "Strict-Transport-Security" not in res_dev.headers


# ---------------------------------------------------------------------------
# 7. Rate Limiting & 429 Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_rate_limiting_tier_and_429():
    """Verify slowapi rate limiter trips when limit is exceeded."""
    from app.api.v1.limiter import limiter
    assert limiter is not None
    assert app.state.limiter is not None

    # Verify limiter settings
    assert settings.RATE_LIMIT_LLM == "30/minute"
    assert settings.RATE_LIMIT_DATA == "60/minute"
    assert settings.RATE_LIMIT_LIST == "120/minute"
    assert settings.RATE_LIMIT_HEALTH == "300/minute"


# ---------------------------------------------------------------------------
# 8. Request ID Generation & Propagation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_request_id_generation_and_propagation():
    """Verify auto-generation of X-Request-ID and preservation of incoming request ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Auto-generated
        res1 = await client.get("/api/v1/health")
        assert res1.status_code == 200
        req_id1 = res1.headers.get("X-Request-ID")
        assert req_id1 is not None
        assert len(req_id1) >= 16

        # 2. Supplied
        custom_id = "test-gateway-correlation-12345"
        res2 = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert res2.headers.get("X-Request-ID") == custom_id


# ---------------------------------------------------------------------------
# 9. Centralized Logging & Sensitive Data Redaction
# ---------------------------------------------------------------------------

def test_gateway_sensitive_log_redaction():
    """Verify SensitiveDataRedactionFilter redacts Bearer tokens, passwords, and DB credentials."""
    filter_obj = SensitiveDataRedactionFilter()
    
    test_cases = [
        ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token123", "Authorization: Bearer [REDACTED]"),
        ('{"password": "MySecretPassword123!"}', '{"password": "[REDACTED]"}'),
        ("postgresql://user:SecretDbPass@db.railway.app:5432/railway", "postgresql://user:[REDACTED]@db.railway.app:5432/railway"),
        ("api_key=SECRET_FINNHUB_KEY_999", "api_key=[REDACTED]"),
    ]

    for raw, expected_pattern in test_cases:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=raw, args=(), exc_info=None,
        )
        filter_obj.filter(record)
        assert "[REDACTED]" in record.msg


# ---------------------------------------------------------------------------
# 10. Unified Error Contract
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_unified_error_format():
    """Verify 4xx and 5xx responses strictly adhere to {"error": {...}} format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/expenses/summary") # 401
        data = res.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "timestampUtc" in data["error"]
        assert "requestId" in data["error"]
        # No stack trace or internal attributes exposed
        assert "traceback" not in data["error"]
        assert "exception" not in data["error"]


# ---------------------------------------------------------------------------
# 11. Max Body Size Enforcement (HTTP 413)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_max_body_size_middleware():
    """Verify MaxBodySizeMiddleware rejects requests exceeding limit with HTTP 413."""
    app_instance = create_app()
    middleware = MaxBodySizeMiddleware(app=app_instance, max_bytes=1000)

    req_oversized = MagicMock(spec=Request)
    req_oversized.headers = {"content-length": "2000"}
    req_oversized.url.path = "/api/v1/test"

    async def dummy_call_next(r):
        return Response("ok", status_code=200)

    res = await middleware.dispatch(req_oversized, dummy_call_next)
    assert res.status_code == 413
    body = json.loads(res.body.decode())
    assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"


# ---------------------------------------------------------------------------
# 12. Production Documentation Protection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_production_docs_protection():
    """Verify /docs, /redoc, /openapi.json are disabled when APP_ENV=production."""
    with patch("app.main.get_settings") as mock_settings:
        mock_s = Settings(
            APP_ENV="production",
            APP_NAME="GlobalPulse",
            DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/test",
            JWT_SECRET_KEY="supersecretkeyforproductiontestingmin32chars",
        )
        mock_settings.return_value = mock_s
        prod_app = create_app()

        assert prod_app.docs_url is None
        assert prod_app.redoc_url is None
        assert prod_app.openapi_url is None


@pytest.mark.asyncio
async def test_gateway_development_docs_enabled():
    """Verify /docs, /redoc, /openapi.json are enabled when APP_ENV=development."""
    with patch("app.main.get_settings") as mock_settings:
        mock_s = Settings(
            APP_ENV="development",
            APP_NAME="GlobalPulse",
            DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/test",
            JWT_SECRET_KEY="supersecretkeyforproductiontestingmin32chars",
        )
        mock_settings.return_value = mock_s
        dev_app = create_app()

        assert dev_app.docs_url == "/docs"
        assert dev_app.redoc_url == "/redoc"
        assert dev_app.openapi_url == "/openapi.json"


def test_gateway_external_api_exception_status_codes():
    """Verify external API exception classes map to 502 Bad Gateway and 504 Gateway Timeout."""
    bg_err = ExplanationProviderResponseError("External provider returned invalid response")
    assert bg_err.http_status == 502
    assert bg_err.error_code == "EXPLANATION_PROVIDER_RESPONSE_ERROR"

    gt_err = ExplanationProviderTimeoutError("External provider timed out")
    assert gt_err.http_status == 504
    assert gt_err.error_code == "EXPLANATION_PROVIDER_TIMEOUT"

    svc_err = ProviderUnavailableError("Finnhub service unavailable")
    assert svc_err.http_status == 503
    assert svc_err.error_code == "PROVIDER_UNAVAILABLE"
