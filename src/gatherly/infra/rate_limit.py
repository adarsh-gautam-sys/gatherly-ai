"""Bounded process-local fixed-window rate limiting with an injected timer."""

import hashlib
import math
import secrets
from collections import OrderedDict
from collections.abc import Callable
from time import monotonic

WINDOW_SECONDS = 60


class RateLimiter:
    """Keep expiring counters under salted hashes instead of retaining IP text."""

    def __init__(
        self,
        limit: int,
        capacity: int,
        timer: Callable[[], float] = monotonic,
    ) -> None:
        """Configure bounded counters and a process-private hashing salt."""
        self._limit = limit
        self._capacity = capacity
        self._timer = timer
        self._salt = secrets.token_bytes(32)
        self._entries: OrderedDict[bytes, tuple[float, int]] = OrderedDict()

    def consume(self, address: str) -> int:
        """Return zero if permitted, otherwise seconds until a retry is possible."""
        now = self._timer()
        while self._entries and next(iter(self._entries.values()))[0] <= now:
            self._entries.popitem(last=False)
        key = hashlib.blake2s(address.encode(), key=self._salt).digest()
        if key not in self._entries:
            if len(self._entries) >= self._capacity:
                return max(1, math.ceil(next(iter(self._entries.values()))[0] - now))
            self._entries[key] = (now + WINDOW_SECONDS, 0)
        expires, count = self._entries[key]
        if count >= self._limit:
            return max(1, math.ceil(expires - now))
        self._entries[key] = (expires, count + 1)
        return 0
