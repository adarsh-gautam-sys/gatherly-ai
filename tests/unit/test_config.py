"""Verify configuration defaults, precedence and rejection of invalid input."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from gatherly.config import Settings


def test_settings_default_to_production() -> None:
    """An unconfigured application uses the safer production setting."""
    assert Settings().environment == "production"


def test_settings_load_from_dotenv(tmp_path: Path) -> None:
    """Local configuration can be loaded from a UTF-8 dotenv file."""
    (tmp_path / ".env").write_text(
        "GATHERLY_ENVIRONMENT=development\n", encoding="utf-8"
    )
    assert Settings().environment == "development"


def test_environment_overrides_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Deployment environment values take precedence over local dotenv values."""
    (tmp_path / ".env").write_text(
        "GATHERLY_ENVIRONMENT=development\n", encoding="utf-8"
    )
    monkeypatch.setenv("GATHERLY_ENVIRONMENT", "production")
    assert Settings().environment == "production"


def test_explicit_settings_override_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Injected configuration takes precedence over process configuration."""
    monkeypatch.setenv("GATHERLY_ENVIRONMENT", "production")
    assert Settings(environment="development").environment == "development"


@pytest.mark.parametrize("value", ["", "staging", "DEVELOPMENT", "1"])
def test_invalid_environment_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Only the two explicitly supported environments are accepted."""
    monkeypatch.setenv("GATHERLY_ENVIRONMENT", value)
    with pytest.raises(ValidationError, match="environment"):
        Settings()


def test_unknown_dotenv_setting_is_rejected(tmp_path: Path) -> None:
    """Typos in local configuration fail instead of silently using defaults."""
    (tmp_path / ".env").write_text(
        "GATHERLY_ENVIROMENT=development\n", encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Settings()


def test_validation_error_does_not_include_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configuration error messages do not echo raw environment values."""
    untrusted_value = "untrusted-environment-value"
    monkeypatch.setenv("GATHERLY_ENVIRONMENT", untrusted_value)
    with pytest.raises(ValidationError) as error:
        Settings()
    assert untrusted_value not in str(error.value)
