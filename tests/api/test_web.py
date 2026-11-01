"""Verify the shipped browser interface and its security boundary."""

import pytest
from fastapi.testclient import TestClient

from gatherly.main import create_app


def test_planner_has_same_origin_csp_without_inline_scripts() -> None:
    """The product page permits only its own scripts, styles and API requests."""
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert 'id="event-form"' in response.text
    assert "90bd4f92" in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "name", ["style.css", "app.js", "model.js", "render.js", "mark.svg"]
)
def test_public_assets_are_cacheable(name: str) -> None:
    """A fixed allowlist serves only the small public interface assets."""
    with TestClient(create_app()) as client:
        response = client.get(f"/assets/{name}")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.content


@pytest.mark.parametrize(
    "path", ["/assets/config.py", "/assets/index.html", "/assets/.env"]
)
def test_asset_route_does_not_expose_other_files(path: str) -> None:
    """Application files and secrets are outside the public allowlist."""
    with TestClient(create_app()) as client:
        assert client.get(path).status_code == 404


def test_frontend_is_below_transfer_budget_before_compression() -> None:
    """The entire initial interface stays below the PRD's 100 KB target."""
    from gatherly.api.web import ASSETS

    with TestClient(create_app()) as client:
        total = len(client.get("/").content)
        total += sum(len(client.get(f"/assets/{name}").content) for name in ASSETS)
    assert total < 100_000
