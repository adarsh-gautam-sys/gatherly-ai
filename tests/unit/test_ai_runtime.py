"""Verify composition and SDK cleanup without using a real key or network."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from google.genai import types
from pydantic import SecretStr

from gatherly.config import Settings
from gatherly.domain.ideas import IdeasResponse
from gatherly.infra.runtime import plan_service
from tests.unit.ai_helpers import sample_ideas
from tests.unit.domain_helpers import event_request


def test_runtime_without_key_never_constructs_sdk_client() -> None:
    """Fallback composition is usable without provider credentials."""

    async def exercise() -> None:
        with patch("gatherly.infra.runtime.genai.Client") as factory:
            async with plan_service(Settings(gemini_api_key=SecretStr(""))) as planner:
                plan = await planner.create(event_request())
                assert plan.ai_status == "unavailable"
            factory.assert_not_called()

    asyncio.run(exercise())


@pytest.mark.parametrize("close_fails", [False, True])
def test_runtime_injects_timeouts_disables_sdk_retries_and_closes_clients(
    close_fails: bool,
) -> None:
    """Client ownership is explicit even when async shutdown raises an error."""

    async def exercise() -> None:
        with patch("gatherly.infra.runtime.genai.Client") as factory:
            client = factory.return_value
            client.aio.aclose = AsyncMock(
                side_effect=RuntimeError("close failed") if close_fails else None
            )
            client.aio.models.generate_content = AsyncMock(
                return_value=types.GenerateContentResponse(
                    candidates=[
                        types.Candidate(
                            finish_reason=types.FinishReason.STOP,
                            content=types.Content(
                                parts=[
                                    types.Part(
                                        text=IdeasResponse(
                                            in_scope=True, ideas=sample_ideas()
                                        ).model_dump_json()
                                    )
                                ]
                            ),
                        )
                    ]
                )
            )

            async def run() -> None:
                async with plan_service(
                    Settings(gemini_api_key=SecretStr("test"))
                ) as planner:
                    assert (
                        await planner.create(event_request())
                    ).ai_status == "available"

            if close_fails:
                with pytest.raises(RuntimeError, match="close failed"):
                    await run()
            else:
                await run()
            options = factory.call_args.kwargs["http_options"]
            assert options.timeout == 6000
            assert options.retry_options.attempts == 1
            assert factory.call_args.kwargs["vertexai"] is False
            client.aio.aclose.assert_awaited_once()
            client.close.assert_called_once()

    asyncio.run(exercise())
