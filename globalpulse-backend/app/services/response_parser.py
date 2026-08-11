"""
GlobalPulse Phase 5C — Explanation Response Parser.
Validates raw LLM provider JSON responses and maps them into domain dataclasses.

Features:
- Strips markdown formatting (```json ... ```)
- Validates required fields and maps enum types
- Raises ExplanationProviderResponseError on malformed, missing, or invalid JSON payloads
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import ExplanationProviderResponseError
from app.core.timezone import TimezoneService
from app.domain.explanation import (
    EvidenceConfidenceLevel,
    ExecutiveSummary,
    ExplanationProviderType,
    SectorRiskNarrative,
    ShockExplanation,
)
from app.domain.india_impact import ImpactDirection

logger = logging.getLogger(__name__)


class ExplanationResponseParser:
    """
    Parses and validates raw LLM JSON outputs into domain models.
    Raises ExplanationProviderResponseError on malformed or unparseable payloads.
    """

    @staticmethod
    def _strip_markdown_code_blocks(raw_text: str) -> str:
        """Remove ```json and ``` fences from raw LLM output text."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            # Remove leading ```json or ``` line
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            # Remove trailing ``` line
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def parse_shock_explanation(
        self,
        raw_json_str: str,
        anomaly_id: Optional[str],
        provider_type: ExplanationProviderType = ExplanationProviderType.LLM_GEMINI,
        evidence_confidence: EvidenceConfidenceLevel = EvidenceConfidenceLevel.MODERATE,
        template_version: str = "v1.0",
    ) -> ShockExplanation:
        """
        Parses raw LLM JSON response string into ShockExplanation.
        Raises ExplanationProviderResponseError if payload is malformed or missing required keys.
        """
        cleaned_json = self._strip_markdown_code_blocks(raw_json_str)

        try:
            data: Dict[str, Any] = json.loads(cleaned_json)
        except Exception as exc:
            logger.warning("Failed to parse raw provider JSON: %s. Output: %s", exc, raw_json_str)
            raise ExplanationProviderResponseError(f"Invalid JSON payload from provider: {exc}") from exc

        if not isinstance(data, dict):
            raise ExplanationProviderResponseError("Provider payload must be a JSON object")

        # Required fields check
        required_fields = ["headline_summary", "root_cause_analysis", "transmission_mechanism_narrative"]
        for field_name in required_fields:
            if field_name not in data or not isinstance(data[field_name], str) or not data[field_name].strip():
                raise ExplanationProviderResponseError(f"Missing or invalid required field '{field_name}' in provider response")

        sector_narratives: List[SectorRiskNarrative] = []
        raw_sectors = data.get("sector_risk_narratives", [])
        if isinstance(raw_sectors, list):
            for sec_item in raw_sectors:
                if isinstance(sec_item, dict) and "sector_name" in sec_item and "risk_summary" in sec_item:
                    dir_str = str(sec_item.get("direction", "NEUTRAL")).upper()
                    try:
                        dir_enum = ImpactDirection(dir_str)
                    except ValueError:
                        dir_enum = ImpactDirection.NEUTRAL

                    sector_narratives.append(
                        SectorRiskNarrative(
                            sector_name=str(sec_item["sector_name"]),
                            direction=dir_enum,
                            risk_summary=str(sec_item["risk_summary"]),
                        )
                    )

        raw_metrics = data.get("key_watch_metrics", [])
        key_watch_metrics: Tuple[str, ...] = tuple(
            str(m) for m in raw_metrics if isinstance(m, (str, int, float))
        )

        now_utc = TimezoneService.now_utc().isoformat()
        now_ist = TimezoneService.now_ist().isoformat()
        exp_id = f"EXP-{anomaly_id or 'GEN'}-{now_utc[:19]}"

        return ShockExplanation(
            explanation_id=exp_id,
            anomaly_id=anomaly_id,
            headline_summary=str(data["headline_summary"]),
            root_cause_analysis=str(data["root_cause_analysis"]),
            transmission_mechanism_narrative=str(data["transmission_mechanism_narrative"]),
            sector_risk_narratives=tuple(sector_narratives),
            key_watch_metrics=key_watch_metrics,
            evidence_confidence_rating=evidence_confidence,
            provider_type=provider_type,
            template_version=template_version,
            generated_at_utc=now_utc,
            generated_at_ist=now_ist,
        )

    def parse_executive_summary(
        self,
        raw_json_str: str,
        provider_type: ExplanationProviderType = ExplanationProviderType.LLM_GEMINI,
        template_version: str = "v1.0",
    ) -> ExecutiveSummary:
        """
        Parses raw LLM JSON response string into ExecutiveSummary.
        Raises ExplanationProviderResponseError if payload is malformed or missing required keys.
        """
        cleaned_json = self._strip_markdown_code_blocks(raw_json_str)

        try:
            data: Dict[str, Any] = json.loads(cleaned_json)
        except Exception as exc:
            logger.warning("Failed to parse raw provider JSON: %s", exc)
            raise ExplanationProviderResponseError(f"Invalid JSON payload from provider: {exc}") from exc

        if not isinstance(data, dict):
            raise ExplanationProviderResponseError("Provider payload must be a JSON object")

        if "title" not in data or "bullet_points" not in data or not isinstance(data["bullet_points"], list):
            raise ExplanationProviderResponseError("Missing required fields 'title' or 'bullet_points'")

        bullets = [str(b) for b in data["bullet_points"] if isinstance(b, str) and b.strip()]
        if not bullets:
            raise ExplanationProviderResponseError("bullet_points list cannot be empty")

        dir_str = str(data.get("overall_sentiment", "NEUTRAL")).upper()
        try:
            sentiment_enum = ImpactDirection(dir_str)
        except ValueError:
            sentiment_enum = ImpactDirection.NEUTRAL

        now_utc = TimezoneService.now_utc().isoformat()
        now_ist = TimezoneService.now_ist().isoformat()
        summ_id = f"SUMM-GEN-{now_utc[:19]}"

        return ExecutiveSummary(
            summary_id=summ_id,
            title=str(data["title"]),
            bullet_points=tuple(bullets),
            overall_sentiment=sentiment_enum,
            provider_type=provider_type,
            template_version=template_version,
            generated_at_utc=now_utc,
            generated_at_ist=now_ist,
        )
