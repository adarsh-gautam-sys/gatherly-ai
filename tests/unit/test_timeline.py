"""Calendar, compression and priority examples with a fixed caller-supplied clock."""

from datetime import date, timedelta

import pytest

from gatherly.domain.models import EventType
from gatherly.domain.timeline import build_timeline
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize(
    ("event_type", "lead_days"),
    [
        ("wedding", 365),
        ("birthday", 42),
        ("community", 84),
    ],
)
def test_standard_lead_time_starts_today(event_type: EventType, lead_days: int) -> None:
    """The standard planning window begins with a due-now foundations task."""
    today = date(2028, 1, 1)
    event = event_request(event_type, event_date=today + timedelta(days=lead_days))
    timeline = build_timeline(event, today)
    assert timeline[0].due_date == today
    assert timeline[0].phase == "Foundations"
    assert timeline[0].status == "due_now"
    assert timeline[-1].due_date == event.date
    assert timeline[-1].phase == "Event Day"


def test_long_horizon_preserves_standard_offsets() -> None:
    """Extra time does not stretch tasks beyond the template's booking guidance."""
    event = event_request(event_date=date(2028, 6, 1))
    tasks = {task.id: task for task in build_timeline(event, date(2026, 1, 1))}
    assert tasks["wedding-scope"].due_date == date(2027, 6, 2)
    assert tasks["wedding-venue"].due_date == date(2027, 8, 6)
    assert tasks["wedding-confirm"].due_date == date(2028, 5, 25)
    assert all(task.status == "upcoming" for task in tasks.values())


def test_short_horizon_flags_missed_deadlines_and_compresses_remaining_tasks() -> None:
    """Missed lead times become urgent while future tasks use proportional offsets."""
    event = event_request("birthday", event_date=date(2028, 2, 22))
    tasks = {task.id: task for task in build_timeline(event, date(2028, 2, 1))}
    assert tasks["birthday-venue"].due_date == date(2028, 2, 1)
    assert tasks["birthday-venue"].status == "due_now"
    assert tasks["birthday-food"].status == "due_now"
    assert tasks["birthday-decor"].due_date == date(2028, 2, 15)
    assert tasks["birthday-confirm"].due_date == date(2028, 2, 19)


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_tomorrow_prioritises_all_overdue_preparation(event_type: EventType) -> None:
    """A one-day window orders urgent tasks by priority and retains event-day tasks."""
    today = date(2028, 2, 28)
    timeline = build_timeline(
        event_request(event_type, event_date=date(2028, 2, 29)), today
    )
    urgent = tuple(task for task in timeline if task.status == "due_now")
    assert len(urgent) == len(timeline) - 1
    assert all(task.due_date == today for task in urgent)
    assert [task.priority for task in urgent] == sorted(
        task.priority for task in urgent
    )
    assert timeline[-1].due_date == date(2028, 2, 29)


@pytest.mark.parametrize("today", [date(2028, 6, 1), date(2028, 6, 2)])
def test_timeline_rejects_today_and_past_events(today: date) -> None:
    """The scheduling entry point enforces future events before calculating offsets."""
    with pytest.raises(ValueError, match="future"):
        build_timeline(event_request(), today)


@pytest.mark.parametrize(
    ("today", "event_date"),
    [
        (date.min, date(1, 1, 2)),
        (date(9999, 12, 30), date.max),
        (date(2027, 12, 31), date(2028, 1, 1)),
    ],
)
def test_calendar_boundaries_do_not_overflow(today: date, event_date: date) -> None:
    """Year boundaries and the full supported date range remain safe."""
    timeline = build_timeline(event_request(event_date=event_date), today)
    assert all(today <= task.due_date <= event_date for task in timeline)
