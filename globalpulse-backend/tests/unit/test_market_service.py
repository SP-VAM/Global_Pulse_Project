"""
Phase 1B — MarketService / Finnhub provider tests.
All Finnhub API calls are mocked — no live network requests.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from app.core.exceptions import (
    InstrumentNotFoundError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.domain.instrument import NormalizedInstrument, NormalizedQuote
from app.domain.market import AssetType
from tests.conftest import MockMarketProvider


# ---------------------------------------------------------------------------
# Quote endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_quote_success(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
    sample_quote: NormalizedQuote,
) -> None:
    mock_provider.get_quote = AsyncMock(return_value=sample_quote)
    response = await client.get("/api/v1/quotes/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["price"] == 210.42
    assert body["source"] == "FINNHUB"


@pytest.mark.asyncio
async def test_get_quote_currency_present(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
    sample_quote: NormalizedQuote,
) -> None:
    mock_provider.get_quote = AsyncMock(return_value=sample_quote)
    response = await client.get("/api/v1/quotes/AAPL")
    body = response.json()
    assert body["currency"] == "USD"


@pytest.mark.asyncio
async def test_get_quote_currency_null_when_unavailable(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    """currency must be null when the provider cannot supply it — never defaulted."""
    quote_no_currency = NormalizedQuote(
        symbol="XYZ",
        price=100.0,
        open=None,
        high=None,
        low=None,
        previous_close=None,
        change=None,
        change_percent=None,
        currency=None,  # ← not available from Finnhub /quote
        timestamp_utc="2024-01-15T14:30:00+00:00",
        timestamp_ist="2024-01-15T20:00:00+05:30",
        source="FINNHUB",
    )
    mock_provider.get_quote = AsyncMock(return_value=quote_no_currency)
    response = await client.get("/api/v1/quotes/XYZ")
    body = response.json()
    assert body["currency"] is None


@pytest.mark.asyncio
async def test_get_quote_missing_optional_fields(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    """Optional price fields should be null when provider doesn't supply them."""
    sparse_quote = NormalizedQuote(
        symbol="SPARSE",
        price=50.0,
        open=None,
        high=None,
        low=None,
        previous_close=None,
        change=None,
        change_percent=None,
        currency=None,
        timestamp_utc="2024-01-15T14:30:00+00:00",
        timestamp_ist="2024-01-15T20:00:00+05:30",
        source="FINNHUB",
    )
    mock_provider.get_quote = AsyncMock(return_value=sparse_quote)
    response = await client.get("/api/v1/quotes/SPARSE")
    body = response.json()
    assert body["open"] is None
    assert body["high"] is None
    assert body["change"] is None


@pytest.mark.asyncio
async def test_get_quote_invalid_symbol_returns_404(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_quote = AsyncMock(
        side_effect=InstrumentNotFoundError("No quote data found for symbol 'INVALID'.")
    )
    response = await client.get("/api/v1/quotes/INVALID")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INSTRUMENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_quote_provider_timeout_returns_503(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_quote = AsyncMock(
        side_effect=ProviderUnavailableError("Finnhub request timed out.")
    )
    response = await client.get("/api/v1/quotes/AAPL")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_get_quote_auth_error_returns_502(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_quote = AsyncMock(
        side_effect=ProviderAuthenticationError("Finnhub API key is invalid.")
    )
    response = await client.get("/api/v1/quotes/AAPL")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "PROVIDER_AUTHENTICATION_ERROR"


@pytest.mark.asyncio
async def test_get_quote_rate_limit_returns_429(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_quote = AsyncMock(
        side_effect=ProviderRateLimitError("Rate limit exceeded.")
    )
    response = await client.get("/api/v1/quotes/AAPL")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "PROVIDER_RATE_LIMIT"


@pytest.mark.asyncio
async def test_get_quote_malformed_response_returns_503(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_quote = AsyncMock(
        side_effect=ProviderUnavailableError("Finnhub returned a malformed quote response.")
    )
    response = await client.get("/api/v1/quotes/AAPL")
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Instrument endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_instrument_success(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
    sample_instrument: NormalizedInstrument,
) -> None:
    mock_provider.get_instrument = AsyncMock(return_value=sample_instrument)
    response = await client.get("/api/v1/instruments/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["name"] == "Apple Inc"
    assert body["exchange"] == "NASDAQ"
    assert body["source"] == "FINNHUB"


@pytest.mark.asyncio
async def test_get_instrument_nullable_fields_preserved(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    """Fields not available from provider must be null — not substituted."""
    partial_instrument = NormalizedInstrument(
        symbol="UNKNOWN",
        name=None,
        exchange=None,
        country=None,
        asset_type=None,
        currency=None,
        timezone=None,
        source="FINNHUB",
    )
    mock_provider.get_instrument = AsyncMock(return_value=partial_instrument)
    response = await client.get("/api/v1/instruments/UNKNOWN")
    body = response.json()
    assert body["name"] is None
    assert body["exchange"] is None
    assert body["currency"] is None


@pytest.mark.asyncio
async def test_get_instrument_invalid_symbol_404(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_instrument = AsyncMock(
        side_effect=InstrumentNotFoundError(
            "Instrument profile not found for symbol 'BADINSTR'. "
            "This may be due to provider plan coverage limitations or an invalid symbol."
        )
    )
    response = await client.get("/api/v1/instruments/BADINSTR")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "INSTRUMENT_NOT_FOUND"
    # Error message should include provider limitation context
    assert "coverage" in body["error"]["message"] or "invalid" in body["error"]["message"]


@pytest.mark.asyncio
async def test_get_instrument_provider_timeout_503(
    client: AsyncClient,
    mock_provider: MockMarketProvider,
) -> None:
    mock_provider.get_instrument = AsyncMock(
        side_effect=ProviderUnavailableError("Timeout")
    )
    response = await client.get("/api/v1/instruments/AAPL")
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Markets endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_markets_returns_all_exchanges(client: AsyncClient) -> None:
    response = await client.get("/api/v1/markets")
    assert response.status_code == 200
    body = response.json()
    assert "exchanges" in body
    assert body["total"] >= 10  # At least 10 exchanges configured


@pytest.mark.asyncio
async def test_list_markets_filter_by_country(client: AsyncClient) -> None:
    response = await client.get("/api/v1/markets?country=India")
    assert response.status_code == 200
    body = response.json()
    for ex in body["exchanges"]:
        assert ex["country"] == "India"
    assert body["total"] >= 2  # NSE + BSE


@pytest.mark.asyncio
async def test_list_markets_filter_singapore(client: AsyncClient) -> None:
    response = await client.get("/api/v1/markets?country=Singapore")
    body = response.json()
    assert body["total"] >= 1
    assert any(ex["exchange_code"] == "SGX" for ex in body["exchanges"])


@pytest.mark.asyncio
async def test_list_markets_empty_country_filter(client: AsyncClient) -> None:
    response = await client.get("/api/v1/markets?country=Antarctica")
    body = response.json()
    assert body["total"] == 0
    assert body["exchanges"] == []


@pytest.mark.asyncio
async def test_exchange_has_sessions(client: AsyncClient) -> None:
    """Each exchange must have at least one session configured."""
    response = await client.get("/api/v1/markets")
    for ex in response.json()["exchanges"]:
        assert len(ex["sessions"]) >= 1, f"{ex['exchange_code']} has no sessions"


@pytest.mark.asyncio
async def test_tse_has_multiple_sessions(client: AsyncClient) -> None:
    """TSE should have 2 sessions (morning + afternoon with lunch break)."""
    response = await client.get("/api/v1/markets?country=Japan")
    body = response.json()
    tse = next((ex for ex in body["exchanges"] if ex["exchange_code"] == "TSE"), None)
    assert tse is not None
    assert len(tse["sessions"]) == 2


@pytest.mark.asyncio
async def test_hkex_has_multiple_sessions(client: AsyncClient) -> None:
    """HKEX should have 2 sessions (morning + afternoon with lunch break)."""
    response = await client.get("/api/v1/markets?country=Hong Kong")
    body = response.json()
    hkex = next((ex for ex in body["exchanges"] if ex["exchange_code"] == "HKEX"), None)
    assert hkex is not None
    assert len(hkex["sessions"]) == 2
