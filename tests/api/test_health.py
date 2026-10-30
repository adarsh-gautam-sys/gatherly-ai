"""Verify liveness and documentation exposure through the ASGI application."""

from http import HTTPStatus
from importlib.metadata import version

import pytest
from fastapi.testclient import TestClient

from gatherly import __version__
from gatherly.config import Settings
from gatherly.main import create_app


def test_health_returns_only_status_and_package_version() -> None:
    """Liveness works without credentials and reports the installed package version."""
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok", "version": version("gatherly-ai")}
    assert version("gatherly-ai") == __version__


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_documentation_is_hidden_by_default(path: str) -> None:
    """Production does not expose interactive docs or the schema."""
    with TestClient(create_app()) as client:
        assert client.get(path).status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_injected_development_settings_enable_documentation(path: str) -> None:
    """Explicit development configuration enables all documentation routes."""
    with TestClient(create_app(Settings(environment="development"))) as client:
        assert client.get(path).status_code == HTTPStatus.OK


def test_factory_loads_environment_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """The server factory uses environment settings when none are injected."""
    monkeypatch.setenv("GATHERLY_ENVIRONMENT", "development")
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["info"]["version"] == __version__
    assert "/health" in response.json()["paths"]


def test_health_does_not_accept_post() -> None:
    """Liveness is a read-only GET endpoint."""
    with TestClient(create_app()) as client:
        assert client.post("/health").status_code == HTTPStatus.METHOD_NOT_ALLOWED
