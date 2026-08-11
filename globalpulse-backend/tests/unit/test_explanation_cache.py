"""
Unit tests for ExplanationCache (Phase 5B).
Verifies build_key format, set/get hit/miss, TTL expiration, LRU capacity eviction, and clear operations.
"""
import time
import pytest
from app.domain.explanation import ExplanationProviderType
from app.services.explanation_cache import InMemoryExplanationCache


def test_build_key_format():
    cache = InMemoryExplanationCache()
    key = cache.build_key(
        entity_id="ANOM-BRENT-1",
        provider_type=ExplanationProviderType.DETERMINISTIC,
        template_version="v1.0",
        language="en-US",
    )
    assert key == "exp:DETERMINISTIC:v1.0:en-US:ANOM-BRENT-1"


def test_cache_put_get_hit_and_miss():
    cache = InMemoryExplanationCache()
    key = cache.build_key("ANOM-1", ExplanationProviderType.DETERMINISTIC)

    # Miss
    assert cache.get(key) is None

    # Put and Hit
    cache.put(key, "EXPLANATION_PAYLOAD_1")
    assert cache.get(key) == "EXPLANATION_PAYLOAD_1"
    assert len(cache) == 1


def test_cache_ttl_expiration():
    cache = InMemoryExplanationCache(default_ttl_seconds=1)
    key = cache.build_key("ANOM-EXPIRING", ExplanationProviderType.DETERMINISTIC)

    cache.put(key, "EXPIRED_DATA", ttl_seconds=1)
    assert cache.get(key) == "EXPIRED_DATA"

    # Wait 1.1s for expiration
    time.sleep(1.1)
    assert cache.get(key) is None
    assert len(cache) == 0


def test_cache_lru_capacity_eviction():
    cache = InMemoryExplanationCache(max_items=2)

    k1 = cache.build_key("E1", ExplanationProviderType.DETERMINISTIC)
    k2 = cache.build_key("E2", ExplanationProviderType.DETERMINISTIC)
    k3 = cache.build_key("E3", ExplanationProviderType.DETERMINISTIC)

    cache.put(k1, "VAL1")
    cache.put(k2, "VAL2")

    # Touch k1 to make k2 LRU
    assert cache.get(k1) == "VAL1"

    # Insert k3 -> causes k2 to be evicted
    cache.put(k3, "VAL3")

    assert len(cache) == 2
    assert cache.get(k1) == "VAL1"
    assert cache.get(k2) is None  # Evicted!
    assert cache.get(k3) == "VAL3"


def test_cache_evict_and_clear():
    cache = InMemoryExplanationCache()
    k1 = cache.build_key("E1", ExplanationProviderType.DETERMINISTIC)
    k2 = cache.build_key("E2", ExplanationProviderType.DETERMINISTIC)

    cache.put(k1, "V1")
    cache.put(k2, "V2")
    assert len(cache) == 2

    cache.evict(k1)
    assert cache.get(k1) is None
    assert len(cache) == 1

    cache.clear()
    assert len(cache) == 0
    assert cache.get(k2) is None
