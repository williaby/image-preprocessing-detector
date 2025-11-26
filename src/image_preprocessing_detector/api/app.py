"""FastAPI application factory.

Creates and configures the FastAPI application with:
- CORS middleware
- Request logging middleware
- Health/ready/version routes
- Processing routes (when implemented)
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from image_preprocessing_detector.api.config import APISettings, get_api_settings
from image_preprocessing_detector.api.middleware import (
    APIKeyAuthMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from image_preprocessing_detector.api.routes.batch import router as batch_router
from image_preprocessing_detector.api.routes.health import (
    router as health_router,
)
from image_preprocessing_detector.api.routes.health import (
    set_server_start_time,
)
from image_preprocessing_detector.api.routes.process import router as process_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:
    """Application lifespan context manager.

    Handles startup and shutdown events.

    Args:
        _app: The FastAPI application instance (unused but required by FastAPI).

    Yields:
        None during application runtime.
    """
    # Startup
    logger.info("application_starting")
    set_server_start_time()

    # Pre-load device capabilities for faster first request
    try:
        from image_preprocessing_detector.utils.device_probe import (
            probe_device_capabilities,
        )

        caps = probe_device_capabilities()
        logger.info(
            "device_capabilities_probed",
            has_gpu=caps.has_local_gpu,
            gpu_name=caps.gpu_name,
            cpu_count=caps.cpu_count,
            modal_available=caps.modal_available,
        )
    except Exception as e:
        logger.warning("device_probe_failed_on_startup", error=str(e))

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_shutting_down")


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional API settings. If None, loads from environment.

    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_api_settings()

    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        lifespan=lifespan,
        openapi_tags=settings.get_openapi_tags(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware if enabled
    if settings.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
        logger.info("cors_middleware_enabled", origins=settings.cors_origins)

    # Add request logging middleware
    app.add_middleware(
        RequestLoggingMiddleware,
        log_request_body=settings.log_request_body,
        log_response_body=settings.log_response_body,
    )
    logger.info("logging_middleware_enabled")

    # Add rate limiting middleware if enabled
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_window=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            enabled=True,
            limit_paths=["/process", "/batch"],  # Only limit processing endpoints
        )
        logger.info(
            "rate_limit_middleware_enabled",
            requests_per_window=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    # Add API key authentication middleware if enabled
    if settings.auth_enabled:
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_keys=settings.api_keys,
            internal_callers=settings.internal_callers,
            enabled=True,
        )
        logger.info(
            "auth_middleware_enabled",
            num_api_keys=len(settings.api_keys),
            num_internal_callers=len(settings.internal_callers),
        )

    # Include routers
    app.include_router(health_router)
    logger.info("health_routes_registered")

    app.include_router(process_router)
    logger.info("process_routes_registered")

    app.include_router(batch_router)
    logger.info("batch_routes_registered")

    # Root endpoint redirect to docs
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Redirect root to API documentation."""
        return {
            "message": "Image Preprocessing Detector API",
            "docs": "/docs",
            "health": "/health",
            "ready": "/ready",
            "version": "/version",
        }

    return app


# Default application instance for uvicorn
app = create_app()
