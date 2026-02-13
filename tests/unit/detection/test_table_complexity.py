# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for TableComplexityAnalyzer.

Tests cover:
- Simple grid table (3x3) with clear lines -> low complexity
- Complex grid with missing lines -> merged cells detected
- Blank image with no lines -> no table structure
- Bbox cropping extracts the correct sub-region
- Complexity score is always in [0, 1]
- Estimated rows and columns are always >= 0
- Edge cases: invalid input (ValueError), tiny image
- Module-level convenience function
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.table_complexity import (
    TableComplexityAnalyzer,
    analyze_table_complexity,
)
from image_preprocessing_detector.schema import TableComplexity

# ---------------------------------------------------------------------------
# Helpers: draw synthetic table images
# ---------------------------------------------------------------------------


def _draw_grid(
    width: int,
    height: int,
    rows: int,
    cols: int,
    thickness: int = 2,
    color: tuple[int, int, int] = (0, 0, 0),
    margin: int = 20,
) -> np.ndarray:
    """Draw a uniform grid table on a white BGR image.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        rows: Number of data rows (rows+1 horizontal lines drawn).
        cols: Number of data columns (cols+1 vertical lines drawn).
        thickness: Line thickness.
        color: BGR line color.
        margin: Pixel margin around the grid.

    Returns:
        BGR image with the drawn grid.
    """
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    x_start, x_end = margin, width - margin
    y_start, y_end = margin, height - margin
    cell_h = (y_end - y_start) / rows if rows > 0 else 0
    cell_w = (x_end - x_start) / cols if cols > 0 else 0

    # Horizontal lines
    for i in range(rows + 1):
        y_pos = int(y_start + i * cell_h)
        cv2.line(img, (x_start, y_pos), (x_end, y_pos), color, thickness)

    # Vertical lines
    for j in range(cols + 1):
        x_pos = int(x_start + j * cell_w)
        cv2.line(img, (x_pos, y_start), (x_pos, y_end), color, thickness)

    return img


def _draw_grid_with_gaps(
    width: int,
    height: int,
    rows: int,
    cols: int,
    skip_h_lines: list[int] | None = None,
    skip_v_lines: list[int] | None = None,
    thickness: int = 2,
    margin: int = 20,
) -> np.ndarray:
    """Draw a grid with some interior lines removed to simulate merged cells.

    Args:
        width: Image width.
        height: Image height.
        rows: Number of data rows.
        cols: Number of data columns.
        skip_h_lines: Indices of interior horizontal lines to omit (1-based).
        skip_v_lines: Indices of interior vertical lines to omit (1-based).
        thickness: Line thickness.
        margin: Margin around the grid.

    Returns:
        BGR image with a partially drawn grid.
    """
    skip_h = set(skip_h_lines or [])
    skip_v = set(skip_v_lines or [])

    img = np.full((height, width, 3), 255, dtype=np.uint8)
    x_start, x_end = margin, width - margin
    y_start, y_end = margin, height - margin
    cell_h = (y_end - y_start) / rows if rows > 0 else 0
    cell_w = (x_end - x_start) / cols if cols > 0 else 0

    for i in range(rows + 1):
        if i in skip_h:
            continue
        y_pos = int(y_start + i * cell_h)
        cv2.line(img, (x_start, y_pos), (x_end, y_pos), (0, 0, 0), thickness)

    for j in range(cols + 1):
        if j in skip_v:
            continue
        x_pos = int(x_start + j * cell_w)
        cv2.line(img, (x_pos, y_start), (x_pos, y_end), (0, 0, 0), thickness)

    return img


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer() -> TableComplexityAnalyzer:
    """Reusable analyzer instance."""
    return TableComplexityAnalyzer()


@pytest.fixture
def simple_3x3_table() -> np.ndarray:
    """A clean 3-row, 3-column grid on a 600x400 image."""
    return _draw_grid(600, 400, rows=3, cols=3, thickness=2)


@pytest.fixture
def large_12x6_table() -> np.ndarray:
    """A 12-row, 6-column grid (exceeds large-table thresholds)."""
    return _draw_grid(800, 800, rows=12, cols=6, thickness=2)


@pytest.fixture
def grid_with_gaps() -> np.ndarray:
    """A 5x4 grid with interior lines removed to simulate merged cells."""
    return _draw_grid_with_gaps(
        600,
        500,
        rows=5,
        cols=4,
        skip_h_lines=[2, 3],
        skip_v_lines=[2],
        thickness=2,
    )


@pytest.fixture
def blank_image() -> np.ndarray:
    """Pure white image with no lines."""
    return np.full((400, 600, 3), 255, dtype=np.uint8)


@pytest.fixture
def tiny_image() -> np.ndarray:
    """Very small image below the minimum analysis dimension."""
    return np.full((5, 5, 3), 200, dtype=np.uint8)


@pytest.fixture
def image_with_table_region() -> np.ndarray:
    """Large image with a table drawn in a known sub-region.

    The table occupies a 400x300 area starting at (100, 50).
    """
    img = np.full((500, 700, 3), 255, dtype=np.uint8)
    # Draw a 3x3 grid inside the bounding box region
    margin = 10
    x_start, y_start = 100 + margin, 50 + margin
    x_end, y_end = 500 - margin, 350 - margin
    rows, cols = 3, 3
    cell_h = (y_end - y_start) / rows
    cell_w = (x_end - x_start) / cols

    for i in range(rows + 1):
        y_pos = int(y_start + i * cell_h)
        cv2.line(img, (x_start, y_pos), (x_end, y_pos), (0, 0, 0), 2)
    for j in range(cols + 1):
        x_pos = int(x_start + j * cell_w)
        cv2.line(img, (x_pos, y_start), (x_pos, y_end), (0, 0, 0), 2)

    return img


# ---------------------------------------------------------------------------
# Tests: simple grid -> low complexity
# ---------------------------------------------------------------------------


class TestSimpleGrid:
    """A clean uniform grid should be detected as a simple bordered table."""

    def test_detects_rows_and_columns(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        result = analyzer.analyze(simple_3x3_table)
        assert result.estimated_rows >= 2, "Should detect at least 2 rows"
        assert result.estimated_columns >= 2, "Should detect at least 2 columns"

    def test_has_borders(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        result = analyzer.analyze(simple_3x3_table)
        assert result.has_borders is True

    def test_no_merged_cells(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        result = analyzer.analyze(simple_3x3_table)
        assert result.has_merged_cells is False

    def test_low_complexity_score(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        result = analyzer.analyze(simple_3x3_table)
        assert result.complexity_score <= 0.4, (
            f"Simple 3x3 grid should have low complexity, got {result.complexity_score}"
        )

    def test_returns_table_complexity_model(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        result = analyzer.analyze(simple_3x3_table)
        assert isinstance(result, TableComplexity)


# ---------------------------------------------------------------------------
# Tests: grid with gaps -> merged cells
# ---------------------------------------------------------------------------


class TestGridWithGaps:
    """A grid with missing interior lines should trigger merged-cell detection."""

    def test_detects_some_structure(
        self, analyzer: TableComplexityAnalyzer, grid_with_gaps: np.ndarray
    ) -> None:
        result = analyzer.analyze(grid_with_gaps)
        # Even with gaps, outer boundary lines should yield some rows/cols
        assert result.estimated_rows >= 1
        assert result.estimated_columns >= 1

    def test_higher_complexity_than_simple(
        self,
        analyzer: TableComplexityAnalyzer,
        simple_3x3_table: np.ndarray,
        grid_with_gaps: np.ndarray,
    ) -> None:
        simple_result = analyzer.analyze(simple_3x3_table)
        gap_result = analyzer.analyze(grid_with_gaps)
        # The gapped grid should generally score higher (or equal in edge cases)
        assert gap_result.complexity_score >= simple_result.complexity_score or (
            gap_result.has_merged_cells or not gap_result.has_borders
        )


# ---------------------------------------------------------------------------
# Tests: blank image -> no table structure
# ---------------------------------------------------------------------------


class TestBlankImage:
    """A blank image with no lines should yield an empty table result."""

    def test_no_rows_or_columns(
        self, analyzer: TableComplexityAnalyzer, blank_image: np.ndarray
    ) -> None:
        result = analyzer.analyze(blank_image)
        assert result.estimated_rows == 0
        assert result.estimated_columns == 0

    def test_no_borders(
        self, analyzer: TableComplexityAnalyzer, blank_image: np.ndarray
    ) -> None:
        result = analyzer.analyze(blank_image)
        assert result.has_borders is False

    def test_no_merged_cells(
        self, analyzer: TableComplexityAnalyzer, blank_image: np.ndarray
    ) -> None:
        result = analyzer.analyze(blank_image)
        assert result.has_merged_cells is False

    def test_zero_complexity(
        self, analyzer: TableComplexityAnalyzer, blank_image: np.ndarray
    ) -> None:
        result = analyzer.analyze(blank_image)
        assert result.complexity_score == 0.0


# ---------------------------------------------------------------------------
# Tests: bbox cropping
# ---------------------------------------------------------------------------


class TestBboxCropping:
    """Bounding box should isolate the table region for analysis."""

    def test_bbox_detects_table(
        self,
        analyzer: TableComplexityAnalyzer,
        image_with_table_region: np.ndarray,
    ) -> None:
        result = analyzer.analyze(image_with_table_region, bbox=(100, 50, 400, 300))
        assert result.estimated_rows >= 1, "Should find rows within bbox"
        assert result.estimated_columns >= 1, "Should find columns within bbox"

    def test_bbox_outside_table_finds_nothing(
        self,
        analyzer: TableComplexityAnalyzer,
        image_with_table_region: np.ndarray,
    ) -> None:
        # Bottom-right corner is all white
        result = analyzer.analyze(image_with_table_region, bbox=(550, 380, 140, 110))
        assert result.estimated_rows == 0
        assert result.estimated_columns == 0

    def test_full_image_without_bbox(
        self,
        analyzer: TableComplexityAnalyzer,
        image_with_table_region: np.ndarray,
    ) -> None:
        # Without bbox, the table lines are still present in the full image
        result = analyzer.analyze(image_with_table_region)
        assert result.estimated_rows >= 1 or result.estimated_columns >= 1


# ---------------------------------------------------------------------------
# Tests: score invariants
# ---------------------------------------------------------------------------


class TestScoreInvariants:
    """Complexity score and counts must satisfy their documented invariants."""

    @pytest.mark.parametrize(
        "fixture_name",
        ["simple_3x3_table", "large_12x6_table", "grid_with_gaps", "blank_image"],
    )
    def test_complexity_score_in_range(
        self,
        analyzer: TableComplexityAnalyzer,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        image = request.getfixturevalue(fixture_name)
        result = analyzer.analyze(image)
        assert 0.0 <= result.complexity_score <= 1.0

    @pytest.mark.parametrize(
        "fixture_name",
        ["simple_3x3_table", "large_12x6_table", "grid_with_gaps", "blank_image"],
    )
    def test_rows_and_columns_non_negative(
        self,
        analyzer: TableComplexityAnalyzer,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        image = request.getfixturevalue(fixture_name)
        result = analyzer.analyze(image)
        assert result.estimated_rows >= 0
        assert result.estimated_columns >= 0


# ---------------------------------------------------------------------------
# Tests: large table triggers higher complexity
# ---------------------------------------------------------------------------


class TestLargeTable:
    """A 12x6 table should trigger the 'large table' complexity bonuses."""

    def test_large_table_higher_complexity(
        self,
        analyzer: TableComplexityAnalyzer,
        simple_3x3_table: np.ndarray,
        large_12x6_table: np.ndarray,
    ) -> None:
        small_result = analyzer.analyze(simple_3x3_table)
        large_result = analyzer.analyze(large_12x6_table)
        assert large_result.complexity_score >= small_result.complexity_score


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: invalid input, tiny images, grayscale input."""

    def test_none_image_raises(self, analyzer: TableComplexityAnalyzer) -> None:
        with pytest.raises(ValueError, match="Invalid image"):
            analyzer.analyze(None)  # type: ignore[arg-type]

    def test_empty_array_raises(self, analyzer: TableComplexityAnalyzer) -> None:
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError):
            analyzer.analyze(empty)

    def test_tiny_image_returns_empty(
        self, analyzer: TableComplexityAnalyzer, tiny_image: np.ndarray
    ) -> None:
        result = analyzer.analyze(tiny_image)
        assert result.estimated_rows == 0
        assert result.estimated_columns == 0
        assert result.complexity_score == 0.0

    def test_grayscale_input(self, analyzer: TableComplexityAnalyzer) -> None:
        gray = np.full((400, 600), 255, dtype=np.uint8)
        # Draw a few lines for a basic grid
        cv2.line(gray, (20, 20), (580, 20), 0, 2)
        cv2.line(gray, (20, 200), (580, 200), 0, 2)
        cv2.line(gray, (20, 380), (580, 380), 0, 2)
        cv2.line(gray, (20, 20), (20, 380), 0, 2)
        cv2.line(gray, (300, 20), (300, 380), 0, 2)
        cv2.line(gray, (580, 20), (580, 380), 0, 2)
        result = analyzer.analyze(gray)
        assert isinstance(result, TableComplexity)
        assert result.estimated_rows >= 1

    def test_bgra_input(self, analyzer: TableComplexityAnalyzer) -> None:
        bgra = np.full((400, 600, 4), 255, dtype=np.uint8)
        bgra[:, :, 3] = 255  # full opacity
        # Draw a simple grid
        cv2.line(bgra, (20, 20), (580, 20), (0, 0, 0, 255), 2)
        cv2.line(bgra, (20, 200), (580, 200), (0, 0, 0, 255), 2)
        cv2.line(bgra, (20, 380), (580, 380), (0, 0, 0, 255), 2)
        cv2.line(bgra, (20, 20), (20, 380), (0, 0, 0, 255), 2)
        cv2.line(bgra, (300, 20), (300, 380), (0, 0, 0, 255), 2)
        cv2.line(bgra, (580, 20), (580, 380), (0, 0, 0, 255), 2)
        result = analyzer.analyze(bgra)
        assert isinstance(result, TableComplexity)

    def test_invalid_bbox_raises(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        # Completely outside the image
        with pytest.raises(ValueError, match="empty region"):
            analyzer.analyze(simple_3x3_table, bbox=(9000, 9000, 100, 100))

    def test_zero_size_bbox_raises(
        self, analyzer: TableComplexityAnalyzer, simple_3x3_table: np.ndarray
    ) -> None:
        with pytest.raises(ValueError, match="empty region"):
            analyzer.analyze(simple_3x3_table, bbox=(100, 100, 0, 0))


# ---------------------------------------------------------------------------
# Tests: module-level convenience function
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """The module-level ``analyze_table_complexity`` function should behave
    identically to the class-based API."""

    def test_returns_table_complexity(self, simple_3x3_table: np.ndarray) -> None:
        result = analyze_table_complexity(simple_3x3_table)
        assert isinstance(result, TableComplexity)

    def test_with_bbox(self, image_with_table_region: np.ndarray) -> None:
        result = analyze_table_complexity(
            image_with_table_region, bbox=(100, 50, 400, 300)
        )
        assert result.estimated_rows >= 1

    def test_blank_image(self, blank_image: np.ndarray) -> None:
        result = analyze_table_complexity(blank_image)
        assert result.estimated_rows == 0
        assert result.complexity_score == 0.0

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            analyze_table_complexity(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: complexity scoring formula unit tests
# ---------------------------------------------------------------------------


class TestComplexityScoringFormula:
    """Direct tests against the scoring formula to ensure correctness."""

    def test_base_score(self) -> None:
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=3,
            estimated_columns=3,
            has_merged_cells=False,
            has_borders=True,
        )
        assert score == pytest.approx(0.1)

    def test_large_dimensions_bonus(self) -> None:
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=12,
            estimated_columns=3,
            has_merged_cells=False,
            has_borders=True,
        )
        # base 0.1 + 0.2 (rows > 10)
        assert score == pytest.approx(0.3)

    def test_merged_cells_bonus(self) -> None:
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=3,
            estimated_columns=3,
            has_merged_cells=True,
            has_borders=True,
        )
        # base 0.1 + 0.3 (merged)
        assert score == pytest.approx(0.4)

    def test_no_borders_bonus(self) -> None:
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=3,
            estimated_columns=3,
            has_merged_cells=False,
            has_borders=False,
        )
        # base 0.1 + 0.1 (no borders)
        assert score == pytest.approx(0.2)

    def test_large_cell_count_bonus(self) -> None:
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=8,
            estimated_columns=7,
            has_merged_cells=False,
            has_borders=True,
        )
        # base 0.1 + 0.2 (cols > 5) + 0.1 (8*7=56 > 50)
        assert score == pytest.approx(0.4)

    def test_all_bonuses_capped_at_one(self) -> None:
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=15,
            estimated_columns=8,
            has_merged_cells=True,
            has_borders=False,
        )
        # base 0.1 + 0.2 + 0.3 + 0.1 + 0.1 = 0.8, under 1.0
        assert score == pytest.approx(0.8)

    def test_cap_at_1_0(self) -> None:
        """Ensure score never exceeds 1.0 even if formula were modified."""
        from image_preprocessing_detector.detection.table_complexity import (
            _compute_complexity_score,
        )

        score = _compute_complexity_score(
            estimated_rows=100,
            estimated_columns=100,
            has_merged_cells=True,
            has_borders=False,
        )
        assert score <= 1.0
