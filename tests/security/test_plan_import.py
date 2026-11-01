"""Imported client-held plans must retain deterministic cross-field consistency."""

from datetime import timedelta

import pytest

from tests.api.helpers import api_client
from tests.unit.ai_helpers import sample_plan


@pytest.mark.parametrize(
    "mutation",
    [
        "budget",
        "vendor_amount",
        "vendor_missing",
        "milestone_missing",
        "milestone_duplicate",
        "milestone_date",
        "milestone_title",
        "milestone_phase",
        "milestone_category",
        "milestone_vendor",
        "milestone_priority",
    ],
)
@pytest.mark.parametrize("endpoint", ["export", "refine"])
def test_inconsistent_saved_plans_are_rejected_before_processing(
    mutation: str,
    endpoint: str,
) -> None:
    """Reject contradictory budgets and changes to template task identities."""
    plan = sample_plan()
    data = plan.model_dump(mode="json")
    if mutation == "budget":
        data["request"]["budget"] += 1
    elif mutation == "vendor_amount":
        data["vendors"][0]["allocated_amount"] += 1
    elif mutation == "vendor_missing":
        data["vendors"].pop()
    elif mutation == "milestone_missing":
        data["timeline"].pop()
    elif mutation == "milestone_duplicate":
        data["timeline"][0] = data["timeline"][1]
    else:
        fields = {
            "milestone_date": (
                "due_date",
                (plan.request.date + timedelta(days=1)).isoformat(),
            ),
            "milestone_title": ("title", "Arbitrary task"),
            "milestone_phase": ("phase", "Event Day"),
            "milestone_category": ("linked_category", "Unknown category"),
            "milestone_vendor": ("linked_vendor", "Unknown vendor"),
            "milestone_priority": ("priority", 3),
        }
        key, value = fields[mutation]
        data["timeline"][0][key] = value
    body = (
        data
        if endpoint == "export"
        else {"plan": data, "change": {"instruction": "Simpler"}}
    )
    with api_client() as client:
        response = client.post(f"/api/v1/plans/{endpoint}", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_plan"
