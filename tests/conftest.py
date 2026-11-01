"""Isolate tests from developer configuration."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep real dotenv files and application environment values out of tests."""
    monkeypatch.chdir(tmp_path)
    for name in tuple(os.environ):
        if name.startswith("GATHERLY_") and name != "GATHERLY_RUN_LIVE_TEST":
            monkeypatch.delenv(name)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    if os.getenv("GATHERLY_RUN_LIVE_TEST") != "1" or os.getenv("CI"):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
