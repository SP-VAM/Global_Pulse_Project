"""
GlobalPulse Anomaly Domain Model
Internal normalized representation for market volatility anomalies and price/yield spikes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class AnomalyMetric(str, Enum):
    """Metric types tracked for unusual market activity."""

    PRICE_SPIKE = "PRICE_SPIKE"
    PRICE_DROP = "PRICE_DROP"
    VOLUME_SPIKE = "VOLUME_SPIKE"
    YIELD_CHANGE = "YIELD_CHANGE"


class AnomalySeverity(str, Enum):
    """Event / anomaly presentation severity level."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DetectionMethod(str, Enum):
    """
    Detection method used to identify the anomaly.

    DETERMINISTIC_THRESHOLD: Triggered by absolute or percentage threshold rules.
    STATISTICAL_ZSCORE: Triggered by standard deviation check against real historical observations.
    """

    DETERMINISTIC_THRESHOLD = "DETERMINISTIC_THRESHOLD"
    STATISTICAL_ZSCORE = "STATISTICAL_ZSCORE"


class ObservationWindow(str, Enum):
    """Time window over which the movement was observed."""

    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H24 = "24h"


@dataclass
class NormalizedAnomaly:
    """
    Provider-agnostic normalized market anomaly.

    Stores metric deltas, baseline values, observation window, severity, and detection method.
    Data is strictly normalized — never fabricated or simulated.
    """

    id: str                                           # Unique anomaly ID e.g. "ANOM-BTC-20260728-001"
    symbol: str                                       # Instrument ticker e.g. "BTC/USD", "AAPL", "BRENT"
    asset_type: str                                   # EQUITY | COMMODITY | FOREX | BOND | CRYPTO
    metric: AnomalyMetric                             # PRICE_SPIKE | PRICE_DROP | YIELD_CHANGE | etc.
    current_value: float                              # Price or yield at detection time
    previous_value: Optional[float]                   # Baseline price/yield prior to movement
    change_percent: float                             # Percentage change over window
    observation_window: str                           # e.g. "15m", "30m", "1h", "24h"
    severity: AnomalySeverity                         # HIGH | MEDIUM | LOW
    detection_method: DetectionMethod                 # DETERMINISTIC_THRESHOLD | STATISTICAL_ZSCORE
    detected_at_utc: str                              # ISO 8601 UTC timestamp
    detected_at_ist: str                              # ISO 8601 IST (Asia/Kolkata) timestamp
    details: Dict[str, Any] = field(default_factory=dict)  # Metadata e.g. threshold_used, z_score if available
