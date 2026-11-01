"""ASGI request bounds, same-origin policy, safe errors and security headers."""

import asyncio
import json
import logging
from time import monotonic
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from gatherly.api.errors import APIError, error_response
from gatherly.config import Settings
from gatherly.infra.rate_limit import RateLimiter

LOGGER = logging.getLogger("gatherly.requests")
MILLISECONDS_PER_SECOND = 1000
SECURITY_HEADERS = {
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'; "
    "base-uri 'none'; form-action 'none'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cache-control": "no-store",
}
ALLOWED_METHODS = {"GET", "POST"}
ALLOWED_HEADERS = {"content-type", "accept"}


def _secure_headers(
    message: Message, scope: Scope, request_id: str, origin: str
) -> None:
    headers = MutableHeaders(scope=message)
    for key, value in SECURITY_HEADERS.items():
        headers.setdefault(key, value)
    headers["x-request-id"] = request_id
    if scope["scheme"] == "https":
        headers["strict-transport-security"] = "max-age=31536000"
    if origin:
        headers["access-control-allow-origin"] = origin
        headers.add_vary_header("Origin")
        headers["access-control-expose-headers"] = (
            "X-Request-ID, Retry-After, Content-Disposition"
        )


def _check_origin(scope: Scope, headers: Headers, origins: tuple[str, ...]) -> str:
    origin = headers.get("origin", "")
    same_origin = f"{scope['scheme']}://{headers.get('host', '')}"
    if origin and origin not in (*origins, same_origin):
        raise APIError(403, "origin_forbidden", "This origin is not allowed.")
    return origin


def _preflight(headers: Headers) -> Response:
    requested = {
        item.strip().lower()
        for item in headers.get("access-control-request-headers", "").split(",")
        if item.strip()
    }
    if (
        headers.get("access-control-request-method") not in ALLOWED_METHODS
        or not requested <= ALLOWED_HEADERS
        or "access-control-request-private-network" in headers
    ):
        raise APIError(
            403, "cors_forbidden", "This cross-origin request is not allowed."
        )
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
            "Access-Control-Max-Age": "600",
        },
    )


async def _read_body(receive: Receive, limit: int) -> bytes | None:
    body = bytearray()
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return None
        chunk = message.get("body", b"")
        if len(body) + len(chunk) > limit:
            raise APIError(413, "body_too_large", "The request body is too large.")
        body.extend(chunk)
        if not message.get("more_body", False):
            return bytes(body)


def _check_body_headers(headers: Headers, limit: int) -> None:
    lengths = headers.getlist("content-length")
    if len(lengths) > 1 or (lengths and not lengths[0].isascii()):
        raise APIError(400, "invalid_length", "Invalid Content-Length header.")
    if lengths:
        if not lengths[0].isdigit() or len(lengths[0]) > 10:
            raise APIError(400, "invalid_length", "Invalid Content-Length header.")
        if int(lengths[0]) > limit:
            raise APIError(413, "body_too_large", "The request body is too large.")
    if headers.get("content-encoding", "identity").lower() != "identity":
        raise APIError(415, "unsupported_encoding", "Send an uncompressed JSON body.")
    if headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise APIError(415, "unsupported_media_type", "Send application/json.")


class RequestGuard:
    """Enforce limits before parsing and keep headers on early and late errors."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        """Create process-local admission control using validated settings."""
        self.app = app
        self.settings = settings
        self.limiter = RateLimiter(
            settings.requests_per_minute, settings.rate_limit_capacity
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bound HTTP work and pass lifespan events through unchanged."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        started = monotonic()
        sent = False
        origin = ""

        async def safe_send(message: Message) -> None:
            nonlocal sent
            if message["type"] == "http.response.start":
                sent = True
                _secure_headers(message, scope, request_id, origin)
            await send(message)

        try:
            headers = Headers(scope=scope)
            origin = _check_origin(scope, headers, self.settings.allowed_origins)
            async with asyncio.timeout(self.settings.request_timeout_seconds):
                await self._dispatch(scope, receive, safe_send, headers)
        except APIError as error:
            await error_response(error.status, error.code, error.message)(
                scope, receive, safe_send
            )
        except TimeoutError:
            if not sent:
                await error_response(
                    503, "request_timeout", "The request timed out. Try again."
                )(scope, receive, safe_send)
        except Exception:
            if not sent:
                await error_response(
                    500, "internal_error", "The request could not be completed."
                )(scope, receive, safe_send)
        finally:
            LOGGER.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "duration_ms": round(
                            (monotonic() - started) * MILLISECONDS_PER_SECOND
                        ),
                    }
                )
            )

    async def _dispatch(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        headers: Headers,
    ) -> None:
        if scope["path"].startswith("/api/"):
            address = scope.get("client")
            retry = self.limiter.consume(address[0] if address else "unknown")
            if retry:
                response = error_response(
                    429, "rate_limited", "Too many requests. Try again later."
                )
                response.headers["retry-after"] = str(retry)
                await response(scope, receive, send)
                return
            if scope["method"] == "OPTIONS" and "origin" in headers:
                await _preflight(headers)(scope, receive, send)
                return
        if scope["method"] in {"POST", "PUT", "PATCH"} and scope["path"].startswith(
            "/api/"
        ):
            _check_body_headers(headers, self.settings.max_body_bytes)
            body = await _read_body(receive, self.settings.max_body_bytes)
            if body is None:
                return

            async def replay() -> Message:
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay, send)
        else:
            await self.app(scope, receive, send)
