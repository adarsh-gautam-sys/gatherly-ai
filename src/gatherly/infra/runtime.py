"""Compose and close the SDK and service adapters without changing HTTP routes."""

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from google import genai
from google.genai import types

from gatherly.config import Settings
from gatherly.infra.cache import MemoryIdeasCache
from gatherly.infra.clock import SystemClock
from gatherly.infra.gemini_client import GeminiIdeasGenerator
from gatherly.infra.prompts import load_prompts
from gatherly.services.plan_service import PlanService

MILLISECONDS_PER_SECOND = 1000
MIN_POLICY_LINE_LENGTH = 24


@asynccontextmanager
async def plan_service(settings: Settings) -> AsyncIterator[PlanService]:
    """Build a process-scoped service, using fallback without an API key."""
    prompts = load_prompts()
    key = settings.gemini_api_key.get_secret_value()
    client = (
        genai.Client(
            api_key=key,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=settings.ai_timeout_seconds * MILLISECONDS_PER_SECOND,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        if key
        else None
    )
    generator = (
        GeminiIdeasGenerator(
            client, settings.gemini_model, prompts, settings.ai_concurrency
        )
        if client
        else None
    )
    policy_digest = hashlib.sha256(
        (prompts.system + prompts.refinement).encode()
    ).hexdigest()
    forbidden = (key,) + tuple(
        line
        for line in (prompts.system + "\n" + prompts.refinement).splitlines()
        if len(line) >= MIN_POLICY_LINE_LENGTH
    )
    service = PlanService(
        generator,
        MemoryIdeasCache(settings.cache_capacity, settings.cache_ttl_seconds),
        SystemClock(),
        settings.gemini_model + policy_digest,
        timeout_seconds=settings.ai_timeout_seconds,
        forbidden=forbidden,
    )
    try:
        yield service
    finally:
        if client is not None:
            try:
                await client.aio.aclose()
            finally:
                client.close()
