"""
GlobalPulse YFinance Stock Market Provider Implementation
Concrete implementation of StockMarketDataProvider wrapping yfinance with resilience.
"""

import asyncio
import logging
import time
from typing import Optional

import pandas as pd
import yfinance as yf

from app.core.exceptions import NotFoundError, ProviderUnavailableError
from app.providers.base.stock_provider import StockMarketDataProvider

logger = logging.getLogger(__name__)


class YFinanceMarketDataProvider(StockMarketDataProvider):
    """Fetches live and historical price data from Yahoo Finance."""

    def __init__(self) -> None:
        self._df_cache: dict = {}

        # Keep successful responses for 5 minutes.
        self._cache_ttl_seconds: float = 300.0

        # Prevent this process from hammering Yahoo.
        self._last_request_time: float = 0.0

        # Minimum time between Yahoo requests from this provider.
        self._min_request_interval: float = 2.0
        # Async lock to serialize throttle checks and cache updates
        self._lock = asyncio.Lock()

    async def get_historical_prices(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame:

        # ---------------------------------------------------------
        # 1. Normalize symbol
        # ---------------------------------------------------------

        clean_symbol = symbol.upper().strip()

        if clean_symbol.endswith(".NS"):
            clean_symbol = clean_symbol[:-3]

        ticker_symbol = f"{clean_symbol}.NS"

        cache_key = f"{ticker_symbol}_{period}_{interval}"

        # ---------------------------------------------------------
        # 2. Check cache
        # ---------------------------------------------------------

        now = time.time()

        cached = self._df_cache.get(cache_key)

        if cached:
            cached_df, cached_time = cached

            if now - cached_time < self._cache_ttl_seconds:
                logger.info(
                    "YFinance cache hit | ticker=%s | period=%s | rows=%d",
                    ticker_symbol,
                    period,
                    len(cached_df),
                )

                return cached_df.copy()

        # ---------------------------------------------------------
        # 3. Controlled request to Yahoo
        # ---------------------------------------------------------

        async def wait_before_request():
            # Ensure only one coroutine updates/checks the last_request_time at a time.
            while True:
                async with self._lock:
                    now_ts = time.time()
                    elapsed = now_ts - self._last_request_time
                    if elapsed >= self._min_request_interval:
                        # Reserve the slot
                        self._last_request_time = now_ts
                        return
                    wait_time = self._min_request_interval - elapsed

                logger.info(
                    "YFinance throttling | ticker=%s | wait=%.2fs",
                    ticker_symbol,
                    wait_time,
                )

                # Sleep outside the lock to allow others to progress
                await asyncio.sleep(wait_time)

        logger.info(
            "YFinance fetch request | ticker=%s | period=%s | interval=%s",
            ticker_symbol,
            period,
            interval,
        )

        # ---------------------------------------------------------
        # 4. Fetch with limited retries
        # ---------------------------------------------------------

        max_attempts = 3

        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):

            try:

                await wait_before_request()

                def _fetch_sync():

                    logger.info(
                        "Calling Yahoo Finance | ticker=%s | attempt=%d",
                        ticker_symbol,
                        attempt,
                    )

                    return yf.download(
                        ticker_symbol,
                        period=period,
                        interval=interval,
                        auto_adjust=False,
                        progress=False,
                        threads=False,
                    )

                loop = asyncio.get_running_loop()

                df = await loop.run_in_executor(
                    None,
                    _fetch_sync,
                )

                # -------------------------------------------------
                # 5. Validate response
                # -------------------------------------------------

                if df is None or df.empty:

                    logger.warning(
                        "Yahoo returned empty dataframe | ticker=%s | "
                        "attempt=%d/%d",
                        ticker_symbol,
                        attempt,
                        max_attempts,
                    )

                    if attempt < max_attempts:

                        # Exponential backoff:
                        # 2s, 4s
                        await asyncio.sleep(2 ** attempt)

                        continue

                    raise NotFoundError(
                        f"No price history returned by Yahoo Finance "
                        f"for '{ticker_symbol}' after {max_attempts} attempts."
                    )

                # -------------------------------------------------
                # 6. Handle yfinance MultiIndex columns
                # -------------------------------------------------

                if isinstance(df.columns, pd.MultiIndex):

                    # yf.download() can return:
                    #
                    # Price       Close High Low Open Volume
                    # Ticker      TCS.NS ...
                    #
                    # Flatten it safely.

                    if ticker_symbol in df.columns.get_level_values(-1):

                        df = df.xs(
                            ticker_symbol,
                            axis=1,
                            level=-1,
                        )

                    else:

                        df.columns = [
                            col[0] if isinstance(col, tuple) else col
                            for col in df.columns
                        ]

                # -------------------------------------------------
                # 7. Reset index
                # -------------------------------------------------

                df = df.reset_index()

                # -------------------------------------------------
                # 8. Standardize date column
                # -------------------------------------------------

                date_col = None

                for candidate in ["Date", "Datetime"]:

                    if candidate in df.columns:
                        date_col = candidate
                        break

                if date_col is None:

                    date_col = df.columns[0]

                df.rename(
                    columns={date_col: "Date"},
                    inplace=True,
                )

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce",
                )

                # -------------------------------------------------
                # 9. Validate required columns
                # -------------------------------------------------

                required_cols = [
                    "Date",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]

                missing = [
                    col
                    for col in required_cols
                    if col not in df.columns
                ]

                if missing:

                    raise ProviderUnavailableError(
                        f"Yahoo Finance response for "
                        f"'{ticker_symbol}' is missing columns: "
                        f"{missing}"
                    )

                # -------------------------------------------------
                # 10. Keep only required columns
                # -------------------------------------------------

                result_df = df[required_cols].copy()

                # Remove invalid dates
                result_df = result_df.dropna(
                    subset=["Date"]
                )

                # Remove rows where Close is missing
                result_df = result_df.dropna(
                    subset=["Close"]
                )

                if result_df.empty:

                    raise NotFoundError(
                        f"Yahoo Finance returned no usable "
                        f"price history for '{ticker_symbol}'."
                    )

                # -------------------------------------------------
                # 11. Sort by date
                # -------------------------------------------------

                result_df = result_df.sort_values(
                    "Date"
                ).reset_index(drop=True)

                # -------------------------------------------------
                # 12. Cache successful response (protected)
                # -------------------------------------------------
                async with self._lock:
                    self._df_cache[cache_key] = (
                        result_df.copy(),
                        time.time(),
                    )

                # -------------------------------------------------
                # 13. Diagnostic logging
                # -------------------------------------------------

                logger.info(
                    "YFinance fetch SUCCESS | "
                    "ticker=%s | rows=%d | first_date=%s | "
                    "last_date=%s | latest_close=%s",
                    ticker_symbol,
                    len(result_df),
                    result_df["Date"].iloc[0],
                    result_df["Date"].iloc[-1],
                    result_df["Close"].iloc[-1],
                )

                return result_df

            except NotFoundError:

                last_error = None

                if attempt < max_attempts:

                    logger.warning(
                        "YFinance returned no usable data | "
                        "ticker=%s | attempt=%d/%d",
                        ticker_symbol,
                        attempt,
                        max_attempts,
                    )

                    await asyncio.sleep(2 ** attempt)

                    continue

                raise

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "YFinance request failed | "
                    "ticker=%s | attempt=%d/%d | "
                    "error=%s: %s",
                    ticker_symbol,
                    attempt,
                    max_attempts,
                    type(exc).__name__,
                    str(exc),
                )

                if attempt < max_attempts:

                    await asyncio.sleep(2 ** attempt)

                    continue

        # ---------------------------------------------------------
        # 14. All attempts failed
        # ---------------------------------------------------------

        if last_error:

            raise ProviderUnavailableError(
                f"Yahoo Finance unavailable for "
                f"'{ticker_symbol}': {last_error}"
            )

        raise NotFoundError(
            f"No price history found for '{ticker_symbol}'."
        )

    async def close(self) -> None:
        """No persistent connection needed for yfinance."""
        pass