"""Structured logging configuration using structlog and rich.

Provides JSON-formatted logs for production environments with rich console
output for development. All logs include contextual information for debugging
and monitoring.

Features:
- Rich console output for development
- JSON-formatted logs for production
- Performance logging helpers
- Proper type annotations

Note: Module named "log_config" to avoid shadowing Python's stdlib logging module.
"""

import logging
import sys
from typing import TYPE_CHECKING

import structlog
from rich.console import Console
from rich.logging import RichHandler
from structlog.stdlib import BoundLogger
from structlog.types import Processor

if TYPE_CHECKING:
    from structlog.types import EventDict, WrappedLogger

# Global console for rich output (stderr for proper output separation)
console = Console(stderr=True)


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
    include_timestamp: bool = True,
) -> None:
    """Configure structured logging for the application.

    Sets up both standard logging and structlog with appropriate handlers
    for the environment (JSON for production, rich console for development).

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to INFO.
        json_logs: If True, output JSON logs (production mode). If False,
            use rich console formatting (development mode). Defaults to False.
        include_timestamp: Whether to include timestamps in log output.
            Defaults to True.

    Example:
        >>> # Development setup
        >>> setup_logging(level="DEBUG", json_logs=False)

        >>> # Production setup
        >>> setup_logging(level="INFO", json_logs=True)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard Python logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=[
            (
                RichHandler(
                    console=console,
                    rich_tracebacks=True,
                    show_time=include_timestamp,
                    show_level=True,
                    show_path=True,
                )
                if not json_logs
                else logging.StreamHandler(sys.stdout)
            )
        ],
    )

    # Define a no-op processor for when timestamp is disabled
    def noop_processor(
        _logger: "WrappedLogger",
        _method_name: str,
        event_dict: "EventDict",
    ) -> "EventDict":
        """No-op processor that passes through the event dict unchanged."""
        return event_dict

    # Configure structlog processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        (
            structlog.processors.TimeStamper(fmt="iso")
            if include_timestamp
            else noop_processor
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # Production: JSON logs for easy parsing and aggregation
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Rich console output with colors and formatting
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """Get a structured logger instance.

    Creates or retrieves a structlog logger with the given name. This should
    typically be called with __name__ to create module-specific loggers.

    Args:
        name: Logger name (typically __name__ of the module).

    Returns:
        Configured structlog logger instance with methods like:
        - logger.info()
        - logger.debug()
        - logger.warning()
        - logger.error()
        - logger.exception()

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started", document_id="doc_001")
        >>> logger.warning("Low confidence", confidence=0.45, threshold=0.5)
        >>> logger.error("Processing failed", error="file_not_found")
    """
    # structlog.get_logger returns a BoundLogger when configured with stdlib LoggerFactory
    # Cast is safe because we configure structlog with stdlib LoggerFactory above
    from typing import cast

    return cast(BoundLogger, structlog.get_logger(name))


def log_performance(
    logger: BoundLogger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **context: object,
) -> None:
    """Log performance metrics for an operation.

    Provides a standardized way to log performance data with operation name,
    duration, success status, and additional context.

    Args:
        logger: Structlog logger instance from get_logger().
        operation: Name of the operation being timed.
        duration_ms: Duration in milliseconds.
        success: Whether the operation succeeded. Defaults to True.
        **context: Additional context key-value pairs to include in the log.

    Example:
        >>> logger = get_logger(__name__)
        >>> log_performance(
        ...     logger,
        ...     operation="image_processing",
        ...     duration_ms=42.5,
        ...     success=True,
        ...     image_count=10,
        ...     output_dir="/results",
        ... )
    """
    logger.info(
        "performance",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        success=success,
        **context,
    )


# Example usage and testing
if __name__ == "__main__":
    # Setup for development (rich console)
    setup_logging(level="DEBUG", json_logs=False)

    logger = get_logger(__name__)

    logger.debug("Debug message", extra_field="debug_value")
    logger.info("Processing started", document_id="doc_001", pages=10)
    logger.warning("Low confidence detection", confidence=0.42, threshold=0.5)
    logger.error("Failed to process", error="file_not_found", path="./missing.pdf")

    log_performance(
        logger,
        operation="image_quality_assessment",
        duration_ms=15.3,
        success=True,
        model="resnet18",
    )

    # Example of structured error logging
    def _raise_example_error() -> None:
        """Helper function to demonstrate error logging."""
        error_msg = "Example error for demonstration"
        raise ValueError(error_msg)

    try:
        _raise_example_error()
    except Exception:
        logger.exception("Unexpected error during processing")
