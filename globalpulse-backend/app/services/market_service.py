"""
GlobalPulse MarketService
Orchestrates market data operations via the provider interface.
Routers call MarketService — never providers directly.
Provides live quotes for market indices & FX symbols (SENSEX, NIFTY 50, NASDAQ, USD/INR) via YFinance,
while preserving domain exception propagation for equity tickers.
"""
from __future__ import annotations

import logging
from typing import Optional
import numpy as np
import pandas as pd
import yfinance as yf

from app.core.exceptions import GlobalPulseError
from app.core.timezone import TimezoneService
from app.domain.exchange import (
    ExchangeMetadata,
    get_all_exchanges,
    get_exchanges_by_country,
)
from app.domain.instrument import NormalizedInstrument, NormalizedQuote
from app.providers.base.market_provider import MarketDataProvider

logger = logging.getLogger(__name__)

# Map common index / FX symbols to Yahoo Finance tickers
INDEX_SYMBOL_MAP = {
    "SENSEX": "^BSESN",
    "^BSESN": "^BSESN",
    "NIFTY": "^NSEI",
    "NIFTY 50": "^NSEI",
    "^NSEI": "^NSEI",
    "NASDAQ": "^IXIC",
    "^IXIC": "^IXIC",
    "USD/INR": "USDINR=X",
    "USDINR": "USDINR=X",
    "USDINR=X": "USDINR=X",
    "USDIRN": "USDINR=X",
}


class MarketService:
    """
    Service layer for market data operations.

    Dependency direction:
        Router → MarketService → MarketDataProvider → Finnhub / YFinance
    """

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def _fetch_yfinance_quote(self, symbol: str) -> Optional[NormalizedQuote]:
        """Fallback sync fetcher for yfinance quotes when primary provider returns null."""
        ticker_symbol = INDEX_SYMBOL_MAP.get(symbol.upper(), symbol.upper())
        try:
            ticker = yf.Ticker(ticker_symbol)
            now_utc = TimezoneService.now_utc()
            now_ist = TimezoneService.utc_to_ist(now_utc)

            current_close: Optional[float] = None
            prev_close: Optional[float] = None
            open_price: Optional[float] = None
            high_price: Optional[float] = None
            low_price: Optional[float] = None

            # 1. Try fast_info for instantaneous real-time index & stock quotes
            try:
                fi = ticker.fast_info
                lp = getattr(fi, "last_price", None)
                pc = getattr(fi, "previous_close", None) or getattr(fi, "regular_market_previous_close", None)
                if lp is not None and lp > 0:
                    current_close = float(lp)
                if pc is not None and pc > 0:
                    prev_close = float(pc)
                open_price = float(getattr(fi, "open", 0) or 0) or None
                high_price = float(getattr(fi, "day_high", 0) or 0) or None
                low_price = float(getattr(fi, "day_low", 0) or 0) or None
            except Exception as fi_err:
                logger.debug("fast_info fetch skipped for %s: %s", ticker_symbol, fi_err)

            # 2. If fast_info is incomplete, query history dataframe
            if current_close is None or prev_close is None:
                df = ticker.history(period="5d")
                if not df.empty:
                    if current_close is None:
                        current_close = float(df["Close"].iloc[-1])
                    if prev_close is None:
                        prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else current_close
                    if open_price is None:
                        open_price = float(df["Open"].iloc[-1])
                    if high_price is None:
                        high_price = float(df["High"].iloc[-1])
                    if low_price is None:
                        low_price = float(df["Low"].iloc[-1])

            # 3. If no valid price data could be retrieved from provider, return None (NO hardcoded fake values)
            if current_close is None or current_close <= 0:
                return None

            if prev_close is None or prev_close <= 0:
                prev_close = current_close

            change = round(current_close - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2) if prev_close != 0 else 0.0

            return NormalizedQuote(
                symbol=symbol.upper(),
                price=round(current_close, 2),
                open=round(open_price, 2) if open_price else round(current_close, 2),
                high=round(high_price, 2) if high_price else round(current_close, 2),
                low=round(low_price, 2) if low_price else round(current_close, 2),
                previous_close=round(prev_close, 2),
                change=change,
                change_percent=change_pct,
                currency="INR" if "INR" in symbol.upper() or "BSESN" in ticker_symbol or "NSEI" in ticker_symbol else "USD",
                timestamp_utc=now_utc.isoformat(),
                timestamp_ist=now_ist.isoformat(),
                source="YFINANCE_FALLBACK",
            )
        except Exception as e:
            logger.warning("YFinance fallback quote fetch failed for %s (%s): %s", symbol, ticker_symbol, e)
            return None

    async def get_quote(self, symbol: str) -> NormalizedQuote:
        """
        Retrieve a normalized real-time quote for the given symbol.
        Index & FX symbols use YFinance adapter; equity tickers use primary provider.
        """
        clean_sym = symbol.upper().strip().replace("%2F", "/")
        logger.info("MarketService.get_quote | symbol=%s", clean_sym)

        # 1. Handle Index / FX symbols
        if clean_sym in INDEX_SYMBOL_MAP:
            yf_quote = self._fetch_yfinance_quote(clean_sym)
            if yf_quote:
                return yf_quote

        # 2. Delegate equity symbols to primary provider (re-raising domain exceptions)
        return await self._provider.get_quote(clean_sym)

    async def get_instrument(self, symbol: str) -> NormalizedInstrument:
        """
        Retrieve normalized instrument metadata for the given symbol.
        Delegates to the configured market-data provider.
        """
        logger.info("MarketService.get_instrument | symbol=%s", symbol)
        return await self._provider.get_instrument(symbol.upper())

    def list_markets(self, country: Optional[str] = None) -> list[ExchangeMetadata]:
        """
        Return supported exchange metadata.
        Optionally filter by country name (case-insensitive).
        """
        if country:
            logger.debug("MarketService.list_markets | filter country=%s", country)
            return get_exchanges_by_country(country)
        return get_all_exchanges()
