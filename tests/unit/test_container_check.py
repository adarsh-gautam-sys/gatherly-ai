"""Test disposable-container cleanup and runtime verification failures offline."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from scripts import check_container as container


def test_runtime_dependencies_must_match_lock() -> None:
    """Unknown packages and changed versions fail runtime verification."""
    container.verify_packages({"gatherly-ai": "0.1.0", "FastAPI": "0.162.0"})
    with pytest.raises(RuntimeError, match="differs from lock"):
        container.verify_packages({"unexpected": "1.0"})


@pytest.mark.parametrize("failure", ["none", "port", "packages", "load"])
def test_container_is_stopped_after_success_or_verification_failure(
    failure: str,
) -> None:
    """Every container created by the check is cleaned up, even on failure."""
    mapping = "0.0.0.0:1234" if failure == "port" else "127.0.0.1:1234"
    packages = {"unexpected": "1"} if failure == "packages" else {"FastAPI": "0.162.0"}
    replies = ["container-id", mapping, json.dumps(packages), "stopped"]
    if failure == "port":
        replies = ["container-id", mapping, "stopped"]
    report = {"failures": int(failure == "load"), "p95_seconds": 0.1}
    with (
        patch("scripts.check_container.shutil.which", return_value="docker"),
        patch.object(container, "docker", side_effect=replies) as docker,
        patch.object(container, "wait_ready"),
        patch.object(container, "run_load", return_value=report),
    ):
        if failure == "none":
            assert container.check_image("local:test") == [report, report]
        else:
            with pytest.raises(RuntimeError):
                container.check_image("local:test")
    assert docker.call_args.args == ("docker", "stop", "--time=5", "container-id")
    launch = docker.call_args_list[0].args
    assert "--read-only" in launch
    assert "--publish=127.0.0.1::8080" in launch
    assert "--env=GEMINI_API_KEY=" in launch


def test_container_check_requires_docker() -> None:
    """A missing Docker CLI produces an actionable preflight failure."""
    with patch("scripts.check_container.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="Install Docker"):
            container.check_image("local:test")


def test_docker_errors_are_not_ignored() -> None:
    """The CLI adapter requests checked execution without a shell."""
    with patch(
        "scripts.check_container.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout=" id\n"),
    ) as run:
        assert container.docker("docker", "run", "image") == "id"
    assert run.call_args.kwargs["check"] is True
    assert not run.call_args.kwargs.get("shell", False)


def test_health_retries_until_ready_and_closes_connections() -> None:
    """A transient startup failure is retried without leaking connections."""
    connection = Mock()
    connection.getresponse.side_effect = [
        OSError("starting"),
        Mock(status=200, read=Mock(return_value=b'{"status":"ok"}')),
    ]
    with (
        patch(
            "scripts.check_container.http.client.HTTPConnection",
            return_value=connection,
        ),
        patch.object(container, "sleep"),
    ):
        container.wait_ready(1234)
    assert connection.close.call_count == 2


def test_health_deadline_is_bounded() -> None:
    """An unready container cannot hang the check indefinitely."""
    with patch.object(container, "monotonic", side_effect=[0, 31]):
        with pytest.raises(RuntimeError, match="deadline"):
            container.wait_ready(1234)


def test_container_cli_reports_success_and_failure() -> None:
    """The command provides a reliable process status for CI."""
    with patch.object(container, "check_image", return_value=[]):
        assert container.main([]) == 0
    with patch.object(container, "check_image", side_effect=RuntimeError("failure")):
        assert container.main([]) == 1
    with pytest.raises(SystemExit) as error:
        container.main(["--image=--bad-flag"])
    assert error.value.code == 2
