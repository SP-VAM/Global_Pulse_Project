"""
GlobalPulse Domain & Provider Exceptions
Centralized exception hierarchy and FastAPI global handlers.
Stack traces are never exposed to API consumers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain Exceptions
# ---------------------------------------------------------------------------


class GlobalPulseError(Exception):
    """Base exception for all GlobalPulse domain errors."""

    error_code: str = "INTERNAL_ERROR"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ProviderUnavailableError(GlobalPulseError):
    """Raised when a market-data provider is unreachable or returns unexpected data."""

    error_code = "PROVIDER_UNAVAILABLE"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


class ProviderRateLimitError(GlobalPulseError):
    """Raised when the provider responds with HTTP 429 Too Many Requests."""

    error_code = "PROVIDER_RATE_LIMIT"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


class ProviderAuthenticationError(GlobalPulseError):
    """Raised when the provider rejects the API key (HTTP 401 Unauthorized)."""

    error_code = "PROVIDER_AUTHENTICATION_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY


class ProviderFeatureUnavailableError(GlobalPulseError):
    """
    Raised when the provider returns HTTP 403 Forbidden.

    This is distinct from ProviderAuthenticationError (401).
    A 403 typically means the API key is valid but the requested feature,
    endpoint, or data range is not available under the configured subscription plan.

    Callers should treat this as a plan-restriction rather than an auth failure.
    """

    error_code = "PROVIDER_FEATURE_UNAVAILABLE"
    http_status = status.HTTP_403_FORBIDDEN


class InstrumentNotFoundError(GlobalPulseError):
    """Raised when a requested instrument/symbol cannot be found via the provider."""

    error_code = "INSTRUMENT_NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND


class InvalidExchangeError(GlobalPulseError):
    """Raised when an unknown or unsupported exchange code is requested."""

    error_code = "INVALID_EXCHANGE"
    http_status = status.HTTP_404_NOT_FOUND


class NotFoundError(GlobalPulseError):
    """Raised when a requested resource is not found."""

    error_code = "NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND



class ValidationError(GlobalPulseError):
    """Raised when request parameters fail domain-level validation."""


    error_code = "VALIDATION_ERROR"
    http_status = status.HTTP_422_UNPROCESSABLE_CONTENT


class AuthenticationError(GlobalPulseError):
    """Raised when credentials or token fail authentication."""

    error_code = "AUTHENTICATION_ERROR"
    http_status = status.HTTP_401_UNAUTHORIZED


class DuplicateRecordError(GlobalPulseError):
    """Raised when an operation violates a unique database constraint."""

    error_code = "DUPLICATE_RECORD"
    http_status = status.HTTP_409_CONFLICT


class DatabaseConnectionError(GlobalPulseError):
    """Raised when database connectivity fails."""

    error_code = "DATABASE_ERROR"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Explanation Provider Exceptions (Phase 5)
# ---------------------------------------------------------------------------


class ExplanationProviderError(GlobalPulseError):
    """Base exception for external explanation provider failures (eligible for fallback)."""

    error_code = "EXPLANATION_PROVIDER_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY


class ExplanationProviderTimeoutError(ExplanationProviderError):
    """Raised when an external LLM explanation provider request times out."""

    error_code = "EXPLANATION_PROVIDER_TIMEOUT"
    http_status = status.HTTP_504_GATEWAY_TIMEOUT


class ExplanationProviderRateLimitError(ExplanationProviderError):
    """Raised when an external LLM explanation provider returns HTTP 429 Rate Limit."""

    error_code = "EXPLANATION_PROVIDER_RATE_LIMIT"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


class ExplanationProviderAuthError(ExplanationProviderError):
    """Raised when external LLM credentials/API keys are missing or invalid."""

    error_code = "EXPLANATION_PROVIDER_AUTH_ERROR"
    http_status = status.HTTP_401_UNAUTHORIZED


class ExplanationProviderResponseError(ExplanationProviderError):
    """Raised when an external LLM provider returns malformed or invalid JSON output."""

    error_code = "EXPLANATION_PROVIDER_RESPONSE_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY


# ---------------------------------------------------------------------------
# Standard Error Response Builder
# ---------------------------------------------------------------------------


def _error_response(code: str, message: str, http_status: int, request: Optional[Request] = None) -> JSONResponse:
    content: dict = {
        "error": {
            "code": code,
            "message": message,
            "timestampUtc": datetime.now(timezone.utc).isoformat(),
        }
    }
    if request and hasattr(request, "state") and hasattr(request.state, "request_id"):
        content["error"]["requestId"] = request.state.request_id

    return JSONResponse(
        status_code=http_status,
        content=content,
    )


# ---------------------------------------------------------------------------
# FastAPI Exception Handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI application."""

    @app.exception_handler(GlobalPulseError)
    async def globalpulse_error_handler(
        request: Request, exc: GlobalPulseError
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "-") if hasattr(request, "state") else "-"
        logger.error(
            "Domain error [%s]: %s | path=%s",
            exc.error_code,
            exc.message,
            request.url.path,
            extra={"event": "domain_error", "error_code": exc.error_code, "request_id": req_id, "path": request.url.path},
        )
        return _error_response(exc.error_code, exc.message, exc.http_status, request=request)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "-") if hasattr(request, "state") else "-"
        level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        logger.log(
            level,
            "HTTP exception %d at %s: %s",
            exc.status_code,
            request.url.path,
            exc.detail,
            extra={"event": "http_exception", "status_code": exc.status_code, "request_id": req_id, "path": request.url.path},
        )
        return _error_response(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            http_status=exc.status_code,
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "-") if hasattr(request, "state") else "-"
        errors = exc.errors()
        first_msg = errors[0].get("msg", "Validation error") if errors else "Invalid request body or parameters."
        field = ".".join(str(x) for x in errors[0].get("loc", []) if x not in ("body",)) if errors else ""
        clean_msg = f"{field}: {first_msg}" if field else first_msg

        logger.warning(
            "Request validation error at %s: %s",
            request.url.path,
            clean_msg,
            extra={"event": "validation_error", "request_id": req_id, "path": request.url.path},
        )
        return _error_response(
            code="VALIDATION_ERROR",
            message=clean_msg,
            http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            request=request,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "-") if hasattr(request, "state") else "-"
        logger.exception(
            "Unhandled exception at %s: %s",
            request.url.path,
            type(exc).__name__,
            extra={"event": "unhandled_exception", "request_id": req_id, "error_type": type(exc).__name__, "path": request.url.path},
        )
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again later.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            request=request,
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(
            "NOT_FOUND",
            f"The requested path '{request.url.path}' does not exist.",
            status.HTTP_404_NOT_FOUND,
            request=request,
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return _error_response(
            "METHOD_NOT_ALLOWED",
            f"Method '{request.method}' is not allowed on '{request.url.path}'.",
            status.HTTP_405_METHOD_NOT_ALLOWED,
            request=request,
        )
