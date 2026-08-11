"""
Unit tests for Sub-Phase 3A India Impact domain models, vulnerability matrix, and Pydantic schemas.
Verifies directional shock matrix lookups, qualitative rationales, schema serialization,
and explicit separation between IndiaImpactLevel and Phase 2 presentation ImpactLevel.
"""
import pytest
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaExposureStrength,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    SectorSensitivity,
    TransmissionChannel,
)
from app.schemas.dashboard import ImpactLevel as Phase2PresentationImpactLevel
from app.schemas.india_impact import IndiaImpactResponse, IndianSectorImpactSchema
from app.services.classification.india_vulnerability_matrix import (
    SHOCK_DIRECTION_VULNERABILITY_MATRIX,
    get_vulnerability_rule,
)


def test_india_impact_level_distinct_from_phase2_presentation_impact():
    # Verify Phase 3 has NEGLIGIBLE instead of UNKNOWN
    phase3_levels = set(IndiaImpactLevel)
    phase2_levels = set(Phase2PresentationImpactLevel)

    assert IndiaImpactLevel.NEGLIGIBLE in phase3_levels
    assert Phase2PresentationImpactLevel.UNKNOWN in phase2_levels
    assert IndiaImpactLevel.HIGH.value == "HIGH"


def test_exposure_strength_enum_values():
    assert IndiaExposureStrength.DIRECT_HIGH == 1.00
    assert IndiaExposureStrength.HIGH == 0.80
    assert IndiaExposureStrength.MODERATE == 0.60
    assert IndiaExposureStrength.LOW == 0.30
    assert IndiaExposureStrength.NEGLIGIBLE == 0.00


def test_vulnerability_matrix_brent_shock_directions():
    # BRENT UP -> Negative for Paints & Aviation, Positive for Oil Exploration
    rule_up = get_vulnerability_rule("BRENT", "UP")
    assert rule_up is not None
    assert rule_up["channel"] == TransmissionChannel.COMMODITY_IMPORT
    assert rule_up["overall_direction"] == ImpactDirection.NEGATIVE

    paints_up = next(s for s in rule_up["sectors"] if s.sector_name == "PAINTS")
    assert paints_up.direction == ImpactDirection.NEGATIVE

    oil_up = next(s for s in rule_up["sectors"] if s.sector_name == "OIL_EXPLORATION")
    assert oil_up.direction == ImpactDirection.POSITIVE

    # BRENT DOWN -> Positive for Paints & Aviation, Negative for Oil Exploration
    rule_down = get_vulnerability_rule("BRENT", "DOWN")
    assert rule_down is not None
    assert rule_down["overall_direction"] == ImpactDirection.POSITIVE

    paints_down = next(s for s in rule_down["sectors"] if s.sector_name == "PAINTS")
    assert paints_down.direction == ImpactDirection.POSITIVE

    oil_down = next(s for s in rule_down["sectors"] if s.sector_name == "OIL_EXPLORATION")
    assert oil_down.direction == ImpactDirection.NEGATIVE


def test_vulnerability_matrix_usd_inr_directions():
    rule_up = get_vulnerability_rule("USD/INR", "UP")
    assert rule_up is not None
    assert rule_up["overall_direction"] == ImpactDirection.MIXED

    it_up = next(s for s in rule_up["sectors"] if s.sector_name == "IT_SERVICES")
    assert it_up.direction == ImpactDirection.POSITIVE

    rule_down = get_vulnerability_rule("USD/INR", "DOWN")
    assert rule_down is not None
    it_down = next(s for s in rule_down["sectors"] if s.sector_name == "IT_SERVICES")
    assert it_down.direction == ImpactDirection.NEGATIVE


def test_qualitative_rationales_no_unverified_hardcoded_percentages():
    for key, rule in SHOCK_DIRECTION_VULNERABILITY_MATRIX.items():
        summary = rule["summary"]
        assert "%" not in summary  # No hardcoded unverified percentages in qualitative summary
        for sec in rule["sectors"]:
            assert "%" not in sec.transmission_rationale


def test_india_impact_response_camelcase_serialization():
    sector_schema = IndianSectorImpactSchema(
        sector_name="PAINTS",
        direction=ImpactDirection.NEGATIVE,
        sensitivity=SectorSensitivity.HIGH_SENSITIVITY,
        transmission_rationale="Crude derivatives increase raw material costs",
    )

    response = IndiaImpactResponse(
        impact_score=78.5,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
        affected_sectors=[sector_schema],
        summary_rationale="Crude oil price spikes inflate India's import bill",
    )

    data = response.model_dump(by_alias=True)
    assert data["impactScore"] == 78.5
    assert data["impactLevel"] == "HIGH"
    assert data["impactDirection"] == "NEGATIVE"
    assert data["capitalFlowRisk"] == "MODERATE_RISK"
    assert data["transmissionChannels"] == ["COMMODITY_IMPORT"]
    assert data["affectedSectors"][0]["sectorName"] == "PAINTS"
    assert data["affectedSectors"][0]["transmissionRationale"] == "Crude derivatives increase raw material costs"
