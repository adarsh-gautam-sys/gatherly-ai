"""Strict immutable values shared by the deterministic planning engines."""

from datetime import date as Date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_GUESTS = 5_000
MAX_BUDGET_MINOR = 1_000_000_000
MAX_NAME_LENGTH = 120
MAX_PREFERENCE_LENGTH = 500
MAX_NOTES_LENGTH = 2_000
PERCENT_TOTAL = 100

type EventType = Literal["wedding", "birthday", "community"]
type Currency = Literal["INR", "USD", "EUR", "GBP", "JPY"]
type Priority = Annotated[int, Field(strict=True, ge=1, le=3)]
type Phase = Literal["Foundations", "Bookings", "Details", "Final Week", "Event Day"]
type VendorStatus = Literal["todo", "contacted", "booked", "not_needed"]
type MilestoneStatus = Literal["upcoming", "due_now", "overdue"]
type ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_LENGTH),
]
type Description = Annotated[str, Field(min_length=1, max_length=MAX_NOTES_LENGTH)]
type Preference = Annotated[str, Field(max_length=MAX_PREFERENCE_LENGTH)]
type Amount = Annotated[int, Field(ge=0, lt=MAX_BUDGET_MINOR)]


class DomainModel(BaseModel):
    """Reject coercion and unknown fields, and keep nested planning values immutable."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class EventRequest(DomainModel):
    """Event intake in integer minor currency units, with bounded untrusted text."""

    type: EventType
    name: ShortText
    date: Date
    guests: Annotated[int, Field(ge=1, le=MAX_GUESTS)]
    budget: Annotated[int, Field(gt=0, lt=MAX_BUDGET_MINOR)]
    currency: Currency
    region: Annotated[str, Field(max_length=MAX_NAME_LENGTH)] = ""
    preferences: Preference = ""
    dietary: Preference = ""
    interests: Preference = ""
    notes: Annotated[str, Field(max_length=MAX_NOTES_LENGTH)] = ""

    def validate_future_date(self, today: Date) -> None:
        """Reject today and past events using an explicitly supplied clock value."""
        if self.date <= today:
            raise ValueError("Event date must be in the future.")


class BudgetLine(DomainModel):
    """One category's target percentage and rounded integer allocation."""

    category: ShortText
    percent: Annotated[int, Field(ge=0, le=PERCENT_TOTAL)]
    amount: Amount
    rationale: Description


class BudgetPlan(DomainModel):
    """A complete allocation; per_guest is rounded down to a whole minor unit."""

    lines: Annotated[tuple[BudgetLine, ...], Field(min_length=1)]
    total: Annotated[int, Field(gt=0, lt=MAX_BUDGET_MINOR)]
    per_guest: Amount
    warnings: tuple[Description, ...] = ()

    @model_validator(mode="after")
    def validate_allocation(self) -> Self:
        """Require unique categories, complete percentages and conservation of money."""
        if len({line.category for line in self.lines}) != len(self.lines):
            raise ValueError("Budget categories must be unique.")
        if sum(line.percent for line in self.lines) != PERCENT_TOTAL:
            raise ValueError("Budget percentages must sum to 100.")
        if sum(line.amount for line in self.lines) != self.total:
            raise ValueError("Budget allocations must sum to the total.")
        return self


class Milestone(DomainModel):
    """A scheduled task whose phase can be used to group the chronological timeline."""

    id: ShortText
    title: ShortText
    due_date: Date
    phase: Phase
    priority: Priority
    status: MilestoneStatus
    linked_category: ShortText | None = None
    linked_vendor: ShortText | None = None
    completed: bool = False


class VendorItem(DomainModel):
    """A vendor or coordination role and its linked category budget, not a quote."""

    category: ShortText
    linked_category: ShortText
    why: Description
    questions: Annotated[tuple[Description, ...], Field(min_length=1)]
    documents: Annotated[tuple[Description, ...], Field(min_length=1)]
    lead_time_days: Annotated[int, Field(ge=0)]
    priority: Priority
    status: VendorStatus = "todo"
    allocated_amount: Amount
