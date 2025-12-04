"""Pipeline integration module for drift detection and monitoring.

Sprint 6.3.x: Integrates drift detection and Prometheus metrics
into the document processing pipeline.

This module provides:
- PipelineHooks: Central integration point for monitoring and drift detection
- Automatic metric recording during document processing
- Distribution tracking for drift detection
- Periodic drift checks with alerting
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Any

import structlog

from image_preprocessing_detector.drift import (
    DEFAULT_SAMPLE_RATE,
    DriftResult,
    DriftSeverity,
    FeatureType,
    create_drift_detector,
    create_tracker,
)
from image_preprocessing_detector.drift.alerting import (
    AlertManager,
    check_drift_and_alert,
)
from image_preprocessing_detector.monitoring import (
    MetricsCollector,
    get_metrics,
    record_correction,
    record_error,
    record_page_processed,
    record_quality_score,
    record_teacher_usage,
)

if TYPE_CHECKING:
    from image_preprocessing_detector.drift import (
        DistributionTracker,
        DriftDetector,
    )

logger = structlog.get_logger(__name__)


@dataclass
class ProcessingContext:
    """Context for a single document processing operation."""

    document_id: str
    start_time: float = field(default_factory=time.perf_counter)
    page_count: int = 0
    errors: list[str] = field(default_factory=list)
    corrections_applied: list[str] = field(default_factory=list)
    teacher_used: bool = False
    teacher_reason: str = ""
    device_used: str = "cpu"
    gate_result: str = "unknown"
    quality_scores: list[float] = field(default_factory=list)


@dataclass
class PipelineMetrics:
    """Aggregated metrics for pipeline monitoring."""

    total_pages_processed: int = 0
    total_errors: int = 0
    total_corrections: int = 0
    teacher_invocations: int = 0
    avg_quality_score: float = 0.0
    avg_processing_time_ms: float = 0.0
    drift_warnings: int = 0
    drift_critical: int = 0


class PipelineHooks:
    """Central integration point for monitoring and drift detection.

    This class provides hooks that should be called during document processing
    to record metrics and track distributions for drift detection.

    Example usage:
        hooks = get_pipeline_hooks()

        # Start processing a document
        ctx = hooks.start_document("doc-123")

        # After processing each page
        hooks.record_page(ctx, quality_score=0.85, gate_result="text_detected")

        # After applying corrections
        hooks.record_correction(ctx, "deskew", duration_ms=15.0)

        # If teacher model was used
        hooks.record_teacher_use(ctx, reason="uncertainty", duration_ms=30.0)

        # When document processing completes
        hooks.finish_document(ctx, success=True)

        # Periodic drift check (e.g., hourly)
        drift_results = hooks.check_drift()
    """

    _instance: PipelineHooks | None = None
    _lock: Lock = Lock()

    def __new__(cls) -> PipelineHooks:
        """Singleton pattern for global access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize pipeline hooks with default settings."""
        if getattr(self, "_initialized", False):
            return

        self._sample_rate = DEFAULT_SAMPLE_RATE
        self._enable_drift = True
        self._enable_metrics = True

        # Initialize components
        self._tracker: DistributionTracker | None = None
        self._detector: DriftDetector | None = None
        self._alert_manager: AlertManager | None = None
        self._metrics: MetricsCollector | None = None

        self._tracker = create_tracker(sample_rate=self._sample_rate)
        self._detector = create_drift_detector()
        self._metrics = get_metrics()

        # Aggregated metrics
        self._pipeline_metrics = PipelineMetrics()
        self._metrics_lock = Lock()

        self._initialized = True

        logger.info(
            "pipeline_hooks_initialized",
            drift_enabled=self._enable_drift,
            metrics_enabled=self._enable_metrics,
            sample_rate=self._sample_rate,
        )

    def configure(
        self,
        sample_rate: float | None = None,
        enable_drift_detection: bool | None = None,
        enable_metrics: bool | None = None,
        alert_manager: AlertManager | None = None,
    ) -> None:
        """Configure pipeline hooks after initialization.

        Args:
            sample_rate: Sampling rate for drift detection (0.0 to 1.0).
            enable_drift_detection: Whether to enable drift detection.
            enable_metrics: Whether to enable Prometheus metrics.
            alert_manager: Optional AlertManager for drift alerting.
        """
        if sample_rate is not None:
            self._sample_rate = sample_rate
            if self._tracker:
                self._tracker = create_tracker(sample_rate=sample_rate)

        if enable_drift_detection is not None:
            self._enable_drift = enable_drift_detection
            if not enable_drift_detection:
                self._tracker = None
                self._detector = None
            elif self._tracker is None:
                self._tracker = create_tracker(sample_rate=self._sample_rate)
                self._detector = create_drift_detector()

        if enable_metrics is not None:
            self._enable_metrics = enable_metrics

        if alert_manager is not None:
            self._alert_manager = alert_manager

    def start_document(
        self, document_id: str, device: str = "cpu"
    ) -> ProcessingContext:
        """Start processing a document.

        Args:
            document_id: Unique document identifier.
            device: Device being used (cpu, gpu, modal).

        Returns:
            ProcessingContext to track the document's processing.
        """
        ctx = ProcessingContext(
            document_id=document_id,
            device_used=device,
        )

        logger.debug(
            "document_processing_started",
            document_id=document_id,
            device=device,
        )

        return ctx

    def record_page(
        self,
        ctx: ProcessingContext,
        quality_score: float,
        gate_result: str,
        blur_score: float | None = None,
        noise_score: float | None = None,
        contrast_score: float | None = None,
        skew_angle: float | None = None,
        processing_time_ms: float | None = None,
    ) -> None:
        """Record metrics for a processed page.

        Args:
            ctx: Processing context for the document.
            quality_score: Overall quality score (0-1).
            gate_result: Text gate result (text_detected, no_text).
            blur_score: Blur score (0-1), optional.
            noise_score: Noise score (0-1), optional.
            contrast_score: Contrast score (0-1), optional.
            skew_angle: Detected skew angle in degrees, optional.
            processing_time_ms: Processing time in milliseconds, optional.
        """
        ctx.page_count += 1
        ctx.gate_result = gate_result
        ctx.quality_scores.append(quality_score)

        # Record Prometheus metrics
        if self._enable_metrics and self._metrics:
            duration_sec = (processing_time_ms or 0) / 1000.0
            record_page_processed(
                status="success",
                gate_result=gate_result,
                duration_seconds=duration_sec,
                device=ctx.device_used,
                model="student",
            )
            record_quality_score(quality_score, gate_result)

        # Track distributions for drift detection
        if self._enable_drift and self._tracker:
            self._tracker.add_sample(FeatureType.QUALITY_SCORE, quality_score)

            if blur_score is not None:
                self._tracker.add_sample(FeatureType.BLUR_SCORE, blur_score)
            if noise_score is not None:
                self._tracker.add_sample(FeatureType.NOISE_LEVEL, noise_score)
            if contrast_score is not None:
                self._tracker.add_sample(FeatureType.CONTRAST_SCORE, contrast_score)
            if skew_angle is not None:
                self._tracker.add_sample(FeatureType.SKEW_ANGLE, skew_angle)
            if processing_time_ms is not None:
                self._tracker.add_sample(
                    FeatureType.PROCESSING_TIME, processing_time_ms / 1000.0
                )

    def record_page_error(
        self,
        ctx: ProcessingContext,
        error_code: str,
        category: str,
    ) -> None:
        """Record an error during page processing.

        Args:
            ctx: Processing context for the document.
            error_code: Error code (e.g., E2001).
            category: Error category (e.g., processing, infrastructure).
        """
        ctx.errors.append(error_code)

        if self._enable_metrics:
            record_error(error_code, category)

        with self._metrics_lock:
            self._pipeline_metrics.total_errors += 1

    def record_correction_applied(
        self,
        ctx: ProcessingContext,
        correction_type: str,
        duration_ms: float,
    ) -> None:
        """Record a correction that was applied.

        Args:
            ctx: Processing context for the document.
            correction_type: Type of correction (deskew, contrast, etc.).
            duration_ms: Time taken in milliseconds.
        """
        ctx.corrections_applied.append(correction_type)

        if self._enable_metrics:
            record_correction(correction_type, duration_ms / 1000.0)

        with self._metrics_lock:
            self._pipeline_metrics.total_corrections += 1

    def record_teacher_use(
        self,
        ctx: ProcessingContext,
        reason: str,
        duration_ms: float,
        device: str = "gpu",
        blocked: bool = False,
        blocked_reason: str = "",
    ) -> None:
        """Record teacher model usage.

        Args:
            ctx: Processing context for the document.
            reason: Reason for teacher invocation.
            duration_ms: Time taken in milliseconds.
            device: Device used (gpu, modal).
            blocked: Whether the invocation was blocked.
            blocked_reason: Reason for blocking.
        """
        ctx.teacher_used = True
        ctx.teacher_reason = reason

        if self._enable_metrics:
            record_teacher_usage(
                reason=reason,
                device=device,
                duration_seconds=duration_ms / 1000.0,
                blocked=blocked,
                blocked_reason=blocked_reason,
            )

        # Track escalation rate for drift detection
        if self._enable_drift and self._tracker and not blocked:
            self._tracker.add_sample(FeatureType.ESCALATION_RATE, 1.0)

        with self._metrics_lock:
            if not blocked:
                self._pipeline_metrics.teacher_invocations += 1

    def finish_document(
        self,
        ctx: ProcessingContext,
        success: bool = True,
    ) -> float:
        """Finish processing a document.

        Args:
            ctx: Processing context for the document.
            success: Whether processing succeeded.

        Returns:
            Total processing time in milliseconds.
        """
        elapsed_ms = (time.perf_counter() - ctx.start_time) * 1000

        # Update pipeline metrics
        with self._metrics_lock:
            self._pipeline_metrics.total_pages_processed += ctx.page_count
            if ctx.quality_scores:
                avg_quality = sum(ctx.quality_scores) / len(ctx.quality_scores)
                # Running average
                n = self._pipeline_metrics.total_pages_processed
                if n > 0:
                    old_avg = self._pipeline_metrics.avg_quality_score
                    self._pipeline_metrics.avg_quality_score = (
                        old_avg * (n - 1) + avg_quality
                    ) / n

        status = "success" if success else "error"
        logger.info(
            "document_processing_finished",
            document_id=ctx.document_id,
            status=status,
            page_count=ctx.page_count,
            errors=len(ctx.errors),
            corrections=len(ctx.corrections_applied),
            teacher_used=ctx.teacher_used,
            elapsed_ms=elapsed_ms,
        )

        return elapsed_ms

    def _update_drift_metrics(self, severity: DriftSeverity) -> None:
        """Update pipeline metrics for a drift result.

        Args:
            severity: The severity of the detected drift.
        """
        with self._metrics_lock:
            if severity == DriftSeverity.WARNING:
                self._pipeline_metrics.drift_warnings += 1
            elif severity == DriftSeverity.CRITICAL:
                self._pipeline_metrics.drift_critical += 1

    def check_drift(self) -> list[DriftResult]:
        """Check for drift in tracked feature distributions.

        This should be called periodically (e.g., hourly) to detect
        distribution shifts.

        Returns:
            List of DriftResult objects for features with detected drift.
        """
        if not self._enable_drift or not self._tracker or not self._detector:
            return []

        drift_results = self._detector.detect_drift_from_tracker(self._tracker)

        significant_results: list[DriftResult] = []
        kl_values: dict[str, float] = {}
        psi_values: dict[str, float] = {}

        for result in drift_results:
            if result.severity == DriftSeverity.NONE:
                continue

            significant_results.append(result)
            kl_values[result.feature] = result.kl_divergence
            psi_values[result.feature] = result.psi

            self._update_drift_metrics(result.severity)

            logger.warning(
                "drift_detected",
                feature=result.feature,
                severity=result.severity.value,
                kl_divergence=result.kl_divergence,
                psi=result.psi,
            )

        if self._alert_manager and (kl_values or psi_values):
            check_drift_and_alert(
                self._alert_manager,
                kl_values=kl_values if kl_values else None,
                psi_values=psi_values if psi_values else None,
            )

        return significant_results

    def save_reference_distributions(self) -> None:
        """Save current distributions as reference for future drift detection.

        This should be called periodically (e.g., monthly) to update
        reference distributions.
        """
        if not self._enable_drift or not self._tracker or not self._detector:
            return

        # Get tracked features and save their distributions
        tracked = self._tracker.get_tracked_features()
        for feature_name in tracked:
            # Compute histogram and stats for the feature
            histogram, bin_edges = self._tracker.compute_histogram(feature_name)
            stats = self._tracker.compute_stats(feature_name)

            if stats.count > 0:
                self._detector.reference_store.save_reference(
                    feature=feature_name,
                    histogram=histogram,
                    bin_edges=bin_edges,
                    stats=stats,
                    sample_count=stats.count,
                )

        logger.info("reference_distributions_updated", features=list(tracked))

    def get_pipeline_metrics(self) -> PipelineMetrics:
        """Get aggregated pipeline metrics.

        Returns:
            Current PipelineMetrics snapshot.
        """
        with self._metrics_lock:
            return PipelineMetrics(
                total_pages_processed=self._pipeline_metrics.total_pages_processed,
                total_errors=self._pipeline_metrics.total_errors,
                total_corrections=self._pipeline_metrics.total_corrections,
                teacher_invocations=self._pipeline_metrics.teacher_invocations,
                avg_quality_score=self._pipeline_metrics.avg_quality_score,
                avg_processing_time_ms=self._pipeline_metrics.avg_processing_time_ms,
                drift_warnings=self._pipeline_metrics.drift_warnings,
                drift_critical=self._pipeline_metrics.drift_critical,
            )

    def reset_metrics(self) -> None:
        """Reset aggregated pipeline metrics."""
        with self._metrics_lock:
            self._pipeline_metrics = PipelineMetrics()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (primarily for testing)."""
        with cls._lock:
            cls._instance = None


# Module-level convenience functions


def get_pipeline_hooks() -> PipelineHooks:
    """Get the global PipelineHooks instance.

    Returns:
        PipelineHooks singleton instance.
    """
    return PipelineHooks()


def start_document_processing(
    document_id: str,
    device: str = "cpu",
) -> ProcessingContext:
    """Start processing a document.

    Args:
        document_id: Unique document identifier.
        device: Device being used.

    Returns:
        ProcessingContext for tracking.
    """
    return get_pipeline_hooks().start_document(document_id, device)


def record_page_metrics(
    ctx: ProcessingContext,
    quality_score: float,
    gate_result: str,
    **kwargs: Any,
) -> None:
    """Record metrics for a processed page.

    Args:
        ctx: Processing context.
        quality_score: Overall quality score.
        gate_result: Text gate result.
        **kwargs: Additional metrics (blur_score, noise_score, etc.).
    """
    get_pipeline_hooks().record_page(ctx, quality_score, gate_result, **kwargs)


def finish_document_processing(
    ctx: ProcessingContext,
    success: bool = True,
) -> float:
    """Finish processing a document.

    Args:
        ctx: Processing context.
        success: Whether processing succeeded.

    Returns:
        Total processing time in milliseconds.
    """
    return get_pipeline_hooks().finish_document(ctx, success)


def run_drift_check() -> list[DriftResult]:
    """Run drift detection check.

    Returns:
        List of drift results.
    """
    return get_pipeline_hooks().check_drift()


__all__ = [
    "PipelineHooks",
    "PipelineMetrics",
    "ProcessingContext",
    "finish_document_processing",
    "get_pipeline_hooks",
    "record_page_metrics",
    "run_drift_check",
    "start_document_processing",
]
