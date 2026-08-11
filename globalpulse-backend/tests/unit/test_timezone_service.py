"""
Phase 1C — TimezoneService tests.
Tests UTC/IST conversions and DST-sensitive dates.
No live API calls.
"""
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.timezone import TimezoneService

TZ_UTC = timezone.utc
TZ_IST = ZoneInfo("Asia/Kolkata")
TZ_SGT = ZoneInfo("Asia/Singapore")
TZ_JST = ZoneInfo("Asia/Tokyo")
TZ_HKT = ZoneInfo("Asia/Hong_Kong")
TZ_ET  = ZoneInfo("America/New_York")
TZ_GMT = ZoneInfo("Europe/London")


# ---------------------------------------------------------------------------
# UTC → IST
# ---------------------------------------------------------------------------

def test_utc_to_ist_basic() -> None:
    """IST = UTC + 5:30 (fixed offset, no DST)."""
    utc_dt = datetime(2024, 6, 15, 10, 0, 0, tzinfo=TZ_UTC)
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 15
    assert ist_dt.minute == 30
    assert str(ist_dt.tzinfo) == "Asia/Kolkata"


def test_utc_to_ist_midnight_rollover() -> None:
    utc_dt = datetime(2024, 1, 15, 20, 0, 0, tzinfo=TZ_UTC)
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    # 20:00 UTC → 01:30 IST next day
    assert ist_dt.day == 16
    assert ist_dt.hour == 1
    assert ist_dt.minute == 30


def test_utc_to_ist_naive_raises() -> None:
    naive_dt = datetime(2024, 1, 15, 10, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        TimezoneService.utc_to_ist(naive_dt)


# ---------------------------------------------------------------------------
# Singapore → UTC → IST
# ---------------------------------------------------------------------------

def test_singapore_to_utc() -> None:
    """SGT = UTC+8. Singapore 09:00 → UTC 01:00."""
    sgt_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=TZ_SGT)
    utc_dt = TimezoneService.local_to_utc(sgt_dt, "Asia/Singapore")
    assert utc_dt.hour == 1
    assert utc_dt.minute == 0
    assert utc_dt.tzinfo == TZ_UTC


def test_singapore_to_ist() -> None:
    """SGT → UTC → IST: SGT 09:00 → IST 06:30."""
    sgt_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=TZ_SGT)
    utc_dt = TimezoneService.local_to_utc(sgt_dt, "Asia/Singapore")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 6
    assert ist_dt.minute == 30


# ---------------------------------------------------------------------------
# Tokyo → UTC → IST
# ---------------------------------------------------------------------------

def test_tokyo_to_utc() -> None:
    """JST = UTC+9. Tokyo 09:00 → UTC 00:00."""
    jst_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=TZ_JST)
    utc_dt = TimezoneService.local_to_utc(jst_dt, "Asia/Tokyo")
    assert utc_dt.hour == 0
    assert utc_dt.minute == 0


def test_tokyo_to_ist() -> None:
    """JST 09:00 → UTC 00:00 → IST 05:30."""
    jst_dt = datetime(2024, 6, 15, 9, 0, 0, tzinfo=TZ_JST)
    utc_dt = TimezoneService.local_to_utc(jst_dt, "Asia/Tokyo")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 5
    assert ist_dt.minute == 30


# ---------------------------------------------------------------------------
# Hong Kong → UTC → IST
# ---------------------------------------------------------------------------

def test_hongkong_to_utc() -> None:
    """HKT = UTC+8. HK 09:30 → UTC 01:30."""
    hkt_dt = datetime(2024, 6, 15, 9, 30, 0, tzinfo=TZ_HKT)
    utc_dt = TimezoneService.local_to_utc(hkt_dt, "Asia/Hong_Kong")
    assert utc_dt.hour == 1
    assert utc_dt.minute == 30


def test_hongkong_to_ist() -> None:
    """HKT 09:30 → UTC 01:30 → IST 07:00."""
    hkt_dt = datetime(2024, 6, 15, 9, 30, 0, tzinfo=TZ_HKT)
    utc_dt = TimezoneService.local_to_utc(hkt_dt, "Asia/Hong_Kong")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 7
    assert ist_dt.minute == 0


# ---------------------------------------------------------------------------
# New York → UTC → IST  (DST-sensitive)
# ---------------------------------------------------------------------------

def test_new_york_to_utc_est_winter() -> None:
    """EST = UTC-5. January (no DST). NY 09:30 → UTC 14:30."""
    ny_dt = datetime(2024, 1, 15, 9, 30, 0, tzinfo=TZ_ET)
    utc_dt = TimezoneService.local_to_utc(ny_dt, "America/New_York")
    assert utc_dt.hour == 14
    assert utc_dt.minute == 30


def test_new_york_to_utc_edt_summer() -> None:
    """EDT = UTC-4. July (DST active). NY 09:30 → UTC 13:30."""
    ny_dt = datetime(2024, 7, 15, 9, 30, 0, tzinfo=TZ_ET)
    utc_dt = TimezoneService.local_to_utc(ny_dt, "America/New_York")
    assert utc_dt.hour == 13
    assert utc_dt.minute == 30


def test_new_york_dst_spring_forward() -> None:
    """2024 US DST spring-forward: 2024-03-10 02:00 → clocks spring to 03:00."""
    # Before spring-forward (still EST=UTC-5)
    ny_before = datetime(2024, 3, 10, 1, 0, 0, tzinfo=TZ_ET)
    utc_before = TimezoneService.local_to_utc(ny_before, "America/New_York")
    assert utc_before.hour == 6  # 01:00 EST → 06:00 UTC

    # After spring-forward (EDT=UTC-4)
    ny_after = datetime(2024, 3, 10, 10, 0, 0, tzinfo=TZ_ET)
    utc_after = TimezoneService.local_to_utc(ny_after, "America/New_York")
    assert utc_after.hour == 14  # 10:00 EDT → 14:00 UTC


def test_new_york_dst_fall_back() -> None:
    """2024 US DST fall-back: 2024-11-03 02:00 → clocks fall back to 01:00."""
    # After fall-back (EST=UTC-5)
    ny_after = datetime(2024, 11, 3, 12, 0, 0, tzinfo=TZ_ET)
    utc_after = TimezoneService.local_to_utc(ny_after, "America/New_York")
    assert utc_after.hour == 17  # 12:00 EST → 17:00 UTC


def test_new_york_to_ist_est() -> None:
    """EST: NY 09:30 → UTC 14:30 → IST 20:00."""
    ny_dt = datetime(2024, 1, 15, 9, 30, 0, tzinfo=TZ_ET)
    utc_dt = TimezoneService.local_to_utc(ny_dt, "America/New_York")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 20
    assert ist_dt.minute == 0


def test_new_york_to_ist_edt() -> None:
    """EDT: NY 09:30 → UTC 13:30 → IST 19:00."""
    ny_dt = datetime(2024, 7, 15, 9, 30, 0, tzinfo=TZ_ET)
    utc_dt = TimezoneService.local_to_utc(ny_dt, "America/New_York")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 19
    assert ist_dt.minute == 0


# ---------------------------------------------------------------------------
# London → UTC → IST  (DST-sensitive)
# ---------------------------------------------------------------------------

def test_london_to_utc_gmt_winter() -> None:
    """GMT = UTC+0. January. London 08:00 → UTC 08:00."""
    lon_dt = datetime(2024, 1, 15, 8, 0, 0, tzinfo=TZ_GMT)
    utc_dt = TimezoneService.local_to_utc(lon_dt, "Europe/London")
    assert utc_dt.hour == 8
    assert utc_dt.minute == 0


def test_london_to_utc_bst_summer() -> None:
    """BST = UTC+1. July (DST active). London 08:00 → UTC 07:00."""
    lon_dt = datetime(2024, 7, 15, 8, 0, 0, tzinfo=TZ_GMT)
    utc_dt = TimezoneService.local_to_utc(lon_dt, "Europe/London")
    assert utc_dt.hour == 7
    assert utc_dt.minute == 0


def test_london_dst_spring_forward() -> None:
    """2024 UK BST begins: 2024-03-31 01:00 → clocks spring to 02:00."""
    # Before BST (GMT=UTC+0)
    lon_before = datetime(2024, 3, 30, 8, 0, 0, tzinfo=TZ_GMT)
    utc_before = TimezoneService.local_to_utc(lon_before, "Europe/London")
    assert utc_before.hour == 8  # GMT: London 08:00 = UTC 08:00

    # After BST (UTC+1)
    lon_after = datetime(2024, 4, 1, 8, 0, 0, tzinfo=TZ_GMT)
    utc_after = TimezoneService.local_to_utc(lon_after, "Europe/London")
    assert utc_after.hour == 7  # BST: London 08:00 = UTC 07:00


def test_london_to_ist_gmt() -> None:
    """GMT: London 08:00 → UTC 08:00 → IST 13:30."""
    lon_dt = datetime(2024, 1, 15, 8, 0, 0, tzinfo=TZ_GMT)
    utc_dt = TimezoneService.local_to_utc(lon_dt, "Europe/London")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 13
    assert ist_dt.minute == 30


def test_london_to_ist_bst() -> None:
    """BST: London 08:00 → UTC 07:00 → IST 12:30."""
    lon_dt = datetime(2024, 7, 15, 8, 0, 0, tzinfo=TZ_GMT)
    utc_dt = TimezoneService.local_to_utc(lon_dt, "Europe/London")
    ist_dt = TimezoneService.utc_to_ist(utc_dt)
    assert ist_dt.hour == 12
    assert ist_dt.minute == 30


# ---------------------------------------------------------------------------
# now_in_exchange
# ---------------------------------------------------------------------------

def test_now_in_exchange_is_timezone_aware() -> None:
    dt = TimezoneService.now_in_exchange("Asia/Singapore")
    assert dt.tzinfo is not None


def test_now_in_exchange_correct_tz() -> None:
    dt = TimezoneService.now_in_exchange("Asia/Tokyo")
    assert "Tokyo" in str(dt.tzinfo) or "Japan" in str(dt.tzinfo)


def test_invalid_timezone_raises() -> None:
    with pytest.raises(ValueError, match="Unknown IANA timezone"):
        TimezoneService._resolve_tz("Not/A/Timezone")
