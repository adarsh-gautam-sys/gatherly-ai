"""Immutable event templates and explicit planning policies."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from gatherly.domain.models import Currency, EventType, Phase, Priority

MAX_FOOD_SHIFT = 10
LOW_BUDGET_FOOD_SHIFT = 5
CONTINGENCY = "Contingency"

# These are planning heuristics in minor units, not researched market prices.
LOW_BUDGET_PER_GUEST: Mapping[Currency, Mapping[EventType, int]] = MappingProxyType(
    {
        "INR": MappingProxyType(
            {"wedding": 200_000, "birthday": 50_000, "community": 20_000}
        ),
        "USD": MappingProxyType(
            {"wedding": 5_000, "birthday": 1_500, "community": 500}
        ),
        "EUR": MappingProxyType(
            {"wedding": 4_500, "birthday": 1_500, "community": 500}
        ),
        "GBP": MappingProxyType(
            {"wedding": 4_000, "birthday": 1_200, "community": 400}
        ),
        "JPY": MappingProxyType(
            {"wedding": 6_000, "birthday": 1_800, "community": 600}
        ),
    }
)


@dataclass(frozen=True)
class CategoryTemplate:
    """Budget defaults and the checklist content for a single vendor category."""

    category: str
    percent: int
    rationale: str
    vendor: str | None = None
    questions: tuple[str, ...] = ()
    documents: tuple[str, ...] = ()
    lead_days: int = 0
    priority: Priority = 2


@dataclass(frozen=True)
class MilestoneTemplate:
    """A stable task ID and its standard offset before the event."""

    id: str
    title: str
    days_before: int
    phase: Phase
    priority: Priority
    category: str | None = None
    vendor: str | None = None


@dataclass(frozen=True)
class EventTemplate:
    """All static guidance for one event type."""

    standard_lead_days: int
    baseline_guests: int
    food_category: str
    categories: tuple[CategoryTemplate, ...]
    milestones: tuple[MilestoneTemplate, ...]
