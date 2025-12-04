"""Unit tests for ML-based IQA detector (iqa_ml.py).

Tests edge cases, error handling, and validation logic that aren't covered
by integration tests. Integration tests focus on end-to-end workflows,
while these unit tests focus on specific methods and error paths.

Coverage targets:
- ClassicalIQAScores validation
- Device detection edge cases
- Model loading error paths
- Invalid image handling
- Uncertainty calculation edge cases
- Escalation decision logic
- Dict conversion utilities
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    Device,
    DiscrepancyMetrics,
    MLIQADetector,
    MLIQAScores,
    ModelType,
    UncertaintyMetrics,
    discrepancy_metrics_to_dict,
    ml_iqa_scores_to_dict,
    teacher_iqa_to_dict,
    uncertainty_metrics_to_dict,
)


class TestClassicalIQAScores:
    """Unit tests for ClassicalIQAScores validation."""

    def test_valid_scores_all_required(self):
        """Test valid scores with only required fields."""
        scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
        )
        assert scores.blur_score == pytest.approx(0.8)
        assert scores.contrast_score == pytest.approx(0.7)
        assert scores.skew_score == pytest.approx(0.9)
        # Check defaults
        assert scores.noise_score == pytest.approx(0.0)
        assert scores.illumination_score == pytest.approx(0.0)
        assert scores.compression_score == pytest.approx(0.0)

    def test_valid_scores_all_dimensions(self):
        """Test valid scores with all 8 dimensions."""
        scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.7,
            skew_score=0.9,
            noise_score=0.6,
            illumination_score=0.75,
            compression_score=0.85,
            binarization_score=0.95,
            bleed_through_score=0.5,
        )
        assert scores.blur_score == pytest.approx(0.8)
        assert scores.noise_score == pytest.approx(0.6)
        assert scores.binarization_score == pytest.approx(0.95)
        assert scores.bleed_through_score == pytest.approx(0.5)

    def test_invalid_blur_score_below_zero(self):
        """Test validation rejects blur_score < 0."""
        with pytest.raises(ValueError, match="blur_score must be in"):
            ClassicalIQAScores(
                blur_score=-0.1,
                contrast_score=0.7,
                skew_score=0.9,
            )

    def test_invalid_blur_score_above_one(self):
        """Test validation rejects blur_score > 1."""
        with pytest.raises(ValueError, match="blur_score must be in"):
            ClassicalIQAScores(
                blur_score=1.1,
                contrast_score=0.7,
                skew_score=0.9,
            )

    def test_invalid_contrast_score(self):
        """Test validation rejects invalid contrast_score."""
        with pytest.raises(ValueError, match="contrast_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=2.0,
                skew_score=0.9,
            )

    def test_invalid_skew_score(self):
        """Test validation rejects invalid skew_score."""
        with pytest.raises(ValueError, match="skew_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=0.7,
                skew_score=-0.5,
            )

    def test_invalid_noise_score(self):
        """Test validation rejects invalid noise_score."""
        with pytest.raises(ValueError, match="noise_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=0.7,
                skew_score=0.9,
                noise_score=1.5,
            )

    def test_invalid_illumination_score(self):
        """Test validation rejects invalid illumination_score."""
        with pytest.raises(ValueError, match="illumination_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=0.7,
                skew_score=0.9,
                illumination_score=-0.2,
            )

    def test_invalid_compression_score(self):
        """Test validation rejects invalid compression_score."""
        with pytest.raises(ValueError, match="compression_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=0.7,
                skew_score=0.9,
                compression_score=10.0,
            )

    def test_invalid_binarization_score(self):
        """Test validation rejects invalid binarization_score."""
        with pytest.raises(ValueError, match="binarization_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=0.7,
                skew_score=0.9,
                binarization_score=-1.0,
            )

    def test_invalid_bleed_through_score(self):
        """Test validation rejects invalid bleed_through_score."""
        with pytest.raises(ValueError, match="bleed_through_score must be in"):
            ClassicalIQAScores(
                blur_score=0.8,
                contrast_score=0.7,
                skew_score=0.9,
                bleed_through_score=5.0,
            )

    def test_boundary_scores_zero(self):
        """Test boundary case: all scores = 0.0 (valid)."""
        scores = ClassicalIQAScores(
            blur_score=0.0,
            contrast_score=0.0,
            skew_score=0.0,
            noise_score=0.0,
            illumination_score=0.0,
            compression_score=0.0,
            binarization_score=0.0,
            bleed_through_score=0.0,
        )
        assert scores.blur_score == pytest.approx(0.0)
        assert scores.bleed_through_score == pytest.approx(0.0)

    def test_boundary_scores_one(self):
        """Test boundary case: all scores = 1.0 (valid)."""
        scores = ClassicalIQAScores(
            blur_score=1.0,
            contrast_score=1.0,
            skew_score=1.0,
            noise_score=1.0,
            illumination_score=1.0,
            compression_score=1.0,
            binarization_score=1.0,
            bleed_through_score=1.0,
        )
        assert scores.blur_score == pytest.approx(1.0)
        assert scores.bleed_through_score == pytest.approx(1.0)


class TestMLIQADetectorDeviceDetection:
    """Unit tests for device detection edge cases."""

    @patch("image_preprocessing_detector.detection.iqa_ml.ort", None)
    def test_device_detection_no_onnxruntime(self):
        """Test device detection when ONNX Runtime not installed."""
        detector = MLIQADetector(device=None, use_orchestrator=False)
        # Should fall back to CPU when ort is None
        assert detector.device == Device.CPU

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_device_detection_gpu_available(self, mock_ort):
        """Test device detection when GPU available."""
        mock_ort.get_available_providers.return_value = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        detector = MLIQADetector(device=None, use_orchestrator=False)
        assert detector.device == Device.GPU

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_device_detection_gpu_unavailable(self, mock_ort):
        """Test device detection when GPU unavailable."""
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
        detector = MLIQADetector(device=None, use_orchestrator=False)
        assert detector.device == Device.CPU

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_device_detection_exception_handling(self, mock_ort):
        """Test device detection handles exceptions gracefully."""
        mock_ort.get_available_providers.side_effect = RuntimeError(
            "Provider detection failed"
        )
        detector = MLIQADetector(device=None, use_orchestrator=False)
        # Should fall back to CPU on exception
        assert detector.device == Device.CPU

    def test_explicit_device_selection(self):
        """Test explicit device selection overrides auto-detection."""
        detector = MLIQADetector(device=Device.MODAL, use_orchestrator=False)
        assert detector.device == Device.MODAL


class TestMLIQADetectorModelLoading:
    """Unit tests for model loading error paths."""

    def test_load_student_model_path_none(self):
        """Test student model loading fails when path is None."""
        detector = MLIQADetector(student_model_path=None)
        with pytest.raises(ValueError, match="Student model path not set"):
            detector._load_student_session()

    def test_load_student_model_not_found(self):
        """Test student model loading fails when file doesn't exist."""
        detector = MLIQADetector(student_model_path="/nonexistent/model.onnx")
        with pytest.raises(FileNotFoundError, match="Student model not found"):
            detector._load_student_session()

    @patch("image_preprocessing_detector.detection.iqa_ml.ort", None)
    def test_load_student_model_onnx_not_installed(self):
        """Test student model loading fails when ONNX Runtime not installed."""
        # Create a fake model file to pass the existence check
        fake_model = Path("fake_student_onnx.onnx")
        fake_model.touch()

        try:
            detector = MLIQADetector(student_model_path=str(fake_model))
            with pytest.raises(RuntimeError, match="ONNX Runtime not installed"):
                detector._load_student_session()
        finally:
            fake_model.unlink()

    def test_load_teacher_model_path_none(self):
        """Test teacher model loading fails when path is None."""
        detector = MLIQADetector(teacher_model_path=None)
        with pytest.raises(ValueError, match="Teacher model path not set"):
            detector._load_teacher_session()

    def test_load_teacher_model_not_found(self):
        """Test teacher model loading fails when file doesn't exist."""
        detector = MLIQADetector(teacher_model_path="/nonexistent/model.onnx")
        with pytest.raises(FileNotFoundError, match="Teacher model not found"):
            detector._load_teacher_session()

    @patch("image_preprocessing_detector.detection.iqa_ml.ort", None)
    def test_load_teacher_model_onnx_not_installed(self):
        """Test teacher model loading fails when ONNX Runtime not installed."""
        # Create a fake model file to pass the existence check
        fake_model = Path("fake_teacher_onnx.onnx")
        fake_model.touch()

        try:
            detector = MLIQADetector(teacher_model_path=str(fake_model))
            with pytest.raises(RuntimeError, match="ONNX Runtime not installed"):
                detector._load_teacher_session()
        finally:
            fake_model.unlink()

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_load_student_session_caching(self, mock_ort):
        """Test student session is cached after first load (legacy mode)."""
        # Create a fake model file
        fake_model = Path("fake_student.onnx")
        fake_model.touch()

        try:
            mock_session = MagicMock()
            mock_ort.InferenceSession.return_value = mock_session

            # Use legacy mode for consistent caching behavior
            detector = MLIQADetector(
                student_model_path=str(fake_model), use_orchestrator=False
            )
            # First load
            session1 = detector._load_student_session()
            # Second load (should return cached session)
            session2 = detector._load_student_session()

            assert session1 is session2
            # InferenceSession should only be called once
            assert mock_ort.InferenceSession.call_count == 1
        finally:
            fake_model.unlink()

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_load_teacher_session_caching(self, mock_ort):
        """Test teacher session is cached after first load (legacy mode)."""
        fake_model = Path("fake_teacher.onnx")
        fake_model.touch()

        try:
            mock_session = MagicMock()
            mock_ort.InferenceSession.return_value = mock_session

            # Use legacy mode for consistent caching behavior
            detector = MLIQADetector(
                teacher_model_path=str(fake_model), use_orchestrator=False
            )
            session1 = detector._load_teacher_session()
            session2 = detector._load_teacher_session()

            assert session1 is session2
            assert mock_ort.InferenceSession.call_count == 1
        finally:
            fake_model.unlink()


class TestMLIQADetectorInvalidImages:
    """Unit tests for invalid image handling."""

    def test_student_inference_none_image(self):
        """Test student inference rejects None image."""
        detector = MLIQADetector()
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.run_student_inference(None)

    def test_student_inference_empty_array(self):
        """Test student inference rejects empty array."""
        detector = MLIQADetector()
        empty_img = np.array([])
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.run_student_inference(empty_img)

    def test_teacher_inference_none_image(self):
        """Test teacher inference rejects None image."""
        detector = MLIQADetector()
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.run_teacher_inference(None)

    def test_teacher_inference_empty_array(self):
        """Test teacher inference rejects empty array."""
        detector = MLIQADetector()
        empty_img = np.array([])
        with pytest.raises(ValueError, match="Invalid or empty image"):
            detector.run_teacher_inference(empty_img)


class TestUncertaintyCalculation:
    """Unit tests for uncertainty calculation edge cases."""

    def test_calculate_uncertainty_empty_confidences(self):
        """Test uncertainty calculation with no confidences."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={},  # Empty confidences
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        # Should return zeros for empty confidences
        assert uncertainty.entropy == pytest.approx(0.0)
        assert uncertainty.min_confidence == pytest.approx(0.0)
        assert uncertainty.mean_confidence == pytest.approx(0.0)
        assert uncertainty.head_confidences == {}

    def test_calculate_uncertainty_edge_case_zero_confidence(self):
        """Test entropy calculation with zero confidence (log(0) edge case)."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={"blur": 0.0, "noise": 0.5},  # Zero confidence
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        # Should handle log(0) gracefully (entropy should be finite)
        assert 0.0 <= uncertainty.entropy <= 1.0
        assert uncertainty.min_confidence == pytest.approx(0.0)
        assert uncertainty.mean_confidence == pytest.approx(0.25)

    def test_calculate_uncertainty_edge_case_one_confidence(self):
        """Test entropy calculation with confidence = 1.0 (certain prediction)."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={"blur": 1.0, "noise": 1.0},  # Maximum confidence
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        # Entropy should be 0 for certain predictions
        assert uncertainty.entropy == pytest.approx(0.0)
        assert uncertainty.min_confidence == pytest.approx(1.0)
        assert uncertainty.mean_confidence == pytest.approx(1.0)

    def test_calculate_uncertainty_normal_case(self):
        """Test uncertainty calculation with typical confidence values."""
        detector = MLIQADetector()
        scores = MLIQAScores(
            blur_score=0.7,
            noise_score=0.6,
            contrast_score=0.8,
            skew_score=0.9,
            compression_score=0.75,
            overall_quality=0.75,
            confidences={
                "blur": 0.7,
                "noise": 0.6,
                "contrast": 0.8,
                "skew": 0.9,
                "compression": 0.75,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=15.0,
        )

        uncertainty = detector.calculate_uncertainty(scores)

        # Validate metrics are in reasonable ranges
        assert 0.0 <= uncertainty.entropy <= 1.0
        assert 0.6 <= uncertainty.min_confidence <= 1.0
        assert 0.7 <= uncertainty.mean_confidence <= 0.8
        assert len(uncertainty.head_confidences) == 5


class TestEscalationDecisionLogic:
    """Unit tests for escalation decision logic branches."""

    def test_no_escalation_all_conditions_pass(self):
        """Test no escalation when all conditions below thresholds."""
        detector = MLIQADetector(
            entropy_threshold=0.8,
            min_confidence_threshold=0.6,
            mean_confidence_threshold=0.7,
        )
        scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.8,
            contrast_score=0.8,
            skew_score=0.8,
            compression_score=0.8,
            overall_quality=0.8,
            confidences={
                "blur": 0.9,
                "noise": 0.85,
                "contrast": 0.95,
                "skew": 0.9,
                "compression": 0.88,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        assert not decision.should_escalate
        assert decision.reason is None

    def test_escalation_high_entropy(self):
        """Test escalation when entropy exceeds threshold."""
        detector = MLIQADetector(
            entropy_threshold=0.5,
            min_confidence_threshold=0.6,
            mean_confidence_threshold=0.7,
        )
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={
                "blur": 0.5,  # Maximum entropy (0.5 confidence)
                "noise": 0.5,
                "contrast": 0.5,
                "skew": 0.5,
                "compression": 0.5,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        assert decision.should_escalate
        assert "high_entropy" in decision.reason

    def test_escalation_low_min_confidence(self):
        """Test escalation when min confidence below threshold."""
        detector = MLIQADetector(
            entropy_threshold=0.9,
            min_confidence_threshold=0.7,
            mean_confidence_threshold=0.6,
        )
        scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.8,
            contrast_score=0.8,
            skew_score=0.8,
            compression_score=0.8,
            overall_quality=0.8,
            confidences={
                "blur": 0.9,
                "noise": 0.85,
                "contrast": 0.6,  # Below min_confidence_threshold
                "skew": 0.95,
                "compression": 0.88,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        assert decision.should_escalate
        assert "low_min_confidence" in decision.reason

    def test_escalation_low_mean_confidence(self):
        """Test escalation when mean confidence below threshold."""
        detector = MLIQADetector(
            entropy_threshold=0.9,
            min_confidence_threshold=0.5,
            mean_confidence_threshold=0.75,
        )
        scores = MLIQAScores(
            blur_score=0.7,
            noise_score=0.7,
            contrast_score=0.7,
            skew_score=0.7,
            compression_score=0.7,
            overall_quality=0.7,
            confidences={
                "blur": 0.65,
                "noise": 0.60,
                "contrast": 0.70,
                "skew": 0.68,
                "compression": 0.62,
            },  # Mean = 0.65 < 0.75
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        assert decision.should_escalate
        assert "low_mean_confidence" in decision.reason

    def test_escalation_multiple_conditions(self):
        """Test escalation with multiple conditions triggering."""
        detector = MLIQADetector(
            entropy_threshold=0.5,
            min_confidence_threshold=0.7,
            mean_confidence_threshold=0.8,
        )
        scores = MLIQAScores(
            blur_score=0.5,
            noise_score=0.5,
            contrast_score=0.5,
            skew_score=0.5,
            compression_score=0.5,
            overall_quality=0.5,
            confidences={
                "blur": 0.5,
                "noise": 0.5,
                "contrast": 0.5,
                "skew": 0.5,
                "compression": 0.5,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )

        decision = detector.should_escalate_to_teacher(scores)

        assert decision.should_escalate
        # Should have multiple reasons joined with semicolon
        assert "high_entropy" in decision.reason
        assert "low_min_confidence" in decision.reason
        assert "low_mean_confidence" in decision.reason


class TestDiscrepancyEscalationLogic:
    """Unit tests for discrepancy-based escalation logic."""

    def test_no_discrepancy_escalation(self):
        """Test no escalation when all discrepancies below threshold."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.3
        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.75,
            skew_score=0.9,
            compression_score=0.85,
            overall_quality=0.8,
            confidences={"blur": 0.9, "noise": 0.85, "contrast": 0.8},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.82,  # Discrepancy = 0.02
            contrast_score=0.78,  # Discrepancy = 0.03
            skew_score=0.88,  # Discrepancy = 0.02
            noise_score=0.68,  # Discrepancy = 0.02
            compression_score=0.87,  # Discrepancy = 0.02
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert not decision.should_escalate
        assert decision.reason is None

    def test_blur_discrepancy_escalation(self):
        """Test escalation when blur discrepancy exceeds threshold."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.3
        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.75,
            skew_score=0.9,
            compression_score=0.85,
            overall_quality=0.8,
            confidences={"blur": 0.9},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.45,  # Large discrepancy = 0.35
            contrast_score=0.75,
            skew_score=0.9,
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert decision.should_escalate
        assert "blur_discrepancy" in decision.reason

    def test_contrast_discrepancy_escalation(self):
        """Test escalation when contrast discrepancy exceeds threshold."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.25
        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.9,
            skew_score=0.85,
            compression_score=0.85,
            overall_quality=0.8,
            confidences={"contrast": 0.9},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.6,  # Discrepancy = 0.3
            skew_score=0.85,
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert decision.should_escalate
        assert "contrast_discrepancy" in decision.reason

    def test_skew_discrepancy_escalation(self):
        """Test escalation when skew discrepancy exceeds threshold."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.3
        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.75,
            skew_score=0.95,
            compression_score=0.85,
            overall_quality=0.8,
            confidences={"skew": 0.95},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.75,
            skew_score=0.6,  # Discrepancy = 0.35
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert decision.should_escalate
        assert "skew_discrepancy" in decision.reason

    def test_noise_discrepancy_escalation(self):
        """Test escalation when noise discrepancy exceeds threshold."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.3
        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.85,
            contrast_score=0.75,
            skew_score=0.9,
            compression_score=0.85,
            overall_quality=0.8,
            confidences={"noise": 0.9},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.75,
            skew_score=0.9,
            noise_score=0.5,  # Discrepancy = 0.35
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert decision.should_escalate
        assert "noise_discrepancy" in decision.reason

    def test_compression_discrepancy_escalation(self):
        """Test escalation when compression discrepancy exceeds threshold."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.3
        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.7,
            contrast_score=0.75,
            skew_score=0.9,
            compression_score=0.9,
            overall_quality=0.8,
            confidences={"compression": 0.9},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.8,
            contrast_score=0.75,
            skew_score=0.9,
            compression_score=0.55,  # Discrepancy = 0.35
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert decision.should_escalate
        assert "compression_discrepancy" in decision.reason

    def test_multiple_discrepancies(self):
        """Test escalation with multiple discrepancies."""
        detector = MLIQADetector()
        detector.discrepancy_threshold = 0.25
        student_scores = MLIQAScores(
            blur_score=0.9,
            noise_score=0.85,
            contrast_score=0.9,
            skew_score=0.95,
            compression_score=0.9,
            overall_quality=0.9,
            confidences={
                "blur": 0.95,
                "noise": 0.9,
                "contrast": 0.95,
            },
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=10.0,
        )
        classical_scores = ClassicalIQAScores(
            blur_score=0.6,  # Discrepancy = 0.3
            contrast_score=0.6,  # Discrepancy = 0.3
            skew_score=0.95,
            noise_score=0.55,  # Discrepancy = 0.3
        )

        decision = detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        assert decision.should_escalate
        # Multiple discrepancies should be listed
        assert "blur_discrepancy" in decision.reason
        assert "contrast_discrepancy" in decision.reason
        assert "noise_discrepancy" in decision.reason


class TestDictConversionUtilities:
    """Unit tests for dict conversion utilities."""

    def test_ml_iqa_scores_to_dict(self):
        """Test MLIQAScores to dict conversion."""
        scores = MLIQAScores(
            blur_score=0.8234,
            noise_score=0.7567,
            contrast_score=0.9123,
            skew_score=0.8876,
            compression_score=0.7890,
            overall_quality=0.8338,
            confidences={"blur": 0.9234, "noise": 0.8567},
            model_type=ModelType.STUDENT,
            device=Device.GPU,
            inference_time_ms=12.3456,
        )

        result = ml_iqa_scores_to_dict(scores)

        assert result["source"] == "student"
        assert result["blur_score"] == pytest.approx(0.8234)
        assert result["overall_quality"] == pytest.approx(0.8338)
        assert result["device"] == "cuda"
        assert result["inference_time_ms"] == pytest.approx(
            12.35
        )  # Rounded to 2 decimals
        assert result["confidences"]["blur"] == pytest.approx(0.9234)

    def test_teacher_iqa_to_dict(self):
        """Test teacher IQA scores to dict conversion."""
        scores = MLIQAScores(
            blur_score=0.9,
            noise_score=0.85,
            contrast_score=0.95,
            skew_score=0.92,
            compression_score=0.88,
            overall_quality=0.9,
            confidences={"blur": 0.95, "noise": 0.9},
            model_type=ModelType.TEACHER,
            device=Device.GPU,
            inference_time_ms=25.6789,
        )

        result = teacher_iqa_to_dict(scores, "high_entropy (0.856 >= 0.8)")

        assert result["source"] == "teacher"
        assert result["escalation_reason"] == "high_entropy (0.856 >= 0.8)"
        assert result["overall_quality"] == pytest.approx(0.9)
        assert result["inference_time_ms"] == pytest.approx(25.68)

    def test_uncertainty_metrics_to_dict(self):
        """Test UncertaintyMetrics to dict conversion."""
        metrics = UncertaintyMetrics(
            entropy=0.8567,
            min_confidence=0.6234,
            mean_confidence=0.7890,
            head_confidences={
                "blur": 0.9234,
                "noise": 0.6234,
                "contrast": 0.8567,
            },
        )

        result = uncertainty_metrics_to_dict(metrics)

        assert result["entropy"] == pytest.approx(0.8567)
        assert result["min_confidence"] == pytest.approx(0.6234)
        assert result["mean_confidence"] == pytest.approx(0.7890)
        assert result["head_confidences"]["blur"] == pytest.approx(0.9234)

    def test_discrepancy_metrics_to_dict(self):
        """Test DiscrepancyMetrics to dict conversion."""
        metrics = DiscrepancyMetrics(
            blur_discrepancy=0.3456,
            contrast_discrepancy=0.2789,
            skew_discrepancy=0.1234,
            noise_discrepancy=0.2567,
            illumination_discrepancy=0.0,
            compression_discrepancy=0.1890,
            binarization_discrepancy=0.0,
            bleed_through_discrepancy=0.0,
            max_discrepancy=0.3456,
            mean_discrepancy=0.2387,
            per_head_discrepancies={
                "blur": 0.3456,
                "contrast": 0.2789,
                "skew": 0.1234,
                "noise": 0.2567,
                "compression": 0.1890,
            },
        )

        result = discrepancy_metrics_to_dict(metrics)

        assert result["blur_discrepancy"] == pytest.approx(0.3456)
        assert result["max_discrepancy"] == pytest.approx(0.3456)
        assert result["mean_discrepancy"] == pytest.approx(0.2387)
        assert result["per_head_discrepancies"]["blur"] == pytest.approx(0.3456)
