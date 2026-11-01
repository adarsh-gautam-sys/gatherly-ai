"""Test request admission, privacy and headers through the actual ASGI stack."""

import asyncio
import base64
import hashlib
import json
import logging
import re

import pytest
from fastapi.testclient import TestClient
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send

from gatherly.api.middleware import RequestGuard
from gatherly.config import Settings
from gatherly.main import create_app
from tests.api.helpers import api_client
from tests.unit.domain_helpers import event_request


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/health", 200),
        ("/missing", 404),
        ("/api/v1/event-types", 200),
    ],
)
def test_security_headers_and_request_ids_cover_success_and_errors(
    path: str,
    status: int,
) -> None:
    """Responses forbid active content and caching, and HTTPS advertises HSTS."""
    with TestClient(create_app(), base_url="https://testserver") as client:
        first = client.get(path)
        second = client.get(path, headers={"X-Request-ID": "untrusted-client-id"})
    assert first.status_code == status
    assert first.headers["x-content-type-options"] == "nosniff"
    assert first.headers["referrer-policy"] == "no-referrer"
    assert first.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in first.headers["content-security-policy"]
    assert "unsafe-inline" not in first.headers["content-security-policy"]
    assert first.headers["strict-transport-security"] == "max-age=31536000"
    assert "camera=()" in first.headers["permissions-policy"]
    assert re.fullmatch(r"[0-9a-f]{32}", first.headers["x-request-id"])
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_http_does_not_trust_forwarded_protocol_or_ip_headers() -> None:
    """Proxy trust belongs to the server; clients cannot bypass the IP bucket."""
    with api_client(settings=Settings(requests_per_minute=1)) as client:
        first = client.get(
            "/api/v1/event-types", headers={"X-Forwarded-For": "1.2.3.4"}
        )
        second = client.get(
            "/api/v1/event-types",
            headers={
                "X-Forwarded-For": "5.6.7.8",
                "X-Forwarded-Proto": "https",
            },
        )
        health = client.get("/health")
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "rate_limited"
    assert 1 <= int(second.headers["retry-after"]) <= 60
    assert "strict-transport-security" not in second.headers
    assert second.headers["cache-control"] == "no-store"
    assert health.status_code == 200


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "null", "https://good.example.evil"]
)
def test_disallowed_origins_are_rejected_without_allow_headers(origin: str) -> None:
    """Exact origin matching prevents wildcard and suffix-based trust."""
    with api_client(
        settings=Settings(allowed_origins=("https://good.example",))
    ) as client:
        response = client.get("/api/v1/event-types", headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json()["code"] == "origin_forbidden"
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("origin", ["http://testserver", "https://good.example"])
def test_same_origin_and_explicit_cors_allowlist_work(origin: str) -> None:
    """Approved preflight and validation responses carry narrowly scoped CORS."""
    with api_client(
        settings=Settings(allowed_origins=("https://good.example",))
    ) as client:
        preflight = client.options(
            "/api/v1/plans",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Accept",
            },
        )
        invalid = client.post("/api/v1/plans", json={}, headers={"Origin": origin})
    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-methods"] == "GET, POST"
    for response in (preflight, invalid):
        assert response.headers["access-control-allow-origin"] == origin
        assert "Origin" in response.headers["vary"]
        assert "access-control-allow-credentials" not in response.headers
    assert invalid.status_code == 422


@pytest.mark.parametrize(
    "extra",
    [
        {"Access-Control-Request-Method": "DELETE"},
        {"Access-Control-Request-Headers": "Authorization"},
        {"Access-Control-Request-Private-Network": "true"},
    ],
)
def test_cors_rejects_unsupported_methods_headers_and_private_network(
    extra: dict[str, str],
) -> None:
    """Preflight failures use the same JSON envelope as other HTTP failures."""
    with api_client() as client:
        response = client.options(
            "/api/v1/plans",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "POST",
            }
            | extra,
        )
    assert response.status_code == 403
    assert response.json()["code"] == "cors_forbidden"


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({"Content-Type": "text/plain"}, 415),
        ({"Content-Type": "application/json", "Content-Encoding": "gzip"}, 415),
        ({"Content-Type": "application/json", "Content-Length": "-1"}, 400),
        ({"Content-Type": "application/json", "Content-Length": "9" * 11}, 400),
        ({"Content-Type": "application/json", "Content-Length": "1025"}, 413),
    ],
)
def test_request_headers_cannot_bypass_body_policy(
    headers: dict[str, str], status: int
) -> None:
    """Unsupported encodings and malformed or excessive lengths fail before parsing."""
    with api_client(settings=Settings(max_body_bytes=1024)) as client:
        response = client.post("/api/v1/plans", content="{}", headers=headers)
    assert response.status_code == status
    assert set(response.json()) == {"code", "message", "details"}
    assert response.headers["x-content-type-options"] == "nosniff"


def test_unexpected_failure_is_generic_and_logs_only_id_and_duration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exception payloads, query strings and client identifiers never enter app logs."""
    app = create_app()

    @app.get("/api/v1/broken", include_in_schema=False)
    async def broken() -> None:
        raise RuntimeError("private exception payload")

    caplog.set_level(logging.INFO, logger="gatherly.requests")
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/broken?notes=private-query", headers={"X-Request-ID": "private-id"}
        )
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "private" not in response.text
    records = [
        record for record in caplog.records if record.name == "gatherly.requests"
    ]
    assert records
    for record in records:
        assert set(json.loads(record.getMessage())) == {"request_id", "duration_ms"}
        assert "private" not in record.getMessage()


def test_request_timeout_cancels_work_and_returns_503() -> None:
    """A hung route is bounded even if it never enters the model adapter."""
    app = create_app(Settings(request_timeout_seconds=1))
    cancelled: list[bool] = []

    @app.get("/api/v1/slow", include_in_schema=False)
    async def slow() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    with TestClient(app) as client:
        response = client.get("/api/v1/slow")
    assert response.status_code == 503
    assert response.json()["code"] == "request_timeout"
    assert response.headers["cache-control"] == "no-store"
    assert cancelled == [True]


def test_gzip_response_keeps_security_headers_and_valid_json() -> None:
    """Compression does not alter the returned plan or response protections."""
    with api_client() as client:
        response = client.post(
            "/api/v1/plans",
            json=event_request().model_dump(mode="json"),
            headers={"Accept-Encoding": "gzip"},
        )
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["budget"]["total"] == 1_000_000
    assert response.headers["cache-control"] == "no-store"


def test_development_docs_authorize_only_the_static_bootstrap_script() -> None:
    """Swagger remains usable without allowing arbitrary inline JavaScript."""
    with api_client(settings=Settings(environment="development")) as client:
        response = client.get("/docs")
        alias = client.get("/redoc", follow_redirects=False)
    csp = response.headers["content-security-policy"]
    assert "unsafe-inline" not in csp
    scripts = re.findall(r"<script>(.*?)</script>", response.text, re.DOTALL)
    assert scripts
    for script in scripts:
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        assert f"'sha256-{digest}'" in csp
    assert alias.status_code == 307 and alias.headers["location"] == "/docs"


async def _guard_messages(
    incoming: list[Message],
    headers: list[tuple[bytes, bytes]],
    *,
    slow: bool = False,
) -> tuple[list[Message], list[bool]]:
    sent: list[Message] = []
    called: list[bool] = []
    scope: Scope = {
        "type": "http",
        "path": "/api/v1/plans",
        "method": "POST",
        "scheme": "http",
        "headers": [(b"content-type", b"application/json"), *headers],
        "client": None,
    }

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        called.append(True)
        message = await receive()
        assert message["type"] == "http.request"
        await Response(message.get("body", b""))(scope, receive, send)

    async def receive() -> Message:
        if slow:
            await asyncio.Event().wait()
        return incoming.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    await RequestGuard(app, Settings(max_body_bytes=1024, request_timeout_seconds=1))(
        scope, receive, send
    )
    return sent, called


@pytest.mark.parametrize("length", [[], [(b"content-length", b"1")]])
def test_chunked_and_underreported_bodies_are_counted_as_received(
    length: list[tuple[bytes, bytes]],
) -> None:
    """Actual received bytes enforce the cap even without an honest length header."""
    incoming: list[Message] = [
        {"type": "http.request", "body": b"a" * 600, "more_body": True},
        {"type": "http.request", "body": b"b" * 600, "more_body": True},
        {"type": "http.request", "body": b"unread"},
    ]
    sent, called = asyncio.run(_guard_messages(incoming, length))
    assert sent[0]["status"] == 413
    assert len(incoming) == 1 and not called


def test_body_at_exact_limit_is_replayed_and_disconnect_is_not_an_error() -> None:
    """The guard admits exact-limit bodies and abandons disconnected uploads."""
    sent, called = asyncio.run(
        _guard_messages([{"type": "http.request", "body": b"a" * 1024}], [])
    )
    assert sent[0]["status"] == 200 and called == [True]
    sent, called = asyncio.run(_guard_messages([{"type": "http.disconnect"}], []))
    assert sent == [] and called == []


@pytest.mark.parametrize(
    "headers",
    [
        [(b"content-length", b"1"), (b"content-length", b"2")],
        [(b"content-length", b"\xb2")],
    ],
)
def test_duplicate_and_non_ascii_lengths_are_rejected(
    headers: list[tuple[bytes, bytes]],
) -> None:
    """Ambiguous framing is rejected before reading the body."""
    sent, called = asyncio.run(_guard_messages([], headers))
    assert sent[0]["status"] == 400 and not called


def test_slow_upload_is_inside_the_request_deadline() -> None:
    """A client cannot evade the deadline by never finishing its request body."""
    sent, called = asyncio.run(_guard_messages([], [], slow=True))
    assert sent[0]["status"] == 503 and not called
