"""Preview or explicitly execute a bounded Cloud Run source deployment."""

import argparse
import json
import re
import shutil
import subprocess  # nosec B404
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATTERN = r"[a-z][a-z0-9-]{4,28}[a-z0-9]"
SERVICE_PATTERN = r"[a-z](?:[a-z0-9-]{0,47}[a-z0-9])?"
ACCOUNT_PATTERN = (
    r"[a-z][a-z0-9-]{4,28}[a-z0-9]@" + PROJECT_PATTERN + r"\.iam\.gserviceaccount\.com"
)


def checked(value: str, pattern: str) -> str:
    """Accept only a resource identifier, never shell syntax or secret contents."""
    if not re.fullmatch(pattern, value):
        raise argparse.ArgumentTypeError("Use a valid resource identifier.")
    return value


def parser() -> argparse.ArgumentParser:
    """Define explicit deployment targets and opt-in execution/public access."""
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--project", required=True, type=lambda v: checked(v, PROJECT_PATTERN)
    )
    result.add_argument(
        "--region", required=True, type=lambda v: checked(v, r"[a-z]+-[a-z]+[0-9]+")
    )
    result.add_argument(
        "--service", default="gatherly-ai", type=lambda v: checked(v, SERVICE_PATTERN)
    )
    result.add_argument(
        "--service-account", required=True, type=lambda v: checked(v, ACCOUNT_PATTERN)
    )
    result.add_argument(
        "--secret", type=lambda v: checked(v, r"[A-Za-z0-9_-]{1,255}:[1-9][0-9]*")
    )
    result.add_argument(
        "--public",
        action="store_true",
        help="Explicitly allow unauthenticated invocation.",
    )
    result.add_argument(
        "--execute",
        action="store_true",
        help="Run the previewed command; otherwise perform no cloud actions.",
    )
    return result


def deployment_command(
    options: argparse.Namespace, executable: str = "gcloud"
) -> list[str]:
    """Build a source deployment without embedding any secret value."""
    command = [
        executable,
        "run",
        "deploy",
        options.service,
        f"--project={options.project}",
        f"--region={options.region}",
        f"--source={ROOT}",
        f"--service-account={options.service_account}",
        "--execution-environment=gen2",
        "--port=8080",
        "--cpu=1",
        "--memory=512Mi",
        "--concurrency=16",
        "--max-instances=1",
        "--min-instances=0",
        "--timeout=60s",
        "--ingress=all",
        "--invoker-iam-check",
        "--set-env-vars=GATHERLY_ENVIRONMENT=production,GATHERLY_EXTERNAL_HTTPS=true",
        "--allow-unauthenticated" if options.public else "--no-allow-unauthenticated",
        f"--set-secrets=GEMINI_API_KEY={options.secret}"
        if options.secret
        else "--clear-secrets",
        "--quiet",
    ]
    return command


def main(argv: list[str] | None = None) -> int:
    """Print a reviewable command and deploy only after explicit CLI opt-in."""
    options = parser().parse_args(argv)
    print(json.dumps(deployment_command(options), indent=2))
    if not options.execute:
        return 0
    executable = shutil.which("gcloud")
    if executable is None:
        print("Install the Google Cloud CLI before deploying.")
        return 1
    # Fixed read-only arguments, with shell interpretation disabled.
    account = subprocess.run(  # nosec B603
        [
            executable,
            "auth",
            "list",
            "--filter=status:ACTIVE",
            "--format=value(account)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if account.returncode or not account.stdout.strip():
        print("No active CLI login is available. Run gcloud auth login, then retry.")
        return 1
    # Identifiers are allowlisted; the argument vector is never shell-expanded.
    return subprocess.run(  # nosec B603
        deployment_command(options, executable), check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
