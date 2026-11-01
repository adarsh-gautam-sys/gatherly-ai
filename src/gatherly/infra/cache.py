"""A process-local LRU cache with an injectable monotonic expiry clock."""

from collections import OrderedDict
from collections.abc import Callable
from time import monotonic

from gatherly.domain.ideas import Ideas


class MemoryIdeasCache:
    """Retain only bounded, expiring, immutable ideas; never raw request text."""

    def __init__(
        self, capacity: int, ttl_seconds: int, timer: Callable[[], float] = monotonic
    ) -> None:
        """Create an empty cache with positive capacity and time-to-live."""
        if capacity < 1 or ttl_seconds < 1:
            raise ValueError("Cache capacity and TTL must be positive.")
        self._capacity = capacity
        self._ttl = ttl_seconds
        self._timer = timer
        self._entries: OrderedDict[str, tuple[float, Ideas]] = OrderedDict()

    def get(self, key: str) -> Ideas | None:
        """Return a live value and refresh recency without extending its lifetime."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._timer() >= expires_at:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return value

    def put(self, key: str, value: Ideas) -> None:
        """Store a value and evict the least-recently-used entry if full."""
        self._entries[key] = (self._timer() + self._ttl, value)
        self._entries.move_to_end(key)
        if len(self._entries) > self._capacity:
            self._entries.popitem(last=False)
