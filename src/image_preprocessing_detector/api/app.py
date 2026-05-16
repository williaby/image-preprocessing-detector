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

        # Pre-load ML models to eliminate first-request cold-start latency
        try:
            from image_preprocessing_detector.models.model_loader import (
                get_model_info,
                load_student_model,
                load_teacher_model,
                warmup_models,
            )

            # Determine device for model loading
            model_device = "cuda" if caps.has_local_gpu else "cpu"

            # Always pre-load student model (used for all requests)
            logger.info("preloading_student_model", device=model_device)
            student_model = load_student_model(device=model_device)

            # Pre-load teacher model if GPU available (optional optimization)
            teacher_model = None
            if caps.has_local_gpu:
                logger.info("preloading_teacher_model", device="cuda")
                teacher_model = load_teacher_model(device="cuda")
            else:
                logger.info(
                    "skipping_teacher_preload",
                    reason="No local GPU available, teacher will lazy-load if needed",
                )

            # Warmup models with dummy inference (avoids first-request penalty)
            if student_model is not None or teacher_model is not None:
                logger.info("warming_up_models")
                warmup_stats = warmup_models(student_model, teacher_model)
                logger.info("model_warmup_complete", stats=warmup_stats)

            # Store models in app state for request handlers
            _app.state.student_model = student_model
            _app.state.teacher_model = teacher_model
            _app.state.model_device = model_device

            # Log model info
            if student_model:
                student_info = get_model_info(student_model)
                logger.info("student_model_ready", info=student_info)
            if teacher_model:
                teacher_info = get_model_info(teacher_model)
                logger.info("teacher_model_ready", info=teacher_info)

        except Exception as e:
            logger.warning(
                "model_preload_failed",
                error=str(e),
                fallback="Models will be lazy-loaded on first request",
            )
            # Initialize app state with None (lazy loading will occur)
            _app.state.student_model = None
            _app.state.teacher_model = None
            _app.state.model_device = "cpu"

    except Exception as e:
        logger.warning("device_probe_failed_on_startup", error=str(e))
        # Initialize app state with defaults
        _app.state.student_model = None
        _app.state.teacher_model = None
        _app.state.model_device = "cpu"

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

    contact: dict[str, str] = {}
    if settings.contact_name:
        contact["name"] = settings.contact_name
    if settings.contact_url:
        contact["url"] = settings.contact_url
    if settings.contact_email:
        contact["email"] = settings.contact_email

    fastapi_kwargs: dict[str, Any] = {
        "title": settings.title,
        "description": settings.description,
        "version": settings.version,
        "lifespan": lifespan,
        "openapi_tags": settings.get_openapi_tags(),
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "license_info": {
            "name": settings.license_name,
            "url": settings.license_url,
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local development server"},
        ],
    }
    if contact:
        fastapi_kwargs["contact"] = contact
    if settings.terms_of_service:
        fastapi_kwargs["terms_of_service"] = settings.terms_of_service

    app = FastAPI(**fastapi_kwargs)

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

    # Add CORS middleware last (executes first in the chain, must be outermost)
    if settings.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
        logger.info("cors_middleware_enabled", origins=settings.cors_origins)

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
