"""Structured logging configuration using structlog.

Provides JSON-formatted logs for production with rich console output for development.

Note: Module named "logging" intentionally shadows stdlib for project-specific config.
Uses aliased import to avoid circular import detection by CodeQL.
"""

import logging as stdlib_logging  # Aliased to avoid circular import with CodeQL
import sys
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

# Re-export stdlib logging as logging for internal use
logging = stdlib_logging

# Global console for rich output
console = Console(stderr=True)


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
    include_timestamp: bool = True,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON logs (production). If False, use rich console.
        include_timestamp: Whether to include timestamps in logs
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard logging
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

    # Configure structlog
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        (
            structlog.processors.TimeStamper(fmt="iso")
            if include_timestamp
            else lambda *_args, **_kwargs: {}
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # Production: JSON logs
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Rich console output
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Convenience function for performance logging
def log_performance(
    logger: Any,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **context: Any,
) -> None:
    """Log performance metrics for an operation.

    Args:
        logger: Structlog logger instance
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        success: Whether the operation succeeded
        **context: Additional context to include in the log
    """
    logger.info(
        "performance",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        success=success,
        **context,
    )


# Example usage
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
        model="mobilenet_v3",
    )

    # Example of structured error logging
    def _raise_example_error() -> None:
        """Helper function to demonstrate error logging."""
        raise ValueError("Example error")

    try:
        _raise_example_error()
    except Exception:
        logger.exception("Unexpected error during processing")
