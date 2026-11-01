# Phase 5: Accessible frontend

## Scope and exit criteria

Implement the PRD's intake, results tabs, task checkboxes, vendor progress,
deterministic budget what-if controls, idea refinement, exports and print view.
Exit gates are zero axe violations, Lighthouse accessibility 100 / best practices
at least 95, keyboard operation and the existing lint/type/coverage/security gates.
The frontend is vanilla HTML/CSS/ES modules with no build step. Phase 6 submission
work remains separate.

## Approved direction and implementation

The user selected Festival wayfinding, equal priority across event types, a
single grouped form with expandable preferences, and an overview led by upcoming
tasks and budget. The implementation uses warm paper, forest-green sign bands,
terracotta actions and amber notices, with standard accessible controls.

- Page and fixed public asset allowlist are served by FastAPI. The page permits
  only same-origin scripts/styles/API connections through CSP. Asset responses
  cache for one hour; the document and plans remain non-cacheable.
- User/model strings become DOM text nodes. No HTML parsing or model-selected
  styles are used. Theme colour codes are readable text rather than unchecked
  backgrounds. There are no remote fonts, runtime packages or binary assets.
- Money entry converts exact decimal strings to integer minor units with BigInt.
  Allocation remains on the deterministic endpoint. The slider and exact amount
  input both require an explicit Update budget action, avoiding requests for
  every pointer movement. Vendor allocations update and progress is preserved.
- Results render sections on demand. Ideas from the previous budget are labelled
  as potentially stale until an explicit creative refresh. Instructions never
  infer money changes; users change spending through the Budget tab.
- The current plan lives in browser memory only. JSON export/import preserves it;
  reload without an export loses the in-memory plan. Imported JSON is size-capped
  and validated by the existing export boundary before display.
- Added `Milestone.completed: bool = False`, preserving older imports and the
  existing date-status vocabulary. JSON and Markdown carry completion; the
  existing refinement service retains it. This small backend addition is needed
  for the PRD's checklist workflow and is covered by export/browser tests.
- Server errors, connection failures and deadlines preserve current state. A
  visible status and busy controls communicate progress. Editing creates a new
  plan only on successful generation; users can return to their existing plan.

## Verification and limitations

Browser coverage includes all three event types, exact minor-unit budget changes,
checked-task/vendor retention through refinement and JSON reopening, safe text
rendering, keyboard tab/checkbox operation, import errors, failed network updates,
all downloads and print-section visibility. Unit tests independently exercise
money parsing/formatting and deterministic response reconciliation.

Eight browser tests pass. Axe reports zero violations across tested states and
widths; Lighthouse initial-page accessibility and best practices both score 100.
The complete initial HTML/CSS/JS/SVG payload is approximately 52 KB before gzip,
enforced below 100 KB by an API test. Scans include the npm test-tool lock as well
as the existing Python lock and Git history/staged content.

See [ACCESSIBILITY.md](ACCESSIBILITY.md) for exact automated scope and pending
screen-reader/real zoom checks. Live Gemini, hosted CI and Cloud Run verification
remain unperformed. Tests use fallback mode; no event data or credentials were
sent to a model. Local design captures/reports/browser downloads are ignored.

Context7 verified FastAPI file serving, Playwright webServer/browser testing,
axe-core injection/rule tags, Lighthouse Node invocation and Prettier CLI.
Existing Python pins remain unchanged. Browser dev pins: Playwright 1.64.1,
axe-core 4.14.0, Lighthouse 13.5.0, chrome-launcher 1.2.2, Prettier 3.9.10.
Lighthouse 13.5.0 was selected over 13.6.0 because the latter's transitive test
dependencies had current advisories; the selected lock audits cleanly.
