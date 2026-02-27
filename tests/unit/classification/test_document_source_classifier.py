"""Unit tests for document source/capture method classifier."""

from __future__ import annotations

import numpy as np
import pytest

from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod
from image_preprocessing_detector.classification.document_source_classifier import (
    DocumentSourceClassifier,
    DocumentSourceResult,
    classify_document_source,
)

# ---------------------------------------------------------------------------
# Valid CaptureMethod values for assertion helpers
# ---------------------------------------------------------------------------
_VALID_CAPTURE_METHODS: frozenset[str] = frozenset(m.value for m in CaptureMethod)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def classifier() -> DocumentSourceClassifier:
    """Return a fresh classifier instance with default thresholds."""
    return DocumentSourceClassifier()


@pytest.fixture
def scanner_image() -> np.ndarray:
    """Synthetic image mimicking a clean flatbed scan.

    Properties:
    - Uniform white background (low std-dev in border region).
    - Content is placed well inside the border strip so the 10% inset
      region sees only the uniform background.
    - Even illumination across all quadrants.
    - Lines are predominantly horizontal/vertical (low angular variance).
    """
    img = np.full((600, 800, 3), 245, dtype=np.uint8)
    # Place content well inside the border inset (10% of 600 = 60px,
    # 10% of 800 = 80px).  Start at 100,120 to keep the border strip
    # entirely within the uniform background.
    img[100:500, 120:680] = 30
    # Add horizontal lines inside content to give Hough mostly 0-degree
    # angles (low angular std-dev).
    for row in range(150, 480, 40):
        img[row, 130:670] = 245
    return img


@pytest.fixture
def camera_image() -> np.ndarray:
    """Synthetic image mimicking a smartphone camera capture.

    Properties:
    - Gradient background (high std-dev in border region).
    - Soft, blurred edges (low Canny density).
    - Uneven illumination across quadrants.
    """
    height, width = 600, 800
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Create a strong horizontal gradient for the background to produce
    # high border std-dev and uneven illumination.
    for col in range(width):
        val = int(50 + (col / width) * 180)
        img[:, col, :] = val

    # Add Gaussian blur to destroy sharp edges.
    import cv2

    img = cv2.GaussianBlur(img, (31, 31), 15)

    return img


@pytest.fixture
def white_image() -> np.ndarray:
    """Blank white image -- perfectly uniform background."""
    return np.full((400, 600, 3), 255, dtype=np.uint8)


@pytest.fixture
def grayscale_image() -> np.ndarray:
    """Single-channel grayscale image with uniform background."""
    img = np.full((400, 600), 240, dtype=np.uint8)
    # Small dark rectangle so rectangularity analysis has something to find.
    img[50:350, 50:550] = 20
    return img


@pytest.fixture
def bgra_image() -> np.ndarray:
    """Four-channel BGRA image with uniform background."""
    img = np.full((400, 600, 4), 255, dtype=np.uint8)
    img[:, :, 3] = 255  # fully opaque alpha
    img[50:350, 50:550, :3] = 0
    return img


# ---------------------------------------------------------------------------
# Scanner detection
# ---------------------------------------------------------------------------


class TestScannerDetection:
    """Uniform background + sharp edges should classify as scanner."""

    def test_scanner_image_classified_as_flatbed(
        self, classifier: DocumentSourceClassifier, scanner_image: np.ndarray
    ) -> None:
        """Clean synthetic scan should be classified as scanner_flatbed."""
        result = classifier.classify(scanner_image)

        assert result.capture_method in {
            CaptureMethod.SCANNER_FLATBED.value,
            CaptureMethod.SCANNER_ADF.value,
        }
        assert result.scanner_score > 0.4

    def test_scanner_high_background_uniformity(
        self, classifier: DocumentSourceClassifier, scanner_image: np.ndarray
    ) -> None:
        """Scanner image should have high background uniformity."""
        result = classifier.classify(scanner_image)
        assert result.background_uniformity > 0.5

    def test_scanner_high_illumination_evenness(
        self, classifier: DocumentSourceClassifier, scanner_image: np.ndarray
    ) -> None:
        """Scanner image should have even illumination."""
        result = classifier.classify(scanner_image)
        assert result.illumination_evenness > 0.5

    def test_scanner_low_perspective_distortion(
        self, classifier: DocumentSourceClassifier, scanner_image: np.ndarray
    ) -> None:
        """Scanner image should have minimal perspective distortion."""
        result = classifier.classify(scanner_image)
        assert result.perspective_distortion < 0.5


# ---------------------------------------------------------------------------
# Camera detection
# ---------------------------------------------------------------------------


class TestCameraDetection:
    """Gradient background + blurred edges should classify as camera."""

    def test_camera_image_classified_as_smartphone(
        self, classifier: DocumentSourceClassifier, camera_image: np.ndarray
    ) -> None:
        """Gradient, blurred synthetic image should map to camera_smartphone."""
        result = classifier.classify(camera_image)

        assert result.capture_method in {
            CaptureMethod.CAMERA_SMARTPHONE.value,
            CaptureMethod.UNKNOWN.value,
        }
        assert result.scanner_score < 0.6

    def test_camera_low_background_uniformity(
        self, classifier: DocumentSourceClassifier, camera_image: np.ndarray
    ) -> None:
        """Camera image with gradient should have lower background uniformity."""
        result = classifier.classify(camera_image)
        # The gradient creates high std-dev in the border region.
        assert result.background_uniformity < 0.8

    def test_camera_uneven_illumination(
        self, classifier: DocumentSourceClassifier, camera_image: np.ndarray
    ) -> None:
        """Camera image with horizontal gradient should have uneven illumination."""
        result = classifier.classify(camera_image)
        assert result.illumination_evenness < 0.9


# ---------------------------------------------------------------------------
# Blank / white image
# ---------------------------------------------------------------------------


class TestBlankWhiteImage:
    """A perfectly uniform white image should score highly for scanner."""

    def test_white_image_high_scanner_score(
        self, classifier: DocumentSourceClassifier, white_image: np.ndarray
    ) -> None:
        """Uniform white image has perfect background uniformity."""
        result = classifier.classify(white_image)
        assert result.background_uniformity > 0.9

    def test_white_image_even_illumination(
        self, classifier: DocumentSourceClassifier, white_image: np.ndarray
    ) -> None:
        """Uniform white image has perfectly even illumination."""
        result = classifier.classify(white_image)
        assert result.illumination_evenness > 0.9

    def test_white_image_scanner_method(
        self, classifier: DocumentSourceClassifier, white_image: np.ndarray
    ) -> None:
        """Uniform white image should classify as scanner or unknown (not camera)."""
        result = classifier.classify(white_image)
        assert result.capture_method != CaptureMethod.CAMERA_SMARTPHONE.value


# ---------------------------------------------------------------------------
# Input format handling
# ---------------------------------------------------------------------------


class TestInputFormats:
    """Classifier should handle grayscale, BGR, and BGRA inputs."""

    def test_grayscale_input(
        self, classifier: DocumentSourceClassifier, grayscale_image: np.ndarray
    ) -> None:
        """Single-channel grayscale image should not raise."""
        result = classifier.classify(grayscale_image)
        assert isinstance(result, DocumentSourceResult)

    def test_bgra_input(
        self, classifier: DocumentSourceClassifier, bgra_image: np.ndarray
    ) -> None:
        """Four-channel BGRA image should not raise."""
        result = classifier.classify(bgra_image)
        assert isinstance(result, DocumentSourceResult)

    def test_bgr_input(
        self, classifier: DocumentSourceClassifier, scanner_image: np.ndarray
    ) -> None:
        """Standard 3-channel BGR image should not raise."""
        result = classifier.classify(scanner_image)
        assert isinstance(result, DocumentSourceResult)


# ---------------------------------------------------------------------------
# Invalid input
# ---------------------------------------------------------------------------


class TestInvalidInput:
    """Invalid images should raise ValueError."""

    def test_none_input_raises(self, classifier: DocumentSourceClassifier) -> None:
        """None image should raise ValueError."""
        with pytest.raises(ValueError, match=r"[Ii]nvalid"):
            classifier.classify(None)  # type: ignore[arg-type]

    def test_empty_array_raises(self, classifier: DocumentSourceClassifier) -> None:
        """Zero-size array should raise ValueError."""
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match=r"[Ii]nvalid"):
            classifier.classify(empty)

    def test_zero_dimension_raises(self, classifier: DocumentSourceClassifier) -> None:
        """Image with zero height/width should raise ValueError."""
        zero_dim = np.zeros((0, 100, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match=r"[Ii]nvalid"):
            classifier.classify(zero_dim)


# ---------------------------------------------------------------------------
# Score ranges
# ---------------------------------------------------------------------------


class TestScoreRanges:
    """All scores must be in [0, 1]; capture_method must be valid."""

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "scanner_image",
            "camera_image",
            "white_image",
            "grayscale_image",
            "bgra_image",
        ],
    )
    def test_all_scores_in_unit_interval(
        self,
        classifier: DocumentSourceClassifier,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Every numeric score in the result must be in [0, 1]."""
        image = request.getfixturevalue(fixture_name)
        result = classifier.classify(image)

        for field_name in (
            "scanner_score",
            "background_uniformity",
            "edge_sharpness",
            "rectangularity",
            "perspective_distortion",
            "illumination_evenness",
            "confidence",
        ):
            value = getattr(result, field_name)
            assert 0.0 <= value <= 1.0, (
                f"{field_name}={value} out of [0, 1] for {fixture_name}"
            )

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "scanner_image",
            "camera_image",
            "white_image",
            "grayscale_image",
            "bgra_image",
        ],
    )
    def test_capture_method_is_valid_enum(
        self,
        classifier: DocumentSourceClassifier,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Capture method must always be a valid CaptureMethod value."""
        image = request.getfixturevalue(fixture_name)
        result = classifier.classify(image)
        assert result.capture_method in _VALID_CAPTURE_METHODS


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


class TestConfidence:
    """Confidence should reflect distance from decision boundaries."""

    def test_confidence_at_least_half(
        self, classifier: DocumentSourceClassifier, scanner_image: np.ndarray
    ) -> None:
        """Confidence is always >= 0.5."""
        result = classifier.classify(scanner_image)
        assert result.confidence >= 0.5

    def test_confidence_at_most_one(
        self, classifier: DocumentSourceClassifier, camera_image: np.ndarray
    ) -> None:
        """Confidence is always <= 1.0."""
        result = classifier.classify(camera_image)
        assert result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------


class TestCustomThresholds:
    """Classifier should respect custom threshold overrides."""

    def test_custom_scanner_high_threshold(self, scanner_image: np.ndarray) -> None:
        """Raising scanner_high_threshold changes classification."""
        strict = DocumentSourceClassifier(scanner_high_threshold=0.99)
        result = strict.classify(scanner_image)
        # With a near-impossible threshold, should not be scanner_flatbed
        assert result.capture_method != CaptureMethod.SCANNER_FLATBED.value

    def test_custom_camera_threshold(self, camera_image: np.ndarray) -> None:
        """Setting camera_threshold=0.0 means nothing classifies as camera."""
        lenient = DocumentSourceClassifier(camera_threshold=0.0)
        result = lenient.classify(camera_image)
        assert result.capture_method != CaptureMethod.CAMERA_SMARTPHONE.value


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Module-level classify_document_source wrapper."""

    def test_convenience_returns_result(self, scanner_image: np.ndarray) -> None:
        """Convenience function returns a DocumentSourceResult."""
        result = classify_document_source(scanner_image)
        assert isinstance(result, DocumentSourceResult)

    def test_convenience_matches_class(self, scanner_image: np.ndarray) -> None:
        """Convenience function produces same result as class method."""
        class_result = DocumentSourceClassifier().classify(scanner_image)
        func_result = classify_document_source(scanner_image)

        assert class_result.capture_method == func_result.capture_method
        assert class_result.scanner_score == func_result.scanner_score
        assert class_result.confidence == func_result.confidence

    def test_convenience_invalid_raises(self) -> None:
        """Convenience function propagates ValueError for invalid input."""
        with pytest.raises(ValueError, match=r"[Ii]nvalid"):
            classify_document_source(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Dataclass immutability
# ---------------------------------------------------------------------------


class TestDataclassImmutability:
    """Frozen dataclass should reject mutation."""

    def test_result_is_frozen(self, scanner_image: np.ndarray) -> None:
        """DocumentSourceResult rejects attribute assignment."""
        result = classify_document_source(scanner_image)
        with pytest.raises(AttributeError):
            result.scanner_score = 0.99  # type: ignore[misc]

    def test_result_capture_method_frozen(self, scanner_image: np.ndarray) -> None:
        """capture_method field is immutable."""
        result = classify_document_source(scanner_image)
        with pytest.raises(AttributeError):
            result.capture_method = "born_digital"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Small / tiny images
# ---------------------------------------------------------------------------


class TestSmallImages:
    """Classifier should handle very small images gracefully."""

    def test_tiny_image(self, classifier: DocumentSourceClassifier) -> None:
        """A 10x10 image should not crash."""
        tiny = np.full((10, 10, 3), 200, dtype=np.uint8)
        result = classifier.classify(tiny)
        assert isinstance(result, DocumentSourceResult)
        assert result.capture_method in _VALID_CAPTURE_METHODS

    def test_minimum_viable_image(self, classifier: DocumentSourceClassifier) -> None:
        """A 2x2 image should produce a valid result without crashing."""
        micro = np.full((2, 2, 3), 128, dtype=np.uint8)
        result = classifier.classify(micro)
        assert isinstance(result, DocumentSourceResult)

    def test_single_pixel_image(self, classifier: DocumentSourceClassifier) -> None:
        """A 1x1 image should produce a valid result."""
        pixel = np.array([[[128, 128, 128]]], dtype=np.uint8)
        result = classifier.classify(pixel)
        assert isinstance(result, DocumentSourceResult)


# ---------------------------------------------------------------------------
# Signal isolation tests
# ---------------------------------------------------------------------------


class TestSignalIsolation:
    """Verify individual signals respond to targeted image properties."""

    def test_uniform_bg_high_uniformity(
        self, classifier: DocumentSourceClassifier
    ) -> None:
        """Constant-value image should have very high background uniformity."""
        uniform = np.full((200, 300, 3), 180, dtype=np.uint8)
        result = classifier.classify(uniform)
        assert result.background_uniformity > 0.95

    def test_noisy_bg_lower_uniformity(
        self, classifier: DocumentSourceClassifier
    ) -> None:
        """Random noise image should have lower background uniformity."""
        rng = np.random.default_rng(42)
        noisy = rng.integers(0, 256, (200, 300, 3), dtype=np.uint8)
        result = classifier.classify(noisy)
        assert result.background_uniformity < 0.5

    def test_even_illumination_uniform_image(
        self, classifier: DocumentSourceClassifier
    ) -> None:
        """Constant-value image should have perfect illumination evenness."""
        uniform = np.full((200, 300, 3), 180, dtype=np.uint8)
        result = classifier.classify(uniform)
        assert result.illumination_evenness > 0.95

    def test_uneven_illumination_gradient(
        self, classifier: DocumentSourceClassifier
    ) -> None:
        """Strong vertical gradient should reduce illumination evenness."""
        img = np.zeros((200, 300, 3), dtype=np.uint8)
        for row in range(200):
            val = int((row / 200) * 255)
            img[row, :, :] = val
        result = classifier.classify(img)
        assert result.illumination_evenness < 0.9
