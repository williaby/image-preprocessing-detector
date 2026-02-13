"""Integration tests for Bleed-Through detector + ML IQA pipeline.

Tests the complete workflow:
1. Classical bleed-through detector detects text/images from verso side
2. ClassicalIQAScores created with bleed-through result
3. ML pipeline runs (student + selective teacher)
4. Note: ML model doesn't predict bleed-through (document-specific), so discrepancy is 0.0
"""

import numpy as np
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    detect_bleed_through,
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.iqa_ml import (
    ClassicalIQAScores,
    MLIQADetector,
    ModelType,
)


class TestBleedThroughMLIQAIntegration:
    """Integration tests for Bleed-Through detector + ML IQA.

    Note: Uses shared ml_detector fixture from conftest.py.
    """

    def test_bleed_through_detection_with_ml_pipeline(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test that classical bleed-through detection works with ML IQA pipeline.

        Workflow:
        1. Create image with bleed-through effect (faint text showing through)
        2. Run classical bleed-through detector
        3. Create ClassicalIQAScores with bleed-through result
        4. Run ML pipeline (student inference)
        5. Note: ML model doesn't predict bleed-through, so no direct comparison
        6. Verify pipeline completes successfully
        """
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create image with simulated bleed-through
        # Main text: dark foreground
        img = np.ones((600, 800, 3), dtype=np.uint8) * 240  # Light background

        # Add main text (dark)
        for y in range(50, 550, 40):
            for x in range(50, 750, 60):
                img[y : y + 25, x : x + 50] = 30  # Dark text

        # Add bleed-through: faint text patterns (from verso side)
        for y in range(60, 560, 50):
            for x in range(60, 760, 70):
                # Faint text showing through (gray, not white)
                img[y : y + 20, x : x + 40] = np.clip(
                    img[y : y + 20, x : x + 40] - 40, 0, 255
                ).astype(np.uint8)

        # Run classical bleed-through detector
        bleed_result = detect_bleed_through(img)

        # Create classical scores (bleed_through_score: higher = better, so invert severity)
        # severity is 0-1 where higher = worse, so score = 1.0 - severity
        bleed_through_score = 1.0 - bleed_result.severity

        classical_scores = ClassicalIQAScores(
            blur_score=detect_blur(img).blur_score,
            contrast_score=detect_contrast(img).score,
            skew_score=max(0.0, 1.0 - (abs(detect_skew(img).angle) / 45.0)),
            bleed_through_score=bleed_through_score,  # range 0-1, higher is better
        )

        # Run ML IQA pipeline
        student_scores, _teacher_scores, _escalation_reason = ml_detector.run_pipeline(
            img, classical_scores
        )

        # Validate student inference
        assert student_scores is not None
        assert student_scores.model_type == ModelType.STUDENT
        assert 0.0 <= student_scores.overall_quality <= 1.0

        # Note: ML model doesn't predict bleed-through, so we can't compare
        # We just verify the pipeline completes successfully
        # teacher_scores available for debugging if needed

    def test_bleed_through_no_discrepancy_escalation(
        self, ml_detector: MLIQADetector | None
    ) -> None:
        """Test that bleed-through issues don't trigger discrepancy escalation.

        Since ML model doesn't predict bleed-through, the discrepancy calculation
        should set bleed_through_discrepancy=0.0, and no escalation should occur
        based on bleed-through alone.

        Workflow:
        1. Create image with bleed-through patterns
        2. Run classical bleed-through detector
        3. Run ML pipeline
        4. Verify bleed_through_discrepancy is 0.0 (ML doesn't predict bleed-through)
        5. Verify no escalation due to bleed-through discrepancy
        """
        if ml_detector is None:
            pytest.skip("ML detector not available")

        # Create image with severe bleed-through effect
        img = np.ones((600, 800, 3), dtype=np.uint8) * 220  # Light gray background

        # Add random faint patterns simulating severe bleed-through
        rng = np.random.default_rng(seed=42)
        noise_mask = rng.random((600, 800)) < 0.3  # 30% of pixels affected
        img[noise_mask] = np.clip(img[noise_mask] - 60, 0, 255).astype(np.uint8)

        # Run classical bleed-through detector
        bleed_result = detect_bleed_through(img)

        # Create classical scores (score = 1.0 - severity)
        bleed_through_score = 1.0 - bleed_result.severity

        classical_scores = ClassicalIQAScores(
            blur_score=detect_blur(img).blur_score,
            contrast_score=detect_contrast(img).score,
            skew_score=max(0.0, 1.0 - (abs(detect_skew(img).angle) / 45.0)),
            bleed_through_score=bleed_through_score,
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

        # Verify bleed-through discrepancy is 0.0 (ML doesn't predict bleed-through)
        assert discrepancy.bleed_through_discrepancy == pytest.approx(0.0), (
            "Bleed-through discrepancy should be 0.0 since ML model doesn't predict bleed-through"
        )

        # Check if discrepancy-based escalation occurred
        decision = ml_detector.should_escalate_due_to_discrepancy(
            student_scores, classical_scores
        )

        # Bleed-through should NOT contribute to discrepancy escalation
        if decision.should_escalate:
            # If escalation occurred, verify it's NOT due to bleed-through
            assert "bleed" not in decision.reason.lower(), (
                "Escalation should not be due to bleed-through (ML doesn't predict it)"
            )
        # teacher_scores available for debugging if needed
