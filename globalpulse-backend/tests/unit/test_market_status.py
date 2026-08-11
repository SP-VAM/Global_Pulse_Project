"""
Phase 1C — Market Status tests.
Tests OPEN/CLOSED logic for different weekday/time scenarios.
Uses unittest.mock.patch to control the current UTC time.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from httpx import AsyncClient


# Helper: create a UTC datetime
def utc(year, month, day, hour, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# All exchanges endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_market_statuses_returns_list(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market-status")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 10


@pytest.mark.asyncio
async def test_all_market_statuses_have_required_fields(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market-status")
    for item in response.json():
        assert "exchange" in item
        assert "country" in item
        assert "session_status" in item
        assert "holiday_calendar_applied" in item
        assert "exchange_local_time" in item
        assert "current_time_utc" in item
        assert "current_time_ist" in item


@pytest.mark.asyncio
async def test_holiday_calendar_applied_is_false(client: AsyncClient) -> None:
    """Phase 1C: holiday_calendar_applied must always be false."""
    response = await client.get("/api/v1/market-status")
    for item in response.json():
        assert item["holiday_calendar_applied"] is False, (
            f"{item['exchange']}: holiday_calendar_applied should be False"
        )


# ---------------------------------------------------------------------------
# Single exchange endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_nse_status(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market-status/NSE")
    assert response.status_code == 200
    body = response.json()
    assert body["exchange"] == "NSE"
    assert body["country"] == "India"
    assert body["session_status"] in ("OPEN", "CLOSED")


@pytest.mark.asyncio
async def test_invalid_exchange_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market-status/INVALID_EXCHANGE")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "INVALID_EXCHANGE"


@pytest.mark.asyncio
async def test_exchange_code_case_insensitive(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market-status/sgx")
    assert response.status_code == 200
    assert response.json()["exchange"] == "SGX"


# ---------------------------------------------------------------------------
# OPEN/CLOSED logic — NSE (Asia/Kolkata, 09:15–15:30)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nse_open_during_session(client: AsyncClient) -> None:
    """
    NSE session: 09:15–15:30 IST = 03:45–10:00 UTC.
    Mock UTC at 06:00 on a Tuesday (within NSE session window).
    """
    mock_now = utc(2024, 6, 11, 6, 0)  # Tuesday, 06:00 UTC = 11:30 IST
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NSE")
    assert response.json()["session_status"] == "OPEN"


@pytest.mark.asyncio
async def test_nse_closed_before_open(client: AsyncClient) -> None:
    """
    Before NSE open: UTC 01:00 on a Tuesday = IST 06:30 (before 09:15 open).
    """
    mock_now = utc(2024, 6, 11, 1, 0)  # Tuesday, 01:00 UTC = 06:30 IST
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NSE")
    assert response.json()["session_status"] == "CLOSED"


@pytest.mark.asyncio
async def test_nse_closed_after_session(client: AsyncClient) -> None:
    """
    After NSE close: UTC 12:00 on a Tuesday = IST 17:30 (after 15:30 close).
    """
    mock_now = utc(2024, 6, 11, 12, 0)  # Tuesday, 12:00 UTC = 17:30 IST
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NSE")
    assert response.json()["session_status"] == "CLOSED"


@pytest.mark.asyncio
async def test_nse_closed_on_weekend(client: AsyncClient) -> None:
    """
    Saturday UTC = no trading day for NSE.
    2024-06-15 = Saturday.
    """
    mock_now = utc(2024, 6, 15, 6, 0)  # Saturday
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NSE")
    assert response.json()["session_status"] == "CLOSED"


# ---------------------------------------------------------------------------
# NYSE (America/New_York, 09:30–16:00) — DST-aware
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nyse_open_edt_summer(client: AsyncClient) -> None:
    """
    NYSE summer (EDT = UTC-4). NYSE open = 09:30 EDT = 13:30 UTC.
    Mock UTC at 15:00 on a Wednesday in July (within session).
    """
    mock_now = utc(2024, 7, 10, 15, 0)  # Wednesday, 15:00 UTC = 11:00 EDT
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NYSE")
    assert response.json()["session_status"] == "OPEN"


@pytest.mark.asyncio
async def test_nyse_closed_edt_before_open(client: AsyncClient) -> None:
    """
    NYSE summer (EDT = UTC-4). Before open. UTC 10:00 = 06:00 EDT (before 09:30).
    """
    mock_now = utc(2024, 7, 10, 10, 0)  # Wednesday, 10:00 UTC = 06:00 EDT
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NYSE")
    assert response.json()["session_status"] == "CLOSED"


@pytest.mark.asyncio
async def test_nyse_open_est_winter(client: AsyncClient) -> None:
    """
    NYSE winter (EST = UTC-5). NYSE open = 09:30 EST = 14:30 UTC.
    Mock UTC at 16:00 on a Wednesday in January (within session).
    """
    mock_now = utc(2024, 1, 10, 16, 0)  # Wednesday, 16:00 UTC = 11:00 EST
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NYSE")
    assert response.json()["session_status"] == "OPEN"


# ---------------------------------------------------------------------------
# next_open / next_close fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_closed_market_has_next_open(client: AsyncClient) -> None:
    """When CLOSED, next_open_utc and next_open_ist should be populated."""
    mock_now = utc(2024, 6, 15, 6, 0)  # Saturday
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NSE")
    body = response.json()
    assert body["session_status"] == "CLOSED"
    assert body["next_open_utc"] is not None
    assert body["next_open_ist"] is not None
    assert body["next_close_utc"] is None  # Not applicable when closed
    assert body["next_close_ist"] is None


@pytest.mark.asyncio
async def test_open_market_has_next_close(client: AsyncClient) -> None:
    """When OPEN, next_close_utc and next_close_ist should be populated."""
    mock_now = utc(2024, 6, 11, 6, 0)  # Tuesday, NSE open
    with patch("app.services.market_status_service.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        response = await client.get("/api/v1/market-status/NSE")
    body = response.json()
    assert body["session_status"] == "OPEN"
    assert body["next_close_utc"] is not None
    assert body["next_close_ist"] is not None
    assert body["next_open_utc"] is None
    assert body["next_open_ist"] is None
