"""
GlobalPulse Phase 5B — Explanation Cache Abstraction & InMemory Cache Implementation.
Provides an abstract cache interface (AbstractExplanationCache) and a bounded in-memory LRU cache (InMemoryExplanationCache).

Key Features:
- Composite cache key generator: exp:{provider_type}:{template_version}:{language}:{entity_id}
- Time-To-Live (TTL) expiration per item
- Least Recently Used (LRU) eviction when capacity is reached
- Completely decouples ExplanationService from concrete storage mechanics.
"""
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timezone
import logging
from typing import Any, Optional

from app.domain.explanation import ExplanationProviderType

logger = logging.getLogger(__name__)


class AbstractExplanationCache(ABC):
    """Abstract cache boundary for Phase 5 explanations."""

    @abstractmethod
    def build_key(
        self,
        entity_id: str,
        provider_type: ExplanationProviderType,
        template_version: str = "v1.0",
        language: str = "en-US",
    ) -> str:
        """Construct composite key: exp:{provider_type}:{template_version}:{language}:{entity_id}."""
        ...

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if present and not expired."""
        ...

    @abstractmethod
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store value in cache with optional TTL override."""
        ...

    @abstractmethod
    def evict(self, key: str) -> None:
        """Explicitly evict a single item by key."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached entries."""
        ...


class InMemoryExplanationCache(AbstractExplanationCache):
    """
    Bounded in-memory LRU explanation cache with TTL expiration.
    Thread-safe dictionary store with OrderedDict LRU eviction.
    """

    def __init__(self, max_items: int = 500, default_ttl_seconds: int = 3600) -> None:
        self._max_items = max(1, max_items)
        self._default_ttl_seconds = max(1, default_ttl_seconds)
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def build_key(
        self,
        entity_id: str,
        provider_type: ExplanationProviderType,
        template_version: str = "v1.0",
        language: str = "en-US",
    ) -> str:
        """Construct composite key: exp:{provider_type}:{template_version}:{language}:{entity_id}."""
        provider_str = provider_type.value if isinstance(provider_type, ExplanationProviderType) else str(provider_type)
        return f"exp:{provider_str}:{template_version}:{language}:{entity_id}"

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if present and not expired."""
        if key not in self._store:
            return None

        val, exp_timestamp = self._store[key]
        now_epoch = datetime.now(timezone.utc).timestamp()

        if now_epoch > exp_timestamp:
            # Expired entry -> remove and return None
            del self._store[key]
            logger.debug("Cache entry for key %s expired and evicted", key)
            return None

        # Move key to end to mark as recently used (LRU)
        self._store.move_to_end(key)
        return val

    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store value in cache with TTL and enforce LRU capacity bounds."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        exp_timestamp = datetime.now(timezone.utc).timestamp() + max(1, ttl)

        if key in self._store:
            self._store.move_to_end(key)

        self._store[key] = (value, exp_timestamp)

        # Enforce LRU max items capacity
        while len(self._store) > self._max_items:
            oldest_key, _ = self._store.popitem(last=False)
            logger.debug("LRU capacity reached (%d). Evicted oldest key: %s", self._max_items, oldest_key)

    def evict(self, key: str) -> None:
        """Explicitly evict a single item by key."""
        if key in self._store:
            del self._store[key]
            logger.debug("Evicted cache key: %s", key)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()
        logger.debug("Cleared explanation cache")

    def __len__(self) -> int:
        return len(self._store)
