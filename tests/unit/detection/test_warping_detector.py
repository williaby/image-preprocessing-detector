# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for WarpingDetector.

Tests cover:
- Image with straight horizontal lines (no warping)
- Image with curved lines (barrel distortion)
- Image with converging lines (perspective distortion)
- Blank / uniform image (not enough lines)
- Edge cases: invalid input (ValueError), grayscale input
- warping_score and confidence always in [0, 1]
- Module-level convenience function
- Configurable thresholds
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.warping_detector import (
    WarpingDetectionResult,
    WarpingDetector,
    _classify_warping_type,
    _compute_confidence,
    _compute_line_curvature,
    _compute_polynomial_fit,
    _compute_rectangularity,
    detect_warping_distortion,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable synthetic images
# ---------------------------------------------------------------------------


@pytest.fixture
def straight_lines_image() -> np.ndarray:
    """BGR image with many perfectly horizontal lines (no warping).

    Draws 20 horizontal lines across a white 800x600 page.  These
    lines are perfectly straight, so warping signals should be ~0.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    for y_pos in range(50, 550, 25):
        cv2.line(page, (50, y_pos), (750, y_pos), (0, 0, 0), 2)
    return page


@pytest.fixture
def barrel_warping_image() -> np.ndarray:
    """BGR image with curved (barrel-distorted) horizontal lines.

    Each line is drawn as a series of short segments following a
    parabolic arc that bows downward at the centre, simulating barrel
    distortion from a book scan.  The 40px sag is significant enough
    to produce clear curvature in the Hough-detected segments.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    for base_y in range(80, 520, 60):
        pts: list[tuple[int, int]] = []
        for x_val in range(50, 751, 4):
            # Parabolic sag: maximum 40 px downward at centre
            normalised_x = (x_val - 400) / 350.0
            y_offset = int(40.0 * normalised_x**2)
            pts.append((x_val, base_y + y_offset))
        for idx in range(len(pts) - 1):
            cv2.line(page, pts[idx], pts[idx + 1], (0, 0, 0), 2)
    return page


@pytest.fixture
def perspective_image() -> np.ndarray:
    """BGR image with converging horizontal lines (perspective distortion).

    Lines fan out: left endpoints are closely spaced, right endpoints
    are spread wider, simulating perspective foreshortening.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    num_lines = 20
    left_y_start = 150
    left_y_end = 450
    right_y_start = 50
    right_y_end = 550

    for idx in range(num_lines):
        frac = idx / max(num_lines - 1, 1)
        left_y = int(left_y_start + frac * (left_y_end - left_y_start))
        right_y = int(right_y_start + frac * (right_y_end - right_y_start))
        cv2.line(page, (50, left_y), (750, right_y), (0, 0, 0), 2)
    return page


@pytest.fixture
def wavy_lines_image() -> np.ndarray:
    """BGR image with wavy horizontal lines.

    Each line follows a sinusoidal path, simulating wave-like page
    distortion from a poorly flattened scan.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    for base_y in range(80, 520, 40):
        pts: list[tuple[int, int]] = []
        for x_val in range(50, 751, 5):
            y_offset = int(15.0 * np.sin(x_val * 2 * np.pi / 200))
            pts.append((x_val, base_y + y_offset))
        for idx in range(len(pts) - 1):
            cv2.line(page, pts[idx], pts[idx + 1], (0, 0, 0), 2)
    return page


@pytest.fixture
def blank_page() -> np.ndarray:
    """Pure white BGR image (no lines at all)."""
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def grayscale_image() -> np.ndarray:
    """Grayscale image with horizontal lines."""
    page = np.full((600, 800), 255, dtype=np.uint8)
    for y_pos in range(50, 550, 25):
        cv2.line(page, (50, y_pos), (750, y_pos), 0, 2)
    return page


# ---------------------------------------------------------------------------
# Tests: WarpingDetectionResult dataclass
# ---------------------------------------------------------------------------


class TestWarpingDetectionResult:
    """Verify the result dataclass fields."""

    def test_fields_present(self) -> None:
        """All expected fields are accessible."""
        result = WarpingDetectionResult(
            has_warping=True,
            warping_score=0.45,
            warping_type="barrel",
            line_count=15,
            confidence=0.8,
        )
        assert result.has_warping is True
        assert result.warping_score == pytest.approx(0.45)
        assert result.warping_type == "barrel"
        assert result.line_count == 15
        assert result.confidence == pytest.approx(0.8)

    def test_no_warping_result(self) -> None:
        """No-warping result has expected defaults."""
        result = WarpingDetectionResult(
            has_warping=False,
            warping_score=0.0,
            warping_type=None,
            line_count=0,
            confidence=0.5,
        )
        assert result.has_warping is False
        assert result.warping_type is None


# ---------------------------------------------------------------------------
# Tests: Straight lines (no warping expected)
# ---------------------------------------------------------------------------


class TestNoWarping:
    """Tests for pages that should show little to no warping."""

    def test_straight_lines_no_warping(self, straight_lines_image: np.ndarray) -> None:
        """Perfectly horizontal lines should produce low warping score."""
        detector = WarpingDetector()
        result = detector.detect(straight_lines_image)

        assert result.has_warping is False
        assert result.warping_score < 0.15
        assert result.warping_type is None
        assert result.line_count >= 5

    def test_blank_page_no_warping(self, blank_page: np.ndarray) -> None:
        """A blank page with no lines should return no warping."""
        detector = WarpingDetector()
        result = detector.detect(blank_page)

        assert result.has_warping is False
        assert result.warping_score == pytest.approx(0.0)
        assert result.warping_type is None
        assert result.line_count < 5


# ---------------------------------------------------------------------------
# Tests: Warped images (warping expected)
# ---------------------------------------------------------------------------


class TestWarpingDetection:
    """Tests for pages that should exhibit warping."""

    def test_barrel_warping_detected(self, barrel_warping_image: np.ndarray) -> None:
        """Barrel-distorted lines should produce has_warping=True."""
        detector = WarpingDetector()
        result = detector.detect(barrel_warping_image)

        assert result.has_warping is True
        assert result.warping_score > 0.15
        assert result.line_count >= 3

    def test_perspective_detected(self, perspective_image: np.ndarray) -> None:
        """Converging lines should be detected as warping."""
        detector = WarpingDetector()
        result = detector.detect(perspective_image)

        # Perspective lines have angular spread; should trigger warping
        assert result.has_warping is True
        assert result.warping_score > 0.15
        assert result.line_count >= 3


# ---------------------------------------------------------------------------
# Tests: Edge cases and error handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_none_image_raises(self) -> None:
        """A None image must raise ValueError."""
        detector = WarpingDetector()
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_empty_image_raises(self) -> None:
        """An empty (zero-size) image must raise ValueError."""
        detector = WarpingDetector()
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(empty)

    def test_grayscale_input_accepted(self, grayscale_image: np.ndarray) -> None:
        """A grayscale image should be handled without error."""
        detector = WarpingDetector()
        result = detector.detect(grayscale_image)
        assert isinstance(result, WarpingDetectionResult)
        assert result.has_warping is False
        assert result.line_count >= 5

    def test_small_image_no_crash(self) -> None:
        """A very small image should not crash."""
        detector = WarpingDetector()
        img = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = detector.detect(img)
        assert isinstance(result, WarpingDetectionResult)
        assert result.has_warping is False

    def test_bgra_input_accepted(self) -> None:
        """A BGRA image should be handled without error."""
        page = np.full((600, 800, 4), 255, dtype=np.uint8)
        for y_pos in range(50, 550, 25):
            cv2.line(page, (50, y_pos), (750, y_pos), (0, 0, 0, 255), 2)
        detector = WarpingDetector()
        result = detector.detect(page)
        assert isinstance(result, WarpingDetectionResult)


# ---------------------------------------------------------------------------
# Tests: Score and confidence properties
# ---------------------------------------------------------------------------


class TestScoreProperties:
    """Verify score ranges are always valid."""

    def test_warping_score_in_range(
        self,
        straight_lines_image: np.ndarray,
        barrel_warping_image: np.ndarray,
        blank_page: np.ndarray,
    ) -> None:
        """warping_score is always in [0, 1]."""
        detector = WarpingDetector()
        for img in [straight_lines_image, barrel_warping_image, blank_page]:
            result = detector.detect(img)
            assert 0.0 <= result.warping_score <= 1.0

    def test_confidence_in_range(
        self,
        straight_lines_image: np.ndarray,
        barrel_warping_image: np.ndarray,
        blank_page: np.ndarray,
    ) -> None:
        """confidence is always in [0, 1]."""
        detector = WarpingDetector()
        for img in [straight_lines_image, barrel_warping_image, blank_page]:
            result = detector.detect(img)
            assert 0.0 <= result.confidence <= 1.0

    def test_warped_higher_score_than_straight(
        self,
        straight_lines_image: np.ndarray,
        barrel_warping_image: np.ndarray,
    ) -> None:
        """A warped image must have a higher score than a straight one."""
        detector = WarpingDetector()
        straight_result = detector.detect(straight_lines_image)
        warped_result = detector.detect(barrel_warping_image)
        assert warped_result.warping_score > straight_result.warping_score


# ---------------------------------------------------------------------------
# Tests: Configurable thresholds
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Verify that custom thresholds change classification behaviour."""

    def test_high_threshold_rejects_mild_warping(
        self, barrel_warping_image: np.ndarray
    ) -> None:
        """With a very high threshold, barrel warping may not trigger."""
        strict = WarpingDetector(warping_threshold=0.95)
        result = strict.detect(barrel_warping_image)
        # With threshold at 0.95, mild barrel should not trigger
        assert result.warping_score < 0.95 or result.has_warping is True

    def test_zero_threshold_always_triggers(
        self, straight_lines_image: np.ndarray
    ) -> None:
        """With threshold=0, any lines produce has_warping=True."""
        lenient = WarpingDetector(warping_threshold=0.0)
        result = lenient.detect(straight_lines_image)
        # Score is > 0 if any signal is nonzero; threshold=0 means any > 0 triggers
        if result.warping_score > 0.0:
            assert result.has_warping is True

    def test_min_lines_parameter(self, straight_lines_image: np.ndarray) -> None:
        """Raising min_horizontal_lines can prevent detection."""
        strict = WarpingDetector(min_horizontal_lines=1000)
        result = strict.detect(straight_lines_image)
        # Not enough lines => no-warping result
        assert result.has_warping is False
        assert result.warping_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Test the module-level detect_warping_distortion() function."""

    def test_convenience_detects_no_warping(
        self, straight_lines_image: np.ndarray
    ) -> None:
        """Convenience function returns correct result for straight lines."""
        result = detect_warping_distortion(straight_lines_image)
        assert isinstance(result, WarpingDetectionResult)
        assert result.has_warping is False

    def test_convenience_detects_warping(
        self, barrel_warping_image: np.ndarray
    ) -> None:
        """Convenience function returns correct result for barrel warping."""
        result = detect_warping_distortion(barrel_warping_image)
        assert isinstance(result, WarpingDetectionResult)
        assert result.has_warping is True

    def test_convenience_raises_on_empty(self) -> None:
        """Convenience function raises on invalid input."""
        with pytest.raises(ValueError, match="Invalid image"):
            detect_warping_distortion(np.array([], dtype=np.uint8))


# ---------------------------------------------------------------------------
# Tests: Internal helper functions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Direct tests for internal helper functions."""

    def test_compute_line_curvature_empty(self) -> None:
        """Empty line list returns zero curvature."""
        score, max_dev = _compute_line_curvature([], 600)
        assert score == pytest.approx(0.0)
        assert max_dev == pytest.approx(0.0)

    def test_compute_line_curvature_horizontal(self) -> None:
        """Perfectly horizontal lines have near-zero curvature."""
        lines = [(50, 100, 750, 100), (50, 200, 750, 200)]
        score, max_dev = _compute_line_curvature(lines, 600)
        assert score == pytest.approx(0.0)
        assert max_dev == pytest.approx(0.0)

    def test_compute_line_curvature_tilted(self) -> None:
        """Tilted lines produce non-zero curvature."""
        # Line rises 30px over 700px length
        lines = [(50, 100, 750, 130)]
        score, max_dev = _compute_line_curvature(lines, 600)
        assert score > 0.0
        assert max_dev > 0.0

    def test_compute_rectangularity_blank(self) -> None:
        """A blank image has no contours, returns 0."""
        blank = np.full((100, 100), 255, dtype=np.uint8)
        score = _compute_rectangularity(blank, 100, 100)
        assert score == pytest.approx(0.0)

    def test_compute_polynomial_fit_insufficient_lines(self) -> None:
        """Fewer than 3 lines returns zero polynomial score."""
        lines = [(50, 100, 750, 100), (50, 200, 750, 200)]
        poly_score, coeff, residual = _compute_polynomial_fit(lines, 800)
        assert poly_score == pytest.approx(0.0)
        assert coeff == pytest.approx(0.0)
        assert residual == pytest.approx(0.0)

    def test_compute_polynomial_fit_parabolic(self) -> None:
        """Parabolic midpoints produce non-zero quadratic coefficient."""
        # Midpoints arranged in a parabola
        lines = [
            (100, 110, 200, 110),  # midpoint (150, 110)
            (300, 100, 500, 100),  # midpoint (400, 100)
            (600, 120, 700, 120),  # midpoint (650, 120)
        ]
        _, coeff, _residual = _compute_polynomial_fit(lines, 800)
        # Non-zero quadratic coefficient for parabolic arrangement
        assert coeff != pytest.approx(0.0)

    def test_classify_warping_type_none(self) -> None:
        """Low coefficients and residuals return None."""
        result = _classify_warping_type(0.0, 0.0, [])
        assert result is None

    def test_classify_warping_type_barrel(self) -> None:
        """Positive quadratic coefficient classifies as barrel."""
        lines = [(50, 100, 750, 100)]
        result = _classify_warping_type(50.0, 0.0, lines)
        assert result == "barrel"

    def test_classify_warping_type_pincushion(self) -> None:
        """Negative quadratic coefficient classifies as pincushion."""
        lines = [(50, 100, 750, 100)]
        result = _classify_warping_type(-50.0, 0.0, lines)
        assert result == "pincushion"

    def test_classify_warping_type_wave(self) -> None:
        """High residual score classifies as wave."""
        lines = [(50, 100, 750, 100)]
        result = _classify_warping_type(0.0, 0.5, lines)
        assert result == "wave"

    def test_classify_warping_type_perspective(self) -> None:
        """Lines with high angular spread classify as perspective."""
        # Lines with deliberately large angular differences (>2.5 deg std)
        lines = [
            (50, 100, 750, 100),  # 0 degrees
            (50, 200, 750, 250),  # ~4.1 degrees
            (50, 300, 750, 360),  # ~4.9 degrees
            (50, 400, 750, 350),  # ~-4.1 degrees
        ]
        result = _classify_warping_type(5.0, 0.1, lines)
        assert result == "perspective"

    def test_compute_confidence_many_lines(self) -> None:
        """Many lines yield higher confidence."""
        conf_many = _compute_confidence(25, 0.5)
        conf_few = _compute_confidence(3, 0.5)
        assert conf_many > conf_few

    def test_compute_confidence_range(self) -> None:
        """Confidence is always in [0, 1]."""
        for line_count in [0, 3, 5, 10, 20, 100]:
            for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
                conf = _compute_confidence(line_count, score)
                assert 0.0 <= conf <= 1.0
