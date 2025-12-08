"""Unit tests for continuous weak supervision labeling (Phase 7).

Tests cover:
- Normalization functions for all 8 detectors
- Adaptive label smoothing at different confidence levels
- Sample weight computation
- Detector confidence estimation
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.weak_supervision_labeling_continuous import (
    ContinuousWeakSupervisionLabeler,
)


class TestNormalizationFunctions:
    """Test normalization of raw detector outputs to [0, 1] continuous scores."""

    def setup_method(self):
        """Initialize labeler for testing."""
        self.labeler = ContinuousWeakSupervisionLabeler()

    def test_normalize_skew_score_no_skew(self):
        """Test skew normalization for perfectly aligned image."""
        score = self.labeler.normalize_skew_score(angle=0.0)
        assert score == 1.0, "0° skew should give perfect score"

    def test_normalize_skew_score_severe(self):
        """Test skew normalization for maximum expected angle."""
        score = self.labeler.normalize_skew_score(angle=45.0)
        assert score == 0.0, "45° skew should give worst score"

    def test_normalize_skew_score_medium(self):
        """Test skew normalization for medium skew."""
        score = self.labeler.normalize_skew_score(angle=22.5)
        assert 0.4 < score < 0.6, "22.5° should give mid-range score"

    def test_normalize_blur_score_sharp(self):
        """Test blur normalization for sharp image."""
        score = self.labeler.normalize_blur_score(laplacian_var=1000.0)
        assert score == 1.0, "High Laplacian variance should give sharp score"

    def test_normalize_blur_score_blurry(self):
        """Test blur normalization for blurry image."""
        score = self.labeler.normalize_blur_score(laplacian_var=10.0)
        assert score == 0.0, "Low Laplacian variance should give blurry score"

    def test_normalize_blur_score_medium(self):
        """Test blur normalization for medium quality."""
        score = self.labeler.normalize_blur_score(laplacian_var=500.0)
        assert 0.4 < score < 0.6, "Medium variance should give mid-range score"

    def test_normalize_contrast_score_high(self):
        """Test contrast normalization for high contrast."""
        score = self.labeler.normalize_contrast_score(rms_contrast=0.5)
        assert score == 1.0, "High RMS contrast should give perfect score"

    def test_normalize_contrast_score_low(self):
        """Test contrast normalization for low contrast."""
        score = self.labeler.normalize_contrast_score(rms_contrast=0.01)
        assert score == 0.0, "Low RMS contrast should give worst score"

    def test_normalize_noise_score_clean(self):
        """Test noise normalization for clean image."""
        score = self.labeler.normalize_noise_score(noise_level=0.0)
        assert score == 1.0, "Zero noise should give perfect score"

    def test_normalize_noise_score_noisy(self):
        """Test noise normalization for noisy image."""
        score = self.labeler.normalize_noise_score(noise_level=50.0)
        assert score == 0.0, "Max noise should give worst score"

    def test_normalize_illumination_score_even(self):
        """Test illumination normalization for even lighting."""
        score = self.labeler.normalize_illumination_score(uniformity=1.0)
        assert score == 1.0, "Perfect uniformity should give perfect score"

    def test_normalize_illumination_score_poor(self):
        """Test illumination normalization for poor lighting."""
        score = self.labeler.normalize_illumination_score(uniformity=0.0)
        assert score == 0.0, "Zero uniformity should give worst score"

    def test_normalize_compression_score_no_artifacts(self):
        """Test compression normalization for artifact-free image."""
        score = self.labeler.normalize_compression_score(blockiness=0.0)
        assert score == 1.0, "No blockiness should give perfect score"

    def test_normalize_compression_score_severe_artifacts(self):
        """Test compression normalization for severe JPEG artifacts."""
        score = self.labeler.normalize_compression_score(blockiness=10.0)
        assert score == 0.0, "Max blockiness should give worst score"

    def test_normalization_score_ranges(self):
        """Test all normalization functions return [0, 1] range."""
        # Test boundary values for all normalizers
        test_cases = [
            (self.labeler.normalize_skew_score, [0.0, 22.5, 45.0]),
            (self.labeler.normalize_blur_score, [10.0, 500.0, 1000.0]),
            (self.labeler.normalize_contrast_score, [0.01, 0.25, 0.5]),
            (self.labeler.normalize_noise_score, [0.0, 25.0, 50.0]),
            (self.labeler.normalize_illumination_score, [0.0, 0.5, 1.0]),
            (self.labeler.normalize_compression_score, [0.0, 5.0, 10.0]),
        ]

        for normalize_fn, values in test_cases:
            for val in values:
                score = normalize_fn(val)
                assert 0.0 <= score <= 1.0, (
                    f"{normalize_fn.__name__} returned out-of-range score: {score}"
                )


class TestAdaptiveLabelSmoothing:
    """Test adaptive smoothing based on detector confidence."""

    def setup_method(self):
        """Initialize labeler with known thresholds."""
        self.labeler = ContinuousWeakSupervisionLabeler(
            high_confidence_threshold=0.9,
            medium_confidence_threshold=0.7,
            low_confidence_threshold=0.5,
        )

    def test_high_confidence_preserves_extremes(self):
        """High confidence should preserve near-extreme values."""
        # High confidence (0.95) with extreme low score
        smoothed = self.labeler.adaptive_smooth(score=0.02, confidence=0.95)
        assert 0.02 <= smoothed <= 0.1, "High confidence should preserve low extremes"

        # High confidence with extreme high score
        smoothed = self.labeler.adaptive_smooth(score=0.98, confidence=0.95)
        assert 0.9 <= smoothed <= 0.98, "High confidence should preserve high extremes"

    def test_medium_confidence_moderate_smoothing(self):
        """Medium confidence should apply moderate smoothing."""
        # Medium confidence (0.8) with extreme score
        smoothed = self.labeler.adaptive_smooth(score=0.05, confidence=0.8)
        assert 0.15 <= smoothed <= 0.85, "Medium confidence should clip to [0.15, 0.85]"

    def test_low_confidence_strong_smoothing(self):
        """Low confidence should apply strong smoothing."""
        # Low confidence (0.6) with extreme score
        smoothed = self.labeler.adaptive_smooth(score=0.01, confidence=0.6)
        assert 0.25 <= smoothed <= 0.75, "Low confidence should clip to [0.25, 0.75]"

    def test_very_low_confidence_pushes_neutral(self):
        """Very low confidence should push toward neutral range."""
        # Very low confidence (0.3) with extreme score
        smoothed = self.labeler.adaptive_smooth(score=0.0, confidence=0.3)
        assert 0.35 <= smoothed <= 0.65, (
            "Very low confidence should clip to [0.35, 0.65]"
        )

    def test_smoothing_monotonicity(self):
        """Smoothing should preserve score ordering."""
        scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        confidence = 0.8

        smoothed_scores = [self.labeler.adaptive_smooth(s, confidence) for s in scores]

        for i in range(len(smoothed_scores) - 1):
            assert smoothed_scores[i] <= smoothed_scores[i + 1], (
                "Smoothing should preserve score ordering"
            )


class TestSampleWeighting:
    """Test sample weight computation from detector agreement."""

    def setup_method(self):
        """Initialize labeler for testing."""
        self.labeler = ContinuousWeakSupervisionLabeler()

    def test_high_agreement_high_confidence(self):
        """High detector agreement + high confidence should give high weight."""
        # All detectors agree (low variance) with high confidence
        detector_scores = {
            "blur": 0.8,
            "contrast": 0.82,
            "skew": 0.81,
            "noise": 0.79,
            "illumination": 0.80,
            "compression": 0.81,
            "binarization": 0.80,
            "bleed_through": 0.82,
        }
        detector_confidences = dict.fromkeys(detector_scores, 0.9)

        weight = self.labeler.compute_sample_weight(
            detector_scores, detector_confidences
        )
        assert weight > 0.8, "High agreement + confidence should give high weight"

    def test_low_agreement_reduces_weight(self):
        """High detector disagreement should reduce sample weight."""
        # Detectors disagree (high variance)
        detector_scores = {
            "blur": 0.1,
            "contrast": 0.9,
            "skew": 0.2,
            "noise": 0.8,
            "illumination": 0.3,
            "compression": 0.7,
            "binarization": 0.4,
            "bleed_through": 0.6,
        }
        detector_confidences = dict.fromkeys(detector_scores, 0.8)

        weight = self.labeler.compute_sample_weight(
            detector_scores, detector_confidences
        )
        # High disagreement should reduce weight compared to perfect agreement
        # Variance ~= 0.07, so weight = 0.8 / (1 + 0.07) ≈ 0.75
        assert weight < 0.8, (
            "High disagreement should reduce weight from max confidence"
        )

    def test_low_confidence_reduces_weight(self):
        """Low detector confidence should reduce sample weight."""
        # High agreement but low confidence
        detector_scores = dict.fromkeys(
            [
                "blur",
                "contrast",
                "skew",
                "noise",
                "illumination",
                "compression",
                "binarization",
                "bleed_through",
            ],
            0.5,
        )
        detector_confidences = dict.fromkeys(detector_scores, 0.3)

        weight = self.labeler.compute_sample_weight(
            detector_scores, detector_confidences
        )
        assert weight < 0.5, "Low confidence should reduce weight"

    def test_weight_range(self):
        """Sample weights should be in valid range [0.1, 1.0]."""
        # Test extreme cases
        test_cases = [
            # (scores_variance, confidence_mean, expected_range)
            (
                {"blur": 0.5, "contrast": 0.5},
                {"blur": 0.9, "contrast": 0.9},
                (0.5, 1.0),
            ),
            (
                {"blur": 0.1, "contrast": 0.9},
                {"blur": 0.5, "contrast": 0.5},
                (0.1, 0.5),
            ),
        ]

        for scores, confidences, (min_w, max_w) in test_cases:
            weight = self.labeler.compute_sample_weight(scores, confidences)
            assert 0.1 <= weight <= 1.0, (
                f"Weight {weight} out of valid range [0.1, 1.0]"
            )
            assert min_w <= weight <= max_w, (
                f"Weight {weight} not in expected range [{min_w}, {max_w}]"
            )


class TestDetectorConfidenceEstimation:
    """Test confidence estimation for detector outputs."""

    def setup_method(self):
        """Initialize labeler and test image."""
        self.labeler = ContinuousWeakSupervisionLabeler()

        # Create test image with structure (edges)
        self.image_with_structure = np.zeros((500, 500, 3), dtype=np.uint8)
        cv2.rectangle(
            self.image_with_structure, (100, 100), (400, 400), (255, 255, 255), 2
        )
        cv2.line(self.image_with_structure, (0, 250), (500, 250), (255, 255, 255), 1)

        # Create test image without structure (blank)
        self.image_no_structure = np.ones((500, 500, 3), dtype=np.uint8) * 128

    def test_blur_far_from_threshold_high_confidence(self):
        """Blur metric far from threshold should give high confidence."""
        # Very high variance → far from blur threshold (200)
        confidence = self.labeler.estimate_detector_confidence(
            "blur", metric_value=800.0, image=self.image_with_structure
        )
        assert confidence > 0.8, "Far from threshold should give high confidence"

    def test_blur_near_threshold_lower_confidence(self):
        """Blur metric near threshold should give lower confidence."""
        # Close to blur threshold (200)
        confidence = self.labeler.estimate_detector_confidence(
            "blur", metric_value=210.0, image=self.image_with_structure
        )
        assert confidence < 0.9, "Near threshold should give lower confidence"

    def test_skew_extreme_angles_high_confidence(self):
        """Extreme skew angles should give high confidence."""
        # Very skewed (15°)
        confidence = self.labeler.estimate_detector_confidence(
            "skew", metric_value=15.0, image=self.image_with_structure
        )
        assert confidence > 0.85, "Large skew angle should give high confidence"

    def test_skew_near_zero_high_confidence(self):
        """Near-zero skew should give high confidence."""
        # Nearly aligned (0.3°)
        confidence = self.labeler.estimate_detector_confidence(
            "skew", metric_value=0.3, image=self.image_with_structure
        )
        assert confidence > 0.85, "Near-zero skew should give high confidence"

    def test_structure_boosts_confidence(self):
        """Images with structure should get confidence boost."""
        # Same metric, different images
        conf_with_structure = self.labeler.estimate_detector_confidence(
            "blur", metric_value=500.0, image=self.image_with_structure
        )
        conf_no_structure = self.labeler.estimate_detector_confidence(
            "blur", metric_value=500.0, image=self.image_no_structure
        )

        assert conf_with_structure >= conf_no_structure, (
            "Structured image should have equal or higher confidence"
        )

    def test_confidence_range(self):
        """All confidence estimates should be in [0, 1] range."""
        detectors = ["blur", "contrast", "skew"]
        metric_values = [100.0, 0.3, 5.0]

        for detector, metric in zip(detectors, metric_values):
            confidence = self.labeler.estimate_detector_confidence(
                detector, metric, self.image_with_structure
            )
            assert 0.0 <= confidence <= 1.0, (
                f"Confidence {confidence} out of range for {detector}"
            )


class TestEndToEndLabeling:
    """Integration tests for complete labeling pipeline."""

    def setup_method(self):
        """Create test images."""
        self.labeler = ContinuousWeakSupervisionLabeler()

        # Create high-quality test image
        self.high_quality = np.ones((800, 600, 3), dtype=np.uint8) * 255
        cv2.putText(
            self.high_quality,
            "High Quality Document",
            (50, 400),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (0, 0, 0),
            3,
        )

        # Create low-quality test image (blurred + noisy)
        self.low_quality = np.random.randint(0, 50, (800, 600, 3), dtype=np.uint8)
        self.low_quality = cv2.GaussianBlur(self.low_quality, (15, 15), 0)

    def test_high_quality_image_scores(self, tmp_path):
        """High-quality image should get high continuous scores."""
        # Save test image
        img_path = tmp_path / "high_quality.png"
        cv2.imwrite(str(img_path), self.high_quality)

        # Label image
        result = self.labeler.label_image(img_path)

        # Check scores are generally high (most > 0.5)
        scores = result["continuous_scores"]
        high_scores = sum(1 for s in scores.values() if s > 0.5)
        assert high_scores >= 5, "High-quality image should have mostly high scores"

        # Check sample weight is reasonable
        assert result["sample_weight"] > 0.3, "Sample weight should be reasonable"

    def test_low_quality_image_scores(self, tmp_path):
        """Low-quality image should get low continuous scores."""
        # Save test image
        img_path = tmp_path / "low_quality.png"
        cv2.imwrite(str(img_path), self.low_quality)

        # Label image
        result = self.labeler.label_image(img_path)

        # Check at least some scores are low
        scores = result["continuous_scores"]
        low_scores = sum(1 for s in scores.values() if s < 0.5)
        assert low_scores >= 2, "Low-quality image should have some low scores"

    def test_label_output_schema(self, tmp_path):
        """Verify output contains all required fields."""
        # Save test image
        img_path = tmp_path / "test.png"
        cv2.imwrite(str(img_path), self.high_quality)

        # Label image
        result = self.labeler.label_image(img_path)

        # Check required fields
        assert "image_path" in result
        assert "continuous_scores" in result
        assert "detector_confidences" in result
        assert "sample_weight" in result
        assert "smoothing_applied" in result
        assert "raw_scores" in result

        # Check all 8 detectors present
        detectors = [
            "blur",
            "contrast",
            "skew",
            "noise",
            "illumination",
            "compression",
            "binarization",
            "bleed_through",
        ]
        for detector in detectors:
            assert detector in result["continuous_scores"]
            assert detector in result["detector_confidences"]
            assert detector in result["smoothing_applied"]
            assert detector in result["raw_scores"]

    def test_continuous_not_binary(self, tmp_path):
        """Verify scores are continuous, not binary {0, 1}."""
        # Save test image
        img_path = tmp_path / "test.png"
        cv2.imwrite(str(img_path), self.high_quality)

        # Label image
        result = self.labeler.label_image(img_path)

        # Check scores are not just 0.0 or 1.0
        scores = list(result["continuous_scores"].values())
        intermediate_scores = [s for s in scores if 0.1 < s < 0.9]

        assert len(intermediate_scores) > 0, (
            "Should have some intermediate scores, not just binary 0/1"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
