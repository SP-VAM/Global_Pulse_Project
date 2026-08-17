"""
GlobalPulse Centralized Structured Logging (FRD-051)
Provides standardized, structured, secure, and correlation-aware logging:
  - ContextVar-based Request ID & User ID correlation across all layers.
  - Sensitive data redaction (Authorization headers, tokens, passwords, database credentials).
  - Environment-aware formatting (Text in development, Structured JSON in staging/production).
  - Production-hardened activity helpers (API requests, security events, audit activities, external APIs, database errors).
  - Resilient: Logging errors never break or crash the application.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Correlation Context Variables
# ---------------------------------------------------------------------------
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
user_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)

# ---------------------------------------------------------------------------
# Sensitive Data Redaction Patterns
# ---------------------------------------------------------------------------
_REDACTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    # HTTP Authorization headers
    (re.compile(r"(Authorization:\s*(?:Bearer|Token|Basic)\s+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
    # Standalone Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),
    # URL query parameter ?token=... or &token=... or &api_key=...
    (re.compile(r"([?&](?:token|api_key|apikey|secret|key)=)[^&\s'\",}]+", re.IGNORECASE), r"\1[REDACTED]"),
    # Generic secret keys / passwords in JSON or key=value / key: value
    (re.compile(r"((?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)[=:\s\"']+)[^&\s'\",}{]+", re.IGNORECASE), r"\1[REDACTED]"),
    # Database connection URLs with embedded credentials
    (re.compile(r"(postgres(?:ql)?(?:\+[a-z0-9]+)?://[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1[REDACTED]\3"),
    # X-API-Key header pattern
    (re.compile(r"(X-API-Key:\s*)\S+", re.IGNORECASE), r"\1[REDACTED]"),
]


class SensitiveDataRedactionFilter(logging.Filter):
    """
    Logging filter that redacts known sensitive patterns from log messages.
    Guaranteed never to raise an exception or block log emission.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            formatted: str = record.getMessage()
            for pattern, replacement in _REDACTION_PATTERNS:
                formatted = pattern.sub(replacement, formatted)
            record.msg = formatted
            record.args = ()
        except Exception:
            pass
        return True


class ContextualLoggingFilter(logging.Filter):
    """
    Logging filter that automatically attaches request_id and user_id from ContextVars.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if not hasattr(record, "request_id") or record.request_id == "-":
                record.request_id = request_id_ctx.get()
            if not hasattr(record, "user_id") or record.user_id is None:
                record.user_id = user_id_ctx.get()
            if not hasattr(record, "event"):
                record.event = getattr(record, "event", "application_log")
        except Exception:
            record.request_id = "-"
            record.user_id = None
            record.event = "application_log"
        return True


class StructuredJsonFormatter(logging.Formatter):
    """
    Machine-readable structured JSON formatter for production and staging environments.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            log_data: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "service": "globalpulse-backend",
                "logger": record.name,
                "message": record.getMessage(),
                "request_id": getattr(record, "request_id", "-") or "-",
            }

            user_id = getattr(record, "user_id", None)
            if user_id is not None:
                log_data["user_id"] = user_id

            event = getattr(record, "event", None)
            if event and event != "application_log":
                log_data["event"] = event

            # Optional extra diagnostic metadata
            for attr in ("method", "path", "status_code", "duration_ms", "error_type", "entity_type", "action"):
                val = getattr(record, attr, None)
                if val is not None:
                    log_data[attr] = val

            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_data)
        except Exception:
            # Fallback safe plain output if serialization fails
            return f"{record.asctime} | {record.levelname} | {record.name} | {record.getMessage()}"


class StructuredTextFormatter(logging.Formatter):
    """
    Human-readable structured text formatter for local development environments.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            req_id = getattr(record, "request_id", "-") or "-"
            user_id = getattr(record, "user_id", None)
            user_part = f" | user={user_id}" if user_id else ""
            event = getattr(record, "event", None)
            event_part = f" | event={event}" if event and event != "application_log" else ""

            duration = getattr(record, "duration_ms", None)
            duration_part = f" | {duration}ms" if duration is not None else ""

            status = getattr(record, "status_code", None)
            status_part = f" | status={status}" if status is not None else ""

            base = f"{self.formatTime(record, self.datefmt)} | {record.levelname:<8} | [{req_id}{user_part}] | {record.name}{event_part}{status_part}{duration_part} | {record.getMessage()}"
            if record.exc_info:
                base += f"\n{self.formatException(record.exc_info)}"
            return base
        except Exception:
            return super().format(record)


# ---------------------------------------------------------------------------
# Centralized Logging Setup
# ---------------------------------------------------------------------------


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure application-wide logging.
    Idempotent: clears existing handlers and attaches structured formatters and filters.
    """
    settings = get_settings()
    level_str = log_level or settings.LOG_LEVEL
    level = getattr(logging, level_str.upper(), logging.INFO)

    if settings.APP_ENV in ("staging", "production"):
        formatter = StructuredJsonFormatter()
    else:
        formatter = StructuredTextFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    context_filter = ContextualLoggingFilter()
    redaction_filter = SensitiveDataRedactionFilter()
    handler.addFilter(context_filter)
    handler.addFilter(redaction_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear previous handlers to prevent duplicate lines on reload
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for use in any module."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Structured Activity & Event Helpers
# ---------------------------------------------------------------------------
_app_logger = logging.getLogger("globalpulse.audit")


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[Any] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log incoming HTTP request completion with duration and status."""
    try:
        level = logging.INFO if status_code < 400 else (logging.WARNING if status_code < 500 else logging.ERROR)
        event = "api_request" if status_code < 400 else ("api_client_error" if status_code < 500 else "api_server_error")
        extra = {
            "event": event,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id or request_id_ctx.get(),
            "user_id": user_id or user_id_ctx.get(),
            **kwargs,
        }
        _app_logger.log(
            level,
            "HTTP %s %s -> %d in %.2fms",
            method,
            path,
            status_code,
            duration_ms,
            extra=extra,
        )
    except Exception:
        pass


def log_security_event(
    event_type: str,
    message: str,
    user_id: Optional[Any] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log authentication and security-critical activities."""
    try:
        extra = {
            "event": f"security.{event_type.lower()}",
            "request_id": request_id or request_id_ctx.get(),
            "user_id": user_id or user_id_ctx.get(),
            **kwargs,
        }
        _app_logger.info("[SECURITY] %s: %s", event_type, message, extra=extra)
    except Exception:
        pass


def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: Optional[Any] = None,
    user_id: Optional[Any] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log significant user activities (financial mutations, CRUD actions)."""
    try:
        extra = {
            "event": f"audit.{action.lower()}",
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "request_id": request_id or request_id_ctx.get(),
            "user_id": user_id or user_id_ctx.get(),
            **kwargs,
        }
        _app_logger.info(
            "[AUDIT] %s %s (id=%s) by user=%s",
            action,
            entity_type,
            entity_id or "-",
            user_id or user_id_ctx.get() or "-",
            extra=extra,
        )
    except Exception:
        pass


def log_external_api_call(
    service_name: str,
    endpoint: str,
    duration_ms: float,
    success: bool = True,
    status_code: Optional[int] = None,
    **kwargs: Any,
) -> None:
    """Log third-party provider or external API calls."""
    try:
        level = logging.INFO if success else logging.WARNING
        extra = {
            "event": f"external_api.{service_name.lower()}",
            "service_name": service_name,
            "endpoint": endpoint,
            "duration_ms": duration_ms,
            "status_code": status_code,
            "success": success,
            "request_id": request_id_ctx.get(),
            **kwargs,
        }
        _app_logger.log(
            level,
            "[EXTERNAL API] %s %s -> %s in %.2fms",
            service_name,
            endpoint,
            "SUCCESS" if success else "FAILED",
            duration_ms,
            extra=extra,
        )
    except Exception:
        pass


def log_database_error(operation: str, table: str, error: Exception, **kwargs: Any) -> None:
    """Log database exceptions and transactional failures without exposing sensitive data."""
    try:
        extra = {
            "event": "database.error",
            "operation": operation,
            "table": table,
            "error_type": type(error).__name__,
            "request_id": request_id_ctx.get(),
            **kwargs,
        }
        _app_logger.error(
            "[DATABASE ERROR] %s on %s failed: %s",
            operation,
            table,
            type(error).__name__,
            extra=extra,
        )
    except Exception:
        pass
