# Phase 0 foundation notes

Verification date: 30 October 2026 (Asia/Calcutta).

## Scope and exit criteria

PRD section 12: repository, dependency/configuration tooling, pre-commit,
Makefile, CI skeleton, example environment, MIT license, README skeleton and
health endpoint. Exit criteria: green `make check`, a conventional commit and
green CI on an empty-but-real app. Hosted CI requires a GitHub repository;
local success alone does not prove hosted CI is green.

The supplied root PRD is copied unchanged to `docs/PRD.md`. The original remains
locally available and is ignored to avoid maintaining two tracked copies.

## Submission guide check

The [official PromptWars Virtual page](https://promptwars.in/promptwarsVirtual.html)
requires project code, a live preview and a build-in-public narrative. Its FAQ
requires Google Antigravity; a separate section permits other AI tools. Confirm
the applicable Challenge 5 rule in the portal before submission.

The linked [challenge portal](https://vision.hack2skill.com/event/pwvirtual1/registration)
could not be retrieved. The accessible official page does not establish a
Challenge 5 repository-size or branch limit.

A [secondary Challenge 5 guide](https://saurabh1201.medium.com/promptwars-challenge-5-celebration-event-planner-problem-statement-rules-submission-6bd25d88fa63)
reports a public repository under 10 MB, deployed URL, demo video and LinkedIn
post. These details remain unverified against the official challenge guide.
Use one `main` branch and keep tracked files well below 10 MB as conservative
implementation choices, not as claims of verified official branch rules.
Recheck submission requirements in Phase 6.

## Dependencies and API verification

Context7 was queried before implementation for FastAPI, Pydantic v2,
pydantic-settings, Uvicorn, pytest, pytest-cov, HTTPX, Ruff, mypy, pre-commit,
Bandit, pip-audit and Hatchling configuration. Exact release versions and Python
compatibility were verified against each package's official PyPI metadata.

Primary documentation sources:

- [FastAPI application and documentation settings](https://fastapi.tiangolo.com/reference/fastapi/)
- [Pydantic model configuration](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Uvicorn settings](https://www.uvicorn.org/settings/)
- [pytest fixtures and monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
- [pytest-cov configuration](https://pytest-cov.readthedocs.io/en/latest/config.html)
- [HTTPX](https://www.python-httpx.org/)
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
- [mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html)
- [pre-commit](https://pre-commit.com/)
- [Bandit](https://bandit.readthedocs.io/)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Hatch packaging](https://hatch.pypa.io/latest/config/build/)
- [gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)

The exact direct pins are in `pyproject.toml`; the transitive lock manifest is
`requirements.txt`. A dependency lock is deliberately versioned as required by
PRD section 10.1; generated reports, builds and binaries are ignored.
Gemini SDK/model names, slowapi and Hypothesis will be verified when their
phases introduce them. No model name is guessed or configured in Phase 0.

## Phase interpretation

- Bandit, pip-audit and gitleaks are wired now because the standing workflow
  explicitly requires scans in `make check`. Deployment hardening remains Phase 4.
- Safe production defaults and development-only documentation follow PRD section 9.
- Settings live at `src/gatherly/config.py`, following section 11's concrete layout.
- Future module placeholders are empty packages, not unused implementation stubs.
- No hosted repository, deployment or submission is created by this phase.
- HTTPX2 2.16.0 replaces the PRD's HTTPX test dependency. Current Starlette
  deprecates HTTPX for TestClient; its supported replacement was verified with
  Context7 and PyPI. See the [upstream migration guide](https://github.com/pydantic/httpx2/blob/main/docs/migration.md).
  Tests still use FastAPI TestClient; warnings remain errors.

## Local validation

- Python 3.12.13; 19 tests pass; 100% application coverage (90% required).
- Ruff lint/format and strict mypy pass for source and tests.
- Bandit reports no findings; pip-audit reports no known vulnerabilities.
- gitleaks checks staged content and history with redacted reporting.
- `make install` and all pre-commit hooks pass.
- `make run` was smoke-tested over HTTP: `/health` returns 200 with
  `{"status":"ok","version":"0.1.0"}`; the test server was then stopped.
- The supplied PRD and canonical copy have identical SHA-256 hashes.
- Hosted GitHub Actions execution remains pending a configured remote.
