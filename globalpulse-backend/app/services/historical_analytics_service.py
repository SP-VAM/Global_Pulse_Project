"""
GlobalPulse Phase 4B — Historical Query & Trend Analytics Engine.
Provides statistical calculations, distribution metrics, sector sensitivity hit summaries, and correlation evidence ratios.

Operates strictly over AbstractHistoricalSnapshotStore interface, exhaustively fetching repository pages.
Pure analytics logic — zero Phase 2 or Phase 3 business rule recalculation.
"""
from __future__ import annotations

from datetime import date
import logging
from typing import Dict, List, Optional

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
    ImpactDirection,
    IndiaImpactLevel,
    TransmissionChannel,
)
from app.services.historical_store import AbstractHistoricalSnapshotStore

logger = logging.getLogger(__name__)


class HistoricalAnalyticsService:
    """
    Pure statistical analytics calculation service.
    Exhaustively queries AbstractHistoricalSnapshotStore across pages to aggregate full populations.
    """

    def __init__(self, store: AbstractHistoricalSnapshotStore) -> None:
        self.store = store

    def _fetch_all_anomalies(
        self,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[HistoricalAnomalySnapshot]:
        """Paginate exhaustively through repository to retrieve entire matching anomaly dataset."""
        all_snapshots: List[HistoricalAnomalySnapshot] = []
        offset = 0
        limit = 100
        while True:
            page, total = self.store.get_anomaly_snapshots(
                symbol=symbol,
                asset_type=asset_type,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
                offset=offset,
            )
            all_snapshots.extend(page)
            offset += len(page)
            if len(all_snapshots) >= total or not page:
                break
        return all_snapshots

    def _fetch_all_impacts(
        self,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[HistoricalImpactSnapshot]:
        """Paginate exhaustively through repository to retrieve entire matching impact dataset."""
        all_snapshots: List[HistoricalImpactSnapshot] = []
        offset = 0
        limit = 100
        while True:
            page, total = self.store.get_impact_snapshots(
                symbol=symbol,
                asset_type=asset_type,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
                offset=offset,
            )
            all_snapshots.extend(page)
            offset += len(page)
            if len(all_snapshots) >= total or not page:
                break
        return all_snapshots

    def compute_trend_analytics(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        symbol: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> HistoricalTrendAnalytics:
        """
        Compute aggregate trend analytics over complete matching historical snapshot population.
        Propagates query filters consistently to both anomaly and impact datasets.
        """
        anomalies = self._fetch_all_anomalies(
            symbol=symbol, asset_type=asset_type, from_date=from_date, to_date=to_date
        )
        impacts = self._fetch_all_impacts(
            symbol=symbol, asset_type=asset_type, from_date=from_date, to_date=to_date
        )

        n_anomalies = len(anomalies)
        n_impacts = len(impacts)

        # 1. Average and Peak Score
        if n_impacts > 0:
            avg_score = round(sum(s.impact_score for s in impacts) / n_impacts, 1)
            peak_score = max(s.impact_score for s in impacts)
        else:
            avg_score = 0.0
            peak_score = 0.0

        # 2. Impact Level Breakdown (Fixed Order: HIGH, MEDIUM, LOW, NEGLIGIBLE)
        level_counts_map = {lvl: 0 for lvl in IndiaImpactLevel}
        for s in impacts:
            level_counts_map[s.impact_level] += 1

        level_counts_tuple = tuple(
            ImpactLevelCount(impact_level=lvl, count=level_counts_map[lvl])
            for lvl in [
                IndiaImpactLevel.HIGH,
                IndiaImpactLevel.MEDIUM,
                IndiaImpactLevel.LOW,
                IndiaImpactLevel.NEGLIGIBLE,
            ]
        )

        # 3. Asset Class Frequencies (Deterministic Sort: count DESC, asset_type ASC)
        asset_counts: Dict[str, int] = {}
        for a in anomalies:
            asset_counts[a.asset_type] = asset_counts.get(a.asset_type, 0) + 1

        asset_freq_list = [
            AssetClassFrequency(
                asset_type=at,
                count=cnt,
                ratio=round(cnt / n_anomalies, 2) if n_anomalies > 0 else 0.0,
            )
            for at, cnt in asset_counts.items()
        ]
        asset_freq_list.sort(key=lambda x: (-x.count, x.asset_type))

        # 4. Transmission Channel Distributions (Prevalence Ratio, counted at most once per assessment)
        channel_counts: Dict[TransmissionChannel, int] = {}
        for imp in impacts:
            unique_channels = set(imp.transmission_channels)
            for ch in unique_channels:
                channel_counts[ch] = channel_counts.get(ch, 0) + 1

        channel_dist_list = [
            ChannelDistribution(
                channel=ch,
                count=cnt,
                assessment_ratio=round(cnt / n_impacts, 2) if n_impacts > 0 else 0.0,
            )
            for ch, cnt in channel_counts.items()
        ]
        channel_dist_list.sort(key=lambda x: (-x.count, x.channel.value))

        # 5. Sector Hit Summaries (Complete accounting with neutral_hits and deterministic tie-breaking)
        sector_map: Dict[str, Dict[str, int]] = {}
        for imp in impacts:
            for sec in imp.affected_sectors:
                sname = sec.sector_name
                if sname not in sector_map:
                    sector_map[sname] = {"pos": 0, "neg": 0, "mix": 0, "neu": 0}
                if sec.direction == ImpactDirection.POSITIVE:
                    sector_map[sname]["pos"] += 1
                elif sec.direction == ImpactDirection.NEGATIVE:
                    sector_map[sname]["neg"] += 1
                elif sec.direction == ImpactDirection.MIXED:
                    sector_map[sname]["mix"] += 1
                else:
                    sector_map[sname]["neu"] += 1

        sector_summary_list: List[SectorHitSummary] = []
        for sname, counts in sector_map.items():
            pos, neg, mix, neu = counts["pos"], counts["neg"], counts["mix"], counts["neu"]
            tot = pos + neg + mix + neu

            # Deterministic Primary Direction Resolution:
            # Unique max -> that direction; 2+ tied maxes -> MIXED; total_hits == 0 -> NEUTRAL
            if tot == 0:
                pdir = ImpactDirection.NEUTRAL
            else:
                dir_counts = [
                    (ImpactDirection.POSITIVE, pos),
                    (ImpactDirection.NEGATIVE, neg),
                    (ImpactDirection.MIXED, mix),
                    (ImpactDirection.NEUTRAL, neu),
                ]
                max_cnt = max(cnt for _, cnt in dir_counts)
                max_dirs = [d for d, cnt in dir_counts if cnt == max_cnt]
                pdir = max_dirs[0] if len(max_dirs) == 1 else ImpactDirection.MIXED

            sector_summary_list.append(
                SectorHitSummary(
                    sector_name=sname,
                    total_hits=tot,
                    negative_hits=neg,
                    positive_hits=pos,
                    mixed_hits=mix,
                    neutral_hits=neu,
                    primary_direction=pdir,
                )
            )
        sector_summary_list.sort(key=lambda x: (-x.total_hits, x.sector_name))

        # 6. Correlation Evidence Ratio
        evidence_count = sum(1 for s in impacts if s.has_correlation_evidence)
        evidence_ratio = round(evidence_count / n_impacts, 2) if n_impacts > 0 else 0.0

        return HistoricalTrendAnalytics(
            total_anomalies_evaluated=n_anomalies,
            total_impact_assessments_evaluated=n_impacts,
            average_impact_score=avg_score,
            peak_impact_score=peak_score,
            impact_level_counts=tuple(level_counts_tuple),
            asset_class_frequencies=tuple(asset_freq_list),
            channel_distributions=tuple(channel_dist_list),
            sector_hit_summaries=tuple(sector_summary_list),
            correlated_evidence_count=evidence_count,
            correlation_evidence_ratio=evidence_ratio,
        )
