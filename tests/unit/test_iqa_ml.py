"""Unit tests for ML IQA detector (teacher-student architecture).

Tests cover:
- Initialization with different configurations
- Device detection and selection
- Student model inference
- Teacher model inference
- Uncertainty metrics calculation
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
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
)


class TestMLIQADetector:
    """Test MLIQADetector class."""

    def test_init_default_params(self) -> None:
        """Test MLIQADetector initialization with defaults."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            assert detector.student_model_path is None
            assert detector.teacher_model_path is None
            assert detector.device == Device.CPU
            assert detector.enable_modal_fallback is True

    def test_init_with_model_paths(self) -> None:
        """Test initialization with model paths."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                student_model_path="models/iqa/student.onnx",
                teacher_model_path="models/iqa/teacher.onnx",
                device=Device.GPU,
                enable_modal_fallback=False,
            )

            assert str(detector.student_model_path) == "models/iqa/student.onnx"
            assert str(detector.teacher_model_path) == "models/iqa/teacher.onnx"
            assert detector.device == Device.GPU
            assert detector.enable_modal_fallback is False

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_detect_device_gpu_available(self, mock_ort: Mock) -> None:
        """Test device detection when GPU is available."""
        mock_ort.get_available_providers.return_value = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]

        detector = MLIQADetector()
        assert detector.device == Device.GPU

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    def test_detect_device_cpu_only(self, mock_ort: Mock) -> None:
        """Test device detection when only CPU is available."""
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]

        detector = MLIQADetector()
        assert detector.device == Device.CPU

    def test_detect_device_onnxruntime_not_available(self) -> None:
        """Test device detection when ONNX Runtime is not installed."""
        with patch(
            "image_preprocessing_detector.detection.iqa_ml.ort", side_effect=ImportError
        ):
            detector = MLIQADetector()
            assert detector.device == Device.CPU

    def test_get_ort_providers_gpu(self) -> None:
        """Test ONNX Runtime provider selection for GPU."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.GPU):
            detector = MLIQADetector(device=Device.GPU)
            providers = detector._get_ort_providers()

            assert providers == ["CUDAExecutionProvider", "CPUExecutionProvider"]

    def test_get_ort_providers_cpu(self) -> None:
        """Test ONNX Runtime provider selection for CPU."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(device=Device.CPU)
            providers = detector._get_ort_providers()

            assert providers == ["CPUExecutionProvider"]

    def test_preprocess_image(self) -> None:
        """Test image preprocessing."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            # Create synthetic image (500x500x3, BGR)
            rng = np.random.default_rng(seed=42)
            image = rng.integers(0, 256, (500, 500, 3), dtype=np.uint8)

            preprocessed = detector._preprocess_image(image)

            # Check output shape: (1, 3, 224, 224)
            assert preprocessed.shape == (1, 3, 224, 224)
            assert preprocessed.dtype == np.float32

            # Check normalization (should be centered around 0 after ImageNet normalization)
            assert preprocessed.min() < 0  # Some negative values expected
            assert preprocessed.max() > 0  # Some positive values expected

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_student_session(self, mock_exists: Mock, mock_ort: Mock) -> None:
        """Test loading student model session."""
        mock_session = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session

        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(student_model_path="models/iqa/student.onnx")
            session = detector._load_student_session()

            assert session == mock_session
            mock_ort.InferenceSession.assert_called_once()

    @patch("pathlib.Path.exists", return_value=False)
    def test_load_student_session_file_not_found(self, mock_exists: Mock) -> None:
        """Test loading student session with missing file."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(student_model_path="models/iqa/missing.onnx")

            with pytest.raises(FileNotFoundError, match="Student model not found"):
                detector._load_student_session()

    def test_load_student_session_no_path(self) -> None:
        """Test loading student session without model path."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            with pytest.raises(ValueError, match="Student model path not set"):
                detector._load_student_session()

    @patch("image_preprocessing_detector.detection.iqa_ml.ort")
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_teacher_session(self, mock_exists: Mock, mock_ort: Mock) -> None:
        """Test loading teacher model session."""
        mock_session = MagicMock()
        mock_ort.InferenceSession.return_value = mock_session

        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(teacher_model_path="models/iqa/teacher.onnx")
            session = detector._load_teacher_session()

            assert session == mock_session
            mock_ort.InferenceSession.assert_called_once()

    def test_postprocess_outputs(self) -> None:
        """Test postprocessing of model outputs."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            # Mock model outputs (logits for 5 heads, binary classification)
            outputs = {
                "head_0": np.array([[0.2, 0.8]]),  # blur: high quality
                "head_1": np.array([[0.3, 0.7]]),  # noise: good quality
                "head_2": np.array([[0.4, 0.6]]),  # contrast: moderate quality
                "head_3": np.array([[0.5, 0.5]]),  # skew: uncertain
                "head_4": np.array([[0.1, 0.9]]),  # compression: excellent quality
            }

            scores, confidences = detector._postprocess_outputs(outputs)

            # Check scores (probability of good class)
            assert "blur_score" in scores
            assert "noise_score" in scores
            assert "contrast_score" in scores
            assert "skew_score" in scores
            assert "compression_score" in scores

            # All scores should be between 0 and 1
            for score in scores.values():
                assert 0.0 <= score <= 1.0

            # Check confidences
            assert "blur" in confidences
            assert "noise" in confidences
            assert "contrast" in confidences
            assert "skew" in confidences
            assert "compression" in confidences

            # All confidences should be between 0 and 1
            for conf in confidences.values():
                assert 0.0 <= conf <= 1.0

    @patch.object(MLIQADetector, "_load_student_session")
    @patch.object(MLIQADetector, "_preprocess_image")
    def test_run_student_inference(
        self, mock_preprocess: Mock, mock_load_session: Mock
    ) -> None:
        """Test running student model inference."""
        # Mock preprocessing
        mock_preprocess.return_value = np.zeros((1, 3, 224, 224), dtype=np.float32)

        # Mock ONNX session
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_session.get_inputs.return_value = [mock_input]

        mock_output_0 = MagicMock()
        mock_output_0.name = "head_0"
        mock_output_1 = MagicMock()
        mock_output_1.name = "head_1"
        mock_output_2 = MagicMock()
        mock_output_2.name = "head_2"
        mock_output_3 = MagicMock()
        mock_output_3.name = "head_3"
        mock_output_4 = MagicMock()
        mock_output_4.name = "head_4"

        mock_session.get_outputs.return_value = [
            mock_output_0,
            mock_output_1,
            mock_output_2,
            mock_output_3,
            mock_output_4,
        ]

        # Mock inference outputs
        mock_session.run.return_value = [
            np.array([[0.2, 0.8]]),  # blur
            np.array([[0.3, 0.7]]),  # noise
            np.array([[0.4, 0.6]]),  # contrast
            np.array([[0.5, 0.5]]),  # skew
            np.array([[0.1, 0.9]]),  # compression
        ]

        mock_load_session.return_value = mock_session

        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(student_model_path="models/iqa/student.onnx")

            # Create test image
            rng = np.random.default_rng(seed=42)
            image = rng.integers(0, 256, (500, 500, 3), dtype=np.uint8)

            # Run inference
            result = detector.run_student_inference(image)

            # Validate result
            assert isinstance(result, MLIQAScores)
            assert result.model_type == ModelType.STUDENT
            assert result.device == Device.CPU
            assert 0.0 <= result.overall_quality <= 1.0
            assert result.inference_time_ms > 0

            # Check all scores are present
            assert 0.0 <= result.blur_score <= 1.0
            assert 0.0 <= result.noise_score <= 1.0
            assert 0.0 <= result.contrast_score <= 1.0
            assert 0.0 <= result.skew_score <= 1.0
            assert 0.0 <= result.compression_score <= 1.0

    @patch.object(MLIQADetector, "_load_teacher_session")
    @patch.object(MLIQADetector, "_preprocess_image")
    def test_run_teacher_inference(
        self, mock_preprocess: Mock, mock_load_session: Mock
    ) -> None:
        """Test running teacher model inference."""
        # Mock preprocessing
        mock_preprocess.return_value = np.zeros((1, 3, 224, 224), dtype=np.float32)

        # Mock ONNX session
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_session.get_inputs.return_value = [mock_input]

        mock_output_0 = MagicMock()
        mock_output_0.name = "head_0"
        mock_output_1 = MagicMock()
        mock_output_1.name = "head_1"
        mock_output_2 = MagicMock()
        mock_output_2.name = "head_2"
        mock_output_3 = MagicMock()
        mock_output_3.name = "head_3"
        mock_output_4 = MagicMock()
        mock_output_4.name = "head_4"

        mock_session.get_outputs.return_value = [
            mock_output_0,
            mock_output_1,
            mock_output_2,
            mock_output_3,
            mock_output_4,
        ]

        # Mock inference outputs
        mock_session.run.return_value = [
            np.array([[0.1, 0.9]]),  # blur: excellent
            np.array([[0.2, 0.8]]),  # noise: very good
            np.array([[0.3, 0.7]]),  # contrast: good
            np.array([[0.4, 0.6]]),  # skew: moderate
            np.array([[0.5, 0.5]]),  # compression: uncertain
        ]

        mock_load_session.return_value = mock_session

        with patch.object(MLIQADetector, "_detect_device", return_value=Device.GPU):
            detector = MLIQADetector(teacher_model_path="models/iqa/teacher.onnx")

            # Create test image
            rng = np.random.default_rng(seed=42)
            image = rng.integers(0, 256, (500, 500, 3), dtype=np.uint8)

            # Run inference
            result = detector.run_teacher_inference(image)

            # Validate result
            assert isinstance(result, MLIQAScores)
            assert result.model_type == ModelType.TEACHER
            assert result.device == Device.GPU
            assert 0.0 <= result.overall_quality <= 1.0
            assert result.inference_time_ms > 0

    def test_run_student_inference_invalid_image(self) -> None:
        """Test student inference with invalid image."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(student_model_path="models/iqa/student.onnx")

            with pytest.raises(ValueError, match="Invalid or empty image"):
                detector.run_student_inference(None)  # type: ignore

            with pytest.raises(ValueError, match="Invalid or empty image"):
                detector.run_student_inference(np.array([]))

    def test_run_teacher_inference_invalid_image(self) -> None:
        """Test teacher inference with invalid image."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(teacher_model_path="models/iqa/teacher.onnx")

            with pytest.raises(ValueError, match="Invalid or empty image"):
                detector.run_teacher_inference(None)  # type: ignore

            with pytest.raises(ValueError, match="Invalid or empty image"):
                detector.run_teacher_inference(np.array([]))

    def test_calculate_uncertainty(self) -> None:
        """Test uncertainty metrics calculation."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            # Create mock scores with varying confidences
            scores = MLIQAScores(
                blur_score=0.85,
                noise_score=0.75,
                contrast_score=0.65,
                skew_score=0.55,
                compression_score=0.90,
                overall_quality=0.74,
                confidences={
                    "blur": 0.85,
                    "noise": 0.75,
                    "contrast": 0.65,
                    "skew": 0.55,  # Low confidence
                    "compression": 0.90,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=25.5,
            )

            uncertainty = detector.calculate_uncertainty(scores)

            # Validate uncertainty metrics
            assert isinstance(uncertainty, UncertaintyMetrics)
            assert 0.0 <= uncertainty.entropy <= 1.0  # Binary entropy max is 1.0
            assert uncertainty.min_confidence == pytest.approx(
                0.55
            )  # Lowest confidence
            assert 0.0 <= uncertainty.mean_confidence <= 1.0
            assert len(uncertainty.head_confidences) == 5

    def test_calculate_uncertainty_high_confidence(self) -> None:
        """Test uncertainty calculation with high confidence (should have low entropy)."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            # High confidence scores
            scores = MLIQAScores(
                blur_score=0.95,
                noise_score=0.92,
                contrast_score=0.94,
                skew_score=0.93,
                compression_score=0.96,
                overall_quality=0.94,
                confidences={
                    "blur": 0.95,
                    "noise": 0.92,
                    "contrast": 0.94,
                    "skew": 0.93,
                    "compression": 0.96,
                },
                model_type=ModelType.STUDENT,
                device=Device.GPU,
                inference_time_ms=15.2,
            )

            uncertainty = detector.calculate_uncertainty(scores)

            # High confidence should result in low entropy
            assert uncertainty.entropy < 0.5
            assert uncertainty.min_confidence > 0.9
            assert uncertainty.mean_confidence > 0.9

    def test_calculate_uncertainty_low_confidence(self) -> None:
        """Test uncertainty calculation with low confidence (should have high entropy)."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            # Low confidence scores (near 0.5 = maximum uncertainty)
            scores = MLIQAScores(
                blur_score=0.52,
                noise_score=0.48,
                contrast_score=0.51,
                skew_score=0.49,
                compression_score=0.50,
                overall_quality=0.50,
                confidences={
                    "blur": 0.52,
                    "noise": 0.52,
                    "contrast": 0.51,
                    "skew": 0.51,
                    "compression": 0.50,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=30.1,
            )

            uncertainty = detector.calculate_uncertainty(scores)

            # Low confidence (near 0.5) should result in high entropy (near 1.0)
            assert uncertainty.entropy > 0.9  # Close to maximum uncertainty
            assert uncertainty.min_confidence < 0.55
            assert 0.4 <= uncertainty.mean_confidence <= 0.6

    def test_should_escalate_to_teacher_high_entropy(self) -> None:
        """Test escalation decision with high entropy."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                entropy_threshold=0.7,
                min_confidence_threshold=0.6,
                mean_confidence_threshold=0.7,
            )

            # Low confidence scores (high entropy)
            scores = MLIQAScores(
                blur_score=0.52,
                noise_score=0.48,
                contrast_score=0.51,
                skew_score=0.49,
                compression_score=0.50,
                overall_quality=0.50,
                confidences={
                    "blur": 0.52,
                    "noise": 0.52,
                    "contrast": 0.51,
                    "skew": 0.51,
                    "compression": 0.50,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=25.0,
            )

            decision = detector.should_escalate_to_teacher(scores)

            # Should escalate due to high entropy
            assert isinstance(decision, EscalationDecision)
            assert decision.should_escalate is True
            assert decision.reason is not None
            assert "high_entropy" in decision.reason
            assert isinstance(decision.uncertainty_metrics, UncertaintyMetrics)

    def test_should_escalate_to_teacher_low_min_confidence(self) -> None:
        """Test escalation decision with low minimum confidence."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                entropy_threshold=0.8,
                min_confidence_threshold=0.7,
                mean_confidence_threshold=0.65,
            )

            # One head has very low confidence
            scores = MLIQAScores(
                blur_score=0.85,
                noise_score=0.80,
                contrast_score=0.75,
                skew_score=0.55,  # Low confidence here
                compression_score=0.90,
                overall_quality=0.77,
                confidences={
                    "blur": 0.85,
                    "noise": 0.80,
                    "contrast": 0.75,
                    "skew": 0.55,  # Below threshold
                    "compression": 0.90,
                },
                model_type=ModelType.STUDENT,
                device=Device.GPU,
                inference_time_ms=15.0,
            )

            decision = detector.should_escalate_to_teacher(scores)

            # Should escalate due to low min confidence
            assert decision.should_escalate is True
            assert decision.reason is not None
            assert "low_min_confidence" in decision.reason

    def test_should_escalate_to_teacher_low_mean_confidence(self) -> None:
        """Test escalation decision with low mean confidence."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                entropy_threshold=0.9,
                min_confidence_threshold=0.5,
                mean_confidence_threshold=0.7,
            )

            # All heads have moderate but below-threshold confidence
            scores = MLIQAScores(
                blur_score=0.65,
                noise_score=0.62,
                contrast_score=0.68,
                skew_score=0.60,
                compression_score=0.67,
                overall_quality=0.64,
                confidences={
                    "blur": 0.65,
                    "noise": 0.62,
                    "contrast": 0.68,
                    "skew": 0.60,
                    "compression": 0.67,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=28.0,
            )

            decision = detector.should_escalate_to_teacher(scores)

            # Should escalate due to low mean confidence
            assert decision.should_escalate is True
            assert decision.reason is not None
            assert "low_mean_confidence" in decision.reason

    def test_should_not_escalate_to_teacher(self) -> None:
        """Test no escalation with high confidence scores."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                entropy_threshold=0.8,
                min_confidence_threshold=0.6,
                mean_confidence_threshold=0.7,
            )

            # High confidence scores across all heads
            scores = MLIQAScores(
                blur_score=0.92,
                noise_score=0.88,
                contrast_score=0.91,
                skew_score=0.85,
                compression_score=0.94,
                overall_quality=0.90,
                confidences={
                    "blur": 0.92,
                    "noise": 0.88,
                    "contrast": 0.91,
                    "skew": 0.85,
                    "compression": 0.94,
                },
                model_type=ModelType.STUDENT,
                device=Device.GPU,
                inference_time_ms=12.0,
            )

            decision = detector.should_escalate_to_teacher(scores)

            # Should NOT escalate
            assert decision.should_escalate is False
            assert decision.reason is None
            assert isinstance(decision.uncertainty_metrics, UncertaintyMetrics)

    def test_should_escalate_multiple_reasons(self) -> None:
        """Test escalation with multiple triggering conditions."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector(
                entropy_threshold=0.7,
                min_confidence_threshold=0.7,
                mean_confidence_threshold=0.7,
            )

            # Low confidence on all metrics
            scores = MLIQAScores(
                blur_score=0.55,
                noise_score=0.52,
                contrast_score=0.54,
                skew_score=0.50,
                compression_score=0.53,
                overall_quality=0.53,
                confidences={
                    "blur": 0.55,
                    "noise": 0.52,
                    "contrast": 0.54,
                    "skew": 0.50,
                    "compression": 0.53,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=30.0,
            )

            decision = detector.should_escalate_to_teacher(scores)

            # Should escalate with multiple reasons
            assert decision.should_escalate is True
            assert decision.reason is not None
            # Should have at least 2 reasons
            assert len(decision.reason.split(";")) >= 2

    def test_calculate_discrepancy(self) -> None:
        """Test discrepancy calculation between student and classical IQA."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            student_scores = MLIQAScores(
                blur_score=0.85,
                noise_score=0.80,
                contrast_score=0.75,
                skew_score=0.90,
                compression_score=0.88,
                overall_quality=0.84,
                confidences={
                    "blur": 0.85,
                    "noise": 0.80,
                    "contrast": 0.75,
                    "skew": 0.90,
                    "compression": 0.88,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=25.0,
            )

            classical_scores = ClassicalIQAScores(
                blur_score=0.90,  # 0.05 difference
                contrast_score=0.65,  # 0.10 difference
                skew_score=0.95,  # 0.05 difference
                noise_score=0.78,  # 0.02 difference
                compression_score=0.86,  # 0.02 difference
            )

            discrepancy = detector.calculate_discrepancy(
                student_scores, classical_scores
            )

            # Validate discrepancy metrics
            assert isinstance(discrepancy, DiscrepancyMetrics)
            assert abs(discrepancy.blur_discrepancy - 0.05) < 0.01
            assert abs(discrepancy.contrast_discrepancy - 0.10) < 0.01
            assert abs(discrepancy.skew_discrepancy - 0.05) < 0.01
            assert abs(discrepancy.noise_discrepancy - 0.02) < 0.01
            assert abs(discrepancy.compression_discrepancy - 0.02) < 0.01
            assert abs(discrepancy.max_discrepancy - 0.10) < 0.01  # Max is contrast
            assert 0.0 <= discrepancy.mean_discrepancy <= 1.0

    def test_should_escalate_due_to_high_discrepancy(self) -> None:
        """Test escalation due to high discrepancy."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()
            detector.discrepancy_threshold = 0.3

            # Student says good quality
            student_scores = MLIQAScores(
                blur_score=0.90,
                noise_score=0.85,
                contrast_score=0.88,
                skew_score=0.92,
                compression_score=0.91,
                overall_quality=0.89,
                confidences={
                    "blur": 0.90,
                    "noise": 0.85,
                    "contrast": 0.88,
                    "skew": 0.92,
                    "compression": 0.91,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=25.0,
            )

            # Classical says poor quality (large discrepancy)
            classical_scores = ClassicalIQAScores(
                blur_score=0.50,  # 0.40 difference!
                contrast_score=0.55,  # 0.33 difference!
                skew_score=0.95,  # 0.03 difference (ok)
            )

            decision = detector.should_escalate_due_to_discrepancy(
                student_scores, classical_scores
            )

            # Should escalate due to blur and contrast discrepancies
            assert decision.should_escalate is True
            assert decision.reason is not None
            assert "blur_discrepancy" in decision.reason
            assert "contrast_discrepancy" in decision.reason

    def test_should_not_escalate_due_to_low_discrepancy(self) -> None:
        """Test no escalation when discrepancy is low."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()
            detector.discrepancy_threshold = 0.3

            # Student and classical agree
            student_scores = MLIQAScores(
                blur_score=0.85,
                noise_score=0.80,
                contrast_score=0.82,
                skew_score=0.88,
                compression_score=0.86,
                overall_quality=0.84,
                confidences={
                    "blur": 0.85,
                    "noise": 0.80,
                    "contrast": 0.82,
                    "skew": 0.88,
                    "compression": 0.86,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=25.0,
            )

            classical_scores = ClassicalIQAScores(
                blur_score=0.82,  # 0.03 difference (ok)
                contrast_score=0.80,  # 0.02 difference (ok)
                skew_score=0.90,  # 0.02 difference (ok)
                noise_score=0.78,  # 0.02 difference (ok)
                compression_score=0.84,  # 0.02 difference (ok)
            )

            decision = detector.should_escalate_due_to_discrepancy(
                student_scores, classical_scores
            )

            # Should NOT escalate
            assert decision.should_escalate is False
            assert decision.reason is None

    def test_calculate_discrepancy_edge_cases(self) -> None:
        """Test discrepancy calculation with edge cases."""
        with patch.object(MLIQADetector, "_detect_device", return_value=Device.CPU):
            detector = MLIQADetector()

            # Perfect agreement (0 discrepancy)
            student_scores = MLIQAScores(
                blur_score=0.80,
                noise_score=0.75,
                contrast_score=0.85,
                skew_score=0.90,
                compression_score=0.88,
                overall_quality=0.84,
                confidences={
                    "blur": 0.80,
                    "noise": 0.75,
                    "contrast": 0.85,
                    "skew": 0.90,
                    "compression": 0.88,
                },
                model_type=ModelType.STUDENT,
                device=Device.CPU,
                inference_time_ms=25.0,
            )

            classical_scores = ClassicalIQAScores(
                blur_score=0.80,
                contrast_score=0.85,
                skew_score=0.90,
                noise_score=0.75,
                compression_score=0.88,
            )

            discrepancy = detector.calculate_discrepancy(
                student_scores, classical_scores
            )

            # All discrepancies should be 0
            assert discrepancy.blur_discrepancy == pytest.approx(0.0)
            assert discrepancy.contrast_discrepancy == pytest.approx(0.0)
            assert discrepancy.skew_discrepancy == pytest.approx(0.0)
            assert discrepancy.noise_discrepancy == pytest.approx(0.0)
            assert discrepancy.compression_discrepancy == pytest.approx(0.0)
            assert discrepancy.max_discrepancy == pytest.approx(0.0)
            assert discrepancy.mean_discrepancy == pytest.approx(0.0)
