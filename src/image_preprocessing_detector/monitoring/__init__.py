"""Prometheus metrics export module.

Sprint 6.2.1: Provides metrics for:
- Latency (p50, p95, p99)
- Error rate
- Teacher escalation rate
- Cost estimates (Modal GPU usage)
- Queue depth
- Label cardinality guards
"""

import os
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

# Use prometheus_client if available, otherwise provide stubs
try:
    from prometheus_client import (
        REGISTRY,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
        multiprocess,
        start_http_server,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Stub implementations for when prometheus_client is not installed
    # These stubs provide API compatibility when prometheus_client is not installed
    REGISTRY = None  # type: ignore[assignment]
    CollectorRegistry = None  # type: ignore[misc, assignment]
    multiprocess = None  # type: ignore[assignment]

    class Counter:  # type: ignore[no-redef]
        """Stub Counter metric when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize stub Counter (no-op)."""

        def labels(self, *_args: Any, **_kwargs: Any) -> "Counter":
            """Return self for method chaining (no-op)."""
            return self  # type: ignore[return-value]

        def inc(self, _amount: float = 1) -> None:
            """Increment counter (no-op)."""

    class Gauge:  # type: ignore[no-redef]
        """Stub Gauge metric when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize stub Gauge (no-op)."""

        def labels(self, *_args: Any, **_kwargs: Any) -> "Gauge":
            """Return self for method chaining (no-op)."""
            return self  # type: ignore[return-value]

        def set(self, _value: float) -> None:
            """Set gauge value (no-op)."""

        def inc(self, _amount: float = 1) -> None:
            """Increment gauge (no-op)."""

        def dec(self, _amount: float = 1) -> None:
            """Decrement gauge (no-op)."""

    class Histogram:  # type: ignore[no-redef]
        """Stub Histogram metric when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize stub Histogram (no-op)."""

        def labels(self, *_args: Any, **_kwargs: Any) -> "Histogram":
            """Return self for method chaining (no-op)."""
            return self  # type: ignore[return-value]

        def observe(self, _amount: float) -> None:
            """Observe value (no-op)."""

    class Info:  # type: ignore[no-redef]
        """Stub Info metric when prometheus_client unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            """Initialize stub Info (no-op)."""

        def info(self, _val: dict[str, str]) -> None:
            """Set info labels (no-op)."""

    def generate_latest(_registry: Any = None) -> bytes:  # type: ignore[misc]
        """Generate empty metrics output (stub)."""
        return b""

    def start_http_server(_port: int, _registry: Any = None) -> None:  # type: ignore[misc]
        """Start HTTP server (no-op stub)."""


# ============================================================================
# Configuration
# ============================================================================


class MetricsNamespace(str, Enum):
    """Metric namespace prefixes for different deployments."""

    PRODUCTION = "imgprep_prod"
    STAGING = "imgprep_staging"
    DEVELOPMENT = "imgprep_dev"
    TEST = "imgprep_test"


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""

    enabled: bool = True
    namespace: str = "imgprep"
    subsystem: str = ""

    # HTTP server settings
    port: int = 8000
    start_server: bool = False

    # Cardinality limits
    max_document_id_labels: int = 100
    max_error_code_labels: int = 50

    # Cost tracking
    modal_cost_per_gpu_second: float = 0.0001  # $0.36/hour for T4

    @classmethod
    def from_environment(cls) -> "MetricsConfig":
        """Create config from environment variables."""
        env = os.environ.get("IMGPREP_ENV", "development").lower()
        namespace_map = {
            "production": MetricsNamespace.PRODUCTION.value,
            "staging": MetricsNamespace.STAGING.value,
            "development": MetricsNamespace.DEVELOPMENT.value,
            "test": MetricsNamespace.TEST.value,
        }

        return cls(
            enabled=os.environ.get("IMGPREP_METRICS_ENABLED", "true").lower() == "true",
            namespace=namespace_map.get(env, "imgprep"),
            port=int(os.environ.get("IMGPREP_METRICS_PORT", "8000")),
            start_server=os.environ.get("IMGPREP_METRICS_SERVER", "false").lower()
            == "true",
            modal_cost_per_gpu_second=float(
                os.environ.get("IMGPREP_MODAL_COST_PER_GPU_SEC", "0.0001")
            ),
        )


# ============================================================================
# Label Cardinality Guard
# ============================================================================


class CardinalityGuard:
    """Guards against label cardinality explosion."""

    def __init__(self, max_unique_values: int = 100) -> None:
        """Initialize the guard.

        Args:
            max_unique_values: Maximum unique values to track.
        """
        self._max_values = max_unique_values
        self._seen_values: set[str] = set()
        self._overflow_value = "__other__"

    def sanitize(self, value: str) -> str:
        """Sanitize a label value, limiting cardinality.

        Args:
            value: The label value to sanitize.

        Returns:
            Sanitized value or overflow bucket.
        """
        if value in self._seen_values:
            return value

        if len(self._seen_values) < self._max_values:
            self._seen_values.add(value)
            return value

        return self._overflow_value

    def reset(self) -> None:
        """Reset the guard state."""
        self._seen_values.clear()


# ============================================================================
# Metrics Singleton
# ============================================================================


class MetricsCollector:
    """Singleton metrics collector for the application."""

    _instance: "MetricsCollector | None" = None
    _initialized: bool = False

    def __new__(cls) -> "MetricsCollector":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if MetricsCollector._initialized:
            return

        self._config = MetricsConfig.from_environment()
        self._registry = REGISTRY if PROMETHEUS_AVAILABLE else None

        # Cardinality guards
        self._document_guard = CardinalityGuard(self._config.max_document_id_labels)
        self._error_guard = CardinalityGuard(self._config.max_error_code_labels)

        # Initialize metrics
        self._init_metrics()

        MetricsCollector._initialized = True

    def _init_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        ns = self._config.namespace

        # ----------------------------------------------------------------
        # Latency Metrics
        # ----------------------------------------------------------------

        # Processing latency histogram
        self.processing_latency = Histogram(
            f"{ns}_processing_duration_seconds",
            "Processing duration in seconds",
            ["operation", "device", "model"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Gate latency
        self.gate_latency = Histogram(
            f"{ns}_gate_duration_seconds",
            "Text gate detection duration in seconds",
            ["result"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
        )

        # IQA latency
        self.iqa_latency = Histogram(
            f"{ns}_iqa_duration_seconds",
            "IQA processing duration in seconds",
            ["model", "device"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        # Correction latency
        self.correction_latency = Histogram(
            f"{ns}_correction_duration_seconds",
            "Correction processing duration in seconds",
            ["correction_type"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
        )

        # ----------------------------------------------------------------
        # Counter Metrics
        # ----------------------------------------------------------------

        # Pages processed
        self.pages_processed = Counter(
            f"{ns}_pages_processed_total",
            "Total pages processed",
            ["status", "gate_result"],
        )

        # Documents processed
        self.documents_processed = Counter(
            f"{ns}_documents_processed_total",
            "Total documents processed",
            ["status", "pdf_type"],
        )

        # Errors
        self.errors = Counter(
            f"{ns}_errors_total",
            "Total errors by type",
            ["error_code", "category"],
        )

        # Corrections applied
        self.corrections_applied = Counter(
            f"{ns}_corrections_applied_total",
            "Total corrections applied",
            ["correction_type"],
        )

        # Teacher model invocations
        self.teacher_invocations = Counter(
            f"{ns}_teacher_invocations_total",
            "Total teacher model invocations",
            ["reason", "device"],
        )

        # Teacher invocations blocked
        self.teacher_blocked = Counter(
            f"{ns}_teacher_blocked_total",
            "Total blocked teacher invocations",
            ["reason"],
        )

        # ----------------------------------------------------------------
        # Gauge Metrics
        # ----------------------------------------------------------------

        # Queue depth
        self.queue_depth = Gauge(
            f"{ns}_queue_depth",
            "Current queue depth",
            ["queue_name"],
        )

        # Active workers
        self.active_workers = Gauge(
            f"{ns}_active_workers",
            "Number of active workers",
            ["worker_type"],
        )

        # GPU memory usage
        self.gpu_memory_bytes = Gauge(
            f"{ns}_gpu_memory_bytes",
            "GPU memory usage in bytes",
            ["device_id"],
        )

        # Model loaded status
        self.model_loaded = Gauge(
            f"{ns}_model_loaded",
            "Whether model is loaded (1) or not (0)",
            ["model_name", "device"],
        )

        # ----------------------------------------------------------------
        # Cost Metrics
        # ----------------------------------------------------------------

        # Modal GPU seconds consumed
        self.modal_gpu_seconds = Counter(
            f"{ns}_modal_gpu_seconds_total",
            "Total Modal GPU seconds consumed",
            ["gpu_type"],
        )

        # Estimated cost
        self.estimated_cost_dollars = Counter(
            f"{ns}_estimated_cost_dollars_total",
            "Estimated cost in dollars",
            ["cost_type"],
        )

        # ----------------------------------------------------------------
        # Quality Metrics
        # ----------------------------------------------------------------

        # Quality score distribution
        self.quality_score = Histogram(
            f"{ns}_quality_score",
            "Document quality score distribution",
            ["gate_result"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

        # Escalation rate gauge (for dashboard)
        self.escalation_rate = Gauge(
            f"{ns}_escalation_rate",
            "Current teacher escalation rate (0-1)",
        )

        # ----------------------------------------------------------------
        # Info Metric
        # ----------------------------------------------------------------

        self.build_info = Info(
            f"{ns}_build",
            "Build information",
        )

    @property
    def config(self) -> MetricsConfig:
        """Get the metrics configuration."""
        return self._config

    def set_build_info(
        self,
        version: str,
        git_commit: str = "",
        build_time: str = "",
    ) -> None:
        """Set build information.

        Args:
            version: Application version.
            git_commit: Git commit hash.
            build_time: Build timestamp.
        """
        self.build_info.info(
            {
                "version": version,
                "git_commit": git_commit,
                "build_time": build_time,
            }
        )

    # ----------------------------------------------------------------
    # Convenience Methods
    # ----------------------------------------------------------------

    def record_page_processed(
        self,
        status: str,
        gate_result: str,
        duration_seconds: float,
        device: str,
        model: str,
    ) -> None:
        """Record a processed page.

        Args:
            status: Processing status (success, error).
            gate_result: Gate decision (text_detected, no_text).
            duration_seconds: Processing duration.
            device: Device used (cpu, gpu, modal).
            model: Model used (student, teacher).
        """
        self.pages_processed.labels(status=status, gate_result=gate_result).inc()
        self.processing_latency.labels(
            operation="page", device=device, model=model
        ).observe(duration_seconds)

    def record_error(self, error_code: str, category: str) -> None:
        """Record an error.

        Args:
            error_code: Error code (e.g., E2001).
            category: Error category (e.g., processing).
        """
        sanitized_code = self._error_guard.sanitize(error_code)
        self.errors.labels(error_code=sanitized_code, category=category).inc()

    def record_teacher_usage(
        self,
        reason: str,
        device: str,
        duration_seconds: float,
        blocked: bool = False,
        blocked_reason: str = "",
    ) -> None:
        """Record teacher model usage.

        Args:
            reason: Reason for teacher invocation.
            device: Device used.
            duration_seconds: Processing duration.
            blocked: Whether invocation was blocked.
            blocked_reason: Reason for blocking.
        """
        if blocked:
            self.teacher_blocked.labels(reason=blocked_reason).inc()
        else:
            self.teacher_invocations.labels(reason=reason, device=device).inc()
            self.iqa_latency.labels(model="teacher", device=device).observe(
                duration_seconds
            )

            # Track Modal costs
            if device == "modal":
                self.modal_gpu_seconds.labels(gpu_type="T4").inc(duration_seconds)
                cost = duration_seconds * self._config.modal_cost_per_gpu_second
                self.estimated_cost_dollars.labels(cost_type="modal_gpu").inc(cost)

    def record_correction(self, correction_type: str, duration_seconds: float) -> None:
        """Record a correction operation.

        Args:
            correction_type: Type of correction (deskew, contrast, etc).
            duration_seconds: Processing duration.
        """
        self.corrections_applied.labels(correction_type=correction_type).inc()
        self.correction_latency.labels(correction_type=correction_type).observe(
            duration_seconds
        )

    def record_quality_score(self, score: float, gate_result: str) -> None:
        """Record a quality score.

        Args:
            score: Quality score (0-1).
            gate_result: Gate decision.
        """
        self.quality_score.labels(gate_result=gate_result).observe(score)

    def set_queue_depth(self, queue_name: str, depth: int) -> None:
        """Set current queue depth.

        Args:
            queue_name: Name of the queue.
            depth: Current depth.
        """
        self.queue_depth.labels(queue_name=queue_name).set(depth)

    def set_active_workers(self, worker_type: str, count: int) -> None:
        """Set active worker count.

        Args:
            worker_type: Type of worker.
            count: Number of active workers.
        """
        self.active_workers.labels(worker_type=worker_type).set(count)

    @contextmanager
    def time_operation(
        self,
        operation: str,
        device: str = "cpu",
        model: str = "student",
    ) -> Generator[None, None, None]:
        """Context manager to time an operation.

        Args:
            operation: Operation name.
            device: Device used.
            model: Model used.

        Yields:
            None
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.processing_latency.labels(
                operation=operation, device=device, model=model
            ).observe(duration)

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format.

        Returns:
            Metrics as bytes.
        """
        if not PROMETHEUS_AVAILABLE:
            return b"# prometheus_client not installed\n"
        return generate_latest(self._registry)  # type: ignore[arg-type]

    def start_server(self, port: int | None = None) -> None:
        """Start the metrics HTTP server.

        Args:
            port: Port to listen on.
        """
        if not PROMETHEUS_AVAILABLE:
            return

        server_port = port or self._config.port
        start_http_server(server_port, registry=self._registry)  # type: ignore[arg-type]


# ============================================================================
# Module-Level Convenience Functions
# ============================================================================

# Global metrics instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector instance.
    """
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def record_page_processed(
    status: str,
    gate_result: str,
    duration_seconds: float,
    device: str = "cpu",
    model: str = "student",
) -> None:
    """Record a processed page."""
    get_metrics().record_page_processed(
        status, gate_result, duration_seconds, device, model
    )


def record_error(error_code: str, category: str) -> None:
    """Record an error."""
    get_metrics().record_error(error_code, category)


def record_teacher_usage(
    reason: str,
    device: str,
    duration_seconds: float,
    blocked: bool = False,
    blocked_reason: str = "",
) -> None:
    """Record teacher model usage."""
    get_metrics().record_teacher_usage(
        reason, device, duration_seconds, blocked, blocked_reason
    )


def record_correction(correction_type: str, duration_seconds: float) -> None:
    """Record a correction operation."""
    get_metrics().record_correction(correction_type, duration_seconds)


def record_quality_score(score: float, gate_result: str) -> None:
    """Record a quality score."""
    get_metrics().record_quality_score(score, gate_result)


T = TypeVar("T")


def timed(
    operation: str,
    device: str = "cpu",
    model: str = "student",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to time a function.

    Args:
        operation: Operation name.
        device: Device used.
        model: Model used.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with get_metrics().time_operation(operation, device, model):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Metrics HTTP Handler (for ASGI/WSGI integration)
# ============================================================================


def metrics_endpoint() -> tuple[bytes, str]:
    """Generate metrics response for HTTP endpoint.

    Returns:
        Tuple of (content, content_type).
    """
    content = get_metrics().get_metrics()
    content_type = "text/plain; version=0.0.4; charset=utf-8"
    return content, content_type
