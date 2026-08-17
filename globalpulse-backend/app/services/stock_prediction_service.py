"""
GlobalPulse Stock Prediction Service
Executes XGBoost model inference for stock price direction predictions.

Security & Architectural Invariants:
1. Strict Company Validation: Rejects unknown/unsupported tickers with NotFoundError (HTTP 404). Never defaults to Company_Encoded = 0.
2. Strict Feature Vector Ordering: Reorders feature matrix explicitly to X = X[model_features] prior to passing to model.predict().
3. Exact Sentiment_Mean Semantics: Sentiment_Mean is in range [-1.0, +1.0] matching model training semantics.
   Defaults to 0.0 (Neutral) if missing. Does NOT substitute relevance_score for sentiment.
4. Single-Fetch Execution: Supports optional pre-fetched prices_df to eliminate duplicate provider I/O calls.
5. Structured Logging: Logs NaN/Inf sanitization warnings and inference timing.
6. Serialized Price History & Market Snapshot: Serializes 30-day closing price points for Sparkline rendering.
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.providers.base.stock_provider import StockMarketDataProvider
from app.services.stock_artifact_loader import get_stock_artifact_loader
from app.services.technical_indicator_service import TechnicalIndicatorService

logger = logging.getLogger(__name__)

# Supported 50 Nifty Companies Mapping
TICKER_TO_COMPANY: Dict[str, str] = {
    "ADANIENT": "Adani Enterprises Ltd",
    "ADANIPORTS": "Adani Ports & Special Economic Zone Ltd",
    "APOLLOHOSP": "Apollo Hospitals Enterprise Ltd",
    "ASIANPAINT": "Asian Paints Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "BAJAJ-AUTO": "Bajaj Auto Ltd",
    "BAJFINANCE": "Bajaj Finance Ltd",
    "BAJAJFINSV": "Bajaj Finserv Ltd",
    "BEL": "Bharat Electronics Ltd",
    "BHARTIARTL": "Bharti Airtel Ltd",
    "BPCL": "Bharat Petroleum Corporation Ltd",
    "BRITANNIA": "Britannia Industries Ltd",
    "CIPLA": "Cipla Ltd",
    "COALINDIA": "Coal India Ltd",
    "DIVISLAB": "Divi's Laboratories Ltd",
    "DRREDDY": "Dr. Reddy's Laboratories Ltd",
    "EICHERMOT": "Eicher Motors Ltd",
    "ETERNAL": "Eternal Ltd",
    "GRASIM": "Grasim Industries Ltd",
    "HCLTECH": "HCL Technologies Ltd",
    "HDFCBANK": "HDFC Bank Ltd",
    "HDFCLIFE": "HDFC Life Insurance Ltd",
    "HEROMOTOCO": "Hero MotoCorp Ltd",
    "HINDALCO": "Hindalco Industries Ltd",
    "HINDUNILVR": "Hindustan Unilever Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "INDUSINDBK": "IndusInd Bank Ltd",
    "INFY": "Infosys Ltd",
    "ITC": "ITC Ltd",
    "JSWSTEEL": "JSW Steel Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd",
    "LT": "Larsen & Toubro Ltd",
    "M&M": "Mahindra & Mahindra Ltd",
    "MARUTI": "Maruti Suzuki India Ltd",
    "NESTLEIND": "Nestle India Ltd",
    "NTPC": "NTPC Ltd",
    "ONGC": "Oil & Natural Gas Corporation Ltd",
    "POWERGRID": "Power Grid Corporation of India Ltd",
    "RELIANCE": "Reliance Industries Ltd",
    "SBILIFE": "SBI Life Insurance Ltd",
    "SBIN": "State Bank of India",
    "SHRIRAMFIN": "Shriram Finance Ltd",
    "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
    "TATACONSUM": "Tata Consumer Products Ltd",
    "TATASTEEL": "Tata Steel Ltd",
    "TCS": "Tata Consultancy Services Ltd",
    "TECHM": "Tech Mahindra Ltd",
    "TITAN": "Titan Company Ltd",
    "TRENT": "Trent Ltd",
    "ULTRACEMCO": "UltraTech Cement Ltd",
}


class StockPredictionService:
    """Service layer for stock price movement predictions, company discovery, and market snapshots."""

    def __init__(
        self,
        provider: StockMarketDataProvider,
        indicator_service: TechnicalIndicatorService,
    ) -> None:
        self.provider = provider
        self.indicator_service = indicator_service
        self.artifact_loader = get_stock_artifact_loader()
        self._snapshot_cache: List[Dict[str, Any]] = []
        self._snapshot_cache_timestamp: float = 0.0
        self._cache_ttl_seconds: float = 300.0  # 5 minutes cache TTL
        self._mcap_cache: Dict[str, float] = {}
        self._snapshot_lock = asyncio.Lock()
        self._sentiment_cache: Dict[str, float] = {}
        self._sentiment_mtime: float = 0.0
        self._is_refreshing: bool = False

    def normalize_symbol(self, raw_symbol: str) -> str:
        clean = raw_symbol.upper().strip().replace(".NS", "")
        if clean not in TICKER_TO_COMPANY:
            raise NotFoundError(
                f"Stock symbol '{raw_symbol}' is not supported. "
                f"Supported tickers include: {list(TICKER_TO_COMPANY.keys())[:5]}..."
            )
        return clean

    def get_supported_companies(self) -> List[Dict[str, str]]:
        """Return list of supported Nifty companies."""
        return [
            {
                "symbol": ticker,
                "company_name": name,
                "yahoo_ticker": f"{ticker}.NS",
            }
            for ticker, name in sorted(TICKER_TO_COMPANY.items())
        ]

    def _get_optional_sentiment_mean(self, symbol: str) -> float:
        """
        Optional compatibility sentiment reader.
        Reads Sentiment_Mean in [-1.0, +1.0] from news_sentiment_aggregated.csv if present;
        returns 0.0 (Neutral) if file absent or ticker missing.
        Uses cached dictionary invalidated on file modification.
        """
        settings = get_settings()
        csv_path = os.path.join(settings.STOCK_DATA_DIR, "news_sentiment_aggregated.csv")
        if not os.path.exists(csv_path):
            return 0.0

        try:
            mtime = os.path.getmtime(csv_path)
            if mtime != self._sentiment_mtime or not self._sentiment_cache:
                df = pd.read_csv(csv_path)
                cache = {}
                if "Ticker" in df.columns and "Sentiment_Mean" in df.columns:
                    for _, row in df.iterrows():
                        t = str(row["Ticker"]).upper().strip()
                        val = row["Sentiment_Mean"]
                        if pd.notnull(val):
                            cache[t] = float(np.clip(float(val), -1.0, 1.0))
                self._sentiment_cache = cache
                self._sentiment_mtime = mtime

            return self._sentiment_cache.get(symbol, 0.0)
        except Exception as e:
            logger.debug("Optional sentiment CSV lookup failed for %s: %s", symbol, e)
        return 0.0

    def extract_price_history(self, prices_df: pd.DataFrame, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Extract bounded list of latest N trading days closing prices for Sparkline rendering.
        """
        if prices_df is None or prices_df.empty:
            return []

        tail_df = prices_df.tail(limit)
        history = []
        for _, row in tail_df.iterrows():
            date_str = str(pd.to_datetime(row["Date"]).strftime("%Y-%m-%d"))
            close_val = round(float(row["Close"]), 2)
            history.append({"date": date_str, "close": close_val})
        return history

    def calculate_price_change(self, prices_df: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Compute current_close, absolute daily change, and daily change percentage from price history.
        """
        if prices_df is None or len(prices_df) == 0:
            return 0.0, 0.0, 0.0

        current_close = round(float(prices_df["Close"].iloc[-1]), 2)
        if len(prices_df) < 2:
            return current_close, 0.0, 0.0

        prev_close = float(prices_df["Close"].iloc[-2])
        change = round(current_close - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close != 0 else 0.0
        return current_close, change, change_pct

    def build_feature_vector(
        self,
        symbol: str,
        enriched_df: pd.DataFrame,
        model_features: List[str],
        label_encoder: Any,
        explicit_sentiment: Optional[float] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Construct feature matrix strictly ordered matching model_features (X = X[model_features]).
        """
        latest = enriched_df.iloc[-1:].copy()
        company_name = TICKER_TO_COMPANY[symbol]

        try:
            encoded_company = label_encoder.transform([company_name])[0]
        except Exception:
            raise ValidationError(
                f"Company name '{company_name}' could not be encoded by label encoder."
            )

        as_of_date = pd.to_datetime(latest["Date"].values[0])
        latest["Year"] = as_of_date.year
        latest["Month"] = as_of_date.month

        sentiment_val = (
            float(np.clip(explicit_sentiment, -1.0, 1.0))
            if explicit_sentiment is not None
            else self._get_optional_sentiment_mean(symbol)
        )
        latest["Sentiment_Mean"] = sentiment_val
        latest["Company_Encoded"] = encoded_company

        X = pd.DataFrame(index=latest.index)
        for col in model_features:
            if col in latest.columns:
                X[col] = latest[col].values
            else:
                X[col] = 0.0

        nan_count = X.isnull().sum().sum()
        inf_count = np.isinf(X.values).sum()
        if nan_count > 0 or inf_count > 0:
            logger.warning(
                "Sanitizing %d NaN and %d Inf values to 0.0 in stock feature vector | ticker=%s",
                nan_count,
                inf_count,
                symbol,
            )
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X = X[model_features]

        return X, latest

    async def predict_stock_movement(
        self,
        symbol: str,
        prices_df: Optional[pd.DataFrame] = None,
        explicit_sentiment: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute next-day price movement prediction for a supported stock symbol.
        """
        start_time = time.perf_counter()
        normalized_ticker = self.normalize_symbol(symbol)
        company_name = TICKER_TO_COMPANY[normalized_ticker]

        model = self.artifact_loader.load_model()
        label_encoder = self.artifact_loader.load_label_encoder()
        model_features = self.artifact_loader.load_model_features()

        if prices_df is None or prices_df.empty:
            prices_df = await self.provider.get_historical_prices(normalized_ticker, period="3mo")

        enriched_df = self.indicator_service.compute_all_indicators(prices_df)

        X, latest_row = self.build_feature_vector(
            symbol=normalized_ticker,
            enriched_df=enriched_df,
            model_features=model_features,
            label_encoder=label_encoder,
            explicit_sentiment=explicit_sentiment,
        )

        preds = model.predict(X)
        proba = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else [0.5, 0.5]

        predicted_class = int(preds[0])
        predicted_direction = "UP" if predicted_class == 1 else "DOWN"
        prob_down = float(proba[0])
        prob_up = float(proba[1])
        confidence_pct = round(max(prob_up, prob_down) * 100, 2)
        signal = "BULLISH" if predicted_direction == "UP" else "BEARISH"

        top_features = []
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            feature_imp_pairs = sorted(
                zip(model_features, importances),
                key=lambda x: x[1],
                reverse=True,
            )
            top_features = [
                {"feature": feat, "importance": round(float(imp), 4)}
                for feat, imp in feature_imp_pairs[:10]
            ]

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "Stock inference completed | ticker=%s | direction=%s | confidence=%.2f%% | duration_ms=%.2f",
            normalized_ticker,
            predicted_direction,
            confidence_pct,
            duration_ms,
        )

        current_close, price_change, price_change_pct = self.calculate_price_change(prices_df)
        as_of_date_str = str(pd.to_datetime(latest_row["Date"].values[0]).strftime("%Y-%m-%d"))
        price_history = self.extract_price_history(prices_df, limit=30)

        sentiment_source = "OPTIONAL_CSV_BASELINE"
        if explicit_sentiment is not None:
            sentiment_source = "EXPLICIT_INPUT"

        return {
            "symbol": normalized_ticker,
            "company_name": company_name,
            "as_of_date": as_of_date_str,
            "current_close": current_close,
            "price_change": price_change,
            "price_change_percent": price_change_pct,
            "prediction": {
                "predicted_direction": predicted_direction,
                "confidence_percent": confidence_pct,
                "prob_up": round(prob_up, 4),
                "prob_down": round(prob_down, 4),
                "signal": signal,
            },
            "top_influencing_features": top_features,
            "sentiment_source": sentiment_source,
            "price_history": price_history,
            "prices_df": prices_df,
        }

    async def _background_refresh_snapshot(self) -> None:
        try:
            await self._execute_snapshot_fetch()
        except Exception as e:
            logger.debug("Background market snapshot refresh failed: %s", e)
        finally:
            self._is_refreshing = False

    async def _execute_snapshot_fetch(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        is_full_snapshot = (symbols is None or len(symbols) == len(TICKER_TO_COMPANY))
        target_tickers = symbols if symbols else list(TICKER_TO_COMPANY.keys())

        async def _fetch_single_item(raw_symbol: str) -> Optional[Dict[str, Any]]:
            try:
                symbol = self.normalize_symbol(raw_symbol)
                company_name = TICKER_TO_COMPANY[symbol]
                prices_df = await self.provider.get_historical_prices(symbol, period="1mo")
                current_close, change, change_pct = self.calculate_price_change(prices_df)
                prev_close = round(current_close - change, 2) if len(prices_df) >= 2 else current_close
                price_history = self.extract_price_history(prices_df, limit=30)

                market_cap = self._mcap_cache.get(symbol)
                if market_cap is None:
                    try:
                        ticker_symbol = f"{symbol}.NS"
                        loop = asyncio.get_event_loop()
                        def _fetch_mcap_sync():
                            tk = yf.Ticker(ticker_symbol)
                            fi = tk.fast_info
                            raw_mcap = fi.get("marketCap") or fi.get("market_cap")
                            return float(raw_mcap) if raw_mcap and isinstance(raw_mcap, (int, float)) and raw_mcap > 0 else None
                        market_cap = await loop.run_in_executor(None, _fetch_mcap_sync)
                        if market_cap is not None:
                            self._mcap_cache[symbol] = market_cap
                    except Exception as mcap_err:
                        logger.debug("Failed to fetch market_cap for %s: %s", symbol, mcap_err)

                return {
                    "symbol": symbol,
                    "company_name": company_name,
                    "current_price": current_close,
                    "previous_close": prev_close,
                    "change": change,
                    "change_percent": change_pct,
                    "market_cap": market_cap,
                    "price_history": price_history,
                }
            except Exception as e:
                logger.warning("Failed to fetch market snapshot item for %s: %s", raw_symbol, e)
                return None

        tasks = [_fetch_single_item(s) for s in target_tickers]
        results = await asyncio.gather(*tasks)
        snapshot_items = [item for item in results if item is not None]

        if is_full_snapshot and snapshot_items:
            self._snapshot_cache = snapshot_items
            self._snapshot_cache_timestamp = time.time()

        return snapshot_items

    async def get_market_snapshot(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lightweight bulk stock market snapshot for supported Nifty companies.
        Non-blocking Stale-While-Revalidate (SWR) with 300s TTL.
        """
        is_full_snapshot = (symbols is None or len(symbols) == len(TICKER_TO_COMPANY))
        now = time.time()

        # 1. Fresh cache hit (< 1ms)
        if is_full_snapshot and self._snapshot_cache and (now - self._snapshot_cache_timestamp < self._cache_ttl_seconds):
            logger.debug("Returning fresh cached market snapshot (age: %.2fs)", now - self._snapshot_cache_timestamp)
            return self._snapshot_cache

        # 2. Stale cache hit (< 1ms) with async background refresh
        if is_full_snapshot and self._snapshot_cache:
            if not self._is_refreshing:
                self._is_refreshing = True
                asyncio.create_task(self._background_refresh_snapshot())
            return self._snapshot_cache

        # 3. Cold miss on startup: fetch with single-flight lock
        async with self._snapshot_lock:
            if is_full_snapshot and self._snapshot_cache:
                return self._snapshot_cache
            return await self._execute_snapshot_fetch(symbols)
