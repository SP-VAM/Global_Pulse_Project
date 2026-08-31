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

    def _fetch_direct_yahoo_chart_api(self, ticker_symbol: str) -> Optional[Dict[str, float]]:
        """Direct HTTP query with custom User-Agent to bypass cloud IP rate-limiting on Render."""
        try:
            import urllib.request
            import urllib.parse
            import json
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker_symbol)}?interval=1m&range=1d"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = data["chart"]["result"][0]
                meta = result["meta"]
                price = float(meta.get("regularMarketPrice") or 0)
                prev_close = float(meta.get("previousClose") or meta.get("chartPreviousClose") or price)
                if price > 0:
                    return {
                        "price": price,
                        "previous_close": prev_close,
                        "open": float(meta.get("regularMarketDayOpen") or price),
                        "high": float(meta.get("regularMarketDayHigh") or price),
                        "low": float(meta.get("regularMarketDayLow") or price),
                    }
        except Exception as e:
            logger.debug("Direct Yahoo chart API fetch skipped for %s: %s", ticker_symbol, e)
        return None

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

            # 1. Try direct HTTP Yahoo chart API with custom User-Agent (bypasses cloud IP blocking on Render)
            direct_data = self._fetch_direct_yahoo_chart_api(ticker_symbol)
            if direct_data and direct_data.get("price"):
                current_close = direct_data["price"]
                prev_close = direct_data["previous_close"]
                open_price = direct_data.get("open")
                high_price = direct_data.get("high")
                low_price = direct_data.get("low")

            # 2. Try fast_info for instantaneous real-time index & stock quotes
            if current_close is None or prev_close is None:
                try:
                    fi = ticker.fast_info
                    lp = getattr(fi, "last_price", None)
                    pc = getattr(fi, "previous_close", None) or getattr(fi, "regular_market_previous_close", None)
                    if lp is not None and lp > 0 and current_close is None:
                        current_close = float(lp)
                    if pc is not None and pc > 0 and prev_close is None:
                        prev_close = float(pc)
                    if open_price is None:
                        open_price = float(getattr(fi, "open", 0) or 0) or None
                    if high_price is None:
                        high_price = float(getattr(fi, "day_high", 0) or 0) or None
                    if low_price is None:
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
