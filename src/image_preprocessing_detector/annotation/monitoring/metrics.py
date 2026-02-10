# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Prometheus metrics for annotation system.

Phase 5 Task 5.3.1: Annotation-specific Prometheus metrics for monitoring
parser performance, cache efficiency, batch processing, and scan operations.

Example:
    >>> from image_preprocessing_detector.annotation.monitoring.metrics import (
    ...     get_annotation_metrics,
    ... )
    >>>
    >>> metrics = get_annotation_metrics()
    >>> metrics.record_parse_operation("pubtabnet", 0.5, success=True)
"""

from __future__ import annotations

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

# Import from main monitoring module for Prometheus types
try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Stub implementations when prometheus_client is not available
    class Counter:  # type: ignore[no-redef]
        """No-op counter stub when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize no-op counter."""

        def labels(self, *_args: Any, **_kwargs: Any) -> Any:
            """Return self for chaining (no-op)."""
            return self

        def inc(self, _amount: float = 1) -> None:
            """Increment counter (no-op)."""

    class Gauge:  # type: ignore[no-redef]
        """No-op gauge stub when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize no-op gauge."""

        def labels(self, *_args: Any, **_kwargs: Any) -> Any:
            """Return self for chaining (no-op)."""
            return self

        def set(self, _value: float) -> None:
            """Set gauge value (no-op)."""

        def inc(self, _amount: float = 1) -> None:
            """Increment gauge (no-op)."""

        def dec(self, _amount: float = 1) -> None:
            """Decrement gauge (no-op)."""

    class Histogram:  # type: ignore[no-redef]
        """No-op histogram stub when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize no-op histogram."""

        def labels(self, *_args: Any, **_kwargs: Any) -> Any:
            """Return self for chaining (no-op)."""
            return self

        def observe(self, _amount: float) -> None:
            """Observe value (no-op)."""


# Namespace for annotation metrics
ANNOTATION_NAMESPACE = "imgprep_annotation"


@dataclass
class AnnotationMetricsConfig:
    """Configuration for annotation metrics."""

    enabled: bool = True
    namespace: str = ANNOTATION_NAMESPACE

    # Cardinality limits
    max_parser_labels: int = 50
    max_dataset_labels: int = 100


class AnnotationMetrics:
    """Prometheus metrics collector for annotation operations.

    Singleton class that provides metrics for:
    - Parser operations (parse latency, success/failure)
    - Cache efficiency (hits, misses, evictions)
    - Batch processing (throughput, latency)
    - Scanner operations (discovery, checkpointing)
    """

    _instance: AnnotationMetrics | None = None
    _initialized: bool = False

    def __new__(cls) -> AnnotationMetrics:
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize metrics if not already done."""
        if AnnotationMetrics._initialized:
            return

        self._config = AnnotationMetricsConfig()
        self._init_metrics()
        AnnotationMetrics._initialized = True

    def _init_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        ns = self._config.namespace

        # ================================================================
        # Parser Metrics
        # ================================================================

        self.parse_operations = Counter(
            f"{ns}_parse_operations_total",
            "Total parse operations by parser and status",
            ["parser", "status"],
        )

        self.parse_latency = Histogram(
            f"{ns}_parse_duration_seconds",
            "Parse operation duration in seconds",
            ["parser"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        self.parse_errors = Counter(
            f"{ns}_parse_errors_total",
            "Total parse errors by parser and error type",
            ["parser", "error_type"],
        )

        self.samples_parsed = Counter(
            f"{ns}_samples_parsed_total",
            "Total samples parsed by parser",
            ["parser"],
        )

        # ================================================================
        # Cache Metrics
        # ================================================================

        self.cache_operations = Counter(
            f"{ns}_cache_operations_total",
            "Cache operations by cache name and operation type",
            ["cache_name", "operation"],
        )

        self.cache_hit_rate = Gauge(
            f"{ns}_cache_hit_rate",
            "Cache hit rate (0-1)",
            ["cache_name"],
        )

        self.cache_size = Gauge(
            f"{ns}_cache_size",
            "Current cache size (number of entries)",
            ["cache_name"],
        )

        self.cache_evictions = Counter(
            f"{ns}_cache_evictions_total",
            "Total cache evictions",
            ["cache_name"],
        )

        # ================================================================
        # Batch Processing Metrics
        # ================================================================

        self.batches_processed = Counter(
            f"{ns}_batches_processed_total",
            "Total batches processed",
            ["dataset", "status"],
        )

        self.batch_size = Histogram(
            f"{ns}_batch_size",
            "Batch size distribution",
            ["dataset"],
            buckets=[10, 25, 50, 100, 250, 500, 1000],
        )

        self.batch_latency = Histogram(
            f"{ns}_batch_duration_seconds",
            "Batch processing duration in seconds",
            ["dataset"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.batch_throughput = Gauge(
            f"{ns}_batch_throughput_samples_per_second",
            "Current batch processing throughput",
            ["dataset"],
        )

        # ================================================================
        # Scanner Metrics
        # ================================================================

        self.scan_operations = Counter(
            f"{ns}_scan_operations_total",
            "Total scan operations",
            ["dataset", "status"],
        )

        self.scan_latency = Histogram(
            f"{ns}_scan_duration_seconds",
            "Scan operation duration in seconds",
            ["dataset"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
        )

        self.files_discovered = Counter(
            f"{ns}_files_discovered_total",
            "Total files discovered by scanner",
            ["dataset"],
        )

        self.checkpoint_operations = Counter(
            f"{ns}_checkpoint_operations_total",
            "Checkpoint operations by type",
            ["operation"],
        )

        self.checkpoint_latency = Histogram(
            f"{ns}_checkpoint_duration_seconds",
            "Checkpoint I/O duration in seconds",
            ["operation"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
        )

        self.scan_resume_count = Counter(
            f"{ns}_scan_resume_total",
            "Number of scans resumed from checkpoint",
            ["dataset"],
        )

        # ================================================================
        # JSONL Reader Metrics
        # ================================================================

        self.jsonl_index_operations = Counter(
            f"{ns}_jsonl_index_operations_total",
            "JSONL index operations",
            ["file", "operation"],
        )

        self.jsonl_index_latency = Histogram(
            f"{ns}_jsonl_index_duration_seconds",
            "JSONL index build duration in seconds",
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.jsonl_entries_indexed = Gauge(
            f"{ns}_jsonl_entries_indexed",
            "Number of entries in JSONL index",
            ["file"],
        )

        # ================================================================
        # Pipeline Metrics
        # ================================================================

        self.pipeline_stage_latency = Histogram(
            f"{ns}_pipeline_stage_duration_seconds",
            "Pipeline stage duration in seconds",
            ["stage"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
        )

        self.pipeline_errors = Counter(
            f"{ns}_pipeline_errors_total",
            "Pipeline stage errors",
            ["stage", "error_type"],
        )

        self.active_pipelines = Gauge(
            f"{ns}_active_pipelines",
            "Number of active pipeline instances",
        )

    # ================================================================
    # Recording Methods
    # ================================================================

    def record_parse_operation(
        self,
        parser: str,
        duration_seconds: float,
        success: bool = True,
        samples: int = 0,
        error_type: str = "",
    ) -> None:
        """Record a parse operation.

        Args:
            parser: Parser name (e.g., "pubtabnet", "fintabnet")
            duration_seconds: Operation duration
            success: Whether operation succeeded
            samples: Number of samples parsed
            error_type: Error type if failed
        """
        status = "success" if success else "error"
        self.parse_operations.labels(parser=parser, status=status).inc()
        self.parse_latency.labels(parser=parser).observe(duration_seconds)

        if success and samples > 0:
            self.samples_parsed.labels(parser=parser).inc(samples)
        elif not success and error_type:
            self.parse_errors.labels(parser=parser, error_type=error_type).inc()

    def record_cache_operation(
        self,
        cache_name: str,
        operation: str,
        hit_rate: float | None = None,
        size: int | None = None,
    ) -> None:
        """Record a cache operation.

        Args:
            cache_name: Name of the cache
            operation: Operation type (hit, miss, put, evict)
            hit_rate: Current hit rate (0-1)
            size: Current cache size
        """
        self.cache_operations.labels(cache_name=cache_name, operation=operation).inc()

        if operation == "evict":
            self.cache_evictions.labels(cache_name=cache_name).inc()

        if hit_rate is not None:
            self.cache_hit_rate.labels(cache_name=cache_name).set(hit_rate)

        if size is not None:
            self.cache_size.labels(cache_name=cache_name).set(size)

    def record_batch_processed(
        self,
        dataset: str,
        batch_size: int,
        duration_seconds: float,
        success: bool = True,
    ) -> None:
        """Record a processed batch.

        Args:
            dataset: Dataset name
            batch_size: Number of items in batch
            duration_seconds: Processing duration
            success: Whether processing succeeded
        """
        status = "success" if success else "error"
        self.batches_processed.labels(dataset=dataset, status=status).inc()
        self.batch_size.labels(dataset=dataset).observe(batch_size)
        self.batch_latency.labels(dataset=dataset).observe(duration_seconds)

        if duration_seconds > 0:
            throughput = batch_size / duration_seconds
            self.batch_throughput.labels(dataset=dataset).set(throughput)

    def record_scan_operation(
        self,
        dataset: str,
        duration_seconds: float,
        files_found: int,
        success: bool = True,
        resumed: bool = False,
    ) -> None:
        """Record a scan operation.

        Args:
            dataset: Dataset name
            duration_seconds: Scan duration
            files_found: Number of files discovered
            success: Whether scan succeeded
            resumed: Whether scan was resumed from checkpoint
        """
        status = "success" if success else "error"
        self.scan_operations.labels(dataset=dataset, status=status).inc()
        self.scan_latency.labels(dataset=dataset).observe(duration_seconds)
        self.files_discovered.labels(dataset=dataset).inc(files_found)

        if resumed:
            self.scan_resume_count.labels(dataset=dataset).inc()

    def record_checkpoint_operation(
        self,
        operation: str,
        duration_seconds: float,
    ) -> None:
        """Record a checkpoint operation.

        Args:
            operation: Operation type (save, load, clear)
            duration_seconds: Operation duration
        """
        self.checkpoint_operations.labels(operation=operation).inc()
        self.checkpoint_latency.labels(operation=operation).observe(duration_seconds)

    def record_jsonl_index(
        self,
        file_name: str,
        entries: int,
        duration_seconds: float,
    ) -> None:
        """Record JSONL index build.

        Args:
            file_name: JSONL file name
            entries: Number of entries indexed
            duration_seconds: Index build duration
        """
        self.jsonl_index_operations.labels(file=file_name, operation="build").inc()
        self.jsonl_index_latency.observe(duration_seconds)
        self.jsonl_entries_indexed.labels(file=file_name).set(entries)

    def record_pipeline_stage(
        self,
        stage: str,
        duration_seconds: float,
        error_type: str = "",
    ) -> None:
        """Record pipeline stage execution.

        Args:
            stage: Stage name
            duration_seconds: Execution duration
            error_type: Error type if failed
        """
        self.pipeline_stage_latency.labels(stage=stage).observe(duration_seconds)

        if error_type:
            self.pipeline_errors.labels(stage=stage, error_type=error_type).inc()

    def set_active_pipelines(self, count: int) -> None:
        """Set the number of active pipelines.

        Args:
            count: Number of active pipelines
        """
        self.active_pipelines.set(count)

    @contextmanager
    def time_parse(self, parser: str) -> Generator[None, None, None]:
        """Context manager to time a parse operation.

        Args:
            parser: Parser name

        Yields:
            None
        """
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.perf_counter() - start
            self.record_parse_operation(parser, duration, success=success)

    @contextmanager
    def time_batch(self, dataset: str, batch_size: int) -> Generator[None, None, None]:
        """Context manager to time batch processing.

        Args:
            dataset: Dataset name
            batch_size: Batch size

        Yields:
            None
        """
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.perf_counter() - start
            self.record_batch_processed(dataset, batch_size, duration, success=success)

    @contextmanager
    def time_pipeline_stage(self, stage: str) -> Generator[None, None, None]:
        """Context manager to time a pipeline stage.

        Args:
            stage: Stage name

        Yields:
            None
        """
        start = time.perf_counter()
        error_type = ""
        try:
            yield
        except Exception as e:
            error_type = type(e).__name__
            raise
        finally:
            duration = time.perf_counter() - start
            self.record_pipeline_stage(stage, duration, error_type=error_type)


# ================================================================
# Module-Level Convenience Functions
# ================================================================

_metrics: AnnotationMetrics | None = None


def get_annotation_metrics() -> AnnotationMetrics:
    """Get the global annotation metrics instance.

    Returns:
        AnnotationMetrics singleton instance
    """
    global _metrics
    if _metrics is None:
        _metrics = AnnotationMetrics()
    return _metrics


def record_parse_operation(
    parser: str,
    duration_seconds: float,
    success: bool = True,
    samples: int = 0,
    error_type: str = "",
) -> None:
    """Record a parse operation."""
    get_annotation_metrics().record_parse_operation(
        parser, duration_seconds, success, samples, error_type
    )


def record_cache_operation(
    cache_name: str,
    operation: str,
    hit_rate: float | None = None,
    size: int | None = None,
) -> None:
    """Record a cache operation."""
    get_annotation_metrics().record_cache_operation(
        cache_name, operation, hit_rate, size
    )


def record_batch_processed(
    dataset: str,
    batch_size: int,
    duration_seconds: float,
    success: bool = True,
) -> None:
    """Record a processed batch."""
    get_annotation_metrics().record_batch_processed(
        dataset, batch_size, duration_seconds, success
    )


def record_scan_operation(
    dataset: str,
    duration_seconds: float,
    files_found: int,
    success: bool = True,
    resumed: bool = False,
) -> None:
    """Record a scan operation."""
    get_annotation_metrics().record_scan_operation(
        dataset, duration_seconds, files_found, success, resumed
    )


def record_checkpoint_operation(operation: str, duration_seconds: float) -> None:
    """Record a checkpoint operation."""
    get_annotation_metrics().record_checkpoint_operation(operation, duration_seconds)


T = TypeVar("T")


def timed_annotation(
    operation_type: str,
    name: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to time annotation operations.

    Args:
        operation_type: Type of operation (parse, batch, stage)
        name: Operation name

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            metrics = get_annotation_metrics()
            start = time.perf_counter()
            error_type = ""

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error_type = type(e).__name__
                raise
            else:
                return result
            finally:
                duration = time.perf_counter() - start

                if operation_type == "parse":
                    metrics.record_parse_operation(
                        name, duration, success=not error_type
                    )
                elif operation_type == "stage":
                    metrics.record_pipeline_stage(name, duration, error_type)

        return wrapper

    return decorator
