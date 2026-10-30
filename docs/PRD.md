# Gatherly AI: Celebration & Event Planner

Product Requirements Document v1.0 · Google Virtual PromptWars, Challenge 5

## 1. Overview

**Vertical:** Celebration & Event Planning (weddings, birthdays, community events).

**One-liner:** Gatherly AI turns a few details (event type, date, guest count, budget, tastes) into a complete, realistic plan: a budget breakdown, a backwards-calculated timeline, a vendor checklist, and personalized ideas, with Gemini providing the creative layer and deterministic code providing the numbers.

**Core design principle:** *Deterministic code for anything that must be correct (money, dates, checklists); GenAI for anything that benefits from creativity (themes, menus, activities, personalization).* This one decision improves testability, security, efficiency and reliability at the same time, and it is the backbone of this PRD.

**Architecture principle:** The server is stateless. No database, no accounts, no stored personal data. The plan lives in the browser and can be exported.

## 2. Scoring Strategy

### 2.1 Rubric mapping

Tier assignments are inferred from the flag colours in the portal screenshot (green = High Impact, blue = Medium, grey = Low). Only the Code Quality tooltip is explicitly confirmed as High Impact, so verify the rest in the portal. The target is 100% on every criterion regardless of tier.

| Criterion | Likely tier | What a reviewer will look for | How we win it |
| --- | --- | --- | --- |
| Code Quality | High | Clear structure, naming, typing, small functions, separation of concerns | Layered architecture (api, services, domain, infra), strict typing, ruff and mypy clean, protocols and dependency injection, docstrings, no dead code |
| Problem Statement Alignment | High | Budgets, timelines, vendor checklists, personalized ideas for weddings, birthdays and community events | Each phrase of the problem statement is a first-class feature with its own module, endpoint, test and README section |
| Security | Medium | Secrets handling, input validation, injection defence, safe output rendering, rate limiting | See section 9.1 |
| Efficiency | Medium | Sensible resource use, caching, no wasteful calls, small footprint | See section 9.2 |
| Testing | Low | Real validation of functionality, visible test suite | 90%+ coverage enforced in CI, property-based tests, fake LLM client, security and accessibility tests |
| Accessibility | Low | Inclusive, usable UI | WCAG 2.2 AA target, axe-core and Lighthouse checks in CI |

### 2.2 Evaluator-oriented tactics

These are practical heuristics, not confirmed insider facts. Reviews of hackathon repositories are often partly automated or AI-assisted, so the repository must be easy to read quickly.

1. **Mirror the required README headings exactly:** Chosen Vertical, Approach and Logic, How the Solution Works, Assumptions. Add extra sections after these, not instead of them.
2. **Make the repo self-evidently complete:** public, default branch `main`, no committed secrets, no `node_modules`, no virtualenv, no large binaries. Keep the repo small. Check the official submission guide for size and branch limits before submitting.
3. **Show Google technology visibly:** Gemini through the official `google-genai` SDK, optional Cloud Run deployment with a one-command deploy script. This supports both alignment and the spirit of the event.
4. **Make quality provable:** CI badge, coverage badge, a `make check` command that runs lint, types, tests and security scans, and a short `ARCHITECTURE.md`.
5. **Keep a clean commit history:** one or more conventional commits per phase (`feat:`, `test:`, `docs:`, `chore:`). Reviewers read history as evidence of process.
6. **Polish beats breadth:** three event types done excellently outweigh ten done thinly. Resist scope creep and cut stretch goals before cutting tests.
7. **Graceful failure everywhere:** a plan must still be produced if Gemini is down. Reviewers test failure paths.
8. **Self-audit against the rubric before submitting** (section 15).

## 3. Goals and Non-Goals

### Goals

- G1: Generate a complete, coherent event plan in under 15 seconds from a short form.
- G2: Budget allocations always sum exactly to the user's total, with explainable rationale.
- G3: Timelines are realistic for the time remaining, and compress gracefully when the event is soon.
- G4: Ideas feel personal (culture, dietary needs, interests, vibe) and fit the budget.
- G5: Zero secrets leaked, zero stored personal data, hostile input handled safely.
- G6: Usable with keyboard, screen reader, zoom and low-end devices.

### Non-goals

- Real vendor booking, payments, or live vendor pricing.
- User accounts, databases, or multi-user collaboration.
- Native mobile apps.
- Image generation.

## 4. Personas and User Stories

**Priya, bride-to-be (wedding):** Overwhelmed by hundreds of tasks. *As a bride, I want a month-by-month timeline and a vendor checklist so I never miss a booking deadline.*

**Marcus, parent (birthday):** Limited time and budget. *As a parent, I want theme ideas and a budget split that fits 25 guests so I can plan in one evening.*

**Aisha, community volunteer (community event):** Needs permits, volunteers, safety. *As an organiser, I want a checklist covering permits, sound, first aid and volunteers so nothing is forgotten.*

**Cross-cutting stories**

- As any user, I can change my budget and instantly see the new allocation without waiting for AI.
- As any user, I can tick off checklist items and mark vendors as contacted or booked.
- As any user, I can ask the planner to refine the plan (for example: make it vegetarian, cheaper, outdoors).
- As any user, I can export my plan to Markdown, JSON, or calendar (ICS).
- As a screen-reader or keyboard-only user, I can complete every task without a mouse.

## 5. Functional Requirements

### FR-1 Event intake

Inputs: event type (`wedding`, `birthday`, `community`), event name, date, guest count, total budget, currency, optional city or region (free text), cultural or style preferences, dietary needs, interests, and a free-text 'special requests' field.

Validation: date in the future, guests 1 to 5000, budget greater than 0 and under a sane maximum, text fields length-capped, enums strictly validated. Errors are returned as structured, human-readable messages.

### FR-2 Budget engine (deterministic)

- Category percentage templates per event type (table below).
- Adjusts weights for guest count (catering scales per head) and for a per-guest sanity check. If budget per guest is below a threshold, the response includes a warning and a suggestion.
- Uses the largest-remainder method so allocated amounts are integers that sum exactly to the total.
- Includes a contingency category (about 7 to 8%) always.
- Each category includes a plain-language rationale.
- 'What-if' recalculation endpoint with no AI call.

| Wedding | % | Birthday | % | Community | % |
| --- | --- | --- | --- | --- | --- |
| Venue | 20 | Venue | 15 | Venue and permits | 20 |
| Catering | 30 | Food and cake | 35 | Food and refreshments | 25 |
| Photo and video | 10 | Decor | 12 | AV and sound | 12 |
| Decor and flowers | 10 | Entertainment and activities | 18 | Marketing and outreach | 10 |
| Attire and beauty | 10 | Invitations | 3 | Volunteers and logistics | 10 |
| Music and entertainment | 7 | Return gifts | 7 | Programming | 10 |
| Invitations and stationery | 2 | Photography | 3 | Safety, first aid, insurance | 5 |
| Transport and logistics | 3 | Contingency | 7 | Contingency | 8 |
| Contingency | 8 |  |  |  |  |

Each column sums to 100.

### FR-3 Timeline engine (deterministic)

- Milestones defined as 'days before event' per event type (wedding standard lead time about 12 months, birthday about 6 weeks, community about 12 weeks).
- Computed backwards from the event date using an injectable clock (testable).
- If time remaining is shorter than the standard lead time, milestones compress proportionally and tasks already past due are flagged 'do now' with priority order.
- Output is grouped into phases (for example: Foundations, Bookings, Details, Final Week, Event Day, After).
- Each milestone links to a budget category and a vendor type where relevant.

### FR-4 Vendor checklist (deterministic)

- Per event type, a list of vendor categories with: why it matters, questions to ask, documents to request, typical booking lead time, and priority.
- Each item has a status: `todo`, `contacted`, `booked`, `not_needed`.
- Each item maps to a budget category and shows its allocated amount.

### FR-5 Personalized ideas (Gemini)

Structured output containing: 3 theme options (with mood, colour palette, decor notes), menu suggestions respecting dietary needs, entertainment and activities, personal touches, 'save money' tips tied to the actual budget, and a short event concept summary.

Requirements: strictly schema-constrained JSON, grounded in the budget and guest count, never invents specific businesses, prices, phone numbers or URLs.

### FR-6 Plan refinement (Gemini)

User gives an instruction ('make it eco-friendly', 'we dropped the budget by 20%'). The server regenerates only the affected parts. Budget changes always go through the deterministic engine first.

### FR-7 Export

Markdown (human readable), JSON (round-trip import), and ICS (timeline milestones as calendar events). A print-friendly stylesheet covers the PDF use case without a PDF library.

### FR-8 Graceful degradation

If Gemini times out, errors, or returns invalid output after one retry, the API still returns the full deterministic plan with template-based ideas and a flag `ai_status: "unavailable"`. The UI explains this clearly.

## 6. AI Design

- **SDK:** official `google-genai` Python SDK.
- **Model:** configurable through `GEMINI_MODEL`. Default to a fast, low-cost Gemini Flash model. Verify the current model name in the official docs at the start of Phase 2 (use Context7 or the docs site) rather than trusting memory.
- **Structured output:** pass a Pydantic schema as the response schema; parse and re-validate server side. Reject anything that fails validation.
- **Prompt architecture:** a versioned system instruction stored in `prompts/` (plain text files, unit tested), plus a user message that contains trusted structured fields as JSON and untrusted free text inside clearly delimited blocks.
- **Prompt-injection posture:** the system instruction states that content inside the delimited block is data, never instructions. Output is schema-constrained, so an injected instruction cannot change the response shape. Output text is sanitised (strip HTML, drop URLs and email addresses, length caps).
- **Safety:** enable Gemini safety settings, refuse out-of-scope requests gracefully (this is an event planner, not a general chatbot), and never echo secrets or system prompts.
- **Determinism where possible:** low temperature for refinement, moderate for ideas, fixed token ceilings.
- **Testability:** the LLM is behind a `IdeasGenerator` protocol. Tests use a fake client with canned JSON. A tiny opt-in live test (env flag) exists for manual verification and is skipped in CI.

## 7. Architecture and Stack

```
Browser (vanilla HTML/CSS/ES modules, built last)
   |
   v
FastAPI app
   api/        routers, request and response schemas, error handlers, middleware
   services/   plan orchestration (combines engines + ideas + fallback)
   domain/     pure logic: budget, timeline, vendors, models (no I/O)
   infra/      Gemini adapter, cache, settings, clock
```

| Concern | Choice | Reason |
| --- | --- | --- |
| Language | Python 3.12 | Readable, strong typing tools, first-class Gemini SDK |
| Web | FastAPI + Uvicorn | Async, automatic validation, OpenAPI docs for free |
| Models | Pydantic v2 | Validation and LLM schema in one definition |
| Config | pydantic-settings | 12-factor env config, no secrets in code |
| Rate limiting | slowapi (or small in-house limiter) | Abuse protection |
| Tests | pytest, pytest-cov, hypothesis, httpx | Unit, property, API tests |
| Quality | ruff, mypy (strict), pre-commit | Enforced style and types |
| Security scans | bandit, pip-audit, gitleaks | Static, dependency and secret scanning |
| CI | GitHub Actions | Visible green badge |
| Deploy | Dockerfile (non-root, slim) and Cloud Run | One-command deploy |
| Frontend (Phase 5) | Vanilla HTML, CSS, ES modules, no build step | Tiny footprint, easiest to make accessible, fast |

## 8. Data Models (summary)

- `EventRequest`: type, name, date, guests, budget (integer, minor-unit safe), currency, region, preferences, dietary, interests, notes.
- `BudgetLine`: category, percent, amount, rationale.
- `BudgetPlan`: lines, total, per\_guest, warnings.
- `Milestone`: id, title, due\_date, phase, priority, status (`upcoming`, `due_now`, `overdue`), linked\_category.
- `VendorItem`: category, why, questions, documents, lead\_time\_days, priority, status, allocated\_amount.
- `Ideas`: concept\_summary, themes\[3\], menu\[\], activities\[\], personal\_touches\[\], saving\_tips\[\].
- `Plan`: request, budget, timeline, vendors, ideas, ai\_status, generated\_at, schema\_version.

Money is stored as integers (no floats) and formatted only at the edge.

## 9. API (v1)

| Method and path | Purpose | AI? |
| --- | --- | --- |
| GET `/health` | Liveness and version | No |
| GET `/api/v1/event-types` | Event types, default categories | No |
| POST `/api/v1/plans` | Full plan (budget + timeline + vendors + ideas) | Yes, with fallback |
| POST `/api/v1/plans/budget` | What-if budget recalculation | No |
| POST `/api/v1/plans/ideas` | Regenerate ideas only | Yes |
| POST `/api/v1/plans/refine` | Refine with an instruction | Yes |
| POST `/api/v1/plans/export?format=md\|json\|ics` | Export a plan | No |

Conventions: versioned path, consistent error envelope (`code`, `message`, `details`), correct status codes (422, 429, 503), OpenAPI docs enabled in dev only.

## 10. Non-Functional Requirements

### 10.1 Security

- **Secrets:** API key only from environment. `.env.example` committed, `.env` git-ignored, gitleaks in CI and pre-commit. Key never logged and never sent to the client.
- **Input validation:** strict Pydantic models, `extra="forbid"`, length and range caps, request body size limit, enum whitelists.
- **Prompt injection:** delimited untrusted input, schema-constrained output, output sanitisation, system-prompt confidentiality, tests with adversarial strings.
- **Output safety:** frontend uses `textContent` and never `innerHTML` with model output.
- **Transport and headers:** HSTS (behind HTTPS), strict Content-Security-Policy (no inline scripts), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, locked-down CORS.
- **Abuse control:** per-IP rate limiting, request timeouts, concurrency limit on LLM calls, bounded retries.
- **Privacy:** no persistence, no analytics, logs contain request IDs and timings only, never user free text.
- **Supply chain:** pinned dependencies (lockfile), `pip-audit` and Dependabot, minimal dependency set.
- **Container:** slim image, non-root user, read-only filesystem where possible.
- Add a `SECURITY.md` describing the threat model and reporting process.

### 10.2 Efficiency

- One structured Gemini call for the full plan (not one per section); refinement regenerates only what changed.
- Deterministic engines are O(n) pure functions with no network cost; budget what-if never touches the LLM.
- In-memory LRU cache keyed by a hash of the normalised request (with TTL) to avoid repeat LLM calls.
- Token ceilings, concise prompts, timeouts, and bounded retry with backoff.
- Async I/O, gzip responses, long-cache headers on static assets.
- Frontend: no framework, no build step, under 100 KB total transfer target, lazy-render long lists.
- Repo stays small (no binaries, no vendored dependencies).

### 10.3 Testing

- **Unit:** every budget, timeline and vendor rule, including edge cases (event tomorrow, huge guest count, tiny budget, leap day, past dates).
- **Property-based (hypothesis):** budget lines always sum to total, no negative amounts, milestones are sorted and never after the event date.
- **Service and contract:** orchestration with a fake LLM, fallback path when the LLM fails, invalid JSON, timeout, and empty output.
- **API:** FastAPI TestClient covering success, validation errors, rate limit, oversized body, and error envelope shape.
- **Security tests:** injection strings in every free-text field, HTML and script payloads, secret never present in responses or logs.
- **Accessibility tests:** axe-core run in CI against the rendered pages (Phase 5).
- **Gates:** coverage at or above 90% enforced in CI, tests run on every push, `make check` runs everything locally.
- Test names describe behaviour. Include a short `tests/README.md` explaining the strategy.

### 10.4 Accessibility (WCAG 2.2 AA target)

- Semantic landmarks (`header`, `nav`, `main`, `footer`), logical heading hierarchy, `lang` attribute, skip link.
- Every input has a visible label, hint text and programmatically associated errors; an error summary receives focus on failed submit.
- Full keyboard operability with visible focus indicators; no keyboard traps; logical tab order.
- Contrast at or above 4.5:1 for text and 3:1 for UI components; information never conveyed by colour alone.
- `aria-live` regions announce loading, success and AI-fallback status; busy states are exposed.
- Respect `prefers-reduced-motion` and `prefers-color-scheme`; layout works at 200% zoom and 320 px width; touch targets at least 44 px.
- Tables have captions and header scopes; checklists use native checkboxes.
- Plain-language copy, clear instructions, print stylesheet.
- Verification: axe-core in CI, Lighthouse accessibility score of 100 target, and a manual keyboard and screen-reader pass documented in `docs/ACCESSIBILITY.md`.

### 10.5 Code Quality

- Strict layering: `domain` has no imports from `api` or `infra`. Dependencies injected, LLM behind a protocol.
- Full type hints with mypy strict, ruff for lint and format, functions short and single-purpose, no magic numbers (templates live in data modules).
- Docstrings on public functions, meaningful names, no dead code or commented-out blocks.
- Central settings, central error types, structured logging.
- Docs: `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `CONTRIBUTING.md`, short ADRs for key decisions.

## 11. Repository Structure

```
gatherly-ai/
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── Dockerfile
├── pyproject.toml
├── .env.example
├── .github/workflows/ci.yml
├── docs/ (ACCESSIBILITY.md, adr/, api examples)
├── prompts/ (system and refinement prompts)
├── src/gatherly/
│   ├── main.py
│   ├── config.py
│   ├── api/ (routers, schemas, middleware, errors)
│   ├── services/ (plan_service.py, export_service.py)
│   ├── domain/ (models.py, budget.py, timeline.py, vendors.py, templates/)
│   ├── infra/ (gemini_client.py, cache.py, clock.py)
│   └── web/ (static frontend, built last)
└── tests/ (unit/, property/, api/, security/, a11y/)
```

## 12. Phased Roadmap

Each phase ends with a green `make check`, a commit, and the exit criteria below. Do not start the next phase until the current one passes.

| Phase | Scope | Exit criteria |
| --- | --- | --- |
| 0. Foundation | Repo, pyproject, ruff, mypy, pytest, pre-commit, Makefile, CI skeleton, `.env.example`, LICENSE, README skeleton, health endpoint | CI green on an empty-but-real app; `make check` works |
| 1. Domain core | Models, budget engine, timeline engine, vendor checklists, event templates | 100% coverage on domain; hypothesis properties pass; no I/O in domain |
| 2. Gemini integration | Settings, Gemini adapter, prompts, structured output, sanitisation, cache, fallback | Fake-LLM tests for success, bad JSON, timeout, injection; optional live test passes locally |
| 3. API layer | Routers, schemas, error envelope, rate limit, security headers, request limits, export (md, json, ics) | API tests green; OpenAPI correct; security tests green; coverage at or above 90% |
| 4. Hardening | bandit, pip-audit, gitleaks, mypy strict clean, Docker image, Cloud Run deploy script, load sanity check | All scanners clean in CI; container runs non-root; deploy documented |
| 5. Frontend | Accessible UI: intake form, results tabs, interactive checklists, what-if budget slider, refine box, export, print CSS | axe-core zero violations; Lighthouse accessibility 100, best practices 95 or above; keyboard-only walkthrough passes |
| 6. Docs and submission | README final, ARCHITECTURE, SECURITY, ACCESSIBILITY docs, screenshots, demo script, final self-audit | Checklist in section 15 fully ticked; public repo verified in a private browser window |

Stretch goals (only if everything above is complete): multi-language UI, dark theme polish, share via URL-encoded plan, additional event types (corporate, baby shower).

## 13. README Blueprint

Use these top-level headings in this order so reviewers find required items instantly:

1. Title, badges (CI, coverage), one-line pitch, screenshot or short GIF
2. **Chosen Vertical**
3. **Approach and Logic** (deterministic-versus-GenAI split, with a diagram)
4. **How the Solution Works** (architecture, request flow, endpoints, example request and response)
5. **Assumptions**
6. Features mapped to the problem statement (budgets, timelines, vendor checklists, personalized ideas)
7. Security, Efficiency, Testing, Accessibility (one short section each, linking to evidence)
8. Quick start (local, Docker, Cloud Run) and environment variables
9. Project structure, development commands, limitations and future work

## 14. Assumptions

- Users plan one event at a time and are comfortable entering rough figures.
- Budget is a single total; currency is user-selected and used for formatting only (no conversion).
- Percentage templates are reasonable general defaults, not guarantees of local pricing.
- Lead times are typical industry guidance and are adjusted when time is short.
- Regional or cultural customs are handled through user-provided preferences and AI suggestions, not hard-coded rules.
- The tool provides planning guidance, not legal, financial, or safety advice. Community events must verify local permit requirements with the relevant authority.
- The Gemini API key is supplied by the deployer through the environment; the app works in fallback mode without it.

## 15. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Gemini model or SDK names change | Model name is configurable; verify against current docs in Phase 2; pin SDK version |
| LLM returns invalid or off-topic output | Schema validation, one retry, deterministic fallback |
| Prompt injection through free text | Delimited data blocks, schema-constrained output, sanitisation, tests |
| Cost or abuse from public deployment | Rate limits, caching, token ceilings, concurrency cap |
| Scope creep hurts quality | Phase gates and exit criteria; stretch goals only at the end |
| Hidden submission rules (size, branch, format) | Read the official submission guide at Phase 0 and again at Phase 6 |

## 16. Final Submission Checklist

- [ ] Repo is public and opens in a private browser window
- [ ] Default branch is `main`, repo size is small, no secrets in history
- [ ] README has the four required sections with exact headings
- [ ] `make check` passes from a fresh clone using only the README instructions
- [ ] CI is green; coverage at or above 90%
- [ ] All scanners (ruff, mypy, bandit, pip-audit, gitleaks) clean
- [ ] Works with no API key (fallback) and with a key (full AI)
- [ ] axe-core zero violations; Lighthouse accessibility 100
- [ ] Keyboard-only and screen-reader walkthrough completed
- [ ] Each of budgets, timelines, vendor checklists, personalized ideas demonstrably works for wedding, birthday and community events
- [ ] Submission form filled with the repo link, then re-verified after submitting
