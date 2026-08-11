"""
GlobalPulse Event Correlation Service (Sub-Phase 2C)
Correlates detected market anomalies with news articles AND economic calendar releases.

Candidate-Type-Aware Normalized Scoring (0.00 to 1.00):
  - ARTICLE: Entity (0.40) + Category/Sector (0.25) + Country (0.15) + Time (0.20)
  - ECONOMIC_EVENT: Macro Relevance (0.35) + Country (0.25) + Category (0.20) + Time (0.20)

Strictly evaluates correlation evidence strength — NEVER claims causation.
Enforces exactly one candidate (article XOR economic_event) per CorrelatedEventPair.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import math
from typing import List, Optional, Tuple, Union

from app.domain.anomaly import NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.news import NormalizedArticle
from app.services.classification.asset_registry import get_asset_entry

logger = logging.getLogger(__name__)

# Time Window Bounds (in seconds)
WINDOW_PAST_MAX_SECONDS = 5400   # T - 90 minutes
WINDOW_FUTURE_MAX_SECONDS = 1800 # T + 30 minutes


def _parse_utc_datetime(iso_str: str) -> Optional[datetime]:
    """Parse ISO timestamp string into timezone-aware UTC datetime."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _calculate_time_proximity_score(
    anomaly_utc_str: str, candidate_utc_str: str
) -> Tuple[Optional[float], Optional[float]]:
    """
    Evaluate time proximity between anomaly time T and candidate event time T_c.

    Returns:
        (time_diff_seconds, proximity_score)
        If candidate is outside [T - 90m, T + 30m], returns (delta, None).
        At exact boundaries (T - 90m or T + 30m), proximity_score = 0.0.
    """
    dt_anom = _parse_utc_datetime(anomaly_utc_str)
    dt_cand = _parse_utc_datetime(candidate_utc_str)

    if not dt_anom or not dt_cand:
        return None, None

    delta_seconds = (dt_cand - dt_anom).total_seconds()

    # Outside inclusive window check
    if delta_seconds < -WINDOW_PAST_MAX_SECONDS or delta_seconds > WINDOW_FUTURE_MAX_SECONDS:
        return delta_seconds, None

    # Linear decay calculation
    if delta_seconds <= 0:
        # Pre-event window [T - 90m, T] -> decay from 1.0 at 0 down to 0.0 at -5400s
        score = 1.0 - (abs(delta_seconds) / WINDOW_PAST_MAX_SECONDS)
    else:
        # Post-event window [T, T + 30m] -> decay from 1.0 at 0 down to 0.0 at +1800s
        score = 1.0 - (delta_seconds / WINDOW_FUTURE_MAX_SECONDS)

    return delta_seconds, max(0.0, min(1.0, score))


class EventCorrelationService:
    """
    Service layer for correlating market anomalies with candidate events and articles.
    """

    def correlate_anomaly_with_article(
        self,
        anomaly: NormalizedAnomaly,
        article: NormalizedArticle,
        min_confidence: float = 0.50,
    ) -> Optional[CorrelatedEventPair]:
        """
        Evaluate correlation between a market anomaly and a news article candidate.
        """
        delta_sec, time_score = _calculate_time_proximity_score(
            anomaly.detected_at_utc, article.published_at_utc
        )
        if time_score is None:
            return None  # Outside time window

        asset = get_asset_entry(anomaly.symbol)
        match_reasons: List[str] = []

        # 1. Entity / Asset Match (0.40)
        entity_score = 0.0
        combined_text = f"{article.headline} {article.summary or ''}".lower()

        if asset:
            for alias in asset.aliases:
                if alias.lower() in combined_text:
                    entity_score = 1.0
                    match_reasons.append(f"Direct asset/entity match: '{alias}'")
                    break

        # 2. Category & Sector Overlap (0.25)
        cat_sector_score = 0.0
        art_cat = article.primary_category.value if hasattr(article.primary_category, "value") else str(article.primary_category)

        if asset:
            if asset.default_category.upper() in art_cat.upper() or any(asset.default_category.upper() in t.upper() for t in article.tags):
                cat_sector_score += 0.6
                match_reasons.append(f"Category alignment: '{art_cat}'")

            if asset.default_sector and any(asset.default_sector.lower() in s.lower() for s in article.sectors):
                cat_sector_score += 0.4
                match_reasons.append(f"Sector alignment: '{asset.default_sector}'")

            cat_sector_score = min(1.0, cat_sector_score)

        # 3. Country Relevance (0.15)
        country_score = 0.0
        if asset and asset.country:
            if any(asset.country.upper() in c.upper() for c in article.countries):
                country_score = 1.0
                match_reasons.append(f"Country tag overlap: '{asset.country}'")

        # 4. Time Proximity (0.20)
        mins = abs(int(delta_sec / 60)) if delta_sec else 0
        if time_score > 0:
            match_reasons.append(f"Time proximity: {mins} mins")

        # Total Normalized Confidence Score
        confidence = (
            (entity_score * 0.40) +
            (cat_sector_score * 0.25) +
            (country_score * 0.15) +
            (time_score * 0.20)
        )
        confidence = round(min(1.0, max(0.0, confidence)), 4)

        if confidence < min_confidence:
            return None

        correlation_id = f"CORR-{anomaly.id}-{article.id}"
        return CorrelatedEventPair(
            correlation_id=correlation_id,
            anomaly=anomaly,
            article=article,
            economic_event=None,
            candidate_type="ARTICLE",
            confidence_score=confidence,
            match_reasons=match_reasons,
        )

    def correlate_anomaly_with_economic_event(
        self,
        anomaly: NormalizedAnomaly,
        economic_event: NormalizedEconomicEvent,
        min_confidence: float = 0.50,
    ) -> Optional[CorrelatedEventPair]:
        """
        Evaluate correlation between a market anomaly and an economic calendar event.
        """
        delta_sec, time_score = _calculate_time_proximity_score(
            anomaly.detected_at_utc, economic_event.timestamp_utc
        )
        if time_score is None:
            return None  # Outside time window

        asset = get_asset_entry(anomaly.symbol)
        match_reasons: List[str] = []

        # 1. Macro Relevance (0.35)
        macro_score = 0.0
        event_cat_str = economic_event.category.value if hasattr(economic_event.category, "value") else str(economic_event.category)
        event_text = f"{economic_event.event} {event_cat_str}".lower()

        if asset:
            for kw in asset.macro_keywords:
                if kw.lower() in event_text:
                    macro_score = 1.0
                    match_reasons.append(f"Macro relevance signal: '{kw}'")
                    break

        # 2. Country Alignment (0.25)
        country_score = 0.0
        if asset and asset.country:
            if asset.country.upper() == economic_event.country.upper():
                country_score = 1.0
                match_reasons.append(f"Country release alignment: '{economic_event.country}'")
        elif economic_event.country.upper() in ["US", "IN"]:
            # US and India releases have global/regional macro alignment
            country_score = 0.5
            match_reasons.append(f"Regional macro alignment: '{economic_event.country}'")

        # 3. Category Overlap (0.20)
        category_score = 0.0
        if asset and asset.default_category.upper() in event_cat_str.upper():
            category_score = 1.0
            match_reasons.append(f"Macro category match: '{event_cat_str}'")

        # 4. Time Proximity (0.20)
        mins = abs(int(delta_sec / 60)) if delta_sec else 0
        if time_score > 0:
            match_reasons.append(f"Time proximity: {mins} mins")

        # Total Normalized Confidence Score
        confidence = (
            (macro_score * 0.35) +
            (country_score * 0.25) +
            (category_score * 0.20) +
            (time_score * 0.20)
        )
        confidence = round(min(1.0, max(0.0, confidence)), 4)

        if confidence < min_confidence:
            return None

        event_id = getattr(economic_event, "id", f"{economic_event.country}-{event_cat_str}")
        correlation_id = f"CORR-{anomaly.id}-{event_id}"

        return CorrelatedEventPair(
            correlation_id=correlation_id,
            anomaly=anomaly,
            article=None,
            economic_event=economic_event,
            candidate_type="ECONOMIC_EVENT",
            confidence_score=confidence,
            match_reasons=match_reasons,
        )


    def correlate_all_candidates(
        self,
        anomaly: NormalizedAnomaly,
        articles: List[NormalizedArticle],
        economic_events: Optional[List[NormalizedEconomicEvent]] = None,
        min_confidence: float = 0.50,
    ) -> List[CorrelatedEventPair]:
        """
        Correlate anomaly against both article and economic event candidates.
        Returns correlated pairs sorted by confidence_score descending.
        """
        pairs: List[CorrelatedEventPair] = []

        for art in articles:
            pair = self.correlate_anomaly_with_article(anomaly, art, min_confidence=min_confidence)
            if pair:
                pairs.append(pair)

        if economic_events:
            for ee in economic_events:
                pair = self.correlate_anomaly_with_economic_event(anomaly, ee, min_confidence=min_confidence)
                if pair:
                    pairs.append(pair)

        # Sort candidate pairs by confidence score descending
        pairs.sort(key=lambda p: p.confidence_score, reverse=True)
        return pairs
