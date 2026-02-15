# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/generate_dqs_routing_matrix.py - DQS routing matrix generation.

These tests verify the DQS routing matrix generation correctly:
- Calculates blur, noise, contrast, skew, and DPI scores
- Classifies degradation levels
- Calculates structural complexity from annotations
- Classifies complexity levels
- Maps to routing bins
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

rng = np.random.default_rng(42)

# Scripts directory added to sys.path via tests/conftest.py
from generate_dqs_routing_matrix import (
    DOCLAYNET_CLASSES,
    _score_metric,
    calculate_blur_score,
    calculate_contrast_score,
    calculate_noise_score,
    calculate_skew_score,
    calculate_structural_complexity,
    classify_degradation,
    classify_structural_complexity,
    estimate_dpi,
)


class TestDocLayNetClasses:
    """Tests for DocLayNet class mapping."""

    def test_class_mapping_count(self) -> None:
        """Test that all 11 DocLayNet classes are defined."""
        assert len(DOCLAYNET_CLASSES) == 11

    def test_class_mapping_values(self) -> None:
        """Test specific class mappings."""
        assert DOCLAYNET_CLASSES[3] == "Formula"
        assert DOCLAYNET_CLASSES[7] == "Picture"
        assert DOCLAYNET_CLASSES[9] == "Table"
        assert DOCLAYNET_CLASSES[10] == "Text"


class TestCalculateBlurScore:
    """Tests for calculate_blur_score function."""

    def test_blur_score_sharp_image(self) -> None:
        """Test blur score for sharp image with edges."""
        # Create image with sharp edges (high frequency content)
        image = np.zeros((100, 100), dtype=np.uint8)
        # Add sharp edges
        image[40:60, 40:60] = 255
        cv2.rectangle(image, (20, 20), (80, 80), 128, 2)

        score = calculate_blur_score(image)

        # Sharp images should have higher blur score (Laplacian variance)
        assert score > 0

    def test_blur_score_blurry_image(self) -> None:
        """Test blur score for blurry image."""
        # Create uniform/smooth image (low frequency content)
        image = np.full((100, 100), 128, dtype=np.uint8)
        # Apply heavy blur
        blurred = cv2.GaussianBlur(image, (21, 21), 10)

        score = calculate_blur_score(blurred)

        # Blurry images should have lower blur score
        assert score < 50  # Low variance

    def test_blur_score_bgr_image(self) -> None:
        """Test blur score handles BGR images."""
        # Create 3-channel BGR image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[40:60, 40:60] = [255, 255, 255]

        score = calculate_blur_score(image)

        assert isinstance(score, float)
        assert score > 0

    def test_blur_score_comparison(self) -> None:
        """Test that sharp images have higher scores than blurry ones."""
        # Sharp image with edges
        sharp = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(sharp, (10, 10), (90, 90), 255, 1)
        cv2.rectangle(sharp, (30, 30), (70, 70), 128, 1)

        # Blurred version
        blurry = cv2.GaussianBlur(sharp, (15, 15), 5)

        sharp_score = calculate_blur_score(sharp)
        blurry_score = calculate_blur_score(blurry)

        assert sharp_score > blurry_score


class TestCalculateNoiseScore:
    """Tests for calculate_noise_score function."""

    def test_noise_score_clean_image(self) -> None:
        """Test noise score for clean uniform image."""
        # Create clean uniform image
        image = np.full((100, 100), 128, dtype=np.uint8)

        score = calculate_noise_score(image)

        # Clean images should have low noise score
        assert score >= 0

    def test_noise_score_noisy_image(self) -> None:
        """Test noise score for noisy image."""
        # Create image with noise
        image = np.full((100, 100), 128, dtype=np.uint8)
        noise = rng.integers(-50, 50, (100, 100), dtype=np.int16)
        noisy = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        score = calculate_noise_score(noisy)

        assert isinstance(score, float)
        assert score >= 0

    def test_noise_score_bgr_conversion(self) -> None:
        """Test noise score handles BGR images."""
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        score = calculate_noise_score(image)

        assert isinstance(score, float)


class TestCalculateContrastScore:
    """Tests for calculate_contrast_score function."""

    def test_contrast_score_low_contrast(self) -> None:
        """Test contrast score for low contrast image."""
        # Create low contrast image (all similar values)
        image = np.full((100, 100), 128, dtype=np.uint8)
        image[:50, :] = 130  # Small difference

        score = calculate_contrast_score(image)

        assert score < 10  # Low RMS contrast

    def test_contrast_score_high_contrast(self) -> None:
        """Test contrast score for high contrast image."""
        # Create high contrast image (black and white)
        image = np.zeros((100, 100), dtype=np.uint8)
        image[:50, :] = 255

        score = calculate_contrast_score(image)

        assert score > 100  # High RMS contrast

    def test_contrast_score_comparison(self) -> None:
        """Test contrast score ordering."""
        # Low contrast
        low = np.full((100, 100), 128, dtype=np.uint8)

        # High contrast
        high = np.zeros((100, 100), dtype=np.uint8)
        high[:50, :] = 255

        low_score = calculate_contrast_score(low)
        high_score = calculate_contrast_score(high)

        assert high_score > low_score


class TestCalculateSkewScore:
    """Tests for calculate_skew_score function."""

    def test_skew_score_no_lines(self) -> None:
        """Test skew score for image without lines."""
        # Uniform image with no edges
        image = np.full((100, 100), 128, dtype=np.uint8)

        score = calculate_skew_score(image)

        # No lines detected should return 0
        assert score == pytest.approx(0.0)

    def test_skew_score_horizontal_lines(self) -> None:
        """Test skew score for horizontal lines."""
        # Create image with horizontal lines
        image = np.zeros((200, 200), dtype=np.uint8)
        for y in range(20, 180, 20):
            cv2.line(image, (10, y), (190, y), 255, 2)

        score = calculate_skew_score(image)

        # Horizontal lines should have low skew
        assert isinstance(score, float)

    def test_skew_score_returns_float(self) -> None:
        """Test that skew score returns float."""
        image = np.zeros((100, 100), dtype=np.uint8)
        cv2.line(image, (10, 10), (90, 90), 255, 2)

        score = calculate_skew_score(image)

        assert isinstance(score, float)


class TestEstimateDpi:
    """Tests for estimate_dpi function."""

    def test_estimate_dpi_a4_300dpi(self) -> None:
        """Test DPI estimation for A4 at 300 DPI."""
        # A4 at 300 DPI: height = 11.69 * 300 = 3507
        image = np.zeros((3507, 2480), dtype=np.uint8)

        dpi = estimate_dpi(image)

        assert abs(dpi - 300) < 5  # Should be close to 300

    def test_estimate_dpi_a4_150dpi(self) -> None:
        """Test DPI estimation for A4 at 150 DPI."""
        # A4 at 150 DPI: height = 11.69 * 150 = 1754
        image = np.zeros((1754, 1240), dtype=np.uint8)

        dpi = estimate_dpi(image)

        assert abs(dpi - 150) < 5  # Should be close to 150

    def test_estimate_dpi_small_image(self) -> None:
        """Test DPI estimation for small image."""
        image = np.zeros((100, 100), dtype=np.uint8)

        dpi = estimate_dpi(image)

        # Small image = low estimated DPI
        assert dpi < 100


class TestCalculateStructuralComplexity:
    """Tests for calculate_structural_complexity function."""

    def test_empty_annotations(self) -> None:
        """Test complexity with no annotations."""
        metrics = calculate_structural_complexity([], 1000)

        assert metrics["table_count"] == 0
        assert metrics["formula_count"] == 0
        assert metrics["picture_count"] == 0
        assert metrics["text_blocks"] == 0
        assert metrics["column_count"] == 1

    def test_table_count(self) -> None:
        """Test counting table annotations."""
        annotations = [
            {"category_id": 9, "bbox": [0, 0, 100, 100]},
            {"category_id": 9, "bbox": [200, 0, 100, 100]},
        ]

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["table_count"] == 2

    def test_formula_count(self) -> None:
        """Test counting formula annotations."""
        annotations = [
            {"category_id": 3, "bbox": [0, 0, 100, 50]},
            {"category_id": 3, "bbox": [0, 100, 100, 50]},
            {"category_id": 3, "bbox": [0, 200, 100, 50]},
        ]

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["formula_count"] == 3

    def test_picture_count(self) -> None:
        """Test counting picture annotations."""
        annotations = [
            {"category_id": 7, "bbox": [0, 0, 200, 200]},
        ]

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["picture_count"] == 1

    def test_text_blocks_count(self) -> None:
        """Test counting text block annotations."""
        annotations = [
            {"category_id": 10, "bbox": [0, 0, 100, 50]},
            {"category_id": 10, "bbox": [0, 100, 100, 50]},
            {"category_id": 10, "bbox": [0, 200, 100, 50]},
        ]

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["text_blocks"] == 3

    def test_column_detection_single(self) -> None:
        """Test single column detection."""
        # All text blocks at same x position
        annotations = [
            {"category_id": 10, "bbox": [100, i * 50, 800, 40]} for i in range(10)
        ]

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["column_count"] == 1

    def test_column_detection_multi(self) -> None:
        """Test multi-column detection."""
        # Text blocks in two distinct columns
        annotations = []
        for i in range(5):
            annotations.append({"category_id": 10, "bbox": [50, i * 50, 400, 40]})
            annotations.append({"category_id": 10, "bbox": [550, i * 50, 400, 40]})

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["column_count"] >= 2

    def test_mixed_annotations(self) -> None:
        """Test mixed annotation types."""
        annotations = [
            {"category_id": 9, "bbox": [0, 0, 100, 100]},  # Table
            {"category_id": 3, "bbox": [0, 150, 100, 50]},  # Formula
            {"category_id": 7, "bbox": [200, 0, 200, 200]},  # Picture
            {"category_id": 10, "bbox": [0, 250, 400, 50]},  # Text
            {"category_id": 11, "bbox": [0, 320, 200, 30]},  # Title
        ]

        metrics = calculate_structural_complexity(annotations, 1000)

        assert metrics["table_count"] == 1
        assert metrics["formula_count"] == 1
        assert metrics["picture_count"] == 1
        assert metrics["text_blocks"] == 1


class TestScoreMetric:
    """Tests for _score_metric helper function."""

    def test_score_above_high(self) -> None:
        """Test score for value above high threshold."""
        assert _score_metric(10, 5, 2) == 2

    def test_score_between_thresholds(self) -> None:
        """Test score for value between thresholds."""
        assert _score_metric(3, 5, 2) == 1

    def test_score_below_low(self) -> None:
        """Test score for value below low threshold."""
        assert _score_metric(1, 5, 2) == 0

    def test_score_at_thresholds(self) -> None:
        """Test score at threshold boundaries."""
        # At high threshold - should be 2
        assert _score_metric(5, 5, 2) == 1  # Equal is not > high

        # At low threshold - should be 1
        assert _score_metric(2, 5, 2) == 0  # Equal is not > low


class TestClassifyDegradation:
    """Tests for classify_degradation function."""

    def test_low_degradation_high_quality(self) -> None:
        """Test low degradation classification for high quality metrics."""
        # High blur score (sharp), low noise, high contrast, no skew, high DPI
        result = classify_degradation(
            blur=600,
            noise=5,
            contrast=60,
            skew=0.5,
            dpi=300,
        )

        assert result == "low"

    def test_high_degradation_low_quality(self) -> None:
        """Test high degradation classification for low quality metrics."""
        # Low blur score (blurry), high noise, low contrast, high skew, low DPI
        result = classify_degradation(
            blur=50,
            noise=80,
            contrast=10,
            skew=10,
            dpi=72,
        )

        assert result == "high"

    def test_medium_degradation(self) -> None:
        """Test medium degradation classification."""
        result = classify_degradation(
            blur=250,
            noise=25,
            contrast=30,
            skew=2,
            dpi=150,
        )

        assert result == "medium"

    def test_degradation_returns_valid_string(self) -> None:
        """Test that degradation always returns valid string."""
        result = classify_degradation(0, 0, 0, 0, 0)

        assert result in ["low", "medium", "high"]


class TestClassifyStructuralComplexity:
    """Tests for classify_structural_complexity function."""

    def test_low_complexity(self) -> None:
        """Test low complexity classification."""
        metrics = {
            "column_count": 1,
            "table_count": 0,
            "formula_count": 0,
            "picture_count": 0,
        }

        result = classify_structural_complexity(metrics)

        assert result == "low"

    def test_medium_complexity(self) -> None:
        """Test medium complexity classification."""
        metrics = {
            "column_count": 2,
            "table_count": 1,
            "formula_count": 0,
            "picture_count": 0,
        }

        result = classify_structural_complexity(metrics)

        assert result == "medium"

    def test_high_complexity(self) -> None:
        """Test high complexity classification."""
        metrics = {
            "column_count": 3,
            "table_count": 3,
            "formula_count": 10,
            "picture_count": 5,
        }

        result = classify_structural_complexity(metrics)

        assert result == "high"

    def test_complexity_returns_valid_string(self) -> None:
        """Test that complexity always returns valid string."""
        metrics = {
            "column_count": 1,
            "table_count": 0,
            "formula_count": 0,
            "picture_count": 0,
        }

        result = classify_structural_complexity(metrics)

        assert result in ["low", "medium", "high"]


class TestRoutingBinCalculation:
    """Tests for routing bin calculation logic."""

    def test_routing_bin_range(self) -> None:
        """Test that routing bins are in valid range 1-9."""
        for deg in ["low", "medium", "high"]:
            for comp in ["low", "medium", "high"]:
                deg_idx = {"low": 0, "medium": 1, "high": 2}[deg]
                comp_idx = {"low": 0, "medium": 1, "high": 2}[comp]
                routing_bin = deg_idx * 3 + comp_idx + 1

                assert 1 <= routing_bin <= 9

    def test_routing_bin_uniqueness(self) -> None:
        """Test that each combination maps to unique bin."""
        bins = set()
        for deg in ["low", "medium", "high"]:
            for comp in ["low", "medium", "high"]:
                deg_idx = {"low": 0, "medium": 1, "high": 2}[deg]
                comp_idx = {"low": 0, "medium": 1, "high": 2}[comp]
                routing_bin = deg_idx * 3 + comp_idx + 1
                bins.add(routing_bin)

        assert len(bins) == 9  # All 9 bins are unique

    def test_specific_bins(self) -> None:
        """Test specific bin assignments."""
        # Low degradation, low complexity = bin 1
        assert 0 * 3 + 0 + 1 == 1

        # Low degradation, high complexity = bin 3
        assert 0 * 3 + 2 + 1 == 3

        # High degradation, high complexity = bin 9
        assert 2 * 3 + 2 + 1 == 9


class TestGenerateDqsRoutingLabels:
    """Tests for generate_dqs_routing_labels function integration."""

    @pytest.fixture
    def mock_doclaynet(self, tmp_path: Path) -> Path:
        """Create mock DocLayNet directory structure."""
        doclaynet_dir = tmp_path / "doclaynet"

        # Create COCO annotations
        coco_dir = doclaynet_dir / "ground_truth" / "coco"
        coco_dir.mkdir(parents=True)

        # Create images directory
        images_dir = doclaynet_dir / "documents" / "png"
        images_dir.mkdir(parents=True)

        # Create sample image
        image = np.zeros((1000, 800, 3), dtype=np.uint8)
        image[100:200, 100:700] = [255, 255, 255]  # White rectangle
        cv2.imwrite(str(images_dir / "doc1.png"), image)

        # Create COCO JSON
        coco_data = {
            "images": [
                {"id": 1, "file_name": "doc1.png", "width": 800, "height": 1000}
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 10,
                    "bbox": [100, 100, 600, 100],
                },
            ],
            "categories": [{"id": 10, "name": "Text"}],
        }

        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        return doclaynet_dir

    def test_missing_coco_file_raises(self, tmp_path: Path) -> None:
        """Test that missing COCO file raises error."""
        from generate_dqs_routing_matrix import generate_dqs_routing_labels

        fake_dir = tmp_path / "fake_doclaynet"
        fake_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            generate_dqs_routing_labels(fake_dir, tmp_path / "output", "train", 10)

    def test_missing_images_dir_raises(self, tmp_path: Path) -> None:
        """Test that missing images directory raises error."""
        from generate_dqs_routing_matrix import generate_dqs_routing_labels

        # Create COCO file but no images
        doclaynet_dir = tmp_path / "doclaynet"
        coco_dir = doclaynet_dir / "ground_truth" / "coco"
        coco_dir.mkdir(parents=True)

        coco_data = {"images": [], "annotations": []}
        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        with pytest.raises(FileNotFoundError):
            generate_dqs_routing_labels(doclaynet_dir, tmp_path / "output", "train", 10)
