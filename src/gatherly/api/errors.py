"""Consistent public errors with no raw input, provider details or traceback."""

from http import HTTPStatus
from typing import cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from gatherly.domain.models import DomainModel

MAX_ERROR_DETAILS = 20


class ErrorDetail(DomainModel):
    """A safe field location and actionable validation message."""

    field: str
    message: str


class ErrorEnvelope(DomainModel):
    """The common error response for routing, validation and middleware failures."""

    code: str
    message: str
    details: tuple[ErrorDetail, ...] = ()


class APIError(Exception):
    """An intentional public HTTP failure with a fixed, safe message."""

    def __init__(self, status: int, code: str, message: str) -> None:
        """Store a safe response without attaching user input."""
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_response(
    status: int,
    code: str,
    message: str,
    details: tuple[ErrorDetail, ...] = (),
) -> JSONResponse:
    """Serialize one consistent error envelope."""
    return JSONResponse(
        ErrorEnvelope(code=code, message=message, details=details).model_dump(
            mode="json"
        ),
        status_code=status,
    )


async def api_error_handler(request: Request, error: Exception) -> JSONResponse:
    """Render intentional failures; never stringify arbitrary exceptions."""
    failure = cast(APIError, error)
    return error_response(failure.status, failure.code, failure.message)


async def validation_error_handler(request: Request, error: Exception) -> JSONResponse:
    """Keep useful field paths while omitting input values and custom error context."""
    details: list[ErrorDetail] = []
    failure = cast(RequestValidationError, error)
    for item in failure.errors()[:MAX_ERROR_DETAILS]:
        kind = item["type"]
        # Unknown object keys are user text, so do not echo their locations.
        field = (
            "body"
            if kind == "extra_forbidden"
            else ".".join(str(part) for part in item["loc"])
        )
        message = (
            "This field is required."
            if kind == "missing"
            else "Use the documented type, range and allowed values."
        )
        details.append(ErrorDetail(field=field, message=message))
    return error_response(
        422, "validation_error", "Check the request fields.", tuple(details)
    )


async def http_error_handler(request: Request, error: Exception) -> JSONResponse:
    """Normalize framework errors, including 404 and 405, without echoing paths."""
    failure = cast(HTTPException, error)
    status = failure.status_code
    response = error_response(status, f"http_{status}", HTTPStatus(status).phrase)
    if failure.headers:
        response.headers.update(failure.headers)
    return response
