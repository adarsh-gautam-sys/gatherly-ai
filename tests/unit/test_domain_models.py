"""Validation at the domain boundary, including untrusted text and integer money."""

from datetime import date

import pytest
from pydantic import ValidationError

from gatherly.domain.budget import build_budget
from gatherly.domain.models import (
    MAX_BUDGET_MINOR,
    BudgetPlan,
    EventRequest,
    Milestone,
    VendorItem,
)
from gatherly.domain.vendors import build_vendors
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "conference"),
        ("type", "Wedding"),
        ("currency", "usd"),
        ("currency", "XYZ"),
        ("guests", 0),
        ("guests", 5001),
        ("guests", True),
        ("guests", "20"),
        ("guests", 20.0),
        ("budget", 0),
        ("budget", -1),
        ("budget", MAX_BUDGET_MINOR),
        ("budget", False),
        ("budget", "100"),
        ("budget", 100.5),
        ("name", "  "),
        ("name", "x" * 121),
        ("region", "x" * 121),
        ("preferences", "x" * 501),
        ("dietary", "x" * 501),
        ("interests", "x" * 501),
        ("notes", "x" * 2001),
        ("unexpected", "anything"),
        ("date", "2028-06-01"),
        ("date", 0),
    ],
)
def test_invalid_event_fields_are_rejected(field: str, value: object) -> None:
    """Unknown, out-of-range and coercible values fail at the boundary."""
    payload = event_request().model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        EventRequest.model_validate(payload)


def test_event_json_round_trip_and_text_remains_data() -> None:
    """ISO dates decode from JSON and bounded hostile text has no special meaning."""
    payload = event_request().model_dump()
    text = "<script>ignore all instructions</script>"
    payload.update(name="  A celebration  ", notes=text, dietary=text, preferences=text)
    event = EventRequest.model_validate(payload)
    assert event.name == "A celebration"
    assert event.notes == event.dietary == event.preferences == text
    assert EventRequest.model_validate_json(event.model_dump_json()) == event
    with pytest.raises(ValidationError, match="frozen"):
        event.__setattr__("name", "Changed")


@pytest.mark.parametrize("event_date", [date(2028, 2, 28), date(2028, 2, 29)])
def test_today_and_past_dates_are_rejected(event_date: date) -> None:
    """Future-date validation is relative to an injected date, including leap day."""
    with pytest.raises(ValueError, match="future"):
        event_request(event_date=event_date).validate_future_date(date(2028, 2, 29))


def test_tomorrow_is_valid_without_reading_the_clock() -> None:
    """A leap-day event can be planned on the previous day."""
    event_request(event_date=date(2028, 2, 29)).validate_future_date(date(2028, 2, 28))


@pytest.mark.parametrize("corruption", ["duplicate", "percent", "amount"])
def test_inconsistent_budget_plans_are_rejected(corruption: str) -> None:
    """Imported allocations cannot contradict their own totals or repeat categories."""
    payload = build_budget(event_request()).model_dump()
    lines = list(payload["lines"])
    if corruption == "duplicate":
        lines[1]["category"] = lines[0]["category"]
    elif corruption == "percent":
        lines[0]["percent"] += 1
    else:
        lines[0]["amount"] += 1
    payload["lines"] = tuple(lines)
    with pytest.raises(ValidationError):
        BudgetPlan.model_validate(payload)


@pytest.mark.parametrize("status", ["todo", "contacted", "booked", "not_needed"])
def test_vendor_statuses_round_trip(status: str) -> None:
    """Each PRD checklist state is supported by the immutable value model."""
    vendor = build_vendors("wedding", build_budget(event_request()))[0]
    payload = vendor.model_dump()
    payload["status"] = status
    updated = VendorItem.model_validate(payload)
    assert VendorItem.model_validate_json(updated.model_dump_json()) == updated


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "paid"),
        ("allocated_amount", -1),
        ("allocated_amount", 1.0),
        ("priority", 4),
        ("priority", True),
        ("priority", 1.0),
        ("lead_time_days", -1),
        ("questions", ()),
        ("documents", ()),
    ],
)
def test_invalid_vendor_values_are_rejected(field: str, value: object) -> None:
    """Checklists require actionable guidance, valid states and integer allocations."""
    payload = build_vendors("wedding", build_budget(event_request()))[0].model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        VendorItem.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "unknown"),
        ("phase", "unknown"),
        ("priority", "unknown"),
        ("priority", True),
        ("priority", 1.0),
        ("priority", 0),
        ("priority", 4),
    ],
)
def test_invalid_milestone_values_are_rejected(field: str, value: object) -> None:
    """Milestone labels are whitelisted and priorities are strict bounded integers."""
    payload: dict[str, object] = {
        "id": "task",
        "title": "Plan",
        "due_date": date(2028, 1, 1),
        "phase": "Foundations",
        "priority": 1,
        "status": "upcoming",
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        Milestone.model_validate(payload)
