# Gatherly API v1

Run `make run`. The local base URL is `http://127.0.0.1:8000`. Send uncompressed
`application/json` for request bodies. There are no accounts or stored plans;
the client retains the returned plan and submits it for refinement or export.

## Routes

| Method | Path | Request body | Success response |
| --- | --- | --- | --- |
| GET | `/health` | None | Status and package version |
| GET | `/api/v1/event-types` | None | Event types and baseline category percentages |
| POST | `/api/v1/plans` | `EventRequest` | Complete `Plan`, including AI availability |
| POST | `/api/v1/plans/budget` | `EventRequest` | Deterministic `BudgetPlan`; no AI |
| POST | `/api/v1/plans/ideas` | `EventRequest` | `ideas` and `ai_status`; bypasses cached generation |
| POST | `/api/v1/plans/refine` | `{"plan": Plan, "change": Refinement}` | Updated complete `Plan` |
| POST | `/api/v1/plans/export?format=md` | `Plan` | Markdown attachment; default format |
| POST | `/api/v1/plans/export?format=json` | `Plan` | Complete versioned JSON attachment |
| POST | `/api/v1/plans/export?format=ics` | `Plan` | All-day timeline calendar attachment |

Success responses use HTTP 200. No API key or personal information belongs in
URLs. Secrets are server-side settings; clients never supply a Gemini key.

## Create a plan

Example request body; choose a future date appropriate to your event:

```json
{
  "type": "birthday",
  "name": "A celebration",
  "date": "2099-06-01",
  "guests": 25,
  "budget": 100000,
  "currency": "INR",
  "region": "",
  "preferences": "Relaxed and outdoors",
  "dietary": "Vegetarian",
  "interests": "Music and board games",
  "notes": "Keep seating and routes accessible"
}
```

Save the body locally as `event.json` and send it, for example, with curl:

```sh
curl --fail-with-body --silent --show-error \
  http://127.0.0.1:8000/api/v1/plans \
  --header 'Content-Type: application/json' --data-binary @event.json \
  --output plan.json
```

On Windows, use `curl.exe` in one line or PowerShell's `Invoke-RestMethod` with
`-Method Post -ContentType application/json -InFile event.json`.

The response contains `request`, `budget`, `timeline`, `vendors`, `ideas`,
`ai_status`, `generated_at` and `schema_version`. Money remains integer minor
units: this example is INR 1,000.00. JSON dates use ISO `YYYY-MM-DD`; generated
timestamps have an explicit timezone. Arrays represent immutable domain tuples.
Strings such as `"25"`, booleans and floats do not substitute for integers.
Unknown fields and unsupported schema versions are rejected.

Without a key, or after two failed provider attempts, the result still contains
the complete deterministic plan and template ideas, with
`"ai_status": "unavailable"`. Provider failure alone does not cause HTTP 503.

## Budget, ideas and refinement

Budget recalculation accepts the same event body with a changed integer budget.
It never invokes the model, cache or system clock and also supports past event
dates when inspecting an archived plan. Creating plans or refreshing/refining
ideas requires a future date.

Creative refresh accepts the event body and returns only `ideas` and `ai_status`.
It bypasses an existing cached generation; successful new ideas replace the
cached value. The deterministic components remain client-side.

Refinement sends the complete saved plan and a change object. For example, the
`change` value can be:

```json
{
  "instruction": "Make the menu vegetarian and reuse decorations",
  "sections": ["menu", "themes"],
  "budget": 80000
}
```

Allowed sections are `concept_summary`, `themes`, `menu`, `activities`,
`personal_touches` and `saving_tips`. Omitted sections mean all creative sections.
An explicit budget is recomputed first and adds `saving_tips` to the requested
sections. Omit `budget` to keep the current total. Natural-language percentages
are not converted to money by the model; the caller supplies the final integer.
The selected-section contract from Phase 2 is unchanged.

Vendor statuses (`todo`, `contacted`, `booked`, `not_needed`) and unaffected
creative sections are preserved. Imported plans must contain the expected
milestone identities, consistent allocations and no milestone after the event.
These are consistency checks, not a signature proving the plan's provenance.

## Export and JSON import

```sh
curl --fail-with-body --silent --show-error \
  'http://127.0.0.1:8000/api/v1/plans/export?format=ics' \
  --header 'Content-Type: application/json' --data-binary @plan.json \
  --output gatherly-plan.ics
```

Exports never invoke AI. Filenames are fixed to `gatherly-plan.md`,
`gatherly-plan.json` or `gatherly-plan.ics`; event names do not enter headers.
Markdown escapes user-supplied markup and formats currency with integer
arithmetic. JSON preserves the plan exactly, including checklist state, for
loading locally or resubmitting to refinement/export; there is no persistence or
separate upload/import endpoint. Calendar exports use all-day events, stable
milestone UIDs, CRLF lines and UTF-8-safe folding. No calendar events are booked
or sent automatically.

## Errors and response headers

All errors use `code`, `message` and `details`. For example:

```json
{
  "code": "validation_error",
  "message": "Check the request fields.",
  "details": [{"field": "body.guests", "message": "This field is required."}]
}
```

| Status | Meaning |
| --- | --- |
| 400 | Invalid framing/header or malformed request rejected by the framework |
| 403 | Origin or preflight policy denied |
| 404 / 405 | Unknown route / unsupported method |
| 413 | Request body exceeds the configured cap |
| 415 | Unsupported media type or compressed body |
| 422 | Invalid JSON, fields, future date, schema version or plan consistency |
| 429 | API rate limit or counter capacity reached; includes `Retry-After` |
| 500 | Unexpected internal failure; no exception payload is returned |
| 503 | Runtime unavailable or total request deadline exceeded |

Responses carry a server-generated `X-Request-ID`, `Cache-Control: no-store`,
`X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` and CSP. HSTS is
added for server-recognized HTTPS or explicitly configured managed HTTPS ingress.
Application logs contain IDs and elapsed milliseconds only. Forwarded headers
are ignored by both `make run` and the container. Cloud Run limits requests by
proxy peer; see [deployment constraints](DEPLOYMENT.md).

## Settings

| Environment setting | Default | Accepted range or policy |
| --- | --- | --- |
| `GATHERLY_MAX_BODY_BYTES` | 262144 | 1024–1048576; measured on received bytes |
| `GATHERLY_REQUEST_TIMEOUT_SECONDS` | 14 | 1–14; includes body upload and downstream work |
| `GATHERLY_REQUESTS_PER_MINUTE` | 60 | 1–600; all `/api/` requests, including preflight |
| `GATHERLY_RATE_LIMIT_CAPACITY` | 4096 | 1–65536 active client counters |
| `GATHERLY_ALLOWED_ORIGINS` | `[]` | JSON list of at most ten exact HTTP(S) origins |
| `PORT` | 8080 | Container listener; integer 1024–65535 |
| `GATHERLY_EXTERNAL_HTTPS` | false | Enable only when ingress guarantees HTTPS |

Same-origin access is permitted without extra configuration. Cross-origin
credentials are never enabled. Preflight permits GET/POST and Content-Type/Accept
only. Active rate counters are never evicted to admit new clients; a full store
returns 429 until an entry expires. Health checks are not rate limited.

For local schema inspection, set `GATHERLY_ENVIRONMENT=development` and open
`/docs` or `/openapi.json`. `/redoc` redirects to the same Swagger interface.
The documentation script is allowed by an exact CSP hash; the API does not
permit arbitrary inline scripts. Production exposes none of these docs routes.
