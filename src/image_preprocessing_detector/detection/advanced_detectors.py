# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Advanced detection features for Phase D implementation.

These are deferred features that extend detection capabilities:
- FR-3.12: Warping/Curvature Detection (book scans)
- FR-3.13: Perspective Distortion Detection (mobile captures)
- FR-5.1: Formula Detection (STEM documents)
- FR-5.5/5.6: Signature/Stamp Detection (legal documents)
- FR-5.3: Language Detection
- FR-4.7: Vertical Text Orientation (CJK documents)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.iqa_classical import Severity
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# Common Helper Functions (reduces cyclomatic complexity)
# ============================================================================


def _validate_and_preprocess(
    image: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Validate image and return grayscale + binary versions.

    Args:
        image: Input image (BGR, BGRA, or grayscale)

    Returns:
        Tuple of (grayscale, binary, height, width)

    Raises:
        ValueError: If image is invalid
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image")

    h, w = image.shape[:2]

    # Handle grayscale, 3-channel (BGR), and 4-channel (BGRA/RGBA) images
    if len(image.shape) == 2:
        gray = image
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    return gray, binary, h, w


def _get_filtered_components(
    binary: np.ndarray,
    h: int,
    w: int,
    min_area: int = 20,
    min_size: int = 5,
) -> list[dict[str, Any]]:
    """Get connected components filtered by size.

    Args:
        binary: Binary image
        h: Image height
        w: Image width
        min_area: Minimum component area
        min_size: Minimum component width/height

    Returns:
        List of component dictionaries with bbox, area, centroid, aspect_ratio
    """
    num_labels, _labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    components = []
    for i in range(1, num_labels):  # Skip background
        x, y, comp_w, comp_h, area = stats[i]
        if (
            comp_w > min_size
            and comp_h > min_size
            and comp_w < w // 3
            and comp_h < h // 3
            and area > min_area
        ):
            components.append(
                {
                    "bbox": (x, y, comp_w, comp_h),
                    "area": area,
                    "centroid": centroids[i],
                    "aspect_ratio": comp_w / comp_h if comp_h > 0 else 0,
                    "density": area / (comp_w * comp_h) if comp_w * comp_h > 0 else 0,
                }
            )

    return components


# ============================================================================
# Warping/Curvature Detection (FR-3.12)
# ============================================================================


@dataclass
class WarpingResult:
    """Result of warping/curvature detection."""

    is_warped: bool
    severity: Severity
    curvature_score: float  # 0-1, higher = more curvature
    estimated_curvature_angle: float  # degrees
    confidence: float
    metrics: dict[str, Any]


def detect_warping(image: np.ndarray) -> WarpingResult:
    """Detect warping/curvature in scanned book pages.

    Uses horizontal line analysis to detect page curvature typical
    in book scans where pages curve near the spine.

    Args:
        image: Input image (BGR format)

    Returns:
        WarpingResult with curvature metrics
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image")

    h, w = image.shape[:2]
    lines = _detect_hough_lines(image, w)

    if lines is None or len(lines) < 5:
        return _create_no_warping_result(lines_detected=0)

    horizontal_lines = _filter_horizontal_lines(lines)
    if len(horizontal_lines) < 5:
        return _create_no_warping_result(horizontal_lines=len(horizontal_lines))

    # Calculate curvature metrics
    curvature_score, estimated_angle, y_variance, max_deviation = (
        _calculate_curvature_metrics(horizontal_lines, h)
    )

    # Determine severity and warping status
    severity, is_warped = _classify_warping_severity(curvature_score)

    logger.debug(
        "Warping detection complete",
        is_warped=is_warped,
        curvature_score=curvature_score,
        estimated_angle=estimated_angle,
    )

    return WarpingResult(
        is_warped=is_warped,
        severity=severity,
        curvature_score=curvature_score,
        estimated_curvature_angle=estimated_angle,
        confidence=0.7 if len(horizontal_lines) > 10 else 0.5,
        metrics={
            "horizontal_lines": len(horizontal_lines),
            "y_variance": y_variance,
            "max_deviation": max_deviation,
        },
    )


def _detect_hough_lines(image: np.ndarray, width: int) -> np.ndarray | None:
    """Detect lines in image using Hough Transform."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    return cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=width // 4,
        maxLineGap=10,
    )


def _filter_horizontal_lines(lines: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Filter for nearly horizontal lines (angle < 10 degrees)."""
    horizontal = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        if angle < 10:
            horizontal.append(line[0])
    return horizontal


def _calculate_curvature_metrics(
    horizontal_lines: list[tuple[int, int, int, int]], image_height: int
) -> tuple[float, float, float, float]:
    """Calculate curvature score and related metrics."""
    # Y-position variance of line centers
    y_centers = [(y1 + y2) / 2 for x1, y1, x2, y2 in horizontal_lines]
    y_variance = float(np.std(y_centers) / image_height) if y_centers else 0.0

    # Maximum line deviation (curvature indicator)
    max_deviation = 0.0
    for x1, y1, x2, y2 in horizontal_lines:
        line_length = float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
        if line_length > 0:
            deviation = abs(y2 - y1) / line_length
            max_deviation = max(max_deviation, deviation)

    curvature_score = min(1.0, y_variance * 10 + max_deviation)
    estimated_angle = float(np.arctan(max_deviation) * 180 / np.pi)

    return curvature_score, estimated_angle, y_variance, max_deviation


def _classify_warping_severity(curvature_score: float) -> tuple[Severity, bool]:
    """Classify warping severity based on curvature score."""
    if curvature_score < 0.1:
        return Severity.LOW, False
    if curvature_score < 0.2:
        return Severity.MEDIUM, True
    if curvature_score < 0.4:
        return Severity.HIGH, True
    return Severity.CRITICAL, True


def _create_no_warping_result(**metrics: Any) -> WarpingResult:
    """Create result for non-warped image."""
    return WarpingResult(
        is_warped=False,
        severity=Severity.LOW,
        curvature_score=0.0,
        estimated_curvature_angle=0.0,
        confidence=0.5,
        metrics=metrics,
    )


# ============================================================================
# Perspective Distortion Detection (FR-3.13)
# ============================================================================


@dataclass
class PerspectiveResult:
    """Result of perspective distortion detection."""

    has_perspective: bool
    severity: Severity
    distortion_score: float  # 0-1
    estimated_angles: tuple[float, float]  # (horizontal_tilt, vertical_tilt) degrees
    confidence: float
    corners: list[tuple[int, int]] | None  # Detected document corners


def detect_perspective(image: np.ndarray) -> PerspectiveResult:
    """Detect perspective distortion from mobile captures.

    Analyzes document edges to detect if the image was captured
    at an angle, causing trapezoidal distortion.

    Args:
        image: Input image (BGR format)

    Returns:
        PerspectiveResult with distortion metrics
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image")

    h, w = image.shape[:2]

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Apply bilateral filter to reduce noise while keeping edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)

    # Edge detection
    edges = cv2.Canny(filtered, 30, 100)

    # Dilate edges to connect gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return PerspectiveResult(
            has_perspective=False,
            severity=Severity.LOW,
            distortion_score=0.0,
            estimated_angles=(0.0, 0.0),
            confidence=0.3,
            corners=None,
        )

    # Find largest contour (likely the document)
    largest_contour = max(contours, key=cv2.contourArea)
    contour_area = cv2.contourArea(largest_contour)

    # If contour is too small, likely not a document
    if contour_area < (h * w * 0.1):
        return PerspectiveResult(
            has_perspective=False,
            severity=Severity.LOW,
            distortion_score=0.0,
            estimated_angles=(0.0, 0.0),
            confidence=0.3,
            corners=None,
        )

    # Approximate contour to polygon
    epsilon = 0.02 * cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)

    # Check if we have a quadrilateral (document shape)
    if len(approx) != 4:
        return PerspectiveResult(
            has_perspective=False,
            severity=Severity.LOW,
            distortion_score=0.0,
            estimated_angles=(0.0, 0.0),
            confidence=0.4,
            corners=None,
        )

    # Extract corners
    corners = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]

    # Sort corners: top-left, top-right, bottom-right, bottom-left
    corners = sorted(corners, key=lambda x: x[1])  # Sort by y
    top_corners = sorted(corners[:2], key=lambda x: x[0])
    bottom_corners = sorted(corners[2:], key=lambda x: x[0])
    corners = [top_corners[0], top_corners[1], bottom_corners[1], bottom_corners[0]]

    # Calculate perspective distortion
    # For a perfect rectangle: top edge = bottom edge, left edge = right edge
    top_edge = np.sqrt(
        (corners[1][0] - corners[0][0]) ** 2 + (corners[1][1] - corners[0][1]) ** 2
    )
    bottom_edge = np.sqrt(
        (corners[2][0] - corners[3][0]) ** 2 + (corners[2][1] - corners[3][1]) ** 2
    )
    left_edge = np.sqrt(
        (corners[3][0] - corners[0][0]) ** 2 + (corners[3][1] - corners[0][1]) ** 2
    )
    right_edge = np.sqrt(
        (corners[2][0] - corners[1][0]) ** 2 + (corners[2][1] - corners[1][1]) ** 2
    )

    # Calculate distortion ratios
    h_ratio = (
        min(top_edge, bottom_edge) / max(top_edge, bottom_edge)
        if max(top_edge, bottom_edge) > 0
        else 1
    )
    v_ratio = (
        min(left_edge, right_edge) / max(left_edge, right_edge)
        if max(left_edge, right_edge) > 0
        else 1
    )

    distortion_score = 1.0 - (h_ratio * v_ratio)

    # Estimate tilt angles
    h_tilt = np.arccos(h_ratio) * 180 / np.pi if h_ratio <= 1 else 0
    v_tilt = np.arccos(v_ratio) * 180 / np.pi if v_ratio <= 1 else 0

    # Determine severity
    if distortion_score < 0.05:
        severity = Severity.LOW
        has_perspective = False
    elif distortion_score < 0.15:
        severity = Severity.MEDIUM
        has_perspective = True
    elif distortion_score < 0.3:
        severity = Severity.HIGH
        has_perspective = True
    else:
        severity = Severity.CRITICAL
        has_perspective = True

    logger.debug(
        "Perspective detection complete",
        has_perspective=has_perspective,
        distortion_score=distortion_score,
        h_tilt=h_tilt,
        v_tilt=v_tilt,
    )

    return PerspectiveResult(
        has_perspective=has_perspective,
        severity=severity,
        distortion_score=distortion_score,
        estimated_angles=(h_tilt, v_tilt),
        confidence=0.75,
        corners=corners,
    )


# ============================================================================
# Formula Detection (FR-5.1)
# ============================================================================


@dataclass
class FormulaResult:
    """Result of mathematical formula detection."""

    has_formulas: bool
    formula_density: float  # 0-1
    formula_count: int
    regions: list[tuple[int, int, int, int]]  # Bounding boxes [x, y, w, h]
    confidence: float


def _empty_formula_result(confidence: float = 0.5) -> FormulaResult:
    """Return empty formula result for edge cases."""
    return FormulaResult(
        has_formulas=False,
        formula_density=0.0,
        formula_count=0,
        regions=[],
        confidence=confidence,
    )


def _count_formula_indicators(components: list[dict[str, Any]], h: int) -> int:
    """Count formula indicators from component analysis.

    Checks for:
    - Unusual aspect ratios (subscripts, superscripts, operators)
    - High vertical position variance (multi-level text)
    """
    indicators = 0

    # Analyze aspect ratio distribution
    aspect_ratios = [c["aspect_ratio"] for c in components]
    unusual_aspects = sum(1 for ar in aspect_ratios if ar < 0.5 or ar > 2.0)
    if unusual_aspects / len(components) > 0.2:
        indicators += 1

    # Check for vertical positioning variations
    y_positions = [c["centroid"][1] for c in components]
    y_variance = np.std(y_positions) / h if y_positions else 0
    if y_variance > 0.1:
        indicators += 1

    return indicators


def _find_high_density_regions(
    components: list[dict[str, Any]], h: int, w: int, grid_size: int = 50
) -> list[tuple[int, int, int, int]]:
    """Find high-density component regions using grid analysis."""
    grid_h = (h + grid_size - 1) // grid_size
    grid_w = (w + grid_size - 1) // grid_size
    density_grid = np.zeros((grid_h, grid_w))

    for comp in components:
        cx, cy = int(comp["centroid"][0]), int(comp["centroid"][1])
        gx = min(cx // grid_size, grid_w - 1)
        gy = min(cy // grid_size, grid_h - 1)
        density_grid[gy, gx] += 1

    # Find high-density regions (75th percentile threshold)
    threshold = (
        np.percentile(density_grid[density_grid > 0], 75)
        if np.any(density_grid > 0)
        else 1
    )
    high_density_cells = np.argwhere(density_grid >= threshold)

    return [
        (gx * grid_size, gy * grid_size, grid_size, grid_size)
        for gy, gx in high_density_cells
    ]


def detect_formulas(image: np.ndarray) -> FormulaResult:
    """Detect mathematical formulas in STEM documents.

    Uses heuristics to identify regions likely containing math:
    - High density of special characters
    - Subscripts/superscripts patterns
    - Unusual character spacing

    Note: This is a heuristic approach. For production use,
    consider integrating with a dedicated formula detection model.

    Args:
        image: Input image (BGR format)

    Returns:
        FormulaResult with detected formula regions
    """
    # Preprocess image
    _gray, binary, h, w = _validate_and_preprocess(image)

    # Get filtered components
    components = _get_filtered_components(binary, h, w, min_area=20, min_size=5)

    if len(components) < 5:
        return _empty_formula_result()

    # Analyze formula indicators
    formula_indicators = _count_formula_indicators(components, h)

    # Find formula regions
    formula_regions = _find_high_density_regions(components, h, w)

    # Calculate formula density
    formula_area = sum(reg[2] * reg[3] for reg in formula_regions)
    formula_density = formula_area / (h * w) if h * w > 0 else 0

    has_formulas = formula_indicators >= 1 and formula_density > 0.05

    logger.debug(
        "Formula detection complete",
        has_formulas=has_formulas,
        formula_count=len(formula_regions),
        formula_density=formula_density,
    )

    return FormulaResult(
        has_formulas=has_formulas,
        formula_density=formula_density,
        formula_count=len(formula_regions),
        regions=formula_regions,
        confidence=0.6 if formula_indicators >= 2 else 0.4,
    )


# ============================================================================
# Signature/Stamp Detection (FR-5.5/5.6)
# ============================================================================


@dataclass
class SignatureStampResult:
    """Result of signature and stamp detection."""

    has_signature: bool
    has_stamp: bool
    signature_regions: list[tuple[int, int, int, int]]
    stamp_regions: list[tuple[int, int, int, int]]
    confidence: float


def detect_signature_stamp(image: np.ndarray) -> SignatureStampResult:
    """Detect signatures and stamps in legal documents.

    Signatures: Characterized by cursive, connected strokes
    Stamps: Circular or rectangular regions with uniform patterns

    Args:
        image: Input image (BGR format)

    Returns:
        SignatureStampResult with detected regions
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image")

    h, w = image.shape[:2]
    contours = _extract_contours(image)

    signature_regions = []
    stamp_regions = []

    for contour in contours:
        if not _is_valid_region_size(contour, h, w):
            continue

        region = _analyze_contour(contour, h)
        if region.is_signature:
            signature_regions.append(region.bbox)
        if region.is_stamp:
            stamp_regions.append(region.bbox)

    logger.debug(
        "Signature/stamp detection complete",
        signatures=len(signature_regions),
        stamps=len(stamp_regions),
    )

    return SignatureStampResult(
        has_signature=len(signature_regions) > 0,
        has_stamp=len(stamp_regions) > 0,
        signature_regions=signature_regions,
        stamp_regions=stamp_regions,
        confidence=0.5,  # Heuristic-based, moderate confidence
    )


def _extract_contours(image: np.ndarray) -> list[np.ndarray]:
    """Extract contours from image."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return list(contours)


def _is_valid_region_size(contour: np.ndarray, h: int, w: int) -> bool:
    """Check if contour area is within valid range."""
    area = cv2.contourArea(contour)
    return bool(500 <= area <= (h * w * 0.3))


@dataclass
class _RegionAnalysis:
    """Internal class for region analysis results."""

    bbox: tuple[int, int, int, int]
    is_signature: bool
    is_stamp: bool


def _analyze_contour(contour: np.ndarray, image_height: int) -> _RegionAnalysis:
    """Analyze contour to determine if it's a signature or stamp."""
    x, y, cont_w, cont_h = cv2.boundingRect(contour)
    area = cv2.contourArea(contour)
    aspect = cont_w / cont_h if cont_h > 0 else 0
    perimeter = cv2.arcLength(contour, True)
    circularity = (4 * np.pi * area) / (perimeter**2) if perimeter > 0 else 0

    # Check signature heuristics
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    fill_ratio = area / hull_area if hull_area > 0 else 0
    is_signature = 2.0 < aspect < 8.0 and fill_ratio < 0.5

    # Check stamp heuristics (circular/square shape in bottom half)
    is_circular_or_square = 0.5 < circularity < 1.0 or (
        0.8 < aspect < 1.2 and area > 1000
    )
    is_in_stamp_position = y > image_height * 0.5
    is_stamp = is_circular_or_square and is_in_stamp_position

    return _RegionAnalysis(
        bbox=(x, y, cont_w, cont_h), is_signature=is_signature, is_stamp=is_stamp
    )


# ============================================================================
# Language Detection (FR-5.3)
# ============================================================================


class ScriptType(Enum):
    """Detected script/writing system."""

    LATIN = "latin"
    CJK = "cjk"  # Chinese, Japanese, Korean
    ARABIC = "arabic"
    CYRILLIC = "cyrillic"
    DEVANAGARI = "devanagari"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class LanguageResult:
    """Result of language/script detection."""

    primary_script: ScriptType
    scripts_detected: list[ScriptType]
    is_rtl: bool  # Right-to-left text
    confidence: float


def _unknown_language_result(confidence: float = 0.3) -> LanguageResult:
    """Return unknown language result for edge cases."""
    return LanguageResult(
        primary_script=ScriptType.UNKNOWN,
        scripts_detected=[ScriptType.UNKNOWN],
        is_rtl=False,
        confidence=confidence,
    )


def _classify_scripts(
    avg_aspect: float, avg_density: float, aspect_variance: float
) -> list[ScriptType]:
    """Classify scripts based on component statistics.

    Script detection heuristics:
    - CJK: Square characters (aspect ~1), high density
    - Latin: Varied aspect ratios, moderate density
    - Arabic: Connected scripts, high variance
    """
    scripts: list[ScriptType] = []

    # CJK detection: Square characters with high density
    if 0.7 < avg_aspect < 1.3 and avg_density > 0.3:
        scripts.append(ScriptType.CJK)

    # Latin detection: Varied characters
    if 0.3 < avg_aspect < 3.0 and aspect_variance > 0.3:
        scripts.append(ScriptType.LATIN)

    # Arabic/RTL detection: Connected text, specific patterns
    if aspect_variance > 0.5 and avg_density > 0.4:
        scripts.append(ScriptType.ARABIC)

    return scripts if scripts else [ScriptType.UNKNOWN]


def detect_language_script(image: np.ndarray) -> LanguageResult:
    """Detect language script from visual features.

    Uses character shape analysis to identify the writing system.
    Note: This is visual-only detection. For accurate language ID,
    use OCR output with a language classification model.

    Args:
        image: Input image (BGR format)

    Returns:
        LanguageResult with detected script information
    """
    # Preprocess image
    _gray, binary, h, w = _validate_and_preprocess(image)

    # Get filtered components (need at least 10 for reliable detection)
    components = _get_filtered_components(binary, h, w, min_area=20, min_size=3)

    if len(components) < 10:
        return _unknown_language_result()

    # Calculate statistics
    aspects = [c["aspect_ratio"] for c in components]
    densities = [c["density"] for c in components]

    avg_aspect = float(np.mean(aspects))
    avg_density = float(np.mean(densities))
    aspect_variance = float(np.std(aspects))

    # Classify scripts based on statistics
    scripts_detected = _classify_scripts(avg_aspect, avg_density, aspect_variance)

    # Determine primary script
    primary_script = (
        scripts_detected[0] if len(scripts_detected) == 1 else ScriptType.MIXED
    )
    is_rtl = ScriptType.ARABIC in scripts_detected

    logger.debug(
        "Language script detection complete",
        primary_script=primary_script.value,
        scripts=len(scripts_detected),
    )

    return LanguageResult(
        primary_script=primary_script,
        scripts_detected=scripts_detected,
        is_rtl=is_rtl,
        confidence=0.5,  # Visual heuristics only
    )


# ============================================================================
# Vertical Text Orientation Detection (FR-4.7)
# ============================================================================


class TextOrientation(Enum):
    """Detected text orientation."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class OrientationResult:
    """Result of text orientation detection."""

    orientation: TextOrientation
    vertical_ratio: float  # 0-1, ratio of vertical text
    confidence: float
    dominant_angle: float  # degrees (0=horizontal, 90=vertical)


def detect_text_orientation(image: np.ndarray) -> OrientationResult:
    """Detect text orientation for CJK documents.

    CJK documents may have vertical text (top-to-bottom) which
    affects OCR and reading order.

    Args:
        image: Input image (BGR format)

    Returns:
        OrientationResult with orientation information
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image")

    h, w = image.shape[:2]

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)

    # Detect lines using probabilistic Hough transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=30,
        maxLineGap=10,
    )

    if lines is None or len(lines) < 5:
        return OrientationResult(
            orientation=TextOrientation.UNKNOWN,
            vertical_ratio=0.0,
            confidence=0.3,
            dominant_angle=0.0,
        )

    # Classify lines by angle
    horizontal_lines = 0
    vertical_lines = 0
    angles = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        angles.append(angle)

        if angle < 30:
            horizontal_lines += 1
        elif angle > 60:
            vertical_lines += 1

    total_classified = horizontal_lines + vertical_lines
    if total_classified == 0:
        return OrientationResult(
            orientation=TextOrientation.UNKNOWN,
            vertical_ratio=0.0,
            confidence=0.3,
            dominant_angle=float(np.mean(angles)) if angles else 0.0,
        )

    vertical_ratio = vertical_lines / total_classified
    dominant_angle = float(np.mean(angles))

    # Determine orientation
    if vertical_ratio < 0.2:
        orientation = TextOrientation.HORIZONTAL
    elif vertical_ratio > 0.8:
        orientation = TextOrientation.VERTICAL
    else:
        orientation = TextOrientation.MIXED

    confidence = 0.7 if total_classified > 20 else 0.5

    logger.debug(
        "Text orientation detection complete",
        orientation=orientation.value,
        vertical_ratio=vertical_ratio,
        dominant_angle=dominant_angle,
    )

    return OrientationResult(
        orientation=orientation,
        vertical_ratio=vertical_ratio,
        confidence=confidence,
        dominant_angle=dominant_angle,
    )
