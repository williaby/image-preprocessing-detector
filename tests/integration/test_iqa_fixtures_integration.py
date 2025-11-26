"""
Integration tests using IQA ground truth fixtures.

These tests demonstrate how to use the new IQA fixtures with ground truth labels
for validating IQA detection algorithms.
"""

from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.real_data
def test_iqa_fixtures_available(iqa_samples_dir: Path):
    """Test that IQA fixtures directory exists and contains expected files."""
    assert iqa_samples_dir.exists(), "IQA samples directory should exist"

    # Check for labels.json
    labels_file = iqa_samples_dir / "labels.json"
    assert labels_file.exists(), "labels.json should exist"

    # Check for expected sample images
    expected_samples = [
        "reference_clean.png",
        "gaussian_blur_high.png",
        "white_noise_high.png",
        "contrast_low.png",
        "jpeg_artifacts_high.png",
        "combined_blur_noise.png",
    ]

    for sample_name in expected_samples:
        sample_path = iqa_samples_dir / sample_name
        assert sample_path.exists(), f"{sample_name} should exist"


@pytest.mark.integration
@pytest.mark.real_data
def test_iqa_labels_structure(iqa_labels: dict):
    """Test that IQA labels have expected structure."""
    assert isinstance(iqa_labels, dict), "Labels should be a dictionary"
    assert len(iqa_labels) > 0, "Labels should not be empty"

    # Check first sample structure
    sample_labels = next(iter(iqa_labels.values()))
    required_fields = ["dmos", "blur", "noise", "illumination", "artifacts", "skew"]

    for field in required_fields:
        assert field in sample_labels, f"Label should contain '{field}' field"


@pytest.mark.integration
@pytest.mark.real_data
def test_iqa_sample_collection(iqa_sample_images: list[Path]):
    """Test that IQA sample images are collected correctly."""
    assert len(iqa_sample_images) == 6, "Should have 6 IQA sample images"

    for img_path in iqa_sample_images:
        assert img_path.exists(), f"{img_path.name} should exist"
        assert img_path.suffix == ".png", f"{img_path.name} should be PNG"


@pytest.mark.integration
@pytest.mark.real_data
def test_reference_clean_image_fixture(reference_clean_image: Path):
    """Test reference clean image fixture."""
    assert reference_clean_image.exists()
    assert reference_clean_image.name == "reference_clean.png"
    assert reference_clean_image.stat().st_size > 0, "Image should not be empty"


@pytest.mark.integration
@pytest.mark.real_data
def test_blurry_image_fixture(blurry_image: Path):
    """Test blurry image fixture."""
    assert blurry_image.exists()
    assert blurry_image.name == "gaussian_blur_high.png"
    assert blurry_image.stat().st_size > 0, "Image should not be empty"


@pytest.mark.integration
@pytest.mark.real_data
def test_noisy_image_fixture(noisy_image: Path):
    """Test noisy image fixture."""
    assert noisy_image.exists()
    assert noisy_image.name == "white_noise_high.png"
    assert noisy_image.stat().st_size > 0, "Image should not be empty"


@pytest.mark.integration
@pytest.mark.real_data
def test_iqa_labels_match_images(iqa_sample_images: list[Path], iqa_labels: dict):
    """Test that all sample images have corresponding labels."""
    image_names = {img.name for img in iqa_sample_images}

    for img_name in image_names:
        assert img_name in iqa_labels, f"{img_name} should have labels"

        labels = iqa_labels[img_name]
        assert 0.0 <= labels["dmos"] <= 100.0, "DMOS should be in range [0, 100]"
        assert 0.0 <= labels["blur"] <= 1.0, "Blur should be in range [0, 1]"
        assert 0.0 <= labels["noise"] <= 1.0, "Noise should be in range [0, 1]"


@pytest.mark.integration
@pytest.mark.real_data
def test_reference_clean_has_zero_defects(iqa_labels: dict):
    """Test that reference_clean.png has all defect scores = 0.0."""
    ref_labels = iqa_labels["reference_clean.png"]

    assert ref_labels["dmos"] == pytest.approx(0.0), "Reference should have DMOS = 0.0"
    assert ref_labels["blur"] == pytest.approx(0.0), "Reference should have blur = 0.0"
    assert ref_labels["noise"] == pytest.approx(0.0), (
        "Reference should have noise = 0.0"
    )
    assert ref_labels["illumination"] == pytest.approx(0.0), (
        "Reference should have illumination = 0.0"
    )
    assert ref_labels["artifacts"] == pytest.approx(0.0), (
        "Reference should have artifacts = 0.0"
    )
    assert ref_labels["skew"] == pytest.approx(0.0), "Reference should have skew = 0.0"


@pytest.mark.integration
@pytest.mark.real_data
def test_degraded_images_have_positive_defects(iqa_labels: dict):
    """Test that degraded images have positive defect scores."""
    degraded_samples = [
        ("gaussian_blur_high.png", "blur"),
        ("white_noise_high.png", "noise"),
        ("contrast_low.png", "illumination"),
        ("jpeg_artifacts_high.png", "artifacts"),
        ("combined_blur_noise.png", "blur"),  # Should have multiple defects
    ]

    for sample_name, primary_defect in degraded_samples:
        labels = iqa_labels[sample_name]
        assert labels[primary_defect] > 0.0, (
            f"{sample_name} should have {primary_defect} > 0.0"
        )
        assert labels["dmos"] > 0.0, f"{sample_name} should have DMOS > 0.0"
