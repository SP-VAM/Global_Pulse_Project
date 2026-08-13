"""
pytest configuration and shared fixtures for GlobalPulse test suite.
"""
import os

# ---------------------------------------------------------------------------
# Set DATABASE_URL to authoritative PostgreSQL database 'railway'.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:GCaYlRkYnYQvReCFmHguNrHtMkwiiQZi@altaria.proxy.rlwy.net:31962/railway",
)

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import create_app
from app.domain.instrument import NormalizedInstrument, NormalizedQuote
from app.domain.market import AssetType
from app.providers.base.market_provider import MarketDataProvider
from app.services.market_service import MarketService
from app.services.market_status_service import MarketStatusService


# ---------------------------------------------------------------------------
# Shared mock provider
# ---------------------------------------------------------------------------

class MockMarketProvider(MarketDataProvider):
    """Test double for MarketDataProvider. Configure per-test via attributes."""

    async def get_quote(self, symbol: str) -> NormalizedQuote:
        raise NotImplementedError("Configure in test")

    async def get_instrument(self, symbol: str) -> NormalizedInstrument:
        raise NotImplementedError("Configure in test")

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_provider() -> MockMarketProvider:
    return MockMarketProvider()


@pytest_asyncio.fixture
async def client(mock_provider: MockMarketProvider) -> AsyncClient:
    """
    Return an AsyncClient wired to the FastAPI app with the mock provider injected.
    Services are attached to app.state before the first request.
    """
    app = create_app()
    app.state.market_service = MarketService(provider=mock_provider)
    app.state.market_status_service = MarketStatusService()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Canonical domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_quote() -> NormalizedQuote:
    return NormalizedQuote(
        symbol="AAPL",
        price=210.42,
        open=208.00,
        high=212.00,
        low=207.50,
        previous_close=212.60,
        change=-2.18,
        change_percent=-1.03,
        currency="USD",
        timestamp_utc="2024-01-15T14:30:00+00:00",
        timestamp_ist="2024-01-15T20:00:00+05:30",
        source="FINNHUB",
    )


@pytest.fixture
def sample_instrument() -> NormalizedInstrument:
    return NormalizedInstrument(
        symbol="AAPL",
        name="Apple Inc",
        exchange="NASDAQ",
        country="US",
        asset_type=AssetType.EQUITY,
        currency="USD",
        timezone=None,
        source="FINNHUB",
    )
