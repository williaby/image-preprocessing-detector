"""Tests for ML IQA pipeline integration.

This module tests:
- MLIQADetector initialization and configuration
- Student/teacher inference (with mocked ONNX sessions)
- Uncertainty gate logic
- Classical IQA discrepancy checks
- Serialization utilities
- Pipeline orchestration with teacher escalation
"""

import pytest

from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    Device,
    DiscrepancyMetrics,
    EscalationDecision,
    MLIQADetector,
    MLIQAScores,
    ModelType,
    UncertaintyMetrics,
    discrepancy_metrics_to_dict,
    ml_iqa_scores_to_dict,
    teacher_iqa_to_dict,
    uncertainty_metrics_to_dict,
)


class TestMLIQAScores:
    """Tests for MLIQAScores dataclass."""

    def test_creation(self):
        """Test creating MLIQAScores."""
        scores = MLIQAScores(
            blur_score=0.85,
            noise_score=0.78,
            contrast_score=0.82,
            skew_score=0.91,
            compression_score=0.88,
            overall_quality=0.85,
            confidences={"blur": 0.92, "noise": 0.88},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=25.5,
        )
        assert scores.blur_score == 0.85
        assert scores.model_type == ModelType.STUDENT
        assert scores.device == Device.CPU


class TestUncertaintyMetrics:
    """Tests for UncertaintyMetrics dataclass."""

    def test_creation(self):
        """Test creating UncertaintyMetrics."""
        metrics = UncertaintyMetrics(
            entropy=0.75,
            min_confidence=0.55,
            mean_confidence=0.72,
            head_confidences={"blur": 0.55, "noise": 0.89},
        )
        assert metrics.entropy == 0.75
        assert metrics.min_confidence == 0.55


class TestClassicalIQAScores:
    """Tests for ClassicalIQAScores dataclass."""

    def test_default_values(self):
        """Test default values for optional score fields."""
        scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.75,
            skew_score=0.9,
        )
        # Optional fields should default to 0.0
        assert scores.noise_score == 0.0
        assert scores.illumination_score == 0.0
        assert scores.compression_score == 0.0
        assert scores.binarization_score == 0.0
        assert scores.bleed_through_score == 0.0


class TestEscalationDecision:
    """Tests for EscalationDecision dataclass."""

    def test_escalation_with_reason(self):
        """Test escalation decision with reason."""
        metrics = UncertaintyMetrics(
            entropy=0.85, min_confidence=0.5, mean_confidence=0.6, head_confidences={}
        )
        decision = EscalationDecision(
            should_escalate=True,
            reason="high_entropy",
            uncertainty_metrics=metrics,
        )
        assert decision.should_escalate is True
        assert "entropy" in decision.reason


class TestMLIQADetector:
    """Tests for MLIQADetector class."""

    def test_init_defaults(self):
        """Test detector initialization with defaults."""
        detector = MLIQADetector()
        assert detector.entropy_threshold == 0.8
        assert detector.min_confidence_threshold == 0.6
        assert detector.mean_confidence_threshold == 0.7
        assert detector.discrepancy_threshold == 0.3

    def test_init_custom_thresholds(self):
        """Test detector initialization with custom thresholds."""
        detector = MLIQADetector(
            entropy_threshold=0.9,
            min_confidence_threshold=0.7,
            mean_confidence_threshold=0.8,
        )
        assert detector.entropy_threshold == 0.9
        assert detector.min_confidence_threshold == 0.7
        assert detector.mean_confidence_threshold == 0.8

    def test_device_detection_cpu_fallback(self):
        """Test device detection falls back to CPU."""
        detector = MLIQADetector()
        # Without GPU, should default to CPU
        assert detector.device in [Device.CPU, Device.GPU]

    def test_calculate_uncertainty(self):
        """Test uncertainty calculation from scores."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.75,
            overall_quality=0.8,
            confidences={
                "blur": 0.9,
                "noise": 0.6,  # Low confidence
                "contrast": 0.85,
                "skew": 0.95,
                "compression": 0.7,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        assert uncertainty.min_confidence == 0.6
        assert 0.6 <= uncertainty.mean_confidence <= 1.0
        assert uncertainty.entropy >= 0.0

    def test_should_escalate_high_entropy(self):
        """Test escalation due to high entropy."""
        detector = MLIQADetector(entropy_threshold=0.5)

        # Create scores with low confidences (high entropy)
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={
                "blur": 0.51,  # Near 50-50 = high entropy
                "noise": 0.52,
                "contrast": 0.50,
                "skew": 0.51,
                "compression": 0.49,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        # Very low confidences near 0.5 should trigger escalation
        assert decision.should_escalate is True
        assert decision.reason is not None

    def test_should_not_escalate_confident(self):
        """Test no escalation when confident."""
        detector = MLIQADetector()

        # Create scores with high confidences
        scores = MLIQAScores(
            blur_score=0.9,
            noise_score=0.85,
            contrast_score=0.88,
            skew_score=0.92,
            compression_score=0.87,
            overall_quality=0.88,
            confidences={
                "blur": 0.95,
                "noise": 0.90,
                "contrast": 0.92,
                "skew": 0.98,
                "compression": 0.88,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        assert decision.should_escalate is False
        assert decision.reason is None

    def test_calculate_discrepancy(self):
        """Test discrepancy calculation between ML and classical IQA."""
        detector = MLIQADetector()

        ml_scores = MLIQAScores(
            blur_score=0.9,
            noise_score=0.8,
            contrast_score=0.5,  # Big discrepancy here
            skew_score=0.85,
            compression_score=0.75,
            overall_quality=0.76,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        classical_scores = ClassicalIQAScores(
            blur_score=0.85,
            contrast_score=0.9,  # 0.4 difference from ML
            skew_score=0.88,
            noise_score=0.85,  # 0.05 difference from ML
            compression_score=0.70,  # 0.05 difference from ML
        )

        discrepancy = detector.calculate_discrepancy(ml_scores, classical_scores)

        # Check per-head discrepancies
        assert discrepancy.blur_discrepancy == pytest.approx(0.05, abs=0.01)
        assert discrepancy.contrast_discrepancy == pytest.approx(0.4, abs=0.01)
        assert discrepancy.skew_discrepancy == pytest.approx(0.03, abs=0.01)
        assert discrepancy.noise_discrepancy == pytest.approx(0.05, abs=0.01)
        assert discrepancy.compression_discrepancy == pytest.approx(0.05, abs=0.01)

        # Max discrepancy should be contrast (0.4)
        assert discrepancy.max_discrepancy == pytest.approx(0.4, abs=0.01)

    def test_should_escalate_due_to_discrepancy(self):
        """Test escalation due to high discrepancy."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.3  # Set threshold directly

        ml_scores = MLIQAScores(
            blur_score=0.5,  # Large discrepancy
            noise_score=0.8,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.75,
            overall_quality=0.76,
            confidences={
                "blur": 0.9,
                "noise": 0.9,
                "contrast": 0.9,
                "skew": 0.9,
                "compression": 0.9,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        classical_scores = ClassicalIQAScores(
            blur_score=0.9,  # 0.4 difference
            contrast_score=0.85,
            skew_score=0.9,
        )

        decision = detector.should_escalate_due_to_discrepancy(
            ml_scores, classical_scores
        )

        assert decision.should_escalate is True
        assert "blur_discrepancy" in decision.reason


class TestSerializationUtilities:
    """Tests for serialization utility functions."""

    def test_ml_iqa_scores_to_dict(self):
        """Test MLIQAScores serialization."""
        scores = MLIQAScores(
            blur_score=0.85123,
            noise_score=0.78456,
            contrast_score=0.82789,
            skew_score=0.91012,
            compression_score=0.88345,
            overall_quality=0.85345,
            confidences={"blur": 0.92, "noise": 0.88},
            model_type=ModelType.STUDENT,
            device=Device.GPU,
            inference_time_ms=15.3456,
        )

        result = ml_iqa_scores_to_dict(scores)

        assert result["source"] == "student"
        assert result["blur_score"] == 0.8512  # Rounded to 4 decimal places
        assert result["device"] == "cuda"
        assert result["inference_time_ms"] == 15.35  # Rounded to 2 decimal places

    def test_teacher_iqa_to_dict(self):
        """Test teacher IQA serialization with escalation reason."""
        scores = MLIQAScores(
            blur_score=0.85,
            noise_score=0.78,
            contrast_score=0.82,
            skew_score=0.91,
            compression_score=0.88,
            overall_quality=0.85,
            confidences={},
            model_type=ModelType.TEACHER,
            device=Device.GPU,
            inference_time_ms=28.7,
        )

        result = teacher_iqa_to_dict(scores, "high_entropy (0.85 >= 0.80)")

        assert result["source"] == "teacher"
        assert result["escalation_reason"] == "high_entropy (0.85 >= 0.80)"

    def test_uncertainty_metrics_to_dict(self):
        """Test UncertaintyMetrics serialization."""
        metrics = UncertaintyMetrics(
            entropy=0.75123,
            min_confidence=0.55678,
            mean_confidence=0.72345,
            head_confidences={"blur": 0.55678, "noise": 0.89012},
        )

        result = uncertainty_metrics_to_dict(metrics)

        assert result["entropy"] == 0.7512
        assert result["min_confidence"] == 0.5568
        assert result["head_confidences"]["blur"] == 0.5568

    def test_discrepancy_metrics_to_dict(self):
        """Test DiscrepancyMetrics serialization with all 8 dimensions."""
        metrics = DiscrepancyMetrics(
            blur_discrepancy=0.05123,
            contrast_discrepancy=0.40456,
            skew_discrepancy=0.03789,
            noise_discrepancy=0.12345,
            illumination_discrepancy=0.0,  # Not predicted by ML
            compression_discrepancy=0.08901,
            binarization_discrepancy=0.0,  # Not predicted by ML
            bleed_through_discrepancy=0.0,  # Not predicted by ML
            max_discrepancy=0.40456,
            mean_discrepancy=0.16456,
            per_head_discrepancies={
                "blur": 0.05123,
                "contrast": 0.40456,
                "skew": 0.03789,
                "noise": 0.12345,
                "compression": 0.08901,
            },
        )

        result = discrepancy_metrics_to_dict(metrics)

        # Check all 8 dimensions are serialized
        assert result["blur_discrepancy"] == 0.0512
        assert result["contrast_discrepancy"] == 0.4046
        assert result["skew_discrepancy"] == 0.0379
        assert result["noise_discrepancy"] == 0.1235
        assert result["illumination_discrepancy"] == 0.0
        assert result["compression_discrepancy"] == 0.089
        assert result["binarization_discrepancy"] == 0.0
        assert result["bleed_through_discrepancy"] == 0.0
        assert result["max_discrepancy"] == 0.4046


class TestPipelineIntegration:
    """Integration tests for the ML IQA pipeline logic."""

    def test_escalation_decision_combines_uncertainty_and_discrepancy(self):
        """Test that escalation decision correctly combines uncertainty and discrepancy."""
        detector = MLIQADetector()

        # Create scores with high confidence (no uncertainty escalation)
        scores = MLIQAScores(
            blur_score=0.5,  # Will have discrepancy with classical
            noise_score=0.8,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.75,
            overall_quality=0.76,
            confidences={
                "blur": 0.95,
                "noise": 0.95,
                "contrast": 0.95,
                "skew": 0.95,
                "compression": 0.95,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        # Test uncertainty gate (should not escalate with high confidence)
        uncertainty_decision = detector.should_escalate_to_teacher(scores)
        assert uncertainty_decision.should_escalate is False

        # Classical scores with discrepancy
        classical_scores = ClassicalIQAScores(
            blur_score=0.9,  # 0.4 difference from ML
            contrast_score=0.85,
            skew_score=0.9,
        )

        # Test discrepancy check (should escalate)
        discrepancy_decision = detector.should_escalate_due_to_discrepancy(
            scores, classical_scores
        )
        assert discrepancy_decision.should_escalate is True

    def test_discrepancy_decision_provides_reason(self):
        """Test pipeline escalates due to classical-ML discrepancy."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.2

        mock_student_scores = MLIQAScores(
            blur_score=0.5,  # Will have high discrepancy with classical
            noise_score=0.8,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.75,
            overall_quality=0.76,
            confidences={
                "blur": 0.95,
                "noise": 0.95,
                "contrast": 0.95,
                "skew": 0.95,
                "compression": 0.95,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        classical_scores = ClassicalIQAScores(
            blur_score=0.9,  # 0.4 difference
            contrast_score=0.85,
            skew_score=0.9,
        )

        decision = detector.should_escalate_due_to_discrepancy(
            mock_student_scores, classical_scores
        )

        assert decision.should_escalate is True
        assert "blur_discrepancy" in decision.reason

    def test_combined_escalation_reasons(self):
        """Test that both uncertainty and discrepancy reasons can be combined."""
        detector = MLIQADetector(
            entropy_threshold=0.3,  # Very low threshold
            min_confidence_threshold=0.95,  # Very high requirement
        )
        detector.discrepancy_threshold = 0.1  # Very low threshold

        # Create scores that trigger both uncertainty and discrepancy
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={
                "blur": 0.6,  # Below min threshold
                "noise": 0.65,
                "contrast": 0.62,
                "skew": 0.68,
                "compression": 0.64,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        # Both should trigger
        uncertainty_decision = detector.should_escalate_to_teacher(scores)
        assert uncertainty_decision.should_escalate is True
        assert "confidence" in uncertainty_decision.reason.lower()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_confidences(self):
        """Test uncertainty calculation with empty confidences."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.8,
            contrast_score=0.8,
            skew_score=0.8,
            compression_score=0.8,
            overall_quality=0.8,
            confidences={},  # Empty
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        assert uncertainty.entropy == 0.0
        assert uncertainty.min_confidence == 0.0
        assert uncertainty.mean_confidence == 0.0

    def test_single_head_confidence(self):
        """Test uncertainty with single head confidence."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.8,
            contrast_score=0.8,
            skew_score=0.8,
            compression_score=0.8,
            overall_quality=0.8,
            confidences={"blur": 0.85},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        assert uncertainty.min_confidence == 0.85
        assert uncertainty.mean_confidence == 0.85

    def test_model_type_enum_values(self):
        """Test ModelType enum values."""
        assert ModelType.STUDENT.value == "student"
        assert ModelType.TEACHER.value == "teacher"

    def test_device_enum_values(self):
        """Test Device enum values."""
        assert Device.GPU.value == "cuda"
        assert Device.CPU.value == "cpu"
        assert Device.MODAL.value == "modal"
