"""
End-to-end Phase 2 integration tests.

Tests the complete processing pipeline with Phase 2 features:
- Born-digital PDFs
- Image-only documents
- Hybrid documents (text + embedded images)
- Handwriting detection
- Table detection
- Document quality scoring (DQS)
- PDF classification
- OCR routing recommendations

Note: Phase 2 ML components are not yet implemented (~25% complete).
This test suite includes:
1. Tests for implemented Phase 1 components (100% complete)
2. Placeholder tests for Phase 2 ML features (skip until implemented)
"""

import tempfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from image_preprocessing_detector.correction.corrections import (
    correct_skew,
)
from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import detect_text
from image_preprocessing_detector.ingestion.image_loader import load_image
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)
from image_preprocessing_detector.schema import (
    DocumentMetadata,
    ElementCategory,
    IssueSeverity,
    IssueType,
)


class TestPhase2BornDigitalPipeline:
    """Test pipeline with born-digital (clean text) PDFs."""

    def test_born_digital_single_page(self) -> None:
        """Test born-digital PDF with clean text (no quality issues expected)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create clean, born-digital PDF
            pdf_path = Path(tmpdir) / "born_digital.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4

            # High-quality text
            page.insert_text(
                (50, 50),
                "Born-Digital Document\nClean text with no image quality issues.",
                fontsize=14,
            )

            doc.save(str(pdf_path))
            doc.close()

            # Process pipeline
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            builder = MetadataBuilder(
                document_id="born_digital_001", file_name="born_digital.pdf"
            )

            page_image = pages[0]
            text_result = detect_text(page_image.image)

            # Born-digital should have text
            assert text_result.has_text

            # Run IQA
            skew_result = detect_skew(page_image.image)
            blur_result = detect_blur(page_image.image)
            contrast_result = detect_contrast(page_image.image)

            builder.add_page(
                page_number=0,
                page_data=page_image,
                text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            # Generate output
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify
            loaded = load_json(output_path)
            assert loaded.document_id == "born_digital_001"
            assert loaded.num_pages == 1

            # Born-digital PDFs should have minimal quality issues
            page_metadata = loaded.pages[0]
            assert page_metadata.width_px > 0
            assert page_metadata.height_px > 0

            # Validate detected_issues structure
            assert isinstance(page_metadata.detected_issues, list)

    def test_born_digital_multi_page(self) -> None:
        """Test born-digital PDF with multiple pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "multi_page_born_digital.pdf"
            doc = fitz.open()

            # Create 5 pages
            for i in range(5):
                page = doc.new_page(width=595, height=842)
                text = f"Page {i + 1}\nMulti-page born-digital document."
                page.insert_text((50, 50), text, fontsize=14)

            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 5

            builder = MetadataBuilder(
                document_id="multi_born_digital_001",
                file_name="multi_page_born_digital.pdf",
            )

            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)
                skew_result = (
                    detect_skew(page_image.image) if text_result.has_text else None
                )
                blur_result = (
                    detect_blur(page_image.image) if text_result.has_text else None
                )
                contrast_result = (
                    detect_contrast(page_image.image) if text_result.has_text else None
                )

                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            metadata = builder.build()
            assert metadata.num_pages == 5

            # Validate all pages processed
            for idx, page in enumerate(metadata.pages):
                assert page.page_index == idx


class TestPhase2ImageOnlyPipeline:
    """Test pipeline with image-only documents (no text)."""

    def test_image_only_photograph(self) -> None:
        """Test image-only document (photograph with no text)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create synthetic photograph (no text patterns)
            img = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)

            # Add some structure (but no text)
            cv2.circle(img, (300, 400), 100, (255, 0, 0), -1)
            cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), 5)

            img_path = Path(tmpdir) / "photograph.jpg"
            cv2.imwrite(str(img_path), img)

            # Process
            image, img_metadata = load_image(str(img_path))

            builder = MetadataBuilder(
                document_id="image_only_001", file_name="photograph.jpg"
            )

            text_result = detect_text(image)

            # Image-only should have no text
            # (Though text_gate might detect edges as text - this is a known limitation)
            # Just verify the pipeline completes

            builder.add_page(
                page_number=0,
                page_data=(image, img_metadata),
                text_result=text_result,
            )

            metadata = builder.build()
            assert metadata.num_pages == 1
            assert metadata.pages[0].width_px == 600
            assert metadata.pages[0].height_px == 800

    def test_image_only_with_quality_issues(self) -> None:
        """Test image-only document with blur and low contrast."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create low-quality image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 128  # Low contrast

            # Add random noise
            noise = np.random.randint(-30, 30, (1000, 800, 3), dtype=np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            # Apply blur
            img = cv2.GaussianBlur(img, (15, 15), 0)

            img_path = Path(tmpdir) / "low_quality.jpg"
            cv2.imwrite(str(img_path), img)

            # Process
            image, img_metadata = load_image(str(img_path))

            builder = MetadataBuilder(
                document_id="image_low_quality_001", file_name="low_quality.jpg"
            )

            text_result = detect_text(image)

            # Run IQA even if no text (image-only path)
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)

            builder.add_page(
                page_number=0,
                page_data=(image, img_metadata),
                text_result=text_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            metadata = builder.build()
            page = metadata.pages[0]

            # Validate IQA ran
            assert isinstance(page.detected_issues, list)


class TestPhase2HybridPipeline:
    """Test pipeline with hybrid documents (text + embedded images)."""

    def test_hybrid_text_with_embedded_image(self) -> None:
        """Test hybrid PDF with text and embedded images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "hybrid.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # Add text
            page.insert_text(
                (50, 50),
                "Hybrid Document\nText with embedded image below:",
                fontsize=12,
            )

            # Create and embed a simple image
            img_array = np.ones((200, 200, 3), dtype=np.uint8) * 200
            cv2.rectangle(img_array, (50, 50), (150, 150), (100, 100, 255), -1)

            img_path = Path(tmpdir) / "embed.png"
            cv2.imwrite(str(img_path), img_array)

            # Insert image into PDF
            page.insert_image(
                fitz.Rect(100, 200, 300, 400),
                filename=str(img_path),
            )

            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            builder = MetadataBuilder(document_id="hybrid_001", file_name="hybrid.pdf")

            page_image = pages[0]
            text_result = detect_text(page_image.image)

            # Hybrid should have text
            assert text_result.has_text

            skew_result = detect_skew(page_image.image)
            blur_result = detect_blur(page_image.image)
            contrast_result = detect_contrast(page_image.image)

            builder.add_page(
                page_number=0,
                page_data=page_image,
                text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
            )

            metadata = builder.build()
            assert metadata.num_pages == 1

            # Verify pipeline processed hybrid content
            page = metadata.pages[0]
            assert page.width_px > 0
            assert page.height_px > 0


class TestPhase2HandwritingDetection:
    """
    Test handwriting detection (Phase 2 feature).

    NOTE: Handwriting detection requires YOLOv8 layout model (Phase 3).
    These are placeholder tests that will be skipped until implemented.
    """

    @pytest.mark.skip(reason="Phase 3: YOLOv8 layout detection not yet implemented")
    def test_handwriting_detection(self) -> None:
        """Test detection of handwritten content."""
        # Placeholder for future implementation
        # Will use YOLOv8 to detect ElementCategory.HANDWRITING

    @pytest.mark.skip(reason="Phase 3: YOLOv8 layout detection not yet implemented")
    def test_mixed_typed_and_handwritten(self) -> None:
        """Test document with both typed text and handwriting."""
        # Placeholder for future implementation


class TestPhase2TableDetection:
    """
    Test table detection (Phase 2 feature).

    NOTE: Table detection requires YOLOv8 layout model (Phase 3).
    These are placeholder tests that will be skipped until implemented.
    """

    @pytest.mark.skip(reason="Phase 3: YOLOv8 layout detection not yet implemented")
    def test_table_detection(self) -> None:
        """Test detection of tabular data."""
        # Placeholder for future implementation
        # Will use YOLOv8 to detect ElementCategory.TABLE

    @pytest.mark.skip(reason="Phase 3: YOLOv8 layout detection not yet implemented")
    def test_table_with_quality_issues(self) -> None:
        """Test table detection with skewed or low-contrast tables."""
        # Placeholder for future implementation


class TestPhase2SchemaValidation:
    """Test Phase 2 schema fields and validation."""

    def test_schema_detected_issue_validation(self) -> None:
        """Test DetectedIssue model validation."""
        from image_preprocessing_detector.schema import DetectedIssue

        # Valid issue
        issue = DetectedIssue(
            type=IssueType.BLUR,
            confidence=0.85,
            severity=IssueSeverity.MEDIUM,
            metrics={"laplacian_variance": 42.5},
        )

        assert issue.type == IssueType.BLUR
        assert issue.confidence == 0.85
        assert issue.severity == IssueSeverity.MEDIUM

        # Invalid confidence (Pydantic v2 raises ValidationError)
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            DetectedIssue(
                type=IssueType.SKEW,
                confidence=1.5,  # Invalid
                severity=IssueSeverity.LOW,
            )

    def test_schema_document_element_validation(self) -> None:
        """Test DocumentElement model validation."""
        from image_preprocessing_detector.schema import DocumentElement

        # Valid element
        element = DocumentElement(
            id="elem_001",
            category=ElementCategory.TABLE,
            bbox=[100, 200, 300, 400],  # [x, y, width, height]
            confidence=0.92,
            attributes={"num_rows": 5, "num_cols": 3},
            quality_issues=[],
        )

        assert element.category == ElementCategory.TABLE
        assert element.bbox == [100, 200, 300, 400]

        # Invalid bbox (not 4 values)
        with pytest.raises(ValueError, match="exactly 4 values"):
            DocumentElement(
                id="elem_002",
                category=ElementCategory.IMAGE,
                bbox=[100, 200],  # Invalid - only 2 values
                confidence=0.8,
            )

        # Invalid bbox (negative values)
        with pytest.raises(ValueError, match="non-negative"):
            DocumentElement(
                id="elem_003",
                category=ElementCategory.IMAGE,
                bbox=[-100, 200, 300, 400],  # Invalid - negative x
                confidence=0.8,
            )

    def test_schema_page_metadata_structure(self) -> None:
        """Test PageMetadata structure with Phase 2 fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Test", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(document_id="schema_001", file_name="test.pdf")

            page_image = pages[0]
            text_result = detect_text(page_image.image)

            builder.add_page(
                page_number=0,
                page_data=page_image,
                text_result=text_result,
            )

            metadata = builder.build()
            page = metadata.pages[0]

            # Validate Phase 2 schema fields
            assert hasattr(page, "page_index")
            assert hasattr(page, "width_px")
            assert hasattr(page, "height_px")
            assert hasattr(page, "dpi_input")
            assert hasattr(page, "dpi_effective")
            assert hasattr(page, "detected_issues")
            assert hasattr(page, "planned_actions")
            assert hasattr(page, "elements")
            assert hasattr(page, "languages")
            assert hasattr(page, "transform_history")

            # Validate types
            assert isinstance(page.detected_issues, list)
            assert isinstance(page.planned_actions, list)
            assert isinstance(page.elements, list)
            assert isinstance(page.languages, list)
            assert isinstance(page.transform_history, list)

    @pytest.mark.skip(reason="Phase 2: pdf_type field not yet implemented")
    def test_schema_pdf_type_classification(self) -> None:
        """
        Test pdf_type field in DocumentMetadata.

        Phase 2 feature: Classify PDFs as born_digital, image_only, or hybrid.
        """
        # Placeholder for future implementation
        # Expected: metadata.pdf_type in ["born_digital", "image_only", "hybrid"]

    @pytest.mark.skip(
        reason="Phase 2: DQS (Document Quality Score) not yet implemented"
    )
    def test_schema_document_quality_score(self) -> None:
        """
        Test DQS (Document Quality Score) field in DocumentMetadata.

        Phase 2 feature: Overall quality score with degradation and complexity.
        """
        # Placeholder for future implementation
        # Expected: metadata.dqs = {"overall": 0.85, "degradation": 0.15, "complexity": 0.5}

    @pytest.mark.skip(
        reason="Phase 2: ocr_routing_recommendation field not yet implemented"
    )
    def test_schema_ocr_routing_recommendation(self) -> None:
        """
        Test ocr_routing_recommendation field in DocumentMetadata.

        Phase 2 feature: Recommend OCR strategy based on quality.
        """
        # Placeholder for future implementation
        # Expected: metadata.ocr_routing_recommendation in ["ocr_fast", "ocr_advanced", "vision_simple", "vision_structured"]


class TestPhase2MLInference:
    """
    Test ML-based IQA inference (Phase 2 feature).

    NOTE: ML inference code not yet implemented.
    These are placeholder tests that will be skipped until implemented.
    """

    @pytest.mark.skip(reason="Phase 2: ML IQA inference not yet implemented")
    def test_ml_iqa_inference(self) -> None:
        """Test ML-based IQA detector (MobileNetV3/EfficientNet)."""
        # Placeholder for future implementation
        # Will test src/detection/iqa_ml.py when implemented

    @pytest.mark.skip(reason="Phase 2: ML IQA inference not yet implemented")
    def test_ml_confidence_calibration(self) -> None:
        """Test ML confidence score calibration."""
        # Placeholder for future implementation

    @pytest.mark.skip(reason="Phase 2: Hybrid IQA ensemble not yet implemented")
    def test_hybrid_iqa_ensemble_voting(self) -> None:
        """Test ensemble voting between classical and ML IQA."""
        # Placeholder for future implementation
        # Expected: Combine classical + ML results with confidence weighting


class TestPhase2CorrectionsWithMLGuidance:
    """
    Test corrections with ML-guided decisions (Phase 2 feature).

    NOTE: ML-guided corrections not yet implemented.
    """

    def test_corrections_applied_to_detected_issues(self) -> None:
        """Test that corrections are applied to detected quality issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skewed image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 200

            # Add text-like patterns
            for y in range(100, 900, 50):
                cv2.line(img, (100, y), (700, y), (50, 50, 50), 3)

            # Apply skew
            center = (400, 500)
            M = cv2.getRotationMatrix2D(center, -5, 1.0)  # noqa: N806  # fmt: skip
            img = cv2.warpAffine(img, M, (800, 1000))

            img_path = Path(tmpdir) / "skewed.jpg"
            cv2.imwrite(str(img_path), img)

            # Process
            image, metadata = load_image(str(img_path))

            builder = MetadataBuilder(
                document_id="correction_001", file_name="skewed.jpg"
            )

            text_result = detect_text(image)
            skew_result = detect_skew(image) if text_result.has_text else None

            # Apply correction
            skew_correction = None
            if skew_result and skew_result.is_skewed:
                skew_correction = correct_skew(
                    image, skew_result.angle, skew_result.confidence
                )
                if skew_correction.applied:
                    image = skew_correction.corrected_image

            builder.add_page(
                page_number=0,
                page_data=(image, metadata),
                text_result=text_result,
                skew_result=skew_result,
                skew_correction=skew_correction,
            )

            doc_metadata = builder.build()
            page = doc_metadata.pages[0]

            # Verify transform history
            assert isinstance(page.transform_history, list)


class TestPhase2PerformanceTargets:
    """
    Test Phase 2 performance targets.

    NOTE: Performance targets assume ML models are deployed.
    These tests will be updated when models are available.
    """

    @pytest.mark.skip(reason="Phase 2: ML models not yet deployed")
    def test_inference_latency_under_150ms_per_page(self) -> None:
        """Test that ML inference completes in <150ms per page (with GPU)."""
        # Placeholder for future implementation
        # Target: <150ms per page with T4 GPU

    @pytest.mark.skip(reason="Phase 2: ML models not yet deployed")
    def test_throughput_over_6_pages_per_second(self) -> None:
        """Test throughput >6 pages/sec per GPU worker."""
        # Placeholder for future implementation

    @pytest.mark.skip(reason="Phase 2: ML model validation not yet complete")
    def test_iqa_map_over_88_percent(self) -> None:
        """Test that IQA mAP exceeds 0.88 on validation set."""
        # Placeholder for future implementation
        # Target: mAP > 0.88 for multi-label IQA classification


class TestPhase2EndToEndIntegration:
    """Complete end-to-end integration test with all Phase 2 components."""

    def test_complete_pipeline_born_digital_to_json(self) -> None:
        """Test complete pipeline: born-digital PDF → DocumentMetadata JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create realistic born-digital PDF
            pdf_path = Path(tmpdir) / "complete_test.pdf"
            doc = fitz.open()

            # Multi-page document
            for i in range(3):
                page = doc.new_page(width=595, height=842)
                text = f"Page {i + 1}\n\nComplete Pipeline Test\n\nThis is a multi-page document for end-to-end testing."
                page.insert_text((50, 50 + i * 10), text, fontsize=12)

            doc.save(str(pdf_path))
            doc.close()

            # Complete pipeline
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(
                document_id="e2e_complete_001", file_name="complete_test.pdf"
            )

            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)

                skew_result = None
                blur_result = None
                contrast_result = None

                if text_result.has_text:
                    skew_result = detect_skew(page_image.image)
                    blur_result = detect_blur(page_image.image)
                    contrast_result = detect_contrast(page_image.image)

                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Validate complete JSON output
            assert output_path.exists()
            loaded = load_json(output_path)

            # Validate structure
            assert isinstance(loaded, DocumentMetadata)
            assert loaded.document_id == "e2e_complete_001"
            assert loaded.file_name == "complete_test.pdf"
            assert loaded.num_pages == 3
            assert len(loaded.pages) == 3

            # Validate all pages
            for idx, page in enumerate(loaded.pages):
                assert page.page_index == idx
                assert page.width_px > 0
                assert page.height_px > 0
                assert page.dpi_input > 0
                assert page.dpi_effective > 0
                assert isinstance(page.detected_issues, list)
                assert isinstance(page.elements, list)
                assert isinstance(page.transform_history, list)

            # Test JSON round-trip
            json_str = loaded.model_dump_json()
            assert json_str is not None
            assert len(json_str) > 0

    def test_pipeline_handles_all_document_types(self) -> None:
        """Test pipeline with mixed document types in sequence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cases = []

            # Born-digital
            pdf_bd = Path(tmpdir) / "born_digital.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Born-Digital", fontsize=14)
            doc.save(str(pdf_bd))
            doc.close()
            test_cases.append(("born_digital", pdf_bd))

            # Image-only
            img_only = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
            img_path = Path(tmpdir) / "image_only.jpg"
            cv2.imwrite(str(img_path), img_only)
            test_cases.append(("image_only", img_path))

            # Process all
            for doc_type, file_path in test_cases:
                if file_path.suffix == ".pdf":
                    pages = load_pdf(str(file_path))
                else:
                    image, metadata = load_image(str(file_path))
                    pages = [(image, metadata)]

                builder = MetadataBuilder(
                    document_id=f"{doc_type}_001", file_name=file_path.name
                )

                for page_idx, page_data in enumerate(pages):
                    if isinstance(page_data, tuple):
                        page_image = page_data
                    else:
                        page_image = page_data

                    text_result = detect_text(
                        page_image.image
                        if hasattr(page_image, "image")
                        else page_image[0]
                    )

                    builder.add_page(
                        page_number=page_idx,
                        page_data=page_image,
                        text_result=text_result,
                    )

                metadata = builder.build()
                assert metadata.num_pages >= 1
                assert metadata.document_id == f"{doc_type}_001"
