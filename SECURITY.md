# Security

## Current scope

Gatherly accepts untrusted event text, model output and client-held plans. It has
no accounts, database, payments, booking integrations or server-side plan files.
The browser frontend and deployment container are not implemented yet. This
document describes the controls present through Phase 3.

## Trust boundaries and controls

- Input models reject unknown fields, invalid enums, numeric coercion and out-of-
  range values. HTTP parsing preserves strict numbers while accepting JSON dates
  and arrays. Imported plans are checked against deterministic budget and vendor
  calculations and expected timeline identities.
- The server computes money, dates and checklists. Gemini receives delimited,
  escaped input as data and returns schema-constrained creative content only.
  Output is revalidated and sanitised before use. Failed generation receives one
  retry and then deterministic fallback. Prompt controls do not prove semantic
  truth; live ideas still require ordinary event-planning judgment.
- API bodies have a byte cap enforced on actual chunks, not just Content-Length.
  Compressed request bodies are rejected. A deadline includes upload, queueing
  and model work. LLM concurrency, retry count and output tokens are bounded.
- Fixed-window per-client limits use the ASGI peer address, held under a salted
  hash. Counter count is bounded, expired entries are pruned on access, and a
  full store rejects new clients instead of evicting active counters. Caches and
  counters are process-local; neither is a distributed denial-of-service defense.
- Same-origin access is permitted. Additional CORS origins must be exact URLs
  without credentials, wildcards or paths. Credentialed CORS is disabled. CORS is
  a browser policy, not authentication for this public API.
- Security headers apply to successful, validation and middleware error responses.
  Production CSP denies active content; development Swagger uses an exact hash
  for its bootstrap script. HSTS requires a server-recognized HTTPS connection.
- Markdown escapes user markup. Calendar values escape control delimiters and
  use UTF-8-safe line folding. Export filenames are fixed. JSON is an attachment
  with `nosniff` and must be treated as untrusted data when imported.

## Secrets and privacy

Set `GEMINI_API_KEY` in the deployer's environment or ignored local `.env` file.
Only `.env.example` belongs in Git. Settings exclude the key from representations
and serialization. Error responses omit raw input, unknown input key names,
provider messages and tracebacks. Application logs contain generated request IDs
and elapsed time only. `make run` disables access logs so URL text is not logged.

User text appears in the requested plan response and is sent to Gemini when a
key is configured. Successful creative results may contain that text and remain
in a bounded, process-local TTL cache. There is no persistent application storage
or analytics. Expired cache entries are inaccessible and removed on access or
capacity eviction. A production host must also configure its own access-log and
provider data-handling policies; application settings cannot control those logs.

## Deployment assumptions and remaining work

`make run` binds loopback and disables forwarded-header trust. Behind a proxy,
configure Uvicorn to trust only the actual proxy network; otherwise client IP
limits and HTTPS detection may be incorrect. Multiple workers have independent
rate counters and caches. Public deployment needs perimeter resource limits and
careful proxy configuration. Container and Cloud Run hardening are Phase 4.
Frontend output handling and accessibility are Phase 5.

`make check` runs strict types, tests and coverage, Ruff, Bandit, dependency
advisory checks and gitleaks. Hooks scan staged content and CI scans Git history.
No scanner or test suite guarantees absence of vulnerabilities.

## Reporting

A public repository and private reporting channel are not configured yet. Obtain
a private maintainer contact before sending sensitive vulnerability details;
do not post credentials or personal event data in a public issue. A useful
report includes the affected commit, reproduction steps using synthetic data,
observed impact and an expected safe behavior. A GitHub reporting channel will
be documented when the repository is published.
