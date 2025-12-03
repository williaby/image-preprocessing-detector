"""Unit tests for pipeline hooks module.

Tests for Sprint 6.3.x pipeline integration features:
- PipelineHooks initialization and singleton pattern
- Metric recording during document processing
- Distribution tracking for drift detection
- Drift check functionality
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from image_preprocessing_detector.drift import DriftSeverity, FeatureType
from image_preprocessing_detector.pipeline import (
    PipelineHooks,
    PipelineMetrics,
    ProcessingContext,
    finish_document_processing,
    get_pipeline_hooks,
    record_page_metrics,
    run_drift_check,
    start_document_processing,
)


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset singleton before each test."""
    PipelineHooks.reset_instance()


class TestProcessingContext:
    """Tests for ProcessingContext dataclass."""

    def test_context_creation(self) -> None:
        """Test ProcessingContext creation with defaults."""
        ctx = ProcessingContext(document_id="test-doc")

        assert ctx.document_id == "test-doc"
        assert ctx.page_count == 0
        assert ctx.errors == []
        assert ctx.corrections_applied == []
        assert ctx.teacher_used is False
        assert ctx.device_used == "cpu"
        assert ctx.gate_result == "unknown"
        assert ctx.quality_scores == []
        assert ctx.start_time > 0

    def test_context_custom_values(self) -> None:
        """Test ProcessingContext with custom values."""
        ctx = ProcessingContext(
            document_id="custom-doc",
            device_used="gpu",
            gate_result="text_detected",
        )

        assert ctx.document_id == "custom-doc"
        assert ctx.device_used == "gpu"
        assert ctx.gate_result == "text_detected"


class TestPipelineHooksSingleton:
    """Tests for PipelineHooks singleton pattern."""

    def test_singleton_pattern(self) -> None:
        """Test that PipelineHooks uses singleton pattern."""
        hooks1 = PipelineHooks()
        hooks2 = PipelineHooks()

        assert hooks1 is hooks2

    def test_singleton_reset(self) -> None:
        """Test singleton reset for testing."""
        hooks1 = PipelineHooks()
        PipelineHooks.reset_instance()
        hooks2 = PipelineHooks()

        # After reset, should be new instance
        assert hooks2._initialized is True

    def test_get_pipeline_hooks_returns_singleton(self) -> None:
        """Test module-level get_pipeline_hooks returns singleton."""
        hooks1 = get_pipeline_hooks()
        hooks2 = get_pipeline_hooks()

        assert hooks1 is hooks2


class TestPipelineHooksInitialization:
    """Tests for PipelineHooks initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization with both features enabled."""
        hooks = PipelineHooks()

        assert hooks._enable_drift is True
        assert hooks._enable_metrics is True
        assert hooks._tracker is not None
        assert hooks._detector is not None
        assert hooks._metrics is not None

    def test_configure_disabled_drift_detection(self) -> None:
        """Test configuration to disable drift detection."""
        hooks = PipelineHooks()
        hooks.configure(enable_drift_detection=False)

        assert hooks._enable_drift is False
        assert hooks._tracker is None
        assert hooks._detector is None

    def test_configure_disabled_metrics(self) -> None:
        """Test configuration to disable metrics."""
        hooks = PipelineHooks()
        hooks.configure(enable_metrics=False)

        assert hooks._enable_metrics is False

    def test_configure_custom_sample_rate(self) -> None:
        """Test configuration with custom sample rate."""
        hooks = PipelineHooks()
        hooks.configure(sample_rate=0.5)

        assert hooks._sample_rate == 0.5

    def test_configure_alert_manager(self) -> None:
        """Test configuration with alert manager."""
        mock_alert_manager = MagicMock()
        hooks = PipelineHooks()
        hooks.configure(alert_manager=mock_alert_manager)

        assert hooks._alert_manager is mock_alert_manager


class TestDocumentProcessing:
    """Tests for document processing lifecycle."""

    def test_start_document(self) -> None:
        """Test starting document processing."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123", device="gpu")

        assert ctx.document_id == "doc-123"
        assert ctx.device_used == "gpu"
        assert ctx.start_time > 0

    def test_record_page(self) -> None:
        """Test recording page metrics."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        hooks.record_page(
            ctx,
            quality_score=0.85,
            gate_result="text_detected",
            blur_score=0.1,
            noise_score=0.05,
        )

        assert ctx.page_count == 1
        assert ctx.gate_result == "text_detected"
        assert len(ctx.quality_scores) == 1
        assert ctx.quality_scores[0] == 0.85

    def test_record_multiple_pages(self) -> None:
        """Test recording multiple pages."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        for i in range(5):
            hooks.record_page(
                ctx, quality_score=0.8 + i * 0.02, gate_result="text_detected"
            )

        assert ctx.page_count == 5
        assert len(ctx.quality_scores) == 5

    def test_record_page_error(self) -> None:
        """Test recording page error."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        hooks.record_page_error(ctx, error_code="E2001", category="processing")

        assert len(ctx.errors) == 1
        assert ctx.errors[0] == "E2001"

    def test_record_correction(self) -> None:
        """Test recording correction applied."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        hooks.record_correction_applied(ctx, correction_type="deskew", duration_ms=15.0)

        assert len(ctx.corrections_applied) == 1
        assert ctx.corrections_applied[0] == "deskew"

    def test_record_teacher_use(self) -> None:
        """Test recording teacher model usage."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        hooks.record_teacher_use(
            ctx, reason="uncertainty", duration_ms=30.0, device="gpu"
        )

        assert ctx.teacher_used is True
        assert ctx.teacher_reason == "uncertainty"

    def test_finish_document(self) -> None:
        """Test finishing document processing."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        # Add some pages
        for _ in range(3):
            hooks.record_page(ctx, quality_score=0.85, gate_result="text_detected")

        elapsed = hooks.finish_document(ctx, success=True)

        assert elapsed > 0
        assert ctx.page_count == 3

    def test_finish_document_failure(self) -> None:
        """Test finishing document processing with failure."""
        hooks = PipelineHooks()
        ctx = hooks.start_document("doc-123")

        hooks.record_page_error(ctx, error_code="E2001", category="processing")
        elapsed = hooks.finish_document(ctx, success=False)

        assert elapsed > 0


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_start_document_processing(self) -> None:
        """Test module-level start_document_processing."""
        ctx = start_document_processing("doc-123", device="cpu")

        assert ctx.document_id == "doc-123"
        assert isinstance(ctx, ProcessingContext)

    def test_record_page_metrics(self) -> None:
        """Test module-level record_page_metrics."""
        ctx = start_document_processing("doc-123")
        record_page_metrics(ctx, quality_score=0.9, gate_result="no_text")

        assert ctx.page_count == 1
        assert ctx.quality_scores[0] == 0.9

    def test_finish_document_processing(self) -> None:
        """Test module-level finish_document_processing."""
        ctx = start_document_processing("doc-123")
        record_page_metrics(ctx, quality_score=0.85, gate_result="text_detected")

        elapsed = finish_document_processing(ctx, success=True)

        assert elapsed > 0


class TestPipelineMetrics:
    """Tests for aggregated pipeline metrics."""

    def test_initial_metrics(self) -> None:
        """Test initial metrics values."""
        hooks = PipelineHooks()
        metrics = hooks.get_pipeline_metrics()

        assert metrics.total_pages_processed == 0
        assert metrics.total_errors == 0
        assert metrics.total_corrections == 0
        assert metrics.teacher_invocations == 0
        assert metrics.avg_quality_score == 0.0

    def test_metrics_accumulation(self) -> None:
        """Test metrics accumulation across documents."""
        hooks = PipelineHooks()

        # Process first document
        ctx1 = hooks.start_document("doc-1")
        hooks.record_page(ctx1, quality_score=0.8, gate_result="text_detected")
        hooks.record_page(ctx1, quality_score=0.9, gate_result="text_detected")
        hooks.finish_document(ctx1)

        # Process second document
        ctx2 = hooks.start_document("doc-2")
        hooks.record_page(ctx2, quality_score=0.7, gate_result="no_text")
        hooks.record_correction_applied(ctx2, correction_type="deskew", duration_ms=10.0)
        hooks.finish_document(ctx2)

        metrics = hooks.get_pipeline_metrics()

        assert metrics.total_pages_processed == 3
        assert metrics.total_corrections == 1

    def test_metrics_reset(self) -> None:
        """Test metrics reset."""
        hooks = PipelineHooks()

        ctx = hooks.start_document("doc-1")
        hooks.record_page(ctx, quality_score=0.8, gate_result="text_detected")
        hooks.finish_document(ctx)

        hooks.reset_metrics()
        metrics = hooks.get_pipeline_metrics()

        assert metrics.total_pages_processed == 0


class TestDriftDetection:
    """Tests for drift detection integration."""

    def test_check_drift_no_data(self) -> None:
        """Test drift check with no data."""
        hooks = PipelineHooks()
        results = hooks.check_drift()

        # No drift expected with no data
        assert isinstance(results, list)

    def test_check_drift_disabled(self) -> None:
        """Test drift check when disabled."""
        hooks = PipelineHooks()
        hooks.configure(enable_drift_detection=False)
        results = hooks.check_drift()

        assert results == []

    def test_save_reference_distributions(self) -> None:
        """Test saving reference distributions."""
        hooks = PipelineHooks()

        # Add some sample data
        ctx = hooks.start_document("doc-1")
        for i in range(100):
            hooks.record_page(
                ctx, quality_score=0.5 + i * 0.005, gate_result="text_detected"
            )
        hooks.finish_document(ctx)

        # This should not raise
        hooks.save_reference_distributions()

    def test_run_drift_check_function(self) -> None:
        """Test module-level run_drift_check function."""
        results = run_drift_check()

        assert isinstance(results, list)


class TestDistributionTracking:
    """Tests for distribution tracking during processing."""

    def test_quality_score_tracking(self) -> None:
        """Test that quality scores are tracked for drift detection."""
        hooks = PipelineHooks()

        ctx = hooks.start_document("doc-1")
        for _ in range(10):
            hooks.record_page(ctx, quality_score=0.85, gate_result="text_detected")
        hooks.finish_document(ctx)

        # Verify tracker has tracked features
        if hooks._tracker:
            tracked = hooks._tracker.get_tracked_features()
            assert "quality_score" in tracked

    def test_multiple_feature_tracking(self) -> None:
        """Test that multiple features are tracked."""
        hooks = PipelineHooks()

        ctx = hooks.start_document("doc-1")
        hooks.record_page(
            ctx,
            quality_score=0.85,
            gate_result="text_detected",
            blur_score=0.1,
            noise_score=0.05,
            contrast_score=0.9,
            skew_angle=2.5,
            processing_time_ms=50.0,
        )
        hooks.finish_document(ctx)

        # Verify multiple features are tracked
        if hooks._tracker:
            tracked = hooks._tracker.get_tracked_features()
            assert len(tracked) > 0


class TestAlertIntegration:
    """Tests for alert manager integration."""

    def test_alert_manager_configuration(self) -> None:
        """Test that alert manager can be configured."""
        mock_alert_manager = MagicMock()

        hooks = PipelineHooks()
        hooks.configure(alert_manager=mock_alert_manager)

        assert hooks._alert_manager is mock_alert_manager


class TestConcurrency:
    """Tests for thread safety."""

    def test_metrics_lock(self) -> None:
        """Test that metrics updates are thread-safe."""
        hooks = PipelineHooks()
        errors: list[Exception] = []

        def process_document(doc_id: str) -> None:
            try:
                ctx = hooks.start_document(doc_id)
                for _ in range(10):
                    hooks.record_page(
                        ctx, quality_score=0.8, gate_result="text_detected"
                    )
                hooks.finish_document(ctx)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=process_document, args=(f"doc-{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All pages should be counted
        metrics = hooks.get_pipeline_metrics()
        assert metrics.total_pages_processed == 50


class TestPipelineMetricsDataclass:
    """Tests for PipelineMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test PipelineMetrics default values."""
        metrics = PipelineMetrics()

        assert metrics.total_pages_processed == 0
        assert metrics.total_errors == 0
        assert metrics.total_corrections == 0
        assert metrics.teacher_invocations == 0
        assert metrics.avg_quality_score == 0.0
        assert metrics.avg_processing_time_ms == 0.0
        assert metrics.drift_warnings == 0
        assert metrics.drift_critical == 0

    def test_custom_values(self) -> None:
        """Test PipelineMetrics with custom values."""
        metrics = PipelineMetrics(
            total_pages_processed=100,
            total_errors=5,
            avg_quality_score=0.85,
        )

        assert metrics.total_pages_processed == 100
        assert metrics.total_errors == 5
        assert metrics.avg_quality_score == 0.85
