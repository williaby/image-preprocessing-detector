"""
Layout-Lite Detection - Heuristics-Based Document Layout Analysis.

Implements fast classical CV methods for detecting layout features:
- Column detection (projection profile analysis)
- Table detection (Hough line + grid pattern)
- Figure detection (large components with low text density)
- Fuzzy scan detection (blur + noise estimation)
- Watermark detection (FFT low-frequency analysis)
- Colorful background detection (color histogram diversity)
"""

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


@dataclass
class ColumnDetectionResult:
    """
    Result of column detection analysis.

    Attributes:
        column_type: "single" / "multi" / "three_column" / "complex"
        confidence: Confidence score (0.0-1.0)
        num_columns: Estimated number of columns
        column_boundaries: List of x-coordinates marking column boundaries
    """

    column_type: str
    confidence: float
    num_columns: int
    column_boundaries: list[int]


@dataclass
class TableDetectionResult:
    """
    Result of table detection analysis.

    Attributes:
        has_tables: Whether tables are detected
        confidence: Confidence score (0.0-1.0)
        num_horizontal_lines: Number of horizontal lines detected
        num_vertical_lines: Number of vertical lines detected
        grid_score: Grid pattern strength score
    """

    has_tables: bool
    confidence: float
    num_horizontal_lines: int
    num_vertical_lines: int
    grid_score: float


@dataclass
class FigureDetectionResult:
    """
    Result of figure detection analysis.

    Attributes:
        has_figures: Whether figures are detected
        confidence: Confidence score (0.0-1.0)
        num_figures: Number of figure-like regions detected
        largest_figure_area_ratio: Ratio of largest figure to page area
    """

    has_figures: bool
    confidence: float
    num_figures: int
    largest_figure_area_ratio: float


@dataclass
class FuzzyScanDetectionResult:
    """
    Result of fuzzy scan detection analysis.

    Attributes:
        fuzzy_scan: Whether fuzzy scan is detected
        confidence: Confidence score (0.0-1.0)
        blur_score: Blur metric (Laplacian variance)
        noise_score: Noise estimation metric
    """

    fuzzy_scan: bool
    confidence: float
    blur_score: float
    noise_score: float


@dataclass
class WatermarkDetectionResult:
    """
    Result of watermark detection analysis.

    Attributes:
        watermark: Whether watermark is detected
        confidence: Confidence score (0.0-1.0)
        low_freq_energy: Low-frequency energy metric from FFT
        opacity_score: Estimated watermark opacity
    """

    watermark: bool
    confidence: float
    low_freq_energy: float
    opacity_score: float


@dataclass
class ColorfulBackgroundResult:
    """
    Result of colorful background detection analysis.

    Attributes:
        colorful_background: Whether colorful background is detected
        confidence: Confidence score (0.0-1.0)
        unique_colors: Number of unique colors
        avg_saturation: Average saturation in HSV space
    """

    colorful_background: bool
    confidence: float
    unique_colors: int
    avg_saturation: float


def detect_column_count(
    image: np.ndarray,
    min_column_gap: int = 30,
    min_column_width: int = 100,
) -> ColumnDetectionResult:
    """
    Detect column layout using projection profile analysis + connected component clustering.

    Algorithm:
    1. Convert to grayscale and binarize
    2. Compute horizontal projection profile (sum pixels along vertical axis)
    3. Find valleys (low-density regions) indicating column gaps
    4. Cluster valleys into column boundaries
    5. Classify as single/multi/three_column/complex

    Args:
        image: Input image (BGR format, from OpenCV)
        min_column_gap: Minimum gap width between columns in pixels (default: 30)
        min_column_width: Minimum column width in pixels (default: 100)

    Returns:
        ColumnDetectionResult with column type and boundaries

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running column detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Binarize with Otsu's method (invert so text is white)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Compute horizontal projection profile (sum along vertical axis)
    h_projection = np.sum(binary, axis=0)  # Shape: (width,)

    # Normalize projection
    h_projection = h_projection / (binary.shape[0] * 255.0)  # Normalize to 0-1

    # Find valleys (potential column gaps) using threshold
    valley_threshold = 0.05  # Less than 5% pixel density indicates gap
    valleys = h_projection < valley_threshold

    # Find continuous valley regions
    column_boundaries = []
    in_valley = False
    valley_start = 0

    for x in range(len(valleys)):
        if valleys[x] and not in_valley:
            # Start of valley
            in_valley = True
            valley_start = x
        elif not valleys[x] and in_valley:
            # End of valley
            valley_width = x - valley_start
            if valley_width >= min_column_gap:
                # Record valley center as column boundary
                boundary = valley_start + valley_width // 2
                column_boundaries.append(int(boundary))
            in_valley = False

    # Add edges as implicit boundaries
    all_boundaries = [0, *column_boundaries, binary.shape[1]]
    all_boundaries = sorted(set(all_boundaries))

    # Calculate column widths
    column_widths = []
    for i in range(len(all_boundaries) - 1):
        width = all_boundaries[i + 1] - all_boundaries[i]
        if width >= min_column_width:
            column_widths.append(width)

    num_columns = len(column_widths)

    # Classify column type
    if num_columns <= 1:
        column_type = "single"
        confidence = 0.9
    elif num_columns == 2:
        column_type = "multi"
        confidence = 0.85
    elif num_columns == 3:
        column_type = "three_column"
        confidence = 0.8
    else:
        column_type = "complex"
        confidence = 0.7

    logger.debug(
        "Column detection complete",
        column_type=column_type,
        num_columns=num_columns,
        confidence=confidence,
    )

    return ColumnDetectionResult(
        column_type=column_type,
        confidence=confidence,
        num_columns=num_columns,
        column_boundaries=column_boundaries,
    )


def detect_tables(
    image: np.ndarray,
    min_horizontal_lines: int = 10,
    min_vertical_lines: int = 5,
    grid_intersection_threshold: float = 0.3,
) -> TableDetectionResult:
    """
    Detect tables using Hough line detection + grid pattern analysis.

    Algorithm:
    1. Convert to grayscale and apply edge detection
    2. Detect horizontal and vertical lines using Hough Line Transform
    3. Count lines meeting minimum length criteria
    4. Calculate grid score based on line intersections
    5. Threshold: >10 horizontal AND >5 vertical lines forming grid

    Args:
        image: Input image (BGR format, from OpenCV)
        min_horizontal_lines: Minimum horizontal lines for table (default: 10)
        min_vertical_lines: Minimum vertical lines for table (default: 5)
        grid_intersection_threshold: Minimum intersection ratio for grid (default: 0.3)

    Returns:
        TableDetectionResult with detection decision and line counts

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running table detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect lines using Hough Line Transform
    # Use Probabilistic Hough Transform for line segments
    min_line_length = int(min(image.shape[:2]) * 0.1)  # 10% of smaller dimension
    max_line_gap = 10

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )

    if lines is None:
        logger.debug("No lines detected")
        return TableDetectionResult(
            has_tables=False,
            confidence=0.9,
            num_horizontal_lines=0,
            num_vertical_lines=0,
            grid_score=0.0,
        )

    # Classify lines as horizontal or vertical
    horizontal_lines = []
    vertical_lines = []

    angle_threshold = 10  # degrees tolerance for horizontal/vertical

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Calculate angle
        if x2 - x1 == 0:
            angle = 90.0  # Vertical
        else:
            angle = abs(np.degrees(np.arctan((y2 - y1) / (x2 - x1))))

        # Classify as horizontal (0°) or vertical (90°)
        if angle < angle_threshold:
            horizontal_lines.append(line[0])
        elif angle > (90 - angle_threshold):
            vertical_lines.append(line[0])

    num_horizontal = len(horizontal_lines)
    num_vertical = len(vertical_lines)

    # Calculate grid score based on intersection potential
    # Simplified: ratio of minimum(h_lines, v_lines) to maximum
    if num_horizontal > 0 and num_vertical > 0:
        grid_score = min(num_horizontal, num_vertical) / max(
            num_horizontal, num_vertical
        )
    else:
        grid_score = 0.0

    # Detection logic: sufficient lines AND good grid pattern
    has_tables = (
        num_horizontal >= min_horizontal_lines
        and num_vertical >= min_vertical_lines
        and grid_score >= grid_intersection_threshold
    )

    confidence = min(0.95, grid_score + 0.5) if has_tables else 0.8

    logger.debug(
        "Table detection complete",
        has_tables=has_tables,
        num_horizontal=num_horizontal,
        num_vertical=num_vertical,
        grid_score=grid_score,
    )

    return TableDetectionResult(
        has_tables=has_tables,
        confidence=confidence,
        num_horizontal_lines=num_horizontal,
        num_vertical_lines=num_vertical,
        grid_score=grid_score,
    )


def detect_figures(
    image: np.ndarray,
    min_figure_area_ratio: float = 0.20,
    max_text_density: float = 0.05,
) -> FigureDetectionResult:
    """
    Detect figures using large connected components with low text density.

    Algorithm:
    1. Convert to grayscale and binarize
    2. Find connected components
    3. Filter components by area (>20% of page area)
    4. Calculate text density within each component
    5. Classify as figure if text density <5%

    Args:
        image: Input image (BGR format, from OpenCV)
        min_figure_area_ratio: Minimum area ratio for figure (default: 0.20 = 20%)
        max_text_density: Maximum text density for figure (default: 0.05 = 5%)

    Returns:
        FigureDetectionResult with detection decision and figure count

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running figure detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Binarize with Otsu's method
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Calculate page area
    page_area = image.shape[0] * image.shape[1]
    min_area = int(page_area * min_figure_area_ratio)

    # Find connected components
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    figure_count = 0
    largest_figure_area = 0

    # Analyze each component (skip background label 0)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]

        # Check if component is large enough
        if area < min_area:
            continue

        # Extract component region
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        # Calculate text density in this region
        # Use morphological gradient to detect text strokes
        region = gray[y : y + h, x : x + w]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gradient = cv2.morphologyEx(region, cv2.MORPH_GRADIENT, kernel)

        text_pixels = np.count_nonzero(gradient > 30)
        region_pixels = region.size
        text_density = text_pixels / region_pixels if region_pixels > 0 else 1.0

        # Classify as figure if low text density
        if text_density < max_text_density:
            figure_count += 1
            largest_figure_area = max(largest_figure_area, area)

    has_figures = figure_count > 0
    largest_area_ratio = largest_figure_area / page_area if page_area > 0 else 0.0

    # Confidence based on number of figures and area
    confidence = min(0.9, 0.6 + (figure_count * 0.1))

    logger.debug(
        "Figure detection complete",
        has_figures=has_figures,
        figure_count=figure_count,
        largest_area_ratio=largest_area_ratio,
    )

    return FigureDetectionResult(
        has_figures=has_figures,
        confidence=confidence,
        num_figures=figure_count,
        largest_figure_area_ratio=largest_area_ratio,
    )


def detect_fuzzy_scan(
    image: np.ndarray,
    blur_threshold: float = 0.7,
    noise_threshold: float = 0.5,
) -> FuzzyScanDetectionResult:
    """
    Detect fuzzy scans using Laplacian variance + noise estimation.

    Algorithm:
    1. Calculate blur metric using Laplacian variance
    2. Estimate noise using high-frequency component analysis
    3. Normalize scores to 0-1 range
    4. Threshold: blur_score >0.7 AND noise_score >0.5

    Args:
        image: Input image (BGR format, from OpenCV)
        blur_threshold: Minimum blur score for fuzzy scan (default: 0.7)
        noise_threshold: Minimum noise score for fuzzy scan (default: 0.5)

    Returns:
        FuzzyScanDetectionResult with detection decision and scores

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running fuzzy scan detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate blur metric using Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_var = laplacian.var()

    # Normalize blur score (inverse: lower variance = more blur)
    # Typical range: sharp images have variance >500, blurry <100
    blur_score = 1.0 - min(1.0, laplacian_var / 500.0)

    # Estimate noise using high-frequency components
    # Apply high-pass filter (difference from Gaussian blur)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise_image = cv2.absdiff(gray, blurred)

    # Calculate noise metric as standard deviation of noise image
    noise_std = np.std(noise_image)

    # Normalize noise score
    # Typical range: clean images have std <10, noisy >30
    noise_score = min(1.0, noise_std / 30.0)

    # Detection logic: both blur and noise exceed thresholds
    fuzzy_scan = (blur_score > blur_threshold) and (noise_score > noise_threshold)

    # Confidence based on how far above thresholds
    confidence = min(0.95, (blur_score + noise_score) / 2.0) if fuzzy_scan else 0.85

    logger.debug(
        "Fuzzy scan detection complete",
        fuzzy_scan=fuzzy_scan,
        blur_score=blur_score,
        noise_score=noise_score,
    )

    return FuzzyScanDetectionResult(
        fuzzy_scan=fuzzy_scan,
        confidence=confidence,
        blur_score=blur_score,
        noise_score=noise_score,
    )


def detect_watermark(
    image: np.ndarray,
    low_freq_threshold: float = 0.15,
) -> WatermarkDetectionResult:
    """
    Detect watermarks using low-frequency component analysis (FFT) + opacity detection.

    Algorithm:
    1. Convert to grayscale
    2. Apply 2D Fourier Transform (FFT)
    3. Analyze low-frequency energy (center of frequency spectrum)
    4. Calculate opacity score from intensity variations
    5. Threshold: low-frequency energy >threshold

    Args:
        image: Input image (BGR format, from OpenCV)
        low_freq_threshold: Minimum low-frequency energy for watermark (default: 0.15)

    Returns:
        WatermarkDetectionResult with detection decision and metrics

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running watermark detection", image_shape=image.shape)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply 2D FFT
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)

    # Calculate magnitude spectrum
    magnitude_spectrum = np.abs(f_shift)

    # Analyze low-frequency components (center region)
    h, w = magnitude_spectrum.shape
    center_size = min(h, w) // 10  # 10% of dimension

    center_y, center_x = h // 2, w // 2
    low_freq_region = magnitude_spectrum[
        center_y - center_size : center_y + center_size,
        center_x - center_size : center_x + center_size,
    ]

    # Calculate low-frequency energy as ratio to total energy
    low_freq_energy = np.sum(low_freq_region) / np.sum(magnitude_spectrum)

    # Calculate opacity score from intensity variations
    # Watermarks typically have semi-transparent, uniform intensity
    gray_std = np.std(gray)
    opacity_score = 1.0 - min(1.0, gray_std / 50.0)  # Normalize

    # Detection logic: high low-frequency energy indicates watermark
    watermark = low_freq_energy > low_freq_threshold

    # Confidence based on energy level and opacity
    confidence = min(0.9, low_freq_energy * 3.0) if watermark else 0.85

    logger.debug(
        "Watermark detection complete",
        watermark=watermark,
        low_freq_energy=low_freq_energy,
        opacity_score=opacity_score,
    )

    return WatermarkDetectionResult(
        watermark=watermark,
        confidence=confidence,
        low_freq_energy=low_freq_energy,
        opacity_score=opacity_score,
    )


def detect_colorful_background(
    image: np.ndarray,
    min_unique_colors: int = 100,
    min_avg_saturation: float = 0.3,
) -> ColorfulBackgroundResult:
    """
    Detect colorful backgrounds using color histogram diversity + saturation analysis.

    Algorithm:
    1. Convert to HSV color space
    2. Calculate unique colors (histogram bins with significant counts)
    3. Calculate average saturation
    4. Threshold: unique_colors >100 AND avg_saturation >0.3

    Args:
        image: Input image (BGR format, from OpenCV)
        min_unique_colors: Minimum unique colors for colorful background (default: 100)
        min_avg_saturation: Minimum average saturation (default: 0.3)

    Returns:
        ColorfulBackgroundResult with detection decision and metrics

    Raises:
        ValueError: If image is invalid or empty
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided")

    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image.shape}")

    logger.debug("Running colorful background detection", image_shape=image.shape)

    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Calculate average saturation
    saturation_channel = hsv[:, :, 1]
    avg_saturation = np.mean(saturation_channel) / 255.0  # Normalize to 0-1

    # Calculate unique colors using 3D histogram
    # Reduce resolution to count "perceptually unique" colors
    h_bins = 16
    s_bins = 8
    v_bins = 8

    hist = cv2.calcHist(
        [hsv],
        [0, 1, 2],
        None,
        [h_bins, s_bins, v_bins],
        [0, 180, 0, 256, 0, 256],
    )

    # Count bins with significant pixel counts (>0.1% of total pixels)
    total_pixels = image.shape[0] * image.shape[1]
    significant_threshold = total_pixels * 0.001

    unique_colors = np.count_nonzero(hist > significant_threshold)

    # Detection logic: diverse colors AND high saturation
    colorful_background = (
        unique_colors >= min_unique_colors and avg_saturation >= min_avg_saturation
    )

    # Confidence based on both metrics
    confidence = (
        min(0.95, (unique_colors / min_unique_colors + avg_saturation) / 2.0)
        if colorful_background
        else 0.85
    )

    logger.debug(
        "Colorful background detection complete",
        colorful_background=colorful_background,
        unique_colors=unique_colors,
        avg_saturation=avg_saturation,
    )

    return ColorfulBackgroundResult(
        colorful_background=colorful_background,
        confidence=confidence,
        unique_colors=unique_colors,
        avg_saturation=avg_saturation,
    )


class LayoutLiteAnalyzer:
    """
    Combines all layout-lite detection functions into unified analyzer.

    Runs all heuristic-based detections and populates PageLayoutSummary model.
    Optimized for speed (< 100ms per page on CPU).
    """

    def __init__(
        self,
        enable_column_detection: bool = True,
        enable_table_detection: bool = True,
        enable_figure_detection: bool = True,
        enable_fuzzy_scan_detection: bool = True,
        enable_watermark_detection: bool = True,
        enable_colorful_bg_detection: bool = True,
    ) -> None:
        """
        Initialize layout-lite analyzer.

        Args:
            enable_column_detection: Enable column detection (default: True)
            enable_table_detection: Enable table detection (default: True)
            enable_figure_detection: Enable figure detection (default: True)
            enable_fuzzy_scan_detection: Enable fuzzy scan detection (default: True)
            enable_watermark_detection: Enable watermark detection (default: True)
            enable_colorful_bg_detection: Enable colorful background detection (default: True)
        """
        self.enable_column_detection = enable_column_detection
        self.enable_table_detection = enable_table_detection
        self.enable_figure_detection = enable_figure_detection
        self.enable_fuzzy_scan_detection = enable_fuzzy_scan_detection
        self.enable_watermark_detection = enable_watermark_detection
        self.enable_colorful_bg_detection = enable_colorful_bg_detection

        logger.info(
            "LayoutLiteAnalyzer initialized",
            column=enable_column_detection,
            table=enable_table_detection,
            figure=enable_figure_detection,
            fuzzy=enable_fuzzy_scan_detection,
            watermark=enable_watermark_detection,
            colorful_bg=enable_colorful_bg_detection,
        )

    def analyze(self, image: np.ndarray) -> dict[str, Any]:
        """
        Run all enabled detections on an image.

        Args:
            image: Input image (BGR format, from OpenCV)

        Returns:
            Dictionary with all detection results

        Raises:
            ValueError: If image is invalid or empty
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided")

        logger.debug("Starting layout-lite analysis", image_shape=image.shape)

        results: dict[str, Any] = {}

        # Run column detection
        if self.enable_column_detection:
            results["column"] = detect_column_count(image)

        # Run table detection
        if self.enable_table_detection:
            results["table"] = detect_tables(image)

        # Run figure detection
        if self.enable_figure_detection:
            results["figure"] = detect_figures(image)

        # Run fuzzy scan detection
        if self.enable_fuzzy_scan_detection:
            results["fuzzy_scan"] = detect_fuzzy_scan(image)

        # Run watermark detection
        if self.enable_watermark_detection:
            results["watermark"] = detect_watermark(image)

        # Run colorful background detection
        if self.enable_colorful_bg_detection:
            results["colorful_background"] = detect_colorful_background(image)

        logger.info("Layout-lite analysis complete", num_detections=len(results))

        return results


# Convenience function for quick analysis
def analyze_layout(image: np.ndarray) -> dict[str, Any]:
    """
    Convenience function for layout analysis with default settings.

    Args:
        image: Input image (BGR format, from OpenCV)

    Returns:
        Dictionary with all detection results

    Example:
        >>> import cv2
        >>> img = cv2.imread("document.jpg")
        >>> results = analyze_layout(img)
        >>> print(f"Column type: {results['column'].column_type}")
        >>> print(f"Has tables: {results['table'].has_tables}")
    """
    analyzer = LayoutLiteAnalyzer()
    return analyzer.analyze(image)
