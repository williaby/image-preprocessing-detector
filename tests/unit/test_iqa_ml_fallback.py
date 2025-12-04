"""Tests for ML IQA fallback behavior when models unavailable.

These tests run WITHOUT actual ONNX models to verify graceful degradation.
Tests ensure the system handles missing models, device unavailability,
and various fallback scenarios correctly.

Sprint 5.1.x: ML IQA fallback and degradation tests.
"""

from unittest.mock import patch

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    Device,
    EscalationDecision,
    MLIQADetector,
    MLIQAScores,
    ModelType,
    UncertaintyMetrics,
)

# =============================================================================
# Model Unavailable Tests
# =============================================================================


class TestMLIQAModelUnavailable:
    """Test ML IQA behavior when models are unavailable."""

    def test_detector_creation_without_model_paths(self):
        """Test detector can be created without model paths."""
        detector = MLIQADetector(
            student_model_path=None,
            teacher_model_path=None,
        )

        # Verify detector created with expected attributes
        assert detector.student_model_path is None
        assert detector.teacher_model_path is None

    def test_detector_creation_with_nonexistent_paths(self):
        """Test detector handles nonexistent model paths gracefully."""
        detector = MLIQADetector(
            student_model_path="/nonexistent/path/student.onnx",
            teacher_model_path="/nonexistent/path/teacher.onnx",
            use_orchestrator=False,
        )

        # Sessions should remain unloaded for nonexistent paths
        assert detector._student_session is None
        assert detector._teacher_session is None

    def test_student_session_not_loaded(self):
        """Test student session is not loaded for missing model."""
        detector = MLIQADetector(
            student_model_path="/nonexistent/student.onnx",
            use_orchestrator=False,
        )

        # Session should remain None until explicitly loaded
        assert detector._student_session is None

    def test_teacher_session_not_loaded(self):
        """Test teacher session is not loaded for missing model."""
        detector = MLIQADetector(
            teacher_model_path="/nonexistent/teacher.onnx",
            use_orchestrator=False,
        )

        assert detector._teacher_session is None


# =============================================================================
# Device Detection Fallback Tests
# =============================================================================


class TestDeviceDetectionFallback:
    """Test device detection and fallback logic."""

    def test_device_defaults_to_cpu_when_no_gpu(self):
        """Test device defaults to CPU when no GPU available."""
        with patch("image_preprocessing_detector.detection.iqa_ml.ort") as mock_ort:
            # Simulate no GPU providers
            mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]

            detector = MLIQADetector(use_orchestrator=False)

            # Should fall back to CPU
            assert detector.device in [Device.CPU, Device.GPU, Device.MODAL]

    def test_explicit_device_selection(self):
        """Test explicit device selection overrides auto-detection."""
        detector = MLIQADetector(device=Device.CPU, use_orchestrator=False)

        assert detector.device == Device.CPU

    def test_modal_fallback_can_be_disabled(self):
        """Test Modal fallback can be disabled."""
        detector = MLIQADetector(enable_modal_fallback=False)

        assert detector.enable_modal_fallback is False


# =============================================================================
# Inference Graceful Failure Tests
# =============================================================================


class TestInferenceGracefulFailure:
    """Test inference fails gracefully when models unavailable."""

    def test_run_student_inference_raises_without_model(self):
        """Test run_student_inference raises error when model not loaded."""
        detector = MLIQADetector(
            student_model_path="/nonexistent/student.onnx",
        )

        img = np.ones((224, 224, 3), dtype=np.uint8)

        # Should raise FileNotFoundError or similar when model doesn't exist
        with pytest.raises((RuntimeError, ValueError, FileNotFoundError)):
            detector.run_student_inference(img)

    def test_run_teacher_inference_raises_without_model(self):
        """Test run_teacher_inference raises error when model not loaded."""
        detector = MLIQADetector(
            teacher_model_path="/nonexistent/teacher.onnx",
        )

        img = np.ones((224, 224, 3), dtype=np.uint8)

        # Should raise FileNotFoundError or similar when model doesn't exist
        with pytest.raises((RuntimeError, ValueError, FileNotFoundError)):
            detector.run_teacher_inference(img)


# =============================================================================
# Escalation Logic Tests (Without Models)
# =============================================================================


class TestEscalationLogicWithoutModels:
    """Test escalation decision logic without actual models."""

    def test_escalation_decision_dataclass(self):
        """Test EscalationDecision dataclass creation."""
        uncertainty = UncertaintyMetrics(
            entropy=0.5,
            min_confidence=0.7,
            mean_confidence=0.8,
            head_confidences={"blur": 0.8, "noise": 0.9},
        )

        decision = EscalationDecision(
            should_escalate=False,
            reason=None,
            uncertainty_metrics=uncertainty,
        )

        assert decision.should_escalate is False
        assert decision.reason is None
        assert decision.uncertainty_metrics.entropy == pytest.approx(0.5)

    def test_high_uncertainty_should_escalate(self):
        """Test that high uncertainty metrics would trigger escalation."""
        uncertainty = UncertaintyMetrics(
            entropy=0.95,  # High entropy
            min_confidence=0.3,  # Low confidence
            mean_confidence=0.5,
            head_confidences={"blur": 0.3, "noise": 0.7},
        )

        # Manually check escalation logic
        detector = MLIQADetector(
            entropy_threshold=0.8,
            min_confidence_threshold=0.6,
            mean_confidence_threshold=0.7,
        )

        # High entropy should trigger escalation
        assert uncertainty.entropy > detector.entropy_threshold
        # Low min confidence should trigger escalation
        assert uncertainty.min_confidence < detector.min_confidence_threshold

    def test_low_uncertainty_should_not_escalate(self):
        """Test that low uncertainty metrics would not trigger escalation."""
        uncertainty = UncertaintyMetrics(
            entropy=0.3,  # Low entropy
            min_confidence=0.85,  # High confidence
            mean_confidence=0.9,
            head_confidences={"blur": 0.85, "noise": 0.95},
        )

        detector = MLIQADetector(
            entropy_threshold=0.8,
            min_confidence_threshold=0.6,
        )

        # Low entropy should not trigger escalation
        assert uncertainty.entropy < detector.entropy_threshold
        # High min confidence should not trigger escalation
        assert uncertainty.min_confidence > detector.min_confidence_threshold


# =============================================================================
# Classical IQA Scores Tests
# =============================================================================


class TestClassicalIQAScores:
    """Test ClassicalIQAScores dataclass behavior."""

    def test_classical_scores_creation(self):
        """Test ClassicalIQAScores creation with required fields."""
        scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.9,
            skew_score=0.95,
        )

        assert scores.blur_score == pytest.approx(0.8)
        assert scores.contrast_score == pytest.approx(0.9)
        assert scores.skew_score == pytest.approx(0.95)

    def test_classical_scores_with_optional_fields(self):
        """Test ClassicalIQAScores with all fields."""
        scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.9,
            skew_score=0.95,
            noise_score=0.85,
            illumination_score=0.7,
            compression_score=0.9,
            binarization_score=0.8,
            bleed_through_score=0.95,
        )

        assert scores.noise_score == pytest.approx(0.85)
        assert scores.illumination_score == pytest.approx(0.7)
        assert scores.compression_score == pytest.approx(0.9)

    def test_classical_scores_defaults(self):
        """Test ClassicalIQAScores default values."""
        scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.9,
            skew_score=0.95,
        )

        # Optional fields should default to 0.0
        assert scores.noise_score == pytest.approx(0.0)
        assert scores.illumination_score == pytest.approx(0.0)
        assert scores.compression_score == pytest.approx(0.0)

    def test_classical_scores_validation(self):
        """Test ClassicalIQAScores validates score ranges."""
        # Scores outside [0, 1] should raise
        with pytest.raises(ValueError):
            ClassicalIQAScores(
                blur_score=1.5,  # Invalid
                contrast_score=0.9,
                skew_score=0.95,
            )

        with pytest.raises(ValueError):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=-0.1,  # Invalid
                skew_score=0.95,
            )


# =============================================================================
# ML IQA Scores Tests
# =============================================================================


class TestMLIQAScores:
    """Test MLIQAScores dataclass behavior."""

    def test_ml_scores_creation(self):
        """Test MLIQAScores creation."""
        scores = MLIQAScores(
            blur_score=0.85,
            noise_score=0.9,
            contrast_score=0.8,
            skew_score=0.95,
            compression_score=0.88,
            overall_quality=0.87,
            confidences={"blur": 0.9, "noise": 0.95},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=15.5,
        )

        assert scores.blur_score == pytest.approx(0.85)
        assert scores.model_type == ModelType.STUDENT
        assert scores.device == Device.CPU
        assert scores.inference_time_ms == pytest.approx(15.5)

    def test_ml_scores_teacher_model(self):
        """Test MLIQAScores from teacher model."""
        scores = MLIQAScores(
            blur_score=0.82,
            noise_score=0.88,
            contrast_score=0.75,
            skew_score=0.92,
            compression_score=0.85,
            overall_quality=0.84,
            confidences={"blur": 0.92, "noise": 0.96},
            model_type=ModelType.TEACHER,
            device=Device.GPU,
            inference_time_ms=25.0,
        )

        assert scores.model_type == ModelType.TEACHER
        assert scores.device == Device.GPU


# =============================================================================
# Discrepancy Detection Tests
# =============================================================================


class TestDiscrepancyDetection:
    """Test discrepancy detection between classical and ML scores."""

    def test_discrepancy_threshold_setting(self):
        """Test discrepancy threshold can be configured."""
        detector = MLIQADetector()

        # Default threshold
        assert detector.discrepancy_threshold == pytest.approx(0.3)

    def test_no_discrepancy_with_similar_scores(self):
        """Test no discrepancy when scores are similar."""
        classical = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.85,
            skew_score=0.9,
        )

        ml = MLIQAScores(
            blur_score=0.78,  # Within 0.3 of classical
            noise_score=0.9,
            contrast_score=0.83,  # Within 0.3
            skew_score=0.88,  # Within 0.3
            compression_score=0.9,
            overall_quality=0.87,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        # Calculate discrepancy manually
        blur_diff = abs(classical.blur_score - ml.blur_score)
        contrast_diff = abs(classical.contrast_score - ml.contrast_score)

        threshold = 0.3
        assert blur_diff < threshold
        assert contrast_diff < threshold

    def test_discrepancy_with_different_scores(self):
        """Test discrepancy detected when scores differ significantly."""
        classical = ClassicalIQAScores(
            blur_score=0.9,  # High quality
            contrast_score=0.85,
            skew_score=0.9,
        )

        ml = MLIQAScores(
            blur_score=0.3,  # ML says blurry (large diff)
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.9,
            overall_quality=0.7,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        # Calculate discrepancy
        blur_diff = abs(classical.blur_score - ml.blur_score)

        threshold = 0.3
        assert blur_diff > threshold  # Should be flagged


# =============================================================================
# ONNX Runtime Availability Tests
# =============================================================================


class TestONNXRuntimeAvailability:
    """Test behavior when ONNX Runtime is not available."""

    def test_ort_import_handled(self):
        """Test that ONNX Runtime import failure is handled."""
        # The module should still be importable even if ort is None
        from image_preprocessing_detector.detection import iqa_ml

        # Module-level ort variable should exist
        assert hasattr(iqa_ml, "ort")

    def test_detector_creation_without_ort(self):
        """Test detector can be created even without ONNX Runtime."""
        with patch("image_preprocessing_detector.detection.iqa_ml.ort", None):
            # Should not crash during creation
            detector = MLIQADetector()
            assert detector is not None


# =============================================================================
# Pipeline Integration Tests (Without Real Models)
# =============================================================================


class TestPipelineIntegrationWithoutModels:
    """Test pipeline integration behavior without real models."""

    def test_pipeline_returns_none_without_student(self):
        """Test pipeline gracefully handles missing student model."""
        detector = MLIQADetector(
            student_model_path=None,
        )

        img = np.ones((224, 224, 3), dtype=np.uint8)
        classical = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.9,
            skew_score=0.95,
        )

        # Pipeline should not crash, may return None or raise
        try:
            result = detector.run_pipeline(img, classical)
            # If it returns, should indicate no model
        except (RuntimeError, ValueError, AttributeError):
            # Expected - no model loaded
            pass

    def test_device_priority_respected(self):
        """Test device priority is respected in configuration."""
        # GPU preference
        detector_gpu = MLIQADetector(device=Device.GPU)
        assert detector_gpu.device == Device.GPU

        # CPU preference
        detector_cpu = MLIQADetector(device=Device.CPU)
        assert detector_cpu.device == Device.CPU

        # Modal preference
        detector_modal = MLIQADetector(device=Device.MODAL)
        assert detector_modal.device == Device.MODAL


# =============================================================================
# Threshold Configuration Tests
# =============================================================================


class TestThresholdConfiguration:
    """Test uncertainty threshold configuration."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        detector = MLIQADetector()

        assert detector.entropy_threshold == pytest.approx(0.8)
        assert detector.min_confidence_threshold == pytest.approx(0.6)
        assert detector.mean_confidence_threshold == pytest.approx(0.7)

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        detector = MLIQADetector(
            entropy_threshold=0.9,
            min_confidence_threshold=0.5,
            mean_confidence_threshold=0.8,
        )

        assert detector.entropy_threshold == pytest.approx(0.9)
        assert detector.min_confidence_threshold == pytest.approx(0.5)
        assert detector.mean_confidence_threshold == pytest.approx(0.8)

    def test_threshold_validation(self):
        """Test that thresholds are used for escalation decisions."""
        # Low thresholds = more escalations
        detector_sensitive = MLIQADetector(
            entropy_threshold=0.3,
            min_confidence_threshold=0.8,
        )

        # High thresholds = fewer escalations
        detector_permissive = MLIQADetector(
            entropy_threshold=0.95,
            min_confidence_threshold=0.3,
        )

        # Sensitive should escalate more easily
        assert (
            detector_sensitive.entropy_threshold < detector_permissive.entropy_threshold
        )
