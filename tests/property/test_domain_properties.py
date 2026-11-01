"""Generated invariant checks spanning event types, currencies, money and calendars."""

from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from gatherly.domain.budget import build_budget
from gatherly.domain.models import MAX_BUDGET_MINOR, Currency, EventType
from gatherly.domain.timeline import build_timeline
from gatherly.domain.vendors import build_vendors
from tests.unit.domain_helpers import event_request


@settings(max_examples=300, derandomize=True)
@given(
    event_type=st.sampled_from(("wedding", "birthday", "community")),
    currency=st.sampled_from(("INR", "USD", "EUR", "GBP", "JPY")),
    guests=st.integers(min_value=1, max_value=5000),
    total=st.integers(min_value=1, max_value=MAX_BUDGET_MINOR - 1),
)
def test_budget_conserves_every_minor_unit_and_vendor_links(
    event_type: EventType,
    currency: Currency,
    guests: int,
    total: int,
) -> None:
    """Conserve money, keep a reserve and link vendors without duplication."""
    event = event_request(event_type, guests=guests, budget=total, currency=currency)
    plan = build_budget(event)
    assert sum(line.amount for line in plan.lines) == total
    assert sum(line.percent for line in plan.lines) == 100
    assert all(type(line.amount) is int and line.amount >= 0 for line in plan.lines)
    assert plan.lines[-1].category == "Contingency"
    assert plan.lines[-1].percent == (7 if event_type == "birthday" else 8)
    assert plan.per_guest == total // guests
    assert build_budget(event) == plan
    vendors = build_vendors(event_type, plan)
    assert (
        sum(vendor.allocated_amount for vendor in vendors) + plan.lines[-1].amount
        == total
    )


@settings(max_examples=300, derandomize=True)
@given(
    event_type=st.sampled_from(("wedding", "birthday", "community")),
    today=st.dates(min_value=date.min, max_value=date(9990, 1, 1)),
    remaining=st.integers(min_value=1, max_value=3000),
)
def test_timeline_is_sorted_bounded_and_deterministic(
    event_type: EventType,
    today: date,
    remaining: int,
) -> None:
    """Bound every milestone between the supplied planning date and event date."""
    event_date = today + timedelta(days=remaining)
    event = event_request(event_type, event_date=event_date)
    timeline = build_timeline(event, today)
    keys = [(task.due_date, task.priority) for task in timeline]
    assert keys == sorted(keys)
    assert all(today <= task.due_date <= event_date for task in timeline)
    assert all(
        task.status == ("due_now" if task.due_date == today else "upcoming")
        for task in timeline
    )
    assert timeline[-1].due_date == event_date
    assert len({task.id for task in timeline}) == len(timeline)
    assert build_timeline(event, today) == timeline
