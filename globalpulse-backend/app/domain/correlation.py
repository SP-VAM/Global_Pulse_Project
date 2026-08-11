"""
GlobalPulse Correlation Domain Model
Internal representation of a correlated pair linking a market anomaly with a news article OR an economic calendar event.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.domain.anomaly import NormalizedAnomaly
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.news import NormalizedArticle

# Shared Correlation Confidence Threshold for 2C & 2D
DEFAULT_MIN_CONFIDENCE: float = 0.50


@dataclass

class CorrelationMatchReason:
    """Explains why an anomaly and candidate event/article were correlated."""

    reason_type: str        # TIME_PROXIMITY | ENTITY_MATCH | SECTOR_MATCH | CATEGORY_MATCH | COUNTRY_MATCH | MACRO_RELEVANCE
    description: str        # Human-readable explanation e.g. "Time proximity: 14 mins"
    weight: float           # Contribution weight to total confidence score


@dataclass
class CorrelatedEventPair:
    """
    Normalized link between a market anomaly and EXACTLY ONE candidate (article XOR economic_event).

    candidate_type: "ARTICLE" or "ECONOMIC_EVENT"
    confidence_score: Float between 0.00 and 1.00 indicating correlation evidence strength.
    match_reasons: List of human-readable match explanations.
    """

    correlation_id: str
    anomaly: NormalizedAnomaly
    article: Optional[NormalizedArticle] = None
    economic_event: Optional[NormalizedEconomicEvent] = None
    candidate_type: str = "ARTICLE"
    confidence_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Enforce strict XOR invariant: exactly one of article or economic_event must be non-None."""
        if (self.article is None and self.economic_event is None) or \
           (self.article is not None and self.economic_event is not None):
            raise ValueError(
                "CorrelatedEventPair must have exactly one candidate (article XOR economic_event)"
            )
        if self.article is not None:
            self.candidate_type = "ARTICLE"
        elif self.economic_event is not None:
            self.candidate_type = "ECONOMIC_EVENT"
