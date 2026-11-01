"""Verify bounded local load checks detect HTTP and budget failures."""

import json
from unittest.mock import Mock, patch

import pytest

from scripts import load_sanity as load


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1",
        "http://example.com",
        "http://user@localhost",
        "http://localhost/path",
        "http://localhost?x=1",
        "http://localhost#x",
    ],
)
def test_load_cannot_target_a_remote_or_credentialed_service(url: str) -> None:
    """Traffic is restricted to an explicit loopback HTTP origin."""
    with pytest.raises(ValueError, match="loopback"):
        load.target(url)


@pytest.mark.parametrize(
    ("requests", "concurrency", "endpoint"),
    [(0, 1, "budget"), (501, 1, "budget"), (1, 33, "budget"), (1, 1, "other")],
)
def test_load_has_hard_resource_bounds(
    requests: int,
    concurrency: int,
    endpoint: str,
) -> None:
    """Invalid batches fail before opening a connection or starting threads."""
    with pytest.raises(ValueError):
        load.run_load("http://localhost", requests, concurrency, endpoint)


@pytest.mark.parametrize("endpoint", ["budget", "plans"])
@pytest.mark.parametrize("amount", [100_000, 99_999])
def test_load_verifies_budget_conservation(endpoint: str, amount: int) -> None:
    """A 200 response is insufficient when allocated money is inconsistent."""
    budget = {"total": 100_000, "lines": [{"amount": amount}]}
    body = budget if endpoint == "budget" else {"budget": budget}
    connection = Mock()
    connection.getresponse.return_value.status = 200
    connection.getresponse.return_value.read.return_value = json.dumps(body).encode()
    with patch(
        "scripts.load_sanity.http.client.HTTPConnection", return_value=connection
    ):
        elapsed, valid = load.one_request(
            "localhost", 8000, endpoint, load.event_payload()
        )
    assert elapsed >= 0
    assert valid == (amount == 100_000)
    connection.close.assert_called_once()


def test_connection_failure_is_counted_and_closed() -> None:
    """Network errors become failed observations and release the connection."""
    connection = Mock()
    connection.request.side_effect = OSError("unavailable")
    with patch(
        "scripts.load_sanity.http.client.HTTPConnection", return_value=connection
    ):
        assert load.one_request("localhost", 8000, "budget", b"{}")[1] is False
    connection.close.assert_called_once()


def test_batch_reports_aggregate_failures_without_bodies() -> None:
    """The batch preserves latency and failure information without response text."""
    with patch.object(load, "one_request", side_effect=[(0.1, True), (0.3, False)]):
        report = load.run_load("http://localhost:8000", requests=2, concurrency=1)
    assert report["failures"] == 1
    assert report["p50_seconds"] == 0.2
    assert report["p95_seconds"] == 0.3
    assert "Load check" not in json.dumps(report)


@pytest.mark.parametrize(
    ("failures", "latency", "status"), [(0, 0.1, 0), (1, 0.1, 1), (0, 3.0, 1)]
)
def test_cli_fails_on_errors_or_excessive_latency(
    failures: int,
    latency: float,
    status: int,
) -> None:
    """Both functional failures and slow responses fail the command."""
    with patch.object(
        load, "run_load", return_value={"failures": failures, "p95_seconds": latency}
    ):
        assert load.main([]) == status


@pytest.mark.parametrize(
    "args", [["--max-p95-seconds", "0"], ["--url", "http://example.com"]]
)
def test_cli_reports_invalid_load_options(args: list[str]) -> None:
    """Unsafe configuration exits through argparse before requests are sent."""
    with pytest.raises(SystemExit) as error:
        load.main(args)
    assert error.value.code == 2
