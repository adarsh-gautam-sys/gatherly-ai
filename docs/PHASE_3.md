# Phase 3: API layer and exports

## Scope and exit criteria

Implemented every PRD v1 route: event-type metadata, full plans, deterministic
budget recalculation, creative refresh, selected-section refinement, and
Markdown/JSON/ICS export. Added strict HTTP schemas, common error envelopes,
request admission limits, security headers, CORS and development OpenAPI docs.
The app lifespan owns the existing Gemini/cache/clock service and closes it on
shutdown. No frontend, container or deployment resources were added.

Exit criteria are passing API and security tests, correct OpenAPI and overall
coverage at or above 90%. Existing 100% domain coverage is retained.

## Decisions and assumptions

- The PRD permits a small in-house rate limiter. This implementation uses bounded
  per-client fixed windows, monotonic expiry and process-private salted IP hashes.
  Defaults are 60 requests/minute and 4,096 active counters. A full store rejects
  new clients rather than evicting counters that enforce existing limits.
- Request bodies default to 256 KiB. The ASGI guard counts received bytes, rejects
  compressed bodies and malformed/duplicate lengths, and includes upload time
  in the 14-second request deadline. Limits and origins are validated settings.
- JSON dates and arrays are validated with Pydantic's strict JSON semantics at
  the boundary. Integer strings, floats and booleans remain invalid money or
  guest counts. Domain models retain their strict immutable Python semantics.
- The existing Phase 2 refinement contract is unchanged: the caller supplies
  affected section names and any resulting integer budget. The model never
  computes percentage changes. Omitted sections request all creative sections.
- The ideas endpoint explicitly refreshes generation, bypassing cache lookup.
  Budget recalculation is date-independent and does not use the service or AI.
  Export also works without an active planner or provider connection.
- Imported plans retain user vendor statuses, but contradictory budgets, vendor
  allocations, missing/duplicate task identities and dates after the event are
  rejected. There is no plan signing or server-side persistence.
- Errors use `code`, `message`, `details` and safe field locations. Unknown input
  keys, input values, provider messages and exception text are omitted. Up to
  20 validation details are returned. Expected provider failures still yield
  HTTP 200 with fallback; an unavailable runtime or total deadline yields 503.
- Same-origin requests work by default. Additional origins use an explicit
  allowlist; credentialed CORS is disabled. HSTS is emitted only for HTTPS as
  identified by the ASGI server. Local `make run` now explicitly disables proxy
  header trust as well as access logging. Deployment proxy trust is Phase 4.
- `/docs` remains development-only. Its framework-generated bootstrap script is
  authorized with a CSP hash. `/redoc` now redirects to the same Swagger UI,
  keeping one secured documentation renderer. Production exposes neither UI
  nor the OpenAPI schema.
- Markdown escapes user markup; JSON preserves the complete versioned plan.
  Calendars use all-day VEVENTs, stable UIDs, UTC creation stamps, escaped property
  values and UTF-8-safe line folding. `DURATION:P1D` also supports the maximum
  representable event date without an overflowing end-date calculation.

The API shapes, examples, settings and status codes are documented in [API.md](API.md).
The implemented threat model and remaining deployment assumptions are in
[SECURITY.md](../SECURITY.md).

## Documentation and dependency verification

Context7 was consulted before implementation for FastAPI lifespan, exception
handlers, response contracts and documentation helpers; Pydantic before
validators and strict JSON parsing; pydantic-settings origin configuration;
Starlette ASGI middleware, headers and CORS behavior; and Uvicorn proxy trust.

Existing verified pins are retained: FastAPI 0.162.0, Pydantic 2.14.2,
pydantic-settings 2.16.2, Starlette 1.10.0, Uvicorn 0.54.0, pytest 9.2.0,
Ruff 0.17.3 and mypy 2.4.1. Starlette was already transitively installed and
locked; it is now also an explicit runtime dependency because the API uses its
public ASGI interfaces directly. No additional package is installed for rate
limiting, Markdown or calendars.

Primary references:

- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
  [error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/),
  [additional responses](https://fastapi.tiangolo.com/advanced/additional-responses/),
  and [custom documentation UI](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/).
- [Pydantic JSON parsing](https://docs.pydantic.dev/latest/concepts/json/) and
  [before validators](https://docs.pydantic.dev/latest/concepts/validators/).
- [Starlette 1.10 middleware](https://github.com/Kludex/starlette/blob/1.10.0/docs/middleware.md).
- [Uvicorn HTTP settings](https://www.uvicorn.org/settings/#http): verified
  `--no-proxy-headers` against the installed pinned CLI as well.
- [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545): calendar escaping,
  content-line folding, UID, DTSTART, DTSTAMP and all-day duration semantics.

## Verification

Final `make check`: **288 tests passed, one opt-in live test skipped**.
Overall statement/branch coverage is **99.48%**; domain coverage is **100%**.
Ruff lint/format, strict mypy, Bandit, dependency auditing and gitleaks pass.

Tests cover all routes, strict validation, every OpenAPI reference, safe errors,
runtime lifecycle, fallback, explicit ideas refresh and exports without AI.
Security tests cover real runtime secret filtering through HTTP, request/log
privacy, origin policy, per-client limits, forwarded-header spoofing, bounded
chunked uploads, disconnects and request cancellation. Export/import tests cover
currency precision, consistency checks, markup and calendar injection, Unicode
folding, stable UIDs and the maximum event date.

A temporary loopback Uvicorn server also passed real HTTP smoke checks for
health, OpenAPI, complete offline planning and JSON export. Changing forwarded
IP headers did not bypass the configured quota, and a forged forwarded HTTPS
header did not enable HSTS. The temporary server was stopped after verification.

## Manual checks and remaining limits

- Open `/docs` in development and try an example request in a real browser.
  Automated tests validate its CSP hash and OpenAPI, but no browser walkthrough
  has been performed in this phase.
- Open a Markdown download and import a synthetic ICS into the calendar client
  you intend to use, checking all-day dates and Unicode event names.
- The live Gemini smoke test remains opt-in and was skipped. Real creative
  quality and latency remain unverified without that manual test.
- Hosted CI has not run because no GitHub remote is configured. The workflow
  runs the same `make check` locally verified here.
- Official PromptWars submission rules remain unverified as recorded in Phase 0.
  The user has no official guide URL or text to provide.

Phase 4 starts only after explicit approval.
