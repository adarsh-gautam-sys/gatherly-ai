"""Backwards scheduling using a caller-supplied date instead of system time."""

from datetime import date, timedelta

from gatherly.domain.models import EventRequest, Milestone
from gatherly.domain.templates.events import EVENT_TEMPLATES


def build_timeline(event: EventRequest, today: date) -> tuple[Milestone, ...]:
    """Schedule tasks, surface missed lead times and compress short planning windows."""
    event.validate_future_date(today)
    template = EVENT_TEMPLATES[event.type]
    remaining = (event.date - today).days
    milestones: list[Milestone] = []
    for task in template.milestones:
        if task.days_before >= remaining:
            due_date = today
        else:
            offset = (
                task.days_before
                * min(remaining, template.standard_lead_days)
                // template.standard_lead_days
            )
            due_date = event.date - timedelta(days=offset)
        milestones.append(
            Milestone(
                id=task.id,
                title=task.title,
                due_date=due_date,
                phase=task.phase,
                priority=task.priority,
                status="due_now" if due_date == today else "upcoming",
                linked_category=task.category,
                linked_vendor=task.vendor,
            )
        )
    return tuple(sorted(milestones, key=lambda item: (item.due_date, item.priority)))
