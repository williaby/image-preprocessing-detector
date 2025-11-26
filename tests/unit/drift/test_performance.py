"""Tests for model performance monitoring - Sprint 6.3.2.

Tests for metrics storage, evaluation, trend analysis, and job execution.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from image_preprocessing_detector.utils.datetime_compat import utc_now

from image_preprocessing_detector.drift.performance import (
    DEFAULT_EVALUATION_INTERVAL_HOURS,
    DEFAULT_RETENTION_DAYS,
    F1_DROP_CRITICAL_THRESHOLD,
    F1_DROP_WARNING_THRESHOLD,
    MAP_DROP_CRITICAL_THRESHOLD,
    MAP_DROP_WARNING_THRESHOLD,
    AlertSeverity,
    EvaluationResult,
    JobConfig,
    MetricsStore,
    MetricType,
    PerformanceEvaluator,
    PerformanceJob,
    PerformanceReport,
    PerformanceTrend,
    create_sample_config,
    get_dashboard_panel_data,
    validate_job_config,
)


# ============================================================================
# EvaluationResult Tests
# ============================================================================


class TestEvaluationResult:
    """Tests for EvaluationResult data class."""

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        result = EvaluationResult(
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            model_version="v1.0.0",
            dataset_name="test_dataset",
            dataset_version="v1",
            metrics={"mAP": 0.85, "F1": 0.88},
            sample_count=1000,
            evaluation_duration_seconds=120.5,
            metadata={"device": "gpu"},
        )

        d = result.to_dict()

        assert d["model_version"] == "v1.0.0"
        assert d["dataset_name"] == "test_dataset"
        assert d["metrics"]["mAP"] == 0.85
        assert d["sample_count"] == 1000
        assert d["metadata"]["device"] == "gpu"

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "timestamp": "2025-01-15T12:00:00",
            "model_version": "v1.0.0",
            "dataset_name": "test_dataset",
            "dataset_version": "v1",
            "metrics": {"mAP": 0.85},
            "sample_count": 1000,
            "evaluation_duration_seconds": 120.5,
        }

        result = EvaluationResult.from_dict(data)

        assert result.model_version == "v1.0.0"
        assert result.metrics["mAP"] == 0.85

    def test_get_metric(self) -> None:
        """Test getting specific metric."""
        result = EvaluationResult(
            timestamp=utc_now(),
            model_version="v1",
            dataset_name="test",
            dataset_version="v1",
            metrics={"mAP": 0.85, "F1": 0.88},
            sample_count=100,
            evaluation_duration_seconds=10,
        )

        assert result.get_metric(MetricType.MAP) == 0.85
        assert result.get_metric("F1") == 0.88
        assert result.get_metric("nonexistent") is None


# ============================================================================
# JobConfig Tests
# ============================================================================


class TestJobConfig:
    """Tests for JobConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = JobConfig(
            dataset_path="/data/test",
            model_path="/models/test.onnx",
        )

        assert config.evaluation_interval_hours == DEFAULT_EVALUATION_INTERVAL_HOURS
        assert config.retention_days == DEFAULT_RETENTION_DAYS
        assert config.alert_on_degradation is True

    def test_to_dict(self) -> None:
        """Test serialization."""
        config = JobConfig(
            dataset_path="/data/test",
            model_path="/models/test.onnx",
            evaluation_interval_hours=12,
        )

        d = config.to_dict()

        assert d["dataset_path"] == "/data/test"
        assert d["evaluation_interval_hours"] == 12

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "dataset_path": "/data/test",
            "model_path": "/models/test.onnx",
            "evaluation_interval_hours": 6,
        }

        config = JobConfig.from_dict(data)

        assert config.dataset_path == "/data/test"
        assert config.evaluation_interval_hours == 6

    def test_validate_valid_config(self) -> None:
        """Test validation of valid config."""
        config = JobConfig(
            dataset_path="/data/test",
            model_path="/models/test.onnx",
        )

        errors = config.validate()
        assert errors == []

    def test_validate_missing_dataset_path(self) -> None:
        """Test validation catches missing dataset path."""
        config = JobConfig(
            dataset_path="",
            model_path="/models/test.onnx",
        )

        errors = config.validate()
        assert "dataset_path is required" in errors

    def test_validate_missing_model_path(self) -> None:
        """Test validation catches missing model path."""
        config = JobConfig(
            dataset_path="/data/test",
            model_path="",
        )

        errors = config.validate()
        assert "model_path is required" in errors

    def test_validate_invalid_interval(self) -> None:
        """Test validation catches invalid interval."""
        config = JobConfig(
            dataset_path="/data/test",
            model_path="/models/test.onnx",
            evaluation_interval_hours=0,
        )

        errors = config.validate()
        assert "evaluation_interval_hours must be >= 1" in errors

    def test_validate_invalid_thresholds(self) -> None:
        """Test validation catches invalid thresholds."""
        config = JobConfig(
            dataset_path="/data/test",
            model_path="/models/test.onnx",
            map_drop_warning=0.10,
            map_drop_critical=0.05,  # Warning > Critical is invalid
        )

        errors = config.validate()
        assert "map_drop_warning must be < map_drop_critical" in errors


# ============================================================================
# MetricsStore Tests
# ============================================================================


class TestMetricsStore:
    """Tests for MetricsStore."""

    def test_add_and_get_result(self) -> None:
        """Test adding and retrieving results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            result = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1.0.0",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.85},
                sample_count=100,
                evaluation_duration_seconds=10,
            )

            store.add_result(result)

            latest = store.get_latest()
            assert latest is not None
            assert latest.model_version == "v1.0.0"

    def test_get_latest_filtered(self) -> None:
        """Test filtering results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            # Add results for different models
            for version in ["v1", "v2"]:
                result = EvaluationResult(
                    timestamp=utc_now(),
                    model_version=version,
                    dataset_name="test",
                    dataset_version="v1",
                    metrics={"mAP": 0.85},
                    sample_count=100,
                    evaluation_duration_seconds=10,
                )
                store.add_result(result)

            latest = store.get_latest(model_version="v1")
            assert latest is not None
            assert latest.model_version == "v1"

    def test_get_baseline(self) -> None:
        """Test computing baseline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            # Add multiple results
            for i, map_value in enumerate([0.80, 0.82, 0.84, 0.86, 0.88]):
                result = EvaluationResult(
                    timestamp=utc_now() - timedelta(days=i),
                    model_version="v1",
                    dataset_name="test",
                    dataset_version="v1",
                    metrics={"mAP": map_value},
                    sample_count=100,
                    evaluation_duration_seconds=10,
                )
                store.add_result(result)

            baseline = store.get_baseline(window_days=7)
            assert baseline is not None
            # Average of 0.80, 0.82, 0.84, 0.86, 0.88 = 0.84
            assert baseline.metrics["mAP"] == pytest.approx(0.84, rel=0.01)

    def test_get_history(self) -> None:
        """Test getting metric history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            # Add results over time
            for i in range(5):
                result = EvaluationResult(
                    timestamp=utc_now() - timedelta(days=i),
                    model_version="v1",
                    dataset_name="test",
                    dataset_version="v1",
                    metrics={"mAP": 0.80 + i * 0.02},
                    sample_count=100,
                    evaluation_duration_seconds=10,
                )
                store.add_result(result)

            history = store.get_history("mAP", days=7)
            assert len(history) == 5

    def test_cleanup_old_results(self) -> None:
        """Test cleanup of old results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir, retention_days=30)

            # Add old result
            old_result = EvaluationResult(
                timestamp=utc_now() - timedelta(days=60),
                model_version="v1",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.80},
                sample_count=100,
                evaluation_duration_seconds=10,
            )
            store._results.append(old_result)

            # Add recent result
            recent_result = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.85},
                sample_count=100,
                evaluation_duration_seconds=10,
            )
            store.add_result(recent_result)

            removed = store.cleanup_old_results()

            assert removed == 1
            assert store.get_result_count() == 1

    def test_persistence(self) -> None:
        """Test results are persisted to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Add result
            store1 = MetricsStore(tmpdir)
            result = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1.0.0",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.85},
                sample_count=100,
                evaluation_duration_seconds=10,
            )
            store1.add_result(result)

            # Create new store instance (should load from disk)
            store2 = MetricsStore(tmpdir)
            latest = store2.get_latest()

            assert latest is not None
            assert latest.model_version == "v1.0.0"

    def test_clear(self) -> None:
        """Test clearing all results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            result = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.85},
                sample_count=100,
                evaluation_duration_seconds=10,
            )
            store.add_result(result)

            store.clear()

            assert store.get_result_count() == 0
            assert store.get_latest() is None


# ============================================================================
# PerformanceEvaluator Tests
# ============================================================================


class TestPerformanceEvaluator:
    """Tests for PerformanceEvaluator."""

    def test_evaluate_stub(self) -> None:
        """Test evaluation with stub metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            store = MetricsStore(tmpdir)
            evaluator = PerformanceEvaluator(store, config)

            result = evaluator.evaluate(model_version="v1.0.0")

            assert result.model_version == "v1.0.0"
            assert "mAP" in result.metrics
            assert "F1" in result.metrics

    def test_evaluate_with_custom_evaluator(self) -> None:
        """Test evaluation with custom evaluator function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            store = MetricsStore(tmpdir)
            evaluator = PerformanceEvaluator(store, config)

            # Mock evaluator
            mock_eval = MagicMock()
            mock_eval.evaluate.return_value = {"mAP": 0.90, "F1": 0.92}
            evaluator.set_evaluator(mock_eval)

            result = evaluator.evaluate()

            assert result.metrics["mAP"] == 0.90
            assert result.metrics["F1"] == 0.92

    def test_analyze_trends_stable(self) -> None:
        """Test trend analysis with stable performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            store = MetricsStore(tmpdir)
            evaluator = PerformanceEvaluator(store, config)

            # Add baseline results
            for i in range(5):
                result = EvaluationResult(
                    timestamp=utc_now() - timedelta(days=i),
                    model_version="v1",
                    dataset_name="test",
                    dataset_version="v1",
                    metrics={"mAP": 0.85, "F1": 0.88},
                    sample_count=100,
                    evaluation_duration_seconds=10,
                )
                store.add_result(result)

            # Analyze current (similar to baseline)
            current = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.85, "F1": 0.88},
                sample_count=100,
                evaluation_duration_seconds=10,
            )

            trends = evaluator.analyze_trends(current)

            # All trends should be stable
            for trend in trends:
                assert trend.severity == AlertSeverity.NONE

    def test_analyze_trends_degradation(self) -> None:
        """Test trend analysis detects degradation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
                map_drop_warning=0.03,
                map_drop_critical=0.05,
            )
            store = MetricsStore(tmpdir)
            evaluator = PerformanceEvaluator(store, config)

            # Add baseline results with good performance
            for i in range(5):
                result = EvaluationResult(
                    timestamp=utc_now() - timedelta(days=i),
                    model_version="v1",
                    dataset_name="test",
                    dataset_version="v1",
                    metrics={"mAP": 0.90},
                    sample_count=100,
                    evaluation_duration_seconds=10,
                )
                store.add_result(result)

            # Current has significant drop
            current = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.84},  # 6.7% drop
                sample_count=100,
                evaluation_duration_seconds=10,
            )

            trends = evaluator.analyze_trends(current)

            # Find mAP trend
            map_trend = next((t for t in trends if t.metric == "mAP"), None)
            assert map_trend is not None
            assert map_trend.severity == AlertSeverity.CRITICAL
            assert map_trend.trend_direction == "degrading"

    def test_generate_report(self) -> None:
        """Test report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            store = MetricsStore(tmpdir)
            evaluator = PerformanceEvaluator(store, config)

            report = evaluator.generate_report()

            assert report is not None
            assert report.current_evaluation is not None
            assert isinstance(report.trends, list)


# ============================================================================
# PerformanceJob Tests
# ============================================================================


class TestPerformanceJob:
    """Tests for PerformanceJob."""

    def test_should_run_first_time(self) -> None:
        """Test job should run on first invocation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            job = PerformanceJob(config, tmpdir)

            assert job.should_run() is True

    def test_should_run_after_interval(self) -> None:
        """Test job scheduling based on interval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
                evaluation_interval_hours=1,
            )
            job = PerformanceJob(config, tmpdir)

            # Run once
            job.run(force=True)

            # Should not run immediately after
            assert job.should_run() is False

            # Simulate time passing
            job._last_run = utc_now() - timedelta(hours=2)
            assert job.should_run() is True

    def test_run_returns_report(self) -> None:
        """Test job run returns report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            job = PerformanceJob(config, tmpdir)

            report = job.run(model_version="v1.0.0", force=True)

            assert report is not None
            assert report.model_version == "v1.0.0"

    def test_run_saves_report(self) -> None:
        """Test job saves report to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            job = PerformanceJob(config, tmpdir)

            job.run(force=True)

            # Check latest.json exists
            latest_path = Path(tmpdir) / "reports" / "latest.json"
            assert latest_path.exists()

    def test_get_latest_report(self) -> None:
        """Test retrieving latest report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            job = PerformanceJob(config, tmpdir)

            job.run(force=True)

            report = job.get_latest_report()
            assert report is not None

    def test_skip_if_not_scheduled(self) -> None:
        """Test job skips if not scheduled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
                evaluation_interval_hours=24,
            )
            job = PerformanceJob(config, tmpdir)

            # Run first time
            job.run(force=True)

            # Try to run again without force
            result = job.run()
            assert result is None

    def test_cleanup(self) -> None:
        """Test cleanup method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = JobConfig(
                dataset_path="/data/test",
                model_path="/models/test.onnx",
            )
            job = PerformanceJob(config, tmpdir)

            # Should not raise
            job.cleanup()


# ============================================================================
# CI Validation Tests
# ============================================================================


class TestCIValidation:
    """Tests for CI validation functions."""

    def test_validate_valid_config(self) -> None:
        """Test validation of valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            config = {
                "dataset_path": "/data/test",
                "model_path": "/models/test.onnx",
                "evaluation_interval_hours": 24,
            }

            with open(config_path, "w") as f:
                json.dump(config, f)

            is_valid, errors = validate_job_config(config_path)

            assert is_valid is True
            assert errors == []

    def test_validate_missing_file(self) -> None:
        """Test validation handles missing file."""
        is_valid, errors = validate_job_config("/nonexistent/config.json")

        assert is_valid is False
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_validate_invalid_json(self) -> None:
        """Test validation handles invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            with open(config_path, "w") as f:
                f.write("not valid json")

            is_valid, errors = validate_job_config(config_path)

            assert is_valid is False
            assert any("Invalid JSON" in e for e in errors)

    def test_validate_invalid_config(self) -> None:
        """Test validation catches config errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            config = {
                "dataset_path": "",  # Invalid
                "model_path": "/models/test.onnx",
            }

            with open(config_path, "w") as f:
                json.dump(config, f)

            is_valid, errors = validate_job_config(config_path)

            assert is_valid is False
            assert "dataset_path is required" in errors

    def test_create_sample_config(self) -> None:
        """Test creating sample config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sample_config.json"

            create_sample_config(config_path)

            assert config_path.exists()

            with open(config_path) as f:
                config = json.load(f)

            assert "dataset_path" in config
            assert "model_path" in config


# ============================================================================
# Dashboard Panel Data Tests
# ============================================================================


class TestDashboardPanelData:
    """Tests for dashboard panel data generation."""

    def test_get_panel_data(self) -> None:
        """Test getting dashboard panel data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            # Add some results
            for i in range(5):
                result = EvaluationResult(
                    timestamp=utc_now() - timedelta(days=i),
                    model_version="v1",
                    dataset_name="test",
                    dataset_version="v1",
                    metrics={"mAP": 0.80 + i * 0.02, "F1": 0.85 + i * 0.01},
                    sample_count=100,
                    evaluation_duration_seconds=10,
                )
                store.add_result(result)

            data = get_dashboard_panel_data(store)

            assert "generated_at" in data
            assert "metrics" in data
            assert "mAP" in data["metrics"]
            assert "F1" in data["metrics"]
            assert "latest_evaluation" in data

    def test_panel_data_with_specific_metrics(self) -> None:
        """Test getting specific metrics for panel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            result = EvaluationResult(
                timestamp=utc_now(),
                model_version="v1",
                dataset_name="test",
                dataset_version="v1",
                metrics={"mAP": 0.85, "F1": 0.88, "precision": 0.87},
                sample_count=100,
                evaluation_duration_seconds=10,
            )
            store.add_result(result)

            data = get_dashboard_panel_data(store, metrics=["mAP"])

            assert "mAP" in data["metrics"]
            # F1 not requested, may or may not be present

    def test_panel_data_empty_store(self) -> None:
        """Test panel data with no results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MetricsStore(tmpdir)

            data = get_dashboard_panel_data(store)

            assert data["metrics"] == {}
            assert "latest_evaluation" not in data


# ============================================================================
# Data Class Serialization Tests
# ============================================================================


class TestPerformanceTrend:
    """Tests for PerformanceTrend data class."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        trend = PerformanceTrend(
            metric="mAP",
            current_value=0.82,
            baseline_value=0.85,
            change_absolute=-0.03,
            change_percent=-3.53,
            trend_direction="degrading",
            severity=AlertSeverity.WARNING,
            history=[
                (datetime(2025, 1, 10), 0.85),
                (datetime(2025, 1, 11), 0.84),
                (datetime(2025, 1, 12), 0.82),
            ],
        )

        d = trend.to_dict()

        assert d["metric"] == "mAP"
        assert d["current_value"] == 0.82
        assert d["severity"] == "warning"
        assert len(d["history"]) == 3


class TestPerformanceReport:
    """Tests for PerformanceReport data class."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        current = EvaluationResult(
            timestamp=utc_now(),
            model_version="v1",
            dataset_name="test",
            dataset_version="v1",
            metrics={"mAP": 0.85},
            sample_count=100,
            evaluation_duration_seconds=10,
        )

        report = PerformanceReport(
            timestamp=utc_now(),
            model_version="v1",
            current_evaluation=current,
            baseline_evaluation=None,
            trends=[],
            alerts=[{"metric": "mAP", "severity": "warning", "message": "Test"}],
        )

        d = report.to_dict()

        assert d["model_version"] == "v1"
        assert d["current_evaluation"] is not None
        assert d["baseline_evaluation"] is None
        assert len(d["alerts"]) == 1


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_threshold_ordering(self) -> None:
        """Test thresholds are properly ordered."""
        assert MAP_DROP_WARNING_THRESHOLD < MAP_DROP_CRITICAL_THRESHOLD
        assert F1_DROP_WARNING_THRESHOLD < F1_DROP_CRITICAL_THRESHOLD

    def test_default_values_reasonable(self) -> None:
        """Test default values are reasonable."""
        assert DEFAULT_EVALUATION_INTERVAL_HOURS >= 1
        assert DEFAULT_EVALUATION_INTERVAL_HOURS <= 168  # 1 week max

        assert DEFAULT_RETENTION_DAYS >= 7
        assert DEFAULT_RETENTION_DAYS <= 365

    def test_metric_types_complete(self) -> None:
        """Test MetricType enum has expected values."""
        assert hasattr(MetricType, "MAP")
        assert hasattr(MetricType, "F1")
        assert hasattr(MetricType, "PRECISION")
        assert hasattr(MetricType, "RECALL")

    def test_alert_severity_complete(self) -> None:
        """Test AlertSeverity enum has expected values."""
        assert hasattr(AlertSeverity, "NONE")
        assert hasattr(AlertSeverity, "WARNING")
        assert hasattr(AlertSeverity, "CRITICAL")
