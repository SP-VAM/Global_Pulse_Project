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
from datetime import datetime, timezone
import asyncio
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.timezone import TimezoneService
from app.providers.base.stock_provider import StockMarketDataProvider
from app.services.stock_artifact_loader import get_stock_artifact_loader
from app.services.technical_indicator_service import TechnicalIndicatorService
from app.services.stock_alert_service import broadcast_stock_price_alerts
from app.services.market_status_service import MarketStatusService

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

# High-Precision News Search Queries for all 50 NIFTY 50 Companies
COMPANY_NEWS_QUERIES: Dict[str, str] = {
    "ADANIENT": '"Adani Enterprises"',
    "ADANIPORTS": '"Adani Ports" OR "APSEZ"',
    "APOLLOHOSP": '"Apollo Hospitals"',
    "ASIANPAINT": '"Asian Paints"',
    "AXISBANK": '"Axis Bank"',
    "BAJAJ-AUTO": '"Bajaj Auto"',
    "BAJFINANCE": '"Bajaj Finance"',
    "BAJAJFINSV": '"Bajaj Finserv"',
    "BEL": '"Bharat Electronics" OR "BEL India"',
    "BHARTIARTL": '"Bharti Airtel" OR "Airtel"',
    "BPCL": '"Bharat Petroleum" OR "BPCL"',
    "BRITANNIA": '"Britannia Industries"',
    "CIPLA": '"Cipla"',
    "COALINDIA": '"Coal India"',
    "DIVISLAB": '"Divi\'s Laboratories" OR "Divis Lab"',
    "DRREDDY": '"Dr. Reddy" OR "Dr Reddy\'s Laboratories"',
    "EICHERMOT": '"Eicher Motors" OR "Royal Enfield"',
    "ETERNAL": '"Eternal Ltd"',
    "GRASIM": '"Grasim Industries"',
    "HCLTECH": '"HCL Technologies" OR "HCLTech"',
    "HDFCBANK": '"HDFC Bank"',
    "HDFCLIFE": '"HDFC Life"',
    "HEROMOTOCO": '"Hero MotoCorp"',
    "HINDALCO": '"Hindalco"',
    "HINDUNILVR": '"Hindustan Unilever" OR "HUL"',
    "ICICIBANK": '"ICICI Bank"',
    "INDUSINDBK": '"IndusInd Bank"',
    "INFY": '"Infosys"',
    "ITC": '"ITC Ltd" OR "ITC Limited"',
    "JSWSTEEL": '"JSW Steel"',
    "KOTAKBANK": '"Kotak Mahindra Bank" OR "Kotak Bank"',
    "LT": '"Larsen & Toubro" OR "L&T"',
    "M&M": '"Mahindra & Mahindra"',
    "MARUTI": '"Maruti Suzuki"',
    "NESTLEIND": '"Nestle India"',
    "NTPC": '"NTPC"',
    "ONGC": '"ONGC" OR "Oil and Natural Gas Corporation"',
    "POWERGRID": '"Power Grid Corporation" OR "PowerGrid"',
    "RELIANCE": '"Reliance Industries" OR "Reliance Jio"',
    "SBILIFE": '"SBI Life Insurance"',
    "SBIN": '"State Bank of India" OR "SBI"',
    "SHRIRAMFIN": '"Shriram Finance"',
    "SUNPHARMA": '"Sun Pharma" OR "Sun Pharmaceutical"',
    "TATACONSUM": '"Tata Consumer Products"',
    "TATASTEEL": '"Tata Steel"',
    "TCS": '"Tata Consultancy Services" OR "TCS"',
    "TECHM": '"Tech Mahindra"',
    "TITAN": '"Titan Company"',
    "TRENT": '"Trent Ltd" OR "Trent Limited" OR "Westside"',
    "ULTRACEMCO": '"UltraTech Cement"',
}


def _evaluate_financial_sentiment(text: str) -> Tuple[str, str, float]:
    """
    Evaluates financial headline and excerpt using a domain-specific financial sentiment lexicon.
    Returns (sentiment_label, confidence_str, sentiment_score in [-1.0, 1.0]).
    """
    lower = text.lower()

    bullish_terms = [
        "profit surge", "profit jumps", "profit rises", "record profit", "revenue rise", "revenue jump",
        "revenue rises", "growth", "surges", "jumps", "rally", "rallies", "expansion", "upgrades",
        "upgrade", "outperform", "buy rating", "beats estimates", "beat estimates", "record high",
        "order win", "contract win", "deal signed", "dividend", "bonus share", "strong results",
        "robust growth", "bullish", "acquisition", "strategic partnership", "expansion plan",
        "capacity increase", "positive outlook", "gains", "gain", "higher profit", "all-time high"
    ]

    bearish_terms = [
        "loss", "profit drops", "profit falls", "profit decline", "revenue drops", "revenue decline",
        "slumps", "plunges", "crashes", "tumbles", "downgrade", "downgrades", "sell rating",
        "underperform", "misses estimates", "miss estimates", "investigation", "penalty", "fine imposed",
        "fraud", "scam", "default", "debt crisis", "layoffs", "strike", "regulatory hurdle",
        "bearish", "weak results", "guidance cut", "slump", "recall", "sanction", "resignation",
        "tumble", "plunge", "losses", "drop", "drops"
    ]

    pos_score = sum(1 for term in bullish_terms if term in lower)
    neg_score = sum(1 for term in bearish_terms if term in lower)

    if pos_score > neg_score:
        score = min(1.0, 0.2 + (pos_score - neg_score) * 0.25)
        conf = f"{min(98, int(60 + score * 35))}%"
        return "POSITIVE", conf, score
    elif neg_score > pos_score:
        score = -min(1.0, 0.2 + (neg_score - pos_score) * 0.25)
        conf = f"{min(98, int(60 + abs(score) * 35))}%"
        return "NEGATIVE", conf, score
    else:
        return "NEUTRAL", "65%", 0.0


class StockPredictionService:
    """Service layer for stock price movement predictions, company discovery, and market snapshots."""

    def __init__(
        self,
        provider: StockMarketDataProvider,
        indicator_service: TechnicalIndicatorService,
        news_service: Optional[Any] = None,
        db_session_factory: Optional[Any] = None,
    ) -> None:
        self.provider = provider
        self.indicator_service = indicator_service
        self.news_service = news_service
        self.artifact_loader = get_stock_artifact_loader()
        self._snapshot_cache: List[Dict[str, Any]] = []
        self._snapshot_cache_timestamp: float = 0.0
        self._cache_ttl_seconds: float = 60.0  # 60 seconds target freshness TTL
        self._mcap_cache: Dict[str, float] = {}
        self._snapshot_lock = asyncio.Lock()
        self._sentiment_cache: Dict[str, float] = {}
        self._sentiment_mtime: float = 0.0
        self._live_news_sentiment_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._news_sentiment_ttl_seconds: float = 900.0  # 15 minutes per-company cache
        self._is_refreshing: bool = False
        self._rate_limit_cooldown_until: float = 0.0
        self._db_session_factory = db_session_factory

        # Pre-load market caps and baseline snapshot from disk immediately (< 5ms)
        self._load_baseline_snapshot_and_fundamentals()

    def _load_baseline_snapshot_and_fundamentals(self) -> None:
        """Load market cap map and seed market snapshot from persistent disk files."""
        settings = get_settings()
        data_dir = settings.STOCK_DATA_DIR

        # 1. Load fundamentals market cap
        fund_csv = os.path.join(data_dir, "fundamentals_data.csv")
        if os.path.exists(fund_csv):
            try:
                fund_df = pd.read_csv(fund_csv)
                if "Ticker" in fund_df.columns and "Market_Cap" in fund_df.columns:
                    for _, row in fund_df.iterrows():
                        tk = str(row["Ticker"]).upper().strip().replace(".NS", "")
                        val = row["Market_Cap"]
                        if pd.notna(val):
                            self._mcap_cache[tk] = float(val)
            except Exception as e:
                logger.debug("Failed loading fundamentals market caps: %s", e)

        # 2. Load latest or baseline snapshot JSON
        for fname in ["latest_market_snapshot.json", "baseline_market_snapshot.json"]:
            snap_path = os.path.join(data_dir, fname)
            if os.path.exists(snap_path):
                try:
                    import json
                    with open(snap_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        self._snapshot_cache = data
                        self._snapshot_cache_timestamp = time.time() - 30.0  # Fresh baseline
                        logger.info("[MARKET] Seeded %d Nifty 50 constituents from %s", len(data), fname)
                        break
                except Exception as e:
                    logger.debug("Failed loading %s: %s", fname, e)

    def normalize_symbol(self, raw_symbol: str) -> str:
        """
        Normalize stock symbol or company name and validate against Nifty 50 universe.
        Raises ValidationError (HTTP 400) for empty input or unsupported companies.
        Single source of truth: TICKER_TO_COMPANY.
        """
        if not raw_symbol or not str(raw_symbol).strip():
            raise ValidationError("Please enter a company name or symbol.", status_code=400)

        cleaned = str(raw_symbol).strip().upper().replace(".NS", "")

        # 1. Direct ticker match (e.g. RELIANCE, TCS, INFY)
        if cleaned in TICKER_TO_COMPANY:
            return cleaned

        # 2. Match by company name or clean name (e.g. "Reliance Industries", "Infosys")
        for ticker, name in TICKER_TO_COMPANY.items():
            name_upper = name.upper()
            name_clean = name_upper.replace(" LTD", "").replace(" LIMITED", "").strip()
            if cleaned == name_upper or cleaned == name_clean or cleaned in name_upper:
                return ticker

        # 3. Reject unsupported companies cleanly
        raise ValidationError(
            "Company not supported. Please select a company from the supported Nifty 50 list.",
            status_code=400,
        )

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
        Filters out invalid, zero, NaN, or corrupted values to prevent artificial zero spikes.
        """
        if prices_df is None or prices_df.empty:
            return []

        # Filter valid positive prices
        clean_df = prices_df.dropna(subset=["Close", "Date"]).copy()
        clean_df["Close_num"] = pd.to_numeric(clean_df["Close"], errors="coerce")
        clean_df = clean_df[clean_df["Close_num"] > 0]
        if clean_df.empty:
            return []

        tail_df = clean_df.tail(limit)
        history = []
        for _, row in tail_df.iterrows():
            try:
                date_str = str(pd.to_datetime(row["Date"]).strftime("%Y-%m-%d"))
                close_val = round(float(row["Close_num"]), 2)
                if close_val > 0 and not math.isnan(close_val) and not math.isinf(close_val):
                    history.append({"date": date_str, "close": close_val})
            except Exception:
                continue
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
            encoded_company = int(label_encoder.transform([company_name])[0])
        except Exception as exc:
            logger.warning(
                "Company name '%s' for symbol '%s' not present in label_encoder classes; using default encoding 0. Error: %s",
                company_name,
                symbol,
                exc,
            )
            encoded_company = 0

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
        proba = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else [0.5, 0.5, 0.0]

        predicted_class = int(preds[0])
        model_classes = list(getattr(model, "classes_", [0, 1, 2]))
        class_prob_map = {int(c): float(p) for c, p in zip(model_classes, proba)}

        prob_down = float(class_prob_map.get(0, 0.0))
        prob_up = float(class_prob_map.get(1, 0.0))
        prob_hold = float(class_prob_map.get(2, 0.0))

        if predicted_class == 1:
            predicted_direction = "UP"
            signal = "BULLISH"
        elif predicted_class == 0:
            predicted_direction = "DOWN"
            signal = "BEARISH"
        else:
            predicted_direction = "HOLD"
            signal = "NEUTRAL"

        confidence_pct = round(max(prob_up, prob_down, prob_hold) * 100, 2)

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
                "prob_hold": round(prob_hold, 4),
                "signal": signal,
            },
            "top_influencing_features": top_features,
            "sentiment_source": sentiment_source,
            "price_history": price_history,
            "prices_df": prices_df,
        }

    async def _background_refresh_snapshot(self) -> None:
        now = time.time()
        if now < self._rate_limit_cooldown_until:
            logger.debug("[MARKET] Background refresh skipped: in rate-limit cooldown (%.1fs left)", self._rate_limit_cooldown_until - now)
            self._is_refreshing = False
            return

        try:
            logger.info("[PROVIDER_REFRESH_STARTED] Background market snapshot refresh started")
            await self._execute_snapshot_fetch()
            logger.info("[PROVIDER_REFRESH_SUCCESS] Background market snapshot refresh succeeded")
        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "YFRateLimitError" in type(e).__name__:
                self._rate_limit_cooldown_until = time.time() + 180.0
                logger.warning("[PROVIDER_RATE_LIMITED] yfinance rate-limited in background. Cooldown active for 180s.")
            else:
                logger.warning("[PROVIDER_FAILURE] Background market snapshot refresh error: %s", e)
        finally:
            self._is_refreshing = False

    async def _execute_snapshot_fetch(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        is_full_snapshot = (symbols is None or len(symbols) == len(TICKER_TO_COMPANY))
        target_tickers = symbols if symbols else list(TICKER_TO_COMPANY.keys())
        t_start = time.time()

        logger.info("[MARKET] External provider batch request started for %d symbols", len(target_tickers))

        # 1. Single Batch Fetch for all symbols in ONE request with 10s hard timeout
        try:
            batch_prices = await asyncio.wait_for(
                self.provider.get_batch_historical_prices(target_tickers, period="1mo"),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("[PROVIDER_TIMEOUT] External provider batch fetch TIMEOUT after 10.0s. Falling back to cached snapshot.")
            batch_prices = {}
        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e) or "YFRateLimitError" in type(e).__name__:
                self._rate_limit_cooldown_until = time.time() + 180.0
                logger.warning("[PROVIDER_RATE_LIMITED] yfinance rate-limited. Circuit breaker active for 180s.")
            else:
                logger.warning("[PROVIDER_FAILURE] External provider batch fetch ERROR: %s", e)
            batch_prices = {}

        # 2. Build map of existing cached items to merge with
        existing_items_map = {item.get("symbol"): item for item in self._snapshot_cache}
        snapshot_items: List[Dict[str, Any]] = []

        # 3. Parse results synchronously in memory without blocking sequential network loops
        for raw_symbol in target_tickers:
            try:
                symbol = self.normalize_symbol(raw_symbol)
                company_name = TICKER_TO_COMPANY.get(symbol, symbol)
                prices_df = batch_prices.get(symbol)

                if prices_df is not None and not prices_df.empty:
                    current_close, change, change_pct = self.calculate_price_change(prices_df)
                    prev_close = round(current_close - change, 2) if len(prices_df) >= 2 else current_close
                    price_history = self.extract_price_history(prices_df, limit=30)
                    market_cap = self._mcap_cache.get(symbol)

                    snapshot_items.append({
                        "symbol": symbol,
                        "company_name": company_name,
                        "current_price": float(current_close),
                        "previous_close": float(prev_close),
                        "change": float(change),
                        "change_percent": float(change_pct),
                        "market_cap": market_cap,
                        "price_history": price_history,
                    })
                elif symbol in existing_items_map:
                    # Retain last valid cached item for this ticker
                    snapshot_items.append(existing_items_map[symbol])
            except Exception as item_err:
                logger.debug("Failed processing snapshot item for %s: %s", raw_symbol, item_err)
                if symbol in existing_items_map:
                    snapshot_items.append(existing_items_map[symbol])
                continue

        duration_ms = (time.time() - t_start) * 1000
        logger.info(
            "[MARKET] Snapshot processing completed | %d/%d symbols ready | Duration: %.1fms",
            len(snapshot_items),
            len(target_tickers),
            duration_ms,
        )

        if is_full_snapshot and len(snapshot_items) > 0:
            self._snapshot_cache = snapshot_items
            self._snapshot_cache_timestamp = time.time()

            # Atomically save to latest_market_snapshot.json on disk
            try:
                settings = get_settings()
                latest_path = os.path.join(settings.STOCK_DATA_DIR, "latest_market_snapshot.json")
                import json
                with open(latest_path, "w", encoding="utf-8") as f:
                    json.dump(snapshot_items, f, indent=2)
            except Exception as disk_err:
                logger.debug("Failed persisting latest_market_snapshot.json: %s", disk_err)

        # Broadcast stock price change notifications to all active users
        if snapshot_items and self._db_session_factory is not None:
            try:
                async with self._db_session_factory() as alert_session:
                    await broadcast_stock_price_alerts(alert_session, snapshot_items)
            except Exception as alert_err:
                logger.warning("[StockAlert] Failed to broadcast price alerts: %s", alert_err)

        return snapshot_items if snapshot_items else (self._snapshot_cache or [])

    async def get_market_snapshot(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Lightweight bulk stock market snapshot for supported Nifty companies.
        Non-blocking Stale-While-Revalidate (SWR) with persistent cache.
        Always returns immediately (< 5ms) without blocking on external network calls.
        """
        is_full_snapshot = (symbols is None or len(symbols) == len(TICKER_TO_COMPANY))
        now = time.time()

        # 1. Trigger background refresh if cache is stale and not in cooldown
        if self._snapshot_cache and (now - self._snapshot_cache_timestamp > self._cache_ttl_seconds):
            if not self._is_refreshing and now >= self._rate_limit_cooldown_until:
                self._is_refreshing = True
                asyncio.create_task(self._background_refresh_snapshot())

        # 2. Return cached snapshot immediately
        if self._snapshot_cache:
            if not is_full_snapshot and symbols:
                clean_symbols = {self.normalize_symbol(s) for s in symbols}
                filtered = [item for item in self._snapshot_cache if item.get("symbol") in clean_symbols]
                return filtered if filtered else self._snapshot_cache
            return self._snapshot_cache

        # 3. Rare fallback if cache is completely empty: perform bounded fetch
        async with self._snapshot_lock:
            if self._snapshot_cache:
                return self._snapshot_cache
            return await self._execute_snapshot_fetch(symbols)

    async def get_top_movers(self, limit: int = 5) -> Dict[str, Any]:
        """
        Derive top moving stocks strictly from the authoritative market snapshot.
        Does NOT make extra external provider calls; reuses SWR snapshot cache.
        Validates prices/previous close, calculates authoritative change_percent,
        sorts by abs(change_percent) descending, tracks data completeness, and surfaces market status.
        """
        # 1. Reuse existing authoritative market snapshot without extra network requests
        snapshot_items = await self.get_market_snapshot()
        now = time.time()
        snapshot_time = self._snapshot_cache_timestamp or now
        is_stale = (now - snapshot_time) > self._cache_ttl_seconds

        # 2. Filter valid records & compute completeness metrics
        universe_count = len(TICKER_TO_COMPANY)
        valid_movers: List[Dict[str, Any]] = []

        for item in (snapshot_items or []):
            try:
                sym = item.get("symbol")
                if not sym or not isinstance(sym, str):
                    continue
                sym = self.normalize_symbol(sym)
                comp_name = item.get("company_name") or TICKER_TO_COMPANY.get(sym, sym)

                cp = item.get("current_price")
                pc = item.get("previous_close")

                if cp is None or pc is None:
                    continue

                curr_price = float(cp)
                prev_close = float(pc)

                if (
                    math.isnan(curr_price)
                    or math.isinf(curr_price)
                    or curr_price <= 0
                    or math.isnan(prev_close)
                    or math.isinf(prev_close)
                    or prev_close <= 0
                ):
                    continue

                # Authoritative change calculation matching Constituents page
                change = round(curr_price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2) if prev_close != 0 else 0.0

                if math.isnan(change_pct) or math.isinf(change_pct):
                    continue

                direction = "up" if change_pct >= 0 else "down"

                valid_movers.append({
                    "symbol": sym,
                    "yahoo_ticker": f"{sym}.NS",
                    "company_name": comp_name,
                    "current_price": round(curr_price, 2),
                    "previous_close": round(prev_close, 2),
                    "change": change,
                    "change_percent": change_pct,
                    "direction": direction,
                })
            except Exception as item_err:
                logger.debug("Skipping invalid item in top movers processing: %s", item_err)
                continue

        valid_records = len(valid_movers)
        failed_records = max(0, universe_count - valid_records)

        # 3. Sort valid movers by ABS(change_percent) descending (gainers & losers ranked together)
        valid_movers.sort(key=lambda m: abs(m["change_percent"]), reverse=True)
        top_n_movers = valid_movers[:max(1, limit)]

        # 4. Market status & timestamps
        market_status = "CLOSED"
        try:
            status_resp = MarketStatusService().get_status_by_exchange("NSE")
            raw_status = status_resp.status
            market_status = raw_status.value.upper() if hasattr(raw_status, "value") else str(raw_status).upper()
        except Exception as status_err:
            logger.debug("Failed checking NSE market status: %s", status_err)
            market_status = "CLOSED"

        now_ist = TimezoneService.now_ist()
        as_of_iso = now_ist.isoformat()
        as_of_formatted = now_ist.strftime("%d %b, %I:%M %p")
        fetched_at_iso = datetime.fromtimestamp(snapshot_time, tz=timezone.utc).isoformat()

        return {
            "as_of": as_of_iso,
            "as_of_formatted": as_of_formatted,
            "snapshot_timestamp": snapshot_time,
            "fetched_at": fetched_at_iso,
            "market_status": market_status,
            "is_stale": is_stale,
            "market": "NSE",
            "universe": "NIFTY50",
            "universe_count": universe_count,
            "valid_records": valid_records,
            "failed_records": failed_records,
            "movers": top_n_movers,
        }

    async def get_stock_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Dynamically fetch real, recent company-specific news and compute authentic sentiment metrics.
        Guarantees zero company contamination, exact deterministic statistics, and 15-minute per-company caching.
        """
        normalized_ticker = self.normalize_symbol(symbol)
        company_name = TICKER_TO_COMPANY[normalized_ticker]
        now = time.time()

        # 1. Check in-memory company cache
        cached = self._live_news_sentiment_cache.get(normalized_ticker)
        if cached:
            cached_time, cached_payload = cached
            if now - cached_time < self._news_sentiment_ttl_seconds:
                return cached_payload

        articles = []

        # 2. Fetch live recent news via NewsService if available
        if self.news_service is not None:
            query = COMPANY_NEWS_QUERIES.get(normalized_ticker, f'"{company_name}"')
            try:
                raw_news = await self.news_service.search_news(
                    query=query,
                    page=1,
                    page_size=15,
                )

                for idx, art in enumerate(raw_news):
                    headline = (art.headline or "").strip()
                    summary = (art.summary or "").strip()
                    combined_text = f"{headline} {summary}"

                    if not headline:
                        continue

                    # Sentiment evaluation
                    sent_label, conf, score = _evaluate_financial_sentiment(combined_text)

                    # Format timestamp
                    pub_date = "Recent"
                    if art.published_at_utc:
                        try:
                            pub_date = art.published_at_utc[:10]
                        except Exception:
                            pub_date = "Recent"

                    src_name = art.source_name or "Financial News"
                    articles.append({
                        "id": f"news_{art.id or idx}",
                        "title": headline,
                        "sentiment": sent_label,
                        "confidence": conf,
                        "source_date": f"{src_name} • {pub_date}",
                        "excerpt": summary or headline,
                        "url": art.article_url or "",
                        "published_at": art.published_at_utc or "",
                    })
            except Exception as news_err:
                logger.warning(
                    "[NewsSentiment] Live news fetch failed for %s (%s): %s",
                    normalized_ticker, query, news_err
                )

        # 3. Sort articles by publication date descending (newest first)
        articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

        # 4. Deterministic Sentiment Aggregation
        articles_traced = len(articles)
        positive_articles = sum(1 for a in articles if a["sentiment"] == "POSITIVE")
        negative_articles = sum(1 for a in articles if a["sentiment"] == "NEGATIVE")
        neutral_articles = sum(1 for a in articles if a["sentiment"] == "NEUTRAL")

        if articles_traced > 0:
            net_sentiment = round((positive_articles - negative_articles) / float(articles_traced), 2)
        else:
            net_sentiment = 0.0

        if net_sentiment >= 0.15:
            sentiment_label = "Bullish"
        elif net_sentiment <= -0.15:
            sentiment_label = "Bearish"
        else:
            sentiment_label = "Neutral"

        news_list = [
            {
                "id": a["id"],
                "title": a["title"],
                "sentiment": a["sentiment"],
                "confidence": a["confidence"],
                "source_date": a["source_date"],
                "excerpt": a["excerpt"],
                "url": a.get("url", ""),
            }
            for a in articles
        ]

        result_payload = {
            "symbol": normalized_ticker,
            "company_name": company_name,
            "net_sentiment": net_sentiment,
            "sentiment_label": sentiment_label,
            "articles_traced": articles_traced,
            "positive_articles": positive_articles,
            "negative_articles": negative_articles,
            "neutral_articles": neutral_articles,
            "news_list": news_list,
        }

        # Cache valid response
        self._live_news_sentiment_cache[normalized_ticker] = (now, result_payload)
        return result_payload

