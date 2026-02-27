"""Structured logging utilities for annotation system.

Phase 5 Task 5.3.2: Annotation-specific structured logging with
context propagation and standardized log events.

This module extends the main logging infrastructure with:
- Annotation-specific log events and context
- Batch processing log context
- Parser operation logging
- Performance tracking

Example:
    >>> from image_preprocessing_detector.annotation.monitoring.logging import (
    ...     get_annotation_logger,
    ...     log_parse_operation,
    ...     batch_logging_context,
    ... )
    >>>
    >>> logger = get_annotation_logger(__name__)
    >>> logger.info("scan_started", dataset="pubtabnet", total_files=50000)
    >>>
    >>> with batch_logging_context(logger, batch_num=0, batch_size=100):
    ...     log_parse_operation(logger, "pubtabnet", duration_ms=42.5)
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from structlog.stdlib import BoundLogger

if TYPE_CHECKING:
    from pathlib import Path

# Re-export setup from main logging module
from image_preprocessing_detector.utils.log_config import (
    get_logger,
    log_performance,
    setup_logging,
)

# ============================================================================
# Annotation Log Event Types (for standardization)
# ============================================================================


@dataclass(frozen=True)
class AnnotationLogEvents:
    """Standard log event names for annotation operations.

    Use these constants for consistent event naming across the annotation system.
    """

    # Scanner events
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_RESUMED = "scan_resumed"
    SCAN_ERROR = "scan_error"

    # Batch events
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    BATCH_ERROR = "batch_error"

    # Checkpoint events
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_LOADED = "checkpoint_loaded"
    CHECKPOINT_CLEARED = "checkpoint_cleared"

    # Parser events
    PARSE_STARTED = "parse_started"
    PARSE_COMPLETED = "parse_completed"
    PARSE_ERROR = "parse_error"

    # Cache events
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_EVICTION = "cache_eviction"
    CACHE_CLEARED = "cache_cleared"

    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_STAGE_STARTED = "pipeline_stage_started"
    PIPELINE_STAGE_COMPLETED = "pipeline_stage_completed"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_ERROR = "pipeline_error"

    # Index events
    INDEX_BUILD_STARTED = "index_build_started"
    INDEX_BUILD_COMPLETED = "index_build_completed"


# Singleton instance
LOG_EVENTS = AnnotationLogEvents()


# ============================================================================
# Logger Factory
# ============================================================================


def get_annotation_logger(name: str) -> BoundLogger:
    """Get a structured logger for annotation operations.

    Creates a logger with annotation-specific context bound. Use this
    instead of the base get_logger for annotation module code.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger with annotation context

    Example:
        >>> logger = get_annotation_logger(__name__)
        >>> logger.info("scan_started", dataset="pubtabnet")
    """
    base_logger = get_logger(name)
    # Bind annotation subsystem context
    return base_logger.bind(subsystem="annotation")


# ============================================================================
# Logging Helper Functions
# ============================================================================


def log_scan_started(
    logger: BoundLogger,
    dataset: str,
    dataset_path: Path | str,
    total_files: int,
    config: dict[str, Any] | None = None,
) -> None:
    """Log scan start event.

    Args:
        logger: Logger instance
        dataset: Dataset name
        dataset_path: Path to dataset
        total_files: Total files to scan
        config: Optional scan configuration
    """
    logger.info(
        LOG_EVENTS.SCAN_STARTED,
        dataset=dataset,
        dataset_path=str(dataset_path),
        total_files=total_files,
        config=config or {},
    )


def log_scan_completed(
    logger: BoundLogger,
    dataset: str,
    total_files: int,
    batches: int,
    duration_seconds: float,
    resumed: bool = False,
) -> None:
    """Log scan completion event.

    Args:
        logger: Logger instance
        dataset: Dataset name
        total_files: Total files scanned
        batches: Number of batches created
        duration_seconds: Scan duration
        resumed: Whether scan was resumed from checkpoint
    """
    logger.info(
        LOG_EVENTS.SCAN_COMPLETED,
        dataset=dataset,
        total_files=total_files,
        batches=batches,
        duration_seconds=round(duration_seconds, 3),
        throughput_files_per_sec=round(total_files / duration_seconds, 1)
        if duration_seconds > 0
        else 0,
        resumed=resumed,
    )


def log_batch_processed(
    logger: BoundLogger,
    batch_num: int,
    batch_size: int,
    duration_seconds: float,
    success: bool = True,
    error: str = "",
) -> None:
    """Log batch processing event.

    Args:
        logger: Logger instance
        batch_num: Batch number
        batch_size: Number of items in batch
        duration_seconds: Processing duration
        success: Whether processing succeeded
        error: Error message if failed
    """
    event = LOG_EVENTS.BATCH_COMPLETED if success else LOG_EVENTS.BATCH_ERROR
    log_data: dict[str, Any] = {
        "batch_num": batch_num,
        "batch_size": batch_size,
        "duration_seconds": round(duration_seconds, 3),
        "throughput": round(batch_size / duration_seconds, 1)
        if duration_seconds > 0
        else 0,
    }

    if not success:
        log_data["error"] = error
        logger.error(event, **log_data)
    else:
        logger.info(event, **log_data)


def log_parse_operation(
    logger: BoundLogger,
    parser: str,
    duration_ms: float,
    success: bool = True,
    samples: int = 0,
    error: str = "",
) -> None:
    """Log parser operation.

    Args:
        logger: Logger instance
        parser: Parser name
        duration_ms: Operation duration in milliseconds
        success: Whether operation succeeded
        samples: Number of samples parsed
        error: Error message if failed
    """
    event = LOG_EVENTS.PARSE_COMPLETED if success else LOG_EVENTS.PARSE_ERROR
    log_data: dict[str, Any] = {
        "parser": parser,
        "duration_ms": round(duration_ms, 2),
    }

    if success:
        log_data["samples"] = samples
        logger.info(event, **log_data)
    else:
        log_data["error"] = error
        logger.error(event, **log_data)


def log_checkpoint_operation(
    logger: BoundLogger,
    operation: str,
    dataset: str,
    batch_num: int | None = None,
    duration_ms: float | None = None,
) -> None:
    """Log checkpoint operation.

    Args:
        logger: Logger instance
        operation: Operation type (save, load, clear)
        dataset: Dataset name
        batch_num: Batch number (for save operations)
        duration_ms: Operation duration
    """
    event_map = {
        "save": LOG_EVENTS.CHECKPOINT_SAVED,
        "load": LOG_EVENTS.CHECKPOINT_LOADED,
        "clear": LOG_EVENTS.CHECKPOINT_CLEARED,
    }
    event = event_map.get(operation, f"checkpoint_{operation}")

    log_data: dict[str, Any] = {"dataset": dataset, "operation": operation}

    if batch_num is not None:
        log_data["batch_num"] = batch_num

    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)

    logger.info(event, **log_data)


def log_cache_stats(
    logger: BoundLogger,
    cache_name: str,
    size: int,
    max_size: int,
    hit_rate: float,
    evictions: int,
) -> None:
    """Log cache statistics.

    Args:
        logger: Logger instance
        cache_name: Name of the cache
        size: Current cache size
        max_size: Maximum cache size
        hit_rate: Cache hit rate (0-1)
        evictions: Total evictions
    """
    logger.info(
        "cache_stats",
        cache_name=cache_name,
        size=size,
        max_size=max_size,
        utilization=round(size / max_size, 3) if max_size > 0 else 0,
        hit_rate=round(hit_rate, 4),
        evictions=evictions,
    )


def log_pipeline_stage(
    logger: BoundLogger,
    stage: str,
    duration_ms: float,
    success: bool = True,
    error: str = "",
    **context: Any,
) -> None:
    """Log pipeline stage execution.

    Args:
        logger: Logger instance
        stage: Stage name
        duration_ms: Execution duration
        success: Whether stage succeeded
        error: Error message if failed
        **context: Additional context
    """
    event = (
        LOG_EVENTS.PIPELINE_STAGE_COMPLETED if success else LOG_EVENTS.PIPELINE_ERROR
    )
    log_data: dict[str, Any] = {
        "stage": stage,
        "duration_ms": round(duration_ms, 2),
        **context,
    }

    if not success:
        log_data["error"] = error
        logger.error(event, **log_data)
    else:
        logger.info(event, **log_data)


# ============================================================================
# Context Managers for Logging
# ============================================================================


@contextmanager
def batch_logging_context(
    logger: BoundLogger,
    batch_num: int,
    batch_size: int,
    dataset: str = "",
) -> Generator[BoundLogger, None, None]:
    """Context manager that adds batch context to all log entries.

    Args:
        logger: Base logger instance
        batch_num: Batch number
        batch_size: Batch size
        dataset: Optional dataset name

    Yields:
        Logger with batch context bound

    Example:
        >>> with batch_logging_context(
        ...     logger, batch_num=0, batch_size=100
        ... ) as batch_logger:
        ...     batch_logger.info("processing_item", item_idx=42)
    """
    context: dict[str, Any] = {"batch_num": batch_num, "batch_size": batch_size}
    if dataset:
        context["dataset"] = dataset

    bound_logger = logger.bind(**context)
    bound_logger.debug(LOG_EVENTS.BATCH_STARTED)

    start = time.perf_counter()
    success = True
    error = ""

    try:
        yield bound_logger
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration = time.perf_counter() - start
        log_batch_processed(
            bound_logger, batch_num, batch_size, duration, success=success, error=error
        )


@contextmanager
def parse_logging_context(
    logger: BoundLogger,
    parser: str,
) -> Generator[BoundLogger, None, None]:
    """Context manager for parser operation logging.

    Args:
        logger: Base logger instance
        parser: Parser name

    Yields:
        Logger with parser context bound

    Example:
        >>> with parse_logging_context(logger, "pubtabnet") as parse_logger:
        ...     result = parser.parse(sample)
        ...     parse_logger.debug("sample_parsed", sample_id=sample.id)
    """
    bound_logger = logger.bind(parser=parser)
    bound_logger.debug(LOG_EVENTS.PARSE_STARTED)

    start = time.perf_counter()
    success = True
    error = ""

    try:
        yield bound_logger
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        log_parse_operation(
            bound_logger, parser, duration_ms, success=success, error=error
        )


@contextmanager
def pipeline_stage_context(
    logger: BoundLogger,
    stage: str,
    **context: Any,
) -> Generator[BoundLogger, None, None]:
    """Context manager for pipeline stage logging.

    Args:
        logger: Base logger instance
        stage: Stage name
        **context: Additional context to bind

    Yields:
        Logger with stage context bound

    Example:
        >>> with pipeline_stage_context(logger, "validation", dataset="pubtabnet"):
        ...     validate_samples(samples)
    """
    bound_logger = logger.bind(stage=stage, **context)
    bound_logger.debug(LOG_EVENTS.PIPELINE_STAGE_STARTED)

    start = time.perf_counter()
    success = True
    error = ""

    try:
        yield bound_logger
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        log_pipeline_stage(
            bound_logger, stage, duration_ms, success=success, error=error, **context
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Event constants
    "LOG_EVENTS",
    "AnnotationLogEvents",
    # Context managers
    "batch_logging_context",
    # Logger factory
    "get_annotation_logger",
    # Re-exports from base module
    "get_logger",
    # Logging helpers
    "log_batch_processed",
    "log_cache_stats",
    "log_checkpoint_operation",
    "log_parse_operation",
    "log_performance",
    "log_pipeline_stage",
    "log_scan_completed",
    "log_scan_started",
    "parse_logging_context",
    "pipeline_stage_context",
    "setup_logging",
]
