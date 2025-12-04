"""API middleware components.

Provides:
- Request logging middleware
- Correlation ID tracking
- Request timing
- API key authentication
- Rate limiting
"""

import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any, ClassVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication.

    Validates API key from X-API-Key header. Allows bypass for:
    - Internal callers (by IP)
    - Health/ready endpoints
    - OpenAPI documentation endpoints
    """

    # Endpoints that don't require authentication (frozen to prevent accidental modification)
    PUBLIC_PATHS: ClassVar[frozenset[str]] = frozenset(
        {
            "/",
            "/health",
            "/ready",
            "/version",
            "/openapi.json",
            "/docs",
            "/redoc",
        }
    )

    def __init__(
        self,
        app: Any,
        api_keys: list[str],
        internal_callers: list[str] | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize the auth middleware.

        Args:
            app: The ASGI application.
            api_keys: List of valid API keys.
            internal_callers: IP addresses allowed without auth.
            enabled: Whether authentication is enabled.
        """
        super().__init__(app)
        self.api_keys = set(api_keys)
        self.internal_callers = set(internal_callers or [])
        self.enabled = enabled

    def _is_public_path(self, path: str) -> bool:
        """Check if path is publicly accessible."""
        return path in self.PUBLIC_PATHS

    def _is_internal_caller(self, request: Request) -> bool:
        """Check if request is from an internal caller."""
        if not self.internal_callers:
            return False

        client_ip = request.client.host if request.client else None
        if not client_ip:
            return False

        # Check exact match or localhost variants
        if client_ip in self.internal_callers:
            return True

        # Handle localhost variants
        localhost_ips = {"127.0.0.1", "::1", "localhost"}
        return client_ip in localhost_ips and any(
            ip in localhost_ips for ip in self.internal_callers
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Validate API key and process request.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler.

        Returns:
            The response or 401/403 error.
        """
        # Skip if auth is disabled
        if not self.enabled:
            return await call_next(request)

        # Skip for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Allow internal callers without API key
        if self._is_internal_caller(request):
            logger.debug(
                "internal_caller_allowed",
                client_ip=request.client.host if request.client else "unknown",
                path=request.url.path,
            )
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            logger.warning(
                "auth_missing_api_key",
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "API key required. Provide X-API-Key header.",
                    "correlation_id": get_correlation_id(),
                },
            )

        if api_key not in self.api_keys:
            logger.warning(
                "auth_invalid_api_key",
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "forbidden",
                    "message": "Invalid API key.",
                    "correlation_id": get_correlation_id(),
                },
            )

        logger.debug(
            "auth_success",
            path=request.url.path,
        )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for request rate limiting.

    Uses a simple in-memory sliding window counter.
    For production, consider Redis-based rate limiting.
    """

    def __init__(
        self,
        app: Any,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        enabled: bool = True,
        limit_paths: list[str] | None = None,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            app: The ASGI application.
            requests_per_window: Maximum requests allowed per window.
            window_seconds: Window duration in seconds.
            enabled: Whether rate limiting is enabled.
            limit_paths: Specific paths to rate limit (None = all paths).
        """
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.enabled = enabled
        self.limit_paths = set(limit_paths) if limit_paths else None

        # In-memory request tracking: {client_key: [(timestamp, count), ...]}
        # NOTE: This state is per-worker instance. In multi-worker deployments,
        # rate limiting is approximate since each worker tracks independently.
        # For precise distributed rate limiting, use Redis or similar.
        self._request_counts: dict[str, list[tuple[float, int]]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client.

        Uses API key if present, otherwise IP address.
        """
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:8]}..."  # Use partial key for privacy

        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _should_limit_path(self, path: str) -> bool:
        """Check if path should be rate limited."""
        if self.limit_paths is None:
            return True

        # Check exact match or prefix match for batch/process paths
        for limit_path in self.limit_paths:
            if path == limit_path or path.startswith(limit_path + "/"):
                return True

        return False

    def _cleanup_old_entries(self, client_key: str, current_time: float) -> None:
        """Remove entries outside the current window."""
        cutoff = current_time - self.window_seconds
        self._request_counts[client_key] = [
            (ts, count) for ts, count in self._request_counts[client_key] if ts > cutoff
        ]

    def _get_request_count(self, client_key: str, current_time: float) -> int:
        """Get the number of requests in the current window."""
        self._cleanup_old_entries(client_key, current_time)
        return sum(count for _, count in self._request_counts[client_key])

    def _record_request(self, client_key: str, current_time: float) -> None:
        """Record a new request."""
        self._request_counts[client_key].append((current_time, 1))

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Check rate limit and process request.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler.

        Returns:
            The response or 429 error if rate limited.
        """
        # Skip if rate limiting is disabled
        if not self.enabled:
            return await call_next(request)

        # Check if this path should be rate limited
        if not self._should_limit_path(request.url.path):
            return await call_next(request)

        client_key = self._get_client_key(request)
        current_time = time.time()

        # Check current request count
        current_count = self._get_request_count(client_key, current_time)

        if current_count >= self.requests_per_window:
            logger.warning(
                "rate_limit_exceeded",
                client_key=client_key,
                path=request.url.path,
                current_count=current_count,
                limit=self.requests_per_window,
            )

            # Calculate retry-after
            oldest_entry = min(
                (ts for ts, _ in self._request_counts[client_key]),
                default=current_time,
            )
            retry_after = int(self.window_seconds - (current_time - oldest_entry)) + 1

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Rate limit exceeded. "
                        f"Max {self.requests_per_window} requests "
                        f"per {self.window_seconds} seconds."
                    ),
                    "retry_after_seconds": retry_after,
                    "correlation_id": get_correlation_id(),
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record the request
        self._record_request(client_key, current_time)

        # Process request and add rate limit headers
        response = await call_next(request)

        # Add rate limit info to response headers
        remaining = max(0, self.requests_per_window - current_count - 1)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)

        return response
