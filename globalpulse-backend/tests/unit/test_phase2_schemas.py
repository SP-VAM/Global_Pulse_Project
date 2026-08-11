"""
Unit tests for Phase 2A domain models and Pydantic schemas.
Verifies serialization formatting (camelCase output) and model structures.
"""
from app.domain.anomaly import (
    AnomalyMetric,
    AnomalySeverity,
    DetectionMethod,
    NormalizedAnomaly,
)
from app.domain.correlation import CorrelatedEventPair
from app.domain.news import CompanyTag, GlobalEventCategory, NormalizedArticle
from app.schemas.anomaly import (
    AnomalyListResponse,
    AnomalyResponse,
    CorrelatedEventResponse,
)
from app.schemas.dashboard import DashboardFeedItem, DashboardItemType, ImpactLevel


def test_anomaly_response_camelcase_serialization():
    anomaly_res = AnomalyResponse(
        anomaly_id="anom-btc-001",
        symbol="BTC/USD",
        asset_type="CRYPTO",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=68450.0,
        previous_value=65691.0,
        change_percent=4.2,
        observation_window="15m",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-28T17:45:00Z",
        detected_at_ist="2026-07-28T23:15:00+05:30",
        details={"threshold_used": 3.0},
    )

    data = anomaly_res.model_dump(by_alias=True)
    assert data["anomalyId"] == "anom-btc-001"
    assert data["assetType"] == "CRYPTO"
    assert data["currentValue"] == 68450.0
    assert data["previousValue"] == 65691.0
    assert data["changePercent"] == 4.2
    assert data["observationWindow"] == "15m"
    assert data["severity"] == "HIGH"
    assert data["detectionMethod"] == "DETERMINISTIC_THRESHOLD"
    assert data["detectedAtUtc"] == "2026-07-28T17:45:00Z"
    assert data["detectedAtIst"] == "2026-07-28T23:15:00+05:30"


def test_dashboard_feed_item_phase2_fields_serialization():
    item = DashboardFeedItem(
        id="art-200",
        type=DashboardItemType.GLOBAL_EVENT,
        headline="Middle East oil supply tensions mount",
        summary="Crude oil futures jumped following supply disruptions.",
        category="ENERGY",
        impact_level=ImpactLevel.HIGH,
        countries=["SG"],
        companies=[],
        sectors=["Energy"],
        published_at_utc="2026-07-28T16:00:00Z",
        published_at_ist="2026-07-28T21:30:00+05:30",
        source_name="Reuters",
        article_url="https://reuters.com/article-200",
        financially_relevant=True,
        correlation_confidence=0.88,
        match_reasons=["Time proximity: 12m", "Shared sector: Energy"],
        correlated_anomalies=[
            {
                "anomalyId": "anom-brent-001",
                "symbol": "BRENT",
                "assetType": "COMMODITY",
                "changePercent": 3.8,
                "observationWindow": "30m",
                "severity": "HIGH",
                "detectionMethod": "DETERMINISTIC_THRESHOLD",
                "detectedAtUtc": "2026-07-28T16:00:00Z",
                "detectedAtIst": "2026-07-28T21:30:00+05:30",
            }
        ],
    )

    data = item.model_dump(by_alias=True)
    assert data["impactLevel"] == "HIGH"
    assert data["correlationConfidence"] == 0.88
    assert len(data["matchReasons"]) == 2
    assert len(data["correlatedAnomalies"]) == 1
    assert data["correlatedAnomalies"][0]["anomalyId"] == "anom-brent-001"
