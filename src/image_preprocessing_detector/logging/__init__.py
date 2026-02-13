"""Enhanced structured logging framework.

Provides:
- JSON logs with rotation policy
- Correlation ID threading through pipeline
- PII redaction for sensitive data
- Configuration toggles for verbosity
- Log sampling for high-volume scenarios
"""

import logging
import os
import random
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field
from rich.console import Console
from rich.logging import RichHandler

# Module-level SystemRandom for log sampling (uses OS entropy, no seed needed)
_log_sampler = random.SystemRandom()

# ============================================================================
# Context Variables for Request Tracking
# ============================================================================

# Correlation ID for request tracing
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Additional context that flows through the pipeline
# NOTE: Default is None to avoid mutable default; use .set({}) to initialize
request_context_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "request_context", default=None
)


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def get_request_context() -> dict[str, Any]:
    """Get the current request context."""
    return request_context_var.get() or {}


def set_request_context(context: dict[str, Any]) -> None:
    """Set additional request context."""
    request_context_var.set(context)


def update_request_context(**kwargs: Any) -> None:
    """Update request context with additional fields."""
    current = (request_context_var.get() or {}).copy()
    current.update(kwargs)
    request_context_var.set(current)


# ============================================================================
# Configuration
# ============================================================================


class LoggingConfig(BaseModel):
    """Configuration for the logging framework."""

    # Output format
    json_logs: bool = Field(
        default=False,
        description="Output JSON logs (True for production, False for dev)",
    )
    log_level: str = Field(
        default="INFO",
        description="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # File rotation
    log_to_file: bool = Field(default=False, description="Enable file logging")
    log_file_path: str = Field(default="logs/app.log", description="Path to log file")
    max_bytes: int = Field(
        default=10 * 1024 * 1024, description="Max log file size (10MB default)"
    )
    backup_count: int = Field(default=5, description="Number of backup files to keep")
    rotation_when: str = Field(
        default="midnight", description="Time-based rotation (midnight, hourly)"
    )

    # PII redaction
    redact_pii: bool = Field(default=True, description="Enable PII redaction")
    redact_patterns: list[str] = Field(
        default=[
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{16}\b",  # Credit card (simple)
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card (formatted)
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # Phone
        ],
        description="Regex patterns to redact",
    )
    redact_fields: list[str] = Field(
        default=[
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
            "credit_card",
            "ssn",
            "social_security",
        ],
        description="Field names to redact (case-insensitive)",
    )

    # Verbosity controls
    include_timestamp: bool = Field(default=True, description="Include timestamps")
    include_caller: bool = Field(
        default=False, description="Include caller file/line (slower)"
    )
    include_request_context: bool = Field(
        default=True, description="Include request context in logs"
    )

    # Sampling
    sample_rate: float = Field(
        default=1.0,
        description="Log sampling rate (0.0-1.0, 1.0 = log everything)",
    )
    always_log_levels: list[str] = Field(
        default=["WARNING", "ERROR", "CRITICAL"],
        description="Always log these levels regardless of sampling",
    )


# Global config instance
_config: LoggingConfig | None = None


def get_logging_config() -> LoggingConfig:
    """Get the current logging configuration."""
    global _config
    if _config is None:
        _config = LoggingConfig()
    return _config


def set_logging_config(config: LoggingConfig) -> None:
    """Set the logging configuration."""
    global _config
    _config = config


# ============================================================================
# PII Redaction
# ============================================================================


class PIIRedactor:
    """Redacts PII from log data."""

    def __init__(self, config: LoggingConfig) -> None:
        """Initialize the redactor.

        Args:
            config: Logging configuration with redaction patterns.
        """
        self.enabled = config.redact_pii
        self.patterns = [re.compile(p, re.IGNORECASE) for p in config.redact_patterns]
        self.fields = {f.lower() for f in config.redact_fields}
        self.redacted_value = "[REDACTED]"

    def redact(self, data: Any) -> Any:
        """Redact PII from data.

        Args:
            data: Data to redact (dict, list, or string).

        Returns:
            Data with PII redacted.
        """
        if not self.enabled:
            return data

        if isinstance(data, dict):
            return self._redact_dict(data)
        if isinstance(data, list):
            return [self.redact(item) for item in data]
        if isinstance(data, str):
            return self._redact_string(data)
        return data

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact PII from dictionary."""
        result = {}
        for key, value in data.items():
            if key.lower() in self.fields:
                result[key] = self.redacted_value
            else:
                result[key] = self.redact(value)
        return result

    def _redact_string(self, data: str) -> str:
        """Redact PII from string."""
        result = data
        for pattern in self.patterns:
            result = pattern.sub(self.redacted_value, result)
        return result


# ============================================================================
# Custom Processors
# ============================================================================


def add_correlation_id(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add correlation ID to log event."""
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_request_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add request context to log event."""
    config = get_logging_config()
    if config.include_request_context:
        context = get_request_context()
        if context:
            event_dict["request_context"] = context
    return event_dict


def redact_pii_processor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact PII from log event."""
    config = get_logging_config()
    redactor = PIIRedactor(config)
    return redactor.redact(event_dict)  # type: ignore[no-any-return]


def add_service_info(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add service metadata to log event."""
    event_dict["service"] = "image-preprocessing-detector"
    event_dict["version"] = os.environ.get("IMGPREP_VERSION", "0.1.0")
    event_dict["environment"] = os.environ.get("IMGPREP_ENV", "development")
    return event_dict


def sample_logs(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Apply sampling to reduce log volume.

    Structlog processor that probabilistically drops events based on
    configured sample rate. Important log levels are always preserved.

    Uses SystemRandom (OS entropy) instead of the default PRNG to satisfy
    SonarCloud S6709 security hotspot requirements.
    """
    config = get_logging_config()
    level = event_dict.get("level", "").upper()

    # Drop sampled-out events (always preserve important levels)
    if (
        level not in config.always_log_levels
        and config.sample_rate < 1.0
        and _log_sampler.random() > config.sample_rate  # nosec B311
    ):
        raise structlog.DropEvent

    return event_dict


# ============================================================================
# Setup Functions
# ============================================================================


def setup_logging(config: LoggingConfig | None = None) -> None:
    """Configure the logging framework.

    Args:
        config: Logging configuration. If None, uses defaults.
    """
    if config is None:
        config = LoggingConfig(
            json_logs=os.environ.get("IMGPREP_JSON_LOGS", "false").lower() == "true",
            log_level=os.environ.get("IMGPREP_LOG_LEVEL", "INFO"),
            log_to_file=os.environ.get("IMGPREP_LOG_TO_FILE", "false").lower()
            == "true",
            log_file_path=os.environ.get("IMGPREP_LOG_FILE", "logs/app.log"),
            redact_pii=os.environ.get("IMGPREP_REDACT_PII", "true").lower() == "true",
        )

    set_logging_config(config)

    # Get log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Configure handlers
    handlers: list[logging.Handler] = []

    if config.json_logs:
        # Production: JSON to stdout
        handlers.append(logging.StreamHandler(sys.stdout))
    else:
        # Development: Rich console
        console = Console(stderr=True)
        handlers.append(
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=config.include_timestamp,
                show_level=True,
                show_path=config.include_caller,
            )
        )

    # File logging with rotation
    if config.log_to_file:
        log_path = Path(config.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler: RotatingFileHandler | TimedRotatingFileHandler
        if config.rotation_when in ("midnight", "hourly"):
            # Time-based rotation
            file_handler = TimedRotatingFileHandler(
                filename=str(log_path),
                when=config.rotation_when[
                    0
                ].upper(),  # 'M' for midnight, 'H' for hourly
                backupCount=config.backup_count,
            )
        else:
            # Size-based rotation
            file_handler = RotatingFileHandler(
                filename=str(log_path),
                maxBytes=config.max_bytes,
                backupCount=config.backup_count,
            )

        file_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(file_handler)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # Build processor chain
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_correlation_id,
        add_request_context,
        add_service_info,
        redact_pii_processor,
        sample_logs,
    ]

    if config.include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    if config.include_caller:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            )
        )

    processors.extend(
        [
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
    )

    if config.json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,  # Allow reconfiguration
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)


# ============================================================================
# Convenience Functions
# ============================================================================


def log_performance(
    logger: Any,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **context: Any,
) -> None:
    """Log performance metrics for an operation.

    Args:
        logger: Structlog logger instance.
        operation: Name of the operation.
        duration_ms: Duration in milliseconds.
        success: Whether the operation succeeded.
        **context: Additional context to include.
    """
    logger.info(
        "performance",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        success=success,
        **context,
    )


def log_processing_outcome(
    logger: Any,
    document_id: str,
    page_index: int,
    device_used: str,
    model_used: str,
    processing_time_ms: float,
    corrections_applied: list[str] | None = None,
    gate_reason: str | None = None,
    quality_score: float | None = None,
    **context: Any,
) -> None:
    """Log per-page processing outcome.

    Args:
        logger: Structlog logger instance.
        document_id: Document identifier.
        page_index: Page number (0-indexed).
        device_used: Device used (cpu, gpu, modal).
        model_used: Model used (student, teacher).
        processing_time_ms: Processing time in ms.
        corrections_applied: List of corrections applied.
        gate_reason: Reason for gate decision.
        quality_score: Final quality score.
        **context: Additional context.
    """
    logger.info(
        "processing_outcome",
        document_id=document_id,
        page_index=page_index,
        device_used=device_used,
        model_used=model_used,
        processing_time_ms=round(processing_time_ms, 2),
        corrections_applied=corrections_applied or [],
        gate_reason=gate_reason,
        quality_score=quality_score,
        **context,
    )


def log_teacher_usage(
    logger: Any,
    document_id: str,
    page_index: int,
    reason: str,
    student_confidence: float,
    teacher_confidence: float | None = None,
    device_used: str = "gpu",
    processing_time_ms: float | None = None,
) -> None:
    """Log teacher model usage context.

    Args:
        logger: Structlog logger instance.
        document_id: Document identifier.
        page_index: Page number.
        reason: Reason for teacher invocation.
        student_confidence: Student model confidence.
        teacher_confidence: Teacher model confidence (if available).
        device_used: Device used for teacher inference.
        processing_time_ms: Processing time.
    """
    logger.info(
        "teacher_usage",
        document_id=document_id,
        page_index=page_index,
        reason=reason,
        student_confidence=round(student_confidence, 4),
        teacher_confidence=round(teacher_confidence, 4) if teacher_confidence else None,
        device_used=device_used,
        processing_time_ms=round(processing_time_ms, 2) if processing_time_ms else None,
    )


# ============================================================================
# Context Manager for Correlation ID
# ============================================================================


class LoggingContext:
    """Context manager for setting logging context."""

    def __init__(
        self,
        correlation_id: str | None = None,
        **context: Any,
    ) -> None:
        """Initialize logging context.

        Args:
            correlation_id: Correlation ID for the context.
            **context: Additional context fields.
        """
        import uuid

        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.context = context
        self._prev_correlation_id: str = ""
        self._prev_context: dict[str, Any] = {}

    def __enter__(self) -> "LoggingContext":
        """Enter the context."""
        self._prev_correlation_id = get_correlation_id()
        self._prev_context = get_request_context()

        set_correlation_id(self.correlation_id)
        set_request_context(self.context)

        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the context."""
        set_correlation_id(self._prev_correlation_id)
        set_request_context(self._prev_context)


# Initialize with defaults on import
setup_logging()
