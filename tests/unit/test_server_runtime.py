"""Exercise platform settings and the container server's resource controls."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from gatherly import serve
from gatherly.config import Settings
from tests.api.helpers import api_client


def test_platform_settings_and_server_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The runtime honors PORT and disables forwarded headers and access logs."""
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("GATHERLY_EXTERNAL_HTTPS", "true")
    assert Settings().external_https is True
    with patch("gatherly.serve.uvicorn.run") as run:
        serve.main()
    options = run.call_args.kwargs
    assert options["port"] == 9090
    assert options["workers"] == 1
    assert options["limit_concurrency"] == serve.MAX_CONNECTIONS
    assert options["timeout_keep_alive"] == serve.KEEP_ALIVE_SECONDS
    assert options["timeout_graceful_shutdown"] == serve.SHUTDOWN_SECONDS
    assert not options["proxy_headers"]
    assert not options["access_log"]
    assert not options["server_header"]


@pytest.mark.parametrize("port", ["0", "80", "65536", "bad"])
def test_platform_port_is_bounded(monkeypatch: pytest.MonkeyPatch, port: str) -> None:
    """A non-root runtime cannot accidentally listen on a privileged port."""
    monkeypatch.setenv("PORT", port)
    with pytest.raises(ValidationError):
        Settings()


def test_managed_tls_contract_preserves_same_origin_and_peer_limits() -> None:
    """Explicit TLS configuration enables HSTS without trusting client IP headers."""
    settings = Settings(external_https=True, requests_per_minute=1)
    with api_client(settings=settings) as client:
        first = client.get(
            "/api/v1/event-types",
            headers={"Origin": "https://testserver", "X-Forwarded-For": "1.2.3.4"},
        )
        second = client.get(
            "/api/v1/event-types",
            headers={"Origin": "https://testserver", "X-Forwarded-For": "5.6.7.8"},
        )
        wrong_origin = client.get("/health", headers={"Origin": "http://testserver"})
    assert first.status_code == 200
    assert first.headers["strict-transport-security"] == "max-age=31536000"
    assert first.headers["access-control-allow-origin"] == "https://testserver"
    assert second.status_code == 429
    assert wrong_origin.status_code == 403
