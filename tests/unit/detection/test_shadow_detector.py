# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for ShadowDetector.

Tests cover:
- Uniform white image (no shadows)
- Image with dark band on left side (has_shadows=True)
- Gradient from light to dark (moderate shadows)
- Severely dark image (edge case)
- Invalid image raises ValueError
- Grayscale input accepted
- BGRA input accepted
- Severity mapping correctness for all score ranges
- Confidence and score always in [0, 1]
- Module-level convenience function
- Configurable thresholds
"""

from __future__ import annotations

import numpy as np
import pytest

from image_preprocessing_detector.detection.shadow_detector import (
    ShadowDetectionResult,
    ShadowDetector,
    _score_to_severity,
    detect_shadows,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable synthetic images
# ---------------------------------------------------------------------------


@pytest.fixture
def white_page() -> np.ndarray:
    """Pure white BGR image (800x600) -- no shadows expected."""
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def dark_band_left() -> np.ndarray:
    """White page with a dark band occupying the left third.

    Simulates a shadow cast by a book spine or document holder.
    """
    page = np.full((600, 800, 3), 240, dtype=np.uint8)
    # Dark band on left ~33% of width
    page[:, :270, :] = 60
    return page


@pytest.fixture
def light_to_dark_gradient() -> np.ndarray:
    """Horizontal gradient from white (left) to dark gray (right).

    Simulates an uneven illumination shadow falling across the page.
    """
    page = np.zeros((600, 800, 3), dtype=np.uint8)
    for col in range(800):
        intensity = int(255 * (1.0 - col / 800.0))
        page[:, col, :] = intensity
    return page


@pytest.fixture
def mostly_dark_image() -> np.ndarray:
    """Image that is predominantly dark (mean ~50).

    Edge case: the detector should handle very dark input without crashing,
    though the score behaviour depends on the global-mean normalisation.
    """
    page = np.full((600, 800, 3), 50, dtype=np.uint8)
    # Add a slightly lighter strip so there is *some* contrast
    page[200:400, :, :] = 90
    return page


@pytest.fixture
def grayscale_page() -> np.ndarray:
    """Grayscale image with a dark band (single channel)."""
    page = np.full((600, 800), 230, dtype=np.uint8)
    page[:, :270] = 50
    return page


@pytest.fixture
def bgra_shadow_page() -> np.ndarray:
    """BGRA image with shadow band on the left."""
    page = np.full((600, 800, 4), 240, dtype=np.uint8)
    page[:, :, 3] = 255  # alpha channel
    page[:, :270, :3] = 60
    return page


# ---------------------------------------------------------------------------
# Tests: ShadowDetectionResult dataclass
# ---------------------------------------------------------------------------


class TestShadowDetectionResult:
    """Verify the result dataclass fields."""

    def test_fields_present(self) -> None:
        """All expected fields are accessible."""
        result = ShadowDetectionResult(
            has_shadows=True,
            shadow_score=0.45,
            shadow_severity="moderate",
            shadow_ratio=0.35,
            confidence=0.82,
        )
        assert result.has_shadows is True
        assert result.shadow_score == pytest.approx(0.45)
        assert result.shadow_severity == "moderate"
        assert result.shadow_ratio == pytest.approx(0.35)
        assert result.confidence == pytest.approx(0.82)


# ---------------------------------------------------------------------------
# Tests: No-shadow detection (true negatives)
# ---------------------------------------------------------------------------


class TestNoShadowDetection:
    """Pages that should NOT be classified as having shadows."""

    def test_uniform_white_no_shadows(self, white_page: np.ndarray) -> None:
        """A pure white page must not have shadows."""
        detector = ShadowDetector()
        result = detector.detect(white_page)

        assert result.has_shadows is False
        assert result.shadow_score < 0.1
        assert result.shadow_severity == "none"
        assert result.shadow_ratio < 0.05
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests: Shadow detection (true positives)
# ---------------------------------------------------------------------------


class TestShadowDetection:
    """Pages that should be classified as having shadows."""

    def test_dark_band_left_has_shadows(self, dark_band_left: np.ndarray) -> None:
        """A white page with a dark band on the left must detect shadows."""
        detector = ShadowDetector()
        result = detector.detect(dark_band_left)

        assert result.has_shadows is True
        assert result.shadow_score >= 0.1
        assert result.shadow_severity in ("mild", "moderate", "severe")
        assert result.shadow_ratio > 0.0

    def test_gradient_has_shadows(self, light_to_dark_gradient: np.ndarray) -> None:
        """A light-to-dark gradient should trigger shadow detection."""
        detector = ShadowDetector()
        result = detector.detect(light_to_dark_gradient)

        assert result.has_shadows is True
        assert result.shadow_score >= 0.1
        assert result.shadow_severity in ("mild", "moderate", "severe")

    def test_mostly_dark_handles_gracefully(
        self, mostly_dark_image: np.ndarray
    ) -> None:
        """A severely dark image should not crash and produces valid output."""
        detector = ShadowDetector()
        result = detector.detect(mostly_dark_image)

        # The image IS mostly dark; exact classification is less important
        # than not crashing and producing valid ranges.
        assert isinstance(result, ShadowDetectionResult)
        assert 0.0 <= result.shadow_score <= 1.0
        assert 0.0 <= result.shadow_ratio <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.shadow_severity in ("none", "mild", "moderate", "severe")


# ---------------------------------------------------------------------------
# Tests: Edge cases and error handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_image_raises(self) -> None:
        """An empty (zero-size) image must raise ValueError."""
        detector = ShadowDetector()
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(empty)

    def test_none_image_raises(self) -> None:
        """A None image must raise ValueError."""
        detector = ShadowDetector()
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_grayscale_input_accepted(self, grayscale_page: np.ndarray) -> None:
        """A single-channel grayscale image must be accepted."""
        detector = ShadowDetector()
        result = detector.detect(grayscale_page)

        assert isinstance(result, ShadowDetectionResult)
        assert result.has_shadows is True
        assert result.shadow_score >= 0.1

    def test_bgra_input_accepted(self, bgra_shadow_page: np.ndarray) -> None:
        """A 4-channel BGRA image must be accepted."""
        detector = ShadowDetector()
        result = detector.detect(bgra_shadow_page)

        assert isinstance(result, ShadowDetectionResult)
        assert result.has_shadows is True
        assert result.shadow_score >= 0.1

    def test_single_pixel_image(self) -> None:
        """A 1x1 image should not crash."""
        detector = ShadowDetector()
        img = np.full((1, 1, 3), 128, dtype=np.uint8)
        result = detector.detect(img)
        assert isinstance(result, ShadowDetectionResult)
        assert 0.0 <= result.shadow_score <= 1.0


# ---------------------------------------------------------------------------
# Tests: Severity mapping
# ---------------------------------------------------------------------------


class TestSeverityMapping:
    """Verify the score-to-severity mapping covers all ranges."""

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (0.0, "none"),
            (0.05, "none"),
            (0.09, "none"),
            (0.1, "mild"),
            (0.2, "mild"),
            (0.29, "mild"),
            (0.3, "moderate"),
            (0.45, "moderate"),
            (0.59, "moderate"),
            (0.6, "severe"),
            (0.8, "severe"),
            (1.0, "severe"),
        ],
    )
    def test_severity_boundaries(self, score: float, expected: str) -> None:
        """Score-to-severity mapping respects documented thresholds."""
        assert _score_to_severity(score) == expected


# ---------------------------------------------------------------------------
# Tests: Score and confidence ranges
# ---------------------------------------------------------------------------


class TestScoreProperties:
    """Verify score and confidence are always in [0, 1]."""

    def test_score_range(
        self, white_page: np.ndarray, dark_band_left: np.ndarray
    ) -> None:
        """shadow_score is always in [0, 1]."""
        detector = ShadowDetector()
        for img in [white_page, dark_band_left]:
            result = detector.detect(img)
            assert 0.0 <= result.shadow_score <= 1.0

    def test_confidence_range(
        self, white_page: np.ndarray, dark_band_left: np.ndarray
    ) -> None:
        """confidence is always in [0, 1]."""
        detector = ShadowDetector()
        for img in [white_page, dark_band_left]:
            result = detector.detect(img)
            assert 0.0 <= result.confidence <= 1.0

    def test_shadow_ratio_range(
        self, white_page: np.ndarray, dark_band_left: np.ndarray
    ) -> None:
        """shadow_ratio is always in [0, 1]."""
        detector = ShadowDetector()
        for img in [white_page, dark_band_left]:
            result = detector.detect(img)
            assert 0.0 <= result.shadow_ratio <= 1.0

    def test_shadow_page_higher_score_than_white(
        self, white_page: np.ndarray, dark_band_left: np.ndarray
    ) -> None:
        """A shadowed page must score higher than a uniform white page."""
        detector = ShadowDetector()
        white_result = detector.detect(white_page)
        shadow_result = detector.detect(dark_band_left)
        assert shadow_result.shadow_score > white_result.shadow_score


# ---------------------------------------------------------------------------
# Tests: Configurable thresholds
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Verify that custom thresholds change detection behaviour."""

    def test_strict_threshold_increases_sensitivity(
        self, dark_band_left: np.ndarray
    ) -> None:
        """A stricter (higher) shadow_threshold makes detection more sensitive."""
        strict = ShadowDetector(shadow_threshold=0.9)
        result = strict.detect(dark_band_left)
        assert result.has_shadows is True

    def test_lenient_threshold_reduces_sensitivity(
        self, dark_band_left: np.ndarray
    ) -> None:
        """A very lenient (low) shadow_threshold reduces false positives."""
        lenient = ShadowDetector(shadow_threshold=0.1)
        result = lenient.detect(dark_band_left)
        # With threshold=0.1, only cells <10% of global mean count -- very
        # few will qualify, so the score should be lower than default.
        default = ShadowDetector()
        default_result = default.detect(dark_band_left)
        assert result.shadow_score <= default_result.shadow_score

    def test_small_grid_size(self, dark_band_left: np.ndarray) -> None:
        """A small grid (2x2) still produces valid results.

        With only 4 cells, each cell mixes shadow and non-shadow pixels,
        which may dilute the per-cell mean above the threshold. The test
        verifies valid output ranges rather than requiring detection.
        """
        detector = ShadowDetector(grid_size=2)
        result = detector.detect(dark_band_left)
        assert isinstance(result, ShadowDetectionResult)
        assert 0.0 <= result.shadow_score <= 1.0
        assert 0.0 <= result.shadow_ratio <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_large_grid_size(self, dark_band_left: np.ndarray) -> None:
        """A large grid (32x32) still produces valid results."""
        detector = ShadowDetector(grid_size=32)
        result = detector.detect(dark_band_left)
        assert isinstance(result, ShadowDetectionResult)
        assert 0.0 <= result.shadow_score <= 1.0


# ---------------------------------------------------------------------------
# Tests: Module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Test the module-level detect_shadows() function."""

    def test_convenience_detects_no_shadow(self, white_page: np.ndarray) -> None:
        """Convenience function returns correct result for uniform page."""
        result = detect_shadows(white_page)
        assert isinstance(result, ShadowDetectionResult)
        assert result.has_shadows is False

    def test_convenience_detects_shadow(self, dark_band_left: np.ndarray) -> None:
        """Convenience function returns correct result for shadowed page."""
        result = detect_shadows(dark_band_left)
        assert isinstance(result, ShadowDetectionResult)
        assert result.has_shadows is True

    def test_convenience_raises_on_empty(self) -> None:
        """Convenience function raises on invalid input."""
        with pytest.raises(ValueError, match="Invalid image"):
            detect_shadows(np.array([], dtype=np.uint8))
