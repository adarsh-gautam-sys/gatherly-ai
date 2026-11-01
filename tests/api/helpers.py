"""Compose an HTTP test client with deterministic, offline service dependencies."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from gatherly.api.routes import get_service
from gatherly.config import Settings
from gatherly.infra.cache import MemoryIdeasCache
from gatherly.main import create_app
from gatherly.services.plan_service import PlanService
from tests.unit.ai_helpers import FakeGenerator, FixedClock


@contextmanager
def api_client(
    generator: FakeGenerator | None = None,
    settings: Settings | None = None,
) -> Iterator[TestClient]:
    """Run lifespan while replacing model, clock and cache at the API dependency."""
    app = create_app(settings)
    service = PlanService(generator, MemoryIdeasCache(8, 30), FixedClock(), "api-test")
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as client:
        yield client
