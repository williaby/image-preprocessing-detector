"""Unit tests for DocLayout-YOLO detector and integration.

Tests cover:
- DocLayoutYOLODetector initialization and configuration
- Detection result parsing and COCO format conversion
- DocLayoutIntegration metrics calculation
- HybridLayoutAnalyzer combining ML and heuristics
- Graceful fallback when ML dependencies unavailable
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from image_preprocessing_detector.schema import LayoutType, PageLayoutSummary

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def synthetic_document_image() -> np.ndarray:
    """Create a synthetic document-like image for testing.

    Returns:
        A white image with some black rectangles simulating text blocks.
    """
    # Create white background (800x600)
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255

    # Add some black rectangles to simulate text blocks
    # Title area
    image[50:80, 100:700] = 0

    # Text blocks (two columns)
    image[100:400, 50:350] = 50
    image[100:400, 450:750] = 50

    # Table-like structure
    for i in range(5):
        y = 420 + i * 30
        image[y : y + 2, 100:700] = 0  # Horizontal lines
    for i in range(6):
        x = 100 + i * 120
        image[420:570, x : x + 2] = 0  # Vertical lines

    return image


@pytest.fixture
def empty_image() -> np.ndarray:
    """Create an empty/white image for testing."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 255


@pytest.fixture
def mock_yolo_result() -> MagicMock:
    """Create a mock YOLO detection result."""
    mock_result = MagicMock()

    # Mock boxes
    mock_boxes = MagicMock()
    mock_boxes.xyxy = MagicMock()
    mock_boxes.xyxy.__len__ = MagicMock(return_value=3)
    mock_boxes.xyxy.__getitem__ = MagicMock(
        side_effect=[
            MagicMock(
                cpu=MagicMock(
                    return_value=MagicMock(
                        numpy=MagicMock(
                            return_value=MagicMock(
                                tolist=MagicMock(return_value=[100, 50, 700, 80])
                            )
                        )
                    )
                )
            ),
            MagicMock(
                cpu=MagicMock(
                    return_value=MagicMock(
                        numpy=MagicMock(
                            return_value=MagicMock(
                                tolist=MagicMock(return_value=[50, 100, 350, 400])
                            )
                        )
                    )
                )
            ),
            MagicMock(
                cpu=MagicMock(
                    return_value=MagicMock(
                        numpy=MagicMock(
                            return_value=MagicMock(
                                tolist=MagicMock(return_value=[100, 420, 700, 570])
                            )
                        )
                    )
                )
            ),
        ]
    )
    mock_boxes.cls = MagicMock()
    mock_boxes.cls.__getitem__ = MagicMock(
        side_effect=[
            MagicMock(
                cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=0)))
            ),  # title
            MagicMock(
                cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=1)))
            ),  # plain text
            MagicMock(
                cpu=MagicMock(return_value=MagicMock(numpy=MagicMock(return_value=5)))
            ),  # table
        ]
    )
    mock_boxes.conf = MagicMock()
    mock_boxes.conf.__getitem__ = MagicMock(
        side_effect=[
            MagicMock(
                cpu=MagicMock(
                    return_value=MagicMock(numpy=MagicMock(return_value=0.95))
                )
            ),
            MagicMock(
                cpu=MagicMock(
                    return_value=MagicMock(numpy=MagicMock(return_value=0.88))
                )
            ),
            MagicMock(
                cpu=MagicMock(
                    return_value=MagicMock(numpy=MagicMock(return_value=0.92))
                )
            ),
        ]
    )

    mock_result.boxes = mock_boxes
    mock_result.names = {0: "title", 1: "plain text", 5: "table"}

    return mock_result


# =============================================================================
# DocLayoutClass Enum Tests
# =============================================================================


class TestDocLayoutClass:
    """Tests for DocLayoutClass enum."""

    def test_from_model_output_valid(self) -> None:
        """Test conversion from valid model output names."""
        from image_preprocessing_detector.detection.doclayout_yolo import DocLayoutClass

        assert DocLayoutClass.from_model_output("title") == DocLayoutClass.TITLE
        assert (
            DocLayoutClass.from_model_output("plain text") == DocLayoutClass.PLAIN_TEXT
        )
        assert DocLayoutClass.from_model_output("table") == DocLayoutClass.TABLE
        assert DocLayoutClass.from_model_output("figure") == DocLayoutClass.FIGURE
        assert (
            DocLayoutClass.from_model_output("isolate_formula")
            == DocLayoutClass.ISOLATE_FORMULA
        )

    def test_from_model_output_case_insensitive(self) -> None:
        """Test case-insensitive conversion."""
        from image_preprocessing_detector.detection.doclayout_yolo import DocLayoutClass

        assert DocLayoutClass.from_model_output("TITLE") == DocLayoutClass.TITLE
        assert DocLayoutClass.from_model_output("Table") == DocLayoutClass.TABLE
        assert (
            DocLayoutClass.from_model_output("PLAIN TEXT") == DocLayoutClass.PLAIN_TEXT
        )

    def test_from_model_output_variations(self) -> None:
        """Test handling of common variations.

        DocLayNet and DocStructBench use different class names.
        The implementation maps to the primary enum for each schema.
        """
        from image_preprocessing_detector.detection.doclayout_yolo import DocLayoutClass

        # DocLayNet classes (primary schema)
        assert DocLayoutClass.from_model_output("text") == DocLayoutClass.TEXT
        assert DocLayoutClass.from_model_output("picture") == DocLayoutClass.PICTURE
        assert DocLayoutClass.from_model_output("formula") == DocLayoutClass.FORMULA

        # DocStructBench classes with aliases
        assert DocLayoutClass.from_model_output("image") == DocLayoutClass.FIGURE
        assert DocLayoutClass.from_model_output("figure") == DocLayoutClass.FIGURE
        assert (
            DocLayoutClass.from_model_output("abandon") == DocLayoutClass.ABANDONED_TEXT
        )
        assert (
            DocLayoutClass.from_model_output("abandoned")
            == DocLayoutClass.ABANDONED_TEXT
        )

    def test_from_model_output_unknown(self) -> None:
        """Test handling of unknown class names."""
        from image_preprocessing_detector.detection.doclayout_yolo import DocLayoutClass

        assert DocLayoutClass.from_model_output("unknown_class") is None
        assert DocLayoutClass.from_model_output("random_name") is None


# =============================================================================
# DetectedElement Tests
# =============================================================================


class TestDetectedElement:
    """Tests for DetectedElement dataclass."""

    def test_from_prediction(self) -> None:
        """Test creating element from prediction data."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
            DocLayoutClass,
        )

        element = DetectedElement.from_prediction(
            class_id=0,
            class_name="title",
            confidence=0.95,
            bbox_xyxy=[100.5, 50.2, 700.8, 80.9],
        )

        assert element.class_id == 0
        assert element.class_name == "title"
        assert element.class_enum == DocLayoutClass.TITLE
        assert element.confidence == 0.95
        # Check COCO format conversion [x, y, width, height]
        # xyxy: [100.5, 50.2, 700.8, 80.9] -> rounded [100, 50, 701, 81]
        # width = 701 - 100 = 601, height = 81 - 50 = 31
        assert element.bbox == [100, 50, 601, 31]  # Rounded and converted
        assert element.bbox_xyxy == [100, 50, 701, 81]  # Rounded xyxy

    def test_from_prediction_unknown_class(self) -> None:
        """Test element with unknown class name."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
        )

        element = DetectedElement.from_prediction(
            class_id=99,
            class_name="unknown_class",
            confidence=0.5,
            bbox_xyxy=[0, 0, 100, 100],
        )

        assert element.class_enum is None
        assert element.class_name == "unknown_class"


# =============================================================================
# LayoutDetectionResult Tests
# =============================================================================


class TestLayoutDetectionResult:
    """Tests for LayoutDetectionResult dataclass."""

    def test_empty_result(self) -> None:
        """Test empty detection result."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            LayoutDetectionResult,
        )

        result = LayoutDetectionResult()

        assert result.num_elements == 0
        assert result.has_tables is False
        assert result.has_figures is False
        assert result.has_formulas is False
        assert result.success is True

    def test_result_with_elements(self) -> None:
        """Test result with detected elements."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
            DocLayoutClass,
            LayoutDetectionResult,
        )

        elements = [
            DetectedElement(
                class_id=0,
                class_name="title",
                class_enum=DocLayoutClass.TITLE,
                confidence=0.9,
                bbox=[0, 0, 100, 50],
                bbox_xyxy=[0, 0, 100, 50],
            ),
            DetectedElement(
                class_id=5,
                class_name="table",
                class_enum=DocLayoutClass.TABLE,
                confidence=0.85,
                bbox=[0, 100, 200, 150],
                bbox_xyxy=[0, 100, 200, 250],
            ),
            DetectedElement(
                class_id=3,
                class_name="figure",
                class_enum=DocLayoutClass.FIGURE,
                confidence=0.8,
                bbox=[250, 100, 100, 100],
                bbox_xyxy=[250, 100, 350, 200],
            ),
        ]

        result = LayoutDetectionResult(
            elements=elements,
            inference_time_ms=15.5,
            image_size=(600, 800),
            model_name="DocStructBench",
            device="cuda:0",
        )

        assert result.num_elements == 3
        assert result.has_tables is True
        assert result.has_figures is True
        assert result.has_formulas is False

    def test_get_elements_by_class(self) -> None:
        """Test filtering elements by class."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
            DocLayoutClass,
            LayoutDetectionResult,
        )

        elements = [
            DetectedElement(
                class_id=1,
                class_name="plain text",
                class_enum=DocLayoutClass.PLAIN_TEXT,
                confidence=0.9,
                bbox=[0, 0, 100, 50],
                bbox_xyxy=[0, 0, 100, 50],
            ),
            DetectedElement(
                class_id=1,
                class_name="plain text",
                class_enum=DocLayoutClass.PLAIN_TEXT,
                confidence=0.85,
                bbox=[0, 60, 100, 50],
                bbox_xyxy=[0, 60, 100, 110],
            ),
            DetectedElement(
                class_id=5,
                class_name="table",
                class_enum=DocLayoutClass.TABLE,
                confidence=0.8,
                bbox=[0, 120, 200, 100],
                bbox_xyxy=[0, 120, 200, 220],
            ),
        ]

        result = LayoutDetectionResult(elements=elements)

        text_elements = result.get_elements_by_class(DocLayoutClass.PLAIN_TEXT)
        assert len(text_elements) == 2

        table_elements = result.get_elements_by_class(DocLayoutClass.TABLE)
        assert len(table_elements) == 1

        figure_elements = result.get_elements_by_class(DocLayoutClass.FIGURE)
        assert len(figure_elements) == 0

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
            DocLayoutClass,
            LayoutDetectionResult,
        )

        elements = [
            DetectedElement(
                class_id=0,
                class_name="title",
                class_enum=DocLayoutClass.TITLE,
                confidence=0.9,
                bbox=[0, 0, 100, 50],
                bbox_xyxy=[0, 0, 100, 50],
            ),
        ]

        result = LayoutDetectionResult(
            elements=elements,
            inference_time_ms=10.0,
            image_size=(600, 800),
            model_name="Test",
            device="cpu",
        )

        data = result.to_dict()

        assert data["num_elements"] == 1
        assert data["inference_time_ms"] == 10.0
        assert data["image_size"] == [600, 800]
        assert data["success"] is True
        assert len(data["elements"]) == 1
        assert data["elements"][0]["class_name"] == "title"


# =============================================================================
# DocLayoutYOLODetector Tests
# =============================================================================


class TestDocLayoutYOLODetector:
    """Tests for DocLayoutYOLODetector class."""

    def test_initialization_default(self) -> None:
        """Test default initialization."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DocLayoutYOLODetector,
        )

        detector = DocLayoutYOLODetector()

        assert detector.is_loaded is False
        # Test that model_id is set to a valid HuggingFace model
        # (specific model ID comes from config, not hardcoded)
        assert detector._model_id is not None
        assert detector._model_id.startswith("juliozhao/DocLayout-YOLO-")

    def test_initialization_custom_model(self) -> None:
        """Test initialization with custom model key."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DocLayoutYOLODetector,
        )

        detector = DocLayoutYOLODetector(model_key="d4la_pretrained")

        # Test that model was loaded with d4la key (specific ID comes from config)
        assert detector._model_id is not None
        assert detector._model_id.startswith("juliozhao/DocLayout-YOLO-")
        # Verify it's different from default model
        default_detector = DocLayoutYOLODetector()
        assert detector._model_id != default_detector._model_id

    def test_initialization_custom_settings(self) -> None:
        """Test initialization with custom confidence and image size."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DocLayoutYOLODetector,
        )

        detector = DocLayoutYOLODetector(
            confidence_threshold=0.5,
            image_size=640,
            device="cpu",
        )

        assert detector._confidence_threshold == 0.5
        assert detector._image_size == 640
        assert detector._requested_device == "cpu"

    def test_detect_empty_image(self, empty_image: np.ndarray) -> None:
        """Test detection on empty image returns empty result."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DocLayoutYOLODetector,
        )

        detector = DocLayoutYOLODetector()

        # Mock the model loading and prediction
        with patch.object(detector, "_load_model"):
            detector._model_loaded = True
            detector._actual_device = "cpu"
            detector._model = MagicMock()
            detector._model.predict.return_value = []

            result = detector.detect(empty_image)

        assert result.success is True
        assert result.num_elements == 0

    def test_detect_invalid_image(self) -> None:
        """Test detection on invalid image returns error."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DocLayoutYOLODetector,
        )

        detector = DocLayoutYOLODetector()

        result = detector.detect(np.array([]))

        assert result.success is False
        assert result.error_message is not None


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_is_doclayout_yolo_available(self) -> None:
        """Test availability check function."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            is_doclayout_yolo_available,
        )

        # This should return True or False based on whether package is installed
        result = is_doclayout_yolo_available()
        assert isinstance(result, bool)

    def test_get_doclayout_yolo_model_info(self) -> None:
        """Test model info retrieval."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            get_doclayout_yolo_model_info,
        )

        info = get_doclayout_yolo_model_info()

        assert "model_id" in info
        assert "name" in info
        assert "architecture" in info
        assert "is_available" in info
        assert info["architecture"] == "YOLOv10"


# =============================================================================
# DocLayoutIntegration Tests
# =============================================================================


class TestDocLayoutIntegration:
    """Tests for DocLayoutIntegration class."""

    def test_analyze_empty_result(self) -> None:
        """Test analysis of empty detection result."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            LayoutDetectionResult,
        )
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            DocLayoutIntegration,
        )

        integration = DocLayoutIntegration()
        result = LayoutDetectionResult(success=True, elements=[])

        metrics = integration.analyze_detection(result, (600, 800))

        assert metrics.total_elements == 0
        assert metrics.complexity_score == 0.0
        assert metrics.has_tables is False

    def test_analyze_with_elements(self) -> None:
        """Test analysis with detected elements."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
            DocLayoutClass,
            LayoutDetectionResult,
        )
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            DocLayoutIntegration,
        )

        elements = [
            DetectedElement(
                class_id=5,
                class_name="table",
                class_enum=DocLayoutClass.TABLE,
                confidence=0.9,
                bbox=[100, 100, 200, 150],  # COCO format
                bbox_xyxy=[100, 100, 300, 250],
            ),
            DetectedElement(
                class_id=3,
                class_name="figure",
                class_enum=DocLayoutClass.FIGURE,
                confidence=0.8,
                bbox=[400, 100, 150, 150],
                bbox_xyxy=[400, 100, 550, 250],
            ),
        ]

        result = LayoutDetectionResult(
            elements=elements,
            success=True,
            image_size=(600, 800),
        )

        integration = DocLayoutIntegration()
        metrics = integration.analyze_detection(result, (600, 800))

        assert metrics.total_elements == 2
        assert metrics.has_tables is True
        assert metrics.has_figures is True
        assert metrics.has_formulas is False
        assert 0 < metrics.complexity_score <= 1.0
        assert 0 < metrics.element_coverage <= 1.0

    def test_complexity_calculation(self) -> None:
        """Test complexity score calculation."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            DetectedElement,
            DocLayoutClass,
            LayoutDetectionResult,
        )
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            DocLayoutIntegration,
        )

        # Simple document (just text)
        simple_elements = [
            DetectedElement(
                class_id=1,
                class_name="plain text",
                class_enum=DocLayoutClass.PLAIN_TEXT,
                confidence=0.9,
                bbox=[50, 50, 300, 400],
                bbox_xyxy=[50, 50, 350, 450],
            ),
        ]

        # Complex document (tables, figures, formulas)
        complex_elements = [
            DetectedElement(
                class_id=5,
                class_name="table",
                class_enum=DocLayoutClass.TABLE,
                confidence=0.9,
                bbox=[50, 50, 200, 150],
                bbox_xyxy=[50, 50, 250, 200],
            ),
            DetectedElement(
                class_id=5,
                class_name="table",
                class_enum=DocLayoutClass.TABLE,
                confidence=0.85,
                bbox=[50, 220, 200, 150],
                bbox_xyxy=[50, 220, 250, 370],
            ),
            DetectedElement(
                class_id=3,
                class_name="figure",
                class_enum=DocLayoutClass.FIGURE,
                confidence=0.8,
                bbox=[300, 50, 200, 200],
                bbox_xyxy=[300, 50, 500, 250],
            ),
            DetectedElement(
                class_id=8,
                class_name="isolate_formula",
                class_enum=DocLayoutClass.ISOLATE_FORMULA,
                confidence=0.75,
                bbox=[300, 280, 200, 100],
                bbox_xyxy=[300, 280, 500, 380],
            ),
        ]

        integration = DocLayoutIntegration()

        simple_result = LayoutDetectionResult(elements=simple_elements, success=True)
        complex_result = LayoutDetectionResult(elements=complex_elements, success=True)

        simple_metrics = integration.analyze_detection(simple_result, (600, 800))
        complex_metrics = integration.analyze_detection(complex_result, (600, 800))

        # Complex document should have higher complexity
        assert complex_metrics.complexity_score > simple_metrics.complexity_score

    def test_determine_layout_type(self) -> None:
        """Test layout type determination."""
        from image_preprocessing_detector.detection.doclayout_yolo import (
            LayoutDetectionResult,
        )
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            DocLayoutIntegration,
        )

        integration = DocLayoutIntegration()

        # Empty result should use heuristic fallback
        empty_result = LayoutDetectionResult(success=False)
        layout = integration.determine_layout_type(empty_result, "multi")
        assert layout == LayoutType.MULTI_COLUMN

        # With heuristic column type only
        layout = integration.determine_layout_type(empty_result, "single")
        assert layout == LayoutType.SINGLE_COLUMN

        layout = integration.determine_layout_type(empty_result, "three_column")
        assert layout == LayoutType.THREE_COLUMN


# =============================================================================
# HybridLayoutAnalyzer Tests
# =============================================================================


class TestHybridLayoutAnalyzer:
    """Tests for HybridLayoutAnalyzer class."""

    def test_initialization(self) -> None:
        """Test analyzer initialization."""
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            HybridLayoutAnalyzer,
        )

        analyzer = HybridLayoutAnalyzer()

        assert analyzer._enable_ml is True
        assert analyzer._enable_heuristics is True

    def test_initialization_ml_disabled(self) -> None:
        """Test initialization with ML disabled."""
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            HybridLayoutAnalyzer,
        )

        analyzer = HybridLayoutAnalyzer(enable_ml=False)

        assert analyzer._enable_ml is False
        assert analyzer._enable_heuristics is True

    def test_analyze_empty_image(self, empty_image: np.ndarray) -> None:
        """Test analysis of empty image."""
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            HybridLayoutAnalyzer,
        )

        analyzer = HybridLayoutAnalyzer(enable_ml=False)  # Skip ML for this test
        summary = analyzer.analyze(empty_image, page_number=1)

        assert isinstance(summary, PageLayoutSummary)
        assert summary.page_number == 1

    def test_analyze_returns_page_layout_summary(
        self, synthetic_document_image: np.ndarray
    ) -> None:
        """Test that analyze returns PageLayoutSummary."""
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            HybridLayoutAnalyzer,
        )

        analyzer = HybridLayoutAnalyzer(enable_ml=False)  # Use heuristics only
        summary = analyzer.analyze(synthetic_document_image, page_number=1)

        assert isinstance(summary, PageLayoutSummary)
        assert summary.page_number == 1
        assert 0 <= summary.complexity_score <= 1.0

    def test_analyze_invalid_image(self) -> None:
        """Test analysis with invalid image."""
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            HybridLayoutAnalyzer,
        )

        analyzer = HybridLayoutAnalyzer()

        # None image
        summary = analyzer.analyze(None, page_number=1)
        assert summary.layout_type == LayoutType.UNKNOWN

        # Empty array
        summary = analyzer.analyze(np.array([]), page_number=1)
        assert summary.layout_type == LayoutType.UNKNOWN


# =============================================================================
# Integration Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_analyze_layout_hybrid(self, synthetic_document_image: np.ndarray) -> None:
        """Test analyze_layout_hybrid convenience function."""
        from image_preprocessing_detector.detection.layout_lite.doclayout_integration import (
            analyze_layout_hybrid,
        )

        summary = analyze_layout_hybrid(
            synthetic_document_image,
            page_number=1,
            enable_ml=False,  # Skip ML for consistent test
        )

        assert isinstance(summary, PageLayoutSummary)
        assert summary.page_number == 1
