"""Vendor guidance linked to deterministic budget categories."""

from gatherly.domain.models import BudgetPlan, EventType, VendorItem
from gatherly.domain.templates.events import EVENT_TEMPLATES


def build_vendors(event_type: EventType, budget: BudgetPlan) -> tuple[VendorItem, ...]:
    """Build a prioritised checklist and reject budgets from a different event type."""
    template = EVENT_TEMPLATES[event_type]
    amounts = {line.category: line.amount for line in budget.lines}
    if set(amounts) != {category.category for category in template.categories}:
        raise ValueError("Budget categories do not match the event type.")
    items = (
        VendorItem(
            category=category.vendor,
            linked_category=category.category,
            why=category.rationale,
            questions=category.questions,
            documents=category.documents,
            lead_time_days=category.lead_days,
            priority=category.priority,
            allocated_amount=amounts[category.category],
        )
        for category in template.categories
        if category.vendor is not None
    )
    return tuple(sorted(items, key=lambda item: item.priority))
