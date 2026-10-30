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

Property, service, security and accessibility suites arrive with their features
in subsequent PRD phases.
