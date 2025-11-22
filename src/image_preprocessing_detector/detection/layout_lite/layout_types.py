"""Data types for layout-lite detection results."""

from dataclasses import dataclass


@dataclass
class ColumnDetectionResult:
    """Result of column detection analysis.

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
    """Result of table detection analysis.

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
    """Result of figure detection analysis.

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
    """Result of fuzzy scan detection analysis.

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
    """Result of watermark detection analysis.

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
    """Result of colorful background detection analysis.

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
