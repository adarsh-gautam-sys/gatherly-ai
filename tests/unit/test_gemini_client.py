"""Run the real SDK against an offline transport, including schema conversion."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from google import genai
from google.genai import types

from gatherly.domain.ideas import IdeasPatch, IdeasResponse, RefinementResponse
from gatherly.infra.cache import MemoryIdeasCache
from gatherly.infra.gemini_client import GeminiIdeasGenerator
from gatherly.infra.prompts import load_prompts
from gatherly.services.plan_service import PlanService
from gatherly.services.ports import IdeasUnavailable, IdeaTask
from tests.unit.ai_helpers import FixedClock, idea_task, sample_ideas


def provider_body(text: str) -> dict[str, object]:
    """Wrap canned JSON in the actual provider response envelope."""
    return {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {"parts": [{"text": text}]},
            }
        ]
    }


@asynccontextmanager
async def offline_generator(
    body: dict[str, object], requests: list[httpx.Request], status: int = 200
) -> AsyncIterator[GeminiIdeasGenerator]:
    """Inject a transport that cannot open a real network connection."""

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client = genai.Client(
            api_key="test",
            vertexai=False,
            http_options=types.HttpOptions(
                httpx_async_client=transport,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        try:
            yield GeminiIdeasGenerator(
                client, "gemini-3.5-flash-lite", load_prompts(), 1
            )
        finally:
            await client.aio.aclose()
            client.close()


def test_real_sdk_serialises_schema_and_safety_settings() -> None:
    """A valid response is accepted through the actual SDK request path."""
    requests: list[httpx.Request] = []
    body = provider_body(
        IdeasResponse(in_scope=True, ideas=sample_ideas()).model_dump_json()
    )

    async def exercise() -> None:
        async with offline_generator(body, requests) as generator:
            assert await generator.generate(idea_task()) == sample_ideas()

    asyncio.run(exercise())
    assert len(requests) == 1
    sent = json.loads(requests[0].content)
    config = sent["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseSchema"]["properties"]["ideas"]
    assert config["maxOutputTokens"] == 3072
    assert config["temperature"] == 0.6
    assert len(sent["safetySettings"]) == 4
    assert all(
        s["threshold"] == "BLOCK_MEDIUM_AND_ABOVE" for s in sent["safetySettings"]
    )
    assert "GATHERLY_POLICY_V1" in json.dumps(sent["systemInstruction"])
    assert ":generateContent" in str(requests[0].url)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "{}",
        "",
        '{"in_scope":false,"ideas":null}',
        '{"in_scope":true,"ideas":null}',
        "x" * 32_001,
    ],
)
def test_invalid_json_empty_refusal_and_oversized_output_fail_closed(text: str) -> None:
    """Provider output never bypasses strict response validation."""

    async def exercise() -> None:
        async with offline_generator(provider_body(text), []) as generator:
            with pytest.raises(IdeasUnavailable):
                await generator.generate(idea_task())

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"candidates": [{"finishReason": "SAFETY"}]},
        {"candidates": [{"finishReason": "STOP"}]},
        {"candidates": [{"finishReason": "STOP", "content": {}}]},
        {"candidates": [{"finishReason": "MAX_TOKENS"}]},
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [{"text": "private reasoning", "thought": True}]
                    },
                }
            ]
        },
    ],
)
def test_blocked_or_incomplete_responses_are_unavailable(
    body: dict[str, object],
) -> None:
    """A truncated or safety-blocked candidate is never treated as a complete plan."""

    async def exercise() -> None:
        async with offline_generator(body, []) as generator:
            with pytest.raises(IdeasUnavailable):
                await generator.generate(idea_task())

    asyncio.run(exercise())


def test_provider_error_has_no_internal_retry_or_payload_disclosure() -> None:
    """The service owns retries and provider error text is not propagated."""
    requests: list[httpx.Request] = []
    body: dict[str, object] = {
        "error": {"code": 503, "message": "private input", "status": "UNAVAILABLE"}
    }

    async def exercise() -> None:
        async with offline_generator(body, requests, 503) as generator:
            with pytest.raises(IdeasUnavailable) as failure:
                await generator.generate(idea_task())
            assert "private input" not in str(failure.value)

    asyncio.run(exercise())
    assert len(requests) == 1


@pytest.mark.parametrize("valid", [True, False])
def test_partial_refinement_enforces_exact_requested_sections(valid: bool) -> None:
    """A refinement may not quietly overwrite unrelated sections."""
    patch = IdeasPatch(menu=("Seasonal vegetarian dishes",))
    if not valid:
        patch = IdeasPatch(menu=("Seasonal dishes",), activities=("Changed activity",))
    body = provider_body(
        RefinementResponse(in_scope=True, changes=patch).model_dump_json()
    )
    task = IdeaTask.model_validate(
        idea_task().model_dump() | {"current": sample_ideas(), "sections": ("menu",)}
    )
    requests: list[httpx.Request] = []

    async def exercise() -> None:
        async with offline_generator(body, requests) as generator:
            if valid:
                result = await generator.generate(task)
                assert result.menu == patch.menu
                assert result.themes == sample_ideas().themes
            else:
                with pytest.raises(IdeasUnavailable):
                    await generator.generate(task)

    asyncio.run(exercise())
    sent = json.loads(requests[0].content)
    assert sent["generationConfig"]["temperature"] == 0.2
    assert "GATHERLY_REFINEMENT_V1" in json.dumps(sent["systemInstruction"])


def test_out_of_scope_refinement_is_unavailable() -> None:
    """Refusal remains explicit during refinement as well as generation."""
    body = provider_body(
        RefinementResponse(in_scope=False, changes=None).model_dump_json()
    )
    task = IdeaTask.model_validate(
        idea_task().model_dump() | {"current": sample_ideas()}
    )

    async def exercise() -> None:
        async with offline_generator(body, []) as generator:
            with pytest.raises(IdeasUnavailable):
                await generator.generate(task)

    asyncio.run(exercise())


def test_invalid_json_retries_once_then_returns_complete_service_fallback() -> None:
    """The real adapter and service agree on validation failure semantics."""
    requests: list[httpx.Request] = []

    async def exercise() -> None:
        async with offline_generator(provider_body("bad json"), requests) as generator:
            service = PlanService(
                generator, MemoryIdeasCache(1, 10), FixedClock(), "test"
            )
            plan = await service.create(idea_task().event)
            assert plan.ai_status == "unavailable"
            assert plan.budget.total == idea_task().event.budget
            assert plan.timeline and plan.vendors and plan.ideas

    asyncio.run(exercise())
    assert len(requests) == 2


def test_concurrency_is_bounded_and_cancelled_waiters_release_cleanly() -> None:
    """A queued request cannot bypass slots, and cancellation leaves no deadlock."""
    response = types.GenerateContentResponse.model_validate(
        provider_body(
            IdeasResponse(in_scope=True, ideas=sample_ideas()).model_dump_json()
        )
    )

    async def exercise() -> None:
        entered = asyncio.Event()
        release = asyncio.Event()

        async def delayed_response(**kwargs: object) -> types.GenerateContentResponse:
            entered.set()
            await release.wait()
            return response

        with patch("google.genai.Client") as factory:
            client = factory.return_value
            client.aio.models.generate_content = AsyncMock(side_effect=delayed_response)
            generator = GeminiIdeasGenerator(
                client, "gemini-3.5-flash-lite", load_prompts(), 1
            )
            first = asyncio.create_task(generator.generate(idea_task()))
            await entered.wait()
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(generator.generate(idea_task()), timeout=0.001)
            assert client.aio.models.generate_content.await_count == 1
            release.set()
            assert await first == sample_ideas()
            assert await generator.generate(idea_task()) == sample_ideas()
            assert client.aio.models.generate_content.await_count == 2

    asyncio.run(exercise())


def test_network_timeout_is_translated_without_exposing_provider_details() -> None:
    """Transport failures use the same bounded fallback contract as API errors."""

    async def exercise() -> None:
        with patch("google.genai.Client") as factory:
            client = factory.return_value
            client.aio.models.generate_content = AsyncMock(
                side_effect=httpx.ReadTimeout("private payload")
            )
            generator = GeminiIdeasGenerator(
                client, "gemini-3.5-flash-lite", load_prompts(), 1
            )
            with pytest.raises(IdeasUnavailable) as error:
                await generator.generate(idea_task())
            assert not str(error.value)

    asyncio.run(exercise())
