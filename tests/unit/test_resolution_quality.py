"""Unit tests for resolution quality measurement module.

Tests for:
- Piecewise quality score mapping (boundary and interior values)
- Coarse bucket classification
- Connected component character height measurement (Stage 2)
- Confidence computation
- Measurement aggregation (weighted median, range, flagging)
- Polygon line height extraction
- Polygon region cropping and masking
- ResolutionQualityResult serialization
"""

from __future__ import annotations

from typing import ClassVar

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.schema_utils.resolution_quality import (
    BUCKET_THRESHOLDS,
    CoarseBucket,
    ResolutionQualityResult,
    aggregate_measurements,
    classify_coarse_bucket,
    compute_confidence,
    crop_polygon_region,
    extract_line_height_from_polygon,
    measure_char_height_in_region,
    piecewise_quality_score,
)

# ---------------------------------------------------------------------------
# Piecewise Quality Score
# ---------------------------------------------------------------------------


class TestPiecewiseQualityScore:
    """Test the piecewise linear mapping from char height to quality score."""

    def test_negative_height_returns_zero(self) -> None:
        """Negative pixel heights should clamp to 0."""
        assert piecewise_quality_score(-5.0) == pytest.approx(0.0)
        assert piecewise_quality_score(-0.1) == pytest.approx(0.0)

    def test_zero_height_returns_zero(self) -> None:
        """Zero height maps to 0."""
        assert piecewise_quality_score(0.0) == pytest.approx(0.0)

    def test_boundary_at_16px(self) -> None:
        """At 16px, score should be 0.15 (top of needs_major_upscale)."""
        score = piecewise_quality_score(16.0)
        assert score == pytest.approx(0.15, abs=1e-6)

    def test_boundary_at_24px(self) -> None:
        """At 24px, score should be 0.35."""
        score = piecewise_quality_score(24.0)
        assert score == pytest.approx(0.35, abs=1e-6)

    def test_boundary_at_32px(self) -> None:
        """At 32px, score should be 0.55 (start of optimal)."""
        score = piecewise_quality_score(32.0)
        assert score == pytest.approx(0.55, abs=1e-6)

    def test_boundary_at_48px(self) -> None:
        """At 48px, score should be 0.75 (end of optimal)."""
        score = piecewise_quality_score(48.0)
        assert score == pytest.approx(0.75, abs=1e-6)

    def test_boundary_at_64px(self) -> None:
        """At 64px, score should be 0.85."""
        score = piecewise_quality_score(64.0)
        assert score == pytest.approx(0.85, abs=1e-6)

    def test_boundary_at_96px(self) -> None:
        """At 96px, score should be 0.95 (start of oversized)."""
        score = piecewise_quality_score(96.0)
        assert score == pytest.approx(0.95, abs=1e-6)

    def test_optimal_range_midpoint(self) -> None:
        """38.5px is mid-optimal, score should be ~0.63."""
        score = piecewise_quality_score(38.5)
        assert 0.55 < score < 0.75

    def test_monotonically_increasing(self) -> None:
        """Score must increase monotonically with char height."""
        heights = [0, 5, 10, 16, 20, 24, 30, 32, 40, 48, 56, 64, 80, 96, 120, 200]
        scores = [piecewise_quality_score(h) for h in heights]
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1], (
                f"Score at {heights[i]}px ({scores[i]}) < score at "
                f"{heights[i - 1]}px ({scores[i - 1]})"
            )

    def test_score_never_exceeds_one(self) -> None:
        """Score should never exceed 1.0 even for very large heights."""
        assert piecewise_quality_score(500.0) <= 1.0
        assert piecewise_quality_score(10000.0) <= 1.0

    def test_score_always_non_negative(self) -> None:
        """Score should never be negative."""
        for height in [-100, -1, 0, 0.1, 1, 8, 16, 32, 48, 96, 200]:
            assert piecewise_quality_score(height) >= 0.0

    def test_interpolation_within_segment(self) -> None:
        """Score at midpoint of a segment should be midway between boundaries."""
        # Midpoint of 0-16 segment: 8px -> score = 8/16 * 0.15 = 0.075
        assert piecewise_quality_score(8.0) == pytest.approx(0.075, abs=1e-6)

    def test_continuity_at_boundaries(self) -> None:
        """Score should be continuous across piecewise boundaries."""
        boundaries = [16, 24, 32, 48, 64, 96]
        for boundary in boundaries:
            below = piecewise_quality_score(boundary - 0.001)
            at_boundary = piecewise_quality_score(float(boundary))
            assert abs(below - at_boundary) < 0.001, (
                f"Discontinuity at {boundary}px: {below} vs {at_boundary}"
            )


# ---------------------------------------------------------------------------
# Coarse Bucket Classification
# ---------------------------------------------------------------------------


class TestClassifyCoarseBucket:
    """Test coarse bucket classification."""

    BUCKET_CASES: ClassVar[list[tuple[float, str]]] = [
        (0.0, "needs_major_upscale"),
        (8.0, "needs_major_upscale"),
        (15.9, "needs_major_upscale"),
        (16.0, "needs_light_upscale"),
        (24.0, "needs_light_upscale"),
        (31.9, "needs_light_upscale"),
        (32.0, "optimal"),
        (40.0, "optimal"),
        (47.9, "optimal"),
        (48.0, "good"),
        (72.0, "good"),
        (95.9, "good"),
        (96.0, "oversized"),
        (200.0, "oversized"),
    ]

    @pytest.mark.parametrize(("height", "expected"), BUCKET_CASES)
    def test_bucket_classification(self, height: float, expected: str) -> None:
        """Each height maps to the correct coarse bucket."""
        assert classify_coarse_bucket(height) == expected

    def test_all_bucket_values_are_valid_enum_values(self) -> None:
        """All bucket thresholds use valid CoarseBucket enum members."""
        for bucket in BUCKET_THRESHOLDS:
            assert isinstance(bucket, CoarseBucket)

    def test_bucket_thresholds_are_contiguous(self) -> None:
        """Bucket ranges cover 0 to infinity without gaps."""
        boundaries = sorted((low, high) for low, high in BUCKET_THRESHOLDS.values())
        assert boundaries[0][0] == pytest.approx(0.0)
        for i in range(1, len(boundaries)):
            assert boundaries[i][0] == boundaries[i - 1][1], (
                f"Gap between {boundaries[i - 1]} and {boundaries[i]}"
            )


# ---------------------------------------------------------------------------
# Confidence Computation
# ---------------------------------------------------------------------------


class TestComputeConfidence:
    """Test measurement confidence formula."""

    def test_perfect_conditions(self) -> None:
        """10+ regions, zero CV, stage_1_2 -> confidence = 1.0."""
        conf = compute_confidence(
            num_text_regions=15,
            _num_valid_cc_regions=15,
            height_cv=0.0,
            method="stage_1_2",
        )
        assert conf == pytest.approx(1.0, abs=1e-4)

    def test_stage_1_only_penalty(self) -> None:
        """stage_1_only reduces confidence by 0.8 factor."""
        conf_12 = compute_confidence(10, 10, 0.0, "stage_1_2")
        conf_1 = compute_confidence(10, 0, 0.0, "stage_1_only")
        assert conf_1 == pytest.approx(conf_12 * 0.8, abs=1e-4)

    def test_few_regions_reduces_confidence(self) -> None:
        """Fewer than 10 regions scales down region_factor."""
        conf = compute_confidence(5, 5, 0.0, "stage_1_2")
        assert conf == pytest.approx(0.5, abs=1e-4)

    def test_high_cv_reduces_confidence(self) -> None:
        """High coefficient of variation reduces uniformity_factor."""
        conf = compute_confidence(10, 10, 0.5, "stage_1_2")
        assert conf == pytest.approx(0.5, abs=1e-4)

    def test_zero_regions(self) -> None:
        """Zero regions -> confidence = 0."""
        conf = compute_confidence(0, 0, 0.0, "stage_1_2")
        assert conf == pytest.approx(0.0, abs=1e-4)

    def test_cv_greater_than_one_clamps(self) -> None:
        """CV > 1.0 should clamp uniformity_factor to 0."""
        conf = compute_confidence(10, 10, 1.5, "stage_1_2")
        assert conf == pytest.approx(0.0, abs=1e-4)

    def test_confidence_bounded_zero_one(self) -> None:
        """Confidence should always be in [0, 1]."""
        for regions in [0, 1, 5, 10, 50]:
            for cv_val in [0.0, 0.3, 0.7, 1.0, 2.0]:
                for method in ["stage_1_2", "stage_1_only"]:
                    conf = compute_confidence(regions, regions, cv_val, method)
                    assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# Aggregate Measurements
# ---------------------------------------------------------------------------


class TestAggregateMeasurements:
    """Test image-level measurement aggregation."""

    def test_empty_input_returns_flagged_result(self) -> None:
        """No regions -> flagged, confidence=0, default bucket."""
        result = aggregate_measurements([], [], [], [])
        assert result.flagged_for_review is True
        assert result.confidence_pct == pytest.approx(0.0)
        assert result.num_text_regions == 0
        assert result.measurement_method == "none"
        assert result.resolution_quality_score == pytest.approx(0.5)

    def test_single_region(self) -> None:
        """Single region should work but be flagged (< 3 regions)."""
        result = aggregate_measurements(
            region_heights=[40.0],
            _bbox_heights=[42.0],
            cc_success_flags=[True],
            region_areas=[1000.0],
        )
        assert result.num_text_regions == 1
        assert result.flagged_for_review is True
        assert result.char_height_px == pytest.approx(40.0, abs=0.1)
        assert result.coarse_bucket == "optimal"

    def test_uniform_optimal_regions(self) -> None:
        """Many uniform regions in optimal range -> high confidence, not flagged."""
        heights = [38.0, 39.0, 40.0, 41.0, 40.0, 39.0, 38.0, 40.0, 41.0, 39.0]
        areas = [1000.0] * 10
        flags = [True] * 10
        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.num_text_regions == 10
        assert result.num_valid_cc_regions == 10
        assert result.measurement_method == "stage_1_2"
        assert result.coarse_bucket == "optimal"
        assert 0.55 <= result.resolution_quality_score <= 0.75
        assert result.confidence_pct > 0.8
        assert result.flagged_for_review is False

    def test_mixed_cc_success(self) -> None:
        """Mix of CC success and fallback sets method correctly."""
        heights = [40.0, 42.0, 38.0, 44.0, 36.0]
        flags = [True, True, False, True, False]
        areas = [1000.0] * 5
        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.num_valid_cc_regions == 3
        assert result.measurement_method == "stage_1_2"

    def test_all_cc_failed(self) -> None:
        """All CC failures -> stage_1_only."""
        heights = [40.0, 42.0, 38.0, 44.0, 36.0]
        flags = [False, False, False, False, False]
        areas = [1000.0] * 5
        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.num_valid_cc_regions == 0
        assert result.measurement_method == "stage_1_only"

    def test_weighted_median_large_region_dominates(self) -> None:
        """A large region should dominate the weighted median."""
        # 9 small regions at 20px, 1 large region at 60px
        heights = [20.0] * 9 + [60.0]
        areas = [100.0] * 9 + [10000.0]  # Last region 100x larger
        flags = [True] * 10
        result = aggregate_measurements(heights, heights, flags, areas)

        # The large 60px region should pull the weighted median up
        assert result.char_height_px > 30.0

    def test_score_range_maps_through_piecewise(self) -> None:
        """score_range should be piecewise_quality_score of char_height_range_px."""
        heights = [30.0, 35.0, 40.0, 45.0, 50.0]
        areas = [1000.0] * 5
        flags = [True] * 5
        result = aggregate_measurements(heights, heights, flags, areas)

        expected_low = piecewise_quality_score(result.char_height_range_px[0])
        expected_high = piecewise_quality_score(result.char_height_range_px[1])
        assert result.score_range[0] == pytest.approx(expected_low, abs=1e-4)
        assert result.score_range[1] == pytest.approx(expected_high, abs=1e-4)

    def test_high_cv_triggers_flag(self) -> None:
        """Very inconsistent heights should flag for review."""
        # Mix of tiny and huge text -> high CV
        heights = [10.0, 10.0, 10.0, 100.0, 100.0, 100.0, 10.0, 100.0, 10.0, 100.0]
        areas = [1000.0] * 10
        flags = [True] * 10
        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.height_cv > 0.5
        assert result.flagged_for_review is True

    def test_low_region_count_caps_confidence(self) -> None:
        """< 3 regions should cap confidence at 0.3."""
        result = aggregate_measurements(
            region_heights=[40.0, 41.0],
            _bbox_heights=[40.0, 41.0],
            cc_success_flags=[True, True],
            region_areas=[1000.0, 1000.0],
        )
        assert result.confidence_pct <= 0.3
        assert result.flagged_for_review is True


# ---------------------------------------------------------------------------
# ResolutionQualityResult Serialization
# ---------------------------------------------------------------------------


class TestResolutionQualityResultToDict:
    """Test ResolutionQualityResult.to_dict() serialization."""

    def test_to_dict_contains_all_fields(self) -> None:
        """Serialized dict should have all expected keys."""
        result = ResolutionQualityResult(
            resolution_quality_score=0.62,
            confidence_pct=0.85,
            char_height_px=38.5,
            char_height_range_px=(35.0, 42.0),
            score_range=(0.57, 0.67),
            coarse_bucket="optimal",
            measurement_method="stage_1_2",
            num_text_regions=42,
            num_valid_cc_regions=38,
            height_cv=0.12,
            flagged_for_review=False,
        )
        serialized = result.to_dict()

        expected_keys = {
            "resolution_quality_score",
            "confidence_pct",
            "char_height_px",
            "char_height_range_px",
            "score_range",
            "coarse_bucket",
            "measurement_method",
            "num_text_regions",
            "num_valid_cc_regions",
            "height_cv",
            "flagged_for_review",
            # Provenance fields (v2.2)
            "label_provenance",
            "label_source",
            "label_confidence",
        }
        assert set(serialized.keys()) == expected_keys

    def test_to_dict_rounds_values(self) -> None:
        """Serialized values should be rounded appropriately."""
        result = ResolutionQualityResult(
            resolution_quality_score=0.6234567,
            confidence_pct=0.8534567,
            char_height_px=38.5678,
            char_height_range_px=(35.1234, 42.5678),
            score_range=(0.571234, 0.671234),
            coarse_bucket="optimal",
            measurement_method="stage_1_2",
            num_text_regions=42,
            num_valid_cc_regions=38,
            height_cv=0.1234567,
            flagged_for_review=False,
        )
        serialized = result.to_dict()

        assert serialized["resolution_quality_score"] == pytest.approx(0.6235)
        assert serialized["confidence_pct"] == pytest.approx(0.8535)
        assert serialized["char_height_px"] == pytest.approx(38.57)
        assert serialized["height_cv"] == pytest.approx(0.1235)

    def test_to_dict_range_is_list(self) -> None:
        """Ranges should serialize as lists (JSON-compatible), not tuples."""
        result = ResolutionQualityResult(
            resolution_quality_score=0.5,
            confidence_pct=0.5,
            char_height_px=30.0,
            char_height_range_px=(28.0, 32.0),
            score_range=(0.45, 0.55),
            coarse_bucket="needs_light_upscale",
            measurement_method="stage_1_only",
            num_text_regions=5,
            num_valid_cc_regions=0,
            height_cv=0.1,
            flagged_for_review=False,
        )
        serialized = result.to_dict()

        assert isinstance(serialized["char_height_range_px"], list)
        assert isinstance(serialized["score_range"], list)
        assert len(serialized["char_height_range_px"]) == 2
        assert len(serialized["score_range"]) == 2

    def test_frozen_dataclass(self) -> None:
        """ResolutionQualityResult should be immutable."""
        result = ResolutionQualityResult(
            resolution_quality_score=0.5,
            confidence_pct=0.5,
            char_height_px=30.0,
            char_height_range_px=(28.0, 32.0),
            score_range=(0.45, 0.55),
            coarse_bucket="optimal",
            measurement_method="stage_1_2",
            num_text_regions=5,
            num_valid_cc_regions=5,
            height_cv=0.1,
            flagged_for_review=False,
        )
        with pytest.raises(AttributeError):
            result.resolution_quality_score = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Extract Line Height from Polygon
# ---------------------------------------------------------------------------


class TestExtractLineHeightFromPolygon:
    """Test polygon -> line height computation."""

    def test_horizontal_rectangle(self) -> None:
        """A horizontal rectangle should return its height."""
        # top-left, top-right, bottom-right, bottom-left
        polygon = [[10, 10], [100, 10], [100, 30], [10, 30]]
        height = extract_line_height_from_polygon(polygon)
        assert height == pytest.approx(20.0, abs=0.1)

    def test_tall_rectangle(self) -> None:
        """A tall rectangle (vertical text) should return the larger dimension."""
        polygon = [[10, 10], [30, 10], [30, 100], [10, 100]]
        height = extract_line_height_from_polygon(polygon)
        assert height == pytest.approx(90.0, abs=0.1)

    def test_slightly_rotated_polygon(self) -> None:
        """Slightly rotated polygon should give average edge height."""
        # Simulates a slightly skewed text line
        polygon = [[10, 12], [100, 10], [100, 32], [10, 30]]
        height = extract_line_height_from_polygon(polygon)
        # Left edge: (10,12) to (10,30) = 18
        # Right edge: (100,10) to (100,32) = 22
        # Average = 20
        assert height == pytest.approx(20.0, abs=1.0)

    def test_non_four_point_polygon_fallback(self) -> None:
        """Non-4-point polygon should fall back to bounding rect height."""
        polygon = [[10, 10], [100, 10], [100, 30]]  # Triangle
        height = extract_line_height_from_polygon(polygon)
        # Fallback: bounding rect height is 20
        assert height == pytest.approx(20.0, abs=0.1)

    def test_zero_height_polygon(self) -> None:
        """Flat polygon should return 0 height."""
        polygon = [[10, 20], [100, 20], [100, 20], [10, 20]]
        height = extract_line_height_from_polygon(polygon)
        assert height == pytest.approx(0.0, abs=0.1)


# ---------------------------------------------------------------------------
# Crop Polygon Region
# ---------------------------------------------------------------------------


class TestCropPolygonRegion:
    """Test polygon-based region cropping and masking."""

    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a 200x300 grayscale test image with dark text-like regions."""
        img = np.ones((200, 300), dtype=np.uint8) * 255  # White background
        # Draw some dark rectangles to simulate text
        cv2.rectangle(img, (50, 50), (250, 80), 0, -1)
        cv2.rectangle(img, (50, 100), (250, 130), 0, -1)
        return img

    def test_valid_crop_returns_array(self, sample_image: np.ndarray) -> None:
        """Valid polygon should return a cropped region."""
        polygon = [[50, 50], [250, 50], [250, 80], [50, 80]]
        cropped = crop_polygon_region(sample_image, polygon)
        assert cropped is not None
        assert cropped.shape[0] > 0
        assert cropped.shape[1] > 0

    def test_cropped_region_has_mask(self, sample_image: np.ndarray) -> None:
        """Pixels outside the polygon should be set to 255 (white)."""
        # Use a polygon that doesn't fill the bounding rect
        polygon = [[60, 50], [240, 55], [235, 80], [55, 75]]
        cropped = crop_polygon_region(sample_image, polygon)
        assert cropped is not None
        # Corners of the bounding rect (outside polygon) should be white
        assert cropped[0, 0] == 255

    def test_tiny_region_returns_none(self, sample_image: np.ndarray) -> None:
        """Very small polygon (< 4px in either dimension) should return None."""
        # 1x1 polygon + default padding=2 -> still only 5x5 but check with no padding
        polygon = [[50, 50], [51, 50], [51, 51], [50, 51]]
        cropped = crop_polygon_region(sample_image, polygon, padding=0)
        assert cropped is None

    def test_padding_expands_region(self, sample_image: np.ndarray) -> None:
        """Padding should expand the cropped region beyond the polygon bounds."""
        polygon = [[50, 50], [100, 50], [100, 80], [50, 80]]
        cropped_no_pad = crop_polygon_region(sample_image, polygon, padding=0)
        cropped_with_pad = crop_polygon_region(sample_image, polygon, padding=5)
        assert cropped_no_pad is not None
        assert cropped_with_pad is not None
        assert cropped_with_pad.shape[0] >= cropped_no_pad.shape[0]
        assert cropped_with_pad.shape[1] >= cropped_no_pad.shape[1]

    def test_polygon_at_image_edge(self) -> None:
        """Polygon extending beyond image bounds should be clamped."""
        img = np.ones((100, 100), dtype=np.uint8) * 200
        polygon = [[-5, -5], [50, -5], [50, 30], [-5, 30]]
        cropped = crop_polygon_region(img, polygon, padding=0)
        assert cropped is not None
        assert cropped.shape[0] > 0
        assert cropped.shape[1] > 0


# ---------------------------------------------------------------------------
# Measure Char Height in Region (Stage 2 CC Analysis)
# ---------------------------------------------------------------------------


class TestMeasureCharHeightInRegion:
    """Test connected component character height measurement."""

    def _create_text_region(
        self,
        char_height: int = 20,
        num_chars: int = 10,
        spacing: int = 5,
        bg_value: int = 255,
        fg_value: int = 0,
    ) -> np.ndarray:
        """Create a synthetic text region with uniform character-like components.

        Args:
            char_height: Height of each character rectangle.
            num_chars: Number of characters to draw.
            spacing: Horizontal spacing between characters.
            bg_value: Background pixel value.
            fg_value: Foreground (text) pixel value.

        Returns:
            Grayscale image of synthetic text line.
        """
        char_width = int(char_height * 0.6)  # Typical aspect ratio
        width = num_chars * (char_width + spacing) + spacing
        height = char_height + 10  # Small margin
        img = np.ones((height, width), dtype=np.uint8) * bg_value

        for i in range(num_chars):
            x_start = spacing + i * (char_width + spacing)
            y_start = 5
            cv2.rectangle(
                img,
                (x_start, y_start),
                (x_start + char_width, y_start + char_height),
                fg_value,
                -1,
            )
        return img

    def test_measures_known_height(self) -> None:
        """Characters of known height should be measured accurately."""
        region = self._create_text_region(char_height=30, num_chars=10)
        median_h, heights = measure_char_height_in_region(region)

        assert median_h is not None
        # Allow ±3px tolerance for CC measurement vs rectangle height
        assert abs(median_h - 30.0) < 3.0
        assert len(heights) >= 3

    def test_different_heights(self) -> None:
        """Larger characters should produce proportionally larger measurements."""
        region_small = self._create_text_region(char_height=15, num_chars=10)
        region_large = self._create_text_region(char_height=40, num_chars=10)

        h_small, _ = measure_char_height_in_region(region_small)
        h_large, _ = measure_char_height_in_region(region_large)

        assert h_small is not None
        assert h_large is not None
        assert h_large > h_small

    def test_too_few_components(self) -> None:
        """Region with fewer than min_components valid CCs returns None."""
        # Single character
        region = self._create_text_region(char_height=20, num_chars=1)
        median_h, heights = measure_char_height_in_region(region, min_components=3)
        assert median_h is None
        assert heights == []

    def test_tiny_region_returns_none(self) -> None:
        """Very small region (< 16 pixels) returns None."""
        tiny = np.zeros((3, 3), dtype=np.uint8)
        median_h, heights = measure_char_height_in_region(tiny)
        assert median_h is None
        assert heights == []

    def test_blank_region_returns_none(self) -> None:
        """All-white region with no text should return None."""
        blank = np.ones((50, 200), dtype=np.uint8) * 255
        median_h, _ = measure_char_height_in_region(blank)
        assert median_h is None

    def test_custom_min_components(self) -> None:
        """Custom min_components threshold changes the minimum valid CC count."""
        region = self._create_text_region(char_height=20, num_chars=5)

        # With low threshold, should succeed
        median_h, _ = measure_char_height_in_region(region, min_components=2)
        assert median_h is not None

    def test_returns_component_heights_list(self) -> None:
        """The heights list should contain all valid component heights."""
        region = self._create_text_region(char_height=25, num_chars=8)
        median_h, heights = measure_char_height_in_region(region)
        assert median_h is not None
        assert len(heights) > 0
        for h_val in heights:
            assert isinstance(h_val, float)
            assert h_val > 0


# ---------------------------------------------------------------------------
# CoarseBucket Enum
# ---------------------------------------------------------------------------


class TestCoarseBucketEnum:
    """Test CoarseBucket enum properties."""

    def test_all_buckets_are_strings(self) -> None:
        """CoarseBucket values should be usable as strings."""
        for bucket in CoarseBucket:
            assert isinstance(bucket.value, str)

    def test_five_buckets_exist(self) -> None:
        """There should be exactly 5 coarse buckets."""
        assert len(CoarseBucket) == 5

    def test_bucket_names_match_values(self) -> None:
        """Bucket names should match their string values (upper vs lower)."""
        for bucket in CoarseBucket:
            assert bucket.value == bucket.name.lower()


# ---------------------------------------------------------------------------
# Integration: End-to-End Aggregation with Score Validation
# ---------------------------------------------------------------------------


class TestEndToEndAggregation:
    """Integration tests combining aggregation with score validation."""

    def test_optimal_document(self) -> None:
        """Typical well-scanned document at ~300 DPI."""
        heights = [36.0, 38.0, 37.0, 39.0, 38.0, 37.0, 36.0, 38.0, 39.0, 37.0]
        areas = [5000.0] * 10
        flags = [True] * 10

        result = aggregate_measurements(heights, heights, flags, areas)
        output = result.to_dict()

        assert output["coarse_bucket"] == "optimal"
        assert 0.55 <= output["resolution_quality_score"] <= 0.75
        assert output["confidence_pct"] > 0.8
        assert output["flagged_for_review"] is False
        assert output["measurement_method"] == "stage_1_2"

    def test_low_resolution_document(self) -> None:
        """Low-quality scan needing upscaling."""
        heights = [12.0, 11.0, 13.0, 12.0, 11.0, 12.0, 13.0, 11.0, 12.0, 12.0]
        areas = [2000.0] * 10
        flags = [True] * 10

        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.coarse_bucket == "needs_major_upscale"
        assert result.resolution_quality_score < 0.15
        assert result.flagged_for_review is False

    def test_oversized_document(self) -> None:
        """High-DPI scan that could be downscaled."""
        heights = [120.0, 115.0, 125.0, 118.0, 122.0, 116.0, 120.0, 119.0, 121.0, 117.0]
        areas = [10000.0] * 10
        flags = [True] * 10

        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.coarse_bucket == "oversized"
        assert result.resolution_quality_score > 0.95

    def test_sparse_text_page(self) -> None:
        """Page with very few text regions (e.g., title page)."""
        heights = [45.0, 60.0]
        areas = [3000.0, 8000.0]
        flags = [True, True]

        result = aggregate_measurements(heights, heights, flags, areas)

        assert result.flagged_for_review is True
        assert result.confidence_pct <= 0.3  # Capped due to < 3 regions

    def test_to_dict_is_json_serializable(self) -> None:
        """Verify the output can be serialized to JSON without errors."""
        import json

        heights = [38.0, 39.0, 40.0, 41.0, 40.0]
        areas = [1000.0] * 5
        flags = [True] * 5

        result = aggregate_measurements(heights, heights, flags, areas)
        output = result.to_dict()

        # Should not raise
        json_str = json.dumps(output)
        assert isinstance(json_str, str)

        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["coarse_bucket"] == output["coarse_bucket"]
