"""
Unit tests for image correction operations.
"""

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.correction.corrections import (
    BinarizationCorrector,
    BleedThroughSuppressor,
    ContrastEnhancer,
    CorrectionResult,
    Denoiser,
    DeskewCorrector,
    IlluminationNormalizer,
    OrientationCorrector,
    Sharpener,
    correct_orientation,
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

        assert corrector.min_angle == pytest.approx(0.5)
        assert corrector.max_angle == pytest.approx(45.0)
        assert corrector.border_value == 255

    def test_init_custom_params(self) -> None:
        """Test DeskewCorrector initialization with custom parameters."""
        corrector = DeskewCorrector(min_angle=1.0, max_angle=30.0, border_value=128)

        assert corrector.min_angle == pytest.approx(1.0)
        assert corrector.max_angle == pytest.approx(30.0)
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
        assert result.parameters["angle"] == pytest.approx(10.0)
        assert result.parameters["confidence"] == pytest.approx(0.9)
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

        assert enhancer.clip_limit == pytest.approx(2.0)
        assert enhancer.tile_grid_size == (8, 8)
        assert enhancer.min_score == pytest.approx(0.4)

    def test_init_custom_params(self) -> None:
        """Test ContrastEnhancer initialization with custom parameters."""
        enhancer = ContrastEnhancer(
            clip_limit=3.0, tile_grid_size=(16, 16), min_score=0.5
        )

        assert enhancer.clip_limit == pytest.approx(3.0)
        assert enhancer.tile_grid_size == (16, 16)
        assert enhancer.min_score == pytest.approx(0.5)

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
        assert result.parameters["score"] == pytest.approx(0.2)
        assert result.parameters["severity"] == "high"
        # Image should have better contrast
        assert result.corrected_image.std() >= img.std()

    def test_correct_adjusts_clip_limit_by_severity(self) -> None:
        """Test clip limit adjustment based on severity."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        enhancer = ContrastEnhancer(clip_limit=2.0)

        # Critical severity
        result_critical = enhancer.correct(img, score=0.15, severity=Severity.CRITICAL)
        assert result_critical.parameters["clip_limit"] == pytest.approx(
            4.0
        )  # 2.0 * 2.0

        # Low severity
        result_low = enhancer.correct(img, score=0.35, severity=Severity.LOW)
        assert result_low.parameters["clip_limit"] == pytest.approx(1.0)  # 2.0 * 0.5

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

        assert sharpener.amount == pytest.approx(1.0)
        assert sharpener.kernel_size == 5
        assert sharpener.sigma == pytest.approx(1.0)
        assert sharpener.min_blur_score == pytest.approx(200.0)

    def test_init_custom_params(self) -> None:
        """Test Sharpener initialization with custom parameters."""
        sharpener = Sharpener(
            amount=1.5, kernel_size=7, sigma=1.5, min_blur_score=150.0
        )

        assert sharpener.amount == pytest.approx(1.5)
        assert sharpener.kernel_size == 7
        assert sharpener.sigma == pytest.approx(1.5)
        assert sharpener.min_blur_score == pytest.approx(150.0)

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
        assert result.parameters["blur_score"] == pytest.approx(80.0)
        assert result.parameters["severity"] == "high"

    def test_correct_adjusts_amount_by_severity(self) -> None:
        """Test sharpening amount adjustment based on severity."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        sharpener = Sharpener(amount=1.0)

        # Critical severity
        result_critical = sharpener.correct(
            img, blur_score=30.0, severity=Severity.CRITICAL
        )
        assert result_critical.parameters["amount"] == pytest.approx(1.5)  # 1.0 * 1.5

        # Low severity
        result_low = sharpener.correct(img, blur_score=150.0, severity=Severity.LOW)
        assert result_low.parameters["amount"] == pytest.approx(0.5)  # 1.0 * 0.5

    def test_correct_caps_amount_at_two(self) -> None:
        """Test sharpening amount is capped at 2.0."""
        img = np.ones((500, 500, 3), dtype=np.uint8) * 128
        sharpener = Sharpener(amount=2.0)  # Start at 2.0

        # Critical severity would make it 3.0 (2.0 * 1.5), but should cap at 2.0
        result = sharpener.correct(img, blur_score=30.0, severity=Severity.CRITICAL)
        assert result.parameters["amount"] == pytest.approx(2.0)  # Capped

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
        assert result.parameters["angle"] == pytest.approx(5.0)
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


class TestOrientationCorrector:
    """Test OrientationCorrector class (Phase 8)."""

    def test_init_default_params(self) -> None:
        """Test OrientationCorrector initialization with defaults."""
        corrector = OrientationCorrector()

        assert corrector.min_confidence == pytest.approx(0.7)
        assert corrector.auto_correct_threshold == pytest.approx(0.85)

    def test_init_custom_params(self) -> None:
        """Test OrientationCorrector initialization with custom parameters."""
        corrector = OrientationCorrector(min_confidence=0.8, auto_correct_threshold=0.9)

        assert corrector.min_confidence == pytest.approx(0.8)
        assert corrector.auto_correct_threshold == pytest.approx(0.9)

    def test_correct_upright_skipped(self) -> None:
        """Test correction skipped for upright images (0 degrees)."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector()

        result = corrector.correct(img, angle=0, confidence=0.95)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "upright" in result.skipped_reason.lower()

    def test_correct_low_confidence_skipped(self) -> None:
        """Test correction skipped for low confidence."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector(min_confidence=0.7)

        result = corrector.correct(img, angle=90, confidence=0.5)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "below threshold" in result.skipped_reason

    def test_correct_90_degrees(self) -> None:
        """Test correction for 90-degree rotation."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (50, 50), (350, 150), (0, 0, 0), 2)  # Marker

        corrector = OrientationCorrector()
        result = corrector.correct(img, angle=90, confidence=0.9)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["detected_angle"] == 90
        assert result.parameters["correction_applied"] == -90
        # 90° rotation swaps dimensions
        assert result.corrected_image.shape[0] == img.shape[1]
        assert result.corrected_image.shape[1] == img.shape[0]

    def test_correct_180_degrees(self) -> None:
        """Test correction for 180-degree rotation."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector()

        result = corrector.correct(img, angle=180, confidence=0.85)

        assert result.applied is True
        # 180° rotation preserves dimensions
        assert result.corrected_image.shape == img.shape

    def test_correct_270_degrees(self) -> None:
        """Test correction for 270-degree rotation."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector()

        result = corrector.correct(img, angle=270, confidence=0.9)

        assert result.applied is True
        assert result.parameters["detected_angle"] == 270
        # 270° rotation swaps dimensions
        assert result.corrected_image.shape[0] == img.shape[1]
        assert result.corrected_image.shape[1] == img.shape[0]

    def test_correct_force_low_confidence(self) -> None:
        """Test force correction bypasses confidence threshold."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector(min_confidence=0.9)

        # Without force, should skip
        result_no_force = corrector.correct(img, angle=90, confidence=0.5)
        assert result_no_force.applied is False

        # With force, should apply
        result_force = corrector.correct(img, angle=90, confidence=0.5, force=True)
        assert result_force.applied is True

    def test_correct_invalid_angle_raises(self) -> None:
        """Test correction raises ValueError for invalid angles."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector()

        with pytest.raises(ValueError, match="Invalid orientation angle"):
            corrector.correct(img, angle=45, confidence=0.9)

        with pytest.raises(ValueError, match="Invalid orientation angle"):
            corrector.correct(img, angle=135, confidence=0.9)

    def test_correct_empty_image_raises(self) -> None:
        """Test correction raises ValueError for empty image."""
        corrector = OrientationCorrector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            corrector.correct(np.array([]), angle=90, confidence=0.9)

    def test_correct_none_image_raises(self) -> None:
        """Test correction raises ValueError for None image."""
        corrector = OrientationCorrector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            corrector.correct(None, angle=90, confidence=0.9)  # type: ignore

    def test_correct_preserves_dimensions_info(self) -> None:
        """Test correction preserves original and new dimensions in params."""
        img = np.ones((600, 400, 3), dtype=np.uint8) * 255
        corrector = OrientationCorrector()

        result = corrector.correct(img, angle=90, confidence=0.9)

        assert result.applied is True
        assert result.parameters["original_size"] == (400, 600)
        assert result.parameters["new_size"] == (600, 400)

    def test_correct_orientation_convenience(self) -> None:
        """Test correct_orientation convenience function."""
        img = np.ones((500, 400, 3), dtype=np.uint8) * 255
        result = correct_orientation(img, angle=180, confidence=0.9)

        assert isinstance(result, CorrectionResult)
        assert result.applied is True


class TestDenoiser:
    """Test Denoiser class for noise reduction."""

    def test_init_default_params(self) -> None:
        """Test Denoiser initialization with defaults."""
        denoiser = Denoiser()

        assert denoiser.h_luminance == pytest.approx(10.0)
        assert denoiser.h_color == pytest.approx(10.0)
        assert denoiser.template_window_size == 7
        assert denoiser.search_window_size == 21
        assert denoiser.min_noise_score == pytest.approx(0.7)

    def test_init_custom_params(self) -> None:
        """Test Denoiser initialization with custom parameters."""
        denoiser = Denoiser(
            h_luminance=15.0,
            h_color=12.0,
            template_window_size=9,
            search_window_size=25,
            min_noise_score=0.8,
        )

        assert denoiser.h_luminance == pytest.approx(15.0)
        assert denoiser.h_color == pytest.approx(12.0)
        assert denoiser.template_window_size == 9
        assert denoiser.search_window_size == 25
        assert denoiser.min_noise_score == pytest.approx(0.8)

    def test_correct_clean_image_skipped(self) -> None:
        """Test denoising skipped for clean images."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        denoiser = Denoiser(min_noise_score=0.7)

        result = denoiser.correct(img, noise_score=0.8, severity=Severity.LOW)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "above threshold" in result.skipped_reason

    def test_correct_noisy_image(self) -> None:
        """Test denoising applied for noisy images."""
        # Create noisy image using modern numpy.random.Generator API
        rng = np.random.default_rng(seed=42)
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        noise = rng.normal(0, 30, img.shape).astype(np.int16)
        noisy_img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        denoiser = Denoiser()
        result = denoiser.correct(noisy_img, noise_score=0.3, severity=Severity.HIGH)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["noise_score"] == pytest.approx(0.3)
        assert result.parameters["severity"] == "high"

    def test_correct_adjusts_params_by_severity(self) -> None:
        """Test filter strength adjustment based on severity."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        denoiser = Denoiser(h_luminance=10.0, h_color=10.0)

        # Critical severity increases filter strength
        result_critical = denoiser.correct(
            img, noise_score=0.2, severity=Severity.CRITICAL
        )
        assert result_critical.parameters["h_luminance"] == pytest.approx(
            15.0
        )  # 10.0 * 1.5
        assert result_critical.parameters["h_color"] == pytest.approx(15.0)

        # Low severity decreases filter strength
        result_low = denoiser.correct(img, noise_score=0.5, severity=Severity.LOW)
        assert result_low.parameters["h_luminance"] == pytest.approx(5.0)  # 10.0 * 0.5
        assert result_low.parameters["h_color"] == pytest.approx(5.0)

    def test_correct_caps_filter_strength(self) -> None:
        """Test filter strength is capped to prevent over-smoothing."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        denoiser = Denoiser(h_luminance=18.0, h_color=18.0)  # High base values

        # Critical severity would make it 27 (18 * 1.5), but should cap at 20
        result = denoiser.correct(img, noise_score=0.2, severity=Severity.CRITICAL)
        assert result.parameters["h_luminance"] == pytest.approx(20.0)  # Capped
        assert result.parameters["h_color"] == pytest.approx(20.0)

    def test_correct_empty_image_raises(self) -> None:
        """Test denoising raises ValueError for empty image."""
        denoiser = Denoiser()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            denoiser.correct(np.array([]), noise_score=0.3, severity=Severity.HIGH)

    def test_correct_none_image_raises(self) -> None:
        """Test denoising raises ValueError for None image."""
        denoiser = Denoiser()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            denoiser.correct(None, noise_score=0.3, severity=Severity.HIGH)  # type: ignore


class TestBinarizationCorrector:
    """Test BinarizationCorrector class for document binarization."""

    def test_init_default_params(self) -> None:
        """Test BinarizationCorrector initialization with defaults."""
        corrector = BinarizationCorrector()

        assert corrector.block_size == 11
        assert corrector.c_offset == 2
        assert corrector.min_binarization_score == pytest.approx(0.7)
        assert corrector.apply_morphology is True

    def test_init_custom_params(self) -> None:
        """Test BinarizationCorrector initialization with custom parameters."""
        corrector = BinarizationCorrector(
            block_size=15,
            c_offset=3,
            min_binarization_score=0.8,
            apply_morphology=False,
        )

        assert corrector.block_size == 15
        assert corrector.c_offset == 3
        assert corrector.min_binarization_score == pytest.approx(0.8)
        assert corrector.apply_morphology is False

    def test_init_even_block_size_adjusted(self) -> None:
        """Test even block size is adjusted to odd."""
        corrector = BinarizationCorrector(block_size=10)

        assert corrector.block_size == 11  # Adjusted to odd

    def test_correct_good_binarization_skipped(self) -> None:
        """Test binarization skipped for good quality images."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        corrector = BinarizationCorrector(min_binarization_score=0.7)

        result = corrector.correct(img, binarization_score=0.8, severity=Severity.LOW)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "above threshold" in result.skipped_reason

    def test_correct_poor_binarization(self) -> None:
        """Test binarization applied for poor quality images."""
        # Create image with text-like features
        img = np.ones((200, 200, 3), dtype=np.uint8) * 200
        cv2.putText(
            img, "Test", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (50, 50, 50), 2
        )

        corrector = BinarizationCorrector()
        result = corrector.correct(img, binarization_score=0.3, severity=Severity.HIGH)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["binarization_score"] == pytest.approx(0.3)
        assert result.parameters["severity"] == "high"

    def test_correct_adjusts_params_by_severity(self) -> None:
        """Test parameter adjustment based on severity."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        corrector = BinarizationCorrector(block_size=11, c_offset=2)

        # Critical severity increases block size, decreases c_offset
        result_critical = corrector.correct(
            img, binarization_score=0.2, severity=Severity.CRITICAL
        )
        assert result_critical.parameters["block_size"] == 15  # 11 + 4
        assert result_critical.parameters["c_offset"] == 1  # max(2-1, 0)

        # Low severity increases c_offset
        result_low = corrector.correct(
            img, binarization_score=0.5, severity=Severity.LOW
        )
        assert result_low.parameters["c_offset"] == 3  # 2 + 1

    def test_correct_grayscale_image(self) -> None:
        """Test binarization works on grayscale input."""
        img = np.ones((200, 200), dtype=np.uint8) * 128
        corrector = BinarizationCorrector()

        result = corrector.correct(
            img, binarization_score=0.3, severity=Severity.MEDIUM
        )

        assert result.applied is True
        # Output should be BGR format
        assert len(result.corrected_image.shape) == 3
        assert result.corrected_image.shape[2] == 3

    def test_correct_without_morphology(self) -> None:
        """Test binarization without morphological cleanup."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        corrector = BinarizationCorrector(apply_morphology=False)

        result = corrector.correct(
            img, binarization_score=0.3, severity=Severity.MEDIUM
        )

        assert result.applied is True
        assert result.parameters["apply_morphology"] is False

    def test_correct_empty_image_raises(self) -> None:
        """Test binarization raises ValueError for empty image."""
        corrector = BinarizationCorrector()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            corrector.correct(
                np.array([]), binarization_score=0.3, severity=Severity.HIGH
            )


class TestIlluminationNormalizer:
    """Test IlluminationNormalizer class for uneven lighting correction."""

    def test_init_default_params(self) -> None:
        """Test IlluminationNormalizer initialization with defaults."""
        normalizer = IlluminationNormalizer()

        assert normalizer.kernel_size == 51
        assert normalizer.min_illumination_score == pytest.approx(0.7)
        assert normalizer.blend_alpha == pytest.approx(0.8)

    def test_init_custom_params(self) -> None:
        """Test IlluminationNormalizer initialization with custom parameters."""
        normalizer = IlluminationNormalizer(
            kernel_size=71,
            min_illumination_score=0.6,
            blend_alpha=0.9,
        )

        assert normalizer.kernel_size == 71
        assert normalizer.min_illumination_score == pytest.approx(0.6)
        assert normalizer.blend_alpha == pytest.approx(0.9)

    def test_init_even_kernel_size_adjusted(self) -> None:
        """Test even kernel size is adjusted to odd."""
        normalizer = IlluminationNormalizer(kernel_size=50)

        assert normalizer.kernel_size == 51  # Adjusted to odd

    def test_correct_uniform_illumination_skipped(self) -> None:
        """Test normalization skipped for uniformly lit images."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        normalizer = IlluminationNormalizer(min_illumination_score=0.7)

        result = normalizer.correct(img, illumination_score=0.8, severity=Severity.LOW)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "above threshold" in result.skipped_reason

    def test_correct_uneven_illumination(self) -> None:
        """Test normalization applied for uneven lighting."""
        # Create image with lighting gradient
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        for x in range(200):
            img[:, x] = int(50 + (x / 200) * 150)

        normalizer = IlluminationNormalizer()
        result = normalizer.correct(img, illumination_score=0.3, severity=Severity.HIGH)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["illumination_score"] == pytest.approx(0.3)

    def test_correct_adjusts_params_by_severity(self) -> None:
        """Test parameter adjustment based on severity."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 128
        normalizer = IlluminationNormalizer(kernel_size=51, blend_alpha=0.8)

        # Critical severity increases kernel and alpha
        result_critical = normalizer.correct(
            img, illumination_score=0.2, severity=Severity.CRITICAL
        )
        assert result_critical.parameters["kernel_size"] == 71  # 51 + 20
        assert result_critical.parameters["blend_alpha"] == pytest.approx(
            0.9
        )  # 0.8 + 0.1

        # Low severity decreases kernel and alpha
        result_low = normalizer.correct(
            img, illumination_score=0.5, severity=Severity.LOW
        )
        assert result_low.parameters["kernel_size"] == 41  # 51 - 10
        assert result_low.parameters["blend_alpha"] == pytest.approx(0.7)  # 0.8 - 0.1

    def test_correct_grayscale_image(self) -> None:
        """Test normalization works on grayscale input."""
        img = np.ones((200, 200), dtype=np.uint8) * 128
        normalizer = IlluminationNormalizer()

        result = normalizer.correct(
            img, illumination_score=0.3, severity=Severity.MEDIUM
        )

        assert result.applied is True
        # Output should be BGR format
        assert len(result.corrected_image.shape) == 3
        assert result.corrected_image.shape[2] == 3

    def test_correct_empty_image_raises(self) -> None:
        """Test normalization raises ValueError for empty image."""
        normalizer = IlluminationNormalizer()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            normalizer.correct(
                np.array([]), illumination_score=0.3, severity=Severity.HIGH
            )


class TestBleedThroughSuppressor:
    """Test BleedThroughSuppressor class for removing bleed-through artifacts."""

    def test_init_default_params(self) -> None:
        """Test BleedThroughSuppressor initialization with defaults."""
        suppressor = BleedThroughSuppressor()

        assert suppressor.kernel_size == 3
        assert suppressor.min_bleed_score == pytest.approx(0.7)
        assert suppressor.intensity_threshold == 200
        assert suppressor.blend_alpha == pytest.approx(0.7)

    def test_init_custom_params(self) -> None:
        """Test BleedThroughSuppressor initialization with custom parameters."""
        suppressor = BleedThroughSuppressor(
            kernel_size=5,
            min_bleed_score=0.6,
            intensity_threshold=180,
            blend_alpha=0.8,
        )

        assert suppressor.kernel_size == 5
        assert suppressor.min_bleed_score == pytest.approx(0.6)
        assert suppressor.intensity_threshold == 180
        assert suppressor.blend_alpha == pytest.approx(0.8)

    def test_init_even_kernel_size_adjusted(self) -> None:
        """Test even kernel size is adjusted to odd."""
        suppressor = BleedThroughSuppressor(kernel_size=4)

        assert suppressor.kernel_size == 5  # Adjusted to odd

    def test_correct_no_bleed_skipped(self) -> None:
        """Test suppression skipped when no bleed-through."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        suppressor = BleedThroughSuppressor(min_bleed_score=0.7)

        result = suppressor.correct(img, bleed_score=0.8, severity=Severity.LOW)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "above threshold" in result.skipped_reason

    def test_correct_bleed_through_detected(self) -> None:
        """Test suppression applied for bleed-through."""
        # Create image with simulated bleed-through (faint gray marks)
        img = np.ones((200, 200, 3), dtype=np.uint8) * 240
        # Add faint marks to simulate bleed-through
        img[50:150, 50:150] = 220

        suppressor = BleedThroughSuppressor()
        result = suppressor.correct(img, bleed_score=0.3, severity=Severity.HIGH)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["bleed_score"] == pytest.approx(0.3)

    def test_correct_adjusts_params_by_severity(self) -> None:
        """Test parameter adjustment based on severity."""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 200
        suppressor = BleedThroughSuppressor(intensity_threshold=200, blend_alpha=0.7)

        # Critical severity decreases threshold, increases alpha
        result_critical = suppressor.correct(
            img, bleed_score=0.2, severity=Severity.CRITICAL
        )
        assert result_critical.parameters["intensity_threshold"] == 180  # 200 - 20
        assert result_critical.parameters["blend_alpha"] == pytest.approx(
            0.9
        )  # 0.7 + 0.2

        # Low severity increases threshold, decreases alpha
        result_low = suppressor.correct(img, bleed_score=0.5, severity=Severity.LOW)
        assert result_low.parameters["intensity_threshold"] == 220  # 200 + 20
        assert result_low.parameters["blend_alpha"] == pytest.approx(0.6)  # 0.7 - 0.1

    def test_correct_grayscale_image(self) -> None:
        """Test suppression works on grayscale input."""
        img = np.ones((200, 200), dtype=np.uint8) * 200
        suppressor = BleedThroughSuppressor()

        result = suppressor.correct(img, bleed_score=0.3, severity=Severity.MEDIUM)

        assert result.applied is True
        # Output should be BGR format
        assert len(result.corrected_image.shape) == 3
        assert result.corrected_image.shape[2] == 3

    def test_correct_empty_image_raises(self) -> None:
        """Test suppression raises ValueError for empty image."""
        suppressor = BleedThroughSuppressor()

        with pytest.raises(ValueError, match="Invalid or empty image"):
            suppressor.correct(np.array([]), bleed_score=0.3, severity=Severity.HIGH)
