"""Version-one planning endpoints backed by deterministic services."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request, Response

from gatherly.api.errors import APIError, ErrorEnvelope
from gatherly.api.schemas import (
    CategoryDefault,
    EventBody,
    EventTypeInfo,
    ExportFormat,
    IdeasResult,
    PlanBody,
    RefineBody,
)
from gatherly.domain.budget import build_budget
from gatherly.domain.ideas import Plan
from gatherly.domain.models import BudgetPlan
from gatherly.domain.templates.events import EVENT_TEMPLATES
from gatherly.services.export_service import export_ics, export_json, export_markdown
from gatherly.services.plan_service import PlanService

router = APIRouter(
    prefix="/api/v1",
    responses={
        status: {"model": ErrorEnvelope}
        for status in (400, 403, 413, 415, 422, 429, 500, 503)
    },
)


def get_service(request: Request) -> PlanService:
    """Obtain the lifespan-owned service, with FastAPI dependency override support."""
    service = getattr(request.app.state, "planner", None)
    if service is None:
        raise APIError(
            503, "service_unavailable", "The planner is not ready. Try again."
        )
    return cast(PlanService, service)


type Planner = Annotated[PlanService, Depends(get_service)]


def _invalid_plan() -> APIError:
    return APIError(
        422, "invalid_plan", "Check the future event date and plan consistency."
    )


@router.get("/event-types")
async def event_types() -> tuple[EventTypeInfo, ...]:
    """List supported event types and unadjusted category percentages."""
    return tuple(
        EventTypeInfo(
            type=kind,
            categories=tuple(
                CategoryDefault(
                    category=item.category,
                    percent=item.percent,
                    rationale=item.rationale,
                )
                for item in template.categories
            ),
        )
        for kind, template in EVENT_TEMPLATES.items()
    )


@router.post("/plans")
async def create_plan(event: EventBody, planner: Planner) -> Plan:
    """Create a complete plan, returning HTTP 200 even when AI falls back."""
    try:
        return await planner.create(event)
    except ValueError:
        raise _invalid_plan() from None


@router.post("/plans/budget")
async def recalculate_budget(event: EventBody) -> BudgetPlan:
    """Recalculate money immediately without the clock, cache or LLM."""
    return build_budget(event)


@router.post("/plans/ideas")
async def regenerate_ideas(event: EventBody, planner: Planner) -> IdeasResult:
    """Refresh ideas only, with fallback and an explicit availability flag."""
    try:
        ideas, available = await planner.regenerate_ideas(event)
    except ValueError:
        raise _invalid_plan() from None
    return IdeasResult(
        ideas=ideas, ai_status="available" if available else "unavailable"
    )


@router.post("/plans/refine")
async def refine_plan(body: RefineBody, planner: Planner) -> Plan:
    """Apply a selected creative refinement after any explicit budget recalculation."""
    try:
        return await planner.refine(body.plan, body.change)
    except ValueError:
        raise _invalid_plan() from None


@router.post(
    "/plans/export",
    response_class=Response,
    responses={
        200: {
            "description": "Plan attachment",
            "content": {
                "text/markdown": {"schema": {"type": "string"}},
                "application/json": {"schema": {"$ref": "#/components/schemas/Plan"}},
                "text/calendar": {"schema": {"type": "string"}},
            },
        }
    },
)
async def export_plan(
    plan: PlanBody,
    format: Annotated[ExportFormat, Query()] = "md",
) -> Response:
    """Download a deterministic export; filenames never contain user text."""
    exporters = {
        "md": (export_markdown, "text/markdown"),
        "json": (export_json, "application/json"),
        "ics": (export_ics, "text/calendar"),
    }
    exporter, media_type = exporters[format]
    try:
        content = exporter(plan)
    except ValueError:
        raise _invalid_plan() from None
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="gatherly-plan.{format}"',
        },
    )
