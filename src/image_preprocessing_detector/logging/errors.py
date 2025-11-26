"""Error taxonomy and Sentry integration.

Sprint 6.1.3: Provides:
- Structured error codes and classes
- Exception to error code mapping
- Optional Sentry integration (feature-flagged)
- Breadcrumb context for debugging
"""

import os
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from image_preprocessing_detector.logging import get_correlation_id, get_logger
from image_preprocessing_detector.utils.datetime_compat import UTC, datetime

# ============================================================================
# Error Taxonomy
# ============================================================================


class ErrorCategory(str, Enum):
    """High-level error categories."""

    VALIDATION = "validation"
    PROCESSING = "processing"
    INFRASTRUCTURE = "infrastructure"
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL = "internal"


class ErrorCode(str, Enum):
    """Structured error codes for the application."""

    # Validation Errors (400)
    INVALID_FILE_TYPE = "E1001"
    FILE_TOO_LARGE = "E1002"
    INVALID_PARAMETERS = "E1003"
    EMPTY_FILE = "E1004"
    INVALID_IMAGE_FORMAT = "E1005"
    CORRUPT_PDF = "E1006"
    UNSUPPORTED_COLOR_SPACE = "E1007"
    INVALID_DPI = "E1008"

    # Processing Errors (422)
    PROCESSING_FAILED = "E2001"
    IQA_FAILED = "E2002"
    CORRECTION_FAILED = "E2003"
    GATE_DETECTION_FAILED = "E2004"
    LAYOUT_DETECTION_FAILED = "E2005"
    PDF_EXTRACTION_FAILED = "E2006"
    IMAGE_LOAD_FAILED = "E2007"
    MODEL_INFERENCE_FAILED = "E2008"

    # Infrastructure Errors (500)
    GPU_UNAVAILABLE = "E3001"
    MODEL_LOAD_FAILED = "E3002"
    MEMORY_EXHAUSTED = "E3003"
    DISK_FULL = "E3004"
    TIMEOUT = "E3005"
    MODAL_CONNECTION_FAILED = "E3006"
    MODAL_EXECUTION_FAILED = "E3007"

    # Authentication Errors (401/403)
    UNAUTHORIZED = "E4001"
    INVALID_API_KEY = "E4002"
    EXPIRED_API_KEY = "E4003"
    FORBIDDEN = "E4004"

    # Rate Limiting Errors (429)
    RATE_LIMIT_EXCEEDED = "E5001"
    QUOTA_EXCEEDED = "E5002"

    # Configuration Errors
    INVALID_CONFIG = "E6001"
    MISSING_CONFIG = "E6002"
    INCOMPATIBLE_CONFIG = "E6003"

    # External Service Errors
    EXTERNAL_SERVICE_UNAVAILABLE = "E7001"
    EXTERNAL_SERVICE_TIMEOUT = "E7002"
    EXTERNAL_SERVICE_ERROR = "E7003"

    # Internal Errors (500)
    INTERNAL_ERROR = "E9001"
    UNEXPECTED_ERROR = "E9002"
    ASSERTION_FAILED = "E9003"


# Error code to category mapping
ERROR_CATEGORIES: dict[ErrorCode, ErrorCategory] = {
    # Validation
    ErrorCode.INVALID_FILE_TYPE: ErrorCategory.VALIDATION,
    ErrorCode.FILE_TOO_LARGE: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_PARAMETERS: ErrorCategory.VALIDATION,
    ErrorCode.EMPTY_FILE: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_IMAGE_FORMAT: ErrorCategory.VALIDATION,
    ErrorCode.CORRUPT_PDF: ErrorCategory.VALIDATION,
    ErrorCode.UNSUPPORTED_COLOR_SPACE: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_DPI: ErrorCategory.VALIDATION,
    # Processing
    ErrorCode.PROCESSING_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.IQA_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.CORRECTION_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.GATE_DETECTION_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.LAYOUT_DETECTION_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.PDF_EXTRACTION_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.IMAGE_LOAD_FAILED: ErrorCategory.PROCESSING,
    ErrorCode.MODEL_INFERENCE_FAILED: ErrorCategory.PROCESSING,
    # Infrastructure
    ErrorCode.GPU_UNAVAILABLE: ErrorCategory.INFRASTRUCTURE,
    ErrorCode.MODEL_LOAD_FAILED: ErrorCategory.INFRASTRUCTURE,
    ErrorCode.MEMORY_EXHAUSTED: ErrorCategory.INFRASTRUCTURE,
    ErrorCode.DISK_FULL: ErrorCategory.INFRASTRUCTURE,
    ErrorCode.TIMEOUT: ErrorCategory.INFRASTRUCTURE,
    ErrorCode.MODAL_CONNECTION_FAILED: ErrorCategory.INFRASTRUCTURE,
    ErrorCode.MODAL_EXECUTION_FAILED: ErrorCategory.INFRASTRUCTURE,
    # Authentication
    ErrorCode.UNAUTHORIZED: ErrorCategory.AUTHENTICATION,
    ErrorCode.INVALID_API_KEY: ErrorCategory.AUTHENTICATION,
    ErrorCode.EXPIRED_API_KEY: ErrorCategory.AUTHENTICATION,
    ErrorCode.FORBIDDEN: ErrorCategory.AUTHENTICATION,
    # Rate Limiting
    ErrorCode.RATE_LIMIT_EXCEEDED: ErrorCategory.RATE_LIMITING,
    ErrorCode.QUOTA_EXCEEDED: ErrorCategory.RATE_LIMITING,
    # Configuration
    ErrorCode.INVALID_CONFIG: ErrorCategory.CONFIGURATION,
    ErrorCode.MISSING_CONFIG: ErrorCategory.CONFIGURATION,
    ErrorCode.INCOMPATIBLE_CONFIG: ErrorCategory.CONFIGURATION,
    # External
    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: ErrorCategory.EXTERNAL_SERVICE,
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: ErrorCategory.EXTERNAL_SERVICE,
    ErrorCode.EXTERNAL_SERVICE_ERROR: ErrorCategory.EXTERNAL_SERVICE,
    # Internal
    ErrorCode.INTERNAL_ERROR: ErrorCategory.INTERNAL,
    ErrorCode.UNEXPECTED_ERROR: ErrorCategory.INTERNAL,
    ErrorCode.ASSERTION_FAILED: ErrorCategory.INTERNAL,
}

# Error code to HTTP status code mapping
ERROR_HTTP_STATUS: dict[ErrorCode, int] = {
    # 400 Bad Request
    ErrorCode.INVALID_FILE_TYPE: 400,
    ErrorCode.FILE_TOO_LARGE: 400,
    ErrorCode.INVALID_PARAMETERS: 400,
    ErrorCode.EMPTY_FILE: 400,
    ErrorCode.INVALID_IMAGE_FORMAT: 400,
    ErrorCode.CORRUPT_PDF: 400,
    ErrorCode.UNSUPPORTED_COLOR_SPACE: 400,
    ErrorCode.INVALID_DPI: 400,
    # 401 Unauthorized
    ErrorCode.UNAUTHORIZED: 401,
    # 403 Forbidden
    ErrorCode.INVALID_API_KEY: 403,
    ErrorCode.EXPIRED_API_KEY: 403,
    ErrorCode.FORBIDDEN: 403,
    # 422 Unprocessable Entity
    ErrorCode.PROCESSING_FAILED: 422,
    ErrorCode.IQA_FAILED: 422,
    ErrorCode.CORRECTION_FAILED: 422,
    ErrorCode.GATE_DETECTION_FAILED: 422,
    ErrorCode.LAYOUT_DETECTION_FAILED: 422,
    ErrorCode.PDF_EXTRACTION_FAILED: 422,
    ErrorCode.IMAGE_LOAD_FAILED: 422,
    ErrorCode.MODEL_INFERENCE_FAILED: 422,
    # 429 Too Many Requests
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
    # 500 Internal Server Error
    ErrorCode.GPU_UNAVAILABLE: 500,
    ErrorCode.MODEL_LOAD_FAILED: 500,
    ErrorCode.MEMORY_EXHAUSTED: 500,
    ErrorCode.DISK_FULL: 500,
    ErrorCode.TIMEOUT: 500,
    ErrorCode.MODAL_CONNECTION_FAILED: 500,
    ErrorCode.MODAL_EXECUTION_FAILED: 500,
    ErrorCode.INVALID_CONFIG: 500,
    ErrorCode.MISSING_CONFIG: 500,
    ErrorCode.INCOMPATIBLE_CONFIG: 500,
    # 502 Bad Gateway (external services)
    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: 502,
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: 504,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    # 500 Internal
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.UNEXPECTED_ERROR: 500,
    ErrorCode.ASSERTION_FAILED: 500,
}


# ============================================================================
# Structured Error
# ============================================================================


@dataclass
class StructuredError:
    """Structured error with full context."""

    code: ErrorCode
    message: str
    category: ErrorCategory = field(init=False)
    http_status: int = field(init=False)
    details: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=get_correlation_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    exception: Exception | None = None
    traceback_str: str | None = None

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        self.category = ERROR_CATEGORIES.get(self.code, ErrorCategory.INTERNAL)
        self.http_status = ERROR_HTTP_STATUS.get(self.code, 500)

        if self.exception and not self.traceback_str:
            self.traceback_str = traceback.format_exc()

    def to_dict(self, include_traceback: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Args:
            include_traceback: Include traceback in output (for debugging).

        Returns:
            Dictionary representation.
        """
        result = {
            "error_code": self.code.value,
            "error_name": self.code.name,
            "message": self.message,
            "category": self.category.value,
            "http_status": self.http_status,
            "details": self.details,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }

        if include_traceback and self.traceback_str:
            result["traceback"] = self.traceback_str

        return result

    def to_api_response(self) -> dict[str, Any]:
        """Convert to API error response format.

        Returns:
            API-friendly error response.
        """
        return {
            "error": self.code.name.lower(),
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
            "correlation_id": self.correlation_id,
        }


# ============================================================================
# Exception Classes
# ============================================================================


class AppError(Exception):
    """Base application error with error code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize application error.

        Args:
            code: Error code.
            message: Human-readable message.
            details: Additional details.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_structured_error(self) -> StructuredError:
        """Convert to StructuredError."""
        return StructuredError(
            code=self.code,
            message=self.message,
            details=self.details,
            exception=self,
        )


class ValidationError(AppError):
    """Validation error (400)."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.INVALID_PARAMETERS,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


class ProcessingError(AppError):
    """Processing error (422)."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.PROCESSING_FAILED,
        message: str = "Processing failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


class InfrastructureError(AppError):
    """Infrastructure error (500)."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: str = "Infrastructure error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


class AuthenticationError(AppError):
    """Authentication error (401/403)."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.UNAUTHORIZED,
        message: str = "Authentication required",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


class RateLimitError(AppError):
    """Rate limit error (429)."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED,
        message: str = "Rate limit exceeded",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


# ============================================================================
# Exception to Error Code Mapping
# ============================================================================

# Map standard Python exceptions to error codes
EXCEPTION_MAPPING: dict[type[Exception], ErrorCode] = {
    FileNotFoundError: ErrorCode.INVALID_FILE_TYPE,
    PermissionError: ErrorCode.FORBIDDEN,
    MemoryError: ErrorCode.MEMORY_EXHAUSTED,
    TimeoutError: ErrorCode.TIMEOUT,
    ValueError: ErrorCode.INVALID_PARAMETERS,
    TypeError: ErrorCode.INVALID_PARAMETERS,
    OSError: ErrorCode.INTERNAL_ERROR,
    IOError: ErrorCode.INTERNAL_ERROR,
    RuntimeError: ErrorCode.INTERNAL_ERROR,
    AssertionError: ErrorCode.ASSERTION_FAILED,
}


def map_exception_to_error(exception: Exception) -> StructuredError:
    """Map an exception to a structured error.

    Args:
        exception: The exception to map.

    Returns:
        StructuredError with appropriate code.
    """
    # Check if it's already an AppError
    if isinstance(exception, AppError):
        return exception.to_structured_error()

    # Look up in mapping
    error_code = EXCEPTION_MAPPING.get(type(exception), ErrorCode.UNEXPECTED_ERROR)

    return StructuredError(
        code=error_code,
        message=str(exception),
        exception=exception,
    )


# ============================================================================
# Sentry Integration
# ============================================================================


class SentryIntegration:
    """Optional Sentry integration for error tracking.

    Feature-flagged: Set IMGPREP_SENTRY_ENABLED=true to enable.
    """

    _initialized: bool = False
    _enabled: bool = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Sentry is enabled."""
        return cls._enabled and cls._initialized

    @classmethod
    def initialize(
        cls,
        dsn: str | None = None,
        environment: str | None = None,
        release: str | None = None,
        sample_rate: float = 1.0,
        traces_sample_rate: float = 0.1,
    ) -> bool:
        """Initialize Sentry integration.

        Args:
            dsn: Sentry DSN. If None, reads from SENTRY_DSN env var.
            environment: Environment name.
            release: Release version.
            sample_rate: Error sampling rate (0.0-1.0).
            traces_sample_rate: Transaction sampling rate.

        Returns:
            True if initialization succeeded.
        """
        # Check if enabled
        enabled = os.environ.get("IMGPREP_SENTRY_ENABLED", "false").lower() == "true"
        if not enabled:
            cls._enabled = False
            cls._initialized = True
            return False

        dsn = dsn or os.environ.get("SENTRY_DSN")
        if not dsn:
            cls._enabled = False
            cls._initialized = True
            return False

        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_sdk.init(
                dsn=dsn,
                environment=environment or os.environ.get("IMGPREP_ENV", "development"),
                release=release or os.environ.get("IMGPREP_VERSION", "0.1.0"),
                sample_rate=sample_rate,
                traces_sample_rate=traces_sample_rate,
                integrations=[
                    LoggingIntegration(
                        level=None,  # Capture nothing by default
                        event_level=None,  # Don't send log messages as events
                    ),
                ],
            )

            cls._enabled = True
            cls._initialized = True
        except ImportError:
            # sentry-sdk not installed
            cls._enabled = False
            cls._initialized = True
            return False
        except Exception:
            cls._enabled = False
            cls._initialized = True
            return False
        else:
            return True

    @classmethod
    def capture_error(
        cls,
        error: StructuredError | Exception,
        extra: dict[str, Any] | None = None,
    ) -> str | None:
        """Capture an error to Sentry.

        Args:
            error: Error to capture.
            extra: Additional context.

        Returns:
            Sentry event ID if captured, None otherwise.
        """
        if not cls.is_enabled():
            return None

        try:
            import sentry_sdk

            # Add breadcrumb context
            if extra:
                sentry_sdk.add_breadcrumb(
                    category="context",
                    message="Error context",
                    data=extra,
                    level="info",
                )

            if isinstance(error, StructuredError):
                sentry_sdk.set_context(
                    "error_details",
                    {
                        "error_code": error.code.value,
                        "category": error.category.value,
                        "correlation_id": error.correlation_id,
                        "details": error.details,
                    },
                )
                sentry_sdk.set_tag("error_code", error.code.value)
                sentry_sdk.set_tag("error_category", error.category.value)

                if error.exception:
                    return sentry_sdk.capture_exception(error.exception)  # type: ignore[no-any-return]
                return sentry_sdk.capture_message(error.message, level="error")  # type: ignore[no-any-return]
            return sentry_sdk.capture_exception(error)  # type: ignore[no-any-return]

        except Exception:
            return None

    @classmethod
    def add_breadcrumb(
        cls,
        message: str,
        category: str = "custom",
        level: str = "info",
        data: dict[str, Any] | None = None,
    ) -> None:
        """Add a breadcrumb for context.

        Args:
            message: Breadcrumb message.
            category: Category name.
            level: Log level.
            data: Additional data.
        """
        if not cls.is_enabled():
            return

        try:
            import sentry_sdk

            sentry_sdk.add_breadcrumb(
                category=category,
                message=message,
                data=data or {},
                level=level,
            )
        except Exception:  # noqa: S110
            # Sentry SDK may not be installed or configured; silently ignore
            pass  # nosec B110

    @classmethod
    def set_user(cls, user_id: str, **extra: Any) -> None:
        """Set user context for Sentry.

        Args:
            user_id: User identifier.
            **extra: Additional user data.
        """
        if not cls.is_enabled():
            return

        try:
            import sentry_sdk

            sentry_sdk.set_user({"id": user_id, **extra})
        except Exception:  # noqa: S110
            # Sentry SDK may not be installed or configured; silently ignore
            pass  # nosec B110


# ============================================================================
# Error Logger
# ============================================================================


class ErrorLogger:
    """Centralized error logging with Sentry integration."""

    def __init__(self, logger: Any | None = None) -> None:
        """Initialize error logger.

        Args:
            logger: Structlog logger instance.
        """
        self.logger = logger or get_logger(__name__)

    def log_error(
        self,
        error: StructuredError | Exception,
        context: dict[str, Any] | None = None,
        capture_to_sentry: bool = True,
    ) -> StructuredError:
        """Log an error with full context.

        Args:
            error: Error to log.
            context: Additional context.
            capture_to_sentry: Whether to capture to Sentry.

        Returns:
            StructuredError representation.
        """
        if isinstance(error, StructuredError):
            structured = error
        else:
            structured = map_exception_to_error(error)

        # Log locally
        self.logger.error(
            "error_occurred",
            error_code=structured.code.value,
            error_name=structured.code.name,
            category=structured.category.value,
            message=structured.message,
            details=structured.details,
            correlation_id=structured.correlation_id,
            http_status=structured.http_status,
            **(context or {}),
        )

        # Capture to Sentry if enabled
        if capture_to_sentry:
            SentryIntegration.capture_error(structured, extra=context)

        return structured

    def log_warning(
        self,
        message: str,
        code: ErrorCode | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a warning.

        Args:
            message: Warning message.
            code: Optional error code.
            context: Additional context.
        """
        self.logger.warning(
            "warning_occurred",
            message=message,
            error_code=code.value if code else None,
            **(context or {}),
        )


# ============================================================================
# Convenience Functions
# ============================================================================


def get_error_logger() -> ErrorLogger:
    """Get an error logger instance."""
    return ErrorLogger(get_logger("errors"))


def create_error(
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> StructuredError:
    """Create a structured error.

    Args:
        code: Error code.
        message: Human-readable message.
        details: Additional details.
        exception: Original exception.

    Returns:
        StructuredError instance.
    """
    return StructuredError(
        code=code,
        message=message,
        details=details or {},
        exception=exception,
    )
