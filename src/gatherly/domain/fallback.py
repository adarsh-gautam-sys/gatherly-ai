"""Conservative template ideas that require neither an API key nor user-text echoing."""

from gatherly.domain.ideas import Ideas, SavingTip, Theme
from gatherly.domain.models import BudgetPlan, EventRequest

THEME_NAMES = {
    "wedding": ("Shared stories", "Garden gathering", "Simple elegance"),
    "birthday": ("Favourite memories", "Playful colours", "Creative afternoon"),
    "community": ("Neighbourhood connections", "Shared skills", "Local stories"),
}


def fallback_ideas(event: EventRequest, budget: BudgetPlan) -> Ideas:
    """Return usable event-specific ideas without guessing dietary compatibility."""
    return Ideas(
        concept_summary=(
            f"A welcoming {event.type} focused on shared time and a manageable plan."
        ),
        themes=tuple(
            Theme(
                name=name,
                mood="Warm and relaxed",
                colour_palette=("#315C45", "#F5E9D3", "#B76545"),
                decor_notes=(
                    "Reuse simple decorations and keep routes and seating accessible."
                ),
            )
            for name in THEME_NAMES[event.type]
        ),
        menu=(
            "Confirm each guest's dietary and allergen needs before selecting dishes; "
            "offer clearly labelled choices and check cross-contact with the caterer.",
        ),
        activities=("Offer an optional shared-story activity and a quieter space.",),
        personal_touches=(
            "Invite guests to contribute a memory or message with their consent.",
        ),
        saving_tips=(
            SavingTip(
                category=budget.lines[0].category,
                suggestion=(
                    "Compare what is included in the allocated category "
                    "and reuse available resources."
                ),
            ),
        ),
    )
