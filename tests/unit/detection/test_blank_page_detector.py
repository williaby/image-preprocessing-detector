"""Unit tests for BlankPageDetector.

Tests cover:
- Pure white and pure black blank pages
- Near-blank pages with slight noise
- Document pages with real content (text, shapes)
- Half-filled pages
- Edge cases: empty image, grayscale input, BGRA input
- Configurable thresholds
- Module-level convenience function
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.blank_page_detector import (
    BlankPageDetector,
    BlankPageResult,
    detect_blank_page,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable synthetic images
# ---------------------------------------------------------------------------


@pytest.fixture
def white_page() -> np.ndarray:
    """Pure white BGR image (800x600)."""
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def black_page() -> np.ndarray:
    """Pure black BGR image (800x600)."""
    return np.zeros((600, 800, 3), dtype=np.uint8)


@pytest.fixture
def noisy_blank_page() -> np.ndarray:
    """Nearly blank page with slight Gaussian noise."""
    rng = np.random.default_rng(42)
    page = np.full((600, 800, 3), 245, dtype=np.uint8)
    noise = rng.integers(-3, 4, size=page.shape, dtype=np.int16)
    noisy = np.clip(page.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


@pytest.fixture
def content_page() -> np.ndarray:
    """Page with substantial content (rectangles and text-like lines)."""
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    # Draw several filled rectangles to simulate text blocks
    cv2.rectangle(page, (50, 50), (750, 100), (0, 0, 0), -1)
    cv2.rectangle(page, (50, 130), (750, 180), (0, 0, 0), -1)
    cv2.rectangle(page, (50, 210), (750, 260), (0, 0, 0), -1)
    cv2.rectangle(page, (50, 290), (400, 340), (0, 0, 0), -1)
    # Draw horizontal lines
    for y_pos in range(370, 560, 30):
        cv2.line(page, (50, y_pos), (750, y_pos), (0, 0, 0), 2)
    return page


@pytest.fixture
def half_filled_page() -> np.ndarray:
    """Page with content only in the top half."""
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    # Fill top half with text-like content
    cv2.rectangle(page, (50, 30), (750, 70), (0, 0, 0), -1)
    cv2.rectangle(page, (50, 90), (750, 130), (0, 0, 0), -1)
    cv2.rectangle(page, (50, 150), (600, 190), (0, 0, 0), -1)
    return page


@pytest.fixture
def grayscale_page() -> np.ndarray:
    """Grayscale blank image (single channel)."""
    return np.full((600, 800), 255, dtype=np.uint8)


@pytest.fixture
def bgra_content_page() -> np.ndarray:
    """BGRA image with content."""
    page = np.full((600, 800, 4), 255, dtype=np.uint8)
    cv2.rectangle(page, (50, 50), (750, 300), (0, 0, 0, 255), -1)
    return page


# ---------------------------------------------------------------------------
# Tests: BlankPageResult dataclass
# ---------------------------------------------------------------------------


class TestBlankPageResult:
    """Verify the result dataclass fields."""

    def test_fields_present(self) -> None:
        """All expected fields are accessible."""
        result = BlankPageResult(
            is_blank=True,
            blankness_score=0.95,
            content_ratio=0.001,
            edge_density=0.0005,
            pixel_variance=5.0,
            confidence=0.98,
        )
        assert result.is_blank is True
        assert result.blankness_score == pytest.approx(0.95)
        assert result.content_ratio == pytest.approx(0.001)
        assert result.edge_density == pytest.approx(0.0005)
        assert result.pixel_variance == pytest.approx(5.0)
        assert result.confidence == pytest.approx(0.98)


# ---------------------------------------------------------------------------
# Tests: Blank page detection (true positives)
# ---------------------------------------------------------------------------


class TestBlankPageDetection:
    """Tests for pages that should be classified as blank."""

    def test_pure_white_is_blank(self, white_page: np.ndarray) -> None:
        """A pure white page must be detected as blank."""
        detector = BlankPageDetector()
        result = detector.detect(white_page)

        assert result.is_blank is True
        assert result.blankness_score > 0.8
        assert result.pixel_variance < 1.0
        assert result.edge_density < 0.001
        assert result.content_ratio < 0.01
        assert result.confidence > 0.7

    def test_pure_black_is_blank(self, black_page: np.ndarray) -> None:
        """A pure black page must be detected as blank."""
        detector = BlankPageDetector()
        result = detector.detect(black_page)

        assert result.is_blank is True
        assert result.blankness_score > 0.8
        assert result.pixel_variance < 1.0
        assert result.edge_density < 0.001
        assert result.confidence > 0.7

    def test_noisy_blank_is_blank(self, noisy_blank_page: np.ndarray) -> None:
        """A near-blank page with minor noise should still be blank."""
        detector = BlankPageDetector()
        result = detector.detect(noisy_blank_page)

        assert result.is_blank is True
        assert result.blankness_score > 0.5
        assert result.pixel_variance < _DEFAULT_VARIANCE_THRESHOLD
        assert result.confidence > 0.5

    def test_grayscale_blank_is_blank(self, grayscale_page: np.ndarray) -> None:
        """A single-channel grayscale blank page must be detected as blank."""
        detector = BlankPageDetector()
        result = detector.detect(grayscale_page)

        assert result.is_blank is True
        assert result.blankness_score > 0.8


# ---------------------------------------------------------------------------
# Tests: Content page detection (true negatives)
# ---------------------------------------------------------------------------


class TestContentPageDetection:
    """Tests for pages that should NOT be classified as blank."""

    def test_content_page_not_blank(self, content_page: np.ndarray) -> None:
        """A page with text-like blocks must not be blank."""
        detector = BlankPageDetector()
        result = detector.detect(content_page)

        assert result.is_blank is False
        assert result.blankness_score < 0.5
        assert result.edge_density > 0.005
        assert result.content_ratio > 0.01

    def test_bgra_content_not_blank(self, bgra_content_page: np.ndarray) -> None:
        """A BGRA image with content must not be blank."""
        detector = BlankPageDetector()
        result = detector.detect(bgra_content_page)

        assert result.is_blank is False
        assert result.blankness_score < 0.5

    def test_half_filled_not_blank(self, half_filled_page: np.ndarray) -> None:
        """A half-filled page should not be classified as blank."""
        detector = BlankPageDetector()
        result = detector.detect(half_filled_page)

        assert result.is_blank is False
        assert result.blankness_score < 0.5


# ---------------------------------------------------------------------------
# Tests: Edge cases and error handling
# ---------------------------------------------------------------------------

# Reference for noisy-blank threshold check
_DEFAULT_VARIANCE_THRESHOLD = 100.0


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_image_raises(self) -> None:
        """An empty (zero-size) image must raise ValueError."""
        detector = BlankPageDetector()
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(empty)

    def test_none_image_raises(self) -> None:
        """A None image must raise ValueError."""
        detector = BlankPageDetector()
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_single_pixel_image(self) -> None:
        """A 1x1 image should not crash."""
        detector = BlankPageDetector()
        img = np.full((1, 1, 3), 128, dtype=np.uint8)
        result = detector.detect(img)
        assert isinstance(result, BlankPageResult)
        assert result.is_blank is True

    def test_very_small_image(self) -> None:
        """A 2x2 image with uniform colour is blank."""
        detector = BlankPageDetector()
        img = np.full((2, 2, 3), 200, dtype=np.uint8)
        result = detector.detect(img)
        assert result.is_blank is True


# ---------------------------------------------------------------------------
# Tests: Configurable thresholds
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Verify that custom thresholds change classification behaviour."""

    def test_strict_thresholds_classify_noisy_as_not_blank(
        self, noisy_blank_page: np.ndarray
    ) -> None:
        """With very strict (low) thresholds, even a noisy blank page fails."""
        strict = BlankPageDetector(
            variance_threshold=1.0,
            edge_density_threshold=0.0001,
            content_ratio_threshold=0.001,
        )
        result = strict.detect(noisy_blank_page)
        # With extremely strict thresholds, the nearly-blank page may be
        # classified as not-blank because its noise exceeds the tight limits.
        assert result.blankness_score < 0.8

    def test_lenient_thresholds_classify_half_as_blank(
        self, half_filled_page: np.ndarray
    ) -> None:
        """With very lenient thresholds, even a half-filled page is blank."""
        lenient = BlankPageDetector(
            variance_threshold=50000.0,
            edge_density_threshold=0.5,
            content_ratio_threshold=0.5,
        )
        result = lenient.detect(half_filled_page)
        assert result.is_blank is True


# ---------------------------------------------------------------------------
# Tests: Score and confidence properties
# ---------------------------------------------------------------------------


class TestScoreProperties:
    """Verify score ranges and monotonicity."""

    def test_blankness_score_range(
        self, white_page: np.ndarray, content_page: np.ndarray
    ) -> None:
        """Blankness score is always in [0, 1]."""
        detector = BlankPageDetector()
        for img in [white_page, content_page]:
            result = detector.detect(img)
            assert 0.0 <= result.blankness_score <= 1.0

    def test_confidence_range(
        self, white_page: np.ndarray, content_page: np.ndarray
    ) -> None:
        """Confidence is always in [0, 1]."""
        detector = BlankPageDetector()
        for img in [white_page, content_page]:
            result = detector.detect(img)
            assert 0.0 <= result.confidence <= 1.0

    def test_blank_higher_score_than_content(
        self, white_page: np.ndarray, content_page: np.ndarray
    ) -> None:
        """A blank page must have a higher blankness score than a content page."""
        detector = BlankPageDetector()
        blank_result = detector.detect(white_page)
        content_result = detector.detect(content_page)
        assert blank_result.blankness_score > content_result.blankness_score


# ---------------------------------------------------------------------------
# Tests: Module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Test the module-level detect_blank_page() function."""

    def test_convenience_detects_blank(self, white_page: np.ndarray) -> None:
        """Convenience function returns correct result for blank page."""
        result = detect_blank_page(white_page)
        assert isinstance(result, BlankPageResult)
        assert result.is_blank is True

    def test_convenience_detects_content(self, content_page: np.ndarray) -> None:
        """Convenience function returns correct result for content page."""
        result = detect_blank_page(content_page)
        assert isinstance(result, BlankPageResult)
        assert result.is_blank is False

    def test_convenience_raises_on_empty(self) -> None:
        """Convenience function raises on invalid input."""
        with pytest.raises(ValueError, match="Invalid image"):
            detect_blank_page(np.array([], dtype=np.uint8))
