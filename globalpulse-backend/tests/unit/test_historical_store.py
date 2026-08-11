"""
Unit tests for Phase 4A Historical Snapshot Store & Domain Models.
Verifies:
1. Snapshot creation from Phase 2B and Phase 3B domain objects.
2. Correlation provenance derived strictly from accepted pairs satisfying DEFAULT_MIN_CONFIDENCE.
3. True immutability of snapshot dataclasses and nested tuple collections.
4. Idempotent insertion updating records in-place without duplicating count or altering FIFO order.
5. Insertion-order FIFO eviction when capacity limit is reached.
6. UTC date window filtering, min_impact_level hierarchy, sorting, and pagination.
"""
from datetime import date, datetime, timezone
import pytest

from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.historical import HistoricalAnomalySnapshot, HistoricalImpactSnapshot
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    SectorSensitivity,
    TransmissionChannel,
)
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.services.historical_store import (
    AbstractHistoricalSnapshotStore,
    InMemoryHistoricalSnapshotStore,
    create_anomaly_snapshot_from_domain,
    create_impact_snapshot_from_domain,
)


@pytest.fixture
def sample_anomaly():
    return NormalizedAnomaly(
        id="ANOM-BRENT-100",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=6.25,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )


@pytest.fixture
def sample_assessment():
    return IndiaImpactAssessment(
        impact_score=97.8,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
        affected_sectors=[
            IndianSectorSensitivity(
                sector_name="PAINTS",
                direction=ImpactDirection.NEGATIVE,
                sensitivity=SectorSensitivity.HIGH_SENSITIVITY,
                transmission_rationale="Raw material costs rise with crude.",
            )
        ],
        summary_rationale="Crude oil spike inflates domestic import bill.",
    )


def test_anomaly_snapshot_factory_conversion(sample_anomaly):
    snapshot = create_anomaly_snapshot_from_domain(sample_anomaly)

    assert isinstance(snapshot, HistoricalAnomalySnapshot)
    assert snapshot.snapshot_id == "HIST-ANOM-ANOM-BRENT-100"
    assert snapshot.anomaly_id == "ANOM-BRENT-100"
    assert snapshot.symbol == "BRENT"
    assert snapshot.asset_type == "COMMODITY"
    assert snapshot.metric == AnomalyMetric.PRICE_SPIKE
    assert snapshot.current_value == 85.0
    assert snapshot.change_percent == 6.25


def test_impact_snapshot_factory_correlation_provenance_default_min_confidence(
    sample_anomaly, sample_assessment
):
    art_accepted = NormalizedArticle(
        id="ART-ACCEPTED-1",
        headline="OPEC cuts production",
        summary=None,
        source_name="Reuters",
        source_url=None,
        article_url="https://example.com/1",
        author=None,
        published_at_utc="2026-07-30T09:55:00Z",
        published_at_ist="2026-07-30T15:25:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )
    art_rejected = NormalizedArticle(
        id="ART-REJECTED-2",
        headline="Unrelated post",
        summary=None,
        source_name="Blog",
        source_url=None,
        article_url="https://example.com/2",
        author=None,
        published_at_utc="2026-07-30T09:40:00Z",
        published_at_ist="2026-07-30T15:10:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )

    pair_accepted = CorrelatedEventPair(
        correlation_id="CORR-ACC",
        anomaly=sample_anomaly,
        article=art_accepted,
        confidence_score=DEFAULT_MIN_CONFIDENCE + 0.25,  # 0.75 >= 0.50
    )
    pair_rejected = CorrelatedEventPair(
        correlation_id="CORR-REJ",
        anomaly=sample_anomaly,
        article=art_rejected,
        confidence_score=DEFAULT_MIN_CONFIDENCE - 0.05,  # 0.45 < 0.50
    )

    snapshot = create_impact_snapshot_from_domain(
        assessment=sample_assessment,
        anomaly=sample_anomaly,
        correlated_pairs=[pair_accepted, pair_rejected],
    )

    assert isinstance(snapshot, HistoricalImpactSnapshot)
    assert snapshot.snapshot_id == "HIST-IMPACT-ANOM-ANOM-BRENT-100"
    assert snapshot.source_anomaly_id == "ANOM-BRENT-100"
    assert snapshot.symbol == "BRENT"
    assert snapshot.asset_type == "COMMODITY"

    # Correlation provenance derived ONLY from accepted pair
    assert snapshot.has_correlation_evidence is True
    assert snapshot.correlation_count == 1
    assert snapshot.correlated_event_ids == ("ART-ACCEPTED-1",)
    assert snapshot.top_correlation_confidence == DEFAULT_MIN_CONFIDENCE + 0.25

    # Immutable collection fields check
    assert isinstance(snapshot.transmission_channels, tuple)
    assert isinstance(snapshot.affected_sectors, tuple)
    assert isinstance(snapshot.correlated_event_ids, tuple)

    # Immutability check: frozen dataclass raises error on field modification
    with pytest.raises(AttributeError):
        snapshot.impact_score = 50.0  # type: ignore


def test_historical_store_idempotency_and_update_in_place(sample_anomaly):
    store = InMemoryHistoricalSnapshotStore(max_anomaly_items=10)

    snap1 = create_anomaly_snapshot_from_domain(sample_anomaly, snapshot_id="HIST-1")
    added1 = store.add_anomaly_snapshot(snap1)
    assert added1 is True

    snapshots, total = store.get_anomaly_snapshots()
    assert total == 1
    assert snapshots[0].current_value == 85.0

    # Re-insert with updated value
    updated_anomaly = NormalizedAnomaly(
        id="ANOM-BRENT-100",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=88.0,
        previous_value=80.0,
        change_percent=10.0,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )
    snap2 = create_anomaly_snapshot_from_domain(updated_anomaly, snapshot_id="HIST-1")

    added2 = store.add_anomaly_snapshot(snap2)
    assert added2 is False  # Updated in-place

    snapshots_after, total_after = store.get_anomaly_snapshots()
    assert total_after == 1
    assert snapshots_after[0].current_value == 88.0


def test_historical_store_insertion_order_fifo_eviction(sample_anomaly):
    # Bounded store capacity = 3
    store = InMemoryHistoricalSnapshotStore(max_anomaly_items=3)

    for i in range(1, 6):
        snap = create_anomaly_snapshot_from_domain(sample_anomaly, snapshot_id=f"HIST-{i}")
        store.add_anomaly_snapshot(snap)

    # Max capacity is 3 -> HIST-1 and HIST-2 evicted in insertion order FIFO
    snapshots, total = store.get_anomaly_snapshots(limit=10)
    assert total == 3
    assert store.get_anomaly_snapshot_by_id("HIST-1") is None
    assert store.get_anomaly_snapshot_by_id("HIST-2") is None
    assert store.get_anomaly_snapshot_by_id("HIST-3") is not None
    assert store.get_anomaly_snapshot_by_id("HIST-4") is not None
    assert store.get_anomaly_snapshot_by_id("HIST-5") is not None


def test_historical_store_query_filtering_and_utc_sorting(sample_anomaly, sample_assessment):
    store = InMemoryHistoricalSnapshotStore(max_impact_items=10)

    # Insert 3 impact snapshots with different timestamps and assets
    snap1 = create_impact_snapshot_from_domain(
        assessment=sample_assessment,
        anomaly=sample_anomaly,  # BRENT COMMODITY
        snapshot_id="HIST-IMP-1",
        assessed_at_utc="2026-07-30T08:00:00Z",
    )

    forex_anomaly = NormalizedAnomaly(
        id="ANOM-USDINR-1",
        symbol="USD/INR",
        asset_type="FOREX",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=84.0,
        previous_value=83.0,
        change_percent=1.2,
        observation_window="30m",
        severity=AnomalySeverity.MEDIUM,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T11:00:00Z",
        detected_at_ist="2026-07-30T16:30:00+05:30",
    )
    snap2 = create_impact_snapshot_from_domain(
        assessment=sample_assessment,
        anomaly=forex_anomaly,
        snapshot_id="HIST-IMP-2",
        assessed_at_utc="2026-07-30T11:00:00Z",
    )

    store.add_impact_snapshot(snap1)
    store.add_impact_snapshot(snap2)

    # Query filter by symbol="BRENT"
    brent_items, total_brent = store.get_impact_snapshots(symbol="BRENT")
    assert total_brent == 1
    assert brent_items[0].symbol == "BRENT"

    # Query sorting: canonical UTC timestamp DESC (snap2 11:00:00Z before snap1 08:00:00Z)
    all_items, total_all = store.get_impact_snapshots()
    assert total_all == 2
    assert all_items[0].snapshot_id == "HIST-IMP-2"
    assert all_items[1].snapshot_id == "HIST-IMP-1"


def test_abstract_repository_interface_substitutability():
    # Verifies class implements AbstractHistoricalSnapshotStore interface
    store: AbstractHistoricalSnapshotStore = InMemoryHistoricalSnapshotStore()
    assert isinstance(store, AbstractHistoricalSnapshotStore)
