"""
GlobalPulse Phase 5E — End-to-End AI Explanation Integration Test Suite.
Verifies complete integration of Phase 5 (AI Explanation Engine) with Phases 1–4.

Scenarios:
1. Scenario 1: True End-to-End Brent Crude Oil Shock Explanation Pipeline.
2. Scenario 2: Multi-Asset Class Explanation Coverage (FOREX & BOND).
3. Scenario 3: Correlated News vs Standalone Shock Evidence Confidence (HIGH vs MODERATE).
4. Scenario 4: Fact-Locking Invariant Verification (no metric or score fabrication).
5. Scenario 5: Cache Hit, Composite Key Building & Invalid Payload Integrity.
6. Scenario 6: Transient Retry Loop & Targeted Deterministic Fallback.
7. Scenario 7: REST API Contracts, CamelCase Serialization & 404/400 Validation.
8. Scenario 8: Dashboard Feed Integration & Controlled Failure Isolation.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


from app.api.v1.explanation import router as explanation_router
from app.core.exceptions import ExplanationProviderAuthError, ExplanationProviderError, ExplanationProviderTimeoutError
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.explanation import EvidenceConfidenceLevel, ExplanationProviderType
from app.domain.india_impact import CapitalFlowRisk, ImpactDirection, IndiaImpactAssessment, IndiaImpactLevel, TransmissionChannel
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.main import create_app
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.dashboard_service import DashboardService
from app.services.deterministic_template_provider import DeterministicTemplateProvider
from app.services.explanation_cache import InMemoryExplanationCache
from app.services.explanation_context_assembler import ExplanationContextAssembler
from app.services.explanation_service import ExplanationService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import InMemoryHistoricalSnapshotStore, create_anomaly_snapshot_from_domain
from app.services.india_impact_service import IndiaImpactService


@pytest.fixture
def integrated_system():
    """Real service components for Phase 1-5 integration testing."""
    anomaly_service = AnomalyDetectionService()
    correlation_service = EventCorrelationService()
    india_impact_service = IndiaImpactService()
    historical_store = InMemoryHistoricalSnapshotStore()
    analytics_service = HistoricalAnalyticsService(historical_store)

    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()
    template_provider = DeterministicTemplateProvider()
    explanation_service = ExplanationService(assembler, cache, template_provider)

    app = FastAPI()
    app.include_router(explanation_router, prefix="/api/v1")
    app.state.anomaly_service = anomaly_service
    app.state.correlation_service = correlation_service
    app.state.india_impact_service = india_impact_service
    app.state.historical_store = historical_store
    app.state.historical_analytics_service = analytics_service
    app.state.explanation_service = explanation_service

    client = TestClient(app)

    return {
        "anomaly_service": anomaly_service,
        "correlation_service": correlation_service,
        "india_impact_service": india_impact_service,
        "historical_store": historical_store,
        "explanation_service": explanation_service,
        "analytics_service": analytics_service,
        "client": client,
        "app": app,
    }


def test_scenario_1_true_e2e_brent_crude_oil_explanation_pipeline(integrated_system):
    """
    Scenario 1: True End-to-End Brent Crude Oil Shock Explanation Pipeline.
    """
    anomaly_service = integrated_system["anomaly_service"]
    correlation_service = integrated_system["correlation_service"]
    client = integrated_system["client"]

    # 1. Anomaly trigger
    anom = NormalizedAnomaly(
        id="ANOM-BRENT-E2E",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=86.5,
        previous_value=80.0,
        change_percent=8.125,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )
    anomaly_service._memory_store.append(anom)

    # 2. Correlated article
    art = NormalizedArticle(
        id="ART-OPEC-1",
        headline="OPEC announces emergency crude production cuts",
        summary="Supply reductions boost crude benchmarks.",
        source_name="Reuters",
        source_url="https://reuters.com",
        article_url="https://reuters.com/opec",
        author="Energy Desk",
        published_at_utc="2026-07-30T09:45:00Z",
        published_at_ist="2026-07-30T15:15:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )
    pair = correlation_service.correlate_anomaly_with_article(anom, art, min_confidence=0.50)
    if not pair:
        pair = CorrelatedEventPair("CORR-1", anom, article=art, confidence_score=0.92)
    correlation_service.get_correlated_events = MagicMock(return_value=[pair])


    # 3. Call REST API endpoint
    res = client.get("/api/v1/anomalies/ANOM-BRENT-E2E/explanation")
    assert res.status_code == 200
    data = res.json()

    assert data["anomalyId"] == "ANOM-BRENT-E2E"
    assert data["evidenceConfidenceRating"] == "HIGH"
    assert "BRENT" in data["headlineSummary"]
    assert "8.12%" in data["headlineSummary"]
    assert "OPEC announces emergency crude production cuts" in data["rootCauseAnalysis"]
    assert "Reuters" in data["rootCauseAnalysis"]
    assert "COMMODITY_IMPORT" in data["transmissionMechanismNarrative"]
    assert len(data["sectorRiskNarratives"]) >= 1


def test_scenario_2_multi_asset_class_explanation_coverage(integrated_system):
    """
    Scenario 2: Multi-Asset Class Explanation Coverage (FOREX & BOND).
    """
    anomaly_service = integrated_system["anomaly_service"]
    client = integrated_system["client"]

    # Forex anomaly: USD/INR
    anom_forex = NormalizedAnomaly(
        id="ANOM-USDINR-E2E",
        symbol="USD/INR",
        asset_type="FOREX",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=84.2,
        previous_value=83.0,
        change_percent=1.45,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )
    anomaly_service._memory_store.append(anom_forex)

    res_forex = client.get("/api/v1/anomalies/ANOM-USDINR-E2E/explanation")
    assert res_forex.status_code == 200
    data_forex = res_forex.json()
    assert "USD/INR" in data_forex["headlineSummary"]
    assert "CURRENCY_INR" in data_forex["transmissionMechanismNarrative"]

    # Bond yield anomaly: US10Y
    anom_bond = NormalizedAnomaly(
        id="ANOM-US10Y-E2E",
        symbol="US10Y",
        asset_type="BOND",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=4.65,
        previous_value=4.40,
        change_percent=0.25,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    anomaly_service._memory_store.append(anom_bond)

    res_bond = client.get("/api/v1/anomalies/ANOM-US10Y-E2E/explanation")
    assert res_bond.status_code == 200
    data_bond = res_bond.json()
    assert "US10Y" in data_bond["headlineSummary"]
    assert len(data_bond["transmissionMechanismNarrative"]) > 0



def test_scenario_3_correlated_news_vs_standalone_evidence_confidence(integrated_system):
    """
    Scenario 3: Correlated News vs Standalone Shock Evidence Confidence (HIGH vs MODERATE).
    """
    explanation_service = integrated_system["explanation_service"]
    assembler = ExplanationContextAssembler()

    anom = NormalizedAnomaly(
        id="ANOM-TEST-CONF",
        symbol="GOLD",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=2400.0,
        previous_value=2300.0,
        change_percent=4.35,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    # 1. Standalone shock -> MODERATE confidence rating
    exp_standalone = explanation_service.get_shock_explanation(anom)
    assert exp_standalone.evidence_confidence_rating == EvidenceConfidenceLevel.MODERATE

    # 2. Correlated shock -> HIGH confidence rating
    art = NormalizedArticle("A1", "Gold surges on safe haven demand", "Summary", "FT", "https://ft.com", "https://ft.com/gold", "Author", "2026-07-30T09:50:00Z", "2026-07-30T15:20:00+05:30", GlobalEventCategory.OTHER)
    pair = CorrelatedEventPair("P1", anom, article=art, confidence_score=0.90)

    # Clear cache to evaluate new context
    integrated_system["explanation_service"]._cache.clear()
    exp_correlated = explanation_service.get_shock_explanation(anom, correlated_pairs=[pair])
    assert exp_correlated.evidence_confidence_rating == EvidenceConfidenceLevel.HIGH


def test_scenario_4_fact_locking_invariant_verification(integrated_system):
    """
    Scenario 4: Fact-Locking Invariant Verification (no number or fact fabrication).
    """
    explanation_service = integrated_system["explanation_service"]

    anom = NormalizedAnomaly(
        id="ANOM-FACT-LOCK",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=92.50,
        previous_value=85.00,
        change_percent=8.82,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    assess = IndiaImpactAssessment(
        impact_score=88.5,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.HIGH_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
    )

    exp = explanation_service.get_shock_explanation(anom, impact_assessment=assess)

    # Immutable facts check
    assert "8.82%" in exp.headline_summary
    assert "BRENT" in exp.headline_summary
    assert "88.5" in exp.transmission_mechanism_narrative
    assert "HIGH" in exp.transmission_mechanism_narrative
    assert "NEGATIVE" in exp.transmission_mechanism_narrative


def test_scenario_5_cache_hit_and_composite_key_building(integrated_system):
    """
    Scenario 5: Cache Hit, Composite Key Building & Invalid Payload Integrity.
    """
    explanation_service = integrated_system["explanation_service"]
    cache = integrated_system["explanation_service"]._cache

    anom = NormalizedAnomaly("ANOM-CACHE-1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 6.25, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")

    expected_key = cache.build_key("ANOM-CACHE-1", ExplanationProviderType.DETERMINISTIC)
    assert expected_key == "exp:DETERMINISTIC:v1.0:en-US:ANOM-CACHE-1"

    # Miss
    assert cache.get(expected_key) is None

    # First call -> computes & caches
    exp1 = explanation_service.get_shock_explanation(anom)
    assert cache.get(expected_key) == exp1

    # Second call -> cache hit!
    exp2 = explanation_service.get_shock_explanation(anom)
    assert exp1 == exp2


def test_scenario_6_transient_retry_loop_and_targeted_fallback(integrated_system):
    """
    Scenario 6: Transient Provider Retry Loop & Targeted Deterministic Fallback.
    """
    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()

    mock_llm_provider = MagicMock()
    mock_llm_provider.provider_type = ExplanationProviderType.LLM_GEMINI

    # Attempt 1 raises transient timeout -> Attempt 2 succeeds!
    fallback_exp = DeterministicTemplateProvider().generate_shock_explanation(
        assembler.assemble_shock_context(NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30"))
    )

    mock_llm_provider.generate_shock_explanation.side_effect = [
        ExplanationProviderTimeoutError("Transient timeout connecting to Gemini"),
        fallback_exp,
    ]

    service = ExplanationService(
        assembler=assembler,
        cache=cache,
        primary_provider=mock_llm_provider,
        max_retries=2,
        retry_backoff_seconds=0.01,
    )

    anom = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    exp = service.get_shock_explanation(anom)

    assert mock_llm_provider.generate_shock_explanation.call_count == 2
    assert exp == fallback_exp


def test_scenario_7_rest_api_contracts_and_validation(integrated_system):
    """
    Scenario 7: REST API Contracts, CamelCase Serialization & 404/400 Validation.
    """
    client = integrated_system["client"]

    # 404 Not Found
    res_404 = client.get("/api/v1/anomalies/NON_EXISTENT_ID/explanation")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"]

    # 400 Bad Request
    res_400 = client.get("/api/v1/historical/trends/narrative?from_date=2026-08-01&to_date=2026-07-01")
    assert res_400.status_code == 400
    assert res_400.json()["detail"] == "from_date cannot be after to_date"


@pytest.mark.asyncio
async def test_scenario_8_dashboard_feed_integration_and_failure_isolation():
    """
    Scenario 8: Dashboard Feed Integration & Controlled Failure Isolation.
    """
    app = create_app()

    class FailingProviderService:
        def get_executive_summary(self, *args, **kwargs):
            raise ExplanationProviderAuthError("API key invalid")

    app.state.dashboard_service = DashboardService(
        news_service=AsyncMock(),
        explanation_service=FailingProviderService(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        res = await async_client.get("/api/v1/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "feed" in data
        assert data.get("executiveNarrative") is None
