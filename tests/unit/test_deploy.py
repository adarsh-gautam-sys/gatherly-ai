"""Keep deployment explicit, bounded and free of embedded secret values."""

import json
import subprocess
from unittest.mock import patch

import pytest

from scripts import deploy

TARGET = [
    "--project",
    "sample-project",
    "--region",
    "asia-south1",
    "--service-account",
    "gatherly-runtime@sample-project.iam.gserviceaccount.com",
]


def test_preview_is_private_bounded_and_has_no_side_effects(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The default invocation only prints a command and clears previous secrets."""
    with patch("scripts.deploy.subprocess.run") as run:
        assert deploy.main(TARGET) == 0
        run.assert_not_called()
    command = json.loads(capsys.readouterr().out)
    assert "--no-allow-unauthenticated" in command
    assert "--invoker-iam-check" in command
    assert "--max-instances=1" in command
    assert "--concurrency=16" in command
    assert "--clear-secrets" in command
    assert (
        "--set-env-vars=GATHERLY_ENVIRONMENT=production,GATHERLY_EXTERNAL_HTTPS=true"
        in command
    )


def test_public_access_and_secret_version_require_explicit_options() -> None:
    """Only the Secret Manager resource reference is included in the command."""
    options = deploy.parser().parse_args(
        TARGET + ["--public", "--secret", "gemini-key:2"]
    )
    command = deploy.deployment_command(options)
    assert "--allow-unauthenticated" in command
    assert "--set-secrets=GEMINI_API_KEY=gemini-key:2" in command
    assert "--clear-secrets" not in command


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--project", "bad;command"),
        ("--region", "--flags"),
        ("--secret", "key:latest"),
        ("--secret", "raw-secret"),
        ("--service", "bad name"),
        ("--service-account", "user@example.com"),
    ],
)
def test_resource_arguments_reject_shell_syntax_and_unpinned_secrets(
    flag: str,
    value: str,
) -> None:
    """Invalid identifiers are rejected before a subprocess can be started."""
    with pytest.raises(SystemExit) as error:
        deploy.parser().parse_args([*TARGET, f"{flag}={value}"])
    assert error.value.code == 2


@pytest.mark.parametrize("account", ["", "active-account"])
def test_execution_requires_an_active_cli_login(account: str) -> None:
    """Failed authentication cannot fall through to a deployment operation."""
    results = [subprocess.CompletedProcess([], 0, stdout=account)]
    if account:
        results.append(subprocess.CompletedProcess([], 7))
    with (
        patch("scripts.deploy.shutil.which", return_value="gcloud"),
        patch("scripts.deploy.subprocess.run", side_effect=results) as run,
    ):
        assert deploy.main(TARGET + ["--execute"]) == (7 if account else 1)
    assert run.call_count == (2 if account else 1)
    assert run.call_args_list[0].kwargs["capture_output"] is True
    assert all(not call.kwargs.get("shell", False) for call in run.call_args_list)


def test_execution_reports_missing_cli() -> None:
    """Missing installation produces a useful failure without a subprocess."""
    with patch("scripts.deploy.shutil.which", return_value=None):
        assert deploy.main(TARGET + ["--execute"]) == 1
