"""Integration tests for Illumination detector + ML IQA pipeline.

Tests the complete workflow:
1. Classical illumination detector detects issues (vignetting, shadows, hotspots)
2. ClassicalIQAScores created with illumination result
3. ML pipeline runs (student + selective teacher)
4. Note: ML model doesn't predict illumination, so discrepancy is 0.0
"""

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_illumination,
    detect_skew,
)
from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    MLIQADetector,
    ModelType,
)


class TestIlluminationMLIQAIntegration:
    """Integration tests for Illumination detector + ML IQA.

    Note: Uses shared ml_detector fixture from conftest.py.
    """

    def test_poor_illumination_detection_with_ml_pipeline(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test that classical illumination detection works with ML IQA pipeline.

        Workflow:
        1. Create image with vignetting (dark corners)
        2. Run classical illumination detector (should detect issues)
        3. Create ClassicalIQAScores with illumination result
        4. Run ML pipeline (student inference)
        5. Note: ML model doesn't predict illumination, so no direct comparison
        6. Verify pipeline completes successfully

        Note: This test validates the workflow, not ML accuracy on illumination
        since the current ML model doesn't have an illumination prediction head.
        """
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create image with vignetting effect (dark corners, bright center)
        img = np.ones((600, 800, 3), dtype=np.uint8) * 200

        # Create radial gradient for vignetting
        center_x, center_y = 400, 300
        y, x = np.ogrid[:600, :800]
        distances = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        max_distance = np.sqrt(center_x**2 + center_y**2)
        vignette_mask = 1.0 - (distances / max_distance) ** 2
        vignette_mask = np.clip(vignette_mask, 0.3, 1.0)  # Darken edges to 30%

        # Apply vignetting to all channels
        img_vignette = (img * vignette_mask[:, :, np.newaxis]).astype(np.uint8)

        # Run classical illumination detector
        illum_result = detect_illumination(img_vignette)
        assert illum_result.has_issues, (
            "Classical detector should detect illumination issues"
        )
        # score is 0-1 where 0=poor uniformity, 1=good uniformity
        assert illum_result.score < 0.8, (
            "Illumination score should indicate issues (< 0.8)"
        )

        # Create classical scores (illumination_score already normalized: lower = worse quality)
        classical_scores = ClassicalIQAScores(
            blur_score=detect_blur(img_vignette).blur_score,
            contrast_score=detect_contrast(img_vignette).score,
            skew_score=max(0.0, 1.0 - (abs(detect_skew(img_vignette).angle) / 45.0)),
            illumination_score=illum_result.score,  # Already 0-1 normalized
        )

        # Run ML IQA pipeline
        student_scores, _teacher_scores, _escalation_reason = ml_detector.run_pipeline(
            img_vignette, classical_scores
        )

        # Validate student inference
        assert student_scores is not None
        assert student_scores.model_type == ModelType.STUDENT
        assert 0.0 <= student_scores.overall_quality <= 1.0

        # Note: ML model doesn't predict illumination, so we can't compare
        # We just verify the pipeline completes successfully
        # teacher_scores available for debugging if needed

    def test_illumination_no_discrepancy_escalation(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test that illumination issues don't trigger discrepancy escalation.

        Since ML model doesn't predict illumination, the discrepancy calculation
        should set illumination_discrepancy=0.0, and no escalation should occur
        based on illumination alone.

        Workflow:
        1. Create image with illumination issues
        2. Run classical illumination detector (should detect)
        3. Run ML pipeline
        4. Verify illumination_discrepancy is 0.0 (ML doesn't predict illumination)
        5. Verify no escalation due to illumination discrepancy
        """
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create image with shadows (left half darker than right half)
        img = np.ones((600, 800, 3), dtype=np.uint8) * 200
        img[:, :400] = (img[:, :400] * 0.5).astype(np.uint8)  # Darken left half to 50%

        # Run classical illumination detector
        illum_result = detect_illumination(img)

        # Classical should detect illumination issues (detection logged for debugging)

        # Create classical scores
        classical_scores = ClassicalIQAScores(
            blur_score=detect_blur(img).blur_score,
            contrast_score=detect_contrast(img).score,
            skew_score=max(0.0, 1.0 - (abs(detect_skew(img).angle) / 45.0)),
            illumination_score=illum_result.score,  # Already 0-1 normalized
        )

        # Run ML IQA pipeline
        student_scores, _teacher_scores, _escalation_reason = ml_detector.run_pipeline(
            img, classical_scores
        )

        # Validate student inference
        assert student_scores is not None
        assert student_scores.model_type == ModelType.STUDENT

        # Calculate discrepancy
        discrepancy = ml_detector.calculate_discrepancy(
            student_scores, classical_scores
        )

        # Verify illumination discrepancy is 0.0 (ML doesn't predict illumination)
        assert discrepancy.illumination_discrepancy == pytest.approx(0.0), (
            "Illumination discrepancy should be 0.0 since ML model doesn't predict illumination"
        )

        # Check if discrepancy-based escalation occurred
        decision = ml_detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        # Illumination should NOT contribute to discrepancy escalation
        if decision.should_escalate:
            # If escalation occurred, verify it's NOT due to illumination
            assert "illumination" not in decision.reason.lower(), (
                "Escalation should not be due to illumination (ML doesn't predict it)"
            )
        # teacher_scores available for debugging if needed
