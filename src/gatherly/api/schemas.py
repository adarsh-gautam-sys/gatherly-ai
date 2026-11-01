"""HTTP contracts and a strict JSON boundary for immutable domain values."""

import json
from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator

from gatherly.domain.ideas import Ideas, Plan, Refinement
from gatherly.domain.models import DomainModel, EventRequest, EventType


def json_model[T: BaseModel](model: type[T]) -> Callable[[object], T]:
    """Accept JSON dates and arrays without relaxing strict numeric validation."""

    def validate(value: object) -> T:
        if isinstance(value, model):
            return value
        return model.model_validate_json(json.dumps(value, allow_nan=False))

    return validate


class RefineRequest(DomainModel):
    """Client-held plan plus explicit affected sections and optional budget change."""

    plan: Plan
    change: Refinement


class IdeasResult(DomainModel):
    """Creative refresh without duplicating the deterministic plan components."""

    ideas: Ideas
    ai_status: Literal["available", "unavailable"]


class CategoryDefault(DomainModel):
    """An event category's baseline percentage and explanation."""

    category: str
    percent: int
    rationale: str


class EventTypeInfo(DomainModel):
    """Static intake metadata, before guest-count or budget adjustments."""

    type: EventType
    categories: tuple[CategoryDefault, ...]


type EventBody = Annotated[EventRequest, BeforeValidator(json_model(EventRequest))]
type PlanBody = Annotated[Plan, BeforeValidator(json_model(Plan))]
type RefineBody = Annotated[RefineRequest, BeforeValidator(json_model(RefineRequest))]
type ExportFormat = Literal["md", "json", "ics"]
