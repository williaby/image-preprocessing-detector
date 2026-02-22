# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for BorderRemover.

Tests cover:
- Successful border removal on synthetic images
- Safety guardrail: crop < 70% area returns original
- No contours found returns original
- Grayscale input handling
- Convenience function
- Invalid input handling
"""

from __future__ import annotations

import numpy as np
import pytest

from image_preprocessing_detector.correction.border_removal import (
    BorderRemover,
    remove_borders,
)

# =============================================================================
# Synthetic test images
# =============================================================================


def _make_bordered_image(
    border_px: int = 20,
    doc_w: int = 460,
    doc_h: int = 660,
) -> np.ndarray:
    """Create a synthetic image with a white document on black background.

    The document region is white (255), surrounded by a narrow black border.
    Defaults yield ~87% area ratio which passes the 70% guardrail.
    """
    total_w = doc_w + 2 * border_px
    total_h = doc_h + 2 * border_px
    image = np.zeros((total_h, total_w, 3), dtype=np.uint8)

    # White document region
    image[border_px : border_px + doc_h, border_px : border_px + doc_w] = 255

    return image


def _make_uniform_image(value: int = 128, size: int = 500) -> np.ndarray:
    """Create a uniform-color image where Otsu may not separate regions."""
    return np.full((size, size, 3), value, dtype=np.uint8)


# =============================================================================
# Tests
# =============================================================================


class TestBorderRemover:
    """Core BorderRemover tests."""

    def test_removes_border_from_synthetic(self) -> None:
        """Clear black border around white document should be cropped."""
        image = _make_bordered_image(border_px=20, doc_w=460, doc_h=660)
        remover = BorderRemover()
        result = remover.correct(image)

        assert result.applied is True
        assert result.skipped_reason is None

        # Cropped image should be approximately doc_w x doc_h
        ch, cw = result.corrected_image.shape[:2]
        assert 440 <= cw <= 480
        assert 640 <= ch <= 680

    def test_area_ratio_recorded(self) -> None:
        """Parameters should contain area_ratio."""
        image = _make_bordered_image()
        remover = BorderRemover()
        result = remover.correct(image)
        assert "area_ratio" in result.parameters
        assert result.parameters["area_ratio"] > 0

    def test_guardrail_small_crop_rejected(self) -> None:
        """If crop area < 70% of original, return original unchanged."""
        # Create image where the "document" is only 20% of area
        image = np.zeros((1000, 1000, 3), dtype=np.uint8)
        # Small white region (200x200 = 4% of 1M)
        image[400:600, 400:600] = 255

        remover = BorderRemover(min_area_ratio=0.70)
        result = remover.correct(image)

        assert result.applied is False
        assert result.skipped_reason is not None
        assert "area ratio" in result.skipped_reason.lower()
        assert np.array_equal(result.corrected_image, image)

    def test_no_contours_returns_original(self) -> None:
        """Uniform image produces no useful contours."""
        # All black image - after Otsu, everything is same class
        image = np.zeros((500, 500, 3), dtype=np.uint8)
        remover = BorderRemover()
        result = remover.correct(image)

        assert result.applied is False
        assert np.array_equal(result.corrected_image, image)

    def test_grayscale_input(self) -> None:
        """Should handle grayscale (2D) input images."""
        # Use thin borders so area ratio stays above 70%
        gray = np.zeros((700, 500), dtype=np.uint8)
        gray[20:680, 20:480] = 255
        # Area ratio: 660*460 / (700*500) = 303600/350000 = 86.7%

        remover = BorderRemover()
        result = remover.correct(gray)

        assert result.applied is True
        ch, cw = result.corrected_image.shape[:2]
        assert cw < 500
        assert ch < 700

    def test_custom_min_area_ratio(self) -> None:
        """Custom min_area_ratio changes the guardrail threshold."""
        image = _make_bordered_image(border_px=200, doc_w=200, doc_h=200)
        # Total: 600x600, doc: 200x200 = 11% of area

        # Strict threshold -> rejected
        remover_strict = BorderRemover(min_area_ratio=0.50)
        result = remover_strict.correct(image)
        assert result.applied is False

        # Relaxed threshold -> accepted
        remover_relaxed = BorderRemover(min_area_ratio=0.05)
        result = remover_relaxed.correct(image)
        assert result.applied is True

    def test_invalid_image_raises(self) -> None:
        """None or empty image should raise ValueError."""
        remover = BorderRemover()
        with pytest.raises(ValueError, match="Invalid"):
            remover.correct(np.array([]))

    def test_none_image_raises(self) -> None:
        remover = BorderRemover()
        with pytest.raises(ValueError, match="Invalid"):
            remover.correct(None)  # type: ignore[arg-type]

    def test_crop_preserves_channels(self) -> None:
        """Cropped BGR image should still have 3 channels."""
        image = _make_bordered_image(border_px=30)
        remover = BorderRemover()
        result = remover.correct(image)
        if result.applied:
            assert len(result.corrected_image.shape) == 3
            assert result.corrected_image.shape[2] == 3


class TestRemoveBordersConvenience:
    """Convenience function tests."""

    def test_removes_border(self) -> None:
        image = _make_bordered_image()
        result = remove_borders(image)
        assert result.applied is True

    def test_custom_area_ratio(self) -> None:
        image = _make_bordered_image()
        result = remove_borders(image, min_area_ratio=0.99)
        # Default: 20px border, 460x660 doc, 500x700 total -> ~87% ratio
        # With 0.99 threshold this should fail
        assert result.applied is False
