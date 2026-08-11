"""
GlobalPulse Phase 5C — LLM Explanation Provider.
Implements AbstractExplanationProvider for external LLM generation (e.g. Gemini / OpenAI API).

Translates infrastructure and network errors into custom explanation exceptions:
- Missing API Key -> ExplanationProviderAuthError
- Timeout -> ExplanationProviderTimeoutError
- HTTP 429 -> ExplanationProviderRateLimitError
- Malformed JSON -> ExplanationProviderResponseError
"""
import logging
from typing import Any, Callable, Optional

from app.core.exceptions import (
    ExplanationProviderAuthError,
    ExplanationProviderError,
    ExplanationProviderRateLimitError,
    ExplanationProviderResponseError,
    ExplanationProviderTimeoutError,
)
from app.domain.explanation import (
    EvidenceConfidenceLevel,
    ExecutiveSummary,
    ExplanationProviderType,
    GroundingContextBundle,
    ShockExplanation,
)
from app.services.deterministic_template_provider import AbstractExplanationProvider
from app.services.prompt_builder import ExplanationPromptBuilder
from app.services.response_parser import ExplanationResponseParser

logger = logging.getLogger(__name__)


class LLMExplanationProvider(AbstractExplanationProvider):
    """
    External LLM explanation provider (Gemini / OpenAI API).
    Translates network and provider errors into structured ExplanationProviderError exceptions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider_type: ExplanationProviderType = ExplanationProviderType.LLM_GEMINI,
        prompt_builder: Optional[ExplanationPromptBuilder] = None,
        response_parser: Optional[ExplanationResponseParser] = None,
        raw_llm_caller: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self._api_key = api_key
        self._provider_type = provider_type
        self._prompt_builder = prompt_builder or ExplanationPromptBuilder()
        self._response_parser = response_parser or ExplanationResponseParser()
        self._raw_llm_caller = raw_llm_caller

    @property
    def provider_type(self) -> ExplanationProviderType:
        return self._provider_type

    def _execute_llm_call(self, system_prompt: str, user_prompt: str) -> str:
        """
        Execute API call to external LLM provider.
        Translates raw network errors to custom domain provider exceptions.
        """
        if not self._api_key:
            raise ExplanationProviderAuthError(
                f"API key is not configured for provider {self._provider_type.value}"
            )

        if self._raw_llm_caller:
            try:
                return self._raw_llm_caller(system_prompt, user_prompt)
            except ExplanationProviderError:
                raise
            except TimeoutError as exc:
                raise ExplanationProviderTimeoutError(f"LLM provider request timed out: {exc}") from exc
            except OSError as exc:
                raise ExplanationProviderError(f"LLM provider network error: {exc}") from exc
            except Exception as exc:
                raise ExplanationProviderError(f"LLM provider request failed: {exc}") from exc

        raise ExplanationProviderAuthError(
            f"No active network client configured for LLM provider {self._provider_type.value}"
        )

    def generate_shock_explanation(self, context: GroundingContextBundle) -> ShockExplanation:
        """Generate ShockExplanation via LLM API."""
        system_prompt, user_prompt = self._prompt_builder.build_shock_explanation_prompt(context)
        raw_response = self._execute_llm_call(system_prompt, user_prompt)

        anom_id = context.anomaly.id if context.anomaly else None
        evidence_conf = (
            EvidenceConfidenceLevel.HIGH
            if (context.correlated_pairs and len(context.correlated_pairs) > 0)
            else EvidenceConfidenceLevel.MODERATE
        )

        return self._response_parser.parse_shock_explanation(
            raw_json_str=raw_response,
            anomaly_id=anom_id,
            provider_type=self._provider_type,
            evidence_confidence=evidence_conf,
        )

    def generate_executive_summary(self, context: GroundingContextBundle) -> ExecutiveSummary:
        """Generate ExecutiveSummary via LLM API."""
        system_prompt, user_prompt = self._prompt_builder.build_executive_summary_prompt(context)
        raw_response = self._execute_llm_call(system_prompt, user_prompt)

        return self._response_parser.parse_executive_summary(
            raw_json_str=raw_response,
            provider_type=self._provider_type,
        )
