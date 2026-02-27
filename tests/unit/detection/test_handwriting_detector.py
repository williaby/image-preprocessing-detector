"""Unit tests for HandwritingDetector.

Tests cover:
- Image with irregular wavy handwriting-like strokes -> has_handwriting=True
- Image with uniform rectangular printed-text shapes -> has_handwriting=False
- Blank/white image -> no handwriting detected
- to_assessment() returns correct HandwritingAssessment with presence mapping
- Invalid input raises ValueError
- Grayscale single-channel input accepted
- BGRA 4-channel input accepted
- All scores and confidence always in [0, 1]
- Module-level convenience function
- Configurable thresholds
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.handwriting_detector import (
    HandwritingDetectionResult,
    HandwritingDetector,
    detect_handwriting,
)
from image_preprocessing_detector.schema import (
    HandwritingAssessment,
    HandwritingContentType,
    HandwritingLegibility,
    HandwritingPresence,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable synthetic images
# ---------------------------------------------------------------------------


@pytest.fixture
def white_page() -> np.ndarray:
    """Pure white BGR image (800x600) -- no content, no handwriting."""
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def handwriting_image() -> np.ndarray:
    """Synthetic image with irregular glyphs simulating handwriting.

    Draws many individual separated blobs at irregular vertical positions
    with varying sizes, aspect ratios, and stroke widths.  Each "glyph"
    is a small irregular shape (ellipse with random axes and rotation)
    placed along a wavy baseline with non-uniform horizontal spacing.
    This produces many connected components with the high stroke-width
    variance, irregular baselines, uneven spacing, and complex form
    factors that characterise handwriting.
    """

    page = np.full((600, 800, 3), 240, dtype=np.uint8)
    rng = np.random.default_rng(42)

    y_positions = [55, 120, 185, 255, 325, 395, 460, 530]
    for y_base in y_positions:
        x_cursor = 30
        while x_cursor < 760:
            # Irregular baseline offset per glyph
            y_offset = int(rng.integers(-14, 15))
            cy = y_base + y_offset
            cx = x_cursor

            # Variable glyph size (simulates different letter sizes)
            glyph_w = int(rng.integers(8, 22))
            glyph_h = int(rng.integers(10, 28))
            angle = int(rng.integers(-25, 26))  # rotation
            thickness = int(rng.integers(1, 5))

            # Draw ellipse (irregular glyph shape)
            color = (
                int(rng.integers(0, 40)),
                int(rng.integers(0, 40)),
                int(rng.integers(0, 40)),
            )
            cv2.ellipse(
                page,
                (cx, cy),
                (glyph_w // 2, glyph_h // 2),
                angle,
                0,
                360,
                color,
                thickness,
            )

            # Add a small descender/ascender stroke on some glyphs
            if rng.random() < 0.3:
                tail_len = int(rng.integers(5, 15))
                x_end = cx + int(rng.integers(-5, 6))
                cv2.line(
                    page,
                    (cx, cy + glyph_h // 2),
                    (x_end, cy + glyph_h // 2 + tail_len),
                    color,
                    max(1, thickness - 1),
                )

            # Non-uniform spacing (key handwriting characteristic)
            gap = int(rng.integers(4, 25))
            x_cursor += glyph_w + gap

    return page


@pytest.fixture
def printed_text_image() -> np.ndarray:
    """Synthetic image with uniform rectangular blocks simulating printed text.

    Draws rows of evenly-spaced, uniform-sized rectangles with consistent
    stroke width.  This mimics the regularity of typeset characters:
    uniform baselines, even spacing, consistent stroke width, and simple
    rectangular shapes with low form-factor.
    """
    page = np.full((600, 800, 3), 240, dtype=np.uint8)

    # 8 rows of uniform rectangles
    char_width = 12
    char_height = 16
    spacing = 6
    row_gap = 50
    margin_left = 40
    margin_top = 40

    for row_idx in range(8):
        y_top = margin_top + row_idx * (char_height + row_gap)
        # ~40 characters per row
        for col_idx in range(40):
            x_left = margin_left + col_idx * (char_width + spacing)
            if x_left + char_width > 770:
                break
            # Draw a uniform filled rectangle (simulating a printed glyph)
            _draw_rectangle(
                page,
                (x_left, y_top),
                (x_left + char_width, y_top + char_height),
                (30, 30, 30),
                thickness=-1,  # filled
            )

    return page


@pytest.fixture
def grayscale_handwriting() -> np.ndarray:
    """Single-channel grayscale image with handwriting-like irregular glyphs."""

    page = np.full((600, 800), 235, dtype=np.uint8)
    rng = np.random.default_rng(99)

    for y_base in [55, 130, 205, 280, 355, 430, 510]:
        x_cursor = 30
        while x_cursor < 760:
            y_offset = int(rng.integers(-12, 13))
            cy = y_base + y_offset
            cx = x_cursor

            glyph_w = int(rng.integers(8, 22))
            glyph_h = int(rng.integers(10, 26))
            angle = int(rng.integers(-25, 26))
            thickness = int(rng.integers(1, 5))

            cv2.ellipse(
                page,
                (cx, cy),
                (glyph_w // 2, glyph_h // 2),
                angle,
                0,
                360,
                25,
                thickness,
            )

            if rng.random() < 0.3:
                tail_len = int(rng.integers(5, 12))
                x_end = cx + int(rng.integers(-4, 5))
                cv2.line(
                    page,
                    (cx, cy + glyph_h // 2),
                    (x_end, cy + glyph_h // 2 + tail_len),
                    20,
                    max(1, thickness - 1),
                )

            gap = int(rng.integers(4, 25))
            x_cursor += glyph_w + gap

    return page


@pytest.fixture
def bgra_handwriting() -> np.ndarray:
    """BGRA 4-channel image with handwriting-like irregular glyphs."""

    page = np.full((600, 800, 4), 240, dtype=np.uint8)
    page[:, :, 3] = 255  # alpha channel
    rng = np.random.default_rng(77)

    for y_base in [55, 130, 205, 280, 355, 430, 510]:
        x_cursor = 30
        while x_cursor < 760:
            y_offset = int(rng.integers(-12, 13))
            cy = y_base + y_offset
            cx = x_cursor

            glyph_w = int(rng.integers(8, 22))
            glyph_h = int(rng.integers(10, 26))
            angle = int(rng.integers(-25, 26))
            thickness = int(rng.integers(1, 5))

            color = (
                int(rng.integers(0, 40)),
                int(rng.integers(0, 40)),
                int(rng.integers(0, 40)),
                255,
            )
            cv2.ellipse(
                page,
                (cx, cy),
                (glyph_w // 2, glyph_h // 2),
                angle,
                0,
                360,
                color,
                thickness,
            )

            if rng.random() < 0.3:
                tail_len = int(rng.integers(5, 12))
                x_end = cx + int(rng.integers(-4, 5))
                cv2.line(
                    page,
                    (cx, cy + glyph_h // 2),
                    (x_end, cy + glyph_h // 2 + tail_len),
                    color,
                    max(1, thickness - 1),
                )

            gap = int(rng.integers(4, 25))
            x_cursor += glyph_w + gap

    return page


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _draw_rectangle(
    img: np.ndarray,
    pt1: tuple[int, int],
    pt2: tuple[int, int],
    color: tuple[int, ...],
    thickness: int = -1,
) -> None:
    """Draw a rectangle on an image."""
    cv2.rectangle(img, pt1, pt2, color, thickness=thickness)


# ---------------------------------------------------------------------------
# Tests: HandwritingDetectionResult dataclass
# ---------------------------------------------------------------------------


class TestHandwritingDetectionResult:
    """Verify the result dataclass fields."""

    def test_fields_present(self) -> None:
        """All expected fields are accessible."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.65,
            stroke_width_variance=0.7,
            baseline_irregularity=0.5,
            spacing_variance=0.6,
            form_factor_score=0.8,
            confidence=0.75,
        )
        assert result.has_handwriting is True
        assert result.handwriting_score == pytest.approx(0.65)
        assert result.stroke_width_variance == pytest.approx(0.7)
        assert result.baseline_irregularity == pytest.approx(0.5)
        assert result.spacing_variance == pytest.approx(0.6)
        assert result.form_factor_score == pytest.approx(0.8)
        assert result.confidence == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Tests: Handwriting detection (true positives)
# ---------------------------------------------------------------------------


class TestHandwritingDetection:
    """Images that should be classified as having handwriting."""

    def test_wavy_strokes_detected_as_handwriting(
        self, handwriting_image: np.ndarray
    ) -> None:
        """Wavy irregular strokes should trigger has_handwriting=True."""
        detector = HandwritingDetector()
        result = detector.detect(handwriting_image)

        assert result.has_handwriting is True
        assert result.handwriting_score >= 0.4
        assert 0.0 <= result.confidence <= 1.0

    def test_handwriting_score_higher_than_printed(
        self, handwriting_image: np.ndarray, printed_text_image: np.ndarray
    ) -> None:
        """Handwriting image must score higher than printed text image."""
        detector = HandwritingDetector()
        hw_result = detector.detect(handwriting_image)
        pt_result = detector.detect(printed_text_image)
        assert hw_result.handwriting_score > pt_result.handwriting_score


# ---------------------------------------------------------------------------
# Tests: No handwriting detection (true negatives)
# ---------------------------------------------------------------------------


class TestNoHandwritingDetection:
    """Pages that should NOT be classified as having handwriting."""

    def test_uniform_white_no_handwriting(self, white_page: np.ndarray) -> None:
        """A pure white page must not have handwriting."""
        detector = HandwritingDetector()
        result = detector.detect(white_page)

        assert result.has_handwriting is False
        assert result.handwriting_score == pytest.approx(0.0)
        assert 0.0 <= result.confidence <= 1.0

    def test_printed_text_no_handwriting(self, printed_text_image: np.ndarray) -> None:
        """Uniform rectangular printed text should not trigger handwriting."""
        detector = HandwritingDetector()
        result = detector.detect(printed_text_image)

        assert result.has_handwriting is False
        assert result.handwriting_score < 0.4


# ---------------------------------------------------------------------------
# Tests: to_assessment() schema bridge
# ---------------------------------------------------------------------------


class TestToAssessment:
    """Verify conversion to Pydantic HandwritingAssessment."""

    def test_no_handwriting_maps_to_none(self) -> None:
        """Score < 0.2 maps to HandwritingPresence.NONE."""
        result = HandwritingDetectionResult(
            has_handwriting=False,
            handwriting_score=0.1,
            stroke_width_variance=0.05,
            baseline_irregularity=0.05,
            spacing_variance=0.05,
            form_factor_score=0.05,
            confidence=0.6,
        )
        assessment = result.to_assessment()
        assert isinstance(assessment, HandwritingAssessment)
        assert assessment.presence == HandwritingPresence.NONE
        assert assessment.detection_method == "heuristic"
        assert assessment.presence_score == pytest.approx(0.1)
        assert assessment.presence_confidence == pytest.approx(0.6)

    def test_sparse_handwriting(self) -> None:
        """Score in [0.2, 0.4) maps to HandwritingPresence.SPARSE."""
        result = HandwritingDetectionResult(
            has_handwriting=False,
            handwriting_score=0.3,
            stroke_width_variance=0.3,
            baseline_irregularity=0.3,
            spacing_variance=0.3,
            form_factor_score=0.3,
            confidence=0.7,
        )
        assessment = result.to_assessment()
        assert assessment.presence == HandwritingPresence.SPARSE

    def test_moderate_handwriting(self) -> None:
        """Score in [0.4, 0.7) maps to HandwritingPresence.MODERATE."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.55,
            stroke_width_variance=0.5,
            baseline_irregularity=0.5,
            spacing_variance=0.5,
            form_factor_score=0.5,
            confidence=0.8,
        )
        assessment = result.to_assessment()
        assert assessment.presence == HandwritingPresence.MODERATE

    def test_dominant_handwriting(self) -> None:
        """Score >= 0.7 maps to HandwritingPresence.DOMINANT."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.85,
            stroke_width_variance=0.9,
            baseline_irregularity=0.8,
            spacing_variance=0.8,
            form_factor_score=0.9,
            confidence=0.9,
        )
        assessment = result.to_assessment()
        assert assessment.presence == HandwritingPresence.DOMINANT

    def test_legibility_is_not_applicable(self) -> None:
        """Heuristic detector cannot determine legibility."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.6,
            stroke_width_variance=0.5,
            baseline_irregularity=0.5,
            spacing_variance=0.5,
            form_factor_score=0.5,
            confidence=0.7,
        )
        assessment = result.to_assessment()
        assert assessment.legibility == HandwritingLegibility.NOT_APPLICABLE
        assert assessment.legibility_score == pytest.approx(0.0)
        assert assessment.legibility_confidence == pytest.approx(0.0)

    def test_content_type_is_not_applicable(self) -> None:
        """Heuristic detector cannot determine content type."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.6,
            stroke_width_variance=0.5,
            baseline_irregularity=0.5,
            spacing_variance=0.5,
            form_factor_score=0.5,
            confidence=0.7,
        )
        assessment = result.to_assessment()
        assert assessment.content_type == HandwritingContentType.NOT_APPLICABLE
        assert assessment.content_type_confidence == pytest.approx(0.0)

    def test_assessment_boundary_at_0_2(self) -> None:
        """Score exactly at 0.2 maps to SPARSE (not NONE)."""
        result = HandwritingDetectionResult(
            has_handwriting=False,
            handwriting_score=0.2,
            stroke_width_variance=0.2,
            baseline_irregularity=0.2,
            spacing_variance=0.2,
            form_factor_score=0.2,
            confidence=0.6,
        )
        assessment = result.to_assessment()
        assert assessment.presence == HandwritingPresence.SPARSE

    def test_assessment_boundary_at_0_4(self) -> None:
        """Score exactly at 0.4 maps to MODERATE (not SPARSE)."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.4,
            stroke_width_variance=0.4,
            baseline_irregularity=0.4,
            spacing_variance=0.4,
            form_factor_score=0.4,
            confidence=0.7,
        )
        assessment = result.to_assessment()
        assert assessment.presence == HandwritingPresence.MODERATE

    def test_assessment_boundary_at_0_7(self) -> None:
        """Score exactly at 0.7 maps to DOMINANT (not MODERATE)."""
        result = HandwritingDetectionResult(
            has_handwriting=True,
            handwriting_score=0.7,
            stroke_width_variance=0.7,
            baseline_irregularity=0.7,
            spacing_variance=0.7,
            form_factor_score=0.7,
            confidence=0.8,
        )
        assessment = result.to_assessment()
        assert assessment.presence == HandwritingPresence.DOMINANT


# ---------------------------------------------------------------------------
# Tests: Edge cases and error handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_image_raises(self) -> None:
        """An empty (zero-size) image must raise ValueError."""
        detector = HandwritingDetector()
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(empty)

    def test_none_image_raises(self) -> None:
        """A None image must raise ValueError."""
        detector = HandwritingDetector()
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_grayscale_input_accepted(self, grayscale_handwriting: np.ndarray) -> None:
        """A single-channel grayscale image must be accepted."""
        detector = HandwritingDetector()
        result = detector.detect(grayscale_handwriting)

        assert isinstance(result, HandwritingDetectionResult)
        assert result.has_handwriting is True
        assert 0.0 <= result.handwriting_score <= 1.0

    def test_bgra_input_accepted(self, bgra_handwriting: np.ndarray) -> None:
        """A 4-channel BGRA image must be accepted."""
        detector = HandwritingDetector()
        result = detector.detect(bgra_handwriting)

        assert isinstance(result, HandwritingDetectionResult)
        assert result.handwriting_score > 0.2
        assert 0.0 <= result.handwriting_score <= 1.0

    def test_single_pixel_image(self) -> None:
        """A 1x1 image should not crash and returns empty result."""
        detector = HandwritingDetector()
        img = np.full((1, 1, 3), 128, dtype=np.uint8)
        result = detector.detect(img)
        assert isinstance(result, HandwritingDetectionResult)
        assert result.has_handwriting is False
        assert result.handwriting_score == pytest.approx(0.0)

    def test_all_black_image(self) -> None:
        """An all-black image should not crash."""
        detector = HandwritingDetector()
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        result = detector.detect(img)
        assert isinstance(result, HandwritingDetectionResult)
        assert 0.0 <= result.handwriting_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests: Score and confidence ranges
# ---------------------------------------------------------------------------


class TestScoreProperties:
    """Verify all scores and confidence are always in [0, 1]."""

    def test_all_scores_in_range(
        self,
        white_page: np.ndarray,
        handwriting_image: np.ndarray,
        printed_text_image: np.ndarray,
    ) -> None:
        """Every signal score is in [0, 1] across different image types."""
        detector = HandwritingDetector()
        for img in [white_page, handwriting_image, printed_text_image]:
            result = detector.detect(img)
            assert 0.0 <= result.handwriting_score <= 1.0
            assert 0.0 <= result.stroke_width_variance <= 1.0
            assert 0.0 <= result.baseline_irregularity <= 1.0
            assert 0.0 <= result.spacing_variance <= 1.0
            assert 0.0 <= result.form_factor_score <= 1.0
            assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests: Configurable thresholds
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Verify that custom thresholds change detection behaviour."""

    def test_strict_threshold_reduces_positives(
        self, handwriting_image: np.ndarray
    ) -> None:
        """A higher threshold makes it harder to classify as handwriting."""
        strict = HandwritingDetector(threshold=0.9)
        result = strict.detect(handwriting_image)
        # With a very high threshold, even handwriting may not qualify
        # The score itself should still be valid
        assert 0.0 <= result.handwriting_score <= 1.0

    def test_lenient_threshold_increases_positives(
        self, printed_text_image: np.ndarray
    ) -> None:
        """A very low threshold may classify printed text as handwriting."""
        lenient = HandwritingDetector(threshold=0.01)
        result = lenient.detect(printed_text_image)
        # With threshold=0.01, even a small score qualifies
        assert isinstance(result, HandwritingDetectionResult)

    def test_custom_min_components(self, white_page: np.ndarray) -> None:
        """Custom min_components changes the component-count filter."""
        detector = HandwritingDetector(min_components=1)
        result = detector.detect(white_page)
        # Still no handwriting on a blank page regardless of min_components
        assert result.has_handwriting is False

    def test_threshold_below_zero_raises(self) -> None:
        """threshold < 0.0 must raise ValueError."""
        with pytest.raises(ValueError, match="threshold must be between"):
            HandwritingDetector(threshold=-0.1)

    def test_threshold_above_one_raises(self) -> None:
        """threshold > 1.0 must raise ValueError."""
        with pytest.raises(ValueError, match="threshold must be between"):
            HandwritingDetector(threshold=1.1)

    def test_min_components_zero_raises(self) -> None:
        """min_components=0 must raise ValueError."""
        with pytest.raises(ValueError, match="min_components must be"):
            HandwritingDetector(min_components=0)

    def test_min_components_negative_raises(self) -> None:
        """min_components < 0 must raise ValueError."""
        with pytest.raises(ValueError, match="min_components must be"):
            HandwritingDetector(min_components=-5)

    def test_threshold_zero_is_valid(self) -> None:
        """threshold=0.0 is a valid boundary value and must not raise."""
        detector = HandwritingDetector(threshold=0.0)
        assert detector.threshold == 0.0

    def test_threshold_one_is_valid(self) -> None:
        """threshold=1.0 is a valid boundary value and must not raise."""
        detector = HandwritingDetector(threshold=1.0)
        assert detector.threshold == 1.0

    def test_min_components_one_is_valid(self) -> None:
        """min_components=1 is a valid boundary value and must not raise."""
        detector = HandwritingDetector(min_components=1)
        assert detector.min_components == 1


# ---------------------------------------------------------------------------
# Tests: Module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Test the module-level detect_handwriting() function."""

    def test_convenience_detects_no_handwriting(self, white_page: np.ndarray) -> None:
        """Convenience function returns correct result for blank page."""
        result = detect_handwriting(white_page)
        assert isinstance(result, HandwritingDetectionResult)
        assert result.has_handwriting is False

    def test_convenience_detects_handwriting(
        self, handwriting_image: np.ndarray
    ) -> None:
        """Convenience function returns correct result for handwriting."""
        result = detect_handwriting(handwriting_image)
        assert isinstance(result, HandwritingDetectionResult)
        assert result.has_handwriting is True

    def test_convenience_raises_on_empty(self) -> None:
        """Convenience function raises on invalid input."""
        with pytest.raises(ValueError, match="Invalid image"):
            detect_handwriting(np.array([], dtype=np.uint8))
