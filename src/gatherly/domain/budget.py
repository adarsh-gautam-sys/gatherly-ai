"""Integer-only budget allocation with stable largest-remainder rounding."""

from gatherly.domain.models import PERCENT_TOTAL, BudgetLine, BudgetPlan, EventRequest
from gatherly.domain.templates import (
    CONTINGENCY,
    LOW_BUDGET_FOOD_SHIFT,
    LOW_BUDGET_PER_GUEST,
    MAX_FOOD_SHIFT,
    EventTemplate,
)
from gatherly.domain.templates.events import EVENT_TEMPLATES


def _apportion(total: int, weights: tuple[int, ...]) -> tuple[int, ...]:
    denominator = sum(weights)
    amounts = [total * weight // denominator for weight in weights]
    ranked = sorted(
        range(len(weights)),
        key=lambda index: -(total * weights[index] % denominator),
    )
    for index in ranked[: total - sum(amounts)]:
        amounts[index] += 1
    return tuple(amounts)


def _percentages(
    event: EventRequest, template: EventTemplate, low_budget: bool
) -> tuple[int, ...]:
    food = next(c for c in template.categories if c.category == template.food_category)
    reserve = next(c.percent for c in template.categories if c.category == CONTINGENCY)
    guest_shift = (
        food.percent
        * (event.guests - template.baseline_guests)
        // template.baseline_guests
    )
    shift = guest_shift + (LOW_BUDGET_FOOD_SHIFT if low_budget else 0)
    food_percent = food.percent + max(-MAX_FOOD_SHIFT, min(MAX_FOOD_SHIFT, shift))
    others = tuple(
        c for c in template.categories if c.category not in (food.category, CONTINGENCY)
    )
    redistributed = iter(
        _apportion(
            PERCENT_TOTAL - reserve - food_percent, tuple(c.percent for c in others)
        )
    )
    return tuple(
        food_percent
        if c.category == food.category
        else reserve
        if c.category == CONTINGENCY
        else next(redistributed)
        for c in template.categories
    )


def build_budget(event: EventRequest) -> BudgetPlan:
    """Allocate an event's budget exactly, with a guest-aware food share and reserve."""
    template = EVENT_TEMPLATES[event.type]
    threshold = LOW_BUDGET_PER_GUEST[event.currency][event.type]
    low_budget = event.budget < threshold * event.guests
    percentages = _percentages(event, template, low_budget)
    amounts = _apportion(event.budget, percentages)
    lines = tuple(
        BudgetLine(
            category=category.category,
            percent=percent,
            amount=amount,
            rationale=category.rationale
            + (
                " Share adjusted for guest count and per-guest budget."
                if percent != category.percent
                else ""
            ),
        )
        for category, percent, amount in zip(
            template.categories, percentages, amounts, strict=True
        )
    )
    warnings = (
        (
            (
                "The per-guest budget is below this planner's heuristic threshold. "
                "Consider fewer guests, a simpler menu or a donated venue; "
                "check local costs."
            ),
        )
        if low_budget
        else ()
    )
    return BudgetPlan(
        lines=lines,
        total=event.budget,
        per_guest=event.budget // event.guests,
        warnings=warnings,
    )
