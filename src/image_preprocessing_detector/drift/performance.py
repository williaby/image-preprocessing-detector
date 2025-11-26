"""Model performance monitoring job - Sprint 6.3.2.

Periodic evaluation on change-detection set with mAP/F1 tracking.

This module provides:
- PerformanceEvaluator: Evaluates model on test sets
- MetricsStore: Persists evaluation results
- PerformanceJob: Scheduled evaluation job
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from image_preprocessing_detector.utils.datetime_compat import ensure_aware, utc_now

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_EVALUATION_INTERVAL_HOURS = 24
DEFAULT_RETENTION_DAYS = 90
MAP_DROP_WARNING_THRESHOLD = 0.03  # 3%
MAP_DROP_CRITICAL_THRESHOLD = 0.05  # 5%
F1_DROP_WARNING_THRESHOLD = 0.03
F1_DROP_CRITICAL_THRESHOLD = 0.05


class MetricType(Enum):
    """Types of performance metrics tracked."""

    MAP = "mAP"  # Mean Average Precision
    MAP_50 = "mAP@50"  # mAP at IoU 0.5
    MAP_75 = "mAP@75"  # mAP at IoU 0.75
    F1 = "F1"
    PRECISION = "precision"
    RECALL = "recall"
    ACCURACY = "accuracy"
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"


class AlertSeverity(Enum):
    """Severity levels for performance alerts."""

    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class EvaluationResult:
    """Result of a single evaluation run."""

    timestamp: datetime
    model_version: str
    dataset_name: str
    dataset_version: str
    metrics: dict[str, float]
    sample_count: int
    evaluation_duration_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_version": self.model_version,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "metrics": self.metrics,
            "sample_count": self.sample_count,
            "evaluation_duration_seconds": self.evaluation_duration_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationResult:
        """Create from dictionary."""
        return cls(
            timestamp=ensure_aware(datetime.fromisoformat(data["timestamp"])),
            model_version=data["model_version"],
            dataset_name=data["dataset_name"],
            dataset_version=data["dataset_version"],
            metrics=data["metrics"],
            sample_count=data["sample_count"],
            evaluation_duration_seconds=data["evaluation_duration_seconds"],
            metadata=data.get("metadata", {}),
        )

    def get_metric(self, metric: MetricType | str) -> float | None:
        """Get a specific metric value."""
        key = metric.value if isinstance(metric, MetricType) else metric
        return self.metrics.get(key)


@dataclass
class PerformanceTrend:
    """Performance trend analysis over time."""

    metric: str
    current_value: float
    baseline_value: float
    change_absolute: float
    change_percent: float
    trend_direction: str  # "improving", "stable", "degrading"
    severity: AlertSeverity
    history: list[tuple[datetime, float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.metric,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "change_absolute": self.change_absolute,
            "change_percent": self.change_percent,
            "trend_direction": self.trend_direction,
            "severity": self.severity.value,
            "history": [(ts.isoformat(), v) for ts, v in self.history[-30:]],
        }


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""

    timestamp: datetime
    model_version: str
    current_evaluation: EvaluationResult
    baseline_evaluation: EvaluationResult | None
    trends: list[PerformanceTrend]
    alerts: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_version": self.model_version,
            "current_evaluation": self.current_evaluation.to_dict(),
            "baseline_evaluation": (
                self.baseline_evaluation.to_dict() if self.baseline_evaluation else None
            ),
            "trends": [t.to_dict() for t in self.trends],
            "alerts": self.alerts,
        }


@dataclass
class JobConfig:
    """Configuration for performance monitoring job."""

    dataset_path: str
    model_path: str
    evaluation_interval_hours: int = DEFAULT_EVALUATION_INTERVAL_HOURS
    retention_days: int = DEFAULT_RETENTION_DAYS
    metrics_to_track: list[str] = field(
        default_factory=lambda: [
            MetricType.MAP.value,
            MetricType.F1.value,
            MetricType.PRECISION.value,
            MetricType.RECALL.value,
        ]
    )
    baseline_window_days: int = 7
    alert_on_degradation: bool = True
    map_drop_warning: float = MAP_DROP_WARNING_THRESHOLD
    map_drop_critical: float = MAP_DROP_CRITICAL_THRESHOLD
    f1_drop_warning: float = F1_DROP_WARNING_THRESHOLD
    f1_drop_critical: float = F1_DROP_CRITICAL_THRESHOLD

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dataset_path": self.dataset_path,
            "model_path": self.model_path,
            "evaluation_interval_hours": self.evaluation_interval_hours,
            "retention_days": self.retention_days,
            "metrics_to_track": self.metrics_to_track,
            "baseline_window_days": self.baseline_window_days,
            "alert_on_degradation": self.alert_on_degradation,
            "map_drop_warning": self.map_drop_warning,
            "map_drop_critical": self.map_drop_critical,
            "f1_drop_warning": self.f1_drop_warning,
            "f1_drop_critical": self.f1_drop_critical,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobConfig:
        """Create from dictionary."""
        return cls(
            dataset_path=data["dataset_path"],
            model_path=data["model_path"],
            evaluation_interval_hours=data.get(
                "evaluation_interval_hours", DEFAULT_EVALUATION_INTERVAL_HOURS
            ),
            retention_days=data.get("retention_days", DEFAULT_RETENTION_DAYS),
            metrics_to_track=data.get(
                "metrics_to_track",
                [MetricType.MAP.value, MetricType.F1.value],
            ),
            baseline_window_days=data.get("baseline_window_days", 7),
            alert_on_degradation=data.get("alert_on_degradation", True),
            map_drop_warning=data.get("map_drop_warning", MAP_DROP_WARNING_THRESHOLD),
            map_drop_critical=data.get(
                "map_drop_critical", MAP_DROP_CRITICAL_THRESHOLD
            ),
            f1_drop_warning=data.get("f1_drop_warning", F1_DROP_WARNING_THRESHOLD),
            f1_drop_critical=data.get("f1_drop_critical", F1_DROP_CRITICAL_THRESHOLD),
        )

    def validate(self) -> list[str]:
        """Validate configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.dataset_path:
            errors.append("dataset_path is required")

        if not self.model_path:
            errors.append("model_path is required")

        if self.evaluation_interval_hours < 1:
            errors.append("evaluation_interval_hours must be >= 1")

        if self.retention_days < 1:
            errors.append("retention_days must be >= 1")

        if not self.metrics_to_track:
            errors.append("metrics_to_track must not be empty")

        if self.map_drop_warning >= self.map_drop_critical:
            errors.append("map_drop_warning must be < map_drop_critical")

        if self.f1_drop_warning >= self.f1_drop_critical:
            errors.append("f1_drop_warning must be < f1_drop_critical")

        return errors


# ============================================================================
# Protocols
# ============================================================================


class ModelEvaluatorProtocol(Protocol):
    """Protocol for model evaluation."""

    def evaluate(
        self,
        model_path: str,
        dataset_path: str,
    ) -> dict[str, float]:
        """Evaluate model on dataset, returning metrics dict."""
        pass  # Protocol method stub


# ============================================================================
# Metrics Store
# ============================================================================


class MetricsStore:
    """Persistent storage for evaluation metrics.

    Stores evaluation results and provides trend analysis.
    """

    def __init__(
        self,
        storage_path: str | Path,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ):
        """Initialize metrics store.

        Args:
            storage_path: Directory for metric storage
            retention_days: Days to retain historical data
        """
        self.storage_path = Path(storage_path)
        self.retention_days = retention_days
        self._results: list[EvaluationResult] = []

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing results
        self._load_results()

    def _load_results(self) -> None:
        """Load historical results from storage."""
        results_file = self.storage_path / "evaluation_history.json"

        if results_file.exists():
            try:
                with open(results_file) as f:
                    data = json.load(f)

                for item in data:
                    result = EvaluationResult.from_dict(item)
                    # Skip expired results
                    cutoff = utc_now() - timedelta(days=self.retention_days)
                    if result.timestamp > cutoff:
                        self._results.append(result)

                logger.info(
                    f"Loaded {len(self._results)} historical evaluation results"
                )

            except (json.JSONDecodeError, KeyError, ValueError):
                logger.exception("Error loading evaluation history")

    def _save_results(self) -> None:
        """Save results to storage."""
        results_file = self.storage_path / "evaluation_history.json"

        data = [r.to_dict() for r in self._results]
        with open(results_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_result(self, result: EvaluationResult) -> None:
        """Add an evaluation result.

        Args:
            result: Evaluation result to store
        """
        self._results.append(result)
        self._results.sort(key=lambda r: r.timestamp)
        self._save_results()
        logger.info(
            f"Stored evaluation result for {result.model_version} "
            f"on {result.dataset_name}"
        )

    def get_latest(
        self,
        model_version: str | None = None,
        dataset_name: str | None = None,
    ) -> EvaluationResult | None:
        """Get latest evaluation result.

        Args:
            model_version: Filter by model version
            dataset_name: Filter by dataset name

        Returns:
            Latest matching result or None
        """
        filtered = self._filter_results(model_version, dataset_name)
        return filtered[-1] if filtered else None

    def get_baseline(
        self,
        window_days: int = 7,
        model_version: str | None = None,
        dataset_name: str | None = None,
    ) -> EvaluationResult | None:
        """Get baseline evaluation (average of window period).

        Args:
            window_days: Days to include in baseline window
            model_version: Filter by model version
            dataset_name: Filter by dataset name

        Returns:
            Baseline result (aggregated) or None
        """
        cutoff = utc_now() - timedelta(days=window_days)
        filtered = [
            r
            for r in self._filter_results(model_version, dataset_name)
            if r.timestamp > cutoff
        ]

        if not filtered:
            return None

        # Compute average metrics
        avg_metrics: dict[str, list[float]] = {}
        for result in filtered:
            for metric, value in result.metrics.items():
                if metric not in avg_metrics:
                    avg_metrics[metric] = []
                avg_metrics[metric].append(value)

        aggregated_metrics = {
            metric: np.mean(values) for metric, values in avg_metrics.items()
        }

        # Return aggregated baseline
        return EvaluationResult(
            timestamp=utc_now(),
            model_version=filtered[-1].model_version,
            dataset_name=filtered[-1].dataset_name,
            dataset_version="baseline_aggregate",
            metrics=aggregated_metrics,
            sample_count=sum(r.sample_count for r in filtered),
            evaluation_duration_seconds=0,
            metadata={
                "baseline_window_days": window_days,
                "result_count": len(filtered),
            },
        )

    def get_history(
        self,
        metric: str,
        days: int = 30,
        model_version: str | None = None,
        dataset_name: str | None = None,
    ) -> list[tuple[datetime, float]]:
        """Get metric history.

        Args:
            metric: Metric name to retrieve
            days: Number of days of history
            model_version: Filter by model version
            dataset_name: Filter by dataset name

        Returns:
            List of (timestamp, value) tuples
        """
        cutoff = utc_now() - timedelta(days=days)
        filtered = [
            r
            for r in self._filter_results(model_version, dataset_name)
            if r.timestamp > cutoff
        ]

        return [
            (r.timestamp, r.metrics.get(metric, 0.0))
            for r in filtered
            if metric in r.metrics
        ]

    def _filter_results(
        self,
        model_version: str | None,
        dataset_name: str | None,
    ) -> list[EvaluationResult]:
        """Filter results by model and dataset."""
        results = self._results

        if model_version:
            results = [r for r in results if r.model_version == model_version]

        if dataset_name:
            results = [r for r in results if r.dataset_name == dataset_name]

        return results

    def cleanup_old_results(self) -> int:
        """Remove results older than retention period.

        Returns:
            Number of results removed
        """
        cutoff = utc_now() - timedelta(days=self.retention_days)
        original_count = len(self._results)
        self._results = [r for r in self._results if r.timestamp > cutoff]

        removed = original_count - len(self._results)
        if removed > 0:
            self._save_results()
            logger.info(f"Cleaned up {removed} old evaluation results")

        return removed

    def get_result_count(self) -> int:
        """Get total number of stored results."""
        return len(self._results)

    def clear(self) -> None:
        """Clear all stored results."""
        self._results.clear()
        results_file = self.storage_path / "evaluation_history.json"
        if results_file.exists():
            results_file.unlink()


# ============================================================================
# Performance Evaluator
# ============================================================================


class PerformanceEvaluator:
    """Evaluates model performance and computes metrics.

    This is a stub implementation. In production, this would integrate
    with the actual model evaluation pipeline.
    """

    def __init__(
        self,
        metrics_store: MetricsStore,
        config: JobConfig,
    ):
        """Initialize evaluator.

        Args:
            metrics_store: Store for persisting results
            config: Job configuration
        """
        self.metrics_store = metrics_store
        self.config = config
        self._evaluator_fn: ModelEvaluatorProtocol | None = None

    def set_evaluator(self, evaluator: ModelEvaluatorProtocol) -> None:
        """Set the model evaluator function.

        Args:
            evaluator: Function that evaluates model and returns metrics
        """
        self._evaluator_fn = evaluator

    def evaluate(
        self,
        model_version: str = "unknown",
        dataset_version: str = "unknown",
    ) -> EvaluationResult:
        """Run evaluation and store results.

        Args:
            model_version: Version identifier for the model
            dataset_version: Version identifier for the dataset

        Returns:
            Evaluation result
        """
        import time

        start_time = time.time()

        # Run evaluation (stub or actual)
        if self._evaluator_fn:
            metrics = self._evaluator_fn.evaluate(
                self.config.model_path,
                self.config.dataset_path,
            )
        else:
            # Stub metrics for testing
            metrics = self._generate_stub_metrics()

        duration = time.time() - start_time

        # Create result
        result = EvaluationResult(
            timestamp=utc_now(),
            model_version=model_version,
            dataset_name=Path(self.config.dataset_path).name,
            dataset_version=dataset_version,
            metrics=metrics,
            sample_count=self._get_dataset_sample_count(),
            evaluation_duration_seconds=duration,
        )

        # Store result
        self.metrics_store.add_result(result)

        return result

    def _generate_stub_metrics(self) -> dict[str, float]:
        """Generate stub metrics for testing."""
        return {
            MetricType.MAP.value: 0.85 + np.random.normal(0, 0.02),
            MetricType.MAP_50.value: 0.90 + np.random.normal(0, 0.02),
            MetricType.MAP_75.value: 0.80 + np.random.normal(0, 0.02),
            MetricType.F1.value: 0.88 + np.random.normal(0, 0.02),
            MetricType.PRECISION.value: 0.87 + np.random.normal(0, 0.02),
            MetricType.RECALL.value: 0.89 + np.random.normal(0, 0.02),
            MetricType.ACCURACY.value: 0.92 + np.random.normal(0, 0.01),
        }

    def _get_dataset_sample_count(self) -> int:
        """Get sample count from dataset (stub)."""
        # In production, this would read from dataset metadata
        return 1000

    def analyze_trends(
        self,
        current: EvaluationResult,
        baseline_window_days: int = 7,
    ) -> list[PerformanceTrend]:
        """Analyze performance trends.

        Args:
            current: Current evaluation result
            baseline_window_days: Days for baseline window

        Returns:
            List of performance trends for each metric
        """
        baseline = self.metrics_store.get_baseline(
            window_days=baseline_window_days,
            dataset_name=current.dataset_name,
        )

        trends = []
        for metric in self.config.metrics_to_track:
            current_value = current.metrics.get(metric, 0.0)
            baseline_value = (
                baseline.metrics.get(metric, current_value)
                if baseline
                else current_value
            )

            change_absolute = current_value - baseline_value
            change_percent = (
                (change_absolute / baseline_value * 100) if baseline_value else 0.0
            )

            # Determine trend direction
            if abs(change_percent) < 1:
                direction = "stable"
            elif change_absolute > 0:
                direction = "improving"
            else:
                direction = "degrading"

            # Determine severity
            severity = self._compute_severity(metric, change_percent)

            # Get history
            history = self.metrics_store.get_history(
                metric=metric,
                days=30,
                dataset_name=current.dataset_name,
            )

            trends.append(
                PerformanceTrend(
                    metric=metric,
                    current_value=current_value,
                    baseline_value=baseline_value,
                    change_absolute=change_absolute,
                    change_percent=change_percent,
                    trend_direction=direction,
                    severity=severity,
                    history=history,
                )
            )

        return trends

    def _compute_severity(self, metric: str, change_percent: float) -> AlertSeverity:
        """Compute severity based on metric change."""
        # Negative change_percent means degradation for metrics where higher is better
        if change_percent >= 0:
            return AlertSeverity.NONE

        drop = abs(change_percent) / 100  # Convert to decimal

        if metric in [
            MetricType.MAP.value,
            MetricType.MAP_50.value,
            MetricType.MAP_75.value,
        ]:
            if drop >= self.config.map_drop_critical:
                return AlertSeverity.CRITICAL
            if drop >= self.config.map_drop_warning:
                return AlertSeverity.WARNING

        elif metric == MetricType.F1.value:
            if drop >= self.config.f1_drop_critical:
                return AlertSeverity.CRITICAL
            if drop >= self.config.f1_drop_warning:
                return AlertSeverity.WARNING

        return AlertSeverity.NONE

    def generate_report(
        self,
        current: EvaluationResult | None = None,
    ) -> PerformanceReport:
        """Generate comprehensive performance report.

        Args:
            current: Current evaluation (runs new evaluation if None)

        Returns:
            Performance report
        """
        if current is None:
            current = self.evaluate()

        baseline = self.metrics_store.get_baseline(
            window_days=self.config.baseline_window_days,
        )

        trends = self.analyze_trends(current, self.config.baseline_window_days)

        # Generate alerts for significant degradations
        alerts = [
            {
                "metric": trend.metric,
                "severity": trend.severity.value,
                "message": (
                    f"{trend.metric} degraded by {abs(trend.change_percent):.1f}% "
                    f"({trend.baseline_value:.3f} -> {trend.current_value:.3f})"
                ),
                "trend_direction": trend.trend_direction,
            }
            for trend in trends
            if trend.severity != AlertSeverity.NONE
        ]

        return PerformanceReport(
            timestamp=utc_now(),
            model_version=current.model_version,
            current_evaluation=current,
            baseline_evaluation=baseline,
            trends=trends,
            alerts=alerts,
        )


# ============================================================================
# Performance Job
# ============================================================================


class PerformanceJob:
    """Scheduled performance monitoring job.

    Runs periodic evaluations and generates reports.
    """

    def __init__(
        self,
        config: JobConfig,
        storage_path: str | Path,
    ):
        """Initialize job.

        Args:
            config: Job configuration
            storage_path: Directory for storing results
        """
        self.config = config
        self.storage_path = Path(storage_path)
        self.metrics_store = MetricsStore(
            self.storage_path / "metrics",
            retention_days=config.retention_days,
        )
        self.evaluator = PerformanceEvaluator(self.metrics_store, config)
        self._last_run: datetime | None = None
        self._running = False

    def should_run(self) -> bool:
        """Check if job should run based on schedule."""
        if self._last_run is None:
            return True

        next_run = self._last_run + timedelta(
            hours=self.config.evaluation_interval_hours
        )
        return utc_now() >= next_run

    def run(
        self,
        model_version: str = "unknown",
        dataset_version: str = "unknown",
        force: bool = False,
    ) -> PerformanceReport | None:
        """Run the evaluation job.

        Args:
            model_version: Model version identifier
            dataset_version: Dataset version identifier
            force: Force run even if not scheduled

        Returns:
            Performance report or None if skipped
        """
        if not force and not self.should_run():
            logger.info("Skipping evaluation - not yet scheduled")
            return None

        if self._running:
            logger.warning("Evaluation already in progress")
            return None

        try:
            self._running = True
            logger.info("Starting performance evaluation job")

            # Run evaluation
            result = self.evaluator.evaluate(model_version, dataset_version)

            # Generate report
            report = self.evaluator.generate_report(result)

            # Update last run time
            self._last_run = utc_now()

            # Save report
            self._save_report(report)

            # Log alerts
            for alert in report.alerts:
                if alert["severity"] == "critical":
                    logger.error(f"CRITICAL: {alert['message']}")
                elif alert["severity"] == "warning":
                    logger.warning(f"WARNING: {alert['message']}")

            logger.info("Performance evaluation job completed")
            return report

        finally:
            self._running = False

    def _save_report(self, report: PerformanceReport) -> None:
        """Save report to disk."""
        reports_dir = self.storage_path / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        filename = f"report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = reports_dir / filename

        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        # Also save as latest
        latest_path = reports_dir / "latest.json"
        with open(latest_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

    def get_latest_report(self) -> PerformanceReport | None:
        """Get the latest saved report."""
        latest_path = self.storage_path / "reports" / "latest.json"

        if not latest_path.exists():
            return None

        try:
            with open(latest_path) as f:
                data = json.load(f)

            return PerformanceReport(
                timestamp=ensure_aware(datetime.fromisoformat(data["timestamp"])),
                model_version=data["model_version"],
                current_evaluation=EvaluationResult.from_dict(
                    data["current_evaluation"]
                ),
                baseline_evaluation=(
                    EvaluationResult.from_dict(data["baseline_evaluation"])
                    if data.get("baseline_evaluation")
                    else None
                ),
                trends=[],  # Simplified - would need full deserialization
                alerts=data.get("alerts", []),
            )

        except (json.JSONDecodeError, KeyError):
            logger.exception("Error loading latest report")
            return None

    def cleanup(self) -> None:
        """Clean up old data."""
        self.metrics_store.cleanup_old_results()


# ============================================================================
# CI Validation
# ============================================================================


def validate_job_config(config_path: str | Path) -> tuple[bool, list[str]]:
    """Validate job configuration file.

    For use in CI hooks to ensure config is valid before deployment.

    Args:
        config_path: Path to configuration file

    Returns:
        Tuple of (is_valid, error_messages)
    """
    config_path = Path(config_path)

    if not config_path.exists():
        return False, [f"Configuration file not found: {config_path}"]

    try:
        with open(config_path) as f:
            data = json.load(f)

        config = JobConfig.from_dict(data)
        errors = config.validate()

        return len(errors) == 0, errors

    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    except KeyError as e:
        return False, [f"Missing required field: {e}"]


def create_sample_config(output_path: str | Path) -> None:
    """Create a sample configuration file.

    Args:
        output_path: Path to write sample config
    """
    config = JobConfig(
        dataset_path="/data/change_detection_set",
        model_path="/models/iqa_student.onnx",
        evaluation_interval_hours=24,
        retention_days=90,
        metrics_to_track=[
            MetricType.MAP.value,
            MetricType.F1.value,
            MetricType.PRECISION.value,
            MetricType.RECALL.value,
        ],
        baseline_window_days=7,
        alert_on_degradation=True,
    )

    with open(output_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)


# ============================================================================
# Dashboard Panel Data
# ============================================================================


def get_dashboard_panel_data(
    metrics_store: MetricsStore,
    metrics: list[str] | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """Get data formatted for Grafana dashboard panel.

    Args:
        metrics_store: Metrics store to query
        metrics: Specific metrics to include (None for all)
        days: Days of history to include

    Returns:
        Dictionary formatted for dashboard consumption
    """
    if metrics is None:
        metrics = [
            MetricType.MAP.value,
            MetricType.F1.value,
            MetricType.PRECISION.value,
            MetricType.RECALL.value,
        ]

    panel_data: dict[str, Any] = {
        "generated_at": utc_now().isoformat(),
        "time_range_days": days,
        "metrics": {},
    }

    for metric in metrics:
        history = metrics_store.get_history(metric, days=days)

        if history:
            values = [v for _, v in history]
            panel_data["metrics"][metric] = {
                "current": values[-1] if values else 0.0,
                "min": min(values) if values else 0.0,
                "max": max(values) if values else 0.0,
                "avg": np.mean(values) if values else 0.0,
                "data_points": len(history),
                "history": [
                    {"timestamp": ts.isoformat(), "value": v} for ts, v in history
                ],
            }

    # Include latest evaluation summary
    latest = metrics_store.get_latest()
    if latest:
        panel_data["latest_evaluation"] = {
            "timestamp": latest.timestamp.isoformat(),
            "model_version": latest.model_version,
            "dataset_name": latest.dataset_name,
            "sample_count": latest.sample_count,
        }

    return panel_data


__all__ = [
    "DEFAULT_EVALUATION_INTERVAL_HOURS",
    "DEFAULT_RETENTION_DAYS",
    "F1_DROP_CRITICAL_THRESHOLD",
    "F1_DROP_WARNING_THRESHOLD",
    "MAP_DROP_CRITICAL_THRESHOLD",
    "MAP_DROP_WARNING_THRESHOLD",
    "AlertSeverity",
    "EvaluationResult",
    "JobConfig",
    "MetricType",
    "MetricsStore",
    "PerformanceEvaluator",
    "PerformanceJob",
    "PerformanceReport",
    "PerformanceTrend",
    "create_sample_config",
    "get_dashboard_panel_data",
    "validate_job_config",
]
