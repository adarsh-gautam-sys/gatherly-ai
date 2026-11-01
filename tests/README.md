# Test strategy

Phase 0 tests use FastAPI's in-process TestClient and isolated environment/dotenv
configuration. They cover health output, package-version consistency, production
documentation restrictions, development configuration and settings validation.
No network calls or credentials are needed by the tests.

`make test` measures statements and branches across the complete `gatherly`
package. Coverage below 90% fails. `make check` also runs Ruff, strict mypy,
Bandit, dependency auditing and Git secret scans. Scanners require network access
for current advisories; tests do not. Stage intended changes before `make check`
so the staged secret scan includes new files.

Phase 1 adds strict model validation, independently calculated budget examples,
timeline boundary cases, vendor mapping and template consistency tests. Two
Hypothesis properties run 300 reproducible examples each across event types,
currencies, guest counts, integer budgets and calendar dates. They verify money
conservation, nonnegative allocations, checklist links and sorted bounded dates.

The domain receives the planning date explicitly. An AST architecture test
blocks I/O dependencies and direct system-clock calls. `make test` now applies
a separate 100% domain statement/branch coverage gate after the overall 90% gate.
The GitHub workflow uses the same Make target.

Phase 2 adds fake-LLM service tests for complete plans, cache reuse, retries,
timeout cancellation, budget-first refinement and fallback. The actual Google
SDK runs against HTTPX MockTransport to verify schema serialization, response
parsing, partial patches, safety blocks, provider errors and bounded retries.
Concurrency tests cover waiting-call cancellation and slot reuse. Runtime tests
verify explicit client cleanup, including shutdown failure.

Security tests put adversarial delimiters in every event free-text field and
refinement instructions. They verify escaped JSON boundaries, strict output
shapes, HTML/script/contact stripping, confidential-text and price rejection,
and valid links to budget categories. Configuration tests check bounds and
secret exclusion. Cache tests check LRU eviction and exact TTL expiry.

The optional `live` test uses synthetic data and real credentials only when
`GATHERLY_RUN_LIVE_TEST=1`; it is always skipped when `CI` is set. Run it with
`GEMINI_API_KEY` in the environment and `python -m pytest tests/live -m live --no-cov`
using the project virtualenv. It is excluded from normal offline verification.
Accessibility tests arrive with the Phase 5 frontend.
