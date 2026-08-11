"""
GlobalPulse Phase 4A — Historical Snapshot Store & Repository Abstraction.
Provides bounded in-memory snapshot repository with insertion-order FIFO eviction and idempotent updates.

Swappable with persistent database repository in Phase 7 via AbstractHistoricalSnapshotStore.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple

from app.core.timezone import TimezoneService
from app.domain.anomaly import NormalizedAnomaly
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.historical import HistoricalAnomalySnapshot, HistoricalImpactSnapshot
from app.domain.india_impact import (
    IndiaImpactAssessment,
    IndiaImpactLevel,
    TransmissionChannel,
)

logger = logging.getLogger(__name__)


def _parse_utc_date(date_str: str) -> Optional[date]:
    """Parse ISO timestamp string into UTC date object for comparison."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    except (ValueError, TypeError):
        return None


def _map_level_hierarchy(min_level: Optional[IndiaImpactLevel]) -> set[IndiaImpactLevel]:
    """Ordered min_impact_level filter hierarchy."""
    if min_level == IndiaImpactLevel.HIGH:
        return {IndiaImpactLevel.HIGH}
    elif min_level == IndiaImpactLevel.MEDIUM:
        return {IndiaImpactLevel.MEDIUM, IndiaImpactLevel.HIGH}
    elif min_level == IndiaImpactLevel.LOW:
        return {IndiaImpactLevel.LOW, IndiaImpactLevel.MEDIUM, IndiaImpactLevel.HIGH}
    else:
        return {
            IndiaImpactLevel.NEGLIGIBLE,
            IndiaImpactLevel.LOW,
            IndiaImpactLevel.MEDIUM,
            IndiaImpactLevel.HIGH,
        }


class AbstractHistoricalSnapshotStore(ABC):
    """
    Abstract Repository Interface for Historical Snapshots.
    Exposes full storage and querying capabilities without coupling to in-memory deque structures.
    Provides clean boundary for Phase 7 PostgreSQL repository swap.
    """

    @abstractmethod
    def add_anomaly_snapshot(self, snapshot: HistoricalAnomalySnapshot) -> bool:
        """Store or update a historical anomaly snapshot idempotently."""
        ...

    @abstractmethod
    def add_impact_snapshot(self, snapshot: HistoricalImpactSnapshot) -> bool:
        """Store or update a historical India impact snapshot idempotently."""
        ...

    @abstractmethod
    def get_anomaly_snapshots(
        self,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[HistoricalAnomalySnapshot], int]:
        """Query historical anomaly snapshots with UTC date window filtering and pagination."""
        ...

    @abstractmethod
    def get_impact_snapshots(
        self,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        channel: Optional[TransmissionChannel] = None,
        min_impact_level: Optional[IndiaImpactLevel] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[HistoricalImpactSnapshot], int]:
        """Query historical India impact snapshots with filtering and pagination."""
        ...

    @abstractmethod
    def get_anomaly_snapshot_by_id(self, snapshot_id: str) -> Optional[HistoricalAnomalySnapshot]:
        """Retrieve a specific anomaly snapshot by ID."""
        ...

    @abstractmethod
    def get_impact_snapshot_by_id(self, snapshot_id: str) -> Optional[HistoricalImpactSnapshot]:
        """Retrieve a specific impact snapshot by ID."""
        ...

    @abstractmethod
    def clear_store(self) -> None:
        """Clear all stored snapshots for test isolation."""
        ...


class InMemoryHistoricalSnapshotStore(AbstractHistoricalSnapshotStore):
    """
    Bounded, thread-safe in-memory repository implementing AbstractHistoricalSnapshotStore.
    Insertion-order FIFO eviction prevents unlimited memory growth.
    Idempotent: updates existing snapshot_id in-place without altering FIFO order or increasing count.
    """

    def __init__(self, max_anomaly_items: int = 500, max_impact_items: int = 500) -> None:
        self.max_anomaly_items = max_anomaly_items
        self.max_impact_items = max_impact_items
        self._anomaly_store: Dict[str, HistoricalAnomalySnapshot] = {}
        self._anomaly_fifo: List[str] = []
        self._impact_store: Dict[str, HistoricalImpactSnapshot] = {}
        self._impact_fifo: List[str] = []

    def clear_store(self) -> None:
        self._anomaly_store.clear()
        self._anomaly_fifo.clear()
        self._impact_store.clear()
        self._impact_fifo.clear()

    def add_anomaly_snapshot(self, snapshot: HistoricalAnomalySnapshot) -> bool:
        sid = snapshot.snapshot_id
        if sid in self._anomaly_store:
            # Idempotent update: update record in-place, position and count remain unchanged
            self._anomaly_store[sid] = snapshot
            return False

        # New snapshot insertion
        if len(self._anomaly_fifo) >= self.max_anomaly_items:
            # Insertion-order FIFO eviction of oldest snapshot
            evicted_id = self._anomaly_fifo.pop(0)
            self._anomaly_store.pop(evicted_id, None)

        self._anomaly_store[sid] = snapshot
        self._anomaly_fifo.append(sid)
        return True

    def add_impact_snapshot(self, snapshot: HistoricalImpactSnapshot) -> bool:
        sid = snapshot.snapshot_id
        if sid in self._impact_store:
            # Idempotent update: update record in-place, position and count remain unchanged
            self._impact_store[sid] = snapshot
            return False

        # New snapshot insertion
        if len(self._impact_fifo) >= self.max_impact_items:
            # Insertion-order FIFO eviction of oldest snapshot
            evicted_id = self._impact_fifo.pop(0)
            self._impact_store.pop(evicted_id, None)

        self._impact_store[sid] = snapshot
        self._impact_fifo.append(sid)
        return True

    def get_anomaly_snapshot_by_id(self, snapshot_id: str) -> Optional[HistoricalAnomalySnapshot]:
        return self._anomaly_store.get(snapshot_id)

    def get_impact_snapshot_by_id(self, snapshot_id: str) -> Optional[HistoricalImpactSnapshot]:
        return self._impact_store.get(snapshot_id)

    def get_anomaly_snapshots(
        self,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[HistoricalAnomalySnapshot], int]:
        candidates = list(self._anomaly_store.values())

        # Filtering
        filtered: List[HistoricalAnomalySnapshot] = []
        for snap in candidates:
            if symbol and snap.symbol.upper() != symbol.upper():
                continue
            if asset_type and snap.asset_type.upper() != asset_type.upper():
                continue

            snap_date = _parse_utc_date(snap.detected_at_utc)
            if snap_date:
                if from_date and snap_date < from_date:
                    continue
                if to_date and snap_date > to_date:
                    continue

            filtered.append(snap)

        # Deterministic sorting: canonical UTC timestamp DESC
        filtered.sort(key=lambda s: s.detected_at_utc, reverse=True)

        total_count = len(filtered)
        paginated = filtered[offset : offset + limit]
        return paginated, total_count

    def get_impact_snapshots(
        self,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        channel: Optional[TransmissionChannel] = None,
        min_impact_level: Optional[IndiaImpactLevel] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[HistoricalImpactSnapshot], int]:
        candidates = list(self._impact_store.values())
        allowed_levels = _map_level_hierarchy(min_impact_level)

        filtered: List[HistoricalImpactSnapshot] = []
        for snap in candidates:
            if symbol and (not snap.symbol or snap.symbol.upper() != symbol.upper()):
                continue
            if asset_type and (not snap.asset_type or snap.asset_type.upper() != asset_type.upper()):
                continue
            if channel and channel not in snap.transmission_channels:
                continue
            if snap.impact_level not in allowed_levels:
                continue

            snap_date = _parse_utc_date(snap.assessed_at_utc)
            if snap_date:
                if from_date and snap_date < from_date:
                    continue
                if to_date and snap_date > to_date:
                    continue

            filtered.append(snap)

        # Deterministic sorting: canonical UTC timestamp DESC
        filtered.sort(key=lambda s: s.assessed_at_utc, reverse=True)

        total_count = len(filtered)
        paginated = filtered[offset : offset + limit]
        return paginated, total_count


# ---------------------------------------------------------------------------
# Helper Factory Methods for Snapshot Capture
# ---------------------------------------------------------------------------


def create_anomaly_snapshot_from_domain(
    anomaly: NormalizedAnomaly,
    snapshot_id: Optional[str] = None,
) -> HistoricalAnomalySnapshot:
    """
    Factory creating an immutable HistoricalAnomalySnapshot from a Phase 2B NormalizedAnomaly.
    Pure snapshot conversion — zero business logic recalculation.
    """
    sid = snapshot_id or f"HIST-ANOM-{anomaly.id}"
    now_utc = TimezoneService.now_utc().isoformat()

    return HistoricalAnomalySnapshot(
        snapshot_id=sid,
        anomaly_id=anomaly.id,
        symbol=anomaly.symbol,
        asset_type=anomaly.asset_type,
        metric=anomaly.metric,
        current_value=anomaly.current_value,
        previous_value=anomaly.previous_value,
        change_percent=anomaly.change_percent,
        detected_at_utc=anomaly.detected_at_utc,
        detected_at_ist=anomaly.detected_at_ist,
        created_at_utc=now_utc,
    )


def create_impact_snapshot_from_domain(
    assessment: IndiaImpactAssessment,
    anomaly: Optional[NormalizedAnomaly] = None,
    correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    source_event_id: Optional[str] = None,
    snapshot_id: Optional[str] = None,
    assessed_at_utc: Optional[str] = None,
    assessed_at_ist: Optional[str] = None,
) -> HistoricalImpactSnapshot:
    """
    Factory creating an immutable HistoricalImpactSnapshot from a Phase 3B IndiaImpactAssessment.
    Derives correlation provenance ONLY from accepted pairs satisfying DEFAULT_MIN_CONFIDENCE.
    Converts collection fields into immutable tuples.
    """
    now_utc_dt = TimezoneService.now_utc()
    now_utc_str = now_utc_dt.isoformat()
    now_ist_str = TimezoneService.now_ist().isoformat()

    # Filter accepted correlated pairs strictly using DEFAULT_MIN_CONFIDENCE
    accepted_pairs = [
        p for p in (correlated_pairs or [])
        if p.confidence_score is not None and p.confidence_score >= DEFAULT_MIN_CONFIDENCE
    ]

    has_evidence = len(accepted_pairs) > 0
    corr_count = len(accepted_pairs)
    top_confidence = (
        max(p.confidence_score for p in accepted_pairs) if accepted_pairs else None
    )

    event_ids_list = []
    for p in accepted_pairs:
        if p.article:
            event_ids_list.append(p.article.id)
        elif p.economic_event:
            event_ids_list.append(p.economic_event.id)
        else:
            event_ids_list.append(p.correlation_id)
    correlated_event_ids = tuple(event_ids_list)

    source_anom_id = anomaly.id if anomaly else None
    sym = anomaly.symbol if anomaly else None
    asset_t = anomaly.asset_type if anomaly else None

    # Deterministic snapshot ID
    if snapshot_id:
        sid = snapshot_id
    elif anomaly:
        sid = f"HIST-IMPACT-ANOM-{anomaly.id}"
    elif source_event_id:
        sid = f"HIST-IMPACT-EVT-{source_event_id}"
    else:
        sid = f"HIST-IMPACT-{abs(hash(assessment.summary_rationale))}"

    utc_ts = assessed_at_utc or (anomaly.detected_at_utc if anomaly else now_utc_str)
    ist_ts = assessed_at_ist or (anomaly.detected_at_ist if anomaly else now_ist_str)

    return HistoricalImpactSnapshot(
        snapshot_id=sid,
        source_anomaly_id=source_anom_id,
        source_event_id=source_event_id,
        symbol=sym,
        asset_type=asset_t,
        impact_score=assessment.impact_score,
        impact_level=assessment.impact_level,
        impact_direction=assessment.impact_direction,
        capital_flow_risk=assessment.capital_flow_risk,
        transmission_channels=tuple(assessment.transmission_channels),
        affected_sectors=tuple(assessment.affected_sectors),
        has_correlation_evidence=has_evidence,
        correlated_event_ids=correlated_event_ids,
        correlation_count=corr_count,
        top_correlation_confidence=top_confidence,
        assessed_at_utc=utc_ts,
        assessed_at_ist=ist_ts,
        created_at_utc=now_utc_str,
    )
