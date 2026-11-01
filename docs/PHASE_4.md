# Phase 4: Hardening

## Scope and exit criteria

Add a slim non-root Docker image, documented Cloud Run deployment script and a
bounded load sanity check. Retain clean strict typing, lint, tests and security
scans. CI runs those gates plus actual container verification. The frontend is
still Phase 5 and has not been started.

## Implementation and assumptions

- Multi-stage build pins the Python 3.12.16 base by digest and resolves runtime
  wheels under the existing dependency lock. No Python dependencies were added.
  Local tests use Python 3.12.13; both are within the required Python 3.12 series.
- Numeric UID/GID 10001, one Uvicorn worker, bounded connections and timeouts,
  platform `PORT`, no access logs or forwarded-header trust. Explicit managed-TLS
  configuration preserves HSTS and same-origin requests behind Cloud Run.
- Docker and Cloud SDK upload allowlists exclude local environments, tools,
  tests and secrets. The local Cloud SDK upload preview contained 43 files and
  no excluded environment/tool/test/script paths.
- Deploy defaults to private invocation and fallback mode, validates resource
  names, accepts only numeric Secret Manager versions, and previews before an
  explicit `--execute`. It sets resource limits and requires a runtime identity.
- Standard-library deployment/load helpers are included in strict mypy, Ruff,
  Bandit and aggregate coverage. Dependabot checks Python, Docker and Actions
  weekly. Build and runtime artifacts remain untracked.
- Bandit has narrow, documented exceptions for the required container bind
  address (B104), subprocess imports (B404), and validated argument-vector CLI
  calls without shell expansion (B603). No scanner is disabled globally.

The deliberate deployment limitation is shared proxy-peer rate limits on Cloud
Run instead of independent public-client counters. Forwarded client IPs are not
trusted. Cloud Run's filesystem is writable; read-only operation is verified in
local Docker. See [deployment instructions and constraints](DEPLOYMENT.md).

## Verification

- Final `make check` passed: Ruff, strict mypy (67 files), Bandit, pip-audit
  (no known vulnerabilities), and history/staged gitleaks scans (no leaks).
- Unit/API/security/property suite: 336 passed; one optional live Gemini test
  skipped. Overall statement/branch coverage including scripts: 98.92%; domain:
  100%. No credentials or provider calls were used by these tests.
- Real Docker test: UID/GID 10001, writes rejected on a read-only filesystem,
  no development tools in the runtime virtualenv, installed runtime packages
  match the lock, and health succeeds. Test container cleaned up afterward.
- Load sanity: 24 requests each to budget and fallback plans, four concurrent,
  zero failures. Final p95: 0.0258 seconds for budget and 0.0169 seconds for
  plans. These local measurements do not predict Cloud Run or live Gemini latency.
- Local deployment dry run and installed gcloud deploy flags verified; no cloud
  resources were created or modified. Docker Desktop's Linux engine was used.
- Hosted GitHub Actions remains unverified because there is no Git remote.
  The workflow contains the same checks run locally plus container verification.
  Live Cloud Run IAM/secrets/network behavior requires the documented manual pass.

## Documentation verification

Context7 was consulted for Docker multi-stage/non-root/read-only builds, Cloud
Run source deployment and TLS/PORT behavior, Uvicorn runtime options, pip wheel
constraints/isolated environments, and pytest fixtures. Existing verified pins
were retained. Official sources were also checked for
[Cloud SDK flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy),
[source deployment permissions](https://docs.cloud.google.com/run/docs/deploying-source-code),
[secret versions](https://docs.cloud.google.com/run/docs/configuring/services/secrets),
and [Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).

Official PromptWars submission size/branch/format rules remain unverified; no
official guide was located, and the user does not have its URL or text. Recheck
during Phase 6. The repository remains on `main` with no generated artifacts.
