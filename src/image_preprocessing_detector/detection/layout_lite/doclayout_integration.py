# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""DocLayout-YOLO integration for layout-lite detection.

This module bridges DocLayout-YOLO's ML-based detection with the heuristic-based
layout-lite detectors. It provides:

1. Conversion of DocLayout-YOLO detections to PageLayoutSummary attributes
2. Complexity scoring based on ML detections
3. Hybrid detection combining ML and heuristics
4. Graceful fallback when ML is unavailable

Phase 6 Implementation:
- ML-based element detection (tables, figures, formulas, text blocks)
- Heuristic fallback for watermarks, fuzzy scans, colorful backgrounds
- Weighted complexity scoring based on element types and counts

Usage:
    >>> from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
    ...     DocLayoutIntegration,
    ...     HybridLayoutAnalyzer,
    ... )
    >>> analyzer = HybridLayoutAnalyzer()
    >>> summary = analyzer.analyze(image, page_number=1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from image_preprocessing_detector.schema import LayoutType, PageLayoutSummary
from image_preprocessing_detector.utils import get_logger

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from image_preprocessing_detector.detection.doclayout_yolo import (
        LayoutDetectionResult,
    )

logger = get_logger(__name__)


# Complexity weights for different element types
# Higher weights indicate elements that increase OCR complexity
ELEMENT_COMPLEXITY_WEIGHTS: dict[str, float] = {
    "table": 0.25,  # Tables require special handling
    "figure": 0.15,  # Figures need extraction
    "isolate_formula": 0.20,  # Formulas need specialized OCR
    "formula_caption": 0.05,  # Less complex than formulas
    "figure_caption": 0.05,  # Text but spatially complex
    "table_caption": 0.05,  # Text but spatially complex
    "table_footnote": 0.05,  # Text but spatially complex
    "title": 0.02,  # Simple text
    "plain text": 0.01,  # Base text
    "abandon": 0.0,  # Ignored text
}


@dataclass
class LayoutAnalysisMetrics:
    """Metrics derived from DocLayout-YOLO detection.

    Attributes:
        element_counts: Count of each element type detected
        total_elements: Total number of detected elements
        element_coverage: Fraction of page covered by detected elements
        has_tables: Whether tables were detected
        has_figures: Whether figures were detected
        has_formulas: Whether formulas were detected
        complexity_score: Calculated complexity (0-1)
        inference_time_ms: Time taken for ML inference
    """

    element_counts: dict[str, int] = field(default_factory=dict)
    total_elements: int = 0
    element_coverage: float = 0.0
    has_tables: bool = False
    has_figures: bool = False
    has_formulas: bool = False
    complexity_score: float = 0.0
    inference_time_ms: float = 0.0


class DocLayoutIntegration:
    """Integrates DocLayout-YOLO detections with layout-lite analysis.

    This class converts ML-based detections to the attributes needed for
    PageLayoutSummary and routing decisions.

    Example:
        >>> from image_preprocessing_detector.detection.doclayout_yolo import (
        ...     DocLayoutYOLODetector,
        ... )
        >>> detector = DocLayoutYOLODetector()
        >>> result = detector.detect(image)
        >>> integration = DocLayoutIntegration()
        >>> metrics = integration.analyze_detection(result, image.shape[:2])
    """

    def __init__(
        self,
        complexity_weights: dict[str, float] | None = None,
        max_complexity_elements: int = 20,
    ) -> None:
        """Initialize the integration.

        Args:
            complexity_weights: Custom weights for element types.
                              If None, uses default ELEMENT_COMPLEXITY_WEIGHTS.
            max_complexity_elements: Maximum element count for normalization.
                                    More elements than this won't increase score.
        """
        self._weights = complexity_weights or ELEMENT_COMPLEXITY_WEIGHTS
        self._max_elements = max_complexity_elements

        logger.debug(
            "DocLayoutIntegration initialized",
            num_weight_classes=len(self._weights),
            max_elements=max_complexity_elements,
        )

    def analyze_detection(
        self,
        result: LayoutDetectionResult,
        image_shape: tuple[int, int],
    ) -> LayoutAnalysisMetrics:
        """Analyze DocLayout-YOLO detection results.

        Args:
            result: Detection result from DocLayoutYOLODetector
            image_shape: Image shape as (height, width)

        Returns:
            LayoutAnalysisMetrics with derived metrics
        """
        if not result.success or not result.elements:
            return LayoutAnalysisMetrics(
                inference_time_ms=result.inference_time_ms,
            )

        # Count elements by type
        element_counts: dict[str, int] = {}
        for elem in result.elements:
            name = elem.class_name.lower()
            element_counts[name] = element_counts.get(name, 0) + 1

        # Calculate element coverage
        height, width = image_shape
        total_area = height * width
        covered_area = 0.0

        for elem in result.elements:
            # bbox is [x, y, width, height] in COCO format
            bbox_width = elem.bbox[2]
            bbox_height = elem.bbox[3]
            covered_area += bbox_width * bbox_height

        element_coverage = (
            min(covered_area / total_area, 1.0) if total_area > 0 else 0.0
        )

        # Calculate complexity score
        complexity_score = self._calculate_complexity(element_counts, element_coverage)

        return LayoutAnalysisMetrics(
            element_counts=element_counts,
            total_elements=len(result.elements),
            element_coverage=element_coverage,
            has_tables=result.has_tables,
            has_figures=result.has_figures,
            has_formulas=result.has_formulas,
            complexity_score=complexity_score,
            inference_time_ms=result.inference_time_ms,
        )

    def _calculate_complexity(
        self,
        element_counts: dict[str, int],
        element_coverage: float,
    ) -> float:
        """Calculate structural complexity score.

        Complexity is based on:
        1. Weighted sum of element types (tables, formulas more complex)
        2. Total number of elements (more elements = more complex)
        3. Element coverage (higher coverage = more complex layout)

        Args:
            element_counts: Count of each element type
            element_coverage: Fraction of page covered by elements

        Returns:
            Complexity score in range [0, 1]
        """
        # Component 1: Weighted element type score
        type_score = 0.0
        for elem_type, count in element_counts.items():
            weight = self._weights.get(elem_type, 0.01)
            # Diminishing returns for multiple elements of same type
            type_score += weight * min(count, 5)

        # Normalize type score to [0, 1]
        type_score = min(type_score, 1.0)

        # Component 2: Element count score
        total_elements = sum(element_counts.values())
        count_score = min(total_elements / self._max_elements, 1.0)

        # Component 3: Coverage score (already 0-1)
        coverage_score = element_coverage

        # Weighted combination
        # Type is most important, then count, then coverage
        complexity = 0.5 * type_score + 0.3 * count_score + 0.2 * coverage_score

        return min(max(complexity, 0.0), 1.0)

    def determine_layout_type(
        self,
        result: LayoutDetectionResult,
        heuristic_column_type: str | None = None,
    ) -> LayoutType:
        """Determine layout type from ML detection.

        Uses detected elements to infer layout type. Falls back to
        heuristic-based column detection if available.

        Args:
            result: Detection result from DocLayoutYOLODetector
            heuristic_column_type: Column type from heuristic detector
                                  ("single", "multi", "three_column", "complex")

        Returns:
            LayoutType enum value
        """
        if not result.success:
            # Fall back to heuristic if available
            return self._column_type_to_layout(heuristic_column_type)

        # Count text blocks to infer columns
        text_elements = [
            e
            for e in result.elements
            if e.class_name.lower() in ("plain text", "text", "title")
        ]

        if len(text_elements) < 2:
            return LayoutType.SINGLE_COLUMN

        # Analyze horizontal positions of text blocks
        x_positions = [e.bbox[0] + e.bbox[2] / 2 for e in text_elements]  # Center x

        if not x_positions:
            return self._column_type_to_layout(heuristic_column_type)

        # Simple column inference based on x-position clustering
        x_range = max(x_positions) - min(x_positions) if x_positions else 0
        image_width = result.image_size[1] if result.image_size[1] > 0 else 1

        # If text spans less than 60% of width, likely single column
        if x_range < 0.4 * image_width:
            return LayoutType.SINGLE_COLUMN

        # Check for multi-column by looking for gaps
        x_sorted = sorted(x_positions)
        gaps = [x_sorted[i + 1] - x_sorted[i] for i in range(len(x_sorted) - 1)]
        large_gaps = [g for g in gaps if g > image_width * 0.15]

        if len(large_gaps) >= 2:
            return LayoutType.THREE_COLUMN
        if len(large_gaps) == 1:
            return LayoutType.MULTI_COLUMN

        # Check if layout is complex (many overlapping elements)
        if result.has_tables and result.has_figures:
            return LayoutType.COMPLEX

        return LayoutType.SINGLE_COLUMN

    def _column_type_to_layout(self, column_type: str | None) -> LayoutType:
        """Convert heuristic column type to LayoutType enum.

        Args:
            column_type: String from heuristic column detector

        Returns:
            LayoutType enum value
        """
        if column_type is None:
            return LayoutType.UNKNOWN

        mapping = {
            "single": LayoutType.SINGLE_COLUMN,
            "single_column": LayoutType.SINGLE_COLUMN,
            "multi": LayoutType.MULTI_COLUMN,
            "multi_column": LayoutType.MULTI_COLUMN,
            "three_column": LayoutType.THREE_COLUMN,
            "complex": LayoutType.COMPLEX,
        }

        return mapping.get(column_type.lower(), LayoutType.UNKNOWN)


class HybridLayoutAnalyzer:
    """Hybrid analyzer combining DocLayout-YOLO ML with heuristic detectors.

    This analyzer uses ML detection for structural elements (tables, figures,
    formulas, text blocks) and heuristic detectors for quality attributes
    (fuzzy scan, watermark, colorful background).

    The hybrid approach provides:
    - Better accuracy for structural elements (ML)
    - Reliable quality detection (heuristics)
    - Graceful degradation when ML unavailable

    Example:
        >>> analyzer = HybridLayoutAnalyzer()
        >>> summary = analyzer.analyze(image, page_number=1)
        >>> print(f"Has tables: {summary.has_tables}")
        >>> print(f"Complexity: {summary.complexity_score:.2f}")
    """

    def __init__(
        self,
        enable_ml: bool = True,
        enable_heuristics: bool = True,
        ml_model_key: str | None = None,
        ml_confidence_threshold: float = 0.2,
    ) -> None:
        """Initialize the hybrid analyzer.

        Args:
            enable_ml: Enable DocLayout-YOLO ML detection
            enable_heuristics: Enable heuristic-based detection
            ml_model_key: DocLayout-YOLO model key (default: active model)
            ml_confidence_threshold: Confidence threshold for ML detection
        """
        self._enable_ml = enable_ml
        self._enable_heuristics = enable_heuristics
        self._ml_model_key = ml_model_key
        self._ml_confidence_threshold = ml_confidence_threshold

        # Lazy-loaded components
        self._ml_detector: Any = None
        self._ml_integration: DocLayoutIntegration | None = None
        self._heuristic_analyzer: Any = None

        # Track availability
        self._ml_available: bool | None = None

        logger.info(
            "HybridLayoutAnalyzer initialized",
            enable_ml=enable_ml,
            enable_heuristics=enable_heuristics,
            ml_model_key=ml_model_key or "active",
        )

    @property
    def ml_available(self) -> bool:
        """Check if ML detection is available."""
        if self._ml_available is None:
            try:
                from image_preprocessing_detector.detection.doclayout_yolo import (
                    is_doclayout_yolo_available,
                )

                self._ml_available = is_doclayout_yolo_available()
            except ImportError:
                self._ml_available = False

        return self._ml_available

    def _get_ml_detector(self) -> Any:
        """Get or create ML detector (lazy loading)."""
        if self._ml_detector is None and self._enable_ml and self.ml_available:
            from image_preprocessing_detector.detection.doclayout_yolo import (
                DocLayoutYOLODetector,
            )

            self._ml_detector = DocLayoutYOLODetector(
                model_key=self._ml_model_key,
                confidence_threshold=self._ml_confidence_threshold,
            )
            self._ml_integration = DocLayoutIntegration()

        return self._ml_detector

    def _get_heuristic_analyzer(self) -> Any:
        """Get or create heuristic analyzer (lazy loading)."""
        if self._heuristic_analyzer is None and self._enable_heuristics:
            from image_preprocessing_detector.detection.layout_lite.analyzer import (
                LayoutLiteAnalyzer,
            )

            self._heuristic_analyzer = LayoutLiteAnalyzer()

        return self._heuristic_analyzer

    def analyze(
        self,
        image: NDArray[np.uint8],
        page_number: int = 1,
    ) -> PageLayoutSummary:
        """Analyze page layout using hybrid ML + heuristic approach.

        Args:
            image: Input image as numpy array (BGR format)
            page_number: 1-based page number

        Returns:
            PageLayoutSummary with all layout attributes
        """
        if image is None or image.size == 0:
            logger.warning("Empty image provided to hybrid analyzer")
            return self._create_empty_summary(page_number)

        # Initialize results
        ml_metrics: LayoutAnalysisMetrics | None = None
        ml_result: LayoutDetectionResult | None = None
        heuristic_results: dict[str, Any] = {}

        # Run ML detection if enabled and available
        if self._enable_ml and self.ml_available:
            ml_result = self._run_ml_detection(image)
            if ml_result and ml_result.success:
                integration = self._ml_integration or DocLayoutIntegration()
                ml_metrics = integration.analyze_detection(
                    ml_result,
                    image.shape[:2],
                )

        # Run heuristic detection if enabled
        if self._enable_heuristics:
            heuristic_results = self._run_heuristic_detection(image)

        # Combine results
        return self._combine_results(
            page_number=page_number,
            ml_metrics=ml_metrics,
            ml_result=ml_result,
            heuristic_results=heuristic_results,
        )

    def _run_ml_detection(
        self,
        image: NDArray[np.uint8],
    ) -> LayoutDetectionResult | None:
        """Run DocLayout-YOLO detection.

        Args:
            image: Input image

        Returns:
            Detection result or None if ML not available
        """
        try:
            detector = self._get_ml_detector()
            if detector is None:
                return None

            return detector.detect(image)

        except Exception as e:
            logger.warning(
                "ML detection failed, falling back to heuristics", error=str(e)
            )
            return None

    def _run_heuristic_detection(
        self,
        image: NDArray[np.uint8],
    ) -> dict[str, Any]:
        """Run heuristic-based detection.

        Args:
            image: Input image

        Returns:
            Dictionary with heuristic detection results
        """
        try:
            analyzer = self._get_heuristic_analyzer()
            if analyzer is None:
                return {}

            return analyzer.analyze(image)

        except Exception as e:
            logger.warning("Heuristic detection failed", error=str(e))
            return {}

    def _combine_results(
        self,
        page_number: int,
        ml_metrics: LayoutAnalysisMetrics | None,
        ml_result: LayoutDetectionResult | None,
        heuristic_results: dict[str, Any],
    ) -> PageLayoutSummary:
        """Combine ML and heuristic results into PageLayoutSummary.

        ML results take precedence for structural elements.
        Heuristic results are used for quality attributes.

        Args:
            page_number: 1-based page number
            ml_metrics: Metrics from ML detection
            ml_result: Raw ML detection result
            heuristic_results: Results from heuristic analyzers

        Returns:
            PageLayoutSummary combining both sources
        """
        # Structural attributes (prefer ML if available)
        if ml_metrics is not None:
            has_tables = ml_metrics.has_tables
            has_figures = ml_metrics.has_figures
            has_dense_math = ml_metrics.has_formulas
            complexity_score = ml_metrics.complexity_score
        else:
            # Fall back to heuristics
            table_result = heuristic_results.get("table")
            figure_result = heuristic_results.get("figure")

            has_tables = (
                getattr(table_result, "has_tables", False) if table_result else False
            )
            has_figures = (
                getattr(figure_result, "has_figures", False) if figure_result else False
            )
            has_dense_math = False  # Heuristics don't detect math
            complexity_score = self._calculate_heuristic_complexity(heuristic_results)

        # Layout type (combine ML and heuristic column detection)
        heuristic_column_type = None
        column_result = heuristic_results.get("column")
        if column_result:
            heuristic_column_type = getattr(column_result, "column_type", None)

        if ml_result and self._ml_integration:
            layout_type = self._ml_integration.determine_layout_type(
                ml_result,
                heuristic_column_type,
            )
        elif heuristic_column_type:
            layout_type = DocLayoutIntegration()._column_type_to_layout(
                heuristic_column_type
            )
        else:
            layout_type = LayoutType.UNKNOWN

        # Quality attributes (always from heuristics)
        fuzzy_scan = False
        watermark = False
        colorful_background = False
        has_handwriting = False

        fuzzy_result = heuristic_results.get("fuzzy_scan")
        if fuzzy_result:
            fuzzy_scan = getattr(fuzzy_result, "fuzzy_scan", False)

        watermark_result = heuristic_results.get("watermark")
        if watermark_result:
            watermark = getattr(watermark_result, "watermark", False)

        bg_result = heuristic_results.get("colorful_background")
        if bg_result:
            colorful_background = getattr(bg_result, "colorful_background", False)

        # TODO: Add handwriting detection when implemented (Phase 6.11)
        # For now, default to False

        return PageLayoutSummary(
            page_number=page_number,
            layout_type=layout_type,
            has_tables=has_tables,
            has_figures=has_figures,
            has_dense_math=has_dense_math,
            has_handwriting=has_handwriting,
            fuzzy_scan=fuzzy_scan,
            watermark=watermark,
            colorful_background=colorful_background,
            complexity_score=complexity_score,
        )

    def _calculate_heuristic_complexity(
        self,
        heuristic_results: dict[str, Any],
    ) -> float:
        """Calculate complexity from heuristic results only.

        Used when ML detection is not available.

        Args:
            heuristic_results: Results from heuristic analyzers

        Returns:
            Complexity score in range [0, 1]
        """
        score = 0.0

        # Table presence adds complexity
        table_result = heuristic_results.get("table")
        if table_result and getattr(table_result, "has_tables", False):
            score += 0.25

        # Figure presence adds complexity
        figure_result = heuristic_results.get("figure")
        if figure_result and getattr(figure_result, "has_figures", False):
            num_figures = getattr(figure_result, "num_figures", 1)
            score += 0.15 * min(num_figures, 5)

        # Multi-column layout adds complexity
        column_result = heuristic_results.get("column")
        if column_result:
            column_type = getattr(column_result, "column_type", "single")
            if column_type == "three_column":
                score += 0.15
            elif column_type in ("multi", "multi_column"):
                score += 0.10
            elif column_type == "complex":
                score += 0.20

        # Quality issues add complexity
        fuzzy_result = heuristic_results.get("fuzzy_scan")
        if fuzzy_result and getattr(fuzzy_result, "fuzzy_scan", False):
            score += 0.10

        watermark_result = heuristic_results.get("watermark")
        if watermark_result and getattr(watermark_result, "watermark", False):
            score += 0.05

        return min(score, 1.0)

    def _create_empty_summary(self, page_number: int) -> PageLayoutSummary:
        """Create an empty summary for invalid input.

        Args:
            page_number: 1-based page number

        Returns:
            PageLayoutSummary with default values
        """
        return PageLayoutSummary(
            page_number=page_number,
            layout_type=LayoutType.UNKNOWN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            fuzzy_scan=False,
            watermark=False,
            colorful_background=False,
            complexity_score=0.0,
        )


def analyze_layout_hybrid(
    image: NDArray[np.uint8],
    page_number: int = 1,
    enable_ml: bool = True,
    enable_heuristics: bool = True,
) -> PageLayoutSummary:
    """Convenience function for hybrid layout analysis.

    Args:
        image: Input image as numpy array
        page_number: 1-based page number
        enable_ml: Enable DocLayout-YOLO detection
        enable_heuristics: Enable heuristic detection

    Returns:
        PageLayoutSummary with layout attributes

    Example:
        >>> import cv2
        >>> image = cv2.imread("document.png")
        >>> summary = analyze_layout_hybrid(image, page_number=1)
        >>> print(f"Complexity: {summary.complexity_score:.2f}")
    """
    analyzer = HybridLayoutAnalyzer(
        enable_ml=enable_ml,
        enable_heuristics=enable_heuristics,
    )
    return analyzer.analyze(image, page_number)
