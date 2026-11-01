# Product

<!-- impeccable:product-schema 1 -->

Gatherly AI is a celebration and event planner for Google Virtual PromptWars
Challenge 5. [docs/PRD.md](docs/PRD.md) is the source of truth; this record captures
durable product context for design work and does not replace or expand the PRD.

## Platform

web

## Users

Wedding, birthday and community-event planners have **equal priority**, confirmed
by the user during Impeccable initialization. No audience is the default lead.

- Wedding planners need a backwards-calculated timeline and vendor checklist to
  manage bookings and avoid missed deadlines.
- Birthday planners, including parents with limited time and money, need useful
  theme ideas and a realistic budget split they can work through in one evening.
- Community organisers need planning support for permits, volunteers, sound,
  first aid and other event logistics.

Users plan one event at a time and supply rough figures. Keyboard and screen-reader
users, people using zoom, and people on low-end devices must be able to complete
the same tasks.

## Product Purpose

Turn event details into a coherent plan: an exact budget breakdown, timeline,
vendor checklist and personalised creative ideas. Help organisers decide what
to do, when to do it and how much to allocate without handling bookings for them.

Success means a complete plan in under 15 seconds, allocations that always sum
to the entered budget, a useful timeline even when the event is soon, and a flow
that remains usable when Gemini is unavailable. The latency is a product target,
not a verified claim about every deployment or live model request.

## Positioning

Deterministic code owns money, dates and checklists. Gemini supplies creative
ideas and refinement through schema-constrained responses. Deterministic
templates preserve a complete plan when creative generation fails. Explain this
division clearly without suggesting that AI calculates reliable prices or books
real vendors.

## Operating Context

The intended workflow is to enter an event type, name, future date, guest count,
budget and currency, then optionally add region, cultural/style preferences,
dietary needs, interests and special requests. Review the plan, adjust the budget,
track checklist progress and vendor status, refine creative sections, and export.

The server is stateless. The plan lives in the browser; there are no accounts,
database or multi-user collaboration. Export formats are Markdown, JSON and ICS;
a print stylesheet supplies the PDF use case. Do not imply account-based saving,
cross-device sync or persistence guarantees beyond the implemented browser flow.

The product is also evaluated as a small, inspectable challenge repository with
visible tests, security controls and documentation. Official submission size,
branch and format rules remain unverified; do not invent compliance claims.

## Capabilities and Constraints

- Support exactly three event types: `wedding`, `birthday` and `community`.
- Budgets use integer minor units, explain category allocations, always include
  contingency and offer instant deterministic what-if recalculation. Currency
  is for formatting, never exchange conversion or live pricing.
- Timelines count backwards from the event and compress with shorter lead time.
  Vendor entries connect allocations to questions, documents and booking guidance.
  Vendor statuses are `todo`, `contacted`, `booked` and `not_needed`.
- Ideas include three themes, menus, activities, personal touches, saving tips
  and a concept summary. Respect supplied dietary and cultural preferences.
  Never invent businesses, contact details, URLs or specific market prices.
- Refinement changes selected creative sections. Budget changes pass through
  deterministic code first; the existing API accepts an explicit integer budget.
- Clearly explain `ai_status: "unavailable"` while retaining the usable fallback
  plan. Do not present template ideas as successful live Gemini output.
- The frontend is prescribed: vanilla HTML, CSS and ES modules, no framework or
  build step, served with the FastAPI application. Target under 100 KB total
  frontend transfer; measure before claiming it. Backend uses Python 3.12 with
  injected services and infrastructure, and a pure domain layer.
- Treat user/model text as data. Render it using `textContent`, never unsafe HTML.
  Preserve strict validation, safe errors, request limits and privacy controls.
- No real booking, payments, accounts, native apps, image-generation product
  feature or additional event types. Stretch work waits until the PRD is complete.
- Work proceeds one PRD phase at a time. The user approved Phase 5 implementation
  in the Festival wayfinding direction. Phase 6 requires a separate approval.

## Brand Commitments

The product name is **Gatherly AI**. Use plain-language instructions, labels,
errors and fallback explanations. The user selected Festival wayfinding for the
frontend; its implemented visual rules are recorded separately in DESIGN.md.

## Evidence on Hand

- [docs/PRD.md](docs/PRD.md): personas, requirements, accessibility criteria and
  phase boundaries.
- [docs/API.md](docs/API.md): implemented routes, request/response contracts and
  deployment-related HTTP constraints.
- [docs/PHASE_4.md](docs/PHASE_4.md): recorded local verification evidence;
  [tests/README.md](tests/README.md): test strategy.
- [SECURITY.md](SECURITY.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): actual
  controls, deployment instructions and known limits.
- Backend planning and exports are implemented, with the Phase 5 browser flow.
  The interface uses an authored vector mark and no supplied photographic assets.
  No testimonials, customer adoption, live deployment proof or accessibility
  conformance results are available to use as claims.

## Product Principles

1. Keep money, dates and checklists correct and explainable.
2. Make the full planning journey equally useful for all three event types.
3. Preserve useful progress when creative generation is unavailable.
4. Minimise data collection and protect untrusted text at every boundary.
5. Complete the accessible core before adding breadth or decorative complexity.

## Accessibility & Inclusion

Target WCAG 2.2 AA. Use semantic landmarks, visible labels and hints, associated
field errors, a focused error summary, keyboard-operable controls and visible
focus. Announce loading, success and fallback states with appropriate live regions.
Use native checkboxes for checklists and accessible tabular budget information.

Meet contrast ratios of 4.5:1 for text and 3:1 for UI components; do not communicate
meaning with colour alone. Support 200% zoom, 320 px widths, touch targets of at
least 44 px, reduced motion and preferred colour schemes. Include print styling.

Phase 5 exit criteria are zero axe-core violations, Lighthouse accessibility 100
and best practices at least 95, plus a successful keyboard-only walkthrough.
The PRD also requires documented screen-reader verification. These are targets
to verify against the completed interface, not current conformance claims.
