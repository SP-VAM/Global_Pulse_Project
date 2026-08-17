"""
GlobalPulse Security Middleware
Provides three hardening middleware components:

  SecurityHeadersMiddleware  — adds defensive HTTP response headers
  MaxBodySizeMiddleware      — enforces configurable request body size limit
  RequestIDMiddleware        — generates / echoes X-Request-ID for tracing
"""
from __future__ import annotations

import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-critical HTTP response headers to every response.

    Headers applied:
      X-Content-Type-Options     — prevent MIME-type sniffing
      X-Frame-Options            — prevent clickjacking (deny all framing)
      X-XSS-Protection           — legacy XSS filter hint (Belt & suspenders)
      Referrer-Policy            — limit referrer leakage to same origin
      Permissions-Policy         — deny access to sensitive browser APIs
      Strict-Transport-Security  — enforce HTTPS (production only)

    Args:
        app_env: The value of APP_ENV. HSTS is only sent in non-development
                 environments to avoid HTTPS-pinning local dev traffic.
    """

    def __init__(self, app: ASGIApp, app_env: str = "development") -> None:
        super().__init__(app)
        self._app_env = app_env

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        if self._app_env != "development":
            # HSTS — tell browsers to only use HTTPS for the next 2 years.
            # includeSubDomains covers any future subdomains.
            # NOTE: Only set after confirming TLS is terminated at your ingress.
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response


# ---------------------------------------------------------------------------
# Max Body Size Middleware
# ---------------------------------------------------------------------------


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """
    Rejects incoming requests whose Content-Length exceeds ``max_bytes``.

    Reads only the Content-Length header — does NOT buffer the request body —
    so the check is O(1) and does not delay normal request processing.

    Returns HTTP 413 Payload Too Large with a structured JSON error body
    that is consistent with the GlobalPulse error schema.

    Args:
        max_bytes: Maximum allowed Content-Length in bytes.
                   Defaults to 1 MB (1_048_576). Configure via
                   settings.MAX_BODY_SIZE_BYTES.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = 1_048_576) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        content_length_header = request.headers.get("content-length")
        if content_length_header is not None:
            try:
                content_length = int(content_length_header)
            except ValueError:
                # Malformed Content-Length — let FastAPI handle it
                content_length = 0

            if content_length > self._max_bytes:
                logger.warning(
                    "Request body too large | size=%d bytes | limit=%d bytes | path=%s",
                    content_length,
                    self._max_bytes,
                    request.url.path,
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": (
                                f"Request body exceeds the maximum allowed size of "
                                f"{self._max_bytes // 1024} KB."
                            ),
                        }
                    },
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------


import time
from app.core.logging import log_api_request, request_id_ctx


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request and response carries an ``X-Request-ID`` header
    and automatically logs structured request/response events.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        t0 = time.time()

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            duration_ms = round((time.time() - t0) * 1000, 2)
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
            )
            return response
        except Exception as exc:
            duration_ms = round((time.time() - t0) * 1000, 2)
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                request_id=request_id,
                error=type(exc).__name__,
            )
            raise
        finally:
            request_id_ctx.reset(token)
