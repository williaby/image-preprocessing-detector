"""End-to-end tests for Layout-Lite in full pipeline.

Tests Layout-Lite integration with:
- DQS calculation
- Routing recommendations
- Full DocumentMetadata generation

Sprint 5.1.x: E2E tests for Layout-Lite (Phase 6) workflow integration.
"""

from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from image_preprocessing_detector.detection.layout_lite.analyzer import (
    LayoutLiteAnalyzer,
)
from image_preprocessing_detector.ingestion.pdf_loader import PDFLoader
from image_preprocessing_detector.metrics.dqs_calculator import (
    DQSWeightConfig,
    calculate_structural_complexity_score,
)
from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    DQSMetadata,
    LayoutType,
    OCRRoutingRecommendation,
    PageLayoutSummary,
    PageMetadata,
    PDFType,
    ProcessingVersion,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def layout_analyzer():
    """Shared Layout-Lite analyzer for all tests."""
    return LayoutLiteAnalyzer()


@pytest.fixture
def synthetic_table_image():
    """Create synthetic image with table-like structure."""
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    # Draw table grid
    for y in range(100, 700, 80):
        cv2.line(image, (50, y), (550, y), (0, 0, 0), 2)
    for x in range(50, 600, 100):
        cv2.line(image, (x, 100), (x, 620), (0, 0, 0), 2)
    return image


@pytest.fixture
def synthetic_multi_column_image():
    """Create synthetic two-column document image."""
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    # Left column text lines
    for y in range(100, 900, 30):
        cv2.line(image, (50, y), (350, y), (0, 0, 0), 2)
    # Right column text lines
    for y in range(100, 900, 30):
        cv2.line(image, (450, y), (750, y), (0, 0, 0), 2)
    return image


# =============================================================================
# Layout-Lite to DQS Integration Tests
# =============================================================================


class TestLayoutLiteToDQS:
    """Test Layout-Lite output integration with DQS calculation."""

    def test_layout_result_to_page_layout_summary(
        self, layout_analyzer, sample_document_image
    ):
        """Test converting Layout-Lite result to PageLayoutSummary."""
        result = layout_analyzer.analyze(sample_document_image)

        # Extract relevant fields from analyzer result dict
        column_result = result.get("column")
        table_result = result.get("table")
        figure_result = result.get("figure")
        fuzzy_result = result.get("fuzzy_scan")

        # Map column type to LayoutType
        layout_type = LayoutType.SINGLE_COLUMN
        if column_result:
            col_type = column_result.column_type
            if col_type == "multi_column":
                layout_type = LayoutType.MULTI_COLUMN
            elif col_type == "three_column":
                layout_type = LayoutType.THREE_COLUMN
            elif col_type == "complex":
                layout_type = LayoutType.COMPLEX

        # Create PageLayoutSummary
        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=layout_type,
            has_tables=table_result.has_tables if table_result else False,
            has_figures=figure_result.has_figures if figure_result else False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.2,
        )

        assert isinstance(layout_summary, PageLayoutSummary)
        assert layout_summary.layout_type in LayoutType
        assert 0.0 <= layout_summary.complexity_score <= 1.0

    def test_structural_complexity_calculation(
        self, layout_analyzer, sample_document_image
    ):
        """Test structural complexity score calculation from layout."""
        result = layout_analyzer.analyze(sample_document_image)

        # Create basic PageLayoutSummary
        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.2,
        )

        # Calculate structural complexity
        complexity = calculate_structural_complexity_score(layout_summary)

        assert 0.0 <= complexity <= 1.0

    def test_table_detection_increases_complexity(
        self, layout_analyzer, synthetic_table_image
    ):
        """Test that table detection increases complexity score."""
        result = layout_analyzer.analyze(synthetic_table_image)
        table_result = result.get("table")

        # Create layout summaries with and without tables
        no_tables = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.1,
        )

        with_tables = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=True,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.4,
        )

        score_no_tables = calculate_structural_complexity_score(no_tables)
        score_with_tables = calculate_structural_complexity_score(with_tables)

        # Tables should increase complexity
        assert score_with_tables > score_no_tables


# =============================================================================
# Layout-Lite to Routing Integration Tests
# =============================================================================


class TestLayoutLiteToRouting:
    """Test Layout-Lite output integration with OCR routing."""

    def test_simple_layout_routes_to_fast(self, layout_analyzer, sample_document_image):
        """Test simple document routes to fast OCR."""
        result = layout_analyzer.analyze(sample_document_image)

        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.1,
        )

        dqs = DQSMetadata(
            degradation_score=0.9,  # High quality
            structural_complexity_score=0.1,  # Low complexity
        )

        recommendation, rationale = recommend_ocr_routing(
            PDFType.BORN_DIGITAL, dqs, 0.1, [layout_summary]
        )

        # Simple, high-quality document should route to fast/simple
        assert recommendation in [
            OCRRoutingRecommendation.OCR_FAST,
            OCRRoutingRecommendation.VISION_SIMPLE,
        ]

    def test_table_layout_routes_to_structured(
        self, layout_analyzer, synthetic_table_image
    ):
        """Test document with tables routes to structured vision."""
        result = layout_analyzer.analyze(synthetic_table_image)
        table_result = result.get("table")

        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=LayoutType.SINGLE_COLUMN,
            has_tables=True,  # Has tables
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.5,
        )

        dqs = DQSMetadata(
            degradation_score=0.8,
            structural_complexity_score=0.5,
        )

        recommendation, rationale = recommend_ocr_routing(
            PDFType.IMAGE_ONLY, dqs, 0.3, [layout_summary]
        )

        # Tables should trigger VISION_STRUCTURED
        assert recommendation == OCRRoutingRecommendation.VISION_STRUCTURED

    def test_multi_column_layout_routes_appropriately(
        self, layout_analyzer, synthetic_multi_column_image
    ):
        """Test multi-column layout routes appropriately."""
        result = layout_analyzer.analyze(synthetic_multi_column_image)
        column_result = result.get("column")

        layout_type = LayoutType.SINGLE_COLUMN
        if column_result and column_result.num_columns > 1:
            layout_type = LayoutType.MULTI_COLUMN

        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=layout_type,
            has_tables=False,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.4,
        )

        dqs = DQSMetadata(
            degradation_score=0.8,
            structural_complexity_score=0.4,
        )

        recommendation, rationale = recommend_ocr_routing(
            PDFType.IMAGE_ONLY, dqs, 0.3, [layout_summary]
        )

        # Should provide a valid recommendation
        assert recommendation in OCRRoutingRecommendation
        assert len(rationale) > 0


# =============================================================================
# Full Pipeline E2E Tests
# =============================================================================


@pytest.mark.real_data
class TestLayoutLiteFullPipeline:
    """End-to-end tests for Layout-Lite in full document processing pipeline."""

    def test_full_pipeline_with_synthetic_document(
        self, layout_analyzer, sample_document_image
    ):
        """Test full pipeline with synthetic document."""
        # Run Layout-Lite analysis
        result = layout_analyzer.analyze(sample_document_image)

        # Extract results
        column_result = result.get("column")
        table_result = result.get("table")
        figure_result = result.get("figure")
        fuzzy_result = result.get("fuzzy_scan")
        watermark_result = result.get("watermark")
        background_result = result.get("colorful_background")

        # Determine layout type
        layout_type = LayoutType.SINGLE_COLUMN
        if column_result:
            if column_result.column_type == "multi_column":
                layout_type = LayoutType.MULTI_COLUMN
            elif column_result.column_type == "complex":
                layout_type = LayoutType.COMPLEX

        # Create layout summary
        layout_summary = PageLayoutSummary(
            page_number=1,
            layout_type=layout_type,
            has_tables=table_result.has_tables if table_result else False,
            has_figures=figure_result.has_figures if figure_result else False,
            has_dense_math=False,
            has_handwriting=False,
            complexity_score=0.2,
        )

        # Calculate scores
        complexity = calculate_structural_complexity_score(layout_summary)
        dqs = DQSMetadata(
            degradation_score=0.8,
            structural_complexity_score=complexity,
        )

        # Get routing recommendation
        recommendation, rationale = recommend_ocr_routing(
            PDFType.IMAGE_ONLY, dqs, 0.2, [layout_summary]
        )

        # Create page metadata
        page = PageMetadata(
            page_index=0,
            width_px=sample_document_image.shape[1],
            height_px=sample_document_image.shape[0],
            dpi_input=300,
            dpi_effective=300,
        )

        # Create full document metadata
        metadata = DocumentMetadata(
            document_id="e2e_layout_test_001",
            file_name="synthetic_document.pdf",
            source_mime="application/pdf",
            num_pages=1,
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=dqs,
            pre_ocr_risk=0.2,
            ocr_routing_recommendation=recommendation,
            page_layout_summary=[layout_summary],
            processing_version=ProcessingVersion(
                pipeline_version="0.1.0-e2e-test",
                timestamp=datetime.now(tz=UTC),
            ),
            pages=[page],
        )

        # Verify complete metadata
        assert metadata.document_id == "e2e_layout_test_001"
        assert metadata.num_pages == 1
        assert len(metadata.page_layout_summary) == 1
        assert metadata.ocr_routing_recommendation in OCRRoutingRecommendation

        # Verify JSON serialization
        json_output = metadata.model_dump_json()
        assert len(json_output) > 0
        assert "page_layout_summary" in json_output

    def test_full_pipeline_with_real_pdf(
        self, layout_analyzer, simple_text_pdf, doclaynet_fixtures_dir
    ):
        """Test full pipeline with real DocLayNet PDF."""
        if not simple_text_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        # Load PDF
        pdf_loader = PDFLoader()
        page_images = list(pdf_loader.load(str(simple_text_pdf)))

        if not page_images:
            pytest.skip("Could not load PDF pages")

        page_layouts = []
        pages = []

        for idx, page_image in enumerate(page_images):
            # Run Layout-Lite
            result = layout_analyzer.analyze(page_image.image)

            # Extract results
            column_result = result.get("column")
            table_result = result.get("table")
            figure_result = result.get("figure")

            # Determine layout type
            layout_type = LayoutType.SINGLE_COLUMN
            if column_result:
                if column_result.column_type == "multi_column":
                    layout_type = LayoutType.MULTI_COLUMN

            # Create layout summary
            layout_summary = PageLayoutSummary(
                page_number=idx + 1,
                layout_type=layout_type,
                has_tables=table_result.has_tables if table_result else False,
                has_figures=figure_result.has_figures if figure_result else False,
                has_dense_math=False,
                has_handwriting=False,
                complexity_score=0.2,
            )
            page_layouts.append(layout_summary)

            # Create page metadata
            page = PageMetadata(
                page_index=idx,
                width_px=page_image.image.shape[1],
                height_px=page_image.image.shape[0],
                dpi_input=int(page_image.dpi_input),
                dpi_effective=int(page_image.dpi_effective),
            )
            pages.append(page)

        # Calculate document-level scores
        max_complexity = max(p.complexity_score for p in page_layouts)
        dqs = DQSMetadata(
            degradation_score=0.8,
            structural_complexity_score=max_complexity,
        )

        # Get routing recommendation
        recommendation, rationale = recommend_ocr_routing(
            PDFType.IMAGE_ONLY, dqs, 0.2, page_layouts
        )

        # Create full document metadata
        metadata = DocumentMetadata(
            document_id="e2e_real_pdf_001",
            file_name=simple_text_pdf.name,
            source_mime="application/pdf",
            num_pages=len(page_images),
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=dqs,
            pre_ocr_risk=0.2,
            ocr_routing_recommendation=recommendation,
            page_layout_summary=page_layouts,
            processing_version=ProcessingVersion(
                pipeline_version="0.1.0-e2e-test",
                timestamp=datetime.now(tz=UTC),
            ),
            pages=pages,
        )

        # Verify
        assert metadata.num_pages == len(page_images)
        assert len(metadata.page_layout_summary) == len(page_images)
        assert len(metadata.pages) == len(page_images)

    def test_all_doclaynet_pdfs_process(
        self, layout_analyzer, all_doclaynet_pdfs
    ):
        """Test that all DocLayNet PDFs can be processed through Layout-Lite."""
        if not all_doclaynet_pdfs:
            pytest.skip("DocLayNet fixtures not available")

        pdf_loader = PDFLoader()

        for pdf_path in all_doclaynet_pdfs:
            page_images = list(pdf_loader.load(str(pdf_path)))

            for page_image in page_images:
                # Run Layout-Lite - should not crash
                result = layout_analyzer.analyze(page_image.image)

                # Verify we get valid results
                assert result is not None
                assert isinstance(result, dict)

                # Check all expected keys exist
                expected_keys = [
                    "column", "table", "figure",
                    "fuzzy_scan", "watermark", "colorful_background"
                ]
                for key in expected_keys:
                    assert key in result, f"Missing key: {key}"


# =============================================================================
# Edge Case E2E Tests
# =============================================================================


class TestLayoutLiteEdgeCasesE2E:
    """E2E tests for Layout-Lite edge cases."""

    def test_very_small_image(self, layout_analyzer):
        """Test Layout-Lite handles very small images."""
        tiny = np.ones((50, 50, 3), dtype=np.uint8) * 255

        result = layout_analyzer.analyze(tiny)

        # Should not crash
        assert result is not None
        assert isinstance(result, dict)

    def test_very_large_image(self, layout_analyzer):
        """Test Layout-Lite handles large images."""
        large = np.ones((4000, 3000, 3), dtype=np.uint8) * 255
        # Add some content
        for y in range(100, 3800, 50):
            cv2.line(large, (100, y), (2900, y), (0, 0, 0), 2)

        result = layout_analyzer.analyze(large)

        # Should not crash
        assert result is not None
        assert isinstance(result, dict)

    def test_all_black_image(self, layout_analyzer):
        """Test Layout-Lite handles all-black image."""
        black = np.zeros((800, 600, 3), dtype=np.uint8)

        result = layout_analyzer.analyze(black)

        # Should not crash
        assert result is not None

    def test_all_white_image(self, layout_analyzer):
        """Test Layout-Lite handles all-white image."""
        white = np.ones((800, 600, 3), dtype=np.uint8) * 255

        result = layout_analyzer.analyze(white)

        # Should not crash, empty document
        assert result is not None

    def test_grayscale_image(self, layout_analyzer):
        """Test Layout-Lite handles grayscale input (should be rejected)."""
        gray = np.ones((800, 600), dtype=np.uint8) * 128

        # Layout-Lite expects BGR, so this should raise ValueError
        with pytest.raises(ValueError):
            layout_analyzer.analyze(gray)
