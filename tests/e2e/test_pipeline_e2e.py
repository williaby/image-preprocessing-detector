"""End-to-end tests for the complete document processing pipeline.

These tests verify the full pipeline from image input to JSON output,
ensuring the handoff format is correct for Project B consumption.
"""

import json
from datetime import UTC, datetime

import numpy as np

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector,
    NoiseDetector,
    SkewDetector,
)
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
    IssueSeverity,
    IssueType,
    LayoutType,
    OCRRoutingStrategy,
    PageLayoutSummary,
    PageMetadata,
    PDFType,
    ProcessingVersion,
)


class DocumentProcessor:
    """End-to-end document processor for testing.

    This class orchestrates the full pipeline:
    1. IQA Detection (blur, noise, contrast, skew)
    2. DQS Calculation
    3. Routing Recommendation
    4. Metadata Generation
    """

    def __init__(self, config: DQSWeightConfig | None = None):
        """Initialize processor with optional custom config."""
        self.config = config or DQSWeightConfig()
        self.blur_detector = BlurDetector()
        self.noise_detector = NoiseDetector()
        self.contrast_detector = ContrastDetector()
        self.skew_detector = SkewDetector()

    def process_image(self, image: np.ndarray, page_index: int = 0) -> dict:
        """Process a single image through the IQA pipeline.

        Args:
            image: Input image (BGR format)
            page_index: Page index in document

        Returns:
            Dictionary with detection results
        """
        # Run all detectors
        blur_result = self.blur_detector.detect(image)
        noise_result = self.noise_detector.detect(image)
        contrast_result = self.contrast_detector.detect(image)
        skew_result = self.skew_detector.detect(image)

        # Normalize IQA metrics
        iqa_metrics = normalize_classical_iqa(
            blur_result=blur_result,
            contrast_result=contrast_result,
            noise_result=noise_result,
        )

        # Calculate degradation score
        degradation_score = calculate_degradation_score(iqa_metrics, config=self.config)

        # Collect detected issues
        detected_issues = []

        if blur_result.is_blurred:
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.BLUR,
                    confidence=blur_result.confidence,
                    severity=IssueSeverity(blur_result.severity.value),
                    metrics={
                        "laplacian_variance": blur_result.score,
                        "blur_score": blur_result.blur_score,
                    },
                )
            )

        if noise_result.is_noisy:
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.NOISE,
                    confidence=noise_result.confidence,
                    severity=IssueSeverity(noise_result.severity.value),
                    metrics={
                        "noise_sigma": noise_result.noise_sigma,
                        "noise_score": noise_result.noise_score,
                    },
                )
            )

        if contrast_result.is_low_contrast:
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.LOW_CONTRAST,
                    confidence=contrast_result.confidence,
                    severity=IssueSeverity(contrast_result.severity.value),
                    metrics={"contrast_score": contrast_result.score},
                )
            )

        if abs(skew_result.angle) > 2.0:
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.SKEW,
                    confidence=skew_result.confidence,
                    severity=IssueSeverity(skew_result.severity.value),
                    metrics={"angle": skew_result.angle},
                )
            )

        h, w = image.shape[:2]

        return {
            "page_index": page_index,
            "width_px": w,
            "height_px": h,
            "blur_result": blur_result,
            "noise_result": noise_result,
            "contrast_result": contrast_result,
            "skew_result": skew_result,
            "iqa_metrics": iqa_metrics,
            "degradation_score": degradation_score,
            "detected_issues": detected_issues,
        }

    def determine_routing(
        self,
        degradation_score: float,
        complexity_score: float,
        has_tables: bool = False,
        has_handwriting: bool = False,
    ) -> OCRRoutingStrategy:
        """Determine OCR routing recommendation.

        Args:
            degradation_score: IQA degradation score (0-1, higher=better)
            complexity_score: Layout complexity score (0-1, higher=more complex)
            has_tables: Whether document has tables
            has_handwriting: Whether document has handwriting

        Returns:
            Recommended OCR routing strategy
        """
        if has_tables or complexity_score > 0.6:
            return OCRRoutingStrategy.VISION_STRUCTURED

        if has_handwriting:
            return OCRRoutingStrategy.OCR_ADVANCED

        if degradation_score > 0.7 and complexity_score < 0.3:
            return OCRRoutingStrategy.OCR_FAST

        if degradation_score < 0.4:
            return OCRRoutingStrategy.VISION_SIMPLE

        return OCRRoutingStrategy.OCR_ADVANCED

    def create_document_metadata(
        self,
        document_id: str,
        file_name: str,
        images: list[np.ndarray],
        pdf_type: PDFType = PDFType.IMAGE_ONLY,
    ) -> DocumentMetadata:
        """Create complete DocumentMetadata from images.

        Args:
            document_id: Unique document identifier
            file_name: Original filename
            images: List of page images
            pdf_type: PDF type classification

        Returns:
            Complete DocumentMetadata ready for handoff
        """
        pages = []
        page_layouts = []
        degradation_scores = []

        for i, img in enumerate(images):
            # Process each page
            result = self.process_image(img, page_index=i)
            degradation_scores.append(result["degradation_score"])

            # Create PageMetadata
            page = PageMetadata(
                page_index=i,
                width_px=result["width_px"],
                height_px=result["height_px"],
                dpi_input=300,
                dpi_effective=300,
                detected_issues=result["detected_issues"],
            )
            pages.append(page)

            # Create PageLayoutSummary (simplified for E2E test)
            layout = PageLayoutSummary(
                page_number=i + 1,
                layout_type=LayoutType.SINGLE_COLUMN,
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                complexity_score=0.2,
            )
            page_layouts.append(layout)

        # Calculate document-level DQS
        avg_degradation = sum(degradation_scores) / len(degradation_scores)
        max_complexity = max(layout.complexity_score for layout in page_layouts)

        dqs = DQSMetadata(
            degradation_score=avg_degradation,
            structural_complexity_score=max_complexity,
        )

        # Calculate pre-OCR risk
        pre_ocr_risk = calculate_pre_ocr_risk(
            dqs, pdf_type, page_layouts, config=self.config
        )

        # Determine routing
        routing = self.determine_routing(
            avg_degradation,
            max_complexity,
            has_tables=any(layout.has_tables for layout in page_layouts),
            has_handwriting=any(layout.has_handwriting for layout in page_layouts),
        )

        return DocumentMetadata(
            document_id=document_id,
            file_name=file_name,
            source_mime="image/png",
            num_pages=len(images),
            pdf_type=pdf_type,
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


class TestPipelineE2E:
    """End-to-end pipeline tests."""

    def test_clean_document_pipeline(self, sample_document_image, temp_output_dir):
        """Test pipeline with a clean document image."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_clean_001",
            file_name="clean_document.png",
            images=[sample_document_image],
        )

        # Verify basic structure
        assert metadata.document_id == "test_clean_001"
        assert metadata.num_pages == 1
        assert metadata.pdf_type == PDFType.IMAGE_ONLY

        # Verify DQS is reasonable for clean document
        assert metadata.dqs is not None
        assert metadata.dqs.degradation_score > 0.5  # Should be good quality

        # Verify routing recommendation
        assert metadata.ocr_routing_recommendation is not None

        # Verify pre_ocr_risk is low for clean document
        assert metadata.pre_ocr_risk is not None
        assert metadata.pre_ocr_risk < 0.5

        # Verify page metadata
        assert len(metadata.pages) == 1
        page = metadata.pages[0]
        assert page.width_px > 0
        assert page.height_px > 0

        # Write to JSON and validate
        output_path = temp_output_dir / "clean_metadata.json"
        metadata.to_json_file(str(output_path))
        assert output_path.exists()

        # Reload and validate
        loaded = DocumentMetadata.from_json_file(str(output_path))
        assert loaded.document_id == metadata.document_id

    def test_blurry_document_pipeline(self, sample_blurry_image, temp_output_dir):
        """Test pipeline with a blurry document image."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_blur_001",
            file_name="blurry_document.png",
            images=[sample_blurry_image],
        )

        # Blurry document should have lower quality score
        assert metadata.dqs is not None
        assert metadata.dqs.degradation_score < 0.8  # Quality impacted by blur

        # Should detect blur issue
        page = metadata.pages[0]
        blur_issues = [i for i in page.detected_issues if i.type == IssueType.BLUR]
        assert len(blur_issues) > 0

        # Pre-OCR risk should be higher for blurry document
        assert metadata.pre_ocr_risk > 0.1

    def test_noisy_document_pipeline(self, sample_noisy_image, temp_output_dir):
        """Test pipeline with a noisy document image."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_noise_001",
            file_name="noisy_document.png",
            images=[sample_noisy_image],
        )

        # Should detect noise issue
        page = metadata.pages[0]
        noise_issues = [i for i in page.detected_issues if i.type == IssueType.NOISE]
        assert len(noise_issues) > 0

        # Quality should be impacted
        assert metadata.dqs is not None
        assert metadata.dqs.degradation_score < 0.9

    def test_multi_issue_document_pipeline(self, multi_issue_image, temp_output_dir):
        """Test pipeline with a document having multiple issues."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_multi_001",
            file_name="multi_issue_document.png",
            images=[multi_issue_image],
        )

        # Should have multiple detected issues
        page = metadata.pages[0]
        assert len(page.detected_issues) >= 1  # At least blur or noise

        # Quality should be significantly impacted
        assert metadata.dqs is not None
        assert metadata.dqs.degradation_score < 0.85

        # Pre-OCR risk should be elevated
        assert metadata.pre_ocr_risk is not None

    def test_multi_page_document_pipeline(
        self, sample_document_image, sample_blurry_image, temp_output_dir
    ):
        """Test pipeline with multiple pages of varying quality."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_multipage_001",
            file_name="multi_page_document.pdf",
            images=[sample_document_image, sample_blurry_image, sample_document_image],
        )

        assert metadata.num_pages == 3
        assert len(metadata.pages) == 3
        assert len(metadata.page_layout_summary) == 3

        # Verify page indices are correct
        for i, page in enumerate(metadata.pages):
            assert page.page_index == i

        # Verify page numbers in layout summary
        for i, layout in enumerate(metadata.page_layout_summary):
            assert layout.page_number == i + 1

    def test_handoff_json_format(self, sample_document_image, temp_output_dir):
        """Test that output JSON matches Project B handoff specification."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_handoff_001",
            file_name="handoff_test.pdf",
            images=[sample_document_image],
        )

        # Export to JSON
        output_path = temp_output_dir / "handoff_test.json"
        metadata.to_json_file(str(output_path))

        # Load raw JSON and verify structure
        with open(output_path) as f:
            data = json.load(f)

        # Verify required root fields for Project B
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
            assert field in data, f"Missing required field: {field}"

        # Verify DQS structure
        assert "degradation_score" in data["dqs"]
        assert "structural_complexity_score" in data["dqs"]

        # Verify page structure
        assert len(data["pages"]) == 1
        page = data["pages"][0]
        assert "page_index" in page
        assert "width_px" in page
        assert "height_px" in page
        assert "detected_issues" in page

        # Verify page layout summary structure
        assert len(data["page_layout_summary"]) == 1
        layout = data["page_layout_summary"][0]
        assert "page_number" in layout
        assert "layout_type" in layout
        assert "complexity_score" in layout

    def test_routing_strategies(self):
        """Test that routing logic produces correct strategies."""
        processor = DocumentProcessor()

        # High quality, simple layout -> OCR_FAST
        routing = processor.determine_routing(
            degradation_score=0.85,
            complexity_score=0.2,
            has_tables=False,
            has_handwriting=False,
        )
        assert routing == OCRRoutingStrategy.OCR_FAST

        # Has tables -> VISION_STRUCTURED
        routing = processor.determine_routing(
            degradation_score=0.85,
            complexity_score=0.2,
            has_tables=True,
            has_handwriting=False,
        )
        assert routing == OCRRoutingStrategy.VISION_STRUCTURED

        # Has handwriting -> OCR_ADVANCED
        routing = processor.determine_routing(
            degradation_score=0.85,
            complexity_score=0.2,
            has_tables=False,
            has_handwriting=True,
        )
        assert routing == OCRRoutingStrategy.OCR_ADVANCED

        # Low quality -> VISION_SIMPLE
        routing = processor.determine_routing(
            degradation_score=0.3,
            complexity_score=0.3,
            has_tables=False,
            has_handwriting=False,
        )
        assert routing == OCRRoutingStrategy.VISION_SIMPLE

        # High complexity -> VISION_STRUCTURED
        routing = processor.determine_routing(
            degradation_score=0.85,
            complexity_score=0.7,
            has_tables=False,
            has_handwriting=False,
        )
        assert routing == OCRRoutingStrategy.VISION_STRUCTURED

    def test_custom_config(self, sample_document_image):
        """Test pipeline with custom DQS configuration."""
        # Custom config with higher blur weight
        config = DQSWeightConfig(
            blur_weight=0.5,
            noise_weight=0.2,
            contrast_weight=0.15,
            illumination_weight=0.1,
            artifacts_weight=0.05,
        )

        processor = DocumentProcessor(config=config)

        metadata = processor.create_document_metadata(
            document_id="test_config_001",
            file_name="config_test.png",
            images=[sample_document_image],
        )

        # Verify metadata is created with custom config
        assert metadata.dqs is not None
        assert metadata.document_id == "test_config_001"


class TestHandoffValidation:
    """Tests for validating handoff format compliance."""

    def test_schema_validation(self, sample_document_image, temp_output_dir):
        """Test that generated metadata passes schema validation."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_validate_001",
            file_name="validation_test.pdf",
            images=[sample_document_image],
        )

        # Export to JSON
        json_str = metadata.model_dump_json()

        # Re-validate from JSON
        reloaded = DocumentMetadata.model_validate_json(json_str)

        assert reloaded.document_id == metadata.document_id
        assert reloaded.num_pages == metadata.num_pages

    def test_project_b_required_fields(self, sample_document_image):
        """Verify all fields required by Project B are present."""
        processor = DocumentProcessor()

        metadata = processor.create_document_metadata(
            document_id="test_projb_001",
            file_name="project_b_test.pdf",
            images=[sample_document_image],
        )

        # These fields are required for Project B routing
        assert metadata.pdf_type is not None
        assert metadata.dqs is not None
        assert metadata.pre_ocr_risk is not None
        assert metadata.ocr_routing_recommendation is not None
        assert len(metadata.page_layout_summary) > 0
        assert len(metadata.pages) > 0

        # DQS must have both scores
        assert 0 <= metadata.dqs.degradation_score <= 1
        assert 0 <= metadata.dqs.structural_complexity_score <= 1

        # Pre-OCR risk must be valid
        assert 0 <= metadata.pre_ocr_risk <= 1

        # Routing must be a valid strategy
        assert metadata.ocr_routing_recommendation in OCRRoutingStrategy

    def test_page_layout_consistency(self, sample_document_image):
        """Verify page layout summary is consistent with page count."""
        processor = DocumentProcessor()

        images = [sample_document_image] * 3  # 3 pages

        metadata = processor.create_document_metadata(
            document_id="test_layout_001",
            file_name="layout_test.pdf",
            images=images,
        )

        assert len(metadata.page_layout_summary) == metadata.num_pages
        assert len(metadata.pages) == metadata.num_pages

        # Verify page numbers are sequential
        for i, layout in enumerate(metadata.page_layout_summary):
            assert layout.page_number == i + 1

        # Verify page indices are sequential
        for i, page in enumerate(metadata.pages):
            assert page.page_index == i
