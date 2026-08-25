"""
GlobalPulse FastAPI Router — Stock ML Predictions & Technical Indicators
Exposes:
  - GET /api/v1/stocks/health
  - GET /api/v1/stocks/companies
  - GET /api/v1/stocks/market-snapshot (Bulk stock market snapshot)
  - GET /api/v1/stocks/{symbol}/prediction
  - GET /api/v1/stocks/{symbol}/indicators
  - GET /api/v1/stocks/{symbol}/analysis (Orchestrated endpoint)
"""
import time
from typing import Dict, List, Optional, Tuple
import pandas as pd
from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.core.timezone import TimezoneService
from app.schemas.stocks import (
    StockCompanyListResponse,
    StockFullAnalysisResponse,
    StockHealthResponse,
    StockMarketSnapshotItemSchema,
    StockMarketSnapshotResponse,
    StockNewsSentimentResponse,
    StockPredictionResponse,
    StockTopMoverItemSchema,
    StockTopMoversResponse,
    TechnicalIndicatorsResponse,
    TechnicalSummarySchema,
)
from app.services.stock_artifact_loader import get_stock_artifact_loader
from app.services.stock_prediction_service import TICKER_TO_COMPANY, StockPredictionService
from app.services.technical_indicator_service import TechnicalIndicatorService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["Stock ML Predictions & Indicators"])


def get_prediction_service(request: Request) -> StockPredictionService:
    """Dependency helper to extract stock_prediction_service from app.state."""
    return request.app.state.stock_prediction_service


def get_indicator_service(request: Request) -> TechnicalIndicatorService:
    """Dependency helper to extract technical_indicator_service from app.state."""
    return request.app.state.technical_indicator_service


@router.get(
    "/_diag/yfinance",
    summary="Diagnostic: single yfinance fetch (internal use)",
)
async def diag_yfinance_fetch(
    symbol: str = Query(..., description="Ticker symbol, e.g. RELIANCE"),
    period: str = Query("1y", description="History period, e.g. 1y"),
    prediction_service: StockPredictionService = Depends(get_prediction_service),
) -> Dict:
    """Diagnostic endpoint: performs a single provider.get_historical_prices() call and returns metadata.

    Intended for debugging Render production issues (rate-limits, empty data). Do not expose secrets.
    """
    logger = logging.getLogger("app.stocks.diag")
    normalized = prediction_service.normalize_symbol(symbol)
    provider = prediction_service.provider
    provider_name = getattr(provider, "__class__", type(provider)).__name__

    try:
        df = await provider.get_historical_prices(normalized, period=period)
        rows = 0 if df is None else len(df)
        first_date = str(df['Date'].iloc[0]) if rows > 0 and 'Date' in df.columns else None
        last_date = str(df['Date'].iloc[-1]) if rows > 0 and 'Date' in df.columns else None
        latest_close = float(df['Close'].iloc[-1]) if rows > 0 and 'Close' in df.columns else None

        logger.info(
            "diag_yfinance_success | provider=%s | requested=%s | normalized=%s | period=%s | rows=%d | first=%s | last=%s",
            provider_name,
            symbol,
            normalized,
            period,
            rows,
            first_date,
            last_date,
        )

        return {
            "provider": provider_name,
            "requested_symbol": symbol,
            "normalized_symbol": normalized,
            "period": period,
            "rows": rows,
            "first_date": first_date,
            "last_date": last_date,
            "latest_close": latest_close,
        }

    except Exception as e:
        logger.warning(
            "diag_yfinance_error | provider=%s | requested=%s | normalized=%s | period=%s | error=%s",
            provider_name,
            symbol,
            normalized,
            period,
            type(e).__name__ + ": " + str(e),
        )
        return {
            "provider": provider_name,
            "requested_symbol": symbol,
            "normalized_symbol": normalized,
            "period": period,
            "error_type": type(e).__name__,
            "error_message": str(e),
        }


_settings = get_settings()

_full_analysis_cache: Dict[str, Tuple[StockFullAnalysisResponse, float]] = {}
_ANALYSIS_CACHE_TTL: float = 1800.0  # 30-minute in-memory TTL — eliminates repeated yfinance fetches

_SYMBOL_PATH = Path(
    ...,
    min_length=1,
    max_length=40,
    pattern=r"^[\w\.\-&]+$",
    description="Stock symbol (e.g. RELIANCE, HDFCBANK, TCS, M&M)",
)



@router.get(
    "/health",
    response_model=StockHealthResponse,
    summary="Stock Engine Health Check",
)
@limiter.limit(_settings.RATE_LIMIT_HEALTH)
async def get_stocks_health(request: Request) -> StockHealthResponse:
    """
    Returns health status of the stock prediction engine and model artifact loader.
    Validates model artifact loadability, label encoder, and feature counts.
    """
    loader = get_stock_artifact_loader()
    model_ok = False
    encoder_ok = False
    feat_count = 0

    try:
        model = loader.load_model()
        model_ok = model is not None
    except Exception:
        model_ok = False

    try:
        encoder = loader.load_label_encoder()
        encoder_ok = encoder is not None
    except Exception:
        encoder_ok = False

    try:
        features = loader.load_model_features()
        feat_count = len(features)
    except Exception:
        feat_count = 0

    status_str = "healthy" if (model_ok and encoder_ok and feat_count > 0) else "degraded"
    now_utc = TimezoneService.now_utc().isoformat()

    return StockHealthResponse(
        status=status_str,
        active_provider=_settings.STOCK_PROVIDER,
        model_loaded=model_ok,
        label_encoder_loaded=encoder_ok,
        feature_count=feat_count,
        supported_companies_count=len(TICKER_TO_COMPANY),
        timestamp_utc=now_utc,
    )


@router.get(
    "/companies",
    response_model=StockCompanyListResponse,
    summary="List Supported Nifty Companies",
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def list_supported_companies(
    request: Request,
    prediction_service: StockPredictionService = Depends(get_prediction_service),
) -> StockCompanyListResponse:
    """List all supported Nifty companies and ticker mappings."""
    companies = prediction_service.get_supported_companies()
    return StockCompanyListResponse(total=len(companies), companies=companies)


@router.get(
    "/market-snapshot",
    response_model=StockMarketSnapshotResponse,
    summary="Bulk Stock Market Snapshot for Top Movers & Cards",
)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def get_market_snapshot(
    request: Request,
    symbols: Optional[str] = Query(None, description="Comma-separated ticker symbols (optional)"),
    prediction_service: StockPredictionService = Depends(get_prediction_service),
) -> StockMarketSnapshotResponse:
    """
    Lightweight bulk stock market snapshot for supported Nifty companies.
    Returns current price, previous close, change, change_percent, and 30d sparkline.
    """
    t_start = time.time()
    logger.info("[MARKET] NIFTY50 request received | Client: %s", request.client.host if request.client else "unknown")
    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None

    logger.info("[MARKET] Cache & provider lookup started for %s symbols", len(symbol_list) if symbol_list else "all 50")
    items_data = await prediction_service.get_market_snapshot(symbols=symbol_list)
    items = [StockMarketSnapshotItemSchema(**item) for item in items_data]

    duration_ms = (time.time() - t_start) * 1000
    is_stale = (time.time() - prediction_service._snapshot_cache_timestamp) > prediction_service._cache_ttl_seconds
    updated_at = TimezoneService.now_utc().isoformat()

    logger.info(
        "[MARKET_RESPONSE] Generated %d items | Duration: %.1fms | Stale: %s | Refreshing: %s",
        len(items),
        duration_ms,
        is_stale,
        prediction_service._is_refreshing,
    )
    return StockMarketSnapshotResponse(
        total=len(items),
        items=items,
        source="cache",
        cached=True,
        is_stale=is_stale,
        refresh_in_progress=prediction_service._is_refreshing,
        updated_at=updated_at,
    )


@router.get(
    "/top-movers",
    response_model=StockTopMoversResponse,
    summary="Top Movers (India) Market Snapshot",
)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def get_top_movers_endpoint(
    request: Request,
    limit: int = Query(5, ge=1, le=50, description="Number of top movers to return"),
    prediction_service: StockPredictionService = Depends(get_prediction_service),
) -> StockTopMoversResponse:
    """
    Real-Time / Session Top Movers for Indian Market (NIFTY 50).
    Ranks valid stocks by absolute percentage change descending.
    Reuses authoritative market snapshot cache without extra external requests.
    Includes completeness metrics, market open/closed status, and IST timestamps.
    """
    res_data = await prediction_service.get_top_movers(limit=limit)
    return StockTopMoversResponse(**res_data)


@router.get(
    "/{symbol}/prediction",
    response_model=StockPredictionResponse,
    summary="Get Next-Day Price Movement Prediction",
)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def get_stock_prediction(
    request: Request,
    symbol: str = _SYMBOL_PATH,
    prediction_service: StockPredictionService = Depends(get_prediction_service),
) -> StockPredictionResponse:
    """
    Get XGBoost next-day price movement prediction (UP / DOWN), confidence %,
    price change, 30d price history for Sparklines, and top 10 feature importances.
    """
    normalized = prediction_service.normalize_symbol(symbol)
    result = await prediction_service.predict_stock_movement(symbol=normalized)
    result.pop("prices_df", None)
    return StockPredictionResponse(**result)


@router.get(
    "/{symbol}/sentiment",
    response_model=StockNewsSentimentResponse,
    summary="Get Dynamic News Sentiment Analysis for Stock",
)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def get_stock_sentiment(
    request: Request,
    symbol: str = _SYMBOL_PATH,
    prediction_service: StockPredictionService = Depends(get_prediction_service),
) -> StockNewsSentimentResponse:
    """
    Get dynamic news sentiment analysis for a supported stock company.
    Calculates net sentiment score, articles traced, positive/negative/neutral article breakdown,
    and returns sentiment label (Bullish, Neutral, Bearish).
    """
    normalized = prediction_service.normalize_symbol(symbol)
    result = await prediction_service.get_stock_news_sentiment(symbol=normalized)
    return StockNewsSentimentResponse(**result)


@router.get(
    "/{symbol}/indicators",
    response_model=TechnicalIndicatorsResponse,
    summary="Get Computed Technical Indicators",
)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def get_stock_indicators(
    request: Request,
    symbol: str = _SYMBOL_PATH,
    period: str = Query("1mo", pattern=r"^(1mo|3mo|6mo|1y)$", description="Time period"),
    prediction_service: StockPredictionService = Depends(get_prediction_service),
    indicator_service: TechnicalIndicatorService = Depends(get_indicator_service),
) -> TechnicalIndicatorsResponse:
    """
    Get computed technical indicators (RSI, MACD, Bollinger Bands, Moving Averages)
    for a supported stock. Rejects unsupported companies with HTTP 404.
    """
    normalized = prediction_service.normalize_symbol(symbol)
    try:
        prices_df = await prediction_service.provider.get_historical_prices(normalized, period=period)
    except Exception as e:
        # Diagnostic logging for provider failures (do not log secrets)
        logger = logging.getLogger("app.stocks")
        provider_name = getattr(prediction_service.provider, "__class__", type(prediction_service.provider)).__name__
        logger.warning(
            "Stock provider error | provider=%s | requested_symbol=%s | normalized=%s | period=%s | error=%s",
            provider_name,
            symbol,
            normalized,
            period,
            type(e).__name__ + ": " + str(e),
        )
        raise
    enriched_df = indicator_service.compute_all_indicators(prices_df)
    summary_dict = indicator_service.extract_summary(enriched_df)
    as_of_date = str(enriched_df["Date"].iloc[-1].strftime("%Y-%m-%d")) if not enriched_df.empty else ""

    return TechnicalIndicatorsResponse(
        symbol=normalized,
        period=period,
        as_of_date=as_of_date,
        summary=TechnicalSummarySchema(**summary_dict),
    )


@router.get(
    "/{symbol}/analysis",
    response_model=StockFullAnalysisResponse,
    summary="Orchestrated Stock Full Analysis Composite Endpoint",
)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def get_stock_full_analysis(
    request: Request,
    symbol: str = _SYMBOL_PATH,
    period: str = Query("1y", pattern=r"^(1d|5d|1mo|3mo|6mo|1y|5y)$", description="Historical date range"),
    prediction_service: StockPredictionService = Depends(get_prediction_service),
    indicator_service: TechnicalIndicatorService = Depends(get_indicator_service),
) -> StockFullAnalysisResponse:
    """
    Orchestration composite endpoint coordinating StockPredictionService and
    TechnicalIndicatorService into a single UI payload.
    Fetches historical OHLCV prices dynamically matching requested period,
    calculates technical indicators (RSI, MACD, Bollinger Bands, SMA20/50/200),
    and formats historical_chart_data for frontend charts.
    """
    normalized = prediction_service.normalize_symbol(symbol)
    cache_key = f"{normalized}_{period}"
    now = time.time()

    t_start = time.time()
    logger.info("[ANALYSIS_REQUEST] symbol=%s | period=%s | client=%s", normalized, period, request.client.host if request.client else "unknown")

    if cache_key in _full_analysis_cache:
        cached_resp, cached_time = _full_analysis_cache[cache_key]
        if now - cached_time < _ANALYSIS_CACHE_TTL:
            logger.info("[ANALYSIS_CACHE_HIT] symbol=%s | period=%s | age=%.1fs", normalized, period, now - cached_time)
            return cached_resp

    # Determine fetch period (fetch at least 1y if period is short to allow warm-up for SMA200)
    fetch_period = "1y" if period in ("1d", "5d", "1mo", "3mo", "6mo") else period

    # 1. Fetch Historical Prices (with automatic historical dataset fallback)
    try:
        prices_df = await prediction_service.provider.get_historical_prices(normalized, period=fetch_period)
    except Exception as e:
        logger.warning(
            "[ANALYSIS_PROVIDER_ERROR] symbol=%s | period=%s | error=%s. Attempting seed fallback...",
            normalized,
            fetch_period,
            type(e).__name__ + ": " + str(e),
        )
        fallback_fn = getattr(prediction_service.provider, "_get_historical_fallback_df", None)
        prices_df = fallback_fn(normalized, fetch_period) if callable(fallback_fn) else None
        if prices_df is None or prices_df.empty:
            raise

    # 2. Prediction using fetched prices_df
    pred_res = await prediction_service.predict_stock_movement(
        symbol=normalized,
        prices_df=prices_df,
    )
    pred_res.pop("prices_df", None)

    # 3. Technical Indicators on full warm-up prices_df
    enriched_df = indicator_service.compute_all_indicators(prices_df)
    tech_summary = indicator_service.extract_summary(enriched_df)

    # Trim enriched_df to the display range requested by period
    display_df = enriched_df
    if not enriched_df.empty:
        if period == "1d":
            display_df = enriched_df.tail(1)
        elif period == "5d":
            display_df = enriched_df.tail(5)
        elif period == "1mo":
            display_df = enriched_df.tail(22)
        elif period == "3mo":
            display_df = enriched_df.tail(65)
        elif period == "6mo":
            display_df = enriched_df.tail(130)

    # Build historical_chart_data series for chart rendering
    historical_chart_data = []
    for _, row in display_df.iterrows():
        dt_str = str(pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")) if "Date" in row else ""
        close_val = round(float(row.get("Close", 0.0)), 2)

        sma20_val = round(float(row["SMA20"]), 2) if ("SMA20" in row and not pd.isna(row["SMA20"]) and float(row["SMA20"]) > 0) else None
        sma50_val = round(float(row["SMA50"]), 2) if ("SMA50" in row and not pd.isna(row["SMA50"]) and float(row["SMA50"]) > 0) else None
        sma200_val = round(float(row["SMA200"]), 2) if ("SMA200" in row and not pd.isna(row["SMA200"]) and float(row["SMA200"]) > 0) else None
        rsi_val = round(float(row["RSI"]), 2) if ("RSI" in row and not pd.isna(row["RSI"])) else None
        macd_val = round(float(row["MACD"]), 4) if ("MACD" in row and not pd.isna(row["MACD"])) else None
        macd_sig_val = round(float(row["MACD_SIGNAL"]), 4) if ("MACD_SIGNAL" in row and not pd.isna(row["MACD_SIGNAL"])) else None
        macd_hist_val = round(float(row["MACD_HIST"]), 4) if ("MACD_HIST" in row and not pd.isna(row["MACD_HIST"])) else None
        bb_upper = round(float(row["BB_UPPER"]), 2) if ("BB_UPPER" in row and not pd.isna(row["BB_UPPER"]) and float(row["BB_UPPER"]) > 0) else None
        bb_middle = round(float(row["BB_MIDDLE"]), 2) if ("BB_MIDDLE" in row and not pd.isna(row["BB_MIDDLE"]) and float(row["BB_MIDDLE"]) > 0) else None
        bb_lower = round(float(row["BB_LOWER"]), 2) if ("BB_LOWER" in row and not pd.isna(row["BB_LOWER"]) and float(row["BB_LOWER"]) > 0) else None

        historical_chart_data.append({
            "date": dt_str,
            "price": close_val,
            "open": round(float(row.get("Open", close_val)), 2),
            "high": round(float(row.get("High", close_val)), 2),
            "low": round(float(row.get("Low", close_val)), 2),
            "close": close_val,
            "volume": round(float(row.get("Volume", 0.0)), 2),
            "sma20": sma20_val,
            "sma50": sma50_val,
            "sma200": sma200_val,
            "rsi": rsi_val,
            "macd": macd_val,
            "macd_signal": macd_sig_val,
            "macd_hist": macd_hist_val,
            "upper_band": bb_upper,
            "middle_band": bb_middle,
            "lower_band": bb_lower,
        })

    duration_ms = (time.time() - t_start) * 1000
    logger.info("[ANALYSIS_SUCCESS] symbol=%s | period=%s | candles=%d | duration=%.1fms", normalized, period, len(historical_chart_data), duration_ms)

    response = StockFullAnalysisResponse(
        symbol=normalized,
        company_name=pred_res["company_name"],
        period=period,
        as_of_date=pred_res["as_of_date"],
        current_close=pred_res["current_close"],
        price_change=pred_res.get("price_change", 0.0),
        price_change_percent=pred_res.get("price_change_percent", 0.0),
        prediction=pred_res["prediction"],
        technical_indicators=TechnicalSummarySchema(**tech_summary),
        top_influencing_features=pred_res["top_influencing_features"],
        sentiment_source=pred_res["sentiment_source"],
        price_history=pred_res.get("price_history", []),
        historical_chart_data=historical_chart_data,
    )
    _full_analysis_cache[cache_key] = (response, now)
    return response
