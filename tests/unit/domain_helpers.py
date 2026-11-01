"""Small event factory shared by deterministic domain tests."""

from datetime import date

from gatherly.domain.models import Currency, EventRequest, EventType


def event_request(
    event_type: EventType = "wedding",
    *,
    guests: int = 100,
    budget: int = 1_000_000,
    currency: Currency = "USD",
    event_date: date = date(2028, 6, 1),
) -> EventRequest:
    """Create a structurally valid event with explicit deterministic defaults."""
    return EventRequest(
        type=event_type,
        name="A celebration",
        date=event_date,
        guests=guests,
        budget=budget,
        currency=currency,
    )
