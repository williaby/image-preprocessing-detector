# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Monitoring module for annotation system.

Phase 5 Task 5.3: Production-ready monitoring with Prometheus metrics
and structured logging for the annotation pipeline.

This module provides:
- Annotation-specific Prometheus metrics
- Structured logging with JSON output
- Metrics instrumentation helpers
- Context managers for batch and pipeline logging

Example:
    >>> from image_preprocessing_detector.annotation.monitoring import (
    ...     AnnotationMetrics,
    ...     get_annotation_metrics,
    ...     get_annotation_logger,
    ...     batch_logging_context,
    ... )
    >>>
    >>> # Metrics
    >>> metrics = get_annotation_metrics()
    >>> metrics.record_parse_operation("pubtabnet", 0.5, success=True)
    >>>
    >>> # Logging
    >>> logger = get_annotation_logger(__name__)
    >>> with batch_logging_context(logger, batch_num=0, batch_size=100):
    ...     logger.info("processing_batch")
"""

from __future__ import annotations

from .logging import (
    LOG_EVENTS,
    AnnotationLogEvents,
    batch_logging_context,
    get_annotation_logger,
    log_batch_processed,
    log_cache_stats,
    log_checkpoint_operation,
    log_parse_operation,
    log_pipeline_stage,
    log_scan_completed,
    log_scan_started,
    parse_logging_context,
    pipeline_stage_context,
    setup_logging,
)
from .metrics import (
    AnnotationMetrics,
    get_annotation_metrics,
    record_batch_processed,
    record_cache_operation,
    record_checkpoint_operation,
    record_parse_operation,
    record_scan_operation,
    timed_annotation,
)

__all__ = [
    # Logging
    "LOG_EVENTS",
    "AnnotationLogEvents",
    # Metrics
    "AnnotationMetrics",
    "batch_logging_context",
    "get_annotation_logger",
    "get_annotation_metrics",
    "log_batch_processed",
    "log_cache_stats",
    "log_checkpoint_operation",
    "log_parse_operation",
    "log_pipeline_stage",
    "log_scan_completed",
    "log_scan_started",
    "parse_logging_context",
    "pipeline_stage_context",
    "record_batch_processed",
    "record_cache_operation",
    "record_checkpoint_operation",
    "record_parse_operation",
    "record_scan_operation",
    "setup_logging",
    "timed_annotation",
]
