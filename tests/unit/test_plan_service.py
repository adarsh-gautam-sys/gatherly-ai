"""Exercise orchestration with fake dependencies and no network access."""

import asyncio
from datetime import date

import pytest

from gatherly.domain.budget import build_budget
from gatherly.domain.fallback import fallback_ideas
from gatherly.domain.ideas import Ideas, Plan, Refinement
from gatherly.domain.models import EventType
from gatherly.infra.cache import MemoryIdeasCache
from gatherly.services.plan_service import PlanService
from gatherly.services.ports import IdeasUnavailable, IdeaTask
from tests.unit.ai_helpers import FakeGenerator, FixedClock, sample_ideas
from tests.unit.domain_helpers import event_request


def service(generator: FakeGenerator | None = None) -> PlanService:
    """Compose a service using a deterministic clock and isolated cache."""
    return PlanService(generator, MemoryIdeasCache(4, 30), FixedClock(), "test")


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_no_key_still_produces_complete_plan(event_type: EventType) -> None:
    """All event types work offline with internally consistent allocations."""
    event = event_request(event_type)
    plan = asyncio.run(service().create(event))
    assert plan.ai_status == "unavailable"
    assert plan.budget == build_budget(event)
    assert plan.ideas == fallback_ideas(event, plan.budget)
    assert plan.timeline and plan.vendors
    assert len(plan.ideas.themes) == 3
    assert Plan.model_validate_json(plan.model_dump_json()) == plan


def test_success_is_cached_and_changed_requests_miss() -> None:
    """Identical requests reuse ideas; budget changes use a different key."""
    fake = FakeGenerator([sample_ideas(), sample_ideas()])
    planner = service(fake)

    async def exercise() -> None:
        first = await planner.create(event_request())
        again = await planner.create(event_request())
        changed = await planner.create(event_request(budget=900_000))
        assert first.ai_status == again.ai_status == changed.ai_status == "available"
        assert first.ideas == again.ideas == sample_ideas()

    asyncio.run(exercise())
    assert len(fake.tasks) == 2


def test_failure_retries_once_and_does_not_cache_fallback() -> None:
    """Transient provider failure cannot poison the success cache."""
    fake = FakeGenerator([IdeasUnavailable(), IdeasUnavailable(), sample_ideas()])
    planner = service(fake)

    async def exercise() -> None:
        assert (await planner.create(event_request())).ai_status == "unavailable"
        assert (await planner.create(event_request())).ai_status == "available"

    asyncio.run(exercise())
    assert len(fake.tasks) == 3


def test_retry_can_recover() -> None:
    """The second permitted call may return valid ideas."""
    fake = FakeGenerator([IdeasUnavailable(), sample_ideas()])
    assert asyncio.run(service(fake).create(event_request())).ai_status == "available"
    assert len(fake.tasks) == 2


def test_timeout_cancels_both_attempts_and_returns_full_fallback() -> None:
    """Hung providers cannot hold service requests indefinitely."""
    cancellations: list[bool] = []

    class HungGenerator:
        async def generate(self, task: IdeaTask) -> Ideas:
            try:
                await asyncio.Event().wait()
            finally:
                cancellations.append(True)
            raise AssertionError("Unreachable")

    planner = PlanService(
        HungGenerator(), MemoryIdeasCache(1, 10), FixedClock(), "test", 0.001
    )
    plan = asyncio.run(planner.create(event_request()))
    assert plan.ai_status == "unavailable"
    assert len(cancellations) == 2


def test_past_event_is_rejected_before_any_llm_call() -> None:
    """Input date validation precedes expensive provider calls."""
    fake = FakeGenerator([])
    with pytest.raises(ValueError):
        asyncio.run(service(fake).create(event_request(event_date=date(2027, 1, 1))))
    assert not fake.tasks


def test_refinement_recalculates_budget_and_preserves_user_statuses() -> None:
    """Explicit money changes are applied before asking for creative updates."""
    planner = service()
    original = asyncio.run(planner.create(event_request()))
    values = original.model_dump()
    values["vendors"][0]["status"] = "booked"
    original = Plan.model_validate(values)
    fake = FakeGenerator([original.ideas])
    change = Refinement(
        instruction="Reuse decorations", sections=("menu",), budget=800_000
    )
    refined = asyncio.run(service(fake).refine(original, change))
    assert refined.budget.total == refined.request.budget == 800_000
    assert fake.tasks[0].budget == refined.budget
    assert fake.tasks[0].sections == ("menu", "saving_tips")
    assert refined.vendors[0].status == "booked"
    assert refined.timeline == original.timeline
    assert refined.ideas.themes == original.ideas.themes


def test_refinement_fallback_only_replaces_requested_sections() -> None:
    """Failed refinement preserves unrelated previous creative content."""
    original = asyncio.run(
        service(FakeGenerator([sample_ideas()])).create(event_request())
    )
    refined = asyncio.run(
        service().refine(
            original, Refinement(instruction="Simpler menu", sections=("menu",))
        )
    )
    assert refined.ai_status == "unavailable"
    assert refined.ideas.concept_summary == sample_ideas().concept_summary
    assert refined.ideas.menu == fallback_ideas(original.request, original.budget).menu


def test_unsafe_previous_ideas_and_generated_secrets_fall_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Imported text and fresh output cross the same sanitisation boundary."""
    bad = Ideas.model_validate(sample_ideas().model_dump() | {"menu": ("USD 500",)})
    fake = FakeGenerator([bad, bad])
    original = asyncio.run(service(fake).create(event_request()))
    assert original.ai_status == "unavailable"
    altered = Plan.model_validate(original.model_dump() | {"ideas": bad})
    refined = asyncio.run(service().refine(altered, Refinement(instruction="Refresh")))
    assert "USD 500" not in refined.ideas.model_dump_json()
    assert "USD 500" not in caplog.text
