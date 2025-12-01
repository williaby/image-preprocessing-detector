"""Unit tests for office document processor module (Phase 8)."""

import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from image_preprocessing_detector.ingestion.office_processor import (
    OFFICE_EXTENSIONS,
    OFFICE_MIME_TYPES,
    EmbeddedImage,
    OfficeDocumentInfo,
    OfficeProcessor,
    detect_office_type,
    extract_office_images,
)
from image_preprocessing_detector.schema import DocumentType


class TestOfficeExtensionsAndMimeTypes:
    """Test extension and MIME type mappings."""

    def test_docx_extension_mapping(self) -> None:
        """Test .docx maps to OFFICE_WORD."""
        assert OFFICE_EXTENSIONS[".docx"] == DocumentType.OFFICE_WORD

    def test_xlsx_extension_mapping(self) -> None:
        """Test .xlsx maps to OFFICE_EXCEL."""
        assert OFFICE_EXTENSIONS[".xlsx"] == DocumentType.OFFICE_EXCEL

    def test_pptx_extension_mapping(self) -> None:
        """Test .pptx maps to OFFICE_POWERPOINT."""
        assert OFFICE_EXTENSIONS[".pptx"] == DocumentType.OFFICE_POWERPOINT

    def test_word_mime_type_mapping(self) -> None:
        """Test Word MIME types map correctly."""
        docx_mime = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert OFFICE_MIME_TYPES[docx_mime] == DocumentType.OFFICE_WORD

    def test_excel_mime_type_mapping(self) -> None:
        """Test Excel MIME types map correctly."""
        xlsx_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert OFFICE_MIME_TYPES[xlsx_mime] == DocumentType.OFFICE_EXCEL

    def test_powerpoint_mime_type_mapping(self) -> None:
        """Test PowerPoint MIME types map correctly."""
        pptx_mime = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        assert OFFICE_MIME_TYPES[pptx_mime] == DocumentType.OFFICE_POWERPOINT


class TestEmbeddedImage:
    """Test EmbeddedImage dataclass."""

    def test_embedded_image_creation(self) -> None:
        """Test creating an EmbeddedImage instance."""
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        embedded = EmbeddedImage(
            image=img_array,
            image_index=0,
            source_location="slide_1",
            original_filename="image1.png",
            original_size=(100, 100),
            format="png",
        )

        assert embedded.image_index == 0
        assert embedded.source_location == "slide_1"
        assert embedded.original_filename == "image1.png"
        assert embedded.original_size == (100, 100)
        assert embedded.format == "png"
        assert np.array_equal(embedded.image, img_array)

    def test_embedded_image_with_metadata(self) -> None:
        """Test EmbeddedImage with custom metadata."""
        img_array = np.zeros((50, 50, 3), dtype=np.uint8)
        embedded = EmbeddedImage(
            image=img_array,
            image_index=1,
            source_location="page_2",
            original_filename="chart.png",
            original_size=(50, 50),
            format="png",
            metadata={"source": "excel_chart", "sheet": "Sheet1"},
        )

        assert embedded.metadata["source"] == "excel_chart"
        assert embedded.metadata["sheet"] == "Sheet1"


class TestOfficeDocumentInfo:
    """Test OfficeDocumentInfo dataclass."""

    def test_office_document_info_creation(self) -> None:
        """Test creating an OfficeDocumentInfo instance."""
        info = OfficeDocumentInfo(
            document_type=DocumentType.OFFICE_WORD,
            file_path="/path/to/document.docx",
            num_images=3,
            images=[],
            extraction_method="zipfile",
        )

        assert info.document_type == DocumentType.OFFICE_WORD
        assert info.num_images == 3
        assert info.extraction_method == "zipfile"
        assert info.errors == []

    def test_office_document_info_with_errors(self) -> None:
        """Test OfficeDocumentInfo with extraction errors."""
        info = OfficeDocumentInfo(
            document_type=DocumentType.OFFICE_EXCEL,
            file_path="/path/to/spreadsheet.xlsx",
            num_images=1,
            images=[],
            extraction_method="zipfile",
            errors=["Failed to extract image1.png"],
        )

        assert len(info.errors) == 1
        assert "Failed to extract" in info.errors[0]


class TestOfficeProcessor:
    """Test OfficeProcessor class."""

    @pytest.fixture
    def processor(self) -> OfficeProcessor:
        """Create default processor instance."""
        return OfficeProcessor(use_docling=False)

    @pytest.fixture
    def sample_docx(self) -> Path:
        """Create a minimal .docx file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            # Create a minimal OOXML structure
            with zipfile.ZipFile(f.name, "w") as zf:
                # Content Types
                content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
</Types>"""
                zf.writestr("[Content_Types].xml", content_types)

                # Create a test image
                img = Image.new("RGB", (100, 100), color="red")
                img_bytes = tempfile.SpooledTemporaryFile()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                zf.writestr("word/media/image1.png", img_bytes.read())

            return Path(f.name)

    @pytest.fixture
    def sample_xlsx(self) -> Path:
        """Create a minimal .xlsx file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            with zipfile.ZipFile(f.name, "w") as zf:
                content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
</Types>"""
                zf.writestr("[Content_Types].xml", content_types)

                # Create a test JPEG image
                img = Image.new("RGB", (200, 150), color="blue")
                img_bytes = tempfile.SpooledTemporaryFile()
                img.save(img_bytes, format="JPEG")
                img_bytes.seek(0)
                zf.writestr("xl/media/chart1.jpeg", img_bytes.read())

            return Path(f.name)

    @pytest.fixture
    def sample_pptx(self) -> Path:
        """Create a minimal .pptx file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            with zipfile.ZipFile(f.name, "w") as zf:
                content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
</Types>"""
                zf.writestr("[Content_Types].xml", content_types)

                # Create multiple test images
                for i in range(2):
                    img = Image.new("RGB", (100 + i * 50, 100 + i * 50), color="green")
                    img_bytes = tempfile.SpooledTemporaryFile()
                    img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)
                    zf.writestr(f"ppt/media/image{i + 1}.png", img_bytes.read())

            return Path(f.name)

    def test_init_without_docling(self) -> None:
        """Test processor initialization without Docling."""
        processor = OfficeProcessor(use_docling=False)
        assert processor._docling_available is False

    def test_detect_document_type_docx(self, processor: OfficeProcessor) -> None:
        """Test detection of .docx files."""
        result = processor.detect_document_type("document.docx")
        assert result == DocumentType.OFFICE_WORD

    def test_detect_document_type_xlsx(self, processor: OfficeProcessor) -> None:
        """Test detection of .xlsx files."""
        result = processor.detect_document_type("spreadsheet.xlsx")
        assert result == DocumentType.OFFICE_EXCEL

    def test_detect_document_type_pptx(self, processor: OfficeProcessor) -> None:
        """Test detection of .pptx files."""
        result = processor.detect_document_type("presentation.pptx")
        assert result == DocumentType.OFFICE_POWERPOINT

    def test_detect_document_type_non_office(self, processor: OfficeProcessor) -> None:
        """Test detection returns None for non-office files."""
        assert processor.detect_document_type("image.png") is None
        assert processor.detect_document_type("document.pdf") is None
        assert processor.detect_document_type("data.json") is None

    def test_detect_document_type_case_insensitive(
        self, processor: OfficeProcessor
    ) -> None:
        """Test detection is case-insensitive."""
        assert (
            processor.detect_document_type("DOCUMENT.DOCX") == DocumentType.OFFICE_WORD
        )
        assert processor.detect_document_type("file.XLSX") == DocumentType.OFFICE_EXCEL

    def test_is_office_document(self, processor: OfficeProcessor) -> None:
        """Test is_office_document method."""
        assert processor.is_office_document("test.docx") is True
        assert processor.is_office_document("test.xlsx") is True
        assert processor.is_office_document("test.pptx") is True
        assert processor.is_office_document("test.pdf") is False
        assert processor.is_office_document("test.txt") is False

    def test_process_docx(self, processor: OfficeProcessor, sample_docx: Path) -> None:
        """Test processing a .docx file."""
        result = processor.process(sample_docx)

        assert result.document_type == DocumentType.OFFICE_WORD
        assert result.num_images == 1
        assert len(result.images) == 1
        assert result.extraction_method == "zipfile"

        # Check extracted image
        img = result.images[0]
        assert img.image_index == 0
        assert img.format == "png"
        assert img.original_size == (100, 100)
        assert "document_" in img.source_location

    def test_process_xlsx(self, processor: OfficeProcessor, sample_xlsx: Path) -> None:
        """Test processing an .xlsx file."""
        result = processor.process(sample_xlsx)

        assert result.document_type == DocumentType.OFFICE_EXCEL
        assert result.num_images == 1
        assert len(result.images) == 1

        img = result.images[0]
        assert img.format in ("jpeg", "jpg")
        assert img.original_size == (200, 150)
        assert "workbook_" in img.source_location

    def test_process_pptx(self, processor: OfficeProcessor, sample_pptx: Path) -> None:
        """Test processing a .pptx file."""
        result = processor.process(sample_pptx)

        assert result.document_type == DocumentType.OFFICE_POWERPOINT
        assert result.num_images == 2
        assert len(result.images) == 2

        for img in result.images:
            assert "presentation_" in img.source_location

    def test_process_nonexistent_file(self, processor: OfficeProcessor) -> None:
        """Test processing nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            processor.process("/nonexistent/path/document.docx")

    def test_process_unsupported_format(self, processor: OfficeProcessor) -> None:
        """Test processing unsupported format raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            with pytest.raises(ValueError, match="Unsupported file type"):
                processor.process(f.name)

    def test_process_corrupted_zip(self, processor: OfficeProcessor) -> None:
        """Test processing corrupted ZIP archive."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"not a valid zip file")

        result = processor.process(f.name)

        assert len(result.errors) > 0
        assert "Invalid" in result.errors[0] or "corrupted" in result.errors[0]

    def test_determine_source_location_word(self, processor: OfficeProcessor) -> None:
        """Test source location determination for Word."""
        location = processor._determine_source_location(
            "word/media/image1.png", DocumentType.OFFICE_WORD
        )
        assert "document_" in location

    def test_determine_source_location_excel(self, processor: OfficeProcessor) -> None:
        """Test source location determination for Excel."""
        location = processor._determine_source_location(
            "xl/media/chart1.png", DocumentType.OFFICE_EXCEL
        )
        assert "workbook_" in location

    def test_determine_source_location_powerpoint(
        self, processor: OfficeProcessor
    ) -> None:
        """Test source location determination for PowerPoint."""
        location = processor._determine_source_location(
            "ppt/media/slide1.png", DocumentType.OFFICE_POWERPOINT
        )
        assert "presentation_" in location

    def test_extract_images_to_files(
        self, processor: OfficeProcessor, sample_docx: Path
    ) -> None:
        """Test extracting images to files."""
        doc_info = processor.process(sample_docx)

        with tempfile.TemporaryDirectory() as tmpdir:
            saved_paths = processor.extract_images_to_files(doc_info, tmpdir)

            assert len(saved_paths) == 1
            assert Path(saved_paths[0]).exists()
            assert saved_paths[0].endswith(".png")


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_detect_office_type_word(self) -> None:
        """Test detect_office_type for Word document."""
        result = detect_office_type("report.docx")
        assert result == DocumentType.OFFICE_WORD

    def test_detect_office_type_excel(self) -> None:
        """Test detect_office_type for Excel document."""
        result = detect_office_type("data.xlsx")
        assert result == DocumentType.OFFICE_EXCEL

    def test_detect_office_type_non_office(self) -> None:
        """Test detect_office_type for non-office file."""
        result = detect_office_type("image.png")
        assert result is None

    def test_extract_office_images_word(self) -> None:
        """Test extract_office_images with minimal docx."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            with zipfile.ZipFile(f.name, "w") as zf:
                zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')

            result = extract_office_images(f.name, use_docling=False)

            assert result.document_type == DocumentType.OFFICE_WORD
            assert result.extraction_method == "zipfile"
