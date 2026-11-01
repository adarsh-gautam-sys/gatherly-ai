"""Verify a real image as non-root on a read-only filesystem, then stop it."""

import argparse
import http.client
import json
import re
import shutil
import subprocess  # nosec B404
from pathlib import Path
from time import monotonic, sleep

from scripts.load_sanity import run_load

ROOT = Path(__file__).resolve().parents[1]
STARTUP_SECONDS = 30
POLL_SECONDS = 0.2
MAX_P95_SECONDS = 2
VERIFY_RUNTIME = """
import errno, importlib.metadata, importlib.util, json, os, pathlib
assert os.getuid() == 10001 and os.getgid() == 10001
dev_tools = ('pytest', 'mypy', 'ruff', 'hatchling', 'pip')
assert not any(importlib.util.find_spec(name) for name in dev_tools)
try:
    pathlib.Path('/tmp/gatherly-readonly-probe').write_text('probe')
except OSError as error:
    assert error.errno == errno.EROFS
else:
    raise AssertionError('Container filesystem is writable')
packages = importlib.metadata.distributions()
print(json.dumps({dist.metadata['Name']: dist.version for dist in packages}))
"""


def docker(executable: str, *args: str) -> str:
    """Call the resolved Docker CLI with an argument vector and return stdout."""
    # Resolved executable and fixed Docker operations, with shell=False.
    result = subprocess.run(  # nosec B603
        [executable, *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def wait_ready(port: int) -> None:
    """Poll health with a bounded deadline and no remote requests."""
    deadline = monotonic() + STARTUP_SECONDS
    while monotonic() < deadline:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            if response.status == 200 and json.loads(response.read())["status"] == "ok":
                return
        except (OSError, ValueError, KeyError, http.client.HTTPException):
            pass
        finally:
            connection.close()
        sleep(POLL_SECONDS)
    raise RuntimeError("Container did not become healthy before the deadline.")


def verify_packages(packages: dict[str, str]) -> None:
    """Require every installed runtime dependency to match the repository lock."""

    def normalise(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    pins = dict(
        line.split("==", 1)
        for line in (ROOT / "requirements.txt")
        .read_text(encoding="utf-8-sig")
        .splitlines()
        if "==" in line
    )
    pins = {normalise(name): version for name, version in pins.items()}
    for name, version in packages.items():
        if normalise(name) != "gatherly-ai" and pins.get(normalise(name)) != version:
            raise RuntimeError(f"Runtime dependency differs from lock: {name}.")


def check_image(image: str) -> list[dict[str, int | float | str]]:
    """Launch an isolated disposable container and verify its runtime and load."""
    executable = shutil.which("docker")
    if executable is None:
        raise RuntimeError("Install Docker and start its Linux engine.")
    container = docker(
        executable,
        "run",
        "--detach",
        "--rm",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--memory=512m",
        "--cpus=1",
        "--publish=127.0.0.1::8080",
        "--env=GEMINI_API_KEY=",
        "--env=GATHERLY_REQUESTS_PER_MINUTE=600",
        image,
    )
    try:
        mapping = docker(executable, "port", container, "8080/tcp")
        if not re.fullmatch(r"127\.0\.0\.1:[0-9]+", mapping):
            raise RuntimeError("Expected one loopback-only port mapping.")
        port = int(mapping.rsplit(":", 1)[1])
        wait_ready(port)
        packages = json.loads(
            docker(executable, "exec", container, "python", "-c", VERIFY_RUNTIME)
        )
        verify_packages(packages)
        reports = [
            run_load(f"http://127.0.0.1:{port}", endpoint=endpoint)
            for endpoint in ("budget", "plans")
        ]
        if any(
            report["failures"] or float(report["p95_seconds"]) > MAX_P95_SECONDS
            for report in reports
        ):
            raise RuntimeError("Container load sanity check failed.")
        return reports
    finally:
        docker(executable, "stop", "--time=5", container)


def main(argv: list[str] | None = None) -> int:
    """Report verification results without leaving a test container running."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="gatherly-ai:local")
    options = parser.parse_args(argv)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/@-]*", options.image):
        parser.error("Use a Docker image reference, not command flags.")
    try:
        reports = check_image(options.image)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Container verification failed: {type(error).__name__}.")
        return 1
    print(json.dumps({"uid": 10001, "read_only": True, "load": reports}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
