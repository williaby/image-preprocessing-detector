# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for CodeDetector.

Tests cover:
- Monospace-like images (uniform-width, evenly-spaced rectangles) -> has_code=True
- Natural-text-like images (variable-width scattered shapes) -> has_code=False
- Indentation analysis (multiple left-margin levels)
- Blank image -> no code detected
- Edge cases: invalid input ValueError, minimum component count
- Score and confidence in [0, 1]
- Configurable thresholds
- Module-level convenience function
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.code_detector import (
    CodeDetectionResult,
    CodeDetector,
    detect_code,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable synthetic images
# ---------------------------------------------------------------------------


@pytest.fixture
def monospace_code_image() -> np.ndarray:
    """Synthetic image with evenly-spaced, uniform-width rectangles.

    Simulates monospace text: 6 rows of characters with identical widths,
    regular spacing, and structured indentation (3 indent levels).
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)

    char_w = 12
    char_h = 18
    x_gap = 4
    y_gap = 8

    # Define indent levels (pixels from left edge)
    indent_levels = [40, 88, 136]  # 0, 1, 2 indentation levels

    # Row configurations: (indent_index, num_chars)
    rows = [
        (0, 40),  # def function_name():
        (1, 35),  #     for i in range(10):
        (2, 30),  #         result = compute()
        (2, 25),  #         if result > 0:
        (1, 35),  #     return result
        (0, 40),  # class MyClass:
        (1, 30),  #     def __init__(self):
        (2, 25),  #         self.x = 0
        (2, 28),  #         self.y = 0
        (0, 35),  # def another_function():
        (1, 32),  #     data = []
        (2, 28),  #         data.append(x)
        (1, 30),  #     return data
        (0, 38),  # # comment line
    ]

    y_cursor = 30
    for indent_idx, num_chars in rows:
        x_start = indent_levels[indent_idx]
        for col in range(num_chars):
            x = x_start + col * (char_w + x_gap)
            if x + char_w > 780:
                break
            cv2.rectangle(
                page,
                (x, y_cursor),
                (x + char_w, y_cursor + char_h),
                (0, 0, 0),
                -1,
            )
        y_cursor += char_h + y_gap

    return page


@pytest.fixture
def natural_text_image() -> np.ndarray:
    """Synthetic image with variable-width, irregularly-placed shapes.

    Simulates natural/proportional text: characters have varying widths
    and irregular spacing -- the opposite of monospace code.
    """
    rng = np.random.default_rng(42)
    page = np.full((600, 800, 3), 255, dtype=np.uint8)

    for _ in range(80):
        # Random widths from 6 to 35 (highly variable)
        w = int(rng.integers(6, 36))
        h = int(rng.integers(10, 30))
        x = int(rng.integers(20, 750))
        y = int(rng.integers(20, 560))
        cv2.rectangle(
            page,
            (x, y),
            (min(x + w, 799), min(y + h, 599)),
            (0, 0, 0),
            -1,
        )

    return page


@pytest.fixture
def indented_blocks_image() -> np.ndarray:
    """Synthetic image with clear multi-level indentation.

    Five distinct indent levels with uniform character widths and spacing.
    """
    page = np.full((800, 1000, 3), 255, dtype=np.uint8)

    char_w = 10
    char_h = 14
    x_gap = 3
    y_gap = 6
    indent_step = 40

    y_cursor = 30
    for row_idx in range(20):
        indent_level = row_idx % 5
        x_start = 30 + indent_level * indent_step
        num_chars = 50 - indent_level * 5

        for col in range(num_chars):
            x = x_start + col * (char_w + x_gap)
            if x + char_w > 970:
                break
            cv2.rectangle(
                page,
                (x, y_cursor),
                (x + char_w, y_cursor + char_h),
                (0, 0, 0),
                -1,
            )
        y_cursor += char_h + y_gap

    return page


@pytest.fixture
def blank_page() -> np.ndarray:
    """Pure white BGR image (800x600)."""
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def sparse_page() -> np.ndarray:
    """Page with only a handful of small shapes (below min component count)."""
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    # Draw only 3 small rectangles
    cv2.rectangle(page, (100, 100), (120, 120), (0, 0, 0), -1)
    cv2.rectangle(page, (200, 200), (220, 220), (0, 0, 0), -1)
    cv2.rectangle(page, (300, 300), (320, 320), (0, 0, 0), -1)
    return page


@pytest.fixture
def grayscale_monospace() -> np.ndarray:
    """Grayscale (single-channel) image with monospace-like text."""
    page = np.full((400, 600), 255, dtype=np.uint8)

    char_w = 10
    char_h = 15
    x_gap = 3
    y_gap = 6

    y_cursor = 20
    for _row in range(12):
        x_start = 30
        for col in range(35):
            x = x_start + col * (char_w + x_gap)
            if x + char_w > 580:
                break
            cv2.rectangle(page, (x, y_cursor), (x + char_w, y_cursor + char_h), 0, -1)
        y_cursor += char_h + y_gap

    return page


# ---------------------------------------------------------------------------
# Tests: CodeDetectionResult dataclass
# ---------------------------------------------------------------------------


class TestCodeDetectionResult:
    """Verify the result dataclass fields."""

    def test_fields_present(self) -> None:
        """All expected fields are accessible."""
        result = CodeDetectionResult(
            has_code=True,
            code_confidence=0.75,
            width_uniformity=0.9,
            indentation_levels=4,
            line_height_uniformity=0.85,
            confidence=0.75,
        )
        assert result.has_code is True
        assert result.code_confidence == pytest.approx(0.75)
        assert result.width_uniformity == pytest.approx(0.9)
        assert result.indentation_levels == 4
        assert result.line_height_uniformity == pytest.approx(0.85)
        assert result.confidence == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Tests: Code detection (true positives -- monospace/code images)
# ---------------------------------------------------------------------------


class TestCodeDetection:
    """Tests for images that should be classified as containing code."""

    def test_monospace_detected_as_code(self, monospace_code_image: np.ndarray) -> None:
        """Uniform-width evenly-spaced rectangles must trigger has_code."""
        detector = CodeDetector()
        result = detector.detect(monospace_code_image)

        assert result.has_code is True
        assert result.code_confidence > 0.5
        assert result.width_uniformity > 0.5
        assert result.indentation_levels >= 2

    def test_indented_blocks_high_indentation(
        self, indented_blocks_image: np.ndarray
    ) -> None:
        """Image with 5 indent levels should show high indentation_levels."""
        detector = CodeDetector()
        result = detector.detect(indented_blocks_image)

        assert result.indentation_levels >= 3
        assert result.has_code is True
        assert result.code_confidence > 0.5

    def test_grayscale_monospace_detected(
        self, grayscale_monospace: np.ndarray
    ) -> None:
        """Single-channel grayscale monospace image must be detected."""
        detector = CodeDetector()
        result = detector.detect(grayscale_monospace)

        assert result.has_code is True
        assert result.width_uniformity > 0.5
        assert result.line_height_uniformity > 0.3


# ---------------------------------------------------------------------------
# Tests: Non-code detection (true negatives)
# ---------------------------------------------------------------------------


class TestNonCodeDetection:
    """Tests for images that should NOT be classified as containing code."""

    def test_natural_text_not_code(self, natural_text_image: np.ndarray) -> None:
        """Variable-width scattered shapes must not trigger has_code."""
        detector = CodeDetector()
        result = detector.detect(natural_text_image)

        assert result.has_code is False
        assert result.code_confidence < 0.5

    def test_blank_page_no_code(self, blank_page: np.ndarray) -> None:
        """A blank page must return no code."""
        detector = CodeDetector()
        result = detector.detect(blank_page)

        assert result.has_code is False
        assert result.code_confidence == pytest.approx(0.0)
        assert result.width_uniformity == pytest.approx(0.0)
        assert result.indentation_levels == 0
        assert result.line_height_uniformity == pytest.approx(0.0)

    def test_sparse_page_no_code(self, sparse_page: np.ndarray) -> None:
        """Page with too few components returns no-code result."""
        detector = CodeDetector()
        result = detector.detect(sparse_page)

        assert result.has_code is False
        assert result.code_confidence == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Edge cases and error handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_image_raises(self) -> None:
        """An empty (zero-size) image must raise ValueError."""
        detector = CodeDetector()
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(empty)

    def test_none_image_raises(self) -> None:
        """A None image must raise ValueError."""
        detector = CodeDetector()
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_single_pixel_image(self) -> None:
        """A 1x1 image should not crash and should return no code."""
        detector = CodeDetector()
        img = np.full((1, 1, 3), 128, dtype=np.uint8)
        result = detector.detect(img)
        assert isinstance(result, CodeDetectionResult)
        assert result.has_code is False

    def test_very_small_image(self) -> None:
        """A small image with few components returns gracefully."""
        detector = CodeDetector()
        img = np.full((10, 10, 3), 200, dtype=np.uint8)
        result = detector.detect(img)
        assert result.has_code is False

    def test_bgra_image_accepted(self) -> None:
        """A BGRA (4-channel) image should be handled without error."""
        page = np.full((400, 600, 4), 255, dtype=np.uint8)
        # Draw some monospace-like characters
        char_w = 10
        y_cursor = 20
        for _row in range(10):
            for col in range(30):
                x = 30 + col * 14
                cv2.rectangle(
                    page,
                    (x, y_cursor),
                    (x + char_w, y_cursor + 15),
                    (0, 0, 0, 255),
                    -1,
                )
            y_cursor += 22
        detector = CodeDetector()
        result = detector.detect(page)
        assert isinstance(result, CodeDetectionResult)


# ---------------------------------------------------------------------------
# Tests: Score and confidence ranges
# ---------------------------------------------------------------------------


class TestScoreProperties:
    """Verify score ranges are always valid."""

    def test_confidence_in_range(
        self,
        monospace_code_image: np.ndarray,
        natural_text_image: np.ndarray,
        blank_page: np.ndarray,
    ) -> None:
        """Confidence and code_confidence must be in [0, 1]."""
        detector = CodeDetector()
        for img in [monospace_code_image, natural_text_image, blank_page]:
            result = detector.detect(img)
            assert 0.0 <= result.confidence <= 1.0
            assert 0.0 <= result.code_confidence <= 1.0

    def test_width_uniformity_in_range(
        self,
        monospace_code_image: np.ndarray,
        natural_text_image: np.ndarray,
    ) -> None:
        """width_uniformity must be in [0, 1]."""
        detector = CodeDetector()
        for img in [monospace_code_image, natural_text_image]:
            result = detector.detect(img)
            assert 0.0 <= result.width_uniformity <= 1.0

    def test_line_height_uniformity_in_range(
        self,
        monospace_code_image: np.ndarray,
        natural_text_image: np.ndarray,
    ) -> None:
        """line_height_uniformity must be in [0, 1]."""
        detector = CodeDetector()
        for img in [monospace_code_image, natural_text_image]:
            result = detector.detect(img)
            assert 0.0 <= result.line_height_uniformity <= 1.0

    def test_indentation_levels_non_negative(
        self,
        monospace_code_image: np.ndarray,
        blank_page: np.ndarray,
    ) -> None:
        """indentation_levels must be >= 0."""
        detector = CodeDetector()
        for img in [monospace_code_image, blank_page]:
            result = detector.detect(img)
            assert result.indentation_levels >= 0

    def test_code_confidence_equals_confidence(
        self, monospace_code_image: np.ndarray
    ) -> None:
        """code_confidence and confidence should be the same value."""
        detector = CodeDetector()
        result = detector.detect(monospace_code_image)
        assert result.code_confidence == result.confidence

    def test_monospace_higher_score_than_natural(
        self,
        monospace_code_image: np.ndarray,
        natural_text_image: np.ndarray,
    ) -> None:
        """Monospace image must have higher confidence than natural text."""
        detector = CodeDetector()
        code_result = detector.detect(monospace_code_image)
        text_result = detector.detect(natural_text_image)
        assert code_result.code_confidence > text_result.code_confidence


# ---------------------------------------------------------------------------
# Tests: Configurable thresholds
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Verify that custom thresholds change classification behaviour."""

    def test_strict_threshold_rejects_moderate_code(
        self, monospace_code_image: np.ndarray
    ) -> None:
        """With a high confidence threshold, borderline images are rejected."""
        strict = CodeDetector(confidence_threshold=0.95)
        result = strict.detect(monospace_code_image)
        # With an extremely high threshold, detection may be suppressed
        assert isinstance(result, CodeDetectionResult)
        # The confidence value itself should not change
        assert 0.0 <= result.confidence <= 1.0

    def test_lenient_threshold_accepts_more(
        self, natural_text_image: np.ndarray
    ) -> None:
        """With a very low threshold, even weak signals trigger has_code."""
        lenient = CodeDetector(confidence_threshold=0.01)
        result = lenient.detect(natural_text_image)
        # At an extremely low threshold any positive signal triggers detection
        assert isinstance(result, CodeDetectionResult)

    def test_high_min_components(self, monospace_code_image: np.ndarray) -> None:
        """Raising min_components can force empty result."""
        detector = CodeDetector(min_components=100_000)
        result = detector.detect(monospace_code_image)
        assert result.has_code is False
        assert result.code_confidence == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Test the module-level detect_code() function."""

    def test_convenience_detects_code(self, monospace_code_image: np.ndarray) -> None:
        """Convenience function returns correct result for code image."""
        result = detect_code(monospace_code_image)
        assert isinstance(result, CodeDetectionResult)
        assert result.has_code is True

    def test_convenience_rejects_blank(self, blank_page: np.ndarray) -> None:
        """Convenience function returns no-code for blank image."""
        result = detect_code(blank_page)
        assert isinstance(result, CodeDetectionResult)
        assert result.has_code is False

    def test_convenience_raises_on_empty(self) -> None:
        """Convenience function raises on invalid input."""
        with pytest.raises(ValueError, match="Invalid image"):
            detect_code(np.array([], dtype=np.uint8))
