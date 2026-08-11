"""
GlobalPulse Global Event Domain Model
A NormalizedGlobalEvent wraps a NormalizedArticle with financial relevance annotation.

The distinction between a raw news article and a "global event" is intentional:
  - Not every news article is a globally significant financial event.
  - This model represents articles that have passed the financial relevance filter.
  - Future phases will use NormalizedGlobalEvent as input to the ripple-effect engine.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.news import NormalizedArticle


@dataclass(frozen=True)
class NormalizedGlobalEvent:
    """
    A news article classified as a potentially financially relevant real-world event.

    is_financially_relevant: True when the relevance filter threshold is met.
    relevance_score: raw score from relevance_filter (higher = more relevant signals).
    The article field contains the full normalized article metadata.
    """

    article: NormalizedArticle
    is_financially_relevant: bool
    relevance_score: int
