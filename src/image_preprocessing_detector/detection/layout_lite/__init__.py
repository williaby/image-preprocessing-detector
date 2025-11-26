"""Layout-Lite Detection - Hybrid ML + Heuristics Document Layout Analysis.

Phase 6 Implementation combining:
- DocLayout-YOLO ML detection (tables, figures, formulas, text blocks)
- Heuristic-based detection for quality attributes

Heuristic detectors (classical CV methods):
- Column detection (projection profile analysis)
- Table detection (Hough line + grid pattern)
- Figure detection (large components with low text density)
- Fuzzy scan detection (blur + noise estimation)
- Watermark detection (FFT low-frequency analysis)
- Colorful background detection (color histogram diversity)

ML-based detection (DocLayout-YOLO):
- Document element detection (10 DocStructBench classes)
- Structural complexity scoring
- Layout type inference

Usage:
    # Heuristic-only analysis (fast, no ML dependencies)
    >>> from image_preprocessing_detector.detection.layout_lite import analyze_layout
    >>> results = analyze_layout(image)

    # Hybrid ML + heuristic analysis (recommended)
    >>> from image_preprocessing_detector.detection.layout_lite import (
    ...     HybridLayoutAnalyzer,
    ...     analyze_layout_hybrid,
    ... )
    >>> summary = analyze_layout_hybrid(image, page_number=1)
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

# DocLayout-YOLO integration (Phase 6)
# Import with try/except to allow graceful degradation when ML deps unavailable
try:
    from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
        DocLayoutIntegration,
        HybridLayoutAnalyzer,
        LayoutAnalysisMetrics,
        analyze_layout_hybrid,
    )

    _has_doclayout_integration = True
except ImportError:
    _has_doclayout_integration = False

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

# Add DocLayout-YOLO integration exports if available
if _has_doclayout_integration:
    __all__.extend([
        # DocLayout-YOLO integration (Phase 6)
        "DocLayoutIntegration",
        "HybridLayoutAnalyzer",
        "LayoutAnalysisMetrics",
        "analyze_layout_hybrid",
    ])
