"""Examples with independently calculated expected budget allocations."""

import pytest

from gatherly.domain.budget import build_budget
from gatherly.domain.models import MAX_BUDGET_MINOR, Currency, EventType
from gatherly.domain.templates import LOW_BUDGET_PER_GUEST
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize(
    ("event_type", "guests", "percentages"),
    [
        ("wedding", 100, (20, 30, 10, 10, 10, 7, 2, 3, 8)),
        ("birthday", 25, (15, 35, 12, 18, 3, 7, 3, 7)),
        ("community", 100, (20, 25, 12, 10, 10, 10, 5, 8)),
    ],
)
def test_baseline_matches_prd_exactly(
    event_type: EventType, guests: int, percentages: tuple[int, ...]
) -> None:
    """Default guest counts and sufficient budgets reproduce the PRD table."""
    budget = build_budget(event_request(event_type, guests=guests))
    assert tuple(line.percent for line in budget.lines) == percentages
    assert tuple(line.amount for line in budget.lines) == tuple(
        p * 10_000 for p in percentages
    )
    assert not budget.warnings


def test_largest_remainder_uses_stable_template_order_for_ties() -> None:
    """Equal remainders favour earlier categories, not random or float rounding."""
    budget = build_budget(event_request(budget=1_000_005))
    assert tuple(line.amount for line in budget.lines) == (
        200001,
        300002,
        100001,
        100001,
        100000,
        70000,
        20000,
        30000,
        80000,
    )


def test_guest_count_changes_food_share_without_reducing_reserve() -> None:
    """Guest adjustments are capped at ten percentage points in either direction."""
    small = build_budget(event_request(guests=1, budget=MAX_BUDGET_MINOR - 1))
    large = build_budget(event_request(guests=5000, budget=MAX_BUDGET_MINOR - 1))
    assert small.lines[1].percent == 20
    assert large.lines[1].percent == 40
    assert small.lines[-1].percent == large.lines[-1].percent == 8
    assert "adjusted" in large.lines[1].rationale


@pytest.mark.parametrize("currency", ["INR", "USD", "EUR", "GBP", "JPY"])
def test_low_budget_threshold_boundary_and_food_adjustment(currency: Currency) -> None:
    """Each currency uses its own minor-unit threshold, with no exchange conversion."""
    threshold = LOW_BUDGET_PER_GUEST[currency]["birthday"] * 25
    low = build_budget(
        event_request("birthday", guests=25, currency=currency, budget=threshold - 1)
    )
    sufficient = build_budget(
        event_request("birthday", guests=25, currency=currency, budget=threshold)
    )
    assert low.warnings and "Consider" in low.warnings[0]
    assert not sufficient.warnings
    assert low.lines[1].percent == 40
    assert sufficient.lines[1].percent == 35
    assert low.lines[-1].percent == 7


def test_one_minor_unit_is_conserved_even_with_zero_category_allocations() -> None:
    """Tiny budgets retain contingency even if its rounded amount is zero."""
    budget = build_budget(event_request(budget=1, guests=5000))
    assert sum(line.amount for line in budget.lines) == 1
    assert budget.lines[1].amount == 1
    assert budget.lines[-1].category == "Contingency"
    assert budget.lines[-1].amount == 0
    assert budget.per_guest == 0
    assert budget.warnings


def test_what_if_recalculation_has_no_hidden_state() -> None:
    """Changing only money returns a new coherent allocation without mutating intake."""
    event = event_request()
    original = build_budget(event)
    changed = build_budget(event_request(budget=2_000_000))
    assert changed.total == original.total * 2
    assert event.budget == original.total
    assert build_budget(event) == original
