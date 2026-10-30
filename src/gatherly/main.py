"""Application composition root."""

from fastapi import FastAPI

from gatherly import __version__
from gatherly.api.health import router
from gatherly.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an app with injectable settings and development-only API documentation."""
    config = settings if settings is not None else Settings()
    app = FastAPI(
        title="Gatherly AI",
        version=__version__,
        openapi_url="/openapi.json" if config.environment == "development" else None,
    )
    app.include_router(router)
    return app
