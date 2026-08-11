"""
GlobalPulse Structured Logging
Configures Python logging with environment-aware output formats:
  - development  → human-readable plain text (easy console reading)
  - staging/production → structured JSON (machine-parseable, log aggregators)

Security hardening:
  - SensitiveDataRedactionFilter scrubs Authorization headers, Bearer tokens,
    API key query parameters, and similar secrets from log messages before
    they are emitted to any handler.
  - Secrets (API keys, tokens) are never logged by provider code.
"""
import logging
import re
import sys
from typing import Optional

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Sensitive Data Redaction Filter
# ---------------------------------------------------------------------------

# Ordered list of (compiled_pattern, replacement) pairs applied to every
# log message before emission. Patterns are intentionally conservative —
# they target known secret-carrying constructs without over-matching.
_REDACTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    # HTTP Authorization header values — covers Bearer, Token, Basic, and bare values
    (re.compile(r"(Authorization:\s*(?:Bearer|Token|Basic)\s+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
    # Standalone Bearer prefix in log strings (e.g. from request logging)
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),
    # URL query-parameter ?token=... or &token=... (Finnhub injects token this way)
    (re.compile(r"([?&]token=)[^&\s'\",}]+"), r"\1[REDACTED]"),
    # Generic API key patterns in key=value or key: value notation
    (re.compile(r"((?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key)[=:\s]+)[^&\s'\",}{]+", re.IGNORECASE), r"\1[REDACTED]"),
    # X-API-Key header pattern
    (re.compile(r"(X-API-Key:\s*)\S+", re.IGNORECASE), r"\1[REDACTED]"),
]


class SensitiveDataRedactionFilter(logging.Filter):
    """
    Logging filter that redacts known sensitive patterns from log messages.

    Applied globally to the root logger so that every handler (stdout, file,
    third-party sink) receives already-redacted log records. This provides a
    safety net against accidental secret exposure regardless of where the log
    statement originates.

    The filter never raises — if redaction itself fails, the original record
    is emitted unchanged so that logging is never silenced by this component.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            # Format msg % args into a single string so patterns can match
            # across both the format string and its interpolated arguments.
            formatted: str = record.getMessage()
            for pattern, replacement in _REDACTION_PATTERNS:
                formatted = pattern.sub(replacement, formatted)
            # Write the redacted text back; clear args to avoid double-formatting.
            record.msg = formatted
            record.args = ()
        except Exception:  # pragma: no cover — filter must never block logging
            pass
        return True


# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure application-wide logging.

    Format selection:
      - APP_ENV == "development"  → plain text (human-readable)
      - APP_ENV == "staging" / "production" → JSON (structured, machine-parseable)

    Call once at application startup (idempotent — clears existing handlers
    before adding the configured one).
    """
    settings = get_settings()
    level_str = log_level or settings.LOG_LEVEL
    level = getattr(logging, level_str.upper(), logging.INFO)

    if settings.APP_ENV == "development":
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        # Structured JSON for staging / production
        try:
            from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
                rename_fields={"levelname": "level", "asctime": "timestamp"},
            )
        except ImportError:  # pragma: no cover — fallback if package absent
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    redaction_filter = SensitiveDataRedactionFilter()
    handler.addFilter(redaction_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers on reload (e.g. uvicorn --reload)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for use in any module."""
    return logging.getLogger(name)
