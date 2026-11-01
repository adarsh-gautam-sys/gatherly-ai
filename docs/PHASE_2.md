# Phase 2: Gemini integration

## Scope and implementation

This phase adds strict creative schemas and complete plans, an injected
`IdeasGenerator` protocol, asynchronous Gemini adapter, versioned packaged
prompts, output sanitisation, bounded LRU/TTL cache and deterministic fallback.
`PlanService` assembles budgets, timelines and vendors before requesting ideas.
No planning HTTP routes or frontend are introduced.

The adapter requests JSON using a Pydantic response schema, independently parses
and validates the response, and rejects incomplete, blocked or out-of-scope
responses. All creative strings and list lengths are bounded. Exactly three
themes are required. Four safety categories use `BLOCK_MEDIUM_AND_ABOVE`.
Generation temperature is 0.6; refinement is 0.2; the output ceiling is 3,072
tokens. Automatic function calling is disabled; no tools or grounding are enabled.

The service allows two attempts total, separated by 0.2 seconds. The default
six-second timeout covers queue waiting and the provider call for each attempt;
SDK retries are disabled to avoid multiplying attempts. The theoretical wait
budget is 12.2 seconds plus local processing. Actual live latency remains to be
measured. Failures produce a complete plan with `ai_status="unavailable"`.

Successful sanitised ideas are cached using SHA-256 of canonical request JSON,
model name and prompt content digest. Raw request text is not retained as a cache
key. The process-local cache holds up to 128 entries for 300 seconds by default.
It stores creative text transiently, which may include personal details supplied
by a user; there is no persistent storage. Repeated cache reads do not extend TTL.
Expired entries are inaccessible and removed on access or capacity eviction.
Fallback results are not cached, allowing recovery on the next request.

## Decisions and assumptions

- Current default: `gemini-3.5-flash-lite`, configurable with `GEMINI_MODEL`.
  Google documents it as stable, low latency and cost effective, with structured
  outputs. The SDK is pinned to `google-genai==2.34.0` and all transitive packages
  are pinned in `requirements.txt`.
- `GEMINI_API_KEY` is excluded from settings representations and serialisation.
  An absent key constructs no SDK client and makes no model call.
- Settings bound timeout to 1–6 seconds, concurrency to 1–16, cache capacity to
  1–1,024 and TTL to 1–3,600 seconds. Defaults are in `.env.example`.
- Refinement takes an instruction, explicit affected section names and an optional
  integer budget override. The service recomputes money first and includes saving
  tips when the budget changes. The adapter accepts only the requested patch
  fields; unaffected ideas, timeline entries and vendor statuses are preserved.
  Natural-language numeric changes are not silently interpreted. A future API/UI
  caller must supply the validated resulting budget and affected sections.
- Prompt data is JSON-encoded and `<`, `>` and `&` are escaped inside a single
  untrusted-data boundary. Prior ideas are also untrusted. No user text is logged.
- Output sanitisation strips HTML, script/style contents, URLs, email addresses
  and phone numbers. It rejects currency prices, known secrets, policy markers,
  matching policy lines, empty results and unknown budget categories. Schema
  validation and prompts cannot prove semantic correctness: dietary suitability,
  invented business references and creative quality still need live review.
- Template menus recommend checking dietary requirements rather than guessing
  that a specific dish is safe. Out-of-scope responses use the same bounded
  retry/fallback path and unavailable flag as other provider failures.
- `infra.runtime.plan_service` owns the process-scoped dependencies and closes
  both async and sync SDK resources. Phase 3 will wire its lifetime into the app.

## Verified documentation

Context7 was consulted before implementation for the Python GenAI SDK,
Pydantic/settings APIs and HTTPX mock transport. Earlier phases verified the
existing pytest, Hypothesis, Ruff and mypy APIs and pins.

- [Official Python SDK](https://github.com/googleapis/python-genai): async
  `generate_content`, `GenerateContentConfig`, Pydantic response schemas,
  safety settings, `HttpOptions`, `HttpRetryOptions(attempts=1)` and client cleanup.
- [Pinned SDK release](https://pypi.org/project/google-genai/2.34.0/).
- [Official model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite),
  checked 2026-11-01: stable model identifier and structured-output capability.
- [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):
  environment aliases and typed settings.
- [HTTPX transports](https://www.python-httpx.org/advanced/transports/): offline
  `MockTransport` injected into the actual SDK client.

## Service example

Run with the project virtualenv after `make install`. Set `GEMINI_API_KEY` in
your environment to enable the provider, or leave it absent for fallback.

```python
import asyncio
from datetime import UTC, datetime, timedelta

from gatherly.config import Settings
from gatherly.domain.models import EventRequest
from gatherly.infra.runtime import plan_service


async def main() -> None:
    event = EventRequest(
        type="birthday",
        name="A celebration",
        date=datetime.now(UTC).date() + timedelta(days=30),
        guests=25,
        budget=100_000,
        currency="INR",
        dietary="Vegetarian",
    )
    async with plan_service(Settings()) as service:
        plan = await service.create(event)
        print(plan.ai_status, plan.budget.total, len(plan.ideas.themes))


asyncio.run(main())
```

## Validation and manual checks

`make check` passes: 174 tests passed, one optional live test skipped; overall
statement/branch coverage 99.67%, domain coverage 100%. Ruff, strict mypy,
Bandit, pip-audit and gitleaks pass. Tests exercise the real SDK with a fake HTTP
transport, so schema conversion and request configuration are covered offline.

The live test was not run because no API key is configured. With a key set in the
environment, enable `GATHERLY_RUN_LIVE_TEST=1` and run:

```sh
python -m pytest tests/live -m live --no-cov
```

Use `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on Unix. This is a
real, potentially billable API call. The test always skips in CI. Inspect live
ideas for dietary compatibility, grounded saving tips and absence of invented
businesses; measure latency for all three event types. Credentials must stay out
of Git and chat.

Hosted CI remains unverified because no GitHub remote is configured. Official
PromptWars submission rules remain unverified as recorded in Phase 0; no guide
URL or text has been supplied. Phase 3 begins only after explicit approval.
