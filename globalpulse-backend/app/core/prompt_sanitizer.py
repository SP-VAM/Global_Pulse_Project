"""
GlobalPulse Prompt Injection Sanitizer
Dedicated security component for sanitizing text that enters LLM prompts.

Responsibility:
  Strip known prompt injection patterns from any user-originated or
  externally-sourced text before it enters the ExplanationContextAssembler
  or the PromptBuilder. This is a defence-in-depth layer — the primary
  protection is the fact-locked GroundingContextBundle design (Phase 5B),
  which limits what facts can reach the LLM. This sanitizer adds a secondary
  layer specifically targeting adversarial text embedded in news articles,
  economic event descriptions, or other external data sources.

Invariants:
  - All injection pattern matches are replaced with the literal string
    "[REDACTED]" so that the template/LLM still receives structurally
    coherent text without silent omissions.
  - Text is truncated to max_length BEFORE pattern matching to prevent
    regex catastrophic backtracking on very long inputs.
  - The sanitizer never raises — on any internal error the original
    truncated text is returned so that the pipeline is never blocked.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Injection Pattern Registry
# ---------------------------------------------------------------------------

# Each entry is (compiled_pattern, description_for_logging).
# Patterns target the most common prompt injection / jailbreak constructs
# seen in adversarial payloads embedded in external news text.
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # "Ignore [all] [previous] instructions" variants
    (re.compile(r"\bignore\s+(?:all\s+)?(?:previous\s+)?instructions?\b", re.IGNORECASE), "ignore-instructions"),
    # "Disregard [previous/prior/all] instructions/rules/context"
    (re.compile(r"\bdisregard\s+(?:previous\s+|prior\s+|all\s+)?(?:instructions?|rules?|context)\b", re.IGNORECASE), "disregard-instructions"),
    # "You are now [a|an] ..." persona switching
    (re.compile(r"\byou\s+are\s+now\s+(?:a|an)\b", re.IGNORECASE), "persona-switch-you-are-now"),
    # "Act as [a|an] ..." persona injection
    (re.compile(r"\bact\s+as\s+(?:a|an|the)?\b", re.IGNORECASE), "act-as-persona"),
    # "Forget [all|previous|your] [rules|instructions|training|context]"
    (re.compile(r"\bforget\s+(?:all\s+|previous\s+|your\s+)*(?:rules?|instructions?|training|context)\b", re.IGNORECASE), "forget-rules"),
    # "System prompt" direct reference
    (re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE), "system-prompt-ref"),
    # "Jailbreak" keyword
    (re.compile(r"\bjailbreak\b", re.IGNORECASE), "jailbreak"),
    # "Do anything now" / DAN jailbreak
    (re.compile(r"\bdo\s+anything\s+now\b", re.IGNORECASE), "dan-jailbreak"),
    # "Reveal [your] [system|hidden|internal] [prompt|instructions]"
    (re.compile(r"\breveal\s+(?:your\s+)?(?:system|hidden|internal)\s+(?:prompt|instructions?)\b", re.IGNORECASE), "reveal-system-prompt"),
    # Prompt delimiter injection: ``` or <<SYS>> or [INST] or similar
    (re.compile(r"(?:<<\s*SYS\s*>>|\[INST\]|\[/INST\]|<\|(?:system|user|assistant)\|>)", re.IGNORECASE), "prompt-delimiter"),
]

_REDACTION_PLACEHOLDER = "[REDACTED]"

# Default max length for sanitized text (characters).
# Prevents catastrophic backtracking on adversarially long inputs.
DEFAULT_MAX_LENGTH = 500


# ---------------------------------------------------------------------------
# PromptSanitizer
# ---------------------------------------------------------------------------


class PromptSanitizer:
    """
    Sanitizes externally-sourced text before it enters LLM prompt construction.

    Usage:
        sanitizer = PromptSanitizer()
        clean = sanitizer.sanitize(article.headline)
        clean_summary = sanitizer.sanitize(article.summary, max_length=300)

    Thread-safety: stateless; safe to use as a module-level singleton.
    """

    def sanitize(
        self,
        text: str | None,
        max_length: int = DEFAULT_MAX_LENGTH,
    ) -> str:
        """
        Truncate and scrub known injection patterns from ``text``.

        Args:
            text:       Raw text from an external source (news headline,
                        article summary, economic event description, etc.).
                        ``None`` and empty strings are returned as-is.
            max_length: Maximum number of characters retained after
                        truncation. Applied before pattern matching.

        Returns:
            Sanitized string with injection patterns replaced by
            ``[REDACTED]`` and length bounded to ``max_length``.
        """
        if not text:
            return text or ""

        try:
            # 1. Truncate first to bound regex complexity
            truncated = text[:max_length]

            # 2. Apply each injection pattern
            result = truncated
            for pattern, label in _INJECTION_PATTERNS:
                before = result
                result = pattern.sub(_REDACTION_PLACEHOLDER, result)
                if result != before:
                    logger.debug(
                        "Prompt injection pattern '%s' redacted from input text",
                        label,
                    )

            return result

        except Exception as exc:  # pragma: no cover — safety net
            logger.warning(
                "PromptSanitizer encountered an unexpected error; returning raw truncated text: %s",
                exc,
            )
            return text[:max_length]


# ---------------------------------------------------------------------------
# Module-level singleton (import and use directly)
# ---------------------------------------------------------------------------

prompt_sanitizer = PromptSanitizer()
