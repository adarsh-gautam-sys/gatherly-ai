"""Liveness endpoint without external dependencies."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from gatherly import __version__

router = APIRouter()


class HealthResponse(BaseModel):
    """Public liveness status and application version."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    status: Literal["ok"]
    version: str


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Return liveness without exposing configuration or contacting services."""
    return HealthResponse(status="ok", version=__version__)
