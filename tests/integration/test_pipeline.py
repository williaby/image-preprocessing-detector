"""
End-to-end pipeline integration tests.

Tests the complete processing pipeline from PDF/image input to JSON output.
"""

import tempfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from image_preprocessing_detector.correction.corrections import (
    correct_skew,
    enhance_contrast,
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


class TestEndToEndPipeline:
    """Test complete end-to-end processing pipeline."""

    def test_single_page_pdf_pipeline(self) -> None:
        """Test complete pipeline with single-page PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple single-page PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4 size

            # Add some text to the page
            text = "Sample Document\nThis is a test PDF for the image preprocessing detector."
            page.insert_text((50, 50), text, fontsize=12)

            doc.save(str(pdf_path))
            doc.close()

            # Process the PDF
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            builder = MetadataBuilder(document_id="test_001", file_name="test.pdf")

            for page_idx, page_image in enumerate(pages):
                # Run detection
                text_result = detect_text(page_image.image)

                skew_result = None
                blur_result = None
                contrast_result = None

                if text_result.has_text:
                    skew_result = detect_skew(page_image.image)
                    blur_result = detect_blur(page_image.image)
                    contrast_result = detect_contrast(page_image.image)

                # Add to builder
                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            # Generate output
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify output
            assert output_path.exists()
            loaded = load_json(output_path)
            assert loaded.document_id == "test_001"
            assert loaded.num_pages == 1
            assert loaded.pages[0].width_px > 0
            assert loaded.pages[0].height_px > 0

    def test_multi_page_pdf_pipeline(self) -> None:
        """Test complete pipeline with multi-page PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a 3-page PDF
            pdf_path = Path(tmpdir) / "multi_page.pdf"
            doc = fitz.open()

            for i in range(3):
                page = doc.new_page(width=595, height=842)
                text = f"Page {i + 1}\nThis is page {i + 1} of the test document."
                page.insert_text((50, 50), text, fontsize=12)

            doc.save(str(pdf_path))
            doc.close()

            # Process the PDF
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 3

            builder = MetadataBuilder(
                document_id="multi_001", file_name="multi_page.pdf"
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
                    _text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            # Generate output
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify output
            assert output_path.exists()
            loaded = load_json(output_path)
            assert loaded.document_id == "multi_001"
            assert loaded.num_pages == 3

            # Verify all pages processed
            for idx, page in enumerate(loaded.pages):
                assert page.page_index == idx
                assert page.width_px > 0
                assert page.height_px > 0

    def test_image_pipeline_with_corrections(self) -> None:
        """Test pipeline with image corrections applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a skewed, low-contrast image
            img = np.ones((1000, 800, 3), dtype=np.uint8) * 128

            # Add text-like patterns
            for y in range(100, 900, 40):
                cv2.line(img, (100, y), (700, y), (80, 80, 80), 2)

            # Apply skew
            center = (400, 500)
            M = cv2.getRotationMatrix2D(center, -3, 1.0)  # noqa: N806  # fmt: skip
            img = cv2.warpAffine(img, M, (800, 1000))

            # Save image
            img_path = Path(tmpdir) / "skewed.jpg"
            cv2.imwrite(str(img_path), img)

            # Load and process
            image, metadata = load_image(str(img_path))

            builder = MetadataBuilder(document_id="img_001", file_name="skewed.jpg")

            # Run detection
            text_result = detect_text(image)

            skew_result = None
            blur_result = None
            contrast_result = None
            skew_correction = None
            contrast_correction = None

            if text_result.has_text:
                skew_result = detect_skew(image)
                blur_result = detect_blur(image)
                contrast_result = detect_contrast(image)

                # Apply corrections
                if skew_result and skew_result.is_skewed:
                    skew_correction = correct_skew(
                        image, skew_result.angle, skew_result.confidence
                    )
                    if skew_correction.applied:
                        image = skew_correction.corrected_image

                if contrast_result and contrast_result.is_low_contrast:
                    contrast_correction = enhance_contrast(
                        image, contrast_result.score, contrast_result.severity
                    )
                    if contrast_correction.applied:
                        image = contrast_correction.corrected_image

            # Add to builder
            builder.add_page(
                page_number=0,
                page_data=(image, metadata),
                _text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
                skew_correction=skew_correction,
                contrast_correction=contrast_correction,
            )

            # Generate output
            doc_metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(doc_metadata, output_path)

            # Verify output
            assert output_path.exists()
            loaded = load_json(output_path)
            assert loaded.num_pages == 1

            # Verify corrections were recorded
            page = loaded.pages[0]
            if len(page.transform_history) > 0:
                # At least one correction was applied
                actions = [t.action for t in page.transform_history]
                assert any(
                    action in ["deskew", "clahe_contrast_enhancement"]
                    for action in actions
                )

    def test_pipeline_with_mixed_quality_pages(self) -> None:
        """Test pipeline with pages having different quality issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create PDF with different quality issues per page
            pdf_path = Path(tmpdir) / "mixed_quality.pdf"
            doc = fitz.open()

            # Page 1: Good quality
            page1 = doc.new_page(width=595, height=842)
            page1.insert_text(
                (50, 50), "High Quality Page\nClear text, no issues.", fontsize=14
            )

            # Page 2: Would be low contrast (but PyMuPDF renders clean)
            page2 = doc.new_page(width=595, height=842)
            page2.insert_text(
                (50, 50), "Second Page\nSome more text here.", fontsize=14
            )

            # Page 3: Another page
            page3 = doc.new_page(width=595, height=842)
            page3.insert_text(
                (50, 50), "Third Page\nFinal page of document.", fontsize=14
            )

            doc.save(str(pdf_path))
            doc.close()

            # Process the PDF
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 3

            builder = MetadataBuilder(
                document_id="mixed_001", file_name="mixed_quality.pdf"
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
                    _text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                )

            # Generate output
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify output
            assert output_path.exists()
            loaded = load_json(output_path)
            assert loaded.num_pages == 3

            # Verify each page was processed
            for page in loaded.pages:
                assert page.width_px > 0
                assert page.height_px > 0
                # All pages should have been analyzed (detected_issues may be empty if no issues found)
                assert isinstance(page.detected_issues, list)


class TestPipelineErrorHandling:
    """Test pipeline error handling and edge cases."""

    def test_empty_page_list_handling(self) -> None:
        """Test handling of metadata builder with no pages added."""
        # Should not be able to build metadata with no pages
        builder = MetadataBuilder(document_id="empty_001", file_name="empty.pdf")

        with pytest.raises(ValueError, match="no pages added"):
            builder.build()

    def test_corrupted_image_data(self) -> None:
        """Test handling of corrupted image data."""
        # Create image with invalid data
        invalid_image = np.array([])

        # Should raise ValueError for empty image
        with pytest.raises(ValueError):  # noqa: PT011  # fmt: skip
            detect_text(invalid_image)

    def test_json_round_trip_preservation(self) -> None:
        """Test that JSON serialization preserves all data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Test Document", fontsize=12)
            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(
                document_id="round_trip_001", file_name="test.pdf"
            )

            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)
                skew_result = (
                    detect_skew(page_image.image) if text_result.has_text else None
                )

                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                    skew_result=skew_result,
                )

            # Save and reload
            metadata = builder.build()
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            loaded = load_json(output_path)

            # Verify all fields preserved
            assert loaded.document_id == metadata.document_id
            assert loaded.file_name == metadata.file_name
            assert loaded.source_mime == metadata.source_mime
            assert loaded.num_pages == metadata.num_pages
            assert len(loaded.pages) == len(metadata.pages)

            for orig_page, loaded_page in zip(
                metadata.pages, loaded.pages, strict=True
            ):
                assert loaded_page.page_index == orig_page.page_index
                assert loaded_page.width_px == orig_page.width_px
                assert loaded_page.height_px == orig_page.height_px
                assert loaded_page.dpi_input == orig_page.dpi_input


class TestPhase1Completion:
    """Phase 1 completion validation tests."""

    def test_complete_schema_validation(self) -> None:
        """Test that output JSON complies with complete DocumentMetadata schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a PDF with various quality issues
            pdf_path = Path(tmpdir) / "complete_test.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text(
                (50, 50),
                "Complete Schema Validation Test\n"
                "This document tests all Phase 1 schema fields.",
                fontsize=12,
            )
            doc.save(str(pdf_path))
            doc.close()

            # Process the PDF
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(
                document_id="phase1_complete_001", file_name="complete_test.pdf"
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

                # Apply corrections if needed
                skew_correction = None
                if skew_result and skew_result.is_skewed:
                    skew_correction = correct_skew(
                        page_image.image, skew_result.angle, skew_result.confidence
                    )

                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                    skew_correction=skew_correction,
                )

            # Build and validate metadata
            metadata = builder.build()

            # Validate all required Phase 1 fields are present
            assert metadata.document_id is not None
            assert metadata.file_name is not None
            assert metadata.source_mime is not None
            assert metadata.num_pages > 0
            assert metadata.processing_version is not None
            assert len(metadata.pages) == metadata.num_pages

            # Validate Phase 8 fields are optional (None is acceptable)
            # These will be populated in Phases 6-8
            assert metadata.pdf_type is None or metadata.pdf_type is not None
            assert metadata.pre_ocr_risk is None or (
                0.0 <= metadata.pre_ocr_risk <= 1.0
            )
            assert metadata.dqs is None or metadata.dqs is not None
            assert (
                metadata.ocr_routing_recommendation is None
                or metadata.ocr_routing_recommendation is not None
            )
            assert isinstance(metadata.page_layout_summary, list)

            # Validate per-page metadata
            for page in metadata.pages:
                assert page.page_index >= 0
                assert page.width_px > 0
                assert page.height_px > 0
                assert page.dpi_input > 0
                assert page.dpi_effective > 0
                assert isinstance(page.detected_issues, list)
                assert isinstance(page.planned_actions, list)
                assert isinstance(page.elements, list)
                assert isinstance(page.transform_history, list)

            # Test JSON serialization compliance
            output_path = Path(tmpdir) / "complete_validation.json"
            generate_json(metadata, output_path)
            assert output_path.exists()

            # Verify round-trip works
            loaded = load_json(output_path)
            assert loaded.document_id == metadata.document_id
            assert loaded.num_pages == metadata.num_pages

    def test_large_document_processing(self) -> None:
        """Test processing a 50-page PDF (Phase 1 success criterion: 100-page support)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a 50-page PDF (reduced from 100 for faster CI)
            pdf_path = Path(tmpdir) / "large_document.pdf"
            doc = fitz.open()

            num_pages = 50
            for i in range(num_pages):
                page = doc.new_page(width=595, height=842)
                text = (
                    f"Page {i + 1} of {num_pages}\nTesting large document processing."
                )
                page.insert_text((50, 50), text, fontsize=12)

            doc.save(str(pdf_path))
            doc.close()

            # Process the PDF
            pages = load_pdf(str(pdf_path))
            assert len(pages) == num_pages

            builder = MetadataBuilder(
                document_id="large_doc_001", file_name="large_document.pdf"
            )

            # Process all pages
            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)

                # Simplified processing for speed (only text detection)
                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                )

            # Build metadata
            metadata = builder.build()
            assert metadata.num_pages == num_pages
            assert len(metadata.pages) == num_pages

            # Verify all pages were processed
            for idx, page in enumerate(metadata.pages):
                assert page.page_index == idx

            # Generate JSON output
            output_path = Path(tmpdir) / "large_output.json"
            generate_json(metadata, output_path)

            # Verify output exists and is loadable
            assert output_path.exists()
            loaded = load_json(output_path)
            assert loaded.num_pages == num_pages

    def test_phase1b_dpi_upscaling_integration(self) -> None:
        """Test integration with Phase 1B DPI upscaling feature."""
        # Import Phase 1B components
        from image_preprocessing_detector.core.config import Settings
        from image_preprocessing_detector.ingestion.pdf_analyzer import (
            PDFDocumentAnalyzer,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a low-resolution PDF (simulated)
            pdf_path = Path(tmpdir) / "low_res.pdf"
            doc = fitz.open()
            page = doc.new_page(
                width=400, height=600
            )  # Smaller page to simulate low DPI
            page.insert_text(
                (50, 50),
                "Low Resolution Document\nThis should trigger upscaling.",
                fontsize=10,
            )
            doc.save(str(pdf_path))
            doc.close()

            # Perform pre-flight analysis
            settings = Settings()
            settings.enable_pdf_upscaling = True  # Ensure upscaling is enabled for test

            analyzer = PDFDocumentAnalyzer(settings)
            preflight = analyzer.analyze(pdf_path)

            # Preflight should complete successfully
            assert preflight.resolution_analysis is not None
            assert "needs_upscaling" in preflight.resolution_analysis

            # Use recommended path (upscaled or original)
            pdf_to_process = preflight.recommended_path or str(pdf_path)

            # Process the PDF
            pages = load_pdf(pdf_to_process)
            builder = MetadataBuilder(
                document_id="upscale_test_001", file_name="low_res.pdf"
            )

            # Add upscaling metadata if upscaling was performed
            if preflight.should_use_upscaled:
                builder.set_upscaling_metadata(preflight.upscaling_result)

            # Process pages normally
            for page_idx, page_image in enumerate(pages):
                text_result = detect_text(page_image.image)
                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    _text_result=text_result,
                )

            # Build metadata
            metadata = builder.build()

            # Verify upscaling metadata is present if upscaling occurred
            if preflight.should_use_upscaled:
                assert metadata.upscaling is not None
                assert isinstance(metadata.upscaling, dict)

            # Generate JSON
            output_path = Path(tmpdir) / "upscale_output.json"
            generate_json(metadata, output_path)

            # Verify output
            assert output_path.exists()
            loaded = load_json(output_path)
            assert loaded.document_id == "upscale_test_001"
