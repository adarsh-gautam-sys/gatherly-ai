"""System clock adapter, separate from the pure planning domain."""

from datetime import UTC, datetime


class SystemClock:
    """Supply aware UTC timestamps to services."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""
        return datetime.now(UTC)
