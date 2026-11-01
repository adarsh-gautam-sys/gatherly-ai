"""Validate cross-field consistency of client-held plans at import boundaries."""

from gatherly.domain.budget import build_budget
from gatherly.domain.ideas import Plan
from gatherly.domain.templates.events import EVENT_TEMPLATES
from gatherly.domain.vendors import build_vendors


def validate_saved_plan(plan: Plan) -> None:
    """Reject contradictory money, vendor allocations or milestone identities."""
    if plan.budget != build_budget(plan.request):
        raise ValueError("Plan budget does not match its event request.")
    expected = build_vendors(plan.request.type, plan.budget)
    actual_values = [item.model_dump(exclude={"status"}) for item in plan.vendors]
    expected_values = [item.model_dump(exclude={"status"}) for item in expected]
    if actual_values != expected_values:
        raise ValueError("Vendor allocations do not match the budget.")
    tasks = {task.id: task for task in EVENT_TEMPLATES[plan.request.type].milestones}
    if len(plan.timeline) != len(tasks) or {item.id for item in plan.timeline} != set(
        tasks
    ):
        raise ValueError("Timeline must contain each expected milestone once.")
    for item in plan.timeline:
        task = tasks[item.id]
        if (
            item.due_date > plan.request.date
            or item.title != task.title
            or item.phase != task.phase
            or item.linked_category != task.category
            or item.linked_vendor != task.vendor
            or item.priority != task.priority
        ):
            raise ValueError("Timeline does not match the event template.")
