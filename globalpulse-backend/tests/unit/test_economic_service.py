"""
Unit tests for EconomicService
Tests date validation, IST boundary computation, and provider delegation.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.domain.economic_event import (
    EconomicEventCategory,
    EconomicImportance,
    NormalizedEconomicEvent,
)
from app.services.economic_service import EconomicService


def _make_event(country="US", category=EconomicEventCategory.INTEREST_RATE):
    return NormalizedEconomicEvent(
        id="evt-001",
        country=country,
        event="Test Event",
        category=category,
        importance=EconomicImportance.HIGH,
        actual=5.5,
        forecast=5.5,
        previous=5.0,
        unit="%",
        timestamp_utc="2024-01-26T14:00:00+00:00",
        timestamp_ist="2024-01-26T19:30:00+05:30",
        source="TRADING_ECONOMICS",
    )


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.get_calendar = AsyncMock(return_value=[_make_event()])
    provider.get_commodities = AsyncMock(return_value=[])
    provider.get_forex = AsyncMock(return_value=[])
    provider.get_bond_yields = AsyncMock(return_value=[])
    return provider


@pytest.fixture
def service(mock_provider):
    return EconomicService(provider=mock_provider)


class TestGetEconomicEvents:
    @pytest.mark.asyncio
    async def test_delegates_to_provider(self, service, mock_provider):
        result = await service.get_economic_events()
        mock_provider.get_calendar.assert_called_once()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_invalid_date_range_raises(self, service):
        with pytest.raises(ValidationError):
            await service.get_economic_events(
                from_date=date(2024, 2, 1),
                to_date=date(2024, 1, 1),  # to < from
            )

    @pytest.mark.asyncio
    async def test_date_range_exceeds_max_raises(self, service):
        with pytest.raises(ValidationError):
            await service.get_economic_events(
                from_date=date(2024, 1, 1),
                to_date=date(2024, 6, 1),  # > 90 days
            )

    @pytest.mark.asyncio
    async def test_valid_date_range_accepted(self, service, mock_provider):
        await service.get_economic_events(
            from_date=date(2024, 1, 1),
            to_date=date(2024, 3, 1),  # ~60 days, within limit
        )
        mock_provider.get_calendar.assert_called_once()

    @pytest.mark.asyncio
    async def test_category_enum_converted_to_string(self, service, mock_provider):
        await service.get_economic_events(category=EconomicEventCategory.INTEREST_RATE)
        call_kwargs = mock_provider.get_calendar.call_args[1]
        assert call_kwargs.get("category") == "INTEREST_RATE"


class TestGetEconomicEventsToday:
    @pytest.mark.asyncio
    async def test_calls_provider_with_today_ist_range(self, service, mock_provider):
        """Today in IST should result in a UTC date range being passed to provider."""
        await service.get_economic_events_today()
        mock_provider.get_calendar.assert_called_once()

        call_kwargs = mock_provider.get_calendar.call_args[1]
        # from_date and to_date should be date objects
        assert call_kwargs.get("from_date") is not None
        assert call_kwargs.get("to_date") is not None
        # IST is UTC+5:30, so IST start (00:00) = UTC previous day 18:30
        # The UTC dates should differ or be same
        from_d = call_kwargs["from_date"]
        to_d = call_kwargs["to_date"]
        assert isinstance(from_d, date)
        assert isinstance(to_d, date)
        assert from_d <= to_d

    @pytest.mark.asyncio
    async def test_ist_boundary_uses_kolkata_timezone(self, service, mock_provider):
        """
        Verify that the IST day boundary is computed using Asia/Kolkata,
        not a fixed +05:30 offset.
        """
        from app.core.timezone import TimezoneService
        with patch.object(TimezoneService, "now_ist") as mock_now:
            # Simulate IST midnight scenario
            from zoneinfo import ZoneInfo
            mock_now.return_value = datetime(2024, 7, 15, 0, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
            await service.get_economic_events_today()

        call_kwargs = mock_provider.get_calendar.call_args[1]
        # IST 2024-07-15 → UTC 2024-07-14 (18:30 prev day) and 2024-07-15 (18:30)
        assert call_kwargs["from_date"] == date(2024, 7, 14)
        assert call_kwargs["to_date"] == date(2024, 7, 15)
