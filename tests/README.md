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

Service, security and accessibility suites arrive with their features in later
PRD phases. No live Gemini test or frontend is added in Phase 1.
