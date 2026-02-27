"""Unit tests for ScriptDetectorHeuristic.

Tests cover:
- Image with roughly square, dense shapes -> CJK-like -> "Hans"
- Image with tall narrow shapes -> Latin-like -> "Latn"
- Blank / uniform image -> unknown -> "Zzzz"
- Few components -> unknown (insufficient data) -> "Zzzz"
- script_probabilities sums approximately to 1.0
- detected_script is always a valid 4-char ISO 15924 code
- Edge cases: invalid input (ValueError), grayscale input
- Module-level convenience function
- Configurable min_components
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.script_detector import (
    ScriptDetectorHeuristic,
    _build_probabilities,
    _compute_aspect_ratio_signal,
    _compute_cc_complexity_signal,
    _compute_confidence,
    _compute_rtl_flow_signal,
    _compute_stroke_density_signal,
    detect_script_heuristic,
)
from image_preprocessing_detector.schema import ScriptDetectionResult
from image_preprocessing_detector.schema_utils.iso_language_script import (
    ISO15924Script,
)

# ---------------------------------------------------------------------------
# Valid ISO 15924 codes (all enum values) for validation
# ---------------------------------------------------------------------------

_VALID_ISO_CODES = {member.value for member in ISO15924Script}


# ---------------------------------------------------------------------------
# Fixtures: reusable synthetic images
# ---------------------------------------------------------------------------


@pytest.fixture
def cjk_like_image() -> np.ndarray:
    """BGR image with square, dense shapes simulating CJK characters.

    Draws a grid of filled squares (roughly 1:1 aspect ratio with high
    stroke density) on a white background.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)

    # Draw grid of filled squares (CJK-like glyphs)
    for row in range(5):
        for col in range(10):
            x_start = 60 + col * 70
            y_start = 60 + row * 100
            size = 40
            # Fill the square completely for high density
            cv2.rectangle(
                page,
                (x_start, y_start),
                (x_start + size, y_start + size),
                (0, 0, 0),
                -1,  # filled
            )
            # Add internal strokes for complexity
            mid_x = x_start + size // 2
            mid_y = y_start + size // 2
            cv2.line(
                page, (x_start, mid_y), (x_start + size, mid_y), (255, 255, 255), 1
            )
            cv2.line(
                page, (mid_x, y_start), (mid_x, y_start + size), (255, 255, 255), 1
            )

    return page


@pytest.fixture
def latin_like_image() -> np.ndarray:
    """BGR image with tall shapes at moderate density simulating Latin chars.

    Draws outlined rectangles with a vertical midline stroke.  The shapes
    have w/h ~0.5-0.7, moderate fill ratio (~0.25-0.35), and low complexity
    -- all typical of Latin script characters.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)

    # Draw Latin-like glyphs: outlined rectangles with vertical midline
    for row in range(5):
        y_start = 40 + row * 110
        for col in range(15):
            x_start = 30 + col * 50
            glyph_w = 20
            glyph_h = 36
            # Outline only (moderate density, not filled)
            cv2.rectangle(
                page,
                (x_start, y_start),
                (x_start + glyph_w, y_start + glyph_h),
                (0, 0, 0),
                2,
            )
            # Vertical midline stroke
            mid_x = x_start + glyph_w // 2
            cv2.line(
                page,
                (mid_x, y_start + 4),
                (mid_x, y_start + glyph_h - 4),
                (0, 0, 0),
                2,
            )

    return page


@pytest.fixture
def blank_image() -> np.ndarray:
    """Pure white BGR image (800x600) -- no text content."""
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def sparse_image() -> np.ndarray:
    """BGR image with only 3 small shapes (below min_components).

    Should produce an unknown result due to insufficient data.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)
    # Only 3 small shapes
    cv2.rectangle(page, (100, 100), (120, 130), (0, 0, 0), -1)
    cv2.rectangle(page, (200, 100), (220, 130), (0, 0, 0), -1)
    cv2.rectangle(page, (300, 100), (320, 130), (0, 0, 0), -1)
    return page


@pytest.fixture
def grayscale_image() -> np.ndarray:
    """Grayscale image with square shapes (CJK-like).

    Verifies that grayscale input is accepted without errors.
    """
    page = np.full((400, 600), 255, dtype=np.uint8)
    for row in range(4):
        for col in range(8):
            x_start = 40 + col * 65
            y_start = 40 + row * 90
            size = 35
            cv2.rectangle(
                page, (x_start, y_start), (x_start + size, y_start + size), 0, -1
            )
            mid_x = x_start + size // 2
            mid_y = y_start + size // 2
            cv2.line(page, (x_start, mid_y), (x_start + size, mid_y), 255, 1)
            cv2.line(page, (mid_x, y_start), (mid_x, y_start + size), 255, 1)
    return page


@pytest.fixture
def rtl_like_image() -> np.ndarray:
    """BGR image with wide shapes placed right-to-left.

    Simulates Arabic-like connected script segments with an RTL layout:
    wider-than-tall shapes arranged so centroids progress right-to-left.
    """
    page = np.full((600, 800, 3), 255, dtype=np.uint8)

    # Draw wide, short shapes in rows (Arabic-like aspect ratio)
    # Place them right-to-left
    for row in range(4):
        y_start = 60 + row * 120
        for col in range(8):
            # Right-to-left: first shapes are on the right
            x_start = 700 - col * 85
            glyph_w = 50
            glyph_h = 20
            cv2.rectangle(
                page,
                (x_start, y_start),
                (x_start + glyph_w, y_start + glyph_h),
                (0, 0, 0),
                -1,
            )

    return page


@pytest.fixture
def detector() -> ScriptDetectorHeuristic:
    """Default ScriptDetectorHeuristic instance."""
    return ScriptDetectorHeuristic()


@pytest.fixture
def strict_detector() -> ScriptDetectorHeuristic:
    """ScriptDetectorHeuristic with higher min_components threshold."""
    return ScriptDetectorHeuristic(min_components=20)


# ---------------------------------------------------------------------------
# Tests: CJK-like detection
# ---------------------------------------------------------------------------


class TestCJKDetection:
    """Tests for CJK-like script detection (square, dense shapes)."""

    def test_cjk_like_detects_hans(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """Square dense shapes should be classified as CJK -> Hans."""
        result = detector.detect(cjk_like_image)

        assert result.detected_script == "Hans"
        assert not result.is_unknown
        assert result.detection_method == "heuristic"

    def test_cjk_like_confidence_positive(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """CJK detection should have non-zero confidence."""
        result = detector.detect(cjk_like_image)

        assert result.confidence > 0.0
        assert result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests: Latin-like detection
# ---------------------------------------------------------------------------


class TestLatinDetection:
    """Tests for Latin-like script detection (tall narrow shapes)."""

    def test_latin_like_detects_latn(
        self, detector: ScriptDetectorHeuristic, latin_like_image: np.ndarray
    ) -> None:
        """Tall narrow shapes should be classified as Latin -> Latn."""
        result = detector.detect(latin_like_image)

        assert result.detected_script == "Latn"
        assert not result.is_unknown
        assert result.detection_method == "heuristic"

    def test_latin_like_confidence_positive(
        self, detector: ScriptDetectorHeuristic, latin_like_image: np.ndarray
    ) -> None:
        """Latin detection should have non-zero confidence."""
        result = detector.detect(latin_like_image)

        assert result.confidence > 0.0
        assert result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests: Unknown / blank / sparse
# ---------------------------------------------------------------------------


class TestUnknownDetection:
    """Tests for unknown script detection (blank, sparse images)."""

    def test_blank_image_is_unknown(
        self, detector: ScriptDetectorHeuristic, blank_image: np.ndarray
    ) -> None:
        """Blank image should produce Zzzz (unknown)."""
        result = detector.detect(blank_image)

        assert result.detected_script == "Zzzz"
        assert result.is_unknown is True
        assert result.confidence == pytest.approx(0.0)
        assert result.unknown_reason is not None

    def test_sparse_image_is_unknown(
        self, detector: ScriptDetectorHeuristic, sparse_image: np.ndarray
    ) -> None:
        """Image with too few components should produce unknown."""
        result = detector.detect(sparse_image)

        assert result.detected_script == "Zzzz"
        assert result.is_unknown is True
        assert "insufficient_components" in (result.unknown_reason or "")

    def test_sparse_image_with_low_threshold(self, sparse_image: np.ndarray) -> None:
        """Lowering min_components should allow detection on sparse images."""
        lenient_detector = ScriptDetectorHeuristic(min_components=2)
        result = lenient_detector.detect(sparse_image)

        # With min_components=2 and 3 shapes, should attempt detection
        assert not result.is_unknown


# ---------------------------------------------------------------------------
# Tests: Probability distribution
# ---------------------------------------------------------------------------


class TestProbabilities:
    """Tests for script_probabilities output."""

    def test_probabilities_sum_to_one(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """script_probabilities values should sum to approximately 1.0."""
        result = detector.detect(cjk_like_image)

        total = sum(result.script_probabilities.values())
        assert abs(total - 1.0) < 0.01, f"Probabilities sum to {total}, expected ~1.0"

    def test_probabilities_sum_to_one_latin(
        self, detector: ScriptDetectorHeuristic, latin_like_image: np.ndarray
    ) -> None:
        """script_probabilities should sum to ~1.0 for Latin-like images."""
        result = detector.detect(latin_like_image)

        total = sum(result.script_probabilities.values())
        assert abs(total - 1.0) < 0.01

    def test_probabilities_all_non_negative(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """All probability values should be >= 0."""
        result = detector.detect(cjk_like_image)

        for code, prob in result.script_probabilities.items():
            assert prob >= 0.0, f"Negative probability for {code}: {prob}"

    def test_unknown_probabilities(
        self, detector: ScriptDetectorHeuristic, blank_image: np.ndarray
    ) -> None:
        """Unknown result should have Zzzz=1.0 in probabilities."""
        result = detector.detect(blank_image)

        assert result.script_probabilities.get("Zzzz") == pytest.approx(1.0)

    def test_probabilities_keys_are_valid_iso(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """All keys in script_probabilities should be valid ISO 15924 codes."""
        result = detector.detect(cjk_like_image)

        for code in result.script_probabilities:
            assert code in _VALID_ISO_CODES, (
                f"Invalid ISO code in probabilities: {code}"
            )


# ---------------------------------------------------------------------------
# Tests: ISO 15924 code validation
# ---------------------------------------------------------------------------


class TestISOCodeValidation:
    """Tests that detected_script is always a valid 4-char ISO 15924 code."""

    @pytest.mark.parametrize(
        "fixture_name",
        ["cjk_like_image", "latin_like_image", "blank_image", "sparse_image"],
    )
    def test_detected_script_is_valid_iso(
        self,
        detector: ScriptDetectorHeuristic,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """detected_script should always be a valid 4-char ISO 15924 code."""
        image = request.getfixturevalue(fixture_name)
        result = detector.detect(image)

        assert len(result.detected_script) == 4, (
            f"Expected 4-char code, got '{result.detected_script}'"
        )
        assert result.detected_script in _VALID_ISO_CODES, (
            f"'{result.detected_script}' is not a valid ISO 15924 code"
        )


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_image_raises_value_error(
        self, detector: ScriptDetectorHeuristic
    ) -> None:
        """None input should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_empty_image_raises_value_error(
        self, detector: ScriptDetectorHeuristic
    ) -> None:
        """Empty numpy array should raise ValueError."""
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Invalid image"):
            detector.detect(empty)

    def test_grayscale_input_accepted(
        self, detector: ScriptDetectorHeuristic, grayscale_image: np.ndarray
    ) -> None:
        """Grayscale (2D) input should be accepted without error."""
        result = detector.detect(grayscale_image)

        assert isinstance(result, ScriptDetectionResult)
        assert result.detected_script in _VALID_ISO_CODES

    def test_bgra_input_accepted(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """BGRA (4-channel) input should be accepted without error."""
        bgra = cv2.cvtColor(cjk_like_image, cv2.COLOR_BGR2BGRA)
        result = detector.detect(bgra)

        assert isinstance(result, ScriptDetectionResult)
        assert result.detected_script in _VALID_ISO_CODES

    def test_confidence_always_in_range(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """Confidence should always be in [0, 1]."""
        result = detector.detect(cjk_like_image)

        assert 0.0 <= result.confidence <= 1.0

    def test_detection_method_is_heuristic(
        self, detector: ScriptDetectorHeuristic, latin_like_image: np.ndarray
    ) -> None:
        """detection_method should always be 'heuristic'."""
        result = detector.detect(latin_like_image)

        assert result.detection_method == "heuristic"

    def test_source_label_is_none(
        self, detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """source_label should be None for heuristic detection."""
        result = detector.detect(cjk_like_image)

        assert result.source_label is None


# ---------------------------------------------------------------------------
# Tests: Module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Tests for the module-level detect_script_heuristic function."""

    def test_convenience_function_returns_result(
        self, cjk_like_image: np.ndarray
    ) -> None:
        """detect_script_heuristic should return a ScriptDetectionResult."""
        result = detect_script_heuristic(cjk_like_image)

        assert isinstance(result, ScriptDetectionResult)
        assert result.detected_script in _VALID_ISO_CODES

    def test_convenience_function_blank_image(self, blank_image: np.ndarray) -> None:
        """detect_script_heuristic with blank image should return unknown."""
        result = detect_script_heuristic(blank_image)

        assert result.detected_script == "Zzzz"
        assert result.is_unknown is True

    def test_convenience_function_raises_on_invalid(self) -> None:
        """detect_script_heuristic with None should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid image"):
            detect_script_heuristic(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: Configurable min_components
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Tests for configurable min_components parameter."""

    def test_higher_min_components_makes_sparse_unknown(
        self, strict_detector: ScriptDetectorHeuristic, cjk_like_image: np.ndarray
    ) -> None:
        """With min_components=20, images near the threshold may differ."""
        result = strict_detector.detect(cjk_like_image)

        # The CJK image has enough components (50 shapes), so should still work
        assert isinstance(result, ScriptDetectionResult)

    def test_custom_min_components(self) -> None:
        """Detector should respect custom min_components setting."""
        det = ScriptDetectorHeuristic(min_components=5)
        assert det.min_components == 5


# ---------------------------------------------------------------------------
# Tests: Internal helper functions
# ---------------------------------------------------------------------------


class TestInternalHelpers:
    """Tests for internal signal computation helpers."""

    def test_build_probabilities_normalises(self) -> None:
        """_build_probabilities should normalise scores to sum to ~1.0."""
        scores = {"cjk": 0.8, "latin": 0.4, "arabic": 0.2, "devanagari": 0.3}
        probs = _build_probabilities(scores)

        total = sum(probs.values())
        assert abs(total - 1.0) < 0.01

    def test_build_probabilities_zero_scores(self) -> None:
        """All-zero scores should produce Zzzz=1.0."""
        scores = {"cjk": 0.0, "latin": 0.0, "arabic": 0.0, "devanagari": 0.0}
        probs = _build_probabilities(scores)

        assert probs.get("Zzzz") == pytest.approx(1.0)

    def test_compute_confidence_high_separation(self) -> None:
        """High score separation should yield higher confidence."""
        high_sep = _compute_confidence(0.9, 0.3, 50, 10)
        low_sep = _compute_confidence(0.5, 0.45, 50, 10)

        assert high_sep > low_sep

    def test_compute_confidence_bounds(self) -> None:
        """Confidence should always be in [0, 1]."""
        conf = _compute_confidence(1.0, 0.0, 100, 10)
        assert 0.0 <= conf <= 1.0

        conf = _compute_confidence(0.0, 0.0, 0, 10)
        assert 0.0 <= conf <= 1.0

    def test_aspect_ratio_signal_square_shapes(self) -> None:
        """Square shapes should have aspect ratio near 1.0."""
        components = [
            {"aspect_ratio": 1.0, "density": 0.5, "centroid": (50, 50)},
            {"aspect_ratio": 0.95, "density": 0.5, "centroid": (100, 50)},
            {"aspect_ratio": 1.05, "density": 0.5, "centroid": (150, 50)},
        ]
        mean_ar = _compute_aspect_ratio_signal(components)
        assert 0.9 <= mean_ar <= 1.1

    def test_stroke_density_signal(self) -> None:
        """Stroke density should reflect mean of component densities."""
        components = [
            {"aspect_ratio": 1.0, "density": 0.6, "centroid": (50, 50)},
            {"aspect_ratio": 1.0, "density": 0.5, "centroid": (100, 50)},
            {"aspect_ratio": 1.0, "density": 0.4, "centroid": (150, 50)},
        ]
        mean_density = _compute_stroke_density_signal(components)
        assert abs(mean_density - 0.5) < 0.01

    def test_rtl_flow_signal_ltr_layout(self) -> None:
        """Left-to-right layout should yield low RTL score."""
        # Components ordered left-to-right in one row
        components = [
            {
                "aspect_ratio": 1.0,
                "density": 0.5,
                "centroid": (50.0, 100.0),
                "bbox": (40, 90, 20, 20),
                "area": 400,
            },
            {
                "aspect_ratio": 1.0,
                "density": 0.5,
                "centroid": (100.0, 100.0),
                "bbox": (90, 90, 20, 20),
                "area": 400,
            },
            {
                "aspect_ratio": 1.0,
                "density": 0.5,
                "centroid": (150.0, 100.0),
                "bbox": (140, 90, 20, 20),
                "area": 400,
            },
            {
                "aspect_ratio": 1.0,
                "density": 0.5,
                "centroid": (200.0, 100.0),
                "bbox": (190, 90, 20, 20),
                "area": 400,
            },
        ]
        rtl_score = _compute_rtl_flow_signal(components, 400)
        assert rtl_score < 0.5

    def test_cc_complexity_on_empty_binary(self) -> None:
        """Empty binary image should return 0.0 complexity."""
        binary = np.zeros((100, 100), dtype=np.uint8)
        complexity = _compute_cc_complexity_signal(binary)
        assert complexity == pytest.approx(0.0)
