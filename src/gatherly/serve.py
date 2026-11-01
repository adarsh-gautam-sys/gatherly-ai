"""Container entry point with bounded server resources and privacy-safe logging."""

import uvicorn

from gatherly.config import Settings

MAX_CONNECTIONS = 64
KEEP_ALIVE_SECONDS = 5
SHUTDOWN_SECONDS = 10
# Cloud Run requires all-interface binding inside the isolated container.
CONTAINER_HOST = "0.0.0.0"  # nosec B104
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(message)s"}},
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "gatherly.requests": {
            "handlers": ["stderr"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {"handlers": ["stderr"], "level": "WARNING", "propagate": False},
    },
}


def main() -> None:
    """Honor the platform port while ignoring spoofable forwarding headers."""
    settings = Settings()
    uvicorn.run(
        "gatherly.main:create_app",
        factory=True,
        host=CONTAINER_HOST,
        port=settings.port,
        workers=1,
        access_log=False,
        proxy_headers=False,
        server_header=False,
        limit_concurrency=MAX_CONNECTIONS,
        timeout_keep_alive=KEEP_ALIVE_SECONDS,
        timeout_graceful_shutdown=SHUTDOWN_SECONDS,
        log_config=LOG_CONFIG,
    )


if __name__ == "__main__":
    main()
