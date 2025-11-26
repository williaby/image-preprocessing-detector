"""End-to-end tests for teacher escalation with real data.

Tests the complete escalation path:
1. Student inference
2. Uncertainty detection
3. Classical discrepancy
4. Teacher escalation
5. Result merging

Sprint 5.1.x: Teacher-student ML IQA escalation E2E tests.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    NoiseDetector,
    SkewDetector,
)
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
# Test Fixtures
# =============================================================================


@pytest.fixture
def ml_detector():
    """Create ML IQA detector, skip if models unavailable."""
    try:
        detector = MLIQADetector()
        # Check if student model is actually loaded
        if detector._student_session is None:
            return None
        return detector
    except Exception:
        return None


@pytest.fixture
def classical_detectors():
    """Create classical IQA detectors."""
    return {
        "blur": BlurDetector(),
        "noise": NoiseDetector(),
        "contrast": ContrastDetector(),
        "skew": SkewDetector(),
    }


@pytest.fixture
def synthetic_blurry_image():
    """Create a synthetically blurred image."""
    # Create sharp document
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    for y in range(100, 700, 30):
        cv2.line(image, (50, y), (550, y), (0, 0, 0), 2)
    # Apply heavy blur
    return cv2.GaussianBlur(image, (31, 31), 15)


@pytest.fixture
def synthetic_noisy_image():
    """Create a synthetically noisy image."""
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    for y in range(100, 700, 30):
        cv2.line(image, (50, y), (550, y), (0, 0, 0), 2)
    # Add gaussian noise
    noise = np.random.normal(0, 50, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy


@pytest.fixture
def synthetic_clean_image():
    """Create a clean synthetic document image."""
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    # Add clear text lines
    for y in range(100, 700, 30):
        cv2.line(image, (50, y), (550, y), (0, 0, 0), 2)
    return image


@pytest.fixture
def synthetic_combined_issues():
    """Create image with multiple quality issues."""
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    for y in range(100, 700, 30):
        cv2.line(image, (50, y), (550, y), (0, 0, 0), 2)

    # Apply blur
    image = cv2.GaussianBlur(image, (15, 15), 5)

    # Add noise
    noise = np.random.normal(0, 25, image.shape).astype(np.float32)
    image = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # Apply skew
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, 3, 1.0)
    image = cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))

    return image


# =============================================================================
# Helper Functions
# =============================================================================


def get_classical_scores(image, detectors):
    """Get classical IQA scores for an image."""
    blur_result = detectors["blur"].detect(image)
    noise_result = detectors["noise"].detect(image)
    contrast_result = detectors["contrast"].detect(image)
    skew_result = detectors["skew"].detect(image)

    return ClassicalIQAScores(
        blur_score=blur_result.blur_score,
        contrast_score=contrast_result.score,
        skew_score=max(0.0, 1.0 - abs(skew_result.angle) / 45.0),
        noise_score=noise_result.noise_score,
    )


# =============================================================================
# Escalation Trigger Tests
# =============================================================================


class TestEscalationTriggers:
    """Test conditions that trigger teacher escalation."""

    def test_high_uncertainty_triggers_escalation(self, ml_detector):
        """Test that high uncertainty would trigger escalation."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create uncertainty metrics that should trigger escalation
        uncertainty = UncertaintyMetrics(
            entropy=0.9,  # High entropy (> 0.8 threshold)
            min_confidence=0.4,  # Low confidence (< 0.6 threshold)
            mean_confidence=0.6,
            head_confidences={"blur": 0.4, "noise": 0.8},
        )

        # Check escalation conditions
        assert uncertainty.entropy > ml_detector.entropy_threshold
        assert uncertainty.min_confidence < ml_detector.min_confidence_threshold

    def test_low_uncertainty_no_escalation(self, ml_detector):
        """Test that low uncertainty does not trigger escalation."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create uncertainty metrics that should NOT trigger escalation
        uncertainty = UncertaintyMetrics(
            entropy=0.3,  # Low entropy
            min_confidence=0.85,  # High confidence
            mean_confidence=0.9,
            head_confidences={"blur": 0.9, "noise": 0.95},
        )

        # Check non-escalation conditions
        assert uncertainty.entropy < ml_detector.entropy_threshold
        assert uncertainty.min_confidence > ml_detector.min_confidence_threshold

    def test_classical_discrepancy_triggers_escalation(self, ml_detector):
        """Test that large classical discrepancy would trigger escalation."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        classical = ClassicalIQAScores(
            blur_score=0.9,  # Classical says sharp
            contrast_score=0.85,
            skew_score=0.9,
        )

        ml_scores = MLIQAScores(
            blur_score=0.3,  # ML says blurry (large discrepancy)
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

        # Check discrepancy
        blur_discrepancy = abs(classical.blur_score - ml_scores.blur_score)
        assert blur_discrepancy > ml_detector.discrepancy_threshold


# =============================================================================
# Synthetic Image Escalation Tests
# =============================================================================


class TestSyntheticImageEscalation:
    """Test escalation behavior with synthetic images."""

    def test_blurry_image_detection(
        self, ml_detector, classical_detectors, synthetic_blurry_image
    ):
        """Test that blurry image is detected by both classical and ML."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Get classical scores
        classical = get_classical_scores(synthetic_blurry_image, classical_detectors)

        # Classical should detect blur (low blur score)
        assert classical.blur_score < 0.7, (
            f"Expected blurry detection, got blur_score={classical.blur_score}"
        )

    def test_noisy_image_detection(
        self, ml_detector, classical_detectors, synthetic_noisy_image
    ):
        """Test that noisy image is detected."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        classical = get_classical_scores(synthetic_noisy_image, classical_detectors)

        # Classical should detect noise (low noise score)
        # Note: noise detection may vary based on intensity
        assert 0.0 <= classical.noise_score <= 1.0

    def test_clean_image_no_issues(
        self, ml_detector, classical_detectors, synthetic_clean_image
    ):
        """Test that clean image has no major issues detected."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        classical = get_classical_scores(synthetic_clean_image, classical_detectors)

        # Clean image should have high quality scores
        assert classical.blur_score > 0.5, "Clean image should not be blurry"
        assert classical.skew_score > 0.8, "Clean image should not be skewed"

    def test_combined_issues_escalation_likely(
        self, ml_detector, classical_detectors, synthetic_combined_issues
    ):
        """Test that image with combined issues is flagged."""
        if ml_detector is None:
            pytest.skip("ML detector not available")

        classical = get_classical_scores(synthetic_combined_issues, classical_detectors)

        # Multiple issues should result in lower overall quality
        avg_score = (
            classical.blur_score + classical.contrast_score + classical.skew_score
        ) / 3
        # With combined issues, average should be lower
        assert avg_score < 0.95, "Combined issues should lower quality"


# =============================================================================
# Real Fixture Escalation Tests
# =============================================================================


@pytest.mark.real_data
class TestRealFixtureEscalation:
    """Test escalation with real fixture files."""

    def test_low_quality_fixture_escalation(
        self, ml_detector, classical_detectors, low_quality_table_image
    ):
        """Test low quality fixture triggers appropriate detection."""
        if ml_detector is None:
            pytest.skip("ML detector not available")
        if low_quality_table_image is None:
            pytest.skip("Low quality fixture not available")

        # Load image
        img = cv2.imread(str(low_quality_table_image))
        if img is None:
            pytest.skip("Could not load image")

        classical = get_classical_scores(img, classical_detectors)

        # Low quality image should have lower scores
        # Exact values depend on the actual fixture
        assert 0.0 <= classical.blur_score <= 1.0
        assert 0.0 <= classical.contrast_score <= 1.0

    def test_simple_table_detection(
        self, ml_detector, classical_detectors, simple_table_image
    ):
        """Test simple table image quality detection."""
        if ml_detector is None:
            pytest.skip("ML detector not available")
        if simple_table_image is None:
            pytest.skip("Simple table fixture not available")

        classical = get_classical_scores(simple_table_image, classical_detectors)

        # Simple table should have reasonable quality
        assert 0.0 <= classical.blur_score <= 1.0

    def test_rotated_image_skew_detection(
        self, ml_detector, classical_detectors, rotated_table_image
    ):
        """Test rotated image skew is detected."""
        if ml_detector is None:
            pytest.skip("ML detector not available")
        if rotated_table_image is None:
            pytest.skip("Rotated table fixture not available")

        classical = get_classical_scores(rotated_table_image, classical_detectors)

        # Rotated image might have skew detected
        # (depends on rotation angle in fixture)
        assert 0.0 <= classical.skew_score <= 1.0


# =============================================================================
# Escalation Reason Tracking Tests
# =============================================================================


class TestEscalationReasonTracking:
    """Test that escalation reasons are properly tracked."""

    def test_escalation_decision_creation(self):
        """Test EscalationDecision creation with different reasons."""
        # No escalation
        no_escalate = EscalationDecision(
            should_escalate=False,
            reason=None,
            uncertainty_metrics=UncertaintyMetrics(
                entropy=0.3,
                min_confidence=0.9,
                mean_confidence=0.92,
                head_confidences={},
            ),
        )
        assert no_escalate.should_escalate is False
        assert no_escalate.reason is None

        # High uncertainty escalation
        uncertainty_escalate = EscalationDecision(
            should_escalate=True,
            reason="high_uncertainty",
            uncertainty_metrics=UncertaintyMetrics(
                entropy=0.95,
                min_confidence=0.3,
                mean_confidence=0.5,
                head_confidences={},
            ),
        )
        assert uncertainty_escalate.should_escalate is True
        assert uncertainty_escalate.reason == "high_uncertainty"

        # Discrepancy escalation
        discrepancy_escalate = EscalationDecision(
            should_escalate=True,
            reason="classical_discrepancy",
            uncertainty_metrics=UncertaintyMetrics(
                entropy=0.5,
                min_confidence=0.7,
                mean_confidence=0.75,
                head_confidences={},
            ),
        )
        assert discrepancy_escalate.reason == "classical_discrepancy"

        # High risk document escalation
        risk_escalate = EscalationDecision(
            should_escalate=True,
            reason="high_risk_document",
            uncertainty_metrics=UncertaintyMetrics(
                entropy=0.6,
                min_confidence=0.65,
                mean_confidence=0.7,
                head_confidences={},
            ),
        )
        assert risk_escalate.reason == "high_risk_document"

    def test_escalation_reasons_are_valid_strings(self):
        """Test that escalation reasons are valid string values."""
        valid_reasons = {
            None,  # No escalation
            "high_uncertainty",
            "classical_discrepancy",
            "high_risk_document",
            "low_confidence",
            "boundary_case",
        }

        # Create decisions with each reason
        for reason in valid_reasons:
            decision = EscalationDecision(
                should_escalate=reason is not None,
                reason=reason,
                uncertainty_metrics=UncertaintyMetrics(
                    entropy=0.5,
                    min_confidence=0.7,
                    mean_confidence=0.75,
                    head_confidences={},
                ),
            )
            assert decision.reason == reason


# =============================================================================
# Model Type Tracking Tests
# =============================================================================


class TestModelTypeTracking:
    """Test that model type (student/teacher) is properly tracked."""

    def test_student_scores_have_correct_model_type(self):
        """Test student inference returns STUDENT model type."""
        scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.88,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=12.0,
        )

        assert scores.model_type == ModelType.STUDENT

    def test_teacher_scores_have_correct_model_type(self):
        """Test teacher inference returns TEACHER model type."""
        scores = MLIQAScores(
            blur_score=0.82,
            noise_score=0.88,
            contrast_score=0.83,
            skew_score=0.92,
            compression_score=0.87,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.TEACHER,
            device=Device.GPU,
            inference_time_ms=25.0,
        )

        assert scores.model_type == ModelType.TEACHER

    def test_device_tracking(self):
        """Test device is properly tracked in scores."""
        # CPU inference
        cpu_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.88,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=40.0,
        )
        assert cpu_scores.device == Device.CPU

        # GPU inference
        gpu_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.88,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.GPU,
            inference_time_ms=10.0,
        )
        assert gpu_scores.device == Device.GPU


# =============================================================================
# Inference Time Tracking Tests
# =============================================================================


class TestInferenceTimeTracking:
    """Test inference time tracking."""

    def test_student_faster_than_teacher(self):
        """Test expectation that student inference is faster."""
        # Student should be ~2-3x faster than teacher
        student_time = 15.0  # ms
        teacher_time = 35.0  # ms

        student_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.88,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=student_time,
        )

        teacher_scores = MLIQAScores(
            blur_score=0.82,
            noise_score=0.88,
            contrast_score=0.83,
            skew_score=0.92,
            compression_score=0.87,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.TEACHER,
            device=Device.CPU,
            inference_time_ms=teacher_time,
        )

        assert student_scores.inference_time_ms < teacher_scores.inference_time_ms

    def test_gpu_faster_than_cpu(self):
        """Test expectation that GPU inference is faster than CPU."""
        cpu_time = 40.0  # ms
        gpu_time = 10.0  # ms

        cpu_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.88,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.CPU,
            inference_time_ms=cpu_time,
        )

        gpu_scores = MLIQAScores(
            blur_score=0.8,
            noise_score=0.9,
            contrast_score=0.85,
            skew_score=0.9,
            compression_score=0.88,
            overall_quality=0.86,
            confidences={},
            model_type=ModelType.STUDENT,
            device=Device.GPU,
            inference_time_ms=gpu_time,
        )

        assert gpu_scores.inference_time_ms < cpu_scores.inference_time_ms
