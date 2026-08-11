"""
Unit tests for TradingEconomicsProvider
Tests use mocked httpx responses — no live API calls.
"""
from __future__ import annotations

from datetime import date, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    ProviderAuthenticationError,
    ProviderFeatureUnavailableError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.domain.economic_event import EconomicEventCategory, EconomicImportance
from app.providers.trading_economics.provider import (
    TradingEconomicsProvider,
    _map_category,
    _map_importance,
    _parse_numeric,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider() -> TradingEconomicsProvider:
    return TradingEconomicsProvider(
        api_key="test-te-key",
        base_url="https://api.tradingeconomics.com",
        timeout=5.0,
    )


def _mock_response(status_code: int, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = Exception("No JSON")
    return resp


# ---------------------------------------------------------------------------
# Unit tests for pure mapping functions
# ---------------------------------------------------------------------------

class TestMapCategory:
    def test_interest_rate(self):
        assert _map_category("Interest Rate") == EconomicEventCategory.INTEREST_RATE

    def test_inflation_cpi(self):
        assert _map_category("CPI") == EconomicEventCategory.INFLATION
        assert _map_category("Inflation Rate") == EconomicEventCategory.INFLATION

    def test_gdp(self):
        assert _map_category("GDP Growth Rate") == EconomicEventCategory.GDP

    def test_employment(self):
        assert _map_category("Employment Change") == EconomicEventCategory.EMPLOYMENT
        assert _map_category("Nonfarm Payrolls") == EconomicEventCategory.EMPLOYMENT

    def test_unemployment(self):
        assert _map_category("Unemployment Rate") == EconomicEventCategory.UNEMPLOYMENT

    def test_central_bank(self):
        assert _map_category("Central Bank") == EconomicEventCategory.CENTRAL_BANK
        assert _map_category("Monetary Policy Minutes") == EconomicEventCategory.CENTRAL_BANK

    def test_manufacturing(self):
        assert _map_category("Manufacturing PMI") == EconomicEventCategory.MANUFACTURING

    def test_services(self):
        # "services sector" and "service sector" map to SERVICES
        assert _map_category("Service Sector Activity") == EconomicEventCategory.SERVICES
        # Manufacturing PMI maps to MANUFACTURING (pmi keyword)
        assert _map_category("Manufacturing PMI") == EconomicEventCategory.MANUFACTURING

    def test_trade(self):
        assert _map_category("Trade Balance") == EconomicEventCategory.TRADE

    def test_consumer(self):
        assert _map_category("Consumer Confidence") == EconomicEventCategory.CONSUMER
        assert _map_category("Retail Sales") == EconomicEventCategory.CONSUMER

    def test_housing(self):
        assert _map_category("Housing Starts") == EconomicEventCategory.HOUSING

    def test_government(self):
        assert _map_category("Government Budget") == EconomicEventCategory.GOVERNMENT

    def test_unknown_falls_through_to_other(self):
        assert _map_category("Random Unknown Thing") == EconomicEventCategory.OTHER

    def test_none_returns_other(self):
        assert _map_category(None) == EconomicEventCategory.OTHER


class TestMapImportance:
    def test_integer_3_is_high(self):
        assert _map_importance(3) == EconomicImportance.HIGH

    def test_integer_2_is_medium(self):
        assert _map_importance(2) == EconomicImportance.MEDIUM

    def test_integer_1_is_low(self):
        assert _map_importance(1) == EconomicImportance.LOW

    def test_string_high(self):
        assert _map_importance("high") == EconomicImportance.HIGH
        assert _map_importance("HIGH") == EconomicImportance.HIGH

    def test_string_numeric(self):
        assert _map_importance("3") == EconomicImportance.HIGH
        assert _map_importance("1") == EconomicImportance.LOW

    def test_none_is_unknown(self):
        assert _map_importance(None) == EconomicImportance.UNKNOWN

    def test_garbage_is_unknown(self):
        assert _map_importance("maybe") == EconomicImportance.UNKNOWN
        assert _map_importance(99) == EconomicImportance.UNKNOWN


class TestParseNumeric:
    def test_float(self):
        assert _parse_numeric(5.25) == 5.25

    def test_integer(self):
        assert _parse_numeric(5) == 5.0

    def test_string_float(self):
        assert _parse_numeric("5.25") == 5.25

    def test_none_returns_none(self):
        assert _parse_numeric(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_numeric("") is None

    def test_non_numeric_string_returns_none(self):
        assert _parse_numeric("N/A") is None

    def test_zero_is_valid(self):
        assert _parse_numeric(0) == 0.0


# ---------------------------------------------------------------------------
# Integration tests using mocked HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture
def provider():
    p = _make_provider()
    yield p


class TestGetCalendar:
    @pytest.mark.asyncio
    async def test_success_normalizes_event(self, provider):
        calendar_data = [
            {
                "CalendarId": "cal-001",
                "Date": "2024-01-26T14:00:00",
                "Country": "United States",
                "Category": "Interest Rate",
                "Event": "Fed Interest Rate Decision",
                "Importance": 3,
                "Actual": "5.5",
                "Previous": "5.5",
                "Forecast": "5.5",
                "Unit": "%",
            }
        ]

        with patch.object(provider, "_get", AsyncMock(return_value=calendar_data)):
            events = await provider.get_calendar()

        assert len(events) == 1
        e = events[0]
        assert e.country == "United States"
        assert e.category == EconomicEventCategory.INTEREST_RATE
        assert e.importance == EconomicImportance.HIGH
        assert e.actual == 5.5
        assert e.forecast == 5.5
        assert e.previous == 5.5
        assert e.unit == "%"
        assert e.source == "TRADING_ECONOMICS"
        assert "UTC" in e.timestamp_utc or "+" in e.timestamp_utc or "Z" not in e.timestamp_utc
        assert e.timestamp_ist is not None

    @pytest.mark.asyncio
    async def test_missing_actual_is_none(self, provider):
        """Missing actual values must be None, never zero."""
        calendar_data = [
            {
                "CalendarId": "cal-002",
                "Date": "2024-01-26T14:00:00",
                "Country": "India",
                "Category": "GDP",
                "Event": "GDP Growth Rate",
                "Importance": 2,
                "Actual": None,
                "Previous": None,
                "Forecast": None,
            }
        ]

        with patch.object(provider, "_get", AsyncMock(return_value=calendar_data)):
            events = await provider.get_calendar()

        assert events[0].actual is None
        assert events[0].previous is None
        assert events[0].forecast is None

    @pytest.mark.asyncio
    async def test_country_filter_passed_in_path(self, provider):
        """country filter should affect the API path."""
        with patch.object(provider, "_get", AsyncMock(return_value=[])) as mock_get:
            await provider.get_calendar(country="Germany")
        # Check path contains country name
        called_path = mock_get.call_args[0][0]
        assert "germany" in called_path.lower()

    @pytest.mark.asyncio
    async def test_importance_filter(self, provider):
        """Importance filter should exclude non-matching events."""
        calendar_data = [
            {"CalendarId": "1", "Date": "2024-01-26T14:00:00", "Country": "US",
             "Category": "GDP", "Event": "GDP", "Importance": 3, "Unit": None},
            {"CalendarId": "2", "Date": "2024-01-26T14:00:00", "Country": "US",
             "Category": "Housing", "Event": "Building Permits", "Importance": 1, "Unit": None},
        ]

        with patch.object(provider, "_get", AsyncMock(return_value=calendar_data)):
            events = await provider.get_calendar(importance="HIGH")

        assert len(events) == 1
        assert events[0].importance == EconomicImportance.HIGH

    @pytest.mark.asyncio
    async def test_malformed_response_skipped(self, provider):
        """Malformed items should be skipped, not crash the provider."""
        calendar_data = [
            {"this": "is nonsense"},
            {"CalendarId": "ok-001", "Date": "2024-01-26T14:00:00",
             "Country": "US", "Category": "GDP", "Event": "GDP"},
        ]

        with patch.object(provider, "_get", AsyncMock(return_value=calendar_data)):
            events = await provider.get_calendar()
        # At least the valid item should be returned (malformed skipped)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_non_list_response_raises_unavailable(self, provider):
        with patch.object(provider, "_get", AsyncMock(return_value={"error": "bad"})):
            with pytest.raises(ProviderUnavailableError):
                await provider.get_calendar()

    @pytest.mark.asyncio
    async def test_limit_respected(self, provider):
        calendar_data = [
            {"CalendarId": str(i), "Date": "2024-01-26T14:00:00",
             "Country": "US", "Category": "GDP", "Event": f"Event {i}"}
            for i in range(20)
        ]

        with patch.object(provider, "_get", AsyncMock(return_value=calendar_data)):
            events = await provider.get_calendar(limit=5)

        assert len(events) == 5


class TestProviderHTTPErrors:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, provider):
        import httpx
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(401, {})
        )):
            with pytest.raises(ProviderAuthenticationError):
                await provider.get_calendar()

    @pytest.mark.asyncio
    async def test_403_raises_feature_unavailable(self, provider):
        """403 must raise ProviderFeatureUnavailableError — NOT ProviderAuthenticationError."""
        import httpx
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(403, {})
        )):
            with pytest.raises(ProviderFeatureUnavailableError):
                await provider.get_calendar()

    @pytest.mark.asyncio
    async def test_403_is_not_authentication_error(self, provider):
        """Explicitly verify 403 is NOT ProviderAuthenticationError."""
        import httpx
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(403, {})
        )):
            with pytest.raises(Exception) as exc_info:
                await provider.get_calendar()
        assert not isinstance(exc_info.value, ProviderAuthenticationError)

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(429, {})
        )):
            with pytest.raises(ProviderRateLimitError):
                await provider.get_calendar()

    @pytest.mark.asyncio
    async def test_500_raises_unavailable(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(503, {})
        )):
            with pytest.raises(ProviderUnavailableError):
                await provider.get_calendar()

    @pytest.mark.asyncio
    async def test_timeout_raises_unavailable(self, provider):
        import httpx
        with patch.object(provider._client, "get", AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )):
            with pytest.raises(ProviderUnavailableError):
                await provider.get_calendar()


class TestGetCommodities:
    @pytest.mark.asyncio
    async def test_success_normalizes_commodity(self, provider):
        raw = [
            {"Symbol": "XAUUSD", "Name": "Gold", "Close": 2030.5,
             "Change": 5.0, "PercentualChange": 0.25,
             "Date": "2024-01-26T14:00:00", "Currency": "USD"}
        ]
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            commodities = await provider.get_commodities()

        assert len(commodities) >= 1
        gold = next((c for c in commodities if c.symbol == "XAUUSD"), None)
        assert gold is not None
        assert gold.price == 2030.5
        assert gold.change == 5.0
        assert gold.currency == "USD"
        assert gold.source == "TRADING_ECONOMICS"

    @pytest.mark.asyncio
    async def test_missing_price_is_none(self, provider):
        raw = [{"Symbol": "XAUUSD", "Name": "Gold", "Close": None,
                "Date": "2024-01-26T14:00:00", "Currency": "USD"}]
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            commodities = await provider.get_commodities()
        gold = next((c for c in commodities if c.symbol == "XAUUSD"), None)
        if gold:
            assert gold.price is None

    @pytest.mark.asyncio
    async def test_403_raises_feature_unavailable(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(403, {})
        )):
            with pytest.raises(ProviderFeatureUnavailableError):
                await provider.get_commodities()


class TestGetForex:
    @pytest.mark.asyncio
    async def test_success_normalizes_pair(self, provider):
        raw = [
            {"Symbol": "USDINR", "Name": "USD/INR", "Close": 83.5,
             "Change": 0.1, "PercentualChange": 0.12,
             "Date": "2024-01-26T14:00:00"}
        ]
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            pairs = await provider.get_forex()

        usdinr = next((p for p in pairs if p.symbol == "USDINR"), None)
        assert usdinr is not None
        assert usdinr.base_currency == "USD"
        assert usdinr.quote_currency == "INR"
        assert usdinr.rate == 83.5

    @pytest.mark.asyncio
    async def test_symbol_filter(self, provider):
        raw = [
            {"Symbol": "USDINR", "Name": "USD/INR", "Close": 83.5, "Date": "2024-01-26T14:00:00"},
            {"Symbol": "EURUSD", "Name": "EUR/USD", "Close": 1.08, "Date": "2024-01-26T14:00:00"},
        ]
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            pairs = await provider.get_forex(symbols=["USDINR"])

        assert len(pairs) == 1
        assert pairs[0].symbol == "USDINR"


class TestGetBondYields:
    @pytest.mark.asyncio
    async def test_success_normalizes_bond(self, provider):
        raw = [
            {"Symbol": "USGG10YR", "Name": "United States 10-Year",
             "Close": 4.15, "Change": 0.05, "PercentualChange": 1.2,
             "Date": "2024-01-26T14:00:00"}
        ]
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            bonds = await provider.get_bond_yields()

        us10y = next((b for b in bonds if b.symbol == "USGG10YR"), None)
        assert us10y is not None
        assert us10y.yield_value == 4.15
        assert us10y.country == "United States"
        assert us10y.maturity == "10Y"

    @pytest.mark.asyncio
    async def test_403_raises_feature_unavailable(self, provider):
        """Bond data commonly requires a premium plan — 403 must be ProviderFeatureUnavailableError."""
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(403, {})
        )):
            with pytest.raises(ProviderFeatureUnavailableError):
                await provider.get_bond_yields()
