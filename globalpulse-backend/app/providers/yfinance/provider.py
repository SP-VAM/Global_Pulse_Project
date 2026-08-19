"""
GlobalPulse YFinance Stock Market Provider Implementation
Concrete implementation of StockMarketDataProvider wrapping yfinance with batching,
resilient caching, single-flight locking, and graceful rate-limit handling.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from app.core.exceptions import NotFoundError, ProviderUnavailableError
from app.providers.base.stock_provider import StockMarketDataProvider

logger = logging.getLogger(__name__)


class YFinanceMarketDataProvider(StockMarketDataProvider):
    """Fetches live and historical price data from Yahoo Finance with batching and rate-limit resilience."""

    def __init__(self) -> None:
        # Cache mapping: cache_key -> (pd.DataFrame, timestamp)
        self._df_cache: Dict[str, tuple[pd.DataFrame, float]] = {}

        # Keep successful responses for 5 minutes (300 seconds)
        self._cache_ttl_seconds: float = 300.0

        # Minimum interval between outgoing individual Yahoo requests (seconds)
        self._min_request_interval: float = 1.0
        self._last_request_time: float = 0.0

        # Rate limit cooldown timestamp (if Yahoo returns 429, pause until this time)
        self._rate_limit_cooldown_until: float = 0.0

        # Async lock to serialize throttle checks and cache updates
        self._lock = asyncio.Lock()

    def _normalize_ticker(self, symbol: str) -> tuple[str, str]:
        """Returns (clean_symbol, ticker_symbol) e.g. ('RELIANCE', 'RELIANCE.NS')."""
        clean = symbol.upper().strip()
        if clean.endswith(".NS"):
            clean = clean[:-3]
        return clean, f"{clean}.NS"

    def _is_rate_limit_exception(self, exc: Exception) -> bool:
        """Identify if an exception is a Yahoo Finance Rate Limit error."""
        exc_str = str(exc).lower()
        exc_name = type(exc).__name__.lower()
        return (
            "rate" in exc_str
            or "429" in exc_str
            or "too many requests" in exc_str
            or "yfratelimiterror" in exc_name
        )

    def _extract_and_format_single_df(self, raw_df: pd.DataFrame, ticker_symbol: str) -> Optional[pd.DataFrame]:
        """Extract and standardize OHLCV dataframe from yfinance download output."""
        if raw_df is None or raw_df.empty:
            return None

        df = raw_df.copy()

        # Handle MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            if ticker_symbol in df.columns.get_level_values(0):
                df = df[ticker_symbol]
            elif ticker_symbol in df.columns.get_level_values(-1):
                df = df.xs(ticker_symbol, axis=1, level=-1)
            else:
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        df = df.reset_index()

        # Standardize date column
        date_col = None
        for candidate in ["Date", "Datetime", "date", "timestamp", "index"]:
            if candidate in df.columns:
                date_col = candidate
                break

        if date_col is None:
            date_col = df.columns[0]

        df.rename(columns={date_col: "Date"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in df.columns:
                if col in ["Open", "High", "Low"] and "Close" in df.columns:
                    df[col] = df["Close"]
                elif col == "Volume":
                    df[col] = 0.0
                else:
                    return None

        result_df = df[required_cols].copy()
        result_df = result_df.dropna(subset=["Date", "Close"])
        result_df["Close"] = pd.to_numeric(result_df["Close"], errors="coerce")
        result_df = result_df[result_df["Close"] > 0]

        if result_df.empty:
            return None

        return result_df.sort_values("Date").reset_index(drop=True)

    async def get_batch_historical_prices(
        self,
        symbols: List[str],
        period: str = "1mo",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price DataFrames in ONE SINGLE BATCH request for all symbols.
        Caches each ticker individually so single requests also get instant cache hits.
        Gracefully handles Yahoo rate-limits by falling back to any available cache.
        """
        if not symbols:
            return {}

        now = time.time()
        results: Dict[str, pd.DataFrame] = {}
        missing_symbols: List[str] = []

        # 1. Check in-memory cache for all symbols
        async with self._lock:
            for raw_sym in symbols:
                clean, ticker = self._normalize_ticker(raw_sym)
                cache_key = f"{ticker}_{period}_{interval}"
                cached = self._df_cache.get(cache_key)
                if cached:
                    cached_df, cached_time = cached
                    if now - cached_time < self._cache_ttl_seconds:
                        results[clean] = cached_df.copy()
                        continue
                missing_symbols.append(clean)

        if not missing_symbols:
            logger.info("Batch yfinance cache HIT | %d symbols served from cache", len(symbols))
            return results

        # 2. Check rate-limit cooldown
        if now < self._rate_limit_cooldown_until:
            logger.warning(
                "YFinance in rate-limit cooldown (%.1fs remaining). Serving cached data for %d symbols.",
                self._rate_limit_cooldown_until - now,
                len(missing_symbols),
            )
            # Return any stale cache available for missing symbols
            for raw_sym in missing_symbols:
                clean, ticker = self._normalize_ticker(raw_sym)
                cache_key = f"{ticker}_{period}_{interval}"
                cached = self._df_cache.get(cache_key)
                if cached:
                    results[clean] = cached[0].copy()
            return results

        # 3. Execute 1 single batched yf.download call
        ticker_list = [f"{self._normalize_ticker(s)[1]}" for s in missing_symbols]
        logger.info("YFinance BATCH download | fetching %d tickers in ONE request: %s", len(ticker_list), ticker_list[:5])

        def _fetch_batch_sync() -> Optional[pd.DataFrame]:
            try:
                return yf.download(
                    tickers=ticker_list,
                    period=period,
                    interval=interval,
                    group_by="ticker",
                    auto_adjust=False,
                    progress=False,
                    threads=True,
                )
            except Exception as e:
                logger.warning("yf.download batch exception: %s", e)
                if self._is_rate_limit_exception(e) or "Too Many Requests" in str(e):
                    self._rate_limit_cooldown_until = time.time() + 180.0
                    logger.warning("[PROVIDER_RATE_LIMITED] yfinance rate-limited. Circuit breaker active for 180s.")
                return None

        loop = asyncio.get_running_loop()
        try:
            batch_df = await asyncio.wait_for(
                loop.run_in_executor(None, _fetch_batch_sync),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("[PROVIDER_TIMEOUT] yf.download batch timed out after 10.0s")
            batch_df = None
        except Exception as batch_exc:
            logger.warning("[PROVIDER_FAILURE] yf.download batch failed: %s", batch_exc)
            batch_df = None

        # 4. Parse batch DataFrame and update cache
        if batch_df is not None and not batch_df.empty:
            async with self._lock:
                save_time = time.time()
                for raw_sym in missing_symbols:
                    clean, ticker = self._normalize_ticker(raw_sym)
                    cache_key = f"{ticker}_{period}_{interval}"
                    try:
                        parsed_df = None
                        if isinstance(batch_df.columns, pd.MultiIndex):
                            tickers_level0 = set(batch_df.columns.get_level_values(0))
                            if ticker in tickers_level0:
                                parsed_df = self._extract_and_format_single_df(batch_df[ticker], ticker)
                            elif clean in tickers_level0:
                                parsed_df = self._extract_and_format_single_df(batch_df[clean], ticker)
                        elif len(ticker_list) == 1:
                            parsed_df = self._extract_and_format_single_df(batch_df, ticker)

                        if parsed_df is not None and not parsed_df.empty:
                            self._df_cache[cache_key] = (parsed_df.copy(), save_time)
                            results[clean] = parsed_df
                        else:
                            # Fallback to older cache if available
                            cached = self._df_cache.get(cache_key)
                            if cached:
                                results[clean] = cached[0].copy()
                    except Exception as parse_err:
                        logger.debug("Failed parsing batch ticker %s: %s", ticker, parse_err)
        else:
            # If batch download returned empty or failed, serve existing stale cache
            logger.warning("Batch download empty or failed. Falling back to stale cache.")
            for raw_sym in missing_symbols:
                clean, ticker = self._normalize_ticker(raw_sym)
                cache_key = f"{ticker}_{period}_{interval}"
                cached = self._df_cache.get(cache_key)
                if cached:
                    results[clean] = cached[0].copy()

        return results

    async def get_historical_prices(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical price DataFrame for a single ticker symbol.
        Checks cache first (< 1ms). If missing, fetches with throttling & rate-limit resilience.
        """
        clean_symbol, ticker_symbol = self._normalize_ticker(symbol)
        cache_key = f"{ticker_symbol}_{period}_{interval}"
        now = time.time()

        # 1. Check cache
        async with self._lock:
            cached = self._df_cache.get(cache_key)
            if cached:
                cached_df, cached_time = cached
                if now - cached_time < self._cache_ttl_seconds:
                    logger.info("YFinance cache hit | ticker=%s | rows=%d", ticker_symbol, len(cached_df))
                    return cached_df.copy()

        # 2. Check rate limit cooldown
        if now < self._rate_limit_cooldown_until and cached:
            logger.warning("YFinance in rate-limit cooldown. Serving cached data for %s", ticker_symbol)
            return cached[0].copy()

        # 3. Controlled fetch with rate-limit protection
        max_attempts = 2
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Throttle
                async with self._lock:
                    elapsed = time.time() - self._last_request_time
                    if elapsed < self._min_request_interval:
                        await asyncio.sleep(self._min_request_interval - elapsed)
                    self._last_request_time = time.time()

                def _fetch_sync():
                    return yf.download(
                        ticker_symbol,
                        period=period,
                        interval=interval,
                        auto_adjust=False,
                        progress=False,
                        threads=False,
                    )

                loop = asyncio.get_running_loop()
                raw_df = await loop.run_in_executor(None, _fetch_sync)
                result_df = self._extract_and_format_single_df(raw_df, ticker_symbol)

                if result_df is None or result_df.empty:
                    if attempt < max_attempts:
                        await asyncio.sleep(1.5)
                        continue
                    if cached:
                        logger.warning("YFinance returned empty data for %s. Using stale cache.", ticker_symbol)
                        return cached[0].copy()
                    raise NotFoundError(f"No price history returned by Yahoo Finance for '{ticker_symbol}'.")

                async with self._lock:
                    self._df_cache[cache_key] = (result_df.copy(), time.time())

                return result_df

            except Exception as exc:
                last_error = exc
                if self._is_rate_limit_exception(exc):
                    self._rate_limit_cooldown_until = time.time() + 60.0
                    logger.warning("YFinance rate limited on %s: %s. Setting 60s cooldown.", ticker_symbol, exc)
                    if cached:
                        return cached[0].copy()
                    raise ProviderUnavailableError(f"Yahoo Finance rate limited for '{ticker_symbol}'. Please retry shortly.")

                if attempt < max_attempts:
                    await asyncio.sleep(1.5)
                    continue

        if cached:
            logger.warning("All fetch attempts failed for %s. Serving stale cache.", ticker_symbol)
            return cached[0].copy()

        if last_error:
            raise ProviderUnavailableError(f"Yahoo Finance unavailable for '{ticker_symbol}': {last_error}")

        raise NotFoundError(f"No price history found for '{ticker_symbol}'.")

    async def close(self) -> None:
        """No persistent connection needed for yfinance."""
        pass