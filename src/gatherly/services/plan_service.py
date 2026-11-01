"""Orchestrate deterministic plans and bounded creative generation with fallback."""

import asyncio
import hashlib
import json

from gatherly.domain.budget import build_budget
from gatherly.domain.fallback import fallback_ideas
from gatherly.domain.ideas import Ideas, Plan, Refinement
from gatherly.domain.models import EventRequest, VendorItem
from gatherly.domain.timeline import build_timeline
from gatherly.domain.vendors import build_vendors
from gatherly.services.idea_validation import sanitise_ideas
from gatherly.services.ports import (
    Clock,
    IdeasCache,
    IdeasGenerator,
    IdeasUnavailable,
    IdeaTask,
)

MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 0.2


class PlanService:
    """Assemble plans with injected adapters; never send arithmetic to the LLM."""

    def __init__(
        self,
        generator: IdeasGenerator | None,
        cache: IdeasCache,
        clock: Clock,
        namespace: str,
        timeout_seconds: float = 6,
        forbidden: tuple[str, ...] = (),
    ) -> None:
        """Inject every external dependency and the bounded generation policy."""
        self._generator = generator
        self._cache = cache
        self._clock = clock
        self._namespace = namespace
        self._timeout = timeout_seconds
        self._forbidden = forbidden

    async def create(self, event: EventRequest) -> Plan:
        """Compute deterministic components before obtaining optional creative ideas."""
        now = self._clock.now()
        event.validate_future_date(now.date())
        budget = build_budget(event)
        timeline = build_timeline(event, now.date())
        vendors = build_vendors(event.type, budget)
        ideas, available = await self._ideas(IdeaTask(event=event, budget=budget))
        return Plan(
            request=event,
            budget=budget,
            timeline=timeline,
            vendors=vendors,
            ideas=ideas,
            ai_status="available" if available else "unavailable",
            generated_at=now,
        )

    async def refine(self, plan: Plan, change: Refinement) -> Plan:
        """Apply explicit budget changes deterministically and refine selected ideas."""
        now = self._clock.now()
        values = plan.request.model_dump()
        if change.budget is not None:
            values["budget"] = change.budget
        event = EventRequest.model_validate(values)
        event.validate_future_date(now.date())
        budget = build_budget(event)
        sections = tuple(
            dict.fromkeys(
                change.sections
                + (("saving_tips",) if change.budget is not None else ())
            )
        )
        try:
            current = sanitise_ideas(plan.ideas, budget, self._forbidden)
        except ValueError:
            current = fallback_ideas(event, budget)
        ideas, available = await self._ideas(
            IdeaTask(
                event=event,
                budget=budget,
                current=current,
                instruction=change.instruction,
                sections=sections,
            )
        )
        statuses = {vendor.category: vendor.status for vendor in plan.vendors}
        vendors = tuple(
            VendorItem.model_validate(
                vendor.model_dump() | {"status": statuses.get(vendor.category, "todo")}
            )
            for vendor in build_vendors(event.type, budget)
        )
        return Plan(
            request=event,
            budget=budget,
            timeline=plan.timeline,
            vendors=vendors,
            ideas=ideas,
            ai_status="available" if available else "unavailable",
            generated_at=now,
        )

    async def _ideas(self, task: IdeaTask) -> tuple[Ideas, bool]:
        key = hashlib.sha256(
            (
                self._namespace
                + json.dumps(task.model_dump(mode="json"), sort_keys=True)
            ).encode()
        ).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached, True
        if self._generator is not None:
            for attempt in range(MAX_ATTEMPTS):
                try:
                    ideas = await asyncio.wait_for(
                        self._generator.generate(task), timeout=self._timeout
                    )
                    ideas = sanitise_ideas(ideas, task.budget, self._forbidden)
                    self._cache.put(key, ideas)
                    return ideas, True
                except (IdeasUnavailable, TimeoutError, ValueError):
                    if attempt == 0:
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
        return self._fallback(task), False

    @staticmethod
    def _fallback(task: IdeaTask) -> Ideas:
        fallback = fallback_ideas(task.event, task.budget)
        if task.current is None:
            return fallback
        values = task.current.model_dump(mode="json")
        replacement = {
            key: value
            for key, value in fallback.model_dump(mode="json").items()
            if key in task.sections
        }
        return Ideas.model_validate_json(json.dumps(values | replacement))
