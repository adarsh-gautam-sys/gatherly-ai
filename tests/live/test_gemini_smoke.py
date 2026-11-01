"""Optional manually enabled provider smoke test; never runs in CI."""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest

from gatherly.config import Settings
from gatherly.infra.runtime import plan_service
from tests.unit.domain_helpers import event_request


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("GATHERLY_RUN_LIVE_TEST") != "1" or bool(os.getenv("CI")),
    reason="Set GATHERLY_RUN_LIVE_TEST=1 and GEMINI_API_KEY locally; disabled in CI.",
)
def test_live_gemini_returns_valid_ideas() -> None:
    """Verify one synthetic request with configured credentials and model access."""
    settings = Settings()
    assert settings.gemini_api_key.get_secret_value(), (
        "Set GEMINI_API_KEY in the environment."
    )
    event = event_request(event_date=datetime.now(UTC).date() + timedelta(days=30))

    async def exercise() -> None:
        async with plan_service(settings) as planner:
            plan = await planner.create(event)
            assert plan.ai_status == "available"
            assert len(plan.ideas.themes) == 3
            assert sum(line.amount for line in plan.budget.lines) == event.budget

    asyncio.run(exercise())
