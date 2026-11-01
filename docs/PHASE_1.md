# Phase 1: deterministic domain core

## Scope

Strict event, budget, milestone and vendor models; integer budget allocation;
backwards timelines; vendor checklists; immutable templates for wedding,
birthday and community events. No Gemini integration, planning API or frontend
is introduced in this phase. Ideas and full Plan schemas arrive with Phase 2.

The engines take validated values and return immutable values. They read no
files, environment variables, network services or system clock. The caller
supplies a date to `build_timeline(event, today)`; the later orchestration layer
will obtain that value from its injected clock adapter.

## Explicit planning policies

The PRD leaves numerical limits and adjustment policies open. Phase 1 chooses:

- Guests: 1 through 5,000. Budget: positive integer, strictly below
  1,000,000,000 minor units. Floats, booleans and numeric strings are rejected.
- Currency whitelist: INR, USD, EUR, GBP and JPY. Amounts are paise, cents,
  pence or yen as appropriate. No currency conversion or display formatting
  occurs in the domain.
- Event name and region: at most 120 characters. Preferences, dietary needs
  and interests: at most 500 each. Notes: at most 2,000. Names cannot be blank.
  Text is retained as data; sanitisation of generated output belongs to Phase 2.
- Structural validation and future-date validation are separate to avoid an
  ambient clock. Call `event.validate_future_date(today)` at intake;
  `build_timeline` also enforces it. Budget-only recalculation is date-independent.
- Baseline guest counts: wedding 100, birthday 25, community 100. At baseline
  with a sufficient budget, percentages exactly reproduce the PRD table.
- Food's percentage-point adjustment is
  `floor(base_food_percent * (guests - baseline_guests) / baseline_guests)`.
  A low per-guest budget adds five points to prioritise food. The final change
  is capped at plus or minus ten points. The 7% or 8% contingency share stays
  fixed; other categories share the remaining percentage proportionally.
- Both percentages and money use integer largest-remainder allocation, with
  ties broken in template order. Line percentages are target shares; tiny
  budgets cannot reproduce those percentages exactly in whole minor units.
  The contingency category is always present, but its amount can round to zero.
- `per_guest` is integer division, rounded down. Warning comparisons use the
  exact total against `threshold * guests`, avoiding rounding at the boundary.

Low-budget thresholds below are **heuristics per guest in minor units**, not
researched prices, exchange rates or claims about local affordability:

| Currency | Wedding | Birthday | Community |
| --- | ---: | ---: | ---: |
| INR | 200000 | 50000 | 20000 |
| USD | 5000 | 1500 | 500 |
| EUR | 4500 | 1500 | 500 |
| GBP | 4000 | 1200 | 400 |
| JPY | 6000 | 1800 | 600 |

## Dates, priorities and links

Standard lead times are 365, 42 and 84 days respectively. Tasks whose original
deadline is today or earlier become `due_now` today. Other offsets compress by
`floor(days_before * min(days_remaining, standard_lead) / standard_lead)`.
Long horizons retain the original offsets. Compression changes guidance, not
real vendor availability or permission requirements.

Milestones are chronological, with priority 1 before 2 before 3 on the same day
and stable template order for ties. Phase labels support grouping into
Foundations, Bookings, Details, Final Week and Event Day. No task is scheduled
after the event; this resolves the PRD's example "After" phase in favour of its
explicit timeline invariant. Fresh timelines emit `upcoming` or `due_now`;
the required `overdue` model state remains valid for later plan updates.

Each checklist entry includes questions, documents, lead time, priority,
initial `todo` status and its exact category allocation. The allocation is a
category budget, not a vendor quote. Community coordination roles cover permits,
volunteers, sound, first aid and insurance. No specific businesses are invented.
Each vendor category has a linked milestone at its stated booking lead time.

## Local domain example

After `make install`, run this with the virtualenv's Python:

```python
from datetime import date

from gatherly.domain.budget import build_budget
from gatherly.domain.models import EventRequest
from gatherly.domain.timeline import build_timeline
from gatherly.domain.vendors import build_vendors

event = EventRequest(
    type="birthday",
    name="A birthday",
    date=date(2028, 2, 22),
    guests=25,
    budget=100_000,
    currency="INR",
    dietary="Vegetarian",
)
today = date(2028, 2, 1)
event.validate_future_date(today)
budget = build_budget(event)
timeline = build_timeline(event, today)
vendors = build_vendors(event.type, budget)
assert sum(line.amount for line in budget.lines) == event.budget
```

## Verification

Pydantic v2 strict constraints, immutable values, JSON validation and model
validators were verified through Context7. The existing Pydantic 2.14.2 pin
is retained. Hypothesis APIs were verified through Context7 and its 6.170.14
release was verified on PyPI before pinning and installation.

- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Pydantic JSON validation](https://docs.pydantic.dev/latest/concepts/json/)
- [Hypothesis settings](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.settings)

The suite has 107 tests, including two reproducible Hypothesis properties with
300 examples each. Domain statement and branch coverage is 100%; `make test`
enforces this separately from the repository-wide 90% gate. Tests cover invalid
intake, tiny and maximum budgets, remainder ties, currency warning thresholds,
leap days, past dates, short horizons, date-range extremes, template links and
vendor allocations. An architecture check blocks I/O imports and clock reads
inside `domain/`.

Manual review: confirm that the currency whitelist, heuristic thresholds,
guest-count adjustments and booking guidance suit the intended demonstration.
Hosted CI remains unverified until a GitHub remote exists.
