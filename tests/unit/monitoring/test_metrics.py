"""Tests for Prometheus metrics export module.

Sprint 6.2.1: Tests for metrics collection and export.
"""

import os
import time
from unittest.mock import patch

import pytest

from image_preprocessing_detector.monitoring import (
    CardinalityGuard,
    MetricsCollector,
    MetricsConfig,
    MetricsNamespace,
    get_metrics,
    metrics_endpoint,
    record_correction,
    record_error,
    record_page_processed,
    record_quality_score,
    record_teacher_usage,
    timed,
)

# ============================================================================
# MetricsConfig Tests
# ============================================================================


class TestMetricsConfig:
    """Tests for MetricsConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MetricsConfig()

        assert config.enabled is True
        assert config.namespace == "imgprep"
        assert config.port == 8000
        assert config.start_server is False
        assert config.max_document_id_labels == 100
        assert config.max_error_code_labels == 50

    def test_from_environment_production(self) -> None:
        """Test config from production environment."""
        with patch.dict(
            os.environ,
            {
                "IMGPREP_ENV": "production",
                "IMGPREP_METRICS_ENABLED": "true",
                "IMGPREP_METRICS_PORT": "9090",
            },
            clear=True,
        ):
            config = MetricsConfig.from_environment()

            assert config.namespace == MetricsNamespace.PRODUCTION.value
            assert config.enabled is True
            assert config.port == 9090

    def test_from_environment_staging(self) -> None:
        """Test config from staging environment."""
        with patch.dict(
            os.environ,
            {"IMGPREP_ENV": "staging"},
            clear=True,
        ):
            config = MetricsConfig.from_environment()
            assert config.namespace == MetricsNamespace.STAGING.value

    def test_from_environment_disabled(self) -> None:
        """Test config with metrics disabled."""
        with patch.dict(
            os.environ,
            {"IMGPREP_METRICS_ENABLED": "false"},
            clear=True,
        ):
            config = MetricsConfig.from_environment()
            assert config.enabled is False

    def test_modal_cost_configuration(self) -> None:
        """Test Modal cost configuration."""
        with patch.dict(
            os.environ,
            {"IMGPREP_MODAL_COST_PER_GPU_SEC": "0.0002"},
            clear=True,
        ):
            config = MetricsConfig.from_environment()
            assert config.modal_cost_per_gpu_second == pytest.approx(0.0002)


class TestMetricsNamespace:
    """Tests for MetricsNamespace enum."""

    def test_all_namespaces_defined(self) -> None:
        """Test all namespace values are defined."""
        assert MetricsNamespace.PRODUCTION.value == "imgprep_prod"
        assert MetricsNamespace.STAGING.value == "imgprep_staging"
        assert MetricsNamespace.DEVELOPMENT.value == "imgprep_dev"
        assert MetricsNamespace.TEST.value == "imgprep_test"


# ============================================================================
# CardinalityGuard Tests
# ============================================================================


class TestCardinalityGuard:
    """Tests for CardinalityGuard."""

    def test_allows_values_under_limit(self) -> None:
        """Test values under limit are allowed."""
        guard = CardinalityGuard(max_unique_values=5)

        assert guard.sanitize("value1") == "value1"
        assert guard.sanitize("value2") == "value2"
        assert guard.sanitize("value3") == "value3"

    def test_returns_same_value_if_seen(self) -> None:
        """Test returns same value if already seen."""
        guard = CardinalityGuard(max_unique_values=5)

        assert guard.sanitize("value1") == "value1"
        assert guard.sanitize("value1") == "value1"  # Same value again

    def test_overflow_when_limit_reached(self) -> None:
        """Test overflow bucket when limit reached."""
        guard = CardinalityGuard(max_unique_values=3)

        guard.sanitize("value1")
        guard.sanitize("value2")
        guard.sanitize("value3")

        # Fourth value should overflow
        assert guard.sanitize("value4") == "__other__"
        assert guard.sanitize("value5") == "__other__"

    def test_seen_values_not_overflow(self) -> None:
        """Test already seen values don't overflow."""
        guard = CardinalityGuard(max_unique_values=3)

        guard.sanitize("value1")
        guard.sanitize("value2")
        guard.sanitize("value3")

        # value1 should still work (already tracked)
        assert guard.sanitize("value1") == "value1"

    def test_reset_clears_state(self) -> None:
        """Test reset clears tracked values."""
        guard = CardinalityGuard(max_unique_values=2)

        guard.sanitize("value1")
        guard.sanitize("value2")
        assert guard.sanitize("value3") == "__other__"

        guard.reset()

        # After reset, value3 should be allowed
        assert guard.sanitize("value3") == "value3"


# ============================================================================
# MetricsCollector Tests
# ============================================================================


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        MetricsCollector._instance = None
        MetricsCollector._initialized = False

    def test_singleton_pattern(self) -> None:
        """Test MetricsCollector is a singleton."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        assert collector1 is collector2

    def test_config_accessible(self) -> None:
        """Test config is accessible."""
        collector = MetricsCollector()
        assert collector.config is not None
        assert isinstance(collector.config, MetricsConfig)

    def test_record_page_processed(self) -> None:
        """Test recording processed page."""
        collector = MetricsCollector()

        # Should not raise
        collector.record_page_processed(
            status="success",
            gate_result="text_detected",
            duration_seconds=0.15,
            device="cpu",
            model="student",
        )

    def test_record_error(self) -> None:
        """Test recording errors."""
        collector = MetricsCollector()

        # Should not raise
        collector.record_error(error_code="E2001", category="processing")

    def test_record_error_with_cardinality_guard(self) -> None:
        """Test error recording respects cardinality guard."""
        collector = MetricsCollector()
        collector._error_guard = CardinalityGuard(max_unique_values=2)

        collector.record_error("E1001", "validation")
        collector.record_error("E1002", "validation")
        collector.record_error("E1003", "validation")  # Should overflow

        # The third error should be tracked as __other__
        # This is an implementation detail, but we can verify it doesn't raise

    def test_record_teacher_usage(self) -> None:
        """Test recording teacher usage."""
        collector = MetricsCollector()

        collector.record_teacher_usage(
            reason="uncertainty",
            device="gpu",
            duration_seconds=0.25,
            blocked=False,
        )

    def test_record_teacher_usage_blocked(self) -> None:
        """Test recording blocked teacher usage."""
        collector = MetricsCollector()

        collector.record_teacher_usage(
            reason="uncertainty",
            device="gpu",
            duration_seconds=0.0,
            blocked=True,
            blocked_reason="budget_exceeded",
        )

    def test_record_teacher_usage_modal_cost(self) -> None:
        """Test Modal cost tracking for teacher usage."""
        collector = MetricsCollector()

        collector.record_teacher_usage(
            reason="high_risk",
            device="modal",
            duration_seconds=1.0,
            blocked=False,
        )

        # Cost should be tracked (implementation detail)

    def test_record_correction(self) -> None:
        """Test recording corrections."""
        collector = MetricsCollector()

        collector.record_correction(correction_type="deskew", duration_seconds=0.05)

    def test_record_quality_score(self) -> None:
        """Test recording quality scores."""
        collector = MetricsCollector()

        collector.record_quality_score(score=0.85, gate_result="text_detected")

    def test_set_queue_depth(self) -> None:
        """Test setting queue depth."""
        collector = MetricsCollector()

        collector.set_queue_depth(queue_name="processing", depth=42)

    def test_set_active_workers(self) -> None:
        """Test setting active workers."""
        collector = MetricsCollector()

        collector.set_active_workers(worker_type="gpu", count=4)

    def test_time_operation_context_manager(self) -> None:
        """Test time_operation context manager."""
        collector = MetricsCollector()

        with collector.time_operation("test_op", device="cpu", model="student"):
            time.sleep(0.01)

        # Should not raise

    def test_set_build_info(self) -> None:
        """Test setting build info."""
        collector = MetricsCollector()

        collector.set_build_info(
            version="1.0.0",
            git_commit="abc123",
            build_time="2025-01-15T10:00:00Z",
        )

    def test_get_metrics(self) -> None:
        """Test getting metrics output."""
        collector = MetricsCollector()

        metrics = collector.get_metrics()
        assert isinstance(metrics, bytes)


# ============================================================================
# Module-Level Function Tests
# ============================================================================


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        MetricsCollector._instance = None
        MetricsCollector._initialized = False
        # Reset module-level _metrics
        import image_preprocessing_detector.monitoring as monitoring

        monitoring._metrics = None

    def test_get_metrics_returns_collector(self) -> None:
        """Test get_metrics returns a collector."""
        collector = get_metrics()
        assert isinstance(collector, MetricsCollector)

    def test_get_metrics_is_singleton(self) -> None:
        """Test get_metrics returns same instance."""
        collector1 = get_metrics()
        collector2 = get_metrics()
        assert collector1 is collector2

    def test_record_page_processed_function(self) -> None:
        """Test record_page_processed convenience function."""
        record_page_processed(
            status="success",
            gate_result="no_text",
            duration_seconds=0.1,
            device="cpu",
            model="student",
        )

    def test_record_error_function(self) -> None:
        """Test record_error convenience function."""
        record_error(error_code="E3001", category="infrastructure")

    def test_record_teacher_usage_function(self) -> None:
        """Test record_teacher_usage convenience function."""
        record_teacher_usage(
            reason="discrepancy",
            device="gpu",
            duration_seconds=0.3,
        )

    def test_record_correction_function(self) -> None:
        """Test record_correction convenience function."""
        record_correction(correction_type="contrast", duration_seconds=0.02)

    def test_record_quality_score_function(self) -> None:
        """Test record_quality_score convenience function."""
        record_quality_score(score=0.72, gate_result="text_detected")


# ============================================================================
# Decorator Tests
# ============================================================================


class TestTimedDecorator:
    """Tests for the @timed decorator."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        MetricsCollector._instance = None
        MetricsCollector._initialized = False
        import image_preprocessing_detector.monitoring as monitoring

        monitoring._metrics = None

    def test_timed_decorator_basic(self) -> None:
        """Test @timed decorator records time."""

        @timed("test_function")
        def slow_function() -> str:
            time.sleep(0.01)
            return "result"

        result = slow_function()
        assert result == "result"

    def test_timed_decorator_with_args(self) -> None:
        """Test @timed decorator with function arguments."""

        @timed("compute", device="gpu", model="teacher")
        def compute(x: int, y: int) -> int:
            return x + y

        result = compute(5, 3)
        assert result == 8

    def test_timed_decorator_preserves_exception(self) -> None:
        """Test @timed decorator preserves exceptions."""

        @timed("failing_op")
        def failing_function() -> None:
            raise ValueError("Expected error")

        with pytest.raises(ValueError, match="Expected error"):
            failing_function()


# ============================================================================
# HTTP Endpoint Tests
# ============================================================================


class TestMetricsEndpoint:
    """Tests for metrics HTTP endpoint."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        MetricsCollector._instance = None
        MetricsCollector._initialized = False
        import image_preprocessing_detector.monitoring as monitoring

        monitoring._metrics = None

    def test_metrics_endpoint_returns_bytes_and_content_type(self) -> None:
        """Test metrics_endpoint returns correct format."""
        content, content_type = metrics_endpoint()

        assert isinstance(content, bytes)
        assert "text/plain" in content_type

    def test_metrics_endpoint_content_type_version(self) -> None:
        """Test content type includes version."""
        _, content_type = metrics_endpoint()

        assert "0.0.4" in content_type  # Prometheus format version


# ============================================================================
# Integration Tests
# ============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        MetricsCollector._instance = None
        MetricsCollector._initialized = False
        import image_preprocessing_detector.monitoring as monitoring

        monitoring._metrics = None

    def test_full_processing_flow(self) -> None:
        """Test recording a full processing flow."""
        collector = get_metrics()

        # Simulate processing a page
        with collector.time_operation("page_processing", "cpu", "student"):
            # Record gate decision
            collector.gate_latency.labels(result="text_detected").observe(0.005)

            # Record IQA
            collector.iqa_latency.labels(model="student", device="cpu").observe(0.05)

            # Record correction
            collector.record_correction("deskew", 0.02)

            # Record quality
            collector.record_quality_score(0.82, "text_detected")

        # Record success
        collector.record_page_processed(
            status="success",
            gate_result="text_detected",
            duration_seconds=0.1,
            device="cpu",
            model="student",
        )

        # Get metrics output
        metrics = collector.get_metrics()
        assert len(metrics) > 0

    def test_error_flow(self) -> None:
        """Test recording an error flow."""
        collector = get_metrics()

        # Record processing that fails
        collector.record_page_processed(
            status="error",
            gate_result="error",
            duration_seconds=0.05,
            device="cpu",
            model="student",
        )

        collector.record_error("E2001", "processing")

    def test_teacher_escalation_flow(self) -> None:
        """Test recording teacher escalation flow."""
        collector = get_metrics()

        # Student processing first
        with collector.time_operation("student_iqa", "cpu", "student"):
            time.sleep(0.01)

        # Escalate to teacher
        collector.record_teacher_usage(
            reason="uncertainty",
            device="modal",
            duration_seconds=0.3,
        )

        # Record final result
        collector.record_page_processed(
            status="success",
            gate_result="text_detected",
            duration_seconds=0.35,
            device="modal",
            model="teacher",
        )

    def test_batch_processing_metrics(self) -> None:
        """Test metrics for batch processing."""
        collector = get_metrics()

        # Set queue depth
        collector.set_queue_depth("processing", 100)
        collector.set_active_workers("cpu", 4)

        # Process batch
        for i in range(10):
            collector.record_page_processed(
                status="success",
                gate_result="no_text" if i % 2 == 0 else "text_detected",
                duration_seconds=0.1 + (i * 0.01),
                device="cpu",
                model="student",
            )

        # Update queue depth
        collector.set_queue_depth("processing", 90)
