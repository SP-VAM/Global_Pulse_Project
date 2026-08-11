"""
GlobalPulse Phase 5C — Explanation Prompt Builder.
Constructs grounded system and user prompts for external LLM providers (Gemini / OpenAI).
Enforces Fact-Locking Rules: all symbols, metrics, change percentages, scores, levels,
and sector directions are locked to ground truth inputs from GroundingContextBundle.
"""
from typing import Tuple

from app.domain.explanation import GroundingContextBundle


class ExplanationPromptBuilder:
    """
    Constructs grounded system and user prompts enforcing strict fact-locking rules.
    Directs external LLM providers to return valid JSON matching expected domain fields.
    """

    def build_shock_explanation_prompt(self, context: GroundingContextBundle) -> Tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) for generating a ShockExplanation.
        Strictly locks all ground truth facts from GroundingContextBundle.
        """
        system_prompt = (
            "You are GlobalPulse AI Macro Analyst, an expert financial analyst. "
            "Your task is to generate a structured, executive natural language shock explanation for a global market anomaly. "
            "\nFACT-LOCKING MANDATE:\n"
            "1. You MUST NOT recalculate, modify, or contradict any numeric metrics, symbols, change percentages, impact scores, impact levels, or sector directions provided in the context.\n"
            "2. All numbers and directional facts provided are IMMUTABLE GROUND TRUTH.\n"
            "3. If a fact is unavailable (e.g. no news correlation or no India impact assessment), explicitly state that evidence is unavailable rather than inferring or fabricating information.\n"
            "4. Output MUST be strictly valid JSON matching the specified JSON schema without additional markdown or explanation text."
        )

        anom = context.anomaly
        impact = context.impact_assessment
        pairs = context.correlated_pairs or ()

        anomaly_facts = "None"
        if anom:
            anomaly_facts = (
                f"Symbol: {anom.symbol}, Asset Type: {anom.asset_type}, Metric: {anom.metric.value}, "
                f"Observed Price/Yield: {anom.current_value}, Previous: {anom.previous_value}, "
                f"Change Percent: {anom.change_percent}%, Window: {anom.observation_window}, Severity: {anom.severity.value}"
            )

        correlation_facts = "None"
        if pairs:
            corr_list = []
            for p in pairs:
                if p.article:
                    corr_list.append(f"Article: '{p.article.headline}' ({p.article.source_name}, Confidence: {p.confidence_score:.2f})")
                elif p.economic_event:
                    corr_list.append(f"Economic Event: '{p.economic_event.event_name}' (Country: {p.economic_event.country}, Actual: {p.economic_event.actual}, Forecast: {p.economic_event.forecast})")
            correlation_facts = "; ".join(corr_list)

        impact_facts = "None"
        if impact:
            sectors_list = [
                f"{sec.sector_name}: {sec.direction.value} ({sec.transmission_rationale})"
                for sec in impact.affected_sectors
            ]
            channels_list = [ch.value for ch in impact.transmission_channels]
            impact_facts = (
                f"Impact Score: {impact.impact_score}/100, Impact Level: {impact.impact_level.value}, "
                f"Impact Direction: {impact.impact_direction.value}, Capital Flow Risk: {impact.capital_flow_risk.value}, "
                f"Transmission Channels: [{', '.join(channels_list)}], Sector Impacts: [{'; '.join(sectors_list)}]"
            )

        user_prompt = (
            f"Grounding Context Bundle:\n"
            f"- Market Anomaly Facts: {anomaly_facts}\n"
            f"- Correlated Evidence Facts: {correlation_facts}\n"
            f"- India Impact Assessment Facts: {impact_facts}\n\n"
            "Return JSON matching format:\n"
            "{\n"
            '  "headline_summary": "1-sentence executive summary",\n'
            '  "root_cause_analysis": "Explanation of trigger event / market movement",\n'
            '  "transmission_mechanism_narrative": "Qualitative narrative of transmission path to India",\n'
            '  "sector_risk_narratives": [\n'
            '    {"sector_name": "SECTOR_NAME", "direction": "NEGATIVE", "risk_summary": "Qualitative risk summary"}\n'
            '  ],\n'
            '  "key_watch_metrics": ["Metric 1", "Metric 2"]\n'
            "}"
        )

        return system_prompt, user_prompt

    def build_executive_summary_prompt(self, context: GroundingContextBundle) -> Tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) for generating an ExecutiveSummary.
        """
        system_prompt = (
            "You are GlobalPulse AI Macro Analyst. Generate a high-level executive bullet point narrative "
            "for macro dashboard reporting based strictly on grounded facts. "
            "Never invent facts. Output strictly valid JSON."
        )

        anom = context.anomaly
        impact = context.impact_assessment
        trends = context.trend_analytics

        if trends:
            context_text = f"Trend Analytics: {trends.total_anomalies_evaluated} anomalies evaluated, Avg Impact: {trends.average_impact_score:.1f}/100, Peak: {trends.peak_impact_score:.1f}/100."
        elif anom:
            context_text = f"Anomaly: {anom.symbol} ({anom.change_percent}% change). Impact: {impact.impact_level.value if impact else 'N/A'}."
        else:
            context_text = "No active market shock context."

        user_prompt = (
            f"Context: {context_text}\n\n"
            "Return JSON matching format:\n"
            "{\n"
            '  "title": "Executive Summary Title",\n'
            '  "bullet_points": ["Point 1", "Point 2"],\n'
            '  "overall_sentiment": "NEGATIVE"\n'
            "}"
        )

        return system_prompt, user_prompt
