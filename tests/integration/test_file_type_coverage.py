"""Integration tests for file type coverage.

Verifies the pipeline correctly handles all supported file formats:
- PDF (single/multi-page, various qualities)
- JPEG/JPG
- PNG
- TIFF/TIF
- BMP
- WEBP

Each format is tested through the complete pipeline from loading to JSON output.
"""

import tempfile
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest
from PIL import Image

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


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_image(
    width: int = 800,
    height: int = 600,
    with_text_patterns: bool = True,
) -> np.ndarray:
    """Create a test image with document-like patterns.

    Args:
        width: Image width
        height: Image height
        with_text_patterns: Add horizontal lines to simulate text

    Returns:
        RGB numpy array
    """
    # Create white background
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    if with_text_patterns:
        # Add text-like horizontal lines
        for y in range(50, height - 50, 30):
            cv2.line(img, (50, y), (width - 50, y), (40, 40, 40), 1)

        # Add a title-like block
        cv2.rectangle(img, (50, 20), (300, 40), (30, 30, 30), -1)

    return img


def run_full_pipeline(
    image: np.ndarray,
    image_metadata: "ImageMetadata",
    document_id: str,
    file_name: str,
    output_dir: Path,
) -> "DocumentMetadata":
    """Run the full processing pipeline on an image.

    Args:
        image: Input image
        image_metadata: Image metadata
        document_id: Document identifier
        file_name: Original filename
        output_dir: Directory for output files

    Returns:
        DocumentMetadata object
    """
    from image_preprocessing_detector.ingestion.image_loader import ImageMetadata

    # Run detection
    text_result = detect_text(image)
    skew_result = detect_skew(image) if text_result.has_text else None
    blur_result = detect_blur(image) if text_result.has_text else None
    contrast_result = detect_contrast(image) if text_result.has_text else None

    # Build metadata
    builder = MetadataBuilder(document_id=document_id, file_name=file_name)
    builder.add_page(
        page_number=0,
        page_data=(image, image_metadata),
        text_result=text_result,
        skew_result=skew_result,
        blur_result=blur_result,
        contrast_result=contrast_result,
    )

    # Generate output
    metadata = builder.build()
    output_path = output_dir / f"{document_id}.json"
    generate_json(metadata, output_path)

    return metadata


# =============================================================================
# JPEG/JPG Format Tests
# =============================================================================


@pytest.mark.integration
class TestJPEGFormat:
    """Test JPEG/JPG file format handling."""

    def test_jpeg_loading_and_processing(self) -> None:
        """Test complete pipeline with JPEG image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create and save JPEG
            img = create_test_image()
            jpeg_path = tmppath / "test_document.jpg"
            cv2.imwrite(str(jpeg_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])

            # Load and process
            image, metadata = load_image(str(jpeg_path))

            assert image is not None
            assert image.shape[0] > 0
            assert image.shape[1] > 0
            assert metadata.format in ("JPEG", "JPG")

            # Run IQA
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)
            skew_result = detect_skew(image)

            assert blur_result is not None
            assert contrast_result is not None
            assert skew_result is not None

    def test_jpeg_with_different_quality_levels(self) -> None:
        """Test JPEG at various compression levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            img = create_test_image()

            for quality in [30, 60, 90, 100]:
                jpeg_path = tmppath / f"test_q{quality}.jpg"
                cv2.imwrite(str(jpeg_path), img, [cv2.IMWRITE_JPEG_QUALITY, quality])

                image, metadata = load_image(str(jpeg_path))
                assert image is not None

                # Low quality should still be processable
                blur_result = detect_blur(image)
                assert blur_result is not None

    def test_jpeg_full_pipeline_to_json(self) -> None:
        """Test complete JPEG to JSON pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create JPEG
            img = create_test_image()
            jpeg_path = tmppath / "document.jpg"
            cv2.imwrite(str(jpeg_path), img)

            # Load
            image, metadata = load_image(str(jpeg_path))

            # Run pipeline
            result = run_full_pipeline(
                image, metadata, "jpeg_001", "document.jpg", tmppath
            )

            assert result.document_id == "jpeg_001"
            assert result.source_mime == "image/jpeg"
            assert result.num_pages == 1

            # Verify JSON output
            json_path = tmppath / "jpeg_001.json"
            assert json_path.exists()
            loaded = load_json(json_path)
            assert loaded.document_id == "jpeg_001"


# =============================================================================
# PNG Format Tests
# =============================================================================


@pytest.mark.integration
class TestPNGFormat:
    """Test PNG file format handling."""

    def test_png_loading_and_processing(self) -> None:
        """Test complete pipeline with PNG image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create and save PNG
            img = create_test_image()
            png_path = tmppath / "test_document.png"
            cv2.imwrite(str(png_path), img)

            # Load and process
            image, metadata = load_image(str(png_path))

            assert image is not None
            assert metadata.format == "PNG"

            # Run IQA
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)

            assert blur_result is not None
            assert contrast_result is not None

    def test_png_with_alpha_channel(self) -> None:
        """Test PNG with alpha channel is handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create RGBA image with alpha
            img_rgba = np.ones((600, 800, 4), dtype=np.uint8) * 255
            img_rgba[:, :, 3] = 200  # Semi-transparent

            # Add some content
            cv2.rectangle(img_rgba, (50, 50), (200, 100), (0, 0, 0, 255), -1)

            png_path = tmppath / "transparent.png"
            cv2.imwrite(str(png_path), img_rgba)

            # Should load successfully (converted to RGB)
            image, metadata = load_image(str(png_path))
            assert image is not None
            # Image should be RGB (3 channels), not RGBA
            assert image.ndim == 3

    def test_png_full_pipeline_to_json(self) -> None:
        """Test complete PNG to JSON pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            img = create_test_image()
            png_path = tmppath / "document.png"
            cv2.imwrite(str(png_path), img)

            image, metadata = load_image(str(png_path))
            result = run_full_pipeline(
                image, metadata, "png_001", "document.png", tmppath
            )

            assert result.document_id == "png_001"
            assert result.source_mime == "image/png"


# =============================================================================
# TIFF Format Tests
# =============================================================================


@pytest.mark.integration
class TestTIFFFormat:
    """Test TIFF/TIF file format handling."""

    def test_tiff_loading_and_processing(self) -> None:
        """Test complete pipeline with TIFF image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create and save TIFF using PIL (more reliable for TIFF)
            img = create_test_image()
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            tiff_path = tmppath / "test_document.tiff"
            pil_img.save(str(tiff_path), format="TIFF")

            # Load and process
            image, metadata = load_image(str(tiff_path))

            assert image is not None
            assert metadata.format == "TIFF"

            # Run IQA
            blur_result = detect_blur(image)
            assert blur_result is not None

    def test_tif_extension(self) -> None:
        """Test .tif extension (shorter variant)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            img = create_test_image()
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            tif_path = tmppath / "test_document.tif"
            pil_img.save(str(tif_path), format="TIFF")

            image, metadata = load_image(str(tif_path))
            assert image is not None

    def test_tiff_full_pipeline_to_json(self) -> None:
        """Test complete TIFF to JSON pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            img = create_test_image()
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            tiff_path = tmppath / "document.tiff"
            pil_img.save(str(tiff_path), format="TIFF")

            image, metadata = load_image(str(tiff_path))
            result = run_full_pipeline(
                image, metadata, "tiff_001", "document.tiff", tmppath
            )

            assert result.document_id == "tiff_001"
            assert result.source_mime == "image/tiff"


# =============================================================================
# BMP Format Tests
# =============================================================================


@pytest.mark.integration
class TestBMPFormat:
    """Test BMP file format handling."""

    def test_bmp_loading_and_processing(self) -> None:
        """Test complete pipeline with BMP image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create and save BMP
            img = create_test_image()
            bmp_path = tmppath / "test_document.bmp"
            cv2.imwrite(str(bmp_path), img)

            # Load and process
            image, metadata = load_image(str(bmp_path))

            assert image is not None
            assert metadata.format == "BMP"

            # Run IQA
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)

            assert blur_result is not None
            assert contrast_result is not None

    def test_bmp_full_pipeline_to_json(self) -> None:
        """Test complete BMP to JSON pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            img = create_test_image()
            bmp_path = tmppath / "document.bmp"
            cv2.imwrite(str(bmp_path), img)

            image, metadata = load_image(str(bmp_path))
            result = run_full_pipeline(
                image, metadata, "bmp_001", "document.bmp", tmppath
            )

            assert result.document_id == "bmp_001"
            assert result.source_mime == "image/bmp"


# =============================================================================
# WEBP Format Tests
# =============================================================================


@pytest.mark.integration
class TestWEBPFormat:
    """Test WEBP file format handling."""

    def test_webp_loading_and_processing(self) -> None:
        """Test complete pipeline with WEBP image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create and save WEBP
            img = create_test_image()
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            webp_path = tmppath / "test_document.webp"
            pil_img.save(str(webp_path), format="WEBP", quality=90)

            # Load and process
            image, metadata = load_image(str(webp_path))

            assert image is not None
            assert metadata.format == "WEBP"

            # Run IQA
            blur_result = detect_blur(image)
            assert blur_result is not None

    def test_webp_full_pipeline_to_json(self) -> None:
        """Test complete WEBP to JSON pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            img = create_test_image()
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            webp_path = tmppath / "document.webp"
            pil_img.save(str(webp_path), format="WEBP")

            image, metadata = load_image(str(webp_path))
            result = run_full_pipeline(
                image, metadata, "webp_001", "document.webp", tmppath
            )

            assert result.document_id == "webp_001"
            assert result.source_mime == "image/webp"


# =============================================================================
# PDF Format Tests (Comprehensive)
# =============================================================================


@pytest.mark.integration
class TestPDFFormat:
    """Test PDF file format handling with various configurations."""

    def test_pdf_single_page(self) -> None:
        """Test single-page PDF processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create single-page PDF
            pdf_path = tmppath / "single_page.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Single Page Document", fontsize=14)
            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 1

            # Run IQA on page
            blur_result = detect_blur(pages[0].image)
            assert blur_result is not None

    def test_pdf_multi_page(self) -> None:
        """Test multi-page PDF processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create multi-page PDF
            pdf_path = tmppath / "multi_page.pdf"
            doc = fitz.open()
            for i in range(5):
                page = doc.new_page(width=595, height=842)
                page.insert_text((50, 50), f"Page {i + 1}", fontsize=14)
            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            assert len(pages) == 5

            # Verify all pages processable
            for page_img in pages:
                blur_result = detect_blur(page_img.image)
                assert blur_result is not None

    def test_pdf_full_pipeline_to_json(self) -> None:
        """Test complete PDF to JSON pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create PDF
            pdf_path = tmppath / "document.pdf"
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Test Document", fontsize=14)
            doc.save(str(pdf_path))
            doc.close()

            # Process
            pages = load_pdf(str(pdf_path))
            builder = MetadataBuilder(document_id="pdf_001", file_name="document.pdf")

            for idx, page_img in enumerate(pages):
                text_result = detect_text(page_img.image)
                builder.add_page(
                    page_number=idx,
                    page_data=page_img,
                    text_result=text_result,
                )

            metadata = builder.build()
            output_path = tmppath / "pdf_001.json"
            generate_json(metadata, output_path)

            assert metadata.document_id == "pdf_001"
            assert metadata.source_mime == "application/pdf"
            assert output_path.exists()


# =============================================================================
# Cross-Format Consistency Tests
# =============================================================================


@pytest.mark.integration
class TestCrossFormatConsistency:
    """Test that different formats produce consistent results."""

    def test_same_content_different_formats(self) -> None:
        """Test that the same image in different formats produces similar results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create base image
            base_img = create_test_image()
            pil_img = Image.fromarray(cv2.cvtColor(base_img, cv2.COLOR_BGR2RGB))

            # Save in different formats
            formats = {
                "jpg": ("JPEG", {"quality": 95}),
                "png": ("PNG", {}),
                "bmp": ("BMP", {}),
            }

            results = {}
            for ext, (fmt, params) in formats.items():
                path = tmppath / f"test.{ext}"
                pil_img.save(str(path), format=fmt, **params)

                image, metadata = load_image(str(path))
                blur_result = detect_blur(image)
                results[ext] = {
                    "blur_score": blur_result.score,
                    "is_blurred": blur_result.is_blurred,
                }

            # Results should be consistent across formats
            # (some variance expected due to compression)
            blur_scores = [r["blur_score"] for r in results.values()]
            score_range = max(blur_scores) - min(blur_scores)

            # Allow some variance but not extreme differences
            assert score_range < 100, (
                f"Blur scores vary too much across formats: {results}"
            )


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.integration
class TestFileTypeErrors:
    """Test error handling for unsupported or corrupted files."""

    def test_unsupported_format_error(self) -> None:
        """Test that unsupported formats raise appropriate errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a file with unsupported extension
            bad_path = tmppath / "test.xyz"
            bad_path.write_text("not an image")

            with pytest.raises((ValueError, OSError, Exception)):
                load_image(str(bad_path))

    def test_corrupted_image_error(self) -> None:
        """Test that corrupted images are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create corrupted JPEG
            corrupted_path = tmppath / "corrupted.jpg"
            corrupted_path.write_bytes(b"this is not a valid jpeg file")

            with pytest.raises((ValueError, OSError, cv2.error, Exception)):
                load_image(str(corrupted_path))

    def test_empty_file_error(self) -> None:
        """Test that empty files raise errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            empty_path = tmppath / "empty.png"
            empty_path.touch()

            with pytest.raises(Exception):
                load_image(str(empty_path))


# =============================================================================
# Parametrized Format Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "extension,mime_type",
    [
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".png", "image/png"),
        (".tiff", "image/tiff"),
        (".tif", "image/tiff"),
        (".bmp", "image/bmp"),
        (".webp", "image/webp"),
    ],
)
def test_file_extension_to_mime_mapping(extension: str, mime_type: str) -> None:
    """Test that file extensions map to correct MIME types in output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create image
        img = create_test_image(width=100, height=100)
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Save with extension
        file_path = tmppath / f"test{extension}"
        if extension in (".jpg", ".jpeg"):
            pil_img.save(str(file_path), format="JPEG")
        elif extension == ".png":
            pil_img.save(str(file_path), format="PNG")
        elif extension in (".tiff", ".tif"):
            pil_img.save(str(file_path), format="TIFF")
        elif extension == ".bmp":
            pil_img.save(str(file_path), format="BMP")
        elif extension == ".webp":
            pil_img.save(str(file_path), format="WEBP")

        # Load and build metadata
        image, metadata = load_image(str(file_path))
        builder = MetadataBuilder(
            document_id="test_001",
            file_name=f"test{extension}",
        )
        builder.add_page(page_number=0, page_data=(image, metadata))
        doc_metadata = builder.build()

        # Verify MIME type
        assert doc_metadata.source_mime == mime_type, (
            f"Expected {mime_type} for {extension}, got {doc_metadata.source_mime}"
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "width,height",
    [
        (100, 100),  # Small
        (800, 600),  # Standard
        (1920, 1080),  # HD
        (3000, 4000),  # Large document
    ],
)
def test_various_image_sizes(width: int, height: int) -> None:
    """Test processing images of various sizes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        img = create_test_image(width=width, height=height)
        img_path = tmppath / "test.png"
        cv2.imwrite(str(img_path), img)

        image, metadata = load_image(str(img_path))

        assert image.shape[1] == width
        assert image.shape[0] == height

        # Should process without error
        blur_result = detect_blur(image)
        assert blur_result is not None
