"""
Unit tests for AnomalyDetectionService (Sub-Phase 2B).
Verifies boundary conditions, Z-score detection, zero-variance protection,
deterministic fallbacks, in-memory bounded storage, and UTC/IST timestamps.
"""
import pytest
from app.core.exceptions import ValidationError
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod
from app.domain.instrument import NormalizedQuote
from app.services.anomaly_service import AnomalyDetectionService


@pytest.fixture
def anomaly_service():
    service = AnomalyDetectionService()
    service.clear_in_memory_store()
    return service


def _make_quote(symbol="AAPL", price=200.0, prev_close=194.0, change_pct=3.0) -> NormalizedQuote:
    return NormalizedQuote(
        symbol=symbol,
        price=price,
        open=195.0,
        high=201.0,
        low=194.0,
        previous_close=prev_close,
        change=price - prev_close,
        change_percent=change_pct,
        currency="USD",
        timestamp_utc="2026-07-29T10:00:00Z",
        timestamp_ist="2026-07-29T15:30:00+05:30",
        source="FINNHUB",
    )


# ---------------------------------------------------------------------------
# 1. Exact Boundary Tests (>= Operator)
# ---------------------------------------------------------------------------


def test_equity_exact_boundary_detected(anomaly_service):
    q_pos = _make_quote(symbol="AAPL", change_pct=3.0)
    anom_pos = anomaly_service.detect_quote_anomaly(q_pos, asset_type="EQUITY")
    assert anom_pos is not None
    assert anom_pos.metric == AnomalyMetric.PRICE_SPIKE
    assert anom_pos.detection_method == DetectionMethod.DETERMINISTIC_THRESHOLD

    q_neg = _make_quote(symbol="AAPL", change_pct=-3.0)
    anom_neg = anomaly_service.detect_quote_anomaly(q_neg, asset_type="EQUITY")
    assert anom_neg is not None
    assert anom_neg.metric == AnomalyMetric.PRICE_DROP


def test_commodity_exact_boundary_detected(anomaly_service):
    q = _make_quote(symbol="BRENT", change_pct=2.5)
    anom = anomaly_service.detect_quote_anomaly(q, asset_type="COMMODITY")
    assert anom is not None
    assert anom.change_percent == 2.5

    q_neg = _make_quote(symbol="BRENT", change_pct=-2.5)
    anom_neg = anomaly_service.detect_quote_anomaly(q_neg, asset_type="COMMODITY")
    assert anom_neg is not None


def test_forex_exact_boundary_detected(anomaly_service):
    q = _make_quote(symbol="USD/INR", change_pct=1.0)
    anom = anomaly_service.detect_quote_anomaly(q, asset_type="FOREX")
    assert anom is not None
    assert anom.change_percent == 1.0


def test_bond_exact_boundary_detected(anomaly_service):
    # Bond yield change of 0.10% (10 bps)
    anom = anomaly_service.detect_raw_anomaly(
        symbol="US10Y",
        asset_type="BOND",
        current_value=4.30,
        previous_value=4.20,
        change_percent=0.10,
    )
    assert anom is not None
    assert anom.metric == AnomalyMetric.YIELD_CHANGE
    assert anom.change_percent == 0.10


def test_crypto_exact_boundary_detected(anomaly_service):
    q = _make_quote(symbol="BTC/USD", change_pct=4.0)
    anom = anomaly_service.detect_quote_anomaly(q, asset_type="CRYPTO")
    assert anom is not None
    assert anom.change_percent == 4.0


# ---------------------------------------------------------------------------
# 2. Sub-Threshold Non-Breach Tests
# ---------------------------------------------------------------------------


def test_sub_thresholds_not_detected(anomaly_service):
    assert anomaly_service.detect_quote_anomaly(_make_quote(change_pct=2.99), asset_type="EQUITY") is None
    assert anomaly_service.detect_quote_anomaly(_make_quote(change_pct=-2.99), asset_type="EQUITY") is None

    assert anomaly_service.detect_quote_anomaly(_make_quote(change_pct=2.49), asset_type="COMMODITY") is None
    assert anomaly_service.detect_quote_anomaly(_make_quote(change_pct=0.99), asset_type="FOREX") is None
    assert anomaly_service.detect_quote_anomaly(_make_quote(change_pct=3.99), asset_type="CRYPTO") is None

    anom_bond = anomaly_service.detect_raw_anomaly(
        symbol="US10Y", asset_type="BOND", current_value=4.29, previous_value=4.20, change_percent=0.09
    )
    assert anom_bond is None


# ---------------------------------------------------------------------------
# 3. Statistical Z-Score Tests & Fallbacks
# ---------------------------------------------------------------------------


def test_zscore_breach_detected(anomaly_service):
    # Historical mean ~ 100, stdev ~ 2. Current value = 110 -> Z = 5.0 >= 2.5
    history = [100.0, 101.0, 99.0, 100.5, 99.5, 100.0, 101.5, 98.5, 100.0, 100.0]
    anom = anomaly_service.detect_raw_anomaly(
        symbol="AAPL",
        asset_type="EQUITY",
        current_value=110.0,
        previous_value=100.0,
        change_percent=1.0,  # Below deterministic 3.0% threshold, but Z-score breaches!
        historical_series=history,
    )
    assert anom is not None
    assert anom.detection_method == DetectionMethod.STATISTICAL_ZSCORE
    assert "z_score" in anom.details
    assert anom.details["z_score"] > 2.5


def test_zscore_non_breach_does_not_emit_statistical_anomaly(anomaly_service):
    # Historical mean ~ 100, stdev ~ 2. Current value = 101 -> Z = 0.5 < 2.5
    history = [100.0, 101.0, 99.0, 100.5, 99.5, 100.0, 101.5, 98.5, 100.0, 100.0]
    anom = anomaly_service.detect_raw_anomaly(
        symbol="AAPL",
        asset_type="EQUITY",
        current_value=101.0,
        previous_value=100.0,
        change_percent=1.0,  # Below threshold 3.0% and Z < 2.5
        historical_series=history,
    )
    assert anom is None


def test_zero_variance_history_handled_safely(anomaly_service):
    # All historical points identical (stdev = 0). Must not crash with ZeroDivisionError!
    history = [100.0] * 12
    # Should fall back to deterministic threshold evaluation without error
    anom_sub = anomaly_service.detect_raw_anomaly(
        symbol="AAPL",
        asset_type="EQUITY",
        current_value=101.0,
        previous_value=100.0,
        change_percent=1.0,
        historical_series=history,
    )
    assert anom_sub is None

    # When deterministic threshold IS breached with zero variance history
    anom_breach = anomaly_service.detect_raw_anomaly(
        symbol="AAPL",
        asset_type="EQUITY",
        current_value=104.0,
        previous_value=100.0,
        change_percent=4.0,
        historical_series=history,
    )
    assert anom_breach is not None
    assert anom_breach.detection_method == DetectionMethod.DETERMINISTIC_THRESHOLD


def test_insufficient_history_falls_back_to_deterministic(anomaly_service):
    # Only 5 history points (less than MIN_HISTORY_POINTS 10)
    short_history = [100.0, 101.0, 99.0, 100.0, 100.5]
    anom = anomaly_service.detect_raw_anomaly(
        symbol="AAPL",
        asset_type="EQUITY",
        current_value=104.0,
        previous_value=100.0,
        change_percent=4.0,  # Breaches 3.0% threshold
        historical_series=short_history,
    )
    assert anom is not None
    assert anom.detection_method == DetectionMethod.DETERMINISTIC_THRESHOLD


# ---------------------------------------------------------------------------
# 4. In-Memory Store & Pagination Tests
# ---------------------------------------------------------------------------


def test_in_memory_store_bounded_limit():
    service = AnomalyDetectionService(max_memory_items=5)
    for i in range(10):
        service.detect_raw_anomaly(
            symbol=f"SYM{i}",
            asset_type="EQUITY",
            current_value=110.0,
            previous_value=100.0,
            change_percent=10.0,
        )

    anomalies, total = service.get_in_memory_anomalies(page=1, page_size=20)
    assert total == 5
    assert len(anomalies) == 5
    # Latest anomaly should be at the front
    assert anomalies[0].symbol == "SYM9"


def test_in_memory_store_filtering_and_pagination(anomaly_service):
    anomaly_service.detect_raw_anomaly("AAPL", "EQUITY", 110.0, 100.0, 10.0)
    anomaly_service.detect_raw_anomaly("BRENT", "COMMODITY", 80.0, 70.0, 5.0)
    anomaly_service.detect_raw_anomaly("MSFT", "EQUITY", 315.0, 300.0, 5.0)

    # Filter by asset_type
    eq_anoms, total_eq = anomaly_service.get_in_memory_anomalies(asset_type="EQUITY")
    assert total_eq == 2
    assert len(eq_anoms) == 2

    # Filter by symbol
    brent_anoms, total_brent = anomaly_service.get_in_memory_anomalies(symbol="BRENT")
    assert total_brent == 1
    assert brent_anoms[0].symbol == "BRENT"

    # Validation errors on invalid page parameters
    with pytest.raises(ValidationError):
        anomaly_service.get_in_memory_anomalies(page=0)

    with pytest.raises(ValidationError):
        anomaly_service.get_in_memory_anomalies(page_size=101)


# ---------------------------------------------------------------------------
# 5. Timestamp Normalization Test
# ---------------------------------------------------------------------------


def test_anomaly_timestamps_utc_and_ist(anomaly_service):
    q = _make_quote(symbol="TSLA", change_pct=5.0)
    anom = anomaly_service.detect_quote_anomaly(q, asset_type="EQUITY")
    assert anom is not None
    assert "T" in anom.detected_at_utc
    assert "+05:30" in anom.detected_at_ist
