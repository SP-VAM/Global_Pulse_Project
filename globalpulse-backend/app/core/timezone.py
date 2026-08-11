"""
GlobalPulse Timezone Service
IANA-aware timezone conversions using Python's zoneinfo module.
All returned datetimes are timezone-aware.
No fixed offsets are ever manually applied.
DST is handled automatically by zoneinfo.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Canonical Timezone Constants
# ---------------------------------------------------------------------------

TZ_UTC = timezone.utc
TZ_IST = ZoneInfo("Asia/Kolkata")

# Exchange timezone registry
EXCHANGE_TIMEZONES: dict[str, ZoneInfo] = {
    "Asia/Kolkata": ZoneInfo("Asia/Kolkata"),
    "Asia/Singapore": ZoneInfo("Asia/Singapore"),
    "Asia/Tokyo": ZoneInfo("Asia/Tokyo"),
    "Asia/Hong_Kong": ZoneInfo("Asia/Hong_Kong"),
    "America/New_York": ZoneInfo("America/New_York"),
    "Europe/London": ZoneInfo("Europe/London"),
    "Europe/Berlin": ZoneInfo("Europe/Berlin"),
    "Europe/Paris": ZoneInfo("Europe/Paris"),
}


# ---------------------------------------------------------------------------
# TimezoneService
# ---------------------------------------------------------------------------


class TimezoneService:
    """
    Reusable timezone conversion service for GlobalPulse.

    Canonical flow:
        SOURCE TIME → UTC (canonical) → IST (user representation)

    All datetimes returned are timezone-aware.
    DST transitions are handled automatically by zoneinfo — no hard-coded offsets.
    """

    @staticmethod
    def now_utc() -> datetime:
        """Return current time in UTC (timezone-aware)."""
        return datetime.now(tz=TZ_UTC)

    @staticmethod
    def now_ist() -> datetime:
        """Return current time in IST (timezone-aware)."""
        return datetime.now(tz=TZ_IST)

    @staticmethod
    def utc_to_ist(dt: datetime) -> datetime:
        """
        Convert a UTC datetime to IST (Asia/Kolkata).

        Args:
            dt: A timezone-aware datetime in UTC.

        Returns:
            Timezone-aware datetime in IST.
        """
        if dt.tzinfo is None:
            raise ValueError("Input datetime must be timezone-aware.")
        utc_dt = dt.astimezone(TZ_UTC)
        return utc_dt.astimezone(TZ_IST)

    @staticmethod
    def local_to_utc(dt: datetime, tz_name: str) -> datetime:
        """
        Convert a naive or local datetime in a named IANA timezone to UTC.

        Args:
            dt: Datetime (naive or aware) in the exchange's local timezone.
            tz_name: IANA timezone string e.g. 'America/New_York'.

        Returns:
            Timezone-aware datetime in UTC.
        """
        tz = TimezoneService._resolve_tz(tz_name)
        if dt.tzinfo is None:
            # Attach the exchange timezone (zoneinfo handles DST automatically)
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        return dt.astimezone(TZ_UTC)

    @staticmethod
    def utc_to_local(dt: datetime, tz_name: str) -> datetime:
        """
        Convert a UTC datetime to the named IANA timezone.

        Args:
            dt: A timezone-aware datetime in UTC.
            tz_name: IANA timezone string e.g. 'Asia/Singapore'.

        Returns:
            Timezone-aware datetime in the requested local timezone.
        """
        if dt.tzinfo is None:
            raise ValueError("Input datetime must be timezone-aware.")
        tz = TimezoneService._resolve_tz(tz_name)
        return dt.astimezone(tz)

    @staticmethod
    def now_in_exchange(tz_name: str) -> datetime:
        """
        Return the current local time in a specific exchange timezone.

        Args:
            tz_name: IANA timezone string e.g. 'Asia/Tokyo'.

        Returns:
            Timezone-aware datetime in the exchange's local timezone.
        """
        tz = TimezoneService._resolve_tz(tz_name)
        return datetime.now(tz=tz)

    @staticmethod
    def _resolve_tz(tz_name: str) -> ZoneInfo:
        """Resolve an IANA timezone name to a ZoneInfo instance."""
        # Use cached instances where possible
        if tz_name in EXCHANGE_TIMEZONES:
            return EXCHANGE_TIMEZONES[tz_name]
        try:
            zi = ZoneInfo(tz_name)
            EXCHANGE_TIMEZONES[tz_name] = zi  # cache for reuse
            return zi
        except ZoneInfoNotFoundError:
            raise ValueError(
                f"Unknown IANA timezone: '{tz_name}'. "
                "Ensure tzdata is installed: pip install tzdata"
            )
