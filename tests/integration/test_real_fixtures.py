"""
Integration tests using real dataset fixtures.

These tests verify the full pipeline works correctly with real-world documents
from DocLayNet, TableBank, and WiLI-2018 datasets.
"""

from pathlib import Path

import pytest

from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.ingestion.pdf_loader import PDFLoader


@pytest.mark.integration
@pytest.mark.real_data
class TestDocLayNetFixtures:
    """Test processing of DocLayNet PDF fixtures."""

    def test_can_load_all_doclaynet_pdfs(self, doclaynet_pdfs: list[Path]) -> None:
        """Verify all DocLayNet PDF fixtures can be loaded."""
        assert len(doclaynet_pdfs) > 0, "No DocLayNet fixtures found"

        pdf_loader = PDFLoader()
        for pdf_path in doclaynet_pdfs:
            assert pdf_path.exists(), f"PDF not found: {pdf_path}"

            # Load PDF (returns generator, convert to list)
            pages = list(pdf_loader.load(pdf_path))
            assert len(pages) > 0, f"No pages extracted from {pdf_path.name}"

            # Verify each page (pages are PageImage objects)
            for page_img in pages:
                assert page_img is not None
                assert page_img.image is not None
                assert page_img.image.shape[0] > 0  # Height
                assert page_img.image.shape[1] > 0  # Width
                assert page_img.image.ndim == 3  # RGB image

    def test_skew_detection_on_skewed_pdf(self, skewed_pdf: Path) -> None:
        """Test skew detection on known skewed PDF fixture."""
        pdf_loader = PDFLoader()
        pages = list(pdf_loader.load(skewed_pdf))

        assert len(pages) > 0, "No pages extracted from skewed PDF"

        # Test skew detection on first page (extract image from PageImage object)
        result = detect_skew(pages[0].image)

        # The skewed fixture should have detectable skew
        # (exact angle depends on the specific fixture, but should be non-zero)
        assert result is not None
        assert hasattr(result, "angle")
        assert hasattr(result, "confidence")
        assert hasattr(result, "severity")

    def test_multi_column_pdf_processing(self, multi_column_pdf: Path) -> None:
        """Test processing of multi-column layout PDF fixture."""
        pdf_loader = PDFLoader()
        pages = list(pdf_loader.load(multi_column_pdf))

        assert len(pages) > 0, "No pages extracted from multi-column PDF"

        # Verify we can run quality assessments (extract image from PageImage object)
        page_image = pages[0].image
        blur_result = detect_blur(page_image)
        contrast_result = detect_contrast(page_image)
        skew_result = detect_skew(page_image)

        # Results should be valid
        assert blur_result is not None
        assert contrast_result is not None
        assert skew_result is not None


@pytest.mark.integration
@pytest.mark.real_data
class TestTableBankFixtures:
    """Test processing of TableBank image fixtures."""

    def test_can_load_all_tablebank_images(self, tablebank_images: list[Path]) -> None:
        """Verify all TableBank image fixtures can be loaded."""
        import cv2

        assert len(tablebank_images) > 0, "No TableBank fixtures found"

        for img_path in tablebank_images:
            assert img_path.exists(), f"Image not found: {img_path}"

            # Load image
            image = cv2.imread(str(img_path))
            assert image is not None, f"Failed to load {img_path.name}"
            assert image.shape[0] > 0  # Height
            assert image.shape[1] > 0  # Width

    def test_table_quality_assessment(self, simple_table_image: Path) -> None:
        """Test quality assessment on simple table image fixture."""
        import cv2

        image = cv2.imread(str(simple_table_image))
        assert image is not None

        # Run quality assessments
        blur_result = detect_blur(image)
        contrast_result = detect_contrast(image)
        skew_result = detect_skew(image)

        # All detectors should complete successfully
        assert blur_result is not None
        assert contrast_result is not None
        assert skew_result is not None

    def test_complex_table_quality_assessment(self, complex_table_image: Path) -> None:
        """Test quality assessment on complex table image fixture."""
        import cv2

        image = cv2.imread(str(complex_table_image))
        assert image is not None

        # Run quality assessments
        blur_result = detect_blur(image)
        contrast_result = detect_contrast(image)

        # Complex tables should still be processed successfully
        assert blur_result is not None
        assert contrast_result is not None


@pytest.mark.integration
@pytest.mark.real_data
class TestWiLIFixtures:
    """Test processing of WiLI-2018 text sample fixtures."""

    def test_can_load_all_language_samples(self, wili_text_samples: list[Path]) -> None:
        """Verify all WiLI-2018 text fixtures can be loaded."""
        assert len(wili_text_samples) >= 10, "Expected at least 10 language samples"

        for sample_path in wili_text_samples:
            assert sample_path.exists(), f"Sample not found: {sample_path}"

            # Read text
            text = sample_path.read_text(encoding="utf-8")
            assert len(text) > 0, f"Empty text in {sample_path.name}"

    def test_language_diversity(self, wili_text_samples: list[Path]) -> None:
        """Verify fixtures contain diverse language samples."""
        # Expected language codes in fixture filenames
        expected_langs = {
            "eng",
            "fra",
            "deu",
            "spa",
            "zho",
            "ara",
            "rus",
            "jpn",
            "kor",
            "hin",
        }

        # Extract language codes from filenames (format: langname_code.txt)
        found_langs = set()
        for sample in wili_text_samples:
            # Extract language code from filename (e.g., "eng_eng.txt" -> "eng")
            parts = sample.stem.split("_")
            if len(parts) >= 2:
                lang_code = parts[-1]  # Last part is the language code
                found_langs.add(lang_code)

        # Verify we have diverse languages
        assert len(found_langs) >= 10, (
            f"Expected 10+ languages, found {len(found_langs)}"
        )

        # Check for at least some expected languages
        common_langs = expected_langs.intersection(found_langs)
        assert len(common_langs) >= 5, (
            f"Expected at least 5 common languages, found {len(common_langs)}"
        )


@pytest.mark.integration
@pytest.mark.real_data
class TestFullPipeline:
    """Test full processing pipeline with real fixtures."""

    def test_end_to_end_pdf_processing(self, simple_text_pdf: Path) -> None:
        """Test complete PDF processing pipeline."""
        pdf_loader = PDFLoader()

        # Step 1: Load PDF
        pages = list(pdf_loader.load(simple_text_pdf))
        assert len(pages) > 0

        # Step 2: Process each page (extract image from PageImage object)
        for page_img in pages:
            image = page_img.image
            # Run IQA detectors
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)
            skew_result = detect_skew(image)

            # All should complete without error
            assert blur_result is not None
            assert contrast_result is not None
            assert skew_result is not None

            # Results should have expected fields
            assert hasattr(blur_result, "score")
            assert hasattr(blur_result, "severity")
            assert hasattr(contrast_result, "score")
            assert hasattr(skew_result, "angle")

    def test_batch_processing_efficiency(self, doclaynet_pdfs: list[Path]) -> None:
        """Test batch processing of multiple PDFs completes efficiently."""
        import time

        pdf_loader = PDFLoader()
        start_time = time.time()

        processed_count = 0
        for pdf_path in doclaynet_pdfs[:3]:  # Process first 3 PDFs
            pages = list(pdf_loader.load(pdf_path))
            for page_img in pages:
                image = page_img.image
                # Run basic quality checks
                _ = detect_blur(image)
                _ = detect_contrast(image)
                processed_count += 1

        elapsed_time = time.time() - start_time

        # Verify processing completed
        assert processed_count > 0

        # Performance expectation: < 5 seconds per page for classical methods
        # (This is very conservative; actual should be < 1s/page)
        max_expected_time = processed_count * 5
        assert elapsed_time < max_expected_time, (
            f"Processing took {elapsed_time:.2f}s for {processed_count} pages "
            f"(expected < {max_expected_time}s)"
        )


# ============================================================================
# Fixture Availability Tests (run these first to verify setup)
# ============================================================================


@pytest.mark.integration
@pytest.mark.real_data
def test_fixtures_directory_exists(fixtures_dir: Path) -> None:
    """Verify test fixtures directory is properly set up."""
    assert fixtures_dir.exists(), f"Fixtures directory not found: {fixtures_dir}"
    assert fixtures_dir.is_dir(), f"Fixtures path is not a directory: {fixtures_dir}"


@pytest.mark.integration
@pytest.mark.real_data
def test_doclaynet_fixtures_available(doclaynet_fixtures_dir: Path) -> None:
    """Verify DocLayNet fixtures are available."""
    assert doclaynet_fixtures_dir.exists()
    pdfs = list(doclaynet_fixtures_dir.glob("*.pdf"))
    assert len(pdfs) > 0, "No DocLayNet PDFs found in fixtures"


@pytest.mark.integration
@pytest.mark.real_data
def test_tablebank_fixtures_available(tablebank_fixtures_dir: Path) -> None:
    """Verify TableBank fixtures are available."""
    assert tablebank_fixtures_dir.exists()
    images = list(tablebank_fixtures_dir.glob("*.{jpg,png}"))
    if not images:  # Fallback to case-insensitive search
        images = list(tablebank_fixtures_dir.glob("*.[jJ][pP][gG]"))
        images.extend(list(tablebank_fixtures_dir.glob("*.[pP][nN][gG]")))
    assert len(images) > 0, "No TableBank images found in fixtures"


@pytest.mark.integration
@pytest.mark.real_data
def test_wili_fixtures_available(wili_fixtures_dir: Path) -> None:
    """Verify WiLI-2018 fixtures are available."""
    assert wili_fixtures_dir.exists()
    samples = [
        s for s in wili_fixtures_dir.glob("*.txt") if "manifest" not in s.name.lower()
    ]
    assert len(samples) >= 10, f"Expected 10+ WiLI samples, found {len(samples)}"
