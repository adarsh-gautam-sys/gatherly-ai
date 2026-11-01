"""Small loopback-only HTTP load check with synthetic events and latency gates."""

import argparse
import http.client
import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from statistics import median
from time import perf_counter
from urllib.parse import urlsplit

MAX_REQUESTS = 500
MAX_CONCURRENCY = 32
REQUEST_TIMEOUT = 15
RESPONSE_LIMIT = 1_048_576
P95 = 0.95


def target(url: str) -> tuple[str, int]:
    """Restrict load traffic to a local HTTP server with no credentials or paths."""
    parts = urlsplit(url)
    if (
        parts.scheme != "http"
        or parts.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parts.username
        or parts.password
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Load checks accept a loopback HTTP origin only.")
    return parts.hostname, parts.port or 80


def event_payload() -> bytes:
    """Use synthetic, bounded input without any user event information."""
    return json.dumps(
        {
            "type": "birthday",
            "name": "Load check",
            "date": str(datetime.now(UTC).date() + timedelta(days=90)),
            "guests": 25,
            "budget": 100_000,
            "currency": "INR",
        }
    ).encode()


def one_request(
    host: str, port: int, endpoint: str, payload: bytes
) -> tuple[float, bool]:
    """Measure one request and verify money conservation without recording its body."""
    started = perf_counter()
    connection = http.client.HTTPConnection(host, port, timeout=REQUEST_TIMEOUT)
    try:
        path = "/api/v1/plans" + ("/budget" if endpoint == "budget" else "")
        connection.request("POST", path, payload, {"Content-Type": "application/json"})
        response = connection.getresponse()
        data = json.loads(response.read(RESPONSE_LIMIT))
        budget = data if endpoint == "budget" else data["budget"]
        valid = (
            response.status == 200
            and budget["total"] == 100_000
            and (sum(line["amount"] for line in budget["lines"]) == budget["total"])
        )
        return perf_counter() - started, valid
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        return perf_counter() - started, False
    finally:
        connection.close()


def run_load(
    url: str,
    requests: int = 24,
    concurrency: int = 4,
    endpoint: str = "budget",
) -> dict[str, int | float | str]:
    """Run a bounded batch and return aggregate metrics without response content."""
    host, port = target(url)
    if not 1 <= requests <= MAX_REQUESTS or not 1 <= concurrency <= MAX_CONCURRENCY:
        raise ValueError("Requests or concurrency exceed the supported bounds.")
    if endpoint not in {"budget", "plans"}:
        raise ValueError("Choose budget or plans.")
    payload = event_payload()
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=min(requests, concurrency)) as pool:
        results = list(
            pool.map(
                lambda _: one_request(host, port, endpoint, payload), range(requests)
            )
        )
    elapsed = perf_counter() - started
    timings = sorted(item[0] for item in results)
    return {
        "endpoint": endpoint,
        "requests": requests,
        "concurrency": concurrency,
        "failures": sum(not item[1] for item in results),
        "p50_seconds": round(median(timings), 4),
        "p95_seconds": round(timings[math.ceil(P95 * requests) - 1], 4),
        "requests_per_second": round(requests / elapsed, 2),
    }


def main(argv: list[str] | None = None) -> int:
    """Fail the check on errors or latency above the selected sanity threshold."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=24)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--endpoint", choices=("budget", "plans"), default="budget")
    parser.add_argument("--max-p95-seconds", type=float, default=2)
    options = parser.parse_args(argv)
    if not 0 < options.max_p95_seconds <= REQUEST_TIMEOUT:
        parser.error("Latency threshold must be positive and at most 15 seconds.")
    try:
        report = run_load(
            options.url, options.requests, options.concurrency, options.endpoint
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True))
    return int(
        report["failures"] != 0
        or float(report["p95_seconds"]) > options.max_p95_seconds
    )


if __name__ == "__main__":
    raise SystemExit(main())
