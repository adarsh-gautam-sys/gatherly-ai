# Deployment

## Local container

Install Docker with a Linux engine and the Python development environment from
the README. Build and verify from the repository root:

```sh
make container-test
```

This builds `gatherly-ai:local`, starts a disposable container on a random
loopback port, checks health, UID/GID 10001, read-only writes and locked runtime
package versions, then sends 24 budget and 24 fallback-plan requests at concurrency
four. Any failed response, incorrect budget sum or p95 above two seconds fails.
The container is stopped on both success and verification failure. Docker must
remain available for cleanup; no other containers or images are removed.

To keep a local instance running:

```sh
make image
docker run --rm --read-only --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=128 --memory=512m --cpus=1 -p 127.0.0.1:8080:8080 gatherly-ai:local
```

Open `http://127.0.0.1:8080/health`. No API key is needed. The image uses a pinned
Python 3.12.16 slim-bookworm digest and a multi-stage build. Only the application,
prompts and runtime dependencies enter its virtualenv; test/build tooling stays
in the builder. Python bytecode writes are disabled. No writable volume is needed.
Both Docker and Cloud SDK upload contexts use explicit file allowlists.

For a development server started with `make run`, run `make load` in another
terminal. With the virtualenv Python, `python -m scripts.load_sanity --help` lists
bounded request/concurrency controls. Only loopback HTTP targets are accepted.
The default budget endpoint never calls Gemini. Selecting `--endpoint plans`
can call Gemini if that local server has a key. These are small sanity checks,
not production capacity or live-model latency measurements.

## Cloud Run prerequisites

Use a dedicated service and a Google Cloud project with billing enabled. Install
the current Google Cloud CLI and sign in with `gcloud auth login`. Source deploys
use Cloud Build and Artifact Registry; enable their APIs and the Cloud Run API.
An administrator must configure the deployer and build identity permissions:
Source Developer and Service Usage Consumer on the project, Service Account User
on the runtime identity, and Cloud Run Builder on the build identity. See the
[official source deployment guide](https://docs.cloud.google.com/run/docs/deploying-source-code).

Create a dedicated runtime service account with no broad project roles. Fallback
mode needs no application access to Google Cloud APIs. For Gemini, create a
Secret Manager secret separately and grant the runtime identity Secret Accessor
on that secret only. Use a numeric secret version; `latest` is rejected. Deployment
of secret configuration also requires appropriate service administration rights.
See the [official secrets guide](https://docs.cloud.google.com/run/docs/configuring/services/secrets).

The script does not create service accounts, grant project roles, enable APIs or
create secret values. It checks for an active CLI login before execution; IAM,
organization policies, billing and quotas are checked by Google Cloud at deploy
time. Local application-default credentials are not needed by this CLI workflow.

## Preview and deploy

Use the project virtualenv Python (`.venv/Scripts/python.exe` on Windows,
`.venv/bin/python` on Unix). Replace the sample project, region and identity:

```sh
python -m scripts.deploy --project sample-project --region asia-south1 --service-account gatherly-runtime@sample-project.iam.gserviceaccount.com
```

The default prints a JSON argument list and performs no cloud operation. To
deploy, append `--execute` to the reviewed command. Append `--secret gemini-key:1`
to enable Gemini through that existing secret version. Without `--secret`, the
deployment clears previous secret bindings and runs in fallback mode.

The script manages this service's environment and secret bindings as a whole;
redeploying replaces previously configured values. Use a dedicated service, or
review the generated `--set-env-vars` and secret flags before updating one.
It deploys the checked-in Dockerfile through `gcloud run deploy --source`.
Cloud Build, storage, container hosting and Gemini usage can incur charges.

Defaults: private invocation with IAM checks, one worker, 1 CPU, 512 MiB memory,
concurrency 16, minimum zero and maximum one instance, 20-second platform timeout,
and production documentation disabled. The app deadline remains 14 seconds and
Gemini concurrency remains four. Instance limits are scaling controls, not a
guaranteed spending cap. Set project budgets and provider quotas separately.

Public access requires the explicit `--public` option and permission to change
service invocation policy. Keep the default private until reviewing the proxy
and privacy constraints below. For private invocation use an identity with
Cloud Run Invoker permission and a bearer identity token for the service URL.
Never paste credentials into this repository or command examples.

## Proxy, filesystem and privacy constraints

Cloud Run terminates TLS and injects `PORT`; the container listens on all
interfaces at that port. The script sets `GATHERLY_EXTERNAL_HTTPS=true`, an
explicit deployment contract that enables HTTPS same-origin handling and HSTS.
Leave it false on plain local HTTP. Forwarded protocol/IP headers remain ignored,
so client input cannot spoof the rate-limit address.

**The rate limiter uses the immediate proxy peer on Cloud Run.** Users behind
that peer share its 60-request/minute bucket. This is conservative abuse control,
not independent per-public-client fairness. Multiple instances have independent
counters and caches. A public production launch needs trusted edge rate limiting
and a reviewed proxy-address policy before increasing instance limits.

Local Docker verification enforces `--read-only`. Cloud Run provides a writable,
memory-backed filesystem; the application makes no runtime file writes, but the
platform does not provide Docker's read-only flag. The non-root image still applies.
See the [container contract](https://docs.cloud.google.com/run/docs/container-contract).

Application request logs contain generated IDs and elapsed time. Uvicorn access
logging is disabled. Cloud Run's own request logs are separate: review retention,
access and URL/query handling before exposing the service. Event text belongs in
JSON request bodies, never URLs. The deployment script cannot disable every
platform/provider log or control Gemini's data-handling policy.

## Verify after deployment

Confirm authenticated `/health` returns status/version, `/docs` is unavailable,
responses carry HSTS, and a same-origin planning request succeeds. Without a
secret, confirm a complete plan with `ai_status: "unavailable"`; with the selected
secret version, run the optional synthetic live test and inspect creative output.
Check the runtime identity, resource limits and invocation policy in Cloud Run.
No live cloud deployment was performed during Phase 4.
