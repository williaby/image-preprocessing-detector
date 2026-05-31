"""Data types for layout-lite detection results."""

from dataclasses import dataclass


@dataclass
class ColumnDetectionResult:
    """Result of column detection analysis.

    Attributes:
        column_type (str): "single" / "multi" / "three_column" / "complex"
        confidence (float): Confidence score (0.0-1.0)
        num_columns (int): Estimated number of columns
        column_boundaries (list[int]): List of x-coordinates marking column boundaries
    """

    column_type: str
    confidence: float
    num_columns: int
    column_boundaries: list[int]


@dataclass
class TableDetectionResult:
    """Result of table detection analysis.

    Attributes:
        has_tables (bool): Whether tables are detected
        confidence (float): Confidence score (0.0-1.0)
        num_horizontal_lines (int): Number of horizontal lines detected
        num_vertical_lines (int): Number of vertical lines detected
        grid_score (float): Grid pattern strength score
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
        has_figures (bool): Whether figures are detected
        confidence (float): Confidence score (0.0-1.0)
        num_figures (int): Number of figure-like regions detected
        largest_figure_area_ratio (float): Ratio of largest figure to page area
    """

    has_figures: bool
    confidence: float
    num_figures: int
    largest_figure_area_ratio: float


@dataclass
class FuzzyScanDetectionResult:
    """Result of fuzzy scan detection analysis.

    Attributes:
        fuzzy_scan (bool): Whether fuzzy scan is detected
        confidence (float): Confidence score (0.0-1.0)
        blur_score (float): Blur metric (Laplacian variance)
        noise_score (float): Noise estimation metric
    """

    fuzzy_scan: bool
    confidence: float
    blur_score: float
    noise_score: float


@dataclass
class WatermarkDetectionResult:
    """Result of watermark detection analysis.

    Attributes:
        watermark (bool): Whether watermark is detected
        confidence (float): Confidence score (0.0-1.0)
        low_freq_energy (float): Low-frequency energy metric from FFT
        opacity_score (float): Estimated watermark opacity
    """

    watermark: bool
    confidence: float
    low_freq_energy: float
    opacity_score: float


@dataclass
class ColorfulBackgroundResult:
    """Result of colorful background detection analysis.

    Attributes:
        colorful_background (bool): Whether colorful background is detected
        confidence (float): Confidence score (0.0-1.0)
        unique_colors (int): Number of unique colors
        avg_saturation (float): Average saturation in HSV space
    """

    colorful_background: bool
    confidence: float
    unique_colors: int
    avg_saturation: float
