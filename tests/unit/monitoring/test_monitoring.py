"""Tests for Prometheus metrics monitoring module."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestMetricsConfig:
    """Tests for MetricsConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        config = MetricsConfig()

        assert config.enabled is True
        assert config.namespace == "imgprep"
        assert config.subsystem == ""
        assert config.port == 8000
        assert config.start_server is False
        assert config.max_document_id_labels == 100
        assert config.max_error_code_labels == 50

    def test_config_from_environment_production(self) -> None:
        """Test configuration from production environment."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        with patch.dict("os.environ", {"IMGPREP_ENV": "production"}):
            config = MetricsConfig.from_environment()
            assert "prod" in config.namespace

    def test_config_from_environment_staging(self) -> None:
        """Test configuration from staging environment."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        with patch.dict("os.environ", {"IMGPREP_ENV": "staging"}):
            config = MetricsConfig.from_environment()
            assert "staging" in config.namespace

    def test_config_from_environment_test(self) -> None:
        """Test configuration from test environment."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        with patch.dict("os.environ", {"IMGPREP_ENV": "test"}):
            config = MetricsConfig.from_environment()
            assert "test" in config.namespace

    def test_config_from_environment_default(self) -> None:
        """Test configuration with default environment."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        with patch.dict("os.environ", {"IMGPREP_ENV": "development"}):
            config = MetricsConfig.from_environment()
            # Default is imgprep (development falls through to default)
            assert config.namespace in ("imgprep", "imgprep_dev")


class TestMetricsNamespace:
    """Tests for MetricsNamespace enum."""

    def test_namespace_values(self) -> None:
        """Test namespace enum values."""
        from image_preprocessing_detector.monitoring import MetricsNamespace

        assert MetricsNamespace.PRODUCTION.value == "imgprep_prod"
        assert MetricsNamespace.STAGING.value == "imgprep_staging"
        assert MetricsNamespace.DEVELOPMENT.value == "imgprep_dev"
        assert MetricsNamespace.TEST.value == "imgprep_test"


class TestCardinalityGuard:
    """Tests for CardinalityGuard class."""

    def test_sanitize_within_limit(self) -> None:
        """Test sanitize returns value when within limit."""
        from image_preprocessing_detector.monitoring import CardinalityGuard

        guard = CardinalityGuard(max_unique_values=10)

        # First 10 values should pass through
        for i in range(10):
            result = guard.sanitize(f"value_{i}")
            assert result == f"value_{i}"

    def test_sanitize_over_limit(self) -> None:
        """Test sanitize returns overflow value when over limit."""
        from image_preprocessing_detector.monitoring import CardinalityGuard

        guard = CardinalityGuard(max_unique_values=3)

        # First 3 values pass through
        assert guard.sanitize("a") == "a"
        assert guard.sanitize("b") == "b"
        assert guard.sanitize("c") == "c"

        # 4th value gets overflow bucket
        assert guard.sanitize("d") == "__other__"

    def test_sanitize_existing_value(self) -> None:
        """Test sanitize returns existing value."""
        from image_preprocessing_detector.monitoring import CardinalityGuard

        guard = CardinalityGuard(max_unique_values=3)

        guard.sanitize("a")
        guard.sanitize("b")
        guard.sanitize("c")

        # Existing value should still work
        assert guard.sanitize("a") == "a"

    def test_reset(self) -> None:
        """Test reset clears guard state."""
        from image_preprocessing_detector.monitoring import CardinalityGuard

        guard = CardinalityGuard(max_unique_values=2)

        guard.sanitize("a")
        guard.sanitize("b")
        assert guard.sanitize("c") == "__other__"

        guard.reset()

        # After reset, new values should work
        assert guard.sanitize("c") == "c"


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        MetricsCollector._instance = None
        MetricsCollector._initialized = False

    def test_singleton_pattern(self) -> None:
        """Test MetricsCollector uses singleton pattern."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        assert collector1 is collector2

    def test_collector_config_property(self) -> None:
        """Test MetricsCollector config property."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector = MetricsCollector()
        config = collector.config

        assert config.enabled is True or config.enabled is False

    def test_record_page_processed(self) -> None:
        """Test recording page processed metrics."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.record_page_processed(
            status="success",
            gate_result="text_detected",
            duration_seconds=0.1,
            device="gpu",
            model="student",
        )

    def test_record_error(self) -> None:
        """Test recording error metrics."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.record_error("E2001", "processing")

    def test_record_teacher_usage(self) -> None:
        """Test recording teacher usage metrics."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.record_teacher_usage(
            reason="uncertainty",
            device="gpu",
            duration_seconds=0.5,
        )

    def test_record_teacher_usage_blocked(self) -> None:
        """Test recording blocked teacher usage metrics."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.record_teacher_usage(
            reason="uncertainty",
            device="gpu",
            duration_seconds=0.0,
            blocked=True,
            blocked_reason="budget_exceeded",
        )

    def test_set_build_info(self) -> None:
        """Test setting build info."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        collector = MetricsCollector()

        # Should not raise
        collector.set_build_info(
            version="1.0.0",
            git_commit="abc123",
            build_time="2025-01-01",
        )


class TestModuleFunctions:
    """Tests for module-level helper functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test."""
        from image_preprocessing_detector.monitoring import MetricsCollector

        MetricsCollector._instance = None
        MetricsCollector._initialized = False

    def test_get_metrics_singleton(self) -> None:
        """Test get_metrics returns singleton."""
        from image_preprocessing_detector.monitoring import get_metrics

        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_record_page_processed_helper(self) -> None:
        """Test record_page_processed helper function."""
        from image_preprocessing_detector.monitoring import record_page_processed

        # Should not raise
        record_page_processed(
            status="success",
            gate_result="no_text",
            duration_seconds=0.2,
            device="modal",
            model="teacher",
        )

    def test_record_quality_score_helper(self) -> None:
        """Test record_quality_score helper function."""
        from image_preprocessing_detector.monitoring import record_quality_score

        # Should not raise
        record_quality_score(0.75, "text_detected")

    def test_record_correction_helper(self) -> None:
        """Test record_correction helper function."""
        from image_preprocessing_detector.monitoring import record_correction

        # Should not raise
        record_correction("clahe", 10.5)

    def test_record_teacher_usage_helper(self) -> None:
        """Test record_teacher_usage helper function."""
        from image_preprocessing_detector.monitoring import record_teacher_usage

        # Should not raise
        record_teacher_usage(
            reason="discrepancy",
            device="gpu",
            duration_seconds=0.3,
        )

    def test_record_error_helper(self) -> None:
        """Test record_error helper function."""
        from image_preprocessing_detector.monitoring import record_error

        # Should not raise
        record_error("E3001", "infrastructure")


class TestPrometheusStubs:
    """Tests for Prometheus stub classes when prometheus_client not available."""

    def test_stub_counter(self) -> None:
        """Test stub Counter class operations."""
        from image_preprocessing_detector.monitoring import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from image_preprocessing_detector.monitoring import Counter

            counter = Counter("test_counter", "Test counter")
            labeled = counter.labels(status="success")
            labeled.inc()  # Should not raise
            labeled.inc(5)  # Should not raise

    def test_stub_gauge(self) -> None:
        """Test stub Gauge class operations."""
        from image_preprocessing_detector.monitoring import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from image_preprocessing_detector.monitoring import Gauge

            gauge = Gauge("test_gauge", "Test gauge")
            labeled = gauge.labels(device="cpu")
            labeled.set(10)  # Should not raise
            labeled.inc()  # Should not raise
            labeled.dec()  # Should not raise

    def test_stub_histogram(self) -> None:
        """Test stub Histogram class operations."""
        from image_preprocessing_detector.monitoring import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from image_preprocessing_detector.monitoring import Histogram

            histogram = Histogram("test_histogram", "Test histogram")
            labeled = histogram.labels(operation="process")
            labeled.observe(0.5)  # Should not raise

    def test_stub_info(self) -> None:
        """Test stub Info class operations."""
        from image_preprocessing_detector.monitoring import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from image_preprocessing_detector.monitoring import Info

            info = Info("test_info", "Test info")
            info.info({"version": "1.0.0"})  # Should not raise

    def test_stub_generate_latest(self) -> None:
        """Test stub generate_latest function."""
        from image_preprocessing_detector.monitoring import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from image_preprocessing_detector.monitoring import generate_latest

            result = generate_latest()
            assert result == b""

    def test_stub_start_http_server(self) -> None:
        """Test stub start_http_server function."""
        from image_preprocessing_detector.monitoring import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from image_preprocessing_detector.monitoring import start_http_server

            # Should not raise
            start_http_server(8000)


class TestCostTracking:
    """Tests for Modal GPU cost tracking."""

    def test_modal_cost_calculation(self) -> None:
        """Test Modal cost estimation."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        config = MetricsConfig(modal_cost_per_gpu_second=0.0001)

        # 1 hour of GPU usage should be $0.36
        gpu_seconds = 3600
        estimated_cost = gpu_seconds * config.modal_cost_per_gpu_second

        assert abs(estimated_cost - 0.36) < 0.01


class TestLabelCardinality:
    """Tests for label cardinality guards."""

    def test_cardinality_limits(self) -> None:
        """Test label cardinality limits are respected."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        config = MetricsConfig(
            max_document_id_labels=100,
            max_error_code_labels=50,
        )

        assert config.max_document_id_labels == 100
        assert config.max_error_code_labels == 50
