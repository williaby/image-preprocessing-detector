"""Integration tests for Binarization Quality detector + ML IQA pipeline.

Tests the complete workflow:
1. Classical binarization quality detector assesses binary/near-binary images
2. ClassicalIQAScores created with binarization result
3. ML pipeline runs (student + selective teacher)
4. Note: ML model doesn't predict binarization (document-specific), so discrepancy is 0.0
"""

from pathlib import Path

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    detect_binarization_quality,
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    Device,
    MLIQADetector,
    ModelType,
)


class TestBinarizationMLIQAIntegration:
    """Integration tests for Binarization Quality detector + ML IQA."""

    @pytest.fixture
    def onnx_models_available(self) -> bool:
        """Check if ONNX models are available."""
        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"
        teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"
        return student_path.exists() and teacher_path.exists()

    @pytest.fixture
    def ml_detector(self, onnx_models_available: bool) -> MLIQADetector | None:
        """Create ML IQA detector with real models if available."""
        if not onnx_models_available:
            pytest.skip("ONNX models not available")

        model_dir = Path(__file__).parents[2] / "models" / "iqa" / "onnx"
        student_path = model_dir / "resnet18_student.onnx"
        teacher_path = model_dir / "resnet50_teacher_50epoch.onnx"

        return MLIQADetector(
            student_model_path=student_path,
            teacher_model_path=teacher_path,
            device=Device.CPU,
            enable_modal_fallback=False,
        )

    def test_poor_binarization_detection_with_ml_pipeline(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test that classical binarization quality assessment works with ML IQA pipeline.

        Workflow:
        1. Create poorly binarized image (gray values, not crisp black/white)
        2. Run classical binarization quality detector
        3. Create ClassicalIQAScores with binarization result
        4. Run ML pipeline (student inference)
        5. Note: ML model doesn't predict binarization, so no direct comparison
        6. Verify pipeline completes successfully
        """
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create poorly binarized image (should be black/white but has many gray values)
        img = np.ones((600, 800, 3), dtype=np.uint8) * 128  # Gray background

        # Add "text-like" regions with poor binarization (gray, not crisp)
        for y in range(50, 550, 30):
            for x in range(50, 750, 50):
                # Poor binarization: text is gray (70-90) instead of black (0)
                img[y : y + 20, x : x + 40] = np.random.randint(
                    70, 90, (20, 40, 3), dtype=np.uint8
                )

        # Run classical binarization quality detector
        binarization_result = detect_binarization_quality(img)

        # Create classical scores (binarization_score already normalized: lower = worse quality)
        classical_scores = ClassicalIQAScores(
            blur_score=detect_blur(img).blur_score,
            contrast_score=detect_contrast(img).score,
            skew_score=max(0.0, 1.0 - (abs(detect_skew(img).angle) / 45.0)),
            binarization_score=binarization_result.binarization_score,  # Already 0-1 normalized
        )

        # Run ML IQA pipeline
        student_scores, teacher_scores, _escalation_reason = ml_detector.run_pipeline(
            img, classical_scores
        )

        # Validate student inference
        assert student_scores is not None
        assert student_scores.model_type == ModelType.STUDENT
        assert 0.0 <= student_scores.overall_quality <= 1.0

        # Note: ML model doesn't predict binarization, so we can't compare
        # We just verify the pipeline completes successfully

        # Log results for analysis
        if teacher_scores:
            pass

    def test_binarization_no_discrepancy_escalation(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test that binarization issues don't trigger discrepancy escalation.

        Since ML model doesn't predict binarization quality, the discrepancy calculation
        should set binarization_discrepancy=0.0, and no escalation should occur
        based on binarization alone.

        Workflow:
        1. Create poorly binarized image
        2. Run classical binarization quality detector
        3. Run ML pipeline
        4. Verify binarization_discrepancy is 0.0 (ML doesn't predict binarization)
        5. Verify no escalation due to binarization discrepancy
        """
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create image with poor binarization (too many gray levels)
        img = np.random.randint(
            50, 200, (600, 800, 3), dtype=np.uint8
        )  # Many gray levels

        # Run classical binarization quality detector
        binarization_result = detect_binarization_quality(img)

        # Create classical scores
        classical_scores = ClassicalIQAScores(
            blur_score=detect_blur(img).blur_score,
            contrast_score=detect_contrast(img).score,
            skew_score=max(0.0, 1.0 - (abs(detect_skew(img).angle) / 45.0)),
            binarization_score=binarization_result.binarization_score,
        )

        # Run ML IQA pipeline
        student_scores, teacher_scores, _escalation_reason = ml_detector.run_pipeline(
            img, classical_scores
        )

        # Validate student inference
        assert student_scores is not None
        assert student_scores.model_type == ModelType.STUDENT

        # Calculate discrepancy
        discrepancy = ml_detector.calculate_discrepancy(
            student_scores, classical_scores
        )

        # Verify binarization discrepancy is 0.0 (ML doesn't predict binarization)
        assert discrepancy.binarization_discrepancy == 0.0, (
            "Binarization discrepancy should be 0.0 since ML model doesn't predict binarization"
        )

        # Check if discrepancy-based escalation occurred
        decision = ml_detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        # Binarization should NOT contribute to discrepancy escalation
        if decision.should_escalate:
            # If escalation occurred, verify it's NOT due to binarization
            assert "binarization" not in decision.reason.lower(), (
                "Escalation should not be due to binarization (ML doesn't predict it)"
            )
        else:
            pass

        # Log results
        if teacher_scores:
            pass
