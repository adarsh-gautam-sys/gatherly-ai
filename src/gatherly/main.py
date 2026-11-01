"""Application composition root."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.gzip import GZipMiddleware

from gatherly import __version__
from gatherly.api.docs import router as docs_router
from gatherly.api.errors import (
    APIError,
    api_error_handler,
    http_error_handler,
    validation_error_handler,
)
from gatherly.api.health import router as health_router
from gatherly.api.middleware import RequestGuard
from gatherly.api.routes import router as plans_router
from gatherly.config import Settings
from gatherly.infra.runtime import plan_service


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an app with injectable settings and development-only API documentation."""
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with plan_service(config) as planner:
            app.state.planner = planner
            try:
                yield
            finally:
                app.state.planner = None

    app = FastAPI(
        title="Gatherly AI",
        version=__version__,
        openapi_url="/openapi.json" if config.environment == "development" else None,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
        separate_input_output_schemas=False,
    )
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.include_router(health_router)
    app.include_router(plans_router)
    if config.environment == "development":
        app.include_router(docs_router)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(RequestGuard, settings=config)
    return app
