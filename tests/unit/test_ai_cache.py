"""Verify bounded LRU retention and monotonic TTL semantics."""

import pytest

from gatherly.infra.cache import MemoryIdeasCache
from gatherly.infra.clock import SystemClock
from tests.unit.ai_helpers import sample_ideas


def test_cache_expires_at_deadline_without_refresh_on_read() -> None:
    """Reading a result must not prolong its privacy retention window."""
    now = [0.0]
    cache = MemoryIdeasCache(2, 10, lambda: now[0])
    ideas = sample_ideas()
    assert cache.get("missing") is None
    cache.put("first", ideas)
    now[0] = 9
    assert cache.get("first") == ideas
    now[0] = 10
    assert cache.get("first") is None


def test_cache_eviction_respects_reads_and_replacements() -> None:
    """Evict the least recently used item without exceeding capacity."""
    cache = MemoryIdeasCache(2, 10)
    ideas = sample_ideas()
    cache.put("first", ideas)
    cache.put("second", ideas)
    cache.get("first")
    cache.put("third", ideas)
    assert cache.get("second") is None
    cache.put("first", ideas)
    assert cache.get("first") == ideas
    assert cache.get("third") == ideas


@pytest.mark.parametrize(("capacity", "ttl"), [(0, 10), (1, 0)])
def test_cache_rejects_unbounded_configuration(capacity: int, ttl: int) -> None:
    """Invalid bounds fail at construction."""
    with pytest.raises(ValueError, match="positive"):
        MemoryIdeasCache(capacity, ttl)


def test_system_clock_is_timezone_aware() -> None:
    """Persisted plan instants use explicit UTC."""
    offset = SystemClock().now().utcoffset()
    assert offset is not None and offset.total_seconds() == 0
