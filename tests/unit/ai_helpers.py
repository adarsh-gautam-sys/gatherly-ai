"""Deterministic fakes for creative service tests."""

import asyncio
from datetime import UTC, datetime

from gatherly.domain.budget import build_budget
from gatherly.domain.fallback import fallback_ideas
from gatherly.domain.ideas import Ideas, Plan
from gatherly.infra.cache import MemoryIdeasCache
from gatherly.services.plan_service import PlanService
from gatherly.services.ports import IdeasUnavailable, IdeaTask
from tests.unit.domain_helpers import event_request


class FixedClock:
    """Keep service date validation independent of the wall clock."""

    def now(self) -> datetime:
        """Return a timezone-aware instant before the example event."""
        return datetime(2028, 1, 1, tzinfo=UTC)


def sample_plan() -> Plan:
    """Create a fixed offline plan for export and import boundary tests."""
    service = PlanService(None, MemoryIdeasCache(1, 10), FixedClock(), "export")
    return asyncio.run(service.create(event_request()))


def idea_task() -> IdeaTask:
    """Return a valid request and deterministically computed budget."""
    event = event_request()
    return IdeaTask(event=event, budget=build_budget(event))


def sample_ideas() -> Ideas:
    """Return valid creative data distinguishable from automatic fallback."""
    task = idea_task()
    values = fallback_ideas(task.event, task.budget).model_dump()
    values["concept_summary"] = "An evening of shared stories and music."
    return Ideas.model_validate(values)


class FakeGenerator:
    """Return canned ideas or failures while recording only test inputs."""

    def __init__(self, results: list[Ideas | IdeasUnavailable]) -> None:
        """Set the finite sequence of provider outcomes."""
        self.results = results
        self.tasks: list[IdeaTask] = []

    async def generate(self, task: IdeaTask) -> Ideas:
        """Consume one canned outcome."""
        self.tasks.append(task)
        result = self.results.pop(0)
        if isinstance(result, IdeasUnavailable):
            raise result
        return result
