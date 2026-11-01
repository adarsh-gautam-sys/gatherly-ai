# Security

## Current scope

Gatherly accepts untrusted event text, model output and client-held plans. It has
no accounts, database, payments, booking integrations or server-side plan files.
The browser frontend is not implemented yet. This document describes the
controls present through Phase 4, including container and deployment tooling.

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
  for its bootstrap script. HSTS requires a server-recognized HTTPS connection
  or explicit managed-HTTPS configuration by the deployer.
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

`make run` binds loopback. The container binds all interfaces as required by
Cloud Run, runs as UID/GID 10001 and ignores forwarded headers. Its entry point
caps connections and timeouts and emits only the application's safe request logs.
Cloud Run deployment explicitly enables `GATHERLY_EXTERNAL_HTTPS` for HSTS and
same-origin handling behind its TLS ingress. This setting is inappropriate for
unprotected HTTP hosts.

Cloud Run requests share rate counters by immediate proxy peer; this does not
provide independent per-public-client quotas. Default deployment is private,
with bounded instances/concurrency. Public production use needs trusted edge
controls. Multiple workers or instances have independent counters and caches.
See [deployment constraints and verification](docs/DEPLOYMENT.md).

The pinned slim image has an isolated runtime virtualenv without development
tools. Local Docker verification uses a read-only filesystem, dropped capabilities
and no privilege escalation. Cloud Run has a writable memory-backed filesystem;
the application does not write event files. Upload/build allowlists exclude local
secrets. Gemini credentials can be injected from a pinned Secret Manager version
using a dedicated runtime identity. Frontend output handling is Phase 5.

`make check` runs strict types, tests and coverage, Ruff, Bandit, dependency
advisory checks and gitleaks. Hooks scan staged content and CI scans Git history.
CI also verifies the real container. Dependabot checks dependency, base image
and workflow updates weekly. Narrow Bandit exceptions cover required container
binding and validated CLI subprocess operations; see [Phase 4](docs/PHASE_4.md).
No scanner or test suite guarantees absence of vulnerabilities.

## Reporting

A public repository and private reporting channel are not configured yet. Obtain
a private maintainer contact before sending sensitive vulnerability details;
do not post credentials or personal event data in a public issue. A useful
report includes the affected commit, reproduction steps using synthetic data,
observed impact and an expected safe behavior. A GitHub reporting channel will
be documented when the repository is published.
