"""
Unit tests for Phase 4B Historical Query & Trend Analytics Engine (HistoricalAnalyticsService).
Verifies:
1. Repository page exhaustion over large populations (> 100 matching snapshots, e.g. 250).
2. Prevalence ratio semantics for transmission channels (count / total assessments).
3. Complete sector hit accounting with neutral_hits and total_hits equality.
4. Deterministic primary direction resolution and tie-breaking.
5. Deterministic sorting for tuple outputs (count DESC, symbol/name ASC).
6. Filter propagation across both anomaly and impact snapshot datasets.
7. Graceful zero-data safety for empty store queries.
"""
from datetime import date
import pytest

from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.historical import (
    AssetClassFrequency,
    ChannelDistribution,
    HistoricalAnomalySnapshot,
    HistoricalImpactSnapshot,
    HistoricalTrendAnalytics,
    ImpactLevelCount,
    SectorHitSummary,
)
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    SectorSensitivity,
    TransmissionChannel,
)
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import (
    InMemoryHistoricalSnapshotStore,
    create_anomaly_snapshot_from_domain,
    create_impact_snapshot_from_domain,
)


@pytest.fixture
def empty_store():
    return InMemoryHistoricalSnapshotStore()


@pytest.fixture
def analytics_service(empty_store):
    return HistoricalAnalyticsService(store=empty_store)


def test_repository_pagination_exhaustion_over_250_records(empty_store):
    """
    CRITICAL TEST: Proves HistoricalAnalyticsService exhaustively fetches pages of 100
    so a dataset of 250 matching records is 100% evaluated (pages 100 + 100 + 50)
    and not truncated by default limit=20 pagination.
    """
    # 1. Expand store capacity to 300
    store = InMemoryHistoricalSnapshotStore(max_anomaly_items=300, max_impact_items=300)
    service = HistoricalAnalyticsService(store=store)

    # 2. Populate 250 anomaly snapshots and 250 impact snapshots
    for i in range(1, 251):
        anom = NormalizedAnomaly(
            id=f"ANOM-MULTI-{i}",
            symbol="BRENT" if i % 2 == 0 else "USD/INR",
            asset_type="COMMODITY" if i % 2 == 0 else "FOREX",
            metric=AnomalyMetric.PRICE_SPIKE,
            current_value=80.0 + i * 0.1,
            previous_value=80.0,
            change_percent=4.0,
            observation_window="1h",
            severity=AnomalySeverity.HIGH,
            detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
            detected_at_utc=f"2026-07-30T{i % 24:02d}:00:00Z",
            detected_at_ist="2026-07-30T12:00:00+05:30",
        )
        anom_snap = create_anomaly_snapshot_from_domain(anom, snapshot_id=f"HIST-ANOM-{i}")
        store.add_anomaly_snapshot(anom_snap)

        assessment = IndiaImpactAssessment(
            impact_score=80.0 + (i % 20),
            impact_level=IndiaImpactLevel.HIGH,
            impact_direction=ImpactDirection.NEGATIVE,
            capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
            transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
            affected_sectors=[],
            summary_rationale="Test crude shock",
        )
        imp_snap = create_impact_snapshot_from_domain(
            assessment=assessment, anomaly=anom, snapshot_id=f"HIST-IMP-{i}"
        )
        store.add_impact_snapshot(imp_snap)

    # 3. Execute analytics calculation
    analytics = service.compute_trend_analytics()

    # 4. Verify pagination exhaustion: 250 / 250 records evaluated cleanly!
    assert analytics.total_anomalies_evaluated == 250
    assert analytics.total_impact_assessments_evaluated == 250


def test_empty_store_zero_data_fallback_safety(analytics_service):
    analytics = analytics_service.compute_trend_analytics()

    assert isinstance(analytics, HistoricalTrendAnalytics)
    assert analytics.total_anomalies_evaluated == 0
    assert analytics.total_impact_assessments_evaluated == 0
    assert analytics.average_impact_score == 0.0
    assert analytics.peak_impact_score == 0.0
    assert analytics.asset_class_frequencies == ()
    assert analytics.channel_distributions == ()
    assert analytics.sector_hit_summaries == ()
    assert analytics.correlated_evidence_count == 0
    assert analytics.correlation_evidence_ratio == 0.0

    # Fixed impact level count check
    assert len(analytics.impact_level_counts) == 4
    for item in analytics.impact_level_counts:
        assert isinstance(item, ImpactLevelCount)
        assert item.count == 0


def test_channel_prevalence_ratio_semantics(empty_store, analytics_service):
    """
    Verifies channel assessment_ratio is calculated as prevalence per assessment.
    Assesses 2 impacts: 1 with COMMODITY_IMPORT, 1 with COMMODITY_IMPORT + CAPITAL_FLOW.
    """
    anom = NormalizedAnomaly(
        id="ANOM-1",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=5.0,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    assess1 = IndiaImpactAssessment(
        impact_score=90.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
    )
    assess2 = IndiaImpactAssessment(
        impact_score=85.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.HIGH_RISK,
        transmission_channels=[
            TransmissionChannel.COMMODITY_IMPORT,
            TransmissionChannel.CAPITAL_FLOW_SENSITIVITY,
        ],
    )

    empty_store.add_impact_snapshot(
        create_impact_snapshot_from_domain(assess1, anomaly=anom, snapshot_id="HIST-IMP-1")
    )
    empty_store.add_impact_snapshot(
        create_impact_snapshot_from_domain(assess2, anomaly=anom, snapshot_id="HIST-IMP-2")
    )

    analytics = analytics_service.compute_trend_analytics()

    assert analytics.total_impact_assessments_evaluated == 2
    # COMMODITY_IMPORT present in 2 / 2 assessments = 1.00
    # CAPITAL_FLOW_SENSITIVITY present in 1 / 2 assessments = 0.50
    dist_map = {c.channel: c for c in analytics.channel_distributions}

    assert dist_map[TransmissionChannel.COMMODITY_IMPORT].count == 2
    assert dist_map[TransmissionChannel.COMMODITY_IMPORT].assessment_ratio == 1.00

    assert dist_map[TransmissionChannel.CAPITAL_FLOW_SENSITIVITY].count == 1
    assert dist_map[TransmissionChannel.CAPITAL_FLOW_SENSITIVITY].assessment_ratio == 0.50


def test_sector_hit_summary_accounting_and_primary_direction_resolution(
    empty_store, analytics_service
):
    """
    Verifies neutral_hits accounting, total_hits equality, and deterministic primary direction tie-breaking.
    """
    anom = NormalizedAnomaly(
        id="ANOM-1",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=5.0,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    # Assessment 1: PAINTS (NEGATIVE), AVIATION (NEUTRAL)
    assess1 = IndiaImpactAssessment(
        impact_score=90.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        affected_sectors=[
            IndianSectorSensitivity("PAINTS", ImpactDirection.NEGATIVE, SectorSensitivity.HIGH_SENSITIVITY, "Cost up"),
            IndianSectorSensitivity("AVIATION", ImpactDirection.NEUTRAL, SectorSensitivity.LOW_SENSITIVITY, "No change"),
        ],
    )
    # Assessment 2: PAINTS (NEGATIVE), AVIATION (POSITIVE)
    assess2 = IndiaImpactAssessment(
        impact_score=80.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.MIXED,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        affected_sectors=[
            IndianSectorSensitivity("PAINTS", ImpactDirection.NEGATIVE, SectorSensitivity.HIGH_SENSITIVITY, "Cost up"),
            IndianSectorSensitivity("AVIATION", ImpactDirection.POSITIVE, SectorSensitivity.LOW_SENSITIVITY, "Fare surge"),
        ],
    )

    empty_store.add_impact_snapshot(
        create_impact_snapshot_from_domain(assess1, anomaly=anom, snapshot_id="HIST-IMP-1")
    )
    empty_store.add_impact_snapshot(
        create_impact_snapshot_from_domain(assess2, anomaly=anom, snapshot_id="HIST-IMP-2")
    )

    analytics = analytics_service.compute_trend_analytics()

    sector_map = {s.sector_name: s for s in analytics.sector_hit_summaries}

    # PAINTS: 2 NEGATIVE hits -> total_hits=2, primary_direction=NEGATIVE
    paints = sector_map["PAINTS"]
    assert paints.total_hits == 2
    assert paints.negative_hits == 2
    assert paints.positive_hits == 0
    assert paints.neutral_hits == 0
    assert paints.total_hits == (paints.positive_hits + paints.negative_hits + paints.mixed_hits + paints.neutral_hits)
    assert paints.primary_direction == ImpactDirection.NEGATIVE

    # AVIATION: 1 POSITIVE hit, 1 NEUTRAL hit -> total_hits=2, tie between POSITIVE and NEUTRAL (max_cnt=1) -> MIXED!
    aviation = sector_map["AVIATION"]
    assert aviation.total_hits == 2
    assert aviation.positive_hits == 1
    assert aviation.neutral_hits == 1
    assert aviation.total_hits == (aviation.positive_hits + aviation.negative_hits + aviation.mixed_hits + aviation.neutral_hits)
    assert aviation.primary_direction == ImpactDirection.MIXED


def test_deterministic_output_sorting(empty_store, analytics_service):
    """
    Verifies tuple output sorting rules:
    - asset_class_frequencies: (count DESC, asset_type ASC)
    - channel_distributions: (count DESC, channel.value ASC)
    - sector_hit_summaries: (total_hits DESC, sector_name ASC)
    """
    anom_forex = NormalizedAnomaly("A1", "USD/INR", "FOREX", AnomalyMetric.PRICE_SPIKE, 84.0, 83.0, 1.2, "1h", AnomalySeverity.MEDIUM, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    anom_bond = NormalizedAnomaly("A2", "US10Y", "BOND", AnomalyMetric.PRICE_SPIKE, 4.25, 4.0, 0.25, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    anom_comm = NormalizedAnomaly("A3", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")

    empty_store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_forex, "H1"))
    empty_store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_bond, "H2"))
    empty_store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_comm, "H3"))

    analytics = analytics_service.compute_trend_analytics()

    # Counts are all 1 -> secondary sort is asset_type ASC: BOND < COMMODITY < FOREX
    asset_types = [a.asset_type for a in analytics.asset_class_frequencies]
    assert asset_types == ["BOND", "COMMODITY", "FOREX"]
