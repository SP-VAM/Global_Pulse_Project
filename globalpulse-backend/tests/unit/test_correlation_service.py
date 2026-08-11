"""
Unit tests for EventCorrelationService (Sub-Phase 2C).
Verifies candidate-type-aware scoring, XOR candidate invariants, centralized asset registry,
exact T-90m/T+30m boundary time proximity, weak match filtering, and candidate ranking.
"""
from datetime import datetime, timedelta, timezone
import pytest

from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.news import CompanyTag, GlobalEventCategory, NormalizedArticle
from app.services.classification.asset_registry import ASSET_REGISTRY, get_asset_entry
from app.services.correlation_service import EventCorrelationService


@pytest.fixture
def correlation_service():
    return EventCorrelationService()


def _make_anomaly(
    id="anom-1",
    symbol="AAPL",
    asset_type="EQUITY",
    timestamp_utc="2026-07-29T12:00:00Z",
) -> NormalizedAnomaly:
    return NormalizedAnomaly(
        id=id,
        symbol=symbol,
        asset_type=asset_type,
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=210.0,
        previous_value=200.0,
        change_percent=5.0,
        observation_window="15m",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc=timestamp_utc,
        detected_at_ist="2026-07-29T17:30:00+05:30",
    )


def _make_article(
    id="art-1",
    headline="Apple releases record breaking iPhone quarterly sales",
    summary="Technology sector surges following Apple earnings announcement.",
    published_utc="2026-07-29T11:45:00Z",  # 15 mins before anomaly
    category=GlobalEventCategory.TECHNOLOGY,
    countries=None,
    companies=None,
    sectors=None,
) -> NormalizedArticle:
    return NormalizedArticle(
        id=id,
        headline=headline,
        summary=summary,
        source_name="Reuters",
        source_url="https://reuters.com",
        article_url=f"https://reuters.com/{id}",
        author="Reporter",
        published_at_utc=published_utc,
        published_at_ist="2026-07-29T17:15:00+05:30",
        primary_category=category,
        tags=["TECHNOLOGY"],
        countries=countries or ["US"],
        companies=companies or [CompanyTag("Apple", "Technology", "US")],
        sectors=sectors or ["Technology"],
        keywords=["apple", "iphone"],
        relevance_score=5,
        source="NEWSAPI",
    )


from app.domain.economic_event import EconomicEventCategory, EconomicImportance, NormalizedEconomicEvent


def _make_economic_event(
    id="ee-1",
    event="Fed Federal Funds Rate Decision",
    category=EconomicEventCategory.CENTRAL_BANK,
    country="US",
    date_utc="2026-07-29T11:50:00Z",  # 10 mins before anomaly
) -> NormalizedEconomicEvent:
    return NormalizedEconomicEvent(
        id=id,
        country=country,
        event=event,
        category=category,
        importance=EconomicImportance.HIGH,
        actual=5.25,
        forecast=5.25,
        previous=5.00,
        unit="%",
        timestamp_utc=date_utc,
        timestamp_ist="2026-07-29T17:20:00+05:30",
        source="TRADING_ECONOMICS",
    )



# ---------------------------------------------------------------------------
# 1. Centralized Asset Registry Tests
# ---------------------------------------------------------------------------


def test_asset_registry_lookup_and_alias_separation():
    entry = get_asset_entry("BRENT")
    assert entry is not None
    assert "brent crude" in entry.aliases
    # "opec" is a macro keyword, NOT a direct ticker alias!
    assert "opec" not in entry.aliases
    assert "opec" in entry.macro_keywords
    # BRENT has no intrinsic domestic country tag
    assert entry.country is None


# ---------------------------------------------------------------------------
# 2. XOR Candidate Invariant Tests
# ---------------------------------------------------------------------------


def test_correlated_pair_xor_invariant():
    anom = _make_anomaly()
    art = _make_article()
    ee = _make_economic_event()

    # Valid with article ONLY
    pair_art = CorrelatedEventPair("corr-1", anom, article=art, candidate_type="ARTICLE")
    assert pair_art.candidate_type == "ARTICLE"

    # Valid with economic_event ONLY
    pair_ee = CorrelatedEventPair("corr-2", anom, economic_event=ee, candidate_type="ECONOMIC_EVENT")
    assert pair_ee.candidate_type == "ECONOMIC_EVENT"

    # Invalid with BOTH or NEITHER -> raises ValueError
    with pytest.raises(ValueError, match="exactly one candidate"):
        CorrelatedEventPair("corr-bad", anom, article=art, economic_event=ee)

    with pytest.raises(ValueError, match="exactly one candidate"):
        CorrelatedEventPair("corr-empty", anom)


# ---------------------------------------------------------------------------
# 3. Article Candidate Correlation & Scoring
# ---------------------------------------------------------------------------


def test_article_correlation_high_confidence(correlation_service):
    anom = _make_anomaly(symbol="AAPL", timestamp_utc="2026-07-29T12:00:00Z")
    art = _make_article(published_utc="2026-07-29T11:45:00Z")  # 15m before

    pair = correlation_service.correlate_anomaly_with_article(anom, art)
    assert pair is not None
    assert pair.candidate_type == "ARTICLE"
    assert pair.confidence_score >= 0.70
    assert any("Direct asset/entity match" in r for r in pair.match_reasons)


# ---------------------------------------------------------------------------
# 4. Economic Event Candidate Correlation & Scoring
# ---------------------------------------------------------------------------


def test_economic_event_correlation_high_confidence(correlation_service):
    anom = _make_anomaly(symbol="US10Y", asset_type="BOND", timestamp_utc="2026-07-29T12:00:00Z")
    ee = _make_economic_event(date_utc="2026-07-29T11:50:00Z")  # 10m before

    pair = correlation_service.correlate_anomaly_with_economic_event(anom, ee)
    assert pair is not None
    assert pair.candidate_type == "ECONOMIC_EVENT"
    assert pair.confidence_score >= 0.70
    assert any("Macro relevance signal" in r for r in pair.match_reasons)


# ---------------------------------------------------------------------------
# 5. Exact Time Window Boundary Tests ([T - 90m, T + 30m])
# ---------------------------------------------------------------------------


def test_exact_time_boundary_inclusive_with_entity_match(correlation_service):
    # Anomaly at 12:00:00. Exact -90m boundary is 10:30:00Z.
    anom = _make_anomaly(symbol="AAPL", timestamp_utc="2026-07-29T12:00:00Z")
    art_exact_past = _make_article(published_utc="2026-07-29T10:30:00Z")

    # Time score is 0.0 at boundary, but entity (0.40) + sector/cat (0.25) + country (0.15) = 0.80 >= min_confidence 0.50
    pair = correlation_service.correlate_anomaly_with_article(anom, art_exact_past, min_confidence=0.50)
    assert pair is not None
    assert pair.confidence_score == 0.80



def test_exact_time_boundary_zero_other_signals_filtered_out(correlation_service):
    # Article at exact -90m boundary but NO entity/category/country match -> time score 0.0, total 0.0
    anom = _make_anomaly(symbol="AAPL", timestamp_utc="2026-07-29T12:00:00Z")
    art_unrelated = _make_article(
        headline="Unrelated gardening news in Spain",
        summary="Weather report for Southern Europe",
        published_utc="2026-07-29T10:30:00Z",
        category=GlobalEventCategory.OTHER,
        countries=["ES"],
        companies=[],
        sectors=[],
    )

    pair = correlation_service.correlate_anomaly_with_article(anom, art_unrelated, min_confidence=0.50)
    assert pair is None


def test_just_outside_time_boundaries_rejected(correlation_service):
    anom = _make_anomaly(symbol="AAPL", timestamp_utc="2026-07-29T12:00:00Z")

    # 90m + 1 second before (10:29:59Z) -> rejected
    art_too_early = _make_article(published_utc="2026-07-29T10:29:59Z")
    assert correlation_service.correlate_anomaly_with_article(anom, art_too_early) is None

    # 30m + 1 second after (12:30:01Z) -> rejected
    art_too_late = _make_article(published_utc="2026-07-29T12:30:01Z")
    assert correlation_service.correlate_anomaly_with_article(anom, art_too_late) is None


# ---------------------------------------------------------------------------
# 6. Weak Match Filtering & Ranking
# ---------------------------------------------------------------------------


def test_weak_time_only_match_filtered_out(correlation_service):
    # Time proximity match ONLY (time score 1.0 * 0.20 = 0.20) with no entity/category/country match
    anom = _make_anomaly(symbol="AAPL", timestamp_utc="2026-07-29T12:00:00Z")
    art_weak = _make_article(
        headline="Local municipal election results announced",
        summary="City council vote completed.",
        published_utc="2026-07-29T12:00:00Z",  # Exact same minute!
        category=GlobalEventCategory.OTHER,
        countries=["ES"],
        companies=[],
        sectors=[],
    )

    # 0.20 < min_confidence 0.50 -> filtered out!
    pair = correlation_service.correlate_anomaly_with_article(anom, art_weak, min_confidence=0.50)
    assert pair is None


def test_correlate_all_candidates_ranking(correlation_service):
    anom = _make_anomaly(symbol="AAPL", timestamp_utc="2026-07-29T12:00:00Z")
    art_high = _make_article(id="art-high", headline="Apple iPhone quarterly earnings break all time records", published_utc="2026-07-29T11:55:00Z")
    art_med = _make_article(id="art-med", headline="Tech sector stocks see moderate buying interest", summary="Broad technology update.", published_utc="2026-07-29T11:30:00Z", companies=[])

    pairs = correlation_service.correlate_all_candidates(anom, articles=[art_med, art_high], min_confidence=0.30)
    assert len(pairs) == 2
    # Highest confidence candidate must be first!
    assert pairs[0].article.id == "art-high"
    assert pairs[0].confidence_score > pairs[1].confidence_score
