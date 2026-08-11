"""Shared datetime utility helpers."""
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def to_iso(dt: datetime) -> str:
    """Convert a timezone-aware datetime to ISO 8601 string."""
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.isoformat()
