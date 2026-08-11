"""
GlobalPulse Market Anomaly Detection Engine (Sub-Phase 2B)
Detects intraday volatility spikes, price swings, and yield movements.

Maintains a bounded in-memory collection (max 200 items) for API and testing.
Data is transient and does not survive application restarts. No database persistence.
"""
from __future__ import annotations

from collections import deque
import math
import statistics
from typing import Dict, List, Optional, Tuple, Union

from app.core.exceptions import ValidationError
from app.core.timezone import TimezoneService
from app.domain.anomaly import (
    AnomalyMetric,
    AnomalySeverity,
    DetectionMethod,
    NormalizedAnomaly,
)
from app.domain.instrument import NormalizedQuote

# ---------------------------------------------------------------------------
# Configurable Constants
# ---------------------------------------------------------------------------

MIN_HISTORY_POINTS = 10     # Minimum real observation count required for Z-score
ZSCORE_THRESHOLD = 2.5       # Z-score magnitude threshold to trigger statistical anomaly

# Default detection threshold percentages (>= threshold triggers anomaly)
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "EQUITY": 3.0,          # >= 3.0% price move
    "COMMODITY": 2.5,       # >= 2.5% price move
    "FOREX": 1.0,           # >= 1.0% price move
    "BOND": 0.10,           # >= 0.10% (10 bps) yield move
    "CRYPTO": 4.0,          # >= 4.0% price move
}


class AnomalyDetectionService:
    """
    Service layer for detecting market anomalies across asset classes.

    Stores detected anomalies in a bounded in-memory deque (max 200 items).
    Zero data fabrication — falls back cleanly to DETERMINISTIC_THRESHOLD
    when real historical series is unavailable or has zero variance.
    """

    def __init__(self, max_memory_items: int = 200) -> None:
        self._memory_store: deque[NormalizedAnomaly] = deque(maxlen=max_memory_items)
        self._anomaly_counter: int = 0

    def clear_in_memory_store(self) -> None:
        """Clear in-memory store for test isolation."""
        self._memory_store.clear()
        self._anomaly_counter = 0

    def get_anomaly_by_id(self, anomaly_id: str) -> Optional[NormalizedAnomaly]:
        """Retrieve a single anomaly from in-memory store by ID."""
        upper_id = anomaly_id.upper()
        for anom in self._memory_store:
            if anom.id.upper() == upper_id:
                return anom
        return None

    def get_in_memory_anomalies(

        self,
        asset_type: Optional[str] = None,
        min_change: Optional[float] = None,
        symbol: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[NormalizedAnomaly], int]:
        """
        Filter, paginate, and return detected anomalies from in-memory store.
        """
        if page < 1:
            raise ValidationError("Page number must be greater than or equal to 1")
        if page_size < 1 or page_size > 100:
            raise ValidationError("Page size must be between 1 and 100")

        filtered = list(self._memory_store)

        if asset_type:
            upper_asset = asset_type.upper()
            filtered = [a for a in filtered if a.asset_type.upper() == upper_asset]

        if symbol:
            upper_sym = symbol.upper()
            filtered = [a for a in filtered if a.symbol.upper() == upper_sym]

        if min_change is not None:
            filtered = [a for a in filtered if abs(a.change_percent) >= abs(min_change)]

        total = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]

        return paginated, total

    def detect_quote_anomaly(
        self,
        quote: NormalizedQuote,
        asset_type: str = "EQUITY",
        observation_window: str = "24h",
        historical_series: Optional[List[float]] = None,
    ) -> Optional[NormalizedAnomaly]:
        """
        Evaluate a single NormalizedQuote for price anomaly.
        """
        if quote.price is None or quote.change_percent is None:
            return None

        return self.detect_raw_anomaly(
            symbol=quote.symbol,
            asset_type=asset_type,
            current_value=quote.price,
            previous_value=quote.previous_close,
            change_percent=quote.change_percent,
            observation_window=observation_window,
            historical_series=historical_series,
        )

    def detect_raw_anomaly(
        self,
        symbol: str,
        asset_type: str,
        current_value: float,
        previous_value: Optional[float],
        change_percent: float,
        observation_window: str = "24h",
        historical_series: Optional[List[float]] = None,
    ) -> Optional[NormalizedAnomaly]:
        """
        Evaluate raw price/yield values for threshold or statistical anomaly.
        """
        upper_asset = asset_type.upper()
        threshold = DEFAULT_THRESHOLDS.get(upper_asset, 3.0)

        detection_method: Optional[DetectionMethod] = None
        z_score: Optional[float] = None
        is_anomaly = False

        # 1. Attempt Statistical Z-score if sufficient real historical series exists
        if historical_series and len(historical_series) >= MIN_HISTORY_POINTS:
            try:
                stdev = statistics.stdev(historical_series)
                mean = statistics.mean(historical_series)
                if stdev > 0:
                    z_score = (current_value - mean) / stdev
                    if abs(z_score) >= ZSCORE_THRESHOLD:
                        is_anomaly = True
                        detection_method = DetectionMethod.STATISTICAL_ZSCORE
            except statistics.StatisticsError:
                # Handle zero variance or numerical edge cases gracefully
                z_score = None

        # 2. Fall back to Deterministic Threshold check if Z-score did not trigger
        if not is_anomaly and abs(change_percent) >= threshold:
            is_anomaly = True
            detection_method = DetectionMethod.DETERMINISTIC_THRESHOLD

        if not is_anomaly or detection_method is None:
            return None

        # Determine metric type (PRICE_SPIKE vs PRICE_DROP vs YIELD_CHANGE)
        if upper_asset == "BOND":
            metric = AnomalyMetric.YIELD_CHANGE
        elif change_percent < 0:
            metric = AnomalyMetric.PRICE_DROP
        else:
            metric = AnomalyMetric.PRICE_SPIKE

        self._anomaly_counter += 1
        anomaly_id = f"ANOM-{symbol.upper().replace('/', '-')}-{self._anomaly_counter:04d}"

        now_utc = TimezoneService.now_utc().isoformat()
        now_ist = TimezoneService.now_ist().isoformat()

        details = {
            "threshold_used": threshold,
            "abs_change_percent": abs(change_percent),
        }
        if z_score is not None:
            details["z_score"] = round(z_score, 4)
            details["history_count"] = len(historical_series) if historical_series else 0

        anomaly = NormalizedAnomaly(
            id=anomaly_id,
            symbol=symbol.upper(),
            asset_type=upper_asset,
            metric=metric,
            current_value=current_value,
            previous_value=previous_value,
            change_percent=change_percent,
            observation_window=observation_window,
            severity=AnomalySeverity.MEDIUM,  # Default severity; 2D will refine severity mapping
            detection_method=detection_method,
            detected_at_utc=now_utc,
            detected_at_ist=now_ist,
            details=details,
        )

        # Store in transient bounded memory
        self._memory_store.appendleft(anomaly)
        return anomaly

    def detect_batch(
        self,
        quotes: List[NormalizedQuote],
        asset_type_map: Optional[Dict[str, str]] = None,
    ) -> List[NormalizedAnomaly]:
        """
        Evaluate a batch of quotes and return all detected anomalies.
        """
        anomalies = []
        asset_map = asset_type_map or {}
        for q in quotes:
            atype = asset_map.get(q.symbol, "EQUITY")
            anom = self.detect_quote_anomaly(quote=q, asset_type=atype)
            if anom:
                anomalies.append(anom)
        return anomalies
