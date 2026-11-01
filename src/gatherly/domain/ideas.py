"""Bounded creative output, refinement inputs and complete immutable plans."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StringConstraints

from gatherly.domain.models import (
    MAX_BUDGET_MINOR,
    MAX_NOTES_LENGTH,
    BudgetPlan,
    DomainModel,
    EventRequest,
    Milestone,
    ShortText,
    VendorItem,
)

MAX_IDEA_TEXT = 360
THEME_COUNT = 3
MAX_IDEA_ITEMS = 6
type IdeaText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_IDEA_TEXT),
]
type Colour = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
type IdeaSection = Literal[
    "concept_summary", "themes", "menu", "activities", "personal_touches", "saving_tips"
]
IDEA_SECTIONS: tuple[IdeaSection, ...] = (
    "concept_summary",
    "themes",
    "menu",
    "activities",
    "personal_touches",
    "saving_tips",
)


class Theme(DomainModel):
    """A theme's name, mood, colour palette and practical decor notes."""

    name: IdeaText
    mood: IdeaText
    colour_palette: Annotated[tuple[Colour, ...], Field(min_length=3, max_length=3)]
    decor_notes: IdeaText


class SavingTip(DomainModel):
    """A suggestion linked to an actual category; the model never supplies money."""

    category: ShortText
    suggestion: IdeaText


type Themes = Annotated[
    tuple[Theme, ...], Field(min_length=THEME_COUNT, max_length=THEME_COUNT)
]
type Suggestions = Annotated[
    tuple[IdeaText, ...], Field(min_length=1, max_length=MAX_IDEA_ITEMS)
]
type SavingTips = Annotated[
    tuple[SavingTip, ...], Field(min_length=1, max_length=MAX_IDEA_ITEMS)
]


class Ideas(DomainModel):
    """The creative portion of a plan, independent of deterministic calculations."""

    concept_summary: IdeaText
    themes: Themes
    menu: Suggestions
    activities: Suggestions
    personal_touches: Suggestions
    saving_tips: SavingTips


class IdeasPatch(DomainModel):
    """Only requested sections may be non-null during refinement."""

    concept_summary: IdeaText | None = None
    themes: Themes | None = None
    menu: Suggestions | None = None
    activities: Suggestions | None = None
    personal_touches: Suggestions | None = None
    saving_tips: SavingTips | None = None


class IdeasResponse(DomainModel):
    """Schema-constrained generation with an explicit out-of-scope refusal."""

    in_scope: bool
    ideas: Ideas | None


class RefinementResponse(DomainModel):
    """Schema-constrained partial refinement with an explicit refusal."""

    in_scope: bool
    changes: IdeasPatch | None


class Refinement(DomainModel):
    """Bounded instruction and explicit deterministic budget override."""

    instruction: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=MAX_NOTES_LENGTH
        ),
    ]
    sections: Annotated[
        tuple[IdeaSection, ...], Field(min_length=1, max_length=len(IDEA_SECTIONS))
    ] = IDEA_SECTIONS
    budget: Annotated[int, Field(gt=0, lt=MAX_BUDGET_MINOR)] | None = None


class Plan(DomainModel):
    """Complete plan assembled by services, never by the model."""

    request: EventRequest
    budget: BudgetPlan
    timeline: tuple[Milestone, ...]
    vendors: tuple[VendorItem, ...]
    ideas: Ideas
    ai_status: Literal["available", "unavailable"]
    generated_at: AwareDatetime
    schema_version: Literal["1"] = "1"
