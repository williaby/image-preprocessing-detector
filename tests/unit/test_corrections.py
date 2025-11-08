"""
Unit tests for image correction operations.
"""

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.correction.corrections import (
    ContrastEnhancer,
    CorrectionResult,
    DeskewCorrector,
    Sharpener,
    correct_skew,
    enhance_contrast,
    sharpen_image,
)
from image_preprocessing_detector.detection.iqa_classical import Severity


class TestDeskewCorrector:
    """Test DeskewCorrector class."""

    def test_init_default_params(self) -> None:
        """Test DeskewCorrector initialization with defaults."""
        corrector = DeskewCorrector()

        assert corrector.min_angle == 0.5
        assert corrector.max_angle == 45.0
        assert corrector.border_value == 255

    def test_init_custom_params(self) -> None:
        """Test DeskewCorrector initialization with custom parameters."""
        corrector = DeskewCorrector(min_angle=1.0, max_angle=30.0, border_value=128)

        assert corrector.min_angle == 1.0
        assert corrector.max_angle == 30.0
        assert corrector.border_value == 128

    def test_correct_small_angle_skipped(self) -> None:
        """Test correction skipped for very small angles."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        corrector = DeskewCorrector(min_angle=0.5)

        result = corrector.correct(img, angle=0.3, confidence=1.0)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "below threshold" in result.skipped_reason
        assert np.array_equal(result.corrected_image, img)

    def test_correct_large_angle_skipped(self) -> None:
        """Test correction skipped for very large angles."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        corrector = DeskewCorrector(max_angle=45.0)

        result = corrector.correct(img, angle=50.0, confidence=1.0)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "exceeds max" in result.skipped_reason

    def test_correct_low_confidence_skipped(self) -> None:
        """Test correction skipped for low confidence."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        corrector = DeskewCorrector()

        result = corrector.correct(img, angle=5.0, confidence=0.2)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "too low" in result.skipped_reason

    def test_correct_valid_angle(self) -> None:
        """Test correction applied for valid angle."""
        # Create simple test image
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (100, 100), (400, 400), (0, 0, 0), 2)

        corrector = DeskewCorrector()
        result = corrector.correct(img, angle=10.0, confidence=0.9)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["angle"] == 10.0
        assert result.parameters["confidence"] == 0.9
        # Image dimensions should change due to rotation
        assert result.corrected_image.shape != img.shape

    def test_correct_preserves_dimensions_info(self) -> None:
        """Test correction preserves original and new dimensions."""
        img = np.ones((500, 600, 3), dtype=np.uint8) * 255
        corrector = DeskewCorrector()

        result = corrector.correct(img, angle=5.0, confidence=1.0)

        assert result.applied is True
        assert result.parameters["original_size"] == (600, 500)
        assert "new_size" in result.parameters

    def test_correct_empty_image_raises(self) -> None:
        """Test correction raises ValueError for empty image."""
        corrector = DeskewCorrector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            corrector.correct(np.array([]), angle=5.0, confidence=1.0)

    def test_correct_none_image_raises(self) -> None:
        """Test correction raises ValueError for None image."""
        corrector = DeskewCorrector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            corrector.correct(None, angle=5.0, confidence=1.0)  # type: ignore


class TestContrastEnhancer:
    """Test ContrastEnhancer class."""

    def test_init_default_params(self) -> None:
        """Test ContrastEnhancer initialization with defaults."""
        enhancer = ContrastEnhancer()

        assert enhancer.clip_limit == 2.0
        assert enhancer.tile_grid_size == (8, 8)
        assert enhancer.min_score == 0.4

    def test_init_custom_params(self) -> None:
        """Test ContrastEnhancer initialization with custom parameters."""
        enhancer = ContrastEnhancer(
            clip_limit=3.0, tile_grid_size=(16, 16), min_score=0.5
        )

        assert enhancer.clip_limit == 3.0
        assert enhancer.tile_grid_size == (16, 16)
        assert enhancer.min_score == 0.5

    def test_correct_good_contrast_skipped(self) -> None:
        """Test enhancement skipped for good contrast."""
        # High contrast image
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img[:, :250] = 0
        img[:, 250:] = 255

        enhancer = ContrastEnhancer(min_score=0.4)
        result = enhancer.correct(img, score=0.5, severity=Severity.LOW)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "above threshold" in result.skipped_reason

    def test_correct_low_contrast(self) -> None:
        """Test enhancement applied for low contrast."""
        # Low contrast image (similar gray values)
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        img[:, :250] = 120
        img[:, 250:] = 136

        enhancer = ContrastEnhancer()
        result = enhancer.correct(img, score=0.2, severity=Severity.HIGH)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["score"] == 0.2
        assert result.parameters["severity"] == "high"
        # Image should have better contrast
        assert result.corrected_image.std() >= img.std()

    def test_correct_adjusts_clip_limit_by_severity(self) -> None:
        """Test clip limit adjustment based on severity."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        enhancer = ContrastEnhancer(clip_limit=2.0)

        # Critical severity
        result_critical = enhancer.correct(img, score=0.15, severity=Severity.CRITICAL)
        assert result_critical.parameters["clip_limit"] == 4.0  # 2.0 * 2.0

        # Low severity
        result_low = enhancer.correct(img, score=0.35, severity=Severity.LOW)
        assert result_low.parameters["clip_limit"] == 1.0  # 2.0 * 0.5

    def test_correct_empty_image_raises(self) -> None:
        """Test enhancement raises ValueError for empty image."""
        enhancer = ContrastEnhancer()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            enhancer.correct(np.array([]), score=0.2, severity=Severity.HIGH)


class TestSharpener:
    """Test Sharpener class."""

    def test_init_default_params(self) -> None:
        """Test Sharpener initialization with defaults."""
        sharpener = Sharpener()

        assert sharpener.amount == 1.0
        assert sharpener.kernel_size == 5
        assert sharpener.sigma == 1.0
        assert sharpener.min_blur_score == 200.0

    def test_init_custom_params(self) -> None:
        """Test Sharpener initialization with custom parameters."""
        sharpener = Sharpener(
            amount=1.5, kernel_size=7, sigma=1.5, min_blur_score=150.0
        )

        assert sharpener.amount == 1.5
        assert sharpener.kernel_size == 7
        assert sharpener.sigma == 1.5
        assert sharpener.min_blur_score == 150.0

    def test_init_even_kernel_adjusted(self) -> None:
        """Test even kernel size is adjusted to odd."""
        sharpener = Sharpener(kernel_size=6)

        assert sharpener.kernel_size == 7  # Adjusted to odd

    def test_correct_sharp_image_skipped(self) -> None:
        """Test sharpening skipped for already sharp images."""
        # Create sharp image (checkerboard)
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        square_size = 25
        for i in range(0, 500, square_size):
            for j in range(0, 500, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    img[i : i + square_size, j : j + square_size] = 255

        sharpener = Sharpener(min_blur_score=200.0)
        result = sharpener.correct(img, blur_score=250.0, severity=Severity.LOW)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "above threshold" in result.skipped_reason

    def test_correct_blurred_image(self) -> None:
        """Test sharpening applied for blurred images."""
        # Create sharp image then blur it
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        square_size = 25
        for i in range(0, 500, square_size):
            for j in range(0, 500, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    img[i : i + square_size, j : j + square_size] = 255

        blurred = cv2.GaussianBlur(img, (15, 15), 5)

        sharpener = Sharpener()
        result = sharpener.correct(blurred, blur_score=80.0, severity=Severity.HIGH)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["blur_score"] == 80.0
        assert result.parameters["severity"] == "high"

    def test_correct_adjusts_amount_by_severity(self) -> None:
        """Test sharpening amount adjustment based on severity."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        sharpener = Sharpener(amount=1.0)

        # Critical severity
        result_critical = sharpener.correct(
            img, blur_score=30.0, severity=Severity.CRITICAL
        )
        assert result_critical.parameters["amount"] == 1.5  # 1.0 * 1.5

        # Low severity
        result_low = sharpener.correct(img, blur_score=150.0, severity=Severity.LOW)
        assert result_low.parameters["amount"] == 0.5  # 1.0 * 0.5

    def test_correct_caps_amount_at_two(self) -> None:
        """Test sharpening amount is capped at 2.0."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        sharpener = Sharpener(amount=2.0)  # Start at 2.0

        # Critical severity would make it 3.0 (2.0 * 1.5), but should cap at 2.0
        result = sharpener.correct(img, blur_score=30.0, severity=Severity.CRITICAL)
        assert result.parameters["amount"] == 2.0  # Capped

    def test_correct_empty_image_raises(self) -> None:
        """Test sharpening raises ValueError for empty image."""
        sharpener = Sharpener()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            sharpener.correct(np.array([]), blur_score=80.0, severity=Severity.HIGH)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_correct_skew_convenience(self) -> None:
        """Test correct_skew convenience function."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 255
        result = correct_skew(img, angle=5.0, confidence=0.9)

        assert isinstance(result, CorrectionResult)
        assert result.applied is True

    def test_enhance_contrast_convenience(self) -> None:
        """Test enhance_contrast convenience function."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        result = enhance_contrast(img, score=0.2, severity=Severity.HIGH)

        assert isinstance(result, CorrectionResult)
        assert result.applied is True

    def test_sharpen_image_convenience(self) -> None:
        """Test sharpen_image convenience function."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        result = sharpen_image(img, blur_score=80.0, severity=Severity.HIGH)

        assert isinstance(result, CorrectionResult)
        assert result.applied is True


class TestCorrectionResult:
    """Test CorrectionResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a CorrectionResult instance."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = CorrectionResult(
            corrected_image=img,
            applied=True,
            parameters={"angle": 5.0},
            skipped_reason=None,
        )

        assert result.applied is True
        assert result.parameters["angle"] == 5.0
        assert result.skipped_reason is None
        assert result.corrected_image.shape == (100, 100, 3)

    def test_result_with_skip_reason(self) -> None:
        """Test CorrectionResult with skip reason."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = CorrectionResult(
            corrected_image=img,
            applied=False,
            parameters={},
            skipped_reason="Angle too small",
        )

        assert result.applied is False
        assert result.skipped_reason == "Angle too small"
