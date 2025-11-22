"""Layout-Lite Detection - Heuristics-Based Document Layout Analysis.

Implements fast classical CV methods for detecting layout features:
- Column detection (projection profile analysis)
- Table detection (Hough line + grid pattern)
- Figure detection (large components with low text density)
- Fuzzy scan detection (blur + noise estimation)
- Watermark detection (FFT low-frequency analysis)
- Colorful background detection (color histogram diversity)
"""

# Export all result types
# Export constants (for advanced users who need to override defaults)
from image_preprocessing_detector.detection.layout_lite import constants

# Export analyzer
from image_preprocessing_detector.detection.layout_lite.analyzer import (
    LayoutLiteAnalyzer,
    analyze_layout,
)

# Export detection functions
from image_preprocessing_detector.detection.layout_lite.background_detector import (
    detect_colorful_background,
)
from image_preprocessing_detector.detection.layout_lite.column_detector import (
    detect_column_count,
)
from image_preprocessing_detector.detection.layout_lite.figure_detector import (
    detect_figures,
)
from image_preprocessing_detector.detection.layout_lite.fuzzy_scan_detector import (
    detect_fuzzy_scan,
)
from image_preprocessing_detector.detection.layout_lite.layout_types import (
    ColorfulBackgroundResult,
    ColumnDetectionResult,
    FigureDetectionResult,
    FuzzyScanDetectionResult,
    TableDetectionResult,
    WatermarkDetectionResult,
)
from image_preprocessing_detector.detection.layout_lite.table_detector import (
    detect_tables,
)
from image_preprocessing_detector.detection.layout_lite.watermark_detector import (
    detect_watermark,
)

__all__ = [
    # Types
    "ColorfulBackgroundResult",
    "ColumnDetectionResult",
    "FigureDetectionResult",
    "FuzzyScanDetectionResult",
    # Analyzer
    "LayoutLiteAnalyzer",
    "TableDetectionResult",
    "WatermarkDetectionResult",
    "analyze_layout",
    # Constants module (for advanced configuration)
    "constants",
    # Detection functions
    "detect_colorful_background",
    "detect_column_count",
    "detect_figures",
    "detect_fuzzy_scan",
    "detect_tables",
    "detect_watermark",
]
