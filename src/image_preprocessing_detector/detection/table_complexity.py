"""Table complexity analysis using Hough line grid detection.

Analyzes table regions to estimate structural complexity by detecting grid
lines, counting rows and columns, identifying merged cells, and scoring
overall complexity. Used for routing decisions between fast and accurate
table extraction modes.

Algorithm:
    1. Detect horizontal and vertical lines via HoughLinesP
    2. Cluster line positions to estimate distinct rows and columns
    3. Check border presence (sufficient lines relative to cell count)
    4. Detect merged cells from gaps in the grid pattern
    5. Score complexity based on size, borders, and merged cells

Performance target: <20ms per table region.
"""

from __future__ import annotations

import cv2
import numpy as np

from image_preprocessing_detector.detection.advanced_detectors import (
    _validate_and_preprocess,
)
from image_preprocessing_detector.schema import TableComplexity
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# HoughLinesP tuning constants
# ---------------------------------------------------------------------------
_HOUGH_RHO = 1
_HOUGH_THETA = np.pi / 180
_HOUGH_THRESHOLD = 30
_MIN_LINE_LENGTH_FRACTION = 0.15
_MAX_LINE_GAP = 10

# Line classification: max degrees from axis to count as horizontal/vertical
_ANGLE_TOLERANCE_DEG = 10.0

# Clustering: minimum pixel distance between distinct row/column positions
_MIN_CLUSTER_GAP = 8

# Border detection: minimum ratio of detected lines to expected grid lines
_BORDER_LINE_RATIO = 0.4

# Merged cell detection: fraction of expected grid intersections that are empty
_MERGE_GAP_THRESHOLD = 0.25

# Minimum image dimension for meaningful analysis
_MIN_DIMENSION = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_lines(
    lines: np.ndarray,
    img_width: int,
    img_height: int,
) -> tuple[list[int], list[int]]:
    """Classify detected lines as horizontal or vertical.

    Args:
        lines (np.ndarray): HoughLinesP output array of shape (N, 1, 4).
        img_width (int): Image width for minimum length filtering.
        img_height (int): Image height for minimum length filtering.

    Returns:
        tuple[list[int], list[int]]: Tuple of (horizontal_y_positions, vertical_x_positions) for the
        midpoints of qualifying lines."""
    horizontal_ys: list[int] = []
    vertical_xs: list[int] = []
    angle_tol_rad = np.radians(_ANGLE_TOLERANCE_DEG)

    min_h_length = img_width * _MIN_LINE_LENGTH_FRACTION
    min_v_length = img_height * _MIN_LINE_LENGTH_FRACTION

    for line in lines:
        x_1, y_1, x_2, y_2 = line[0]
        dx = float(x_2 - x_1)
        dy = float(y_2 - y_1)
        length = np.sqrt(dx * dx + dy * dy)

        if length < 1:
            continue

        angle = abs(np.arctan2(dy, dx))

        # Near-horizontal: angle close to 0 or pi
        if angle < angle_tol_rad or abs(angle - np.pi) < angle_tol_rad:
            if length >= min_h_length:
                horizontal_ys.append((y_1 + y_2) // 2)
        # Near-vertical: angle close to pi/2
        elif abs(angle - np.pi / 2) < angle_tol_rad and length >= min_v_length:
            vertical_xs.append((x_1 + x_2) // 2)

    return horizontal_ys, vertical_xs


def _cluster_positions(positions: list[int], min_gap: int) -> list[int]:
    """Cluster nearby line positions into distinct grid lines.

    Groups positions within ``min_gap`` pixels and returns the mean of each
    cluster, sorted in ascending order.

    Args:
        positions (list[int]): Raw line midpoint positions.
        min_gap (int): Minimum pixel distance between distinct clusters.

    Returns:
        list[int]: Sorted list of distinct cluster center positions."""
    if not positions:
        return []

    sorted_pos = sorted(positions)
    clusters: list[list[int]] = [[sorted_pos[0]]]

    for pos in sorted_pos[1:]:
        if pos - clusters[-1][-1] <= min_gap:
            clusters[-1].append(pos)
        else:
            clusters.append([pos])

    return sorted(int(np.mean(cluster)) for cluster in clusters)


def _is_gap_at_point(
    binary: np.ndarray,
    center_x: int,
    center_y: int,
    img_w: int,
    img_h: int,
    radius: int = 3,
) -> bool:
    """Check if a grid line gap exists at the given point.

    Args:
        binary (np.ndarray): Binary (inverted) image where lines are white.
        center_x (int): X coordinate of the sample center.
        center_y (int): Y coordinate of the sample center.
        img_w (int): Image width.
        img_h (int): Image height.
        radius (int): Half-size of the sampling window.

    Returns:
        bool: True if the region around the point has low intensity (gap)."""
    if not (0 <= center_x < img_w and 0 <= center_y < img_h):
        return False
    y_lo = max(0, center_y - radius)
    y_hi = min(img_h, center_y + radius + 1)
    x_lo = max(0, center_x - radius)
    x_hi = min(img_w, center_x + radius + 1)
    region = binary[y_lo:y_hi, x_lo:x_hi]
    return bool(np.mean(region) < 30)


def _detect_merged_cells(
    binary: np.ndarray,
    row_positions: list[int],
    col_positions: list[int],
) -> bool:
    """Detect merged cells by looking for missing grid lines in cell interiors.

    For each expected interior grid intersection, check whether a line
    segment is present. Large gaps suggest merged cells.

    Args:
        binary (np.ndarray): Binary (inverted) image where lines are white.
        row_positions (list[int]): Distinct row-boundary y-positions.
        col_positions (list[int]): Distinct column-boundary x-positions.

    Returns:
        bool: True if the gap pattern suggests merged cells."""
    if len(row_positions) < 3 or len(col_positions) < 3:
        return False

    img_h, img_w = binary.shape[:2]
    total_checks = 0
    gaps_found = 0

    # Check interior horizontal segments between adjacent column boundaries
    for row_y in row_positions[1:-1]:
        for col_idx in range(len(col_positions) - 1):
            mid_x = (col_positions[col_idx] + col_positions[col_idx + 1]) // 2
            total_checks += 1
            if _is_gap_at_point(binary, mid_x, row_y, img_w, img_h):
                gaps_found += 1

    # Check interior vertical segments between adjacent row boundaries
    for col_x in col_positions[1:-1]:
        for row_idx in range(len(row_positions) - 1):
            mid_y = (row_positions[row_idx] + row_positions[row_idx + 1]) // 2
            total_checks += 1
            if _is_gap_at_point(binary, col_x, mid_y, img_w, img_h):
                gaps_found += 1

    if total_checks == 0:
        return False

    gap_ratio = gaps_found / total_checks
    return gap_ratio >= _MERGE_GAP_THRESHOLD


def _compute_complexity_score(
    estimated_rows: int,
    estimated_columns: int,
    has_merged_cells: bool,
    has_borders: bool,
) -> float:
    """Compute the overall complexity score in [0, 1].

    Scoring formula:
        base = 0.1
        + 0.2 if rows > 10 or columns > 5
        + 0.3 if has_merged_cells
        + 0.1 if not has_borders
        + 0.1 if rows * columns > 50
        capped at 1.0

    Args:
        estimated_rows (int): Number of detected rows.
        estimated_columns (int): Number of detected columns.
        has_merged_cells (bool): Whether merged cells were detected.
        has_borders (bool): Whether the table has visible borders.

    Returns:
        float: Complexity score between 0.0 and 1.0."""
    score = 0.1

    if estimated_rows > 10 or estimated_columns > 5:
        score += 0.2

    if has_merged_cells:
        score += 0.3

    if not has_borders:
        score += 0.1

    if estimated_rows * estimated_columns > 50:
        score += 0.1

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class TableComplexityAnalyzer:
    """Analyzes table regions to estimate structural complexity.

    Uses Hough line detection to find grid structure, clusters line
    positions into rows and columns, detects merged cells, and produces
    an overall complexity score.

    Example::

        analyzer = TableComplexityAnalyzer()
        result = analyzer.analyze(image, bbox=(100, 200, 400, 300))
        print(result.estimated_rows, result.complexity_score)
    """

    def analyze(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> TableComplexity:
        """Analyze a table region and return complexity indicators.

        Args:
            image (np.ndarray): Input image (BGR, BGRA, or grayscale).
            bbox (tuple[int, int, int, int] | None): Optional bounding box ``(x, y, w, h)`` to crop the table region before analysis. If ``None``, the entire image is used.

        Returns:
            TableComplexity: :class:`TableComplexity` with grid estimates and complexity score."""
        region = self._extract_region(image, bbox)
        _gray, binary, height, width = _validate_and_preprocess(region)

        if height < _MIN_DIMENSION or width < _MIN_DIMENSION:
            logger.debug(
                "Image too small for table analysis", height=height, width=width
            )
            return TableComplexity(
                has_borders=False,
                estimated_rows=0,
                estimated_columns=0,
                has_merged_cells=False,
                complexity_score=0.0,
            )

        lines = self._detect_lines(binary, width, height)

        if lines is None or len(lines) == 0:
            logger.debug("No lines detected in table region")
            return TableComplexity(
                has_borders=False,
                estimated_rows=0,
                estimated_columns=0,
                has_merged_cells=False,
                complexity_score=0.0,
            )

        horizontal_ys, vertical_xs = _classify_lines(lines, width, height)

        row_positions = _cluster_positions(horizontal_ys, _MIN_CLUSTER_GAP)
        col_positions = _cluster_positions(vertical_xs, _MIN_CLUSTER_GAP)

        estimated_rows = max(0, len(row_positions) - 1)
        estimated_columns = max(0, len(col_positions) - 1)

        has_borders = self._check_borders(
            len(horizontal_ys),
            len(vertical_xs),
            estimated_rows,
            estimated_columns,
        )

        has_merged_cells = _detect_merged_cells(binary, row_positions, col_positions)

        complexity_score = _compute_complexity_score(
            estimated_rows,
            estimated_columns,
            has_merged_cells,
            has_borders,
        )

        logger.debug(
            "Table complexity analysis complete",
            rows=estimated_rows,
            columns=estimated_columns,
            has_borders=has_borders,
            has_merged_cells=has_merged_cells,
            complexity_score=complexity_score,
        )

        return TableComplexity(
            has_borders=has_borders,
            estimated_rows=estimated_rows,
            estimated_columns=estimated_columns,
            has_merged_cells=has_merged_cells,
            complexity_score=complexity_score,
        )

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _extract_region(
        image: np.ndarray,
        bbox: tuple[int, int, int, int] | None,
    ) -> np.ndarray:
        """Crop the image to the bounding box if provided.

        Args:
            image (np.ndarray): Full input image.
            bbox (tuple[int, int, int, int] | None): ``(x, y, w, h)`` or ``None``.

        Returns:
            np.ndarray: Cropped region or original image.

        Raises:
            ValueError: If bbox yields an empty region.
        """
        if bbox is None:
            return image

        bx, by, bw, bh = bbox
        img_h, img_w = image.shape[:2]

        # Clamp to image boundaries
        x_start = max(0, bx)
        y_start = max(0, by)
        x_end = min(img_w, bx + bw)
        y_end = min(img_h, by + bh)

        if x_end <= x_start or y_end <= y_start:
            raise ValueError(
                f"Bounding box produces empty region: bbox={bbox}, "
                f"image_shape={image.shape[:2]}"
            )

        return image[y_start:y_end, x_start:x_end]

    @staticmethod
    def _detect_lines(
        binary: np.ndarray,
        width: int,
        height: int,
    ) -> np.ndarray | None:
        """Run HoughLinesP on the binary image.

        Args:
            binary (np.ndarray): Binary (inverted) image.
            width (int): Image width.
            height (int): Image height.

        Returns:
            np.ndarray | None: Array of detected lines or ``None``."""
        min_length = int(min(width, height) * _MIN_LINE_LENGTH_FRACTION)
        min_length = max(min_length, 10)

        return cv2.HoughLinesP(
            binary,
            rho=_HOUGH_RHO,
            theta=_HOUGH_THETA,
            threshold=_HOUGH_THRESHOLD,
            minLineLength=min_length,
            maxLineGap=_MAX_LINE_GAP,
        )

    @staticmethod
    def _check_borders(
        num_h_lines: int,
        num_v_lines: int,
        estimated_rows: int,
        estimated_columns: int,
    ) -> bool:
        """Determine whether the table has visible borders.

        A bordered table should have roughly ``rows + 1`` horizontal and
        ``columns + 1`` vertical grid lines.

        Args:
            num_h_lines (int): Total horizontal lines detected (before clustering).
            num_v_lines (int): Total vertical lines detected (before clustering).
            estimated_rows (int): Number of estimated rows.
            estimated_columns (int): Number of estimated columns.

        Returns:
            bool: ``True`` if the table appears to have visible borders."""
        expected_h = estimated_rows + 1 if estimated_rows > 0 else 1
        expected_v = estimated_columns + 1 if estimated_columns > 0 else 1

        h_ratio = num_h_lines / expected_h
        v_ratio = num_v_lines / expected_v

        return h_ratio >= _BORDER_LINE_RATIO and v_ratio >= _BORDER_LINE_RATIO


def analyze_table_complexity(
    image: np.ndarray,
    bbox: tuple[int, int, int, int] | None = None,
) -> TableComplexity:
    """Module-level convenience function for table complexity analysis.

    Args:
        image (np.ndarray): Input image (BGR, BGRA, or grayscale).
        bbox (tuple[int, int, int, int] | None): Optional bounding box ``(x, y, w, h)`` to crop the table region.

    Returns:
        TableComplexity: :class:`TableComplexity` with grid estimates and complexity score."""
    return TableComplexityAnalyzer().analyze(image, bbox)
