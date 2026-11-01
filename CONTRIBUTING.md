# Contributing to Gatherly AI

Thank you for contributing to Gatherly AI! Gatherly AI is built with uncompromising standards for software engineering, mathematical rigor, security, and accessibility.

Please review these guidelines before submitting code.

---

## 1. Prerequisites & Environment Setup

* **Python:** 3.12 (strict requirement)
* **Node.js:** 22.19+ (for browser verification tooling only; no runtime node dependencies)
* **Build Tools:** GNU Make, Git
* **Secret Scanner:** [Gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1) on PATH (or at `.tools/gitleaks/gitleaks.exe` on Windows)

### Initial Setup
```sh
# Clone repository
git clone https://github.com/<your-org>/gatherly-ai.git
cd gatherly-ai

# Initialize virtual environment, locked dependencies, pre-commit hooks, and Playwright Chromium
make install
```

---

## 2. Development Workflow

All contributions must pass the automated gate check before committing:

```sh
# Run all linters, strict type checks, unit/property/browser tests, and security scans
make check
```

Individual checks available:
* `make lint`: Ruff check and formatting validation (`src/`, `tests/`, `scripts/`).
* `make typecheck`: Mypy strict mode verification on all 69+ source files.
* `make test`: Pytest with 90% overall coverage and 100% domain coverage gate.
* `make web-check`: Prettier check, Node model tests, Playwright browser suite, axe-core, and Lighthouse.
* `make scan`: Bandit AST security scan, `pip-audit`, `npm audit`, and Gitleaks secret scan.
* `make run`: Run the local development server at `http://127.0.0.1:8000/`.
* `make container-test`: Build and verify the read-only, non-root Docker container (requires Docker).

---

## 3. Engineering & Architectural Standards

### A. Architectural Boundaries
* **Pure Domain Core:** Code in `src/gatherly/domain/` must be 100% pure functions. Absolutely **no I/O, no network calls, and no system clock access**. Pass timestamps (e.g. `today`) as parameters from the caller.
* **Service Orchestration:** `src/gatherly/services/` orchestrates domain logic and infrastructure.
* **Injected Infrastructure:** External integrations (`gemini_client.py`, `cache.py`, `clock.py`) must be injected into services behind explicit Python `Protocol` interfaces.
* **Deterministic Fallback:** Gemini is used strictly for creative ideas and refinement. Money, dates, vendor tasks, and error handling must remain 100% deterministic.

### B. Typing & Style
* **Strict Mypy:** Code must typecheck with `--strict`. No untyped functions, no `Any` types without justification, and all collections must be typed.
* **Pydantic v2:** Use `ConfigDict(strict=True, frozen=True)` on domain models.
* **Integer Money:** All financial math must use integer minor units (pennies/cents) to prevent floating-point errors. Use Python `int` on backend, `BigInt` on frontend.
* **Documentation:** Docstrings are mandatory on all public classes, functions, and modules (Google style).
* **No Magic Numbers:** Define named constants with explanations.
* **No Dead Code:** Remove unused functions, imports, and variables.

### C. Security Principles
* **No Secrets:** Never commit API keys or credentials. Use `.env.example` as a template and ignore local `.env`.
* **Delimited Prompts:** Treat user input strictly as data inside delimited XML-style blocks.
* **Safe Errors:** Never leak stack traces, SQL errors, or user input in API error responses.
* **Zero User Data in Logs:** Logs record request IDs and timestamps only.

### D. Testing & Quality Gates
* **Coverage Bar:** Every feature must ship with tests in the same commit. Overall coverage must remain $\ge 90\%$; domain coverage must remain $100.00\%$.
* **Invariants:** Use `hypothesis` property-based tests for numerical and chronological invariants.
* **Accessibility Bar:** Frontend changes must report 0 violations in `axe-core` and maintain 100 in Lighthouse Accessibility.

---

## 4. Conventional Commits

We enforce the Conventional Commits specification:
* `feat:` A new feature or capability
* `fix:` A bug fix
* `test:` Adding or updating tests
* `docs:` Documentation additions or updates
* `chore:` Build scripts, dependency bumps, or tool configuration

Each commit should be small, self-contained, and pass `make check`.

---

## 5. Dependency Updates

Direct dependencies are pinned in `pyproject.toml`. Fully resolved locks are maintained in `requirements.txt` (Python) and `package-lock.json` (frontend dev tools).
To update dependencies:
1. Update version pin in `pyproject.toml`.
2. Re-resolve in a clean virtual environment and freeze to `requirements.txt`.
3. Verify that `pip-audit`, `npm audit`, and all test suites pass.
