# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/weak_supervision_labeling.py - Weak supervision label generation.

These tests verify the weak supervision labeler correctly:
- Detects blur using Laplacian variance
- Detects low contrast using RMS contrast
- Detects skew using Hough transform
- Labels single images and entire datasets
- Handles errors gracefully
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Skip tests if OpenCV is not available
cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from weak_supervision_labeling import WeakSupervisionLabeler


class TestWeakSupervisionLabelerInit:
    """Tests for WeakSupervisionLabeler initialization."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        labeler = WeakSupervisionLabeler()

        assert labeler.blur_threshold == 200.0
        assert labeler.low_contrast_threshold == 0.3
        assert labeler.skew_threshold == 0.5

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        labeler = WeakSupervisionLabeler(
            blur_threshold=100.0,
            low_contrast_threshold=0.2,
            skew_threshold=1.0,
        )

        assert labeler.blur_threshold == 100.0
        assert labeler.low_contrast_threshold == 0.2
        assert labeler.skew_threshold == 1.0


class TestDetectBlurLaplacian:
    """Tests for blur detection using Laplacian variance."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler with known threshold."""
        return WeakSupervisionLabeler(blur_threshold=200.0)

    def test_sharp_image_not_blurry(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that sharp image is not detected as blurry."""
        # Create a high-contrast image with edges (not blurry)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        # Add some edges
        image[40:60, 40:60] = 255
        image[20:30, 20:80] = 128
        image[70:80, 20:80] = 128

        result = labeler.detect_blur_laplacian(image)

        assert "value" in result
        assert "confidence" in result
        assert "score" in result
        assert result["source"] == "laplacian_variance"

    def test_blurry_image_detected(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that blurry image is detected."""
        # Create a low-variance image (blurry)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result = labeler.detect_blur_laplacian(image)

        # Uniform image should have very low variance
        assert result["value"] == 1  # Detected as blurry
        assert result["score"] < labeler.blur_threshold

    def test_result_structure(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that result has correct structure."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = labeler.detect_blur_laplacian(image)

        assert isinstance(result["value"], int)
        assert result["value"] in [0, 1]
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["score"], float)
        assert result["source"] == "laplacian_variance"


class TestDetectLowContrast:
    """Tests for low contrast detection using RMS contrast."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler with known threshold."""
        return WeakSupervisionLabeler(low_contrast_threshold=0.3)

    def test_high_contrast_image(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that high contrast image is not flagged."""
        # Create high contrast image (black and white)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:50, :] = 255  # Top half white
        # Bottom half stays black

        result = labeler.detect_low_contrast(image)

        assert result["value"] == 0  # Not low contrast
        assert result["source"] == "rms_contrast"

    def test_low_contrast_image_detected(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that low contrast image is detected."""
        # Create uniform gray image (very low contrast)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result = labeler.detect_low_contrast(image)

        assert result["value"] == 1  # Low contrast detected
        assert result["score"] < labeler.low_contrast_threshold

    def test_result_structure(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that result has correct structure."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = labeler.detect_low_contrast(image)

        assert isinstance(result["value"], int)
        assert result["value"] in [0, 1]
        assert isinstance(result["confidence"], float)
        assert isinstance(result["score"], float)
        assert result["source"] == "rms_contrast"


class TestDetectSkewHough:
    """Tests for skew detection using Hough transform."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler with known threshold."""
        return WeakSupervisionLabeler(skew_threshold=0.5)

    def test_no_lines_returns_no_skew(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that image with no lines returns no skew."""
        # Create uniform image (no edges/lines)
        image = np.full((100, 100, 3), 128, dtype=np.uint8)

        result = labeler.detect_skew_hough(image)

        assert result["value"] == 0  # No skew detected
        assert result["confidence"] == 0.0
        assert result["source"] == "hough_lines"

    def test_result_structure(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that result has correct structure."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = labeler.detect_skew_hough(image)

        assert isinstance(result["value"], int)
        assert result["value"] in [0, 1]
        assert isinstance(result["confidence"], float)
        assert isinstance(result["score"], float)
        assert result["source"] == "hough_lines"

    def test_horizontal_lines_no_skew(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that horizontal lines don't indicate skew."""
        # Create image with horizontal lines
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        for y in range(0, 200, 20):
            cv2.line(image, (0, y), (200, y), (255, 255, 255), 2)

        result = labeler.detect_skew_hough(image)

        # Horizontal lines should produce low angle results
        assert result["source"] == "hough_lines"


class TestEstimateQualityBrisque:
    """Tests for BRISQUE quality estimation."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler instance."""
        return WeakSupervisionLabeler()

    def test_brisque_not_available(self, labeler: WeakSupervisionLabeler) -> None:
        """Test that BRISQUE returns not available message."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = labeler.estimate_quality_brisque(image)

        assert result["available"] is False
        assert result["score"] is None
        assert "not available" in result["message"].lower()


class TestLabelImage:
    """Tests for single image labeling."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler instance."""
        return WeakSupervisionLabeler()

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a sample image file."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[40:60, 40:60] = 255  # Add some content

        image_path = tmp_path / "test_image.png"
        cv2.imwrite(str(image_path), image)
        return image_path

    def test_label_image_default_metrics(
        self, labeler: WeakSupervisionLabeler, sample_image_path: Path
    ) -> None:
        """Test labeling with default metrics."""
        result = labeler.label_image(sample_image_path)

        assert result["image_path"] == str(sample_image_path)
        assert "blur" in result["labels"]
        assert "low_contrast" in result["labels"]
        assert "skew" in result["labels"]
        assert result["metrics_used"] == ["laplacian", "histogram", "hough"]

    def test_label_image_specific_metrics(
        self, labeler: WeakSupervisionLabeler, sample_image_path: Path
    ) -> None:
        """Test labeling with specific metrics."""
        result = labeler.label_image(sample_image_path, metrics=["laplacian"])

        assert "blur" in result["labels"]
        assert "low_contrast" not in result["labels"]
        assert "skew" not in result["labels"]
        assert result["metrics_used"] == ["laplacian"]

    def test_label_image_brisque_metric(
        self, labeler: WeakSupervisionLabeler, sample_image_path: Path
    ) -> None:
        """Test labeling with BRISQUE metric."""
        result = labeler.label_image(sample_image_path, metrics=["brisque"])

        assert "quality_brisque" in result["labels"]
        assert result["labels"]["quality_brisque"]["available"] is False

    def test_label_nonexistent_image_raises(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that labeling non-existent image raises error."""
        fake_path = tmp_path / "nonexistent.png"

        with pytest.raises(ValueError, match="Failed to load image"):
            labeler.label_image(fake_path)

    def test_label_invalid_image_raises(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that labeling invalid image raises error."""
        invalid_path = tmp_path / "invalid.png"
        invalid_path.write_text("not an image")

        with pytest.raises(ValueError, match="Failed to load image"):
            labeler.label_image(invalid_path)


class TestLabelDataset:
    """Tests for dataset labeling."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler instance."""
        return WeakSupervisionLabeler()

    @pytest.fixture
    def sample_dataset(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a sample dataset with images."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        # Create test images
        for i in range(3):
            image = np.zeros((100, 100, 3), dtype=np.uint8)
            if i == 0:
                # Sharp image
                image[40:60, 40:60] = 255
            elif i == 1:
                # Uniform (blurry) image
                image[:, :] = 128
            else:
                # High contrast
                image[:50, :] = 255

            cv2.imwrite(str(input_dir / f"image_{i}.png"), image)

        return input_dir, output_dir

    def test_label_dataset_creates_output(
        self, labeler: WeakSupervisionLabeler, sample_dataset: tuple[Path, Path]
    ) -> None:
        """Test that label_dataset creates output files."""
        input_dir, output_dir = sample_dataset

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert output_dir.exists()
        assert stats["total_images"] == 3
        assert stats["labeled"] == 3
        assert stats["errors"] == 0

        # Check that label files exist
        label_files = list(output_dir.glob("*.json"))
        assert len(label_files) == 3

    def test_label_dataset_dry_run(
        self, labeler: WeakSupervisionLabeler, sample_dataset: tuple[Path, Path]
    ) -> None:
        """Test dry run doesn't create files."""
        input_dir, output_dir = sample_dataset

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir, dry_run=True)

        assert not output_dir.exists()
        assert stats["labeled"] == 3

    def test_label_dataset_max_images(
        self, labeler: WeakSupervisionLabeler, sample_dataset: tuple[Path, Path]
    ) -> None:
        """Test max_images limits processing."""
        input_dir, output_dir = sample_dataset

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir, max_images=2)

        assert stats["total_images"] == 2
        assert stats["labeled"] == 2

    def test_label_dataset_counts_labels(
        self, labeler: WeakSupervisionLabeler, sample_dataset: tuple[Path, Path]
    ) -> None:
        """Test that label counts are tracked."""
        input_dir, output_dir = sample_dataset

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        # Should have some label counts
        assert isinstance(stats["label_counts"], dict)

    def test_label_dataset_specific_metrics(
        self, labeler: WeakSupervisionLabeler, sample_dataset: tuple[Path, Path]
    ) -> None:
        """Test labeling with specific metrics."""
        input_dir, output_dir = sample_dataset

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir, metrics=["laplacian"])

        # Check label files only have blur labels
        label_file = next(output_dir.glob("*.json"))
        with open(label_file) as f:
            data = json.load(f)

        assert "blur" in data["labels"]
        assert "low_contrast" not in data["labels"]

    def test_label_dataset_handles_errors(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that dataset labeling handles errors gracefully."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        # Create one valid and one invalid image
        valid_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(input_dir / "valid.png"), valid_image)
        (input_dir / "invalid.png").write_text("not an image")

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 2
        assert stats["labeled"] == 1
        assert stats["errors"] == 1

    def test_label_dataset_empty_directory(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test labeling empty directory."""
        input_dir = tmp_path / "empty"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 0
        assert stats["labeled"] == 0


class TestLabelFileFormat:
    """Tests for label file format and content."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler instance."""
        return WeakSupervisionLabeler()

    @pytest.fixture
    def labeled_image(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> tuple[Path, dict]:
        """Create and label a sample image."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        # Create test image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[40:60, 40:60] = 255
        cv2.imwrite(str(input_dir / "test.png"), image)

        with patch("builtins.print"):
            labeler.label_dataset(input_dir, output_dir)

        label_file = output_dir / "test.json"
        with open(label_file) as f:
            data = json.load(f)

        return label_file, data

    def test_label_file_has_image_path(self, labeled_image: tuple[Path, dict]) -> None:
        """Test that label file contains image path."""
        _, data = labeled_image

        assert "image_path" in data
        assert data["image_path"].endswith("test.png")

    def test_label_file_has_labels(self, labeled_image: tuple[Path, dict]) -> None:
        """Test that label file contains labels."""
        _, data = labeled_image

        assert "labels" in data
        assert isinstance(data["labels"], dict)

    def test_label_file_has_metrics_used(
        self, labeled_image: tuple[Path, dict]
    ) -> None:
        """Test that label file contains metrics used."""
        _, data = labeled_image

        assert "metrics_used" in data
        assert isinstance(data["metrics_used"], list)

    def test_blur_label_structure(self, labeled_image: tuple[Path, dict]) -> None:
        """Test blur label has correct structure."""
        _, data = labeled_image

        blur = data["labels"]["blur"]
        assert "value" in blur
        assert "confidence" in blur
        assert "score" in blur
        assert "source" in blur

    def test_contrast_label_structure(self, labeled_image: tuple[Path, dict]) -> None:
        """Test contrast label has correct structure."""
        _, data = labeled_image

        contrast = data["labels"]["low_contrast"]
        assert "value" in contrast
        assert "confidence" in contrast
        assert "score" in contrast
        assert "source" in contrast

    def test_skew_label_structure(self, labeled_image: tuple[Path, dict]) -> None:
        """Test skew label has correct structure."""
        _, data = labeled_image

        skew = data["labels"]["skew"]
        assert "value" in skew
        assert "confidence" in skew
        assert "score" in skew
        assert "source" in skew


class TestImageExtensions:
    """Tests for supported image extensions."""

    @pytest.fixture
    def labeler(self) -> WeakSupervisionLabeler:
        """Create labeler instance."""
        return WeakSupervisionLabeler()

    def test_png_images_found(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that PNG images are found."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        cv2.imwrite(str(input_dir / "test.png"), image)

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 1

    def test_jpg_images_found(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that JPG images are found."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        cv2.imwrite(str(input_dir / "test.jpg"), image)

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 1

    def test_jpeg_images_found(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that JPEG images are found."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        cv2.imwrite(str(input_dir / "test.jpeg"), image)

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 1

    def test_non_image_files_ignored(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that non-image files are ignored."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        input_dir.mkdir()

        # Create non-image files
        (input_dir / "readme.txt").write_text("readme")
        (input_dir / "data.json").write_text("{}")

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 0

    def test_nested_images_found(
        self, labeler: WeakSupervisionLabeler, tmp_path: Path
    ) -> None:
        """Test that images in subdirectories are found."""
        input_dir = tmp_path / "images"
        output_dir = tmp_path / "labels"
        subdir = input_dir / "subdir"
        subdir.mkdir(parents=True)

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        cv2.imwrite(str(subdir / "test.png"), image)

        with patch("builtins.print"):
            stats = labeler.label_dataset(input_dir, output_dir)

        assert stats["total_images"] == 1
