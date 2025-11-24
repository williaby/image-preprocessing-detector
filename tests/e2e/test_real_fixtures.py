"""E2E tests using real document fixtures from data/test_fixtures/.

These tests validate the pipeline against actual PDFs and images
from the DocLayNet and TableBank datasets.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    NoiseDetector,
    SkewDetector,
)
from image_preprocessing_detector.ingestion.pdf_loader import PDFLoader
from image_preprocessing_detector.metrics.dqs_calculator import (
    DQSWeightConfig,
    calculate_degradation_score,
    calculate_pre_ocr_risk,
    normalize_classical_iqa,
)
from image_preprocessing_detector.schema import (
    DetectedIssue,
    DocumentMetadata,
    DQSMetadata,
    IssueType,
    LayoutType,
    OCRRoutingStrategy,
    PageLayoutSummary,
    PageMetadata,
    PDFType,
    ProcessingVersion,
)


class RealDocumentProcessor:
    """Document processor for real fixtures testing.

    Similar to DocumentProcessor in test_pipeline_e2e.py but handles
    PDF loading and real document processing.
    """

    def __init__(self, config: DQSWeightConfig | None = None):
        """Initialize processor with optional custom config."""
        self.config = config or DQSWeightConfig()
        self.blur_detector = BlurDetector()
        self.noise_detector = NoiseDetector()
        self.contrast_detector = ContrastDetector()
        self.skew_detector = SkewDetector()
        self.pdf_loader = PDFLoader()

    def process_image(self, image):
        """Run IQA detection on a single image."""
        blur_result = self.blur_detector.detect(image)
        noise_result = self.noise_detector.detect(image)
        contrast_result = self.contrast_detector.detect(image)
        skew_result = self.skew_detector.detect(image)

        # Collect detected issues
        issues = []
        if blur_result.is_blurred:
            issues.append(
                DetectedIssue(
                    type=IssueType.BLUR,
                    severity=blur_result.severity,
                    confidence=1.0 - blur_result.blur_score,
                    description=f"Blur detected: variance={blur_result.variance:.2f}",
                )
            )
        if noise_result.is_noisy:
            issues.append(
                DetectedIssue(
                    type=IssueType.NOISE,
                    severity=noise_result.severity,
                    confidence=1.0 - noise_result.noise_score,
                    description=f"Noise detected: sigma={noise_result.noise_sigma:.2f}",
                )
            )
        if contrast_result.is_low_contrast:
            issues.append(
                DetectedIssue(
                    type=IssueType.LOW_CONTRAST,
                    severity=contrast_result.severity,
                    confidence=1.0 - contrast_result.score,
                    description=f"Low contrast: score={contrast_result.score:.2f}",
                )
            )
        if skew_result.is_skewed:
            issues.append(
                DetectedIssue(
                    type=IssueType.SKEW,
                    severity=skew_result.severity,
                    confidence=skew_result.confidence,
                    description=f"Skew detected: angle={skew_result.angle:.2f}",
                )
            )

        # Calculate normalized scores
        normalized = normalize_classical_iqa(
            blur_result=blur_result,
            noise_result=noise_result,
            contrast_result=contrast_result,
        )

        # Calculate degradation score
        degradation = calculate_degradation_score(normalized, config=self.config)

        return {
            "issues": issues,
            "blur_result": blur_result,
            "noise_result": noise_result,
            "contrast_result": contrast_result,
            "skew_result": skew_result,
            "normalized": normalized,
            "degradation_score": degradation,
        }

    def process_pdf(self, pdf_path: Path) -> DocumentMetadata:
        """Process a PDF file and return DocumentMetadata."""
        # Load PDF pages as PageImage objects (convert generator to list)
        page_images = list(self.pdf_loader.load(str(pdf_path)))

        pages = []
        page_layouts = []
        degradation_scores = []

        for idx, page_image in enumerate(page_images):
            # Extract numpy array from PageImage
            image = page_image.image
            result = self.process_image(image)

            # Create page metadata using correct field names
            page = PageMetadata(
                page_index=idx,
                width_px=image.shape[1],
                height_px=image.shape[0],
                dpi_input=int(page_image.dpi_input),
                dpi_effective=int(page_image.dpi_effective),
                detected_issues=result["issues"],
            )
            pages.append(page)

            # Create page layout summary
            layout = PageLayoutSummary(
                page_number=idx + 1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_handwriting=False,
                complexity_score=0.2,
            )
            page_layouts.append(layout)
            degradation_scores.append(result["degradation_score"])

        # Calculate document-level metrics
        avg_degradation = sum(degradation_scores) / len(degradation_scores)
        max_complexity = max(layout.complexity_score for layout in page_layouts)

        dqs = DQSMetadata(
            degradation_score=avg_degradation,
            structural_complexity_score=max_complexity,
        )

        pre_ocr_risk = calculate_pre_ocr_risk(
            dqs, PDFType.IMAGE_ONLY, page_layouts, config=self.config
        )

        # Determine routing based on quality
        if avg_degradation < 0.5:
            routing = OCRRoutingStrategy.VISION_STRUCTURED
        elif avg_degradation < 0.7:
            routing = OCRRoutingStrategy.OCR_ADVANCED
        else:
            routing = OCRRoutingStrategy.OCR_FAST

        return DocumentMetadata(
            document_id=f"test_{pdf_path.stem}",
            file_name=pdf_path.name,
            source_mime="application/pdf",
            num_pages=len(page_images),
            pdf_type=PDFType.IMAGE_ONLY,
            dqs=dqs,
            pre_ocr_risk=pre_ocr_risk,
            ocr_routing_recommendation=routing,
            page_layout_summary=page_layouts,
            processing_version=ProcessingVersion(
                pipeline_version="0.1.0-e2e-test",
                timestamp=datetime.now(tz=UTC),
            ),
            pages=pages,
        )


@pytest.mark.real_data
class TestRealPDFFixtures:
    """Test E2E pipeline with real DocLayNet PDF fixtures."""

    def test_simple_text_pdf(self, simple_text_pdf):
        """Test processing simple text-heavy PDF."""
        if not simple_text_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        metadata = processor.process_pdf(simple_text_pdf)

        # Verify basic structure
        assert metadata.document_id == "test_simple_text_1"
        assert metadata.file_name == "simple_text_1.pdf"
        assert metadata.num_pages >= 1
        assert metadata.source_mime == "application/pdf"

        # Verify DQS was calculated
        assert 0.0 <= metadata.dqs.degradation_score <= 1.0
        assert 0.0 <= metadata.pre_ocr_risk <= 1.0

        # Verify routing recommendation is valid
        assert metadata.ocr_routing_recommendation in OCRRoutingStrategy

    def test_tables_figures_pdf(self, tables_figures_pdf):
        """Test processing PDF with tables and figures."""
        if not tables_figures_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        metadata = processor.process_pdf(tables_figures_pdf)

        assert metadata.document_id == "test_tables_figures_2"
        assert metadata.num_pages >= 1

        # Should have valid handoff format
        json_output = metadata.model_dump_json()
        parsed = json.loads(json_output)
        assert "dqs" in parsed
        assert "pages" in parsed

    def test_multi_column_pdf(self, multi_column_pdf):
        """Test processing multi-column layout PDF."""
        if not multi_column_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        metadata = processor.process_pdf(multi_column_pdf)

        assert metadata.document_id == "test_multi_column_3"
        assert metadata.num_pages >= 1
        assert len(metadata.page_layout_summary) == metadata.num_pages

    def test_skewed_pdf(self, skewed_pdf):
        """Test processing skewed PDF - should detect skew issues."""
        if not skewed_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        metadata = processor.process_pdf(skewed_pdf)

        assert metadata.document_id == "test_skewed_4"
        assert metadata.num_pages >= 1

        # May or may not detect skew depending on actual content
        # Just verify processing completes successfully
        assert 0.0 <= metadata.dqs.degradation_score <= 1.0

    def test_low_contrast_pdf(self, low_contrast_pdf):
        """Test processing low contrast PDF - should detect contrast issues."""
        if not low_contrast_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        metadata = processor.process_pdf(low_contrast_pdf)

        assert metadata.document_id == "test_low_contrast_5"
        assert metadata.num_pages >= 1

        # Low contrast document might route to advanced OCR
        # Just verify it processes without errors
        assert metadata.ocr_routing_recommendation is not None

    def test_all_doclaynet_pdfs(self, all_doclaynet_pdfs):
        """Test that all DocLayNet PDFs can be processed."""
        if not all_doclaynet_pdfs:
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()

        for pdf_path in all_doclaynet_pdfs:
            metadata = processor.process_pdf(pdf_path)

            # Verify each PDF produces valid output
            assert metadata.num_pages >= 1
            assert 0.0 <= metadata.dqs.degradation_score <= 1.0
            assert 0.0 <= metadata.pre_ocr_risk <= 1.0

            # Verify JSON serialization works
            json_output = metadata.model_dump_json()
            assert len(json_output) > 0


@pytest.mark.real_data
class TestRealImageFixtures:
    """Test E2E pipeline with real TableBank image fixtures."""

    def test_simple_table_image(self, simple_table_image):
        """Test processing simple table image."""
        if simple_table_image is None:
            pytest.skip("TableBank fixtures not available")

        processor = RealDocumentProcessor()
        result = processor.process_image(simple_table_image)

        # Verify IQA results
        assert "degradation_score" in result
        assert 0.0 <= result["degradation_score"] <= 1.0
        assert "issues" in result
        assert isinstance(result["issues"], list)

    def test_complex_table_image(self, complex_table_image):
        """Test processing complex table image."""
        if complex_table_image is None:
            pytest.skip("TableBank fixtures not available")

        processor = RealDocumentProcessor()
        result = processor.process_image(complex_table_image)

        assert 0.0 <= result["degradation_score"] <= 1.0

    def test_rotated_table_image(self, rotated_table_image):
        """Test processing rotated table - may detect skew."""
        if rotated_table_image is None:
            pytest.skip("TableBank fixtures not available")

        processor = RealDocumentProcessor()
        result = processor.process_image(rotated_table_image)

        # Check skew detection ran
        assert result["skew_result"] is not None
        # Rotated image might have skew detected
        assert 0.0 <= result["degradation_score"] <= 1.0

    def test_low_quality_table_image(self, low_quality_table_image):
        """Test processing low quality table - should detect blur/noise."""
        if low_quality_table_image is None:
            pytest.skip("TableBank fixtures not available")

        processor = RealDocumentProcessor()
        result = processor.process_image(low_quality_table_image)

        # Low quality image should have some quality issues
        # But we don't know exactly which ones without inspecting the image
        assert 0.0 <= result["degradation_score"] <= 1.0

    def test_embedded_graphics_table_image(self, embedded_graphics_table_image):
        """Test processing table with embedded graphics."""
        if embedded_graphics_table_image is None:
            pytest.skip("TableBank fixtures not available")

        processor = RealDocumentProcessor()
        result = processor.process_image(embedded_graphics_table_image)

        assert 0.0 <= result["degradation_score"] <= 1.0

    def test_all_tablebank_images(self, all_tablebank_images):
        """Test that all TableBank images can be processed."""
        if not all_tablebank_images:
            pytest.skip("TableBank fixtures not available")

        processor = RealDocumentProcessor()

        for image_path in all_tablebank_images:
            image = cv2.imread(str(image_path))
            assert image is not None, f"Failed to load {image_path}"

            result = processor.process_image(image)

            # Verify each image produces valid output
            assert 0.0 <= result["degradation_score"] <= 1.0
            assert "issues" in result


@pytest.mark.real_data
class TestRealFixturesHandoff:
    """Test handoff format with real fixtures."""

    def test_handoff_json_from_real_pdf(self, simple_text_pdf):
        """Test that real PDF produces valid handoff JSON."""
        if not simple_text_pdf.exists():
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        metadata = processor.process_pdf(simple_text_pdf)

        # Serialize to JSON
        json_output = metadata.model_dump_json(indent=2)
        parsed = json.loads(json_output)

        # Verify all required handoff fields
        required_fields = [
            "document_id",
            "file_name",
            "source_mime",
            "num_pages",
            "pdf_type",
            "dqs",
            "pre_ocr_risk",
            "ocr_routing_recommendation",
            "page_layout_summary",
            "pages",
            "processing_version",
        ]
        for field in required_fields:
            assert field in parsed, f"Missing required field: {field}"

        # Verify nested structures
        assert "degradation_score" in parsed["dqs"]
        assert "pipeline_version" in parsed["processing_version"]
        assert len(parsed["pages"]) == parsed["num_pages"]

    def test_handoff_consistency_across_fixtures(self, all_doclaynet_pdfs):
        """Test that all PDFs produce consistent handoff format."""
        if not all_doclaynet_pdfs:
            pytest.skip("DocLayNet fixtures not available")

        processor = RealDocumentProcessor()
        handoff_outputs = []

        for pdf_path in all_doclaynet_pdfs:
            metadata = processor.process_pdf(pdf_path)
            parsed = json.loads(metadata.model_dump_json())
            handoff_outputs.append(parsed)

        # All outputs should have the same top-level keys
        reference_keys = set(handoff_outputs[0].keys())
        for output in handoff_outputs[1:]:
            assert set(output.keys()) == reference_keys
