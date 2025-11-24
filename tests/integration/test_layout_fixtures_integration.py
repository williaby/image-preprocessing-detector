"""
Integration tests using layout edge case fixtures.

These tests demonstrate how to use the new layout fixtures for validating
layout-lite detection algorithms.
"""

from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.real_data
def test_layout_fixtures_available(layout_samples_dir: Path):
    """Test that layout fixtures directory exists and contains expected files."""
    assert layout_samples_dir.exists(), "Layout samples directory should exist"

    # Check for manifest.json
    manifest_file = layout_samples_dir / "manifest.json"
    assert manifest_file.exists(), "manifest.json should exist"

    # Check for expected samples
    expected_samples = [
        "dense_math_page4.pdf",
        "watermarked_document.pdf",
        "colorful_background.jpg",
        "handwriting_mixed.jpg",
    ]

    for sample_name in expected_samples:
        sample_path = layout_samples_dir / sample_name
        assert sample_path.exists(), f"{sample_name} should exist"


@pytest.mark.integration
@pytest.mark.real_data
def test_layout_edge_case_collection(layout_edge_case_samples: list[Path]):
    """Test that layout edge case samples are collected correctly."""
    assert len(layout_edge_case_samples) == 4, "Should have 4 layout edge case samples"

    # Count PDFs and images
    pdfs = [s for s in layout_edge_case_samples if s.suffix == ".pdf"]
    jpgs = [s for s in layout_edge_case_samples if s.suffix == ".jpg"]

    assert len(pdfs) == 2, "Should have 2 PDF samples"
    assert len(jpgs) == 2, "Should have 2 JPG samples"


@pytest.mark.integration
@pytest.mark.real_data
def test_watermarked_pdf_fixture(watermarked_pdf: Path):
    """Test watermarked PDF fixture."""
    assert watermarked_pdf.exists()
    assert watermarked_pdf.name == "watermarked_document.pdf"
    assert watermarked_pdf.stat().st_size > 0, "PDF should not be empty"
    assert watermarked_pdf.suffix == ".pdf", "Should be a PDF file"


@pytest.mark.integration
@pytest.mark.real_data
def test_dense_math_pdf_fixture(dense_math_pdf: Path):
    """Test dense math PDF fixture."""
    assert dense_math_pdf.exists()
    assert dense_math_pdf.name == "dense_math_page4.pdf"
    assert dense_math_pdf.stat().st_size > 0, "PDF should not be empty"
    assert dense_math_pdf.suffix == ".pdf", "Should be a PDF file"


@pytest.mark.integration
@pytest.mark.real_data
def test_handwriting_mixed_image_fixture(handwriting_mixed_image: Path):
    """Test handwriting mixed image fixture."""
    assert handwriting_mixed_image.exists()
    assert handwriting_mixed_image.name == "handwriting_mixed.jpg"
    assert handwriting_mixed_image.stat().st_size > 0, "Image should not be empty"
    assert handwriting_mixed_image.suffix == ".jpg", "Should be a JPG file"


@pytest.mark.integration
@pytest.mark.real_data
def test_colorful_background_image_fixture(colorful_background_image: Path):
    """Test colorful background image fixture."""
    assert colorful_background_image.exists()
    assert colorful_background_image.name == "colorful_background.jpg"
    assert colorful_background_image.stat().st_size > 0, "Image should not be empty"
    assert colorful_background_image.suffix == ".jpg", "Should be a JPG file"


@pytest.mark.integration
@pytest.mark.real_data
def test_all_layout_samples_readable(layout_edge_case_samples: list[Path]):
    """Test that all layout samples are readable files."""
    for sample_path in layout_edge_case_samples:
        assert sample_path.exists(), f"{sample_path.name} should exist"
        assert sample_path.is_file(), f"{sample_path.name} should be a file"
        assert sample_path.stat().st_size > 0, f"{sample_path.name} should not be empty"


@pytest.mark.integration
@pytest.mark.real_data
def test_training_validation_images_available(training_validation_dir: Path):
    """Test that training validation images are available."""
    assert training_validation_dir.exists()

    manifest_file = training_validation_dir / "manifest.json"
    assert manifest_file.exists(), "Training validation manifest.json should exist"

    expected_samples = [
        "sample_000000.jpg",
        "sample_000001.jpg",
        "sample_000002.jpg",
        "sample_000003.jpg",
        "sample_000009.jpg",
    ]

    for sample_name in expected_samples:
        sample_path = training_validation_dir / sample_name
        assert sample_path.exists(), f"{sample_name} should exist"


@pytest.mark.integration
@pytest.mark.real_data
def test_augmentation_input_images_available(augmentation_input_dir: Path):
    """Test that augmentation input images are available."""
    assert augmentation_input_dir.exists()

    expected_samples = [
        "clean_text_page.jpg",
        "clean_table_page.jpg",
        "clean_form_page.jpg",
    ]

    for sample_name in expected_samples:
        sample_path = augmentation_input_dir / sample_name
        assert sample_path.exists(), f"{sample_name} should exist"


@pytest.mark.integration
@pytest.mark.real_data
def test_augmentation_input_collection(augmentation_input_images: list[Path]):
    """Test that augmentation input images are collected correctly."""
    assert len(augmentation_input_images) == 3, (
        "Should have 3 augmentation input images"
    )

    for img_path in augmentation_input_images:
        assert img_path.exists()
        assert img_path.suffix == ".jpg", "Should be JPG format"
        assert img_path.stat().st_size > 0, "Should not be empty"


@pytest.mark.integration
@pytest.mark.real_data
def test_training_validation_collection(training_validation_images: list[Path]):
    """Test that training validation images are collected correctly."""
    assert len(training_validation_images) == 5, (
        "Should have 5 training validation images"
    )

    for img_path in training_validation_images:
        assert img_path.exists()
        assert img_path.suffix == ".jpg", "Should be JPG format"
        assert img_path.stat().st_size > 0, "Should not be empty"
