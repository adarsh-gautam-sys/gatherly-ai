"""Template consistency and vendor-to-budget integration for all three event types."""

import pytest

from gatherly.domain.budget import build_budget
from gatherly.domain.models import EventType
from gatherly.domain.templates.events import EVENT_TEMPLATES
from gatherly.domain.vendors import build_vendors
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_vendor_checklist_links_every_allocation(event_type: EventType) -> None:
    """Link each non-reserve category to guidance and its exact assigned amount."""
    budget = build_budget(event_request(event_type))
    vendors = build_vendors(event_type, budget)
    amounts = {line.category: line.amount for line in budget.lines}
    assert len(vendors) == len(budget.lines) - 1
    assert {vendor.linked_category for vendor in vendors} == set(amounts) - {
        "Contingency"
    }
    assert [vendor.priority for vendor in vendors] == sorted(
        vendor.priority for vendor in vendors
    )
    for vendor in vendors:
        assert vendor.allocated_amount == amounts[vendor.linked_category]
        assert vendor.why and vendor.questions and vendor.documents
        assert vendor.status == "todo"
        assert vendor.lead_time_days > 0


def test_mismatched_budget_is_rejected() -> None:
    """A wedding allocation cannot silently populate a birthday checklist."""
    with pytest.raises(ValueError, match="do not match"):
        build_vendors("birthday", build_budget(event_request("wedding")))


def test_community_guidance_covers_permits_volunteers_sound_and_safety() -> None:
    """The community template includes each obligation named in the PRD persona."""
    vendors = build_vendors("community", build_budget(event_request("community")))
    assert {vendor.category for vendor in vendors} >= {
        "Venue and permits coordinator",
        "Volunteer coordinator",
        "AV provider",
        "Safety coordinator",
    }
    safety = next(
        vendor for vendor in vendors if vendor.category == "Safety coordinator"
    )
    assert "first-aid" in safety.documents[0]
    assert "insurance" in safety.documents[0]


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_templates_have_unique_ids_and_valid_cross_links(event_type: EventType) -> None:
    """Static data cannot leave broken links or inconsistent booking lead times."""
    template = EVENT_TEMPLATES[event_type]
    categories = {category.category: category for category in template.categories}
    assert len(categories) == len(template.categories)
    assert sum(category.percent for category in template.categories) == 100
    assert len({task.id for task in template.milestones}) == len(template.milestones)
    assert len({category.vendor for category in template.categories}) == len(
        template.categories
    )
    for task in template.milestones:
        assert 0 <= task.days_before <= template.standard_lead_days
        if task.category is not None:
            assert task.category in categories
            assert task.vendor == categories[task.category].vendor
    for category in template.categories:
        if category.vendor is not None:
            assert any(
                task.vendor == category.vendor
                and task.days_before == category.lead_days
                for task in template.milestones
            )
