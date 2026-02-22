# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for PerspectiveCorrector.

Tests cover:
- Successful perspective correction on synthetic warped images
- Warping score gate (> 0.75 blocked)
- No quad found returns original
- Convenience function
- Point ordering
- Invalid input handling
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.correction.perspective_correction import (
    PerspectiveCorrector,
    _order_points,
    correct_perspective,
)

# =============================================================================
# Synthetic test images
# =============================================================================


def _make_perspective_image() -> tuple[np.ndarray, np.ndarray]:
    """Create a synthetic image with a white quad on black background.

    Returns:
        Tuple of (warped image, original 4 corners).
    """
    # Start with a clean white rectangle
    canvas = np.zeros((800, 600, 3), dtype=np.uint8)

    # Define a trapezoid (perspective-distorted rectangle)
    pts = np.array(
        [[100, 100], [480, 80], [500, 680], [80, 700]],
        dtype=np.int32,
    )
    cv2.fillPoly(canvas, [pts], (255, 255, 255))

    return canvas, pts.astype(np.float32)


def _make_no_quad_image() -> np.ndarray:
    """Create an image with no clear quadrilateral.

    Uses a uniform mid-gray image with a few small scattered dots.
    Canny edge detection finds nothing useful -> no quad.
    """
    image = np.full((500, 500, 3), 128, dtype=np.uint8)
    # Add a few tiny dots (too small to form a contour > 10% area)
    image[100, 100] = [0, 0, 0]
    image[200, 300] = [255, 255, 255]
    return image


# =============================================================================
# Tests: _order_points
# =============================================================================


class TestOrderPoints:
    """Tests for the corner point ordering utility."""

    def test_already_ordered(self) -> None:
        """Points already in TL, TR, BR, BL order stay the same."""
        pts = np.array(
            [[0, 0], [100, 0], [100, 100], [0, 100]],
            dtype=np.float32,
        )
        ordered = _order_points(pts)
        np.testing.assert_array_almost_equal(ordered[0], [0, 0])  # TL
        np.testing.assert_array_almost_equal(ordered[1], [100, 0])  # TR
        np.testing.assert_array_almost_equal(ordered[2], [100, 100])  # BR
        np.testing.assert_array_almost_equal(ordered[3], [0, 100])  # BL

    def test_shuffled_order(self) -> None:
        """Shuffled points get correctly reordered."""
        pts = np.array(
            [[100, 100], [0, 0], [0, 100], [100, 0]],
            dtype=np.float32,
        )
        ordered = _order_points(pts)
        np.testing.assert_array_almost_equal(ordered[0], [0, 0])
        np.testing.assert_array_almost_equal(ordered[2], [100, 100])


# =============================================================================
# Tests: PerspectiveCorrector
# =============================================================================


class TestPerspectiveCorrector:
    """Core PerspectiveCorrector tests."""

    def test_corrects_synthetic_perspective(self) -> None:
        """Synthetic perspective image should be corrected."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image, warping_score=0.3)

        assert result.applied is True
        assert result.skipped_reason is None
        assert result.parameters["output_size"] != (0, 0)
        assert result.parameters["corners"] is not None

    def test_warping_gate_blocks_extreme(self) -> None:
        """warping_score > 0.75 should block correction."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image, warping_score=0.85)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "VLM" in result.skipped_reason
        assert np.array_equal(result.corrected_image, image)

    def test_warping_gate_boundary(self) -> None:
        """warping_score == 0.75 should NOT block (only > blocks)."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image, warping_score=0.75)
        # Should attempt correction (may succeed or fail based on quad detection)
        # Key: not blocked by gate
        assert result.skipped_reason is None or "VLM" not in result.skipped_reason

    def test_no_quad_returns_original(self) -> None:
        """Random noise image has no quad -> return original."""
        image = _make_no_quad_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image, warping_score=0.3)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "quadrilateral" in result.skipped_reason.lower()

    def test_custom_warping_threshold(self) -> None:
        """Custom warping_block_threshold respected."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector(warping_block_threshold=0.50)
        result = corrector.correct(image, warping_score=0.6)

        assert result.applied is False
        assert "VLM" in (result.skipped_reason or "")

    def test_output_is_bgr(self) -> None:
        """Output should maintain 3-channel BGR format."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image, warping_score=0.3)
        if result.applied:
            assert len(result.corrected_image.shape) == 3
            assert result.corrected_image.shape[2] == 3

    def test_invalid_image_raises(self) -> None:
        """None or empty image should raise ValueError."""
        corrector = PerspectiveCorrector()
        with pytest.raises(ValueError, match="Invalid"):
            corrector.correct(np.array([]))

    def test_none_image_raises(self) -> None:
        corrector = PerspectiveCorrector()
        with pytest.raises(ValueError, match="Invalid"):
            corrector.correct(None)  # type: ignore[arg-type]

    def test_zero_warping_score_allowed(self) -> None:
        """warping_score=0.0 should not block."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image, warping_score=0.0)
        # Should attempt correction
        assert result.skipped_reason is None or "VLM" not in result.skipped_reason

    def test_uniform_image_no_quad(self) -> None:
        """Uniform color image has no edges -> no quad."""
        image = np.full((500, 500, 3), 128, dtype=np.uint8)
        corrector = PerspectiveCorrector()
        result = corrector.correct(image)
        assert result.applied is False

    def test_parameters_contain_original_size(self) -> None:
        """Parameters should always include original_size."""
        image, _ = _make_perspective_image()
        corrector = PerspectiveCorrector()
        result = corrector.correct(image)
        assert "original_size" in result.parameters


class TestCorrectPerspectiveConvenience:
    """Convenience function tests."""

    def test_returns_result(self) -> None:
        image, _ = _make_perspective_image()
        result = correct_perspective(image, warping_score=0.3)
        assert result.applied is True

    def test_blocks_extreme_warping(self) -> None:
        image, _ = _make_perspective_image()
        result = correct_perspective(image, warping_score=0.9)
        assert result.applied is False
