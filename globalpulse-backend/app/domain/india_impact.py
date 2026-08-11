"""
GlobalPulse India Impact Domain Model (Sub-Phase 3A)
Internal representation for Indian market impact, shock transmission, and sector sensitivity.

Distinct from Phase 2 UI presentation severity — uses IndiaImpactLevel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class IndiaImpactLevel(str, Enum):
    """
    Dedicated India impact magnitude level.
    Semantically separate from Phase 2 UI presentation ImpactLevel.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NEGLIGIBLE = "NEGLIGIBLE"


class ImpactDirection(str, Enum):
    """Direction of overall or sector-specific market impact."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"


class TransmissionChannel(str, Enum):
    """Primary economic transmission channels linking global shocks to India."""

    CURRENCY_INR = "CURRENCY_INR"
    COMMODITY_IMPORT = "COMMODITY_IMPORT"
    CAPITAL_FLOW_SENSITIVITY = "CAPITAL_FLOW_SENSITIVITY"
    INTEREST_RATE_DIFFERENTIAL = "INTEREST_RATE_DIFFERENTIAL"
    GLOBAL_DEMAND = "GLOBAL_DEMAND"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"


class CapitalFlowRisk(str, Enum):
    """Foreign capital reallocation risk level for emerging market assets."""

    HIGH_RISK = "HIGH_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    LOW_RISK = "LOW_RISK"
    NEGLIGIBLE = "NEGLIGIBLE"


class SectorSensitivity(str, Enum):
    """Expected historical sector vulnerability/sensitivity rating."""

    HIGH_SENSITIVITY = "HIGH_SENSITIVITY"
    MODERATE_SENSITIVITY = "MODERATE_SENSITIVITY"
    LOW_SENSITIVITY = "LOW_SENSITIVITY"


class IndiaExposureStrength(float, Enum):
    """
    Documented exposure strength scale for India as an emerging market import economy.
    """

    DIRECT_HIGH = 1.00   # Direct primary import dependency or domestic currency pair (e.g. USD/INR, BRENT)
    HIGH = 0.80          # Major global benchmark with high macroeconomic sensitivity (e.g. US10Y, GOLD)
    MODERATE = 0.60      # Industry-specific global shock (e.g. global tech/semiconductor)
    LOW = 0.30          # Indirect or localized global event
    NEGLIGIBLE = 0.00   # No recognized Indian transmission


@dataclass(frozen=True)
class IndianSectorSensitivity:
    """Expected historical sector sensitivity to a specific directional global shock."""

    sector_name: str                  # e.g. "PAINTS", "IT_SERVICES", "AVIATION", "OIL_REFINING"
    direction: ImpactDirection       # POSITIVE | NEGATIVE | MIXED | NEUTRAL
    sensitivity: SectorSensitivity   # HIGH_SENSITIVITY | MODERATE_SENSITIVITY | LOW_SENSITIVITY
    transmission_rationale: str      # Qualitative explanation (no unverified percentages)


@dataclass
class IndiaImpactAssessment:
    """Result of India impact evaluation for an anomaly or candidate event."""

    impact_score: float                              # 0.0 to 100.0
    impact_level: IndiaImpactLevel                   # HIGH | MEDIUM | LOW | NEGLIGIBLE
    impact_direction: ImpactDirection               # POSITIVE | NEGATIVE | MIXED | NEUTRAL
    capital_flow_risk: CapitalFlowRisk               # HIGH_RISK | MODERATE_RISK | LOW_RISK | NEGLIGIBLE
    transmission_channels: List[TransmissionChannel] = field(default_factory=list)
    affected_sectors: List[IndianSectorSensitivity] = field(default_factory=list)
    summary_rationale: str = ""
