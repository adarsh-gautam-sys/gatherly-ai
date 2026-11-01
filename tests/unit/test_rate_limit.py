"""Verify bounded per-client admission with a deterministic monotonic clock."""

from gatherly.infra.rate_limit import RateLimiter


def test_fixed_window_is_per_client_and_resets_at_exact_deadline() -> None:
    """Repeated traffic cannot extend the counter's expiry time."""
    now = [0.0]
    limiter = RateLimiter(2, 3, lambda: now[0])
    assert limiter.consume("first") == limiter.consume("first") == 0
    assert limiter.consume("first") == 60
    assert limiter.consume("second") == 0
    now[0] = 59.5
    assert limiter.consume("first") == 1
    now[0] = 60
    assert limiter.consume("first") == 0


def test_full_counter_store_fails_closed_without_evicting_active_clients() -> None:
    """Rotating client identifiers cannot reset an existing client's limit."""
    now = [0.0]
    limiter = RateLimiter(1, 1, lambda: now[0])
    assert limiter.consume("first") == 0
    assert limiter.consume("new-client") == 60
    assert limiter.consume("first") == 60
    now[0] = 60
    assert limiter.consume("new-client") == 0
