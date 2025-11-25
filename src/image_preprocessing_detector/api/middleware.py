"""API middleware components.

Provides:
- Request logging middleware
- Correlation ID tracking
- Request timing
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get the current request's correlation ID."""
    return correlation_id_var.get()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses with timing."""

    def __init__(
        self,
        app: Any,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            log_request_body: Whether to log request body.
            log_response_body: Whether to log response body.
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and log details.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler.

        Returns:
            The response from the handler.
        """
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_var.set(correlation_id)

        # Start timing
        start_time = time.perf_counter()

        # Log request
        log_context = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else "unknown",
        }

        logger.info("request_started", **log_context)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "request_error",
                **log_context,
                duration_ms=round(duration_ms, 2),
                error=str(e),
            )
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            "request_completed",
            **log_context,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))

        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures correlation ID is set for all requests."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Set correlation ID and process request.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler.

        Returns:
            The response with correlation ID header.
        """
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_var.set(correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        return response
