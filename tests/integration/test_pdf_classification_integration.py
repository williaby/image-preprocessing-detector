"""
Integration tests for PDF classification in the ingestion pipeline.

Tests the complete end-to-end flow from PDF ingestion to metadata generation
with PDF type classification.
"""

from pathlib import Path

import fitz  # PyMuPDF
import pytest
from PIL import Image

from image_preprocessing_detector.ingestion.document_processor import (
    DocumentProcessor,
    process_document,
)
from image_preprocessing_detector.schema import PDFType


def process_pdf_document(pdf_path: Path):
    """Helper function to process a PDF document.

    Wraps the DocumentProcessor for backward compatibility with tests.
    """
    return process_document(pdf_path)


class TestPDFClassificationIntegration:
    """Integration tests for PDF classification in document processing."""

    def test_process_born_digital_pdf_end_to_end(self, tmp_path: Path) -> None:
        """Test complete processing of a born-digital PDF."""
        pdf_path = tmp_path / "born_digital.pdf"

        # Create text-only PDF (>50 characters, no images)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(
            (100, 100),
            "This is a born-digital document with sufficient text content.",
        )
        page.insert_text((100, 150), "It contains only extractable text, no images.")
        doc.save(str(pdf_path))
        doc.close()

        # Process document
        metadata = process_pdf_document(pdf_path)

        # Verify metadata
        assert metadata.pdf_type == PDFType.BORN_DIGITAL
        assert metadata.file_name == "born_digital.pdf"
        assert metadata.source_mime == "application/pdf"
        assert metadata.num_pages == 1
        assert len(metadata.pages) == 1
        assert metadata.processing_version.pipeline_version == "0.1.0"

        # Verify page metadata
        page_meta = metadata.pages[0]
        assert page_meta.page_index == 0
        assert page_meta.width_px > 0
        assert page_meta.height_px > 0
        assert page_meta.dpi_effective == 300  # Default target DPI

    def test_process_image_only_pdf_end_to_end(self, tmp_path: Path) -> None:
        """Test complete processing of an image-only PDF."""
        pdf_path = tmp_path / "image_only.pdf"

        # Create image
        img = Image.new("RGB", (200, 200), color="blue")
        img_path = tmp_path / "test_image.jpg"
        img.save(str(img_path))

        # Create image-only PDF (minimal text, has images)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(100, 100, 400, 400), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Process document
        metadata = process_pdf_document(pdf_path)

        # Verify metadata
        assert metadata.pdf_type == PDFType.IMAGE_ONLY
        assert metadata.file_name == "image_only.pdf"
        assert metadata.num_pages == 1

    def test_process_hybrid_pdf_end_to_end(self, tmp_path: Path) -> None:
        """Test complete processing of a hybrid PDF."""
        pdf_path = tmp_path / "hybrid.pdf"

        # Create image
        img = Image.new("RGB", (150, 150), color="green")
        img_path = tmp_path / "figure.jpg"
        img.save(str(img_path))

        # Create hybrid PDF (text + images)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Report with text and figures.")
        page.insert_image(fitz.Rect(100, 200, 250, 350), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        # Process document
        metadata = process_pdf_document(pdf_path)

        # Verify metadata
        assert metadata.pdf_type == PDFType.HYBRID
        assert metadata.file_name == "hybrid.pdf"
        assert metadata.num_pages == 1

    def test_process_multipage_pdf(self, tmp_path: Path) -> None:
        """Test processing of a multi-page PDF."""
        pdf_path = tmp_path / "multipage.pdf"

        # Create multi-page text PDF
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text(
                (100, 100),
                f"Page {i + 1} content with sufficient text for classification.",
            )
        doc.save(str(pdf_path))
        doc.close()

        # Process document
        metadata = process_pdf_document(pdf_path)

        # Verify metadata
        assert metadata.pdf_type == PDFType.BORN_DIGITAL
        assert metadata.num_pages == 3
        assert len(metadata.pages) == 3

        # Verify all pages are processed
        for i, page_meta in enumerate(metadata.pages):
            assert page_meta.page_index == i

    def test_document_processor_with_custom_document_id(self, tmp_path: Path) -> None:
        """Test document processor with custom document ID."""
        pdf_path = tmp_path / "test.pdf"

        # Create simple PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Test document for custom ID.")
        doc.save(str(pdf_path))
        doc.close()

        # Process with custom ID
        custom_id = "custom-doc-123"
        processor = DocumentProcessor()
        metadata = processor.process_document(pdf_path, document_id=custom_id)

        # Verify custom ID is used
        assert metadata.document_id == custom_id

    def test_document_processor_generates_id_when_no_id_provided(
        self, tmp_path: Path
    ) -> None:
        """Test that document processor generates an ID when no ID provided."""
        pdf_path = tmp_path / "test.pdf"

        # Create simple PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Test document for auto ID.")
        doc.save(str(pdf_path))
        doc.close()

        # Process without ID
        metadata = process_pdf_document(pdf_path)

        # Verify ID is generated (format: doc_{filestem}_{timestamp})
        assert isinstance(metadata.document_id, str)
        assert len(metadata.document_id) > 0
        assert metadata.document_id.startswith("doc_")
        assert "test" in metadata.document_id  # File stem included

    def test_processing_version_includes_thresholds(self, tmp_path: Path) -> None:
        """Test that processing version includes classification thresholds."""
        pdf_path = tmp_path / "test.pdf"

        # Create simple PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Test document for threshold tracking.")
        doc.save(str(pdf_path))
        doc.close()

        # Process document
        metadata = process_pdf_document(pdf_path)

        # Verify thresholds are tracked
        thresholds = metadata.processing_version.thresholds
        assert "pdf_text_min_threshold" in thresholds
        assert "pdf_text_max_threshold" in thresholds
        assert thresholds["pdf_text_min_threshold"] == 10  # Default
        assert thresholds["pdf_text_max_threshold"] == 50  # Default

    def test_metadata_json_serialization(self, tmp_path: Path) -> None:
        """Test that metadata can be serialized to JSON."""
        pdf_path = tmp_path / "test.pdf"

        # Create simple PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(
            (100, 100), "Test document for JSON serialization with sufficient text."
        )
        doc.save(str(pdf_path))
        doc.close()

        # Process document
        metadata = process_pdf_document(pdf_path)

        # Test JSON serialization
        json_str = metadata.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        assert "born_digital" in json_str  # PDF type should be in JSON
        assert "application/pdf" in json_str  # Source MIME should be in JSON

        # Test saving to file
        json_path = tmp_path / "metadata.json"
        metadata.to_json_file(str(json_path))
        assert json_path.exists()

        # Test loading from file
        from image_preprocessing_detector.schema import DocumentMetadata

        loaded_metadata = DocumentMetadata.from_json_file(str(json_path))
        assert loaded_metadata.document_id == metadata.document_id
        assert loaded_metadata.pdf_type == metadata.pdf_type
        assert loaded_metadata.num_pages == metadata.num_pages

    def test_process_pdf_file_not_found_error(self, tmp_path: Path) -> None:
        """Test error handling when PDF file doesn't exist."""
        pdf_path = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            process_pdf_document(pdf_path)

        assert "not found" in str(exc_info.value)
