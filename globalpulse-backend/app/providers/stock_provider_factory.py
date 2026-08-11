"""
GlobalPulse Stock Data Provider Factory
Instantiates active StockMarketDataProvider driven by application settings.
Raises ValueError if an unsupported provider configuration is specified.
"""
from app.core.config import get_settings
from app.providers.base.stock_provider import StockMarketDataProvider
from app.providers.yfinance.provider import YFinanceMarketDataProvider


def get_stock_provider() -> StockMarketDataProvider:
    """Return active stock data provider based on settings.STOCK_PROVIDER."""
    settings = get_settings()
    provider_name = settings.STOCK_PROVIDER.lower().strip()
    if provider_name == "yfinance":
        return YFinanceMarketDataProvider()
    else:
        raise ValueError(
            f"Unsupported STOCK_PROVIDER '{settings.STOCK_PROVIDER}'. "
            f"Currently supported providers: ['yfinance']."
        )
