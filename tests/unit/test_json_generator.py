"""
Unit tests for JSON output generation.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from image_preprocessing_detector.correction.corrections import CorrectionResult
from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
    Severity,
    SkewDetectionResult,
)
from image_preprocessing_detector.ingestion.image_loader import ImageMetadata
from image_preprocessing_detector.ingestion.pdf_loader import PageImage
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
    load_json,
)
from image_preprocessing_detector.schema import DocumentMetadata


class TestMetadataBuilder:
    """Test MetadataBuilder class."""

    def test_init(self) -> None:
        """Test MetadataBuilder initialization."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        assert builder.document_id == "doc_001"
        assert builder.file_name == "test.pdf"
        assert builder.pages == []

    def test_add_page_from_pdf(self) -> None:
        """Test adding page metadata from PDF."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        # Create PageImage
        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=150.0,
            dpi_effective=300.0,
            needs_upscaling=True,
        )

        builder.add_page(page_number=0, page_data=page_data)

        assert len(builder.pages) == 1
        page = builder.pages[0]
        assert page.page_index == 0
        assert page.width_px == 800
        assert page.height_px == 1000
        assert page.dpi_input == 150
        assert page.dpi_effective == 300

    def test_add_page_from_image(self) -> None:
        """Test adding page metadata from direct image."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.jpg")

        # Create image and metadata tuple
        img = np.zeros((1000, 800, 3), dtype=np.uint8)
        metadata = ImageMetadata(
            width=800,
            height=1000,
            dpi_x=300.0,
            dpi_y=300.0,
            color_mode="RGB",
            format="JPEG",
        )
        page_data = (img, metadata)

        builder.add_page(page_number=0, page_data=page_data)

        assert len(builder.pages) == 1
        page = builder.pages[0]
        assert page.page_index == 0
        assert page.width_px == 800
        assert page.height_px == 1000

    def test_add_page_with_skew_detection(self) -> None:
        """Test adding page with skew detection results."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )

        skew_result = SkewDetectionResult(
            is_skewed=True,
            angle=3.5,
            confidence=0.85,
            severity=Severity.MEDIUM,
            method="hough",
        )

        builder.add_page(page_number=0, page_data=page_data, skew_result=skew_result)

        page = builder.pages[0]
        assert len(page.detected_issues) == 1
        issue = page.detected_issues[0]
        assert issue.type.value == "skew"
        assert issue.severity.value == "medium"
        assert issue.confidence == pytest.approx(0.85)

    def test_add_page_with_blur_detection(self) -> None:
        """Test adding page with blur detection results."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )

        blur_result = BlurDetectionResult(
            is_blurred=True,
            score=80.0,
            blur_score=0.2,  # Normalized score (low = blurry)
            confidence=0.9,
            severity=Severity.HIGH,
        )

        builder.add_page(page_number=0, page_data=page_data, blur_result=blur_result)

        page = builder.pages[0]
        assert len(page.detected_issues) == 1
        issue = page.detected_issues[0]
        assert issue.type.value == "blur"
        assert issue.severity.value == "high"

    def test_add_page_with_contrast_detection(self) -> None:
        """Test adding page with contrast detection results."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )

        contrast_result = ContrastDetectionResult(
            is_low_contrast=True,
            score=0.25,
            confidence=0.85,
            severity=Severity.HIGH,
        )

        builder.add_page(
            page_number=0, page_data=page_data, contrast_result=contrast_result
        )

        page = builder.pages[0]
        assert len(page.detected_issues) == 1
        issue = page.detected_issues[0]
        assert issue.type.value == "low_contrast"

    def test_add_page_with_corrections(self) -> None:
        """Test adding page with correction results."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )

        skew_correction = CorrectionResult(
            corrected_image=np.zeros((1000, 800, 3), dtype=np.uint8),
            applied=True,
            parameters={"angle": 3.5, "confidence": 0.85},
        )

        builder.add_page(
            page_number=0, page_data=page_data, skew_correction=skew_correction
        )

        page = builder.pages[0]
        assert len(page.transform_history) == 1
        transform = page.transform_history[0]
        assert transform.action == "deskew"
        assert transform.params["angle"] == pytest.approx(3.5)

    def test_add_multiple_pages(self) -> None:
        """Test adding multiple pages."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        for i in range(3):
            page_data = PageImage(
                page_number=i,
                image=np.zeros((1000, 800, 3), dtype=np.uint8),
                width=800,
                height=1000,
                dpi_input=300.0,
                dpi_effective=300.0,
                needs_upscaling=False,
            )
            builder.add_page(page_number=i, page_data=page_data)

        assert len(builder.pages) == 3
        for i, page in enumerate(builder.pages):
            assert page.page_index == i

    def test_build_success(self) -> None:
        """Test building DocumentMetadata successfully."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )
        builder.add_page(page_number=0, page_data=page_data)

        metadata = builder.build(processing_version="1.0.0")

        assert isinstance(metadata, DocumentMetadata)
        assert metadata.document_id == "doc_001"
        assert metadata.file_name == "test.pdf"
        assert metadata.source_mime == "application/pdf"
        assert metadata.processing_version.pipeline_version == "1.0.0"
        assert metadata.num_pages == 1
        assert isinstance(metadata.processing_version.timestamp, datetime)

    def test_build_empty_raises(self) -> None:
        """Test building with no pages raises ValueError."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        with pytest.raises(ValueError, match="no pages added"):
            builder.build()

    def test_build_detects_mime_types(self) -> None:
        """Test MIME type detection for various file types."""
        test_cases = [
            ("test.pdf", "application/pdf"),
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.tiff", "image/tiff"),
            ("test.tif", "image/tiff"),
            ("test.bmp", "image/bmp"),
            ("test.webp", "image/webp"),
            ("test.unknown", "application/octet-stream"),
        ]

        for file_name, expected_mime in test_cases:
            builder = MetadataBuilder(document_id="doc_001", file_name=file_name)
            page_data = PageImage(
                page_number=0,
                image=np.zeros((100, 100, 3), dtype=np.uint8),
                width=100,
                height=100,
                dpi_input=300.0,
                dpi_effective=300.0,
                needs_upscaling=False,
            )
            builder.add_page(page_number=0, page_data=page_data)
            metadata = builder.build()

            assert metadata.source_mime == expected_mime, f"Failed for {file_name}"


class TestGenerateJson:
    """Test generate_json function."""

    def test_generate_json_success(self) -> None:
        """Test generating JSON file successfully."""
        # Build metadata
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")
        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )
        builder.add_page(page_number=0, page_data=page_data)
        metadata = builder.build()

        # Generate JSON
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            generate_json(metadata, output_path)

            # Verify file was created
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_generate_json_creates_parent_dirs(self) -> None:
        """Test generate_json creates parent directories."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")
        page_data = PageImage(
            page_number=0,
            image=np.zeros((100, 100, 3), dtype=np.uint8),
            width=100,
            height=100,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )
        builder.add_page(page_number=0, page_data=page_data)
        metadata = builder.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "output.json"
            generate_json(metadata, output_path)

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_generate_json_pretty_vs_compact(self) -> None:
        """Test pretty vs compact JSON output."""
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")
        page_data = PageImage(
            page_number=0,
            image=np.zeros((100, 100, 3), dtype=np.uint8),
            width=100,
            height=100,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )
        builder.add_page(page_number=0, page_data=page_data)
        metadata = builder.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            pretty_path = Path(tmpdir) / "pretty.json"
            compact_path = Path(tmpdir) / "compact.json"

            generate_json(metadata, pretty_path, pretty=True)
            generate_json(metadata, compact_path, pretty=False)

            # Pretty should be larger due to indentation
            assert pretty_path.stat().st_size > compact_path.stat().st_size


class TestLoadJson:
    """Test load_json function."""

    def test_load_json_success(self) -> None:
        """Test loading JSON file successfully."""
        # Generate JSON first
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")
        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=300.0,
            dpi_effective=300.0,
            needs_upscaling=False,
        )
        builder.add_page(page_number=0, page_data=page_data)
        metadata = builder.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            generate_json(metadata, json_path)

            # Load it back
            loaded = load_json(json_path)

            assert loaded.document_id == metadata.document_id
            assert loaded.file_name == metadata.file_name
            assert loaded.num_pages == metadata.num_pages

    def test_load_json_file_not_found(self) -> None:
        """Test loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="JSON file not found"):
            load_json("/nonexistent/file.json")

    def test_load_json_preserves_data(self) -> None:
        """Test loading preserves all data fields."""
        # Build metadata with all fields
        builder = MetadataBuilder(document_id="doc_001", file_name="test.pdf")

        page_data = PageImage(
            page_number=0,
            image=np.zeros((1000, 800, 3), dtype=np.uint8),
            width=800,
            height=1000,
            dpi_input=150.0,
            dpi_effective=300.0,
            needs_upscaling=True,
        )

        skew_result = SkewDetectionResult(
            is_skewed=True,
            angle=3.5,
            confidence=0.85,
            severity=Severity.MEDIUM,
            method="hough",
        )

        builder.add_page(page_number=0, page_data=page_data, skew_result=skew_result)

        metadata = builder.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "test.json"
            generate_json(metadata, json_path)

            loaded = load_json(json_path)

            # Verify all fields preserved
            assert loaded.num_pages == 1
            page = loaded.pages[0]
            assert page.width_px == 800
            assert page.height_px == 1000
            assert page.dpi_input == 150
            assert len(page.detected_issues) == 1
            issue = page.detected_issues[0]
            assert issue.type.value == "skew"
            assert issue.severity.value == "medium"
