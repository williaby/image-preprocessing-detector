"""Tests for scripts/generate_combined_classification_labels.py.

These tests verify the combined classification label generation correctly:
- Loads DocLayNet annotations
- Classifies pages as born_digital or hybrid
- Samples from DocLayNet and RVL-CDIP
- Generates combined output
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Scripts directory added to sys.path via tests/conftest.py
from generate_combined_classification_labels import (
    DOCLAYNET_CLASSES,
    IMAGE_CLASSES,
    TEXT_CLASSES,
    classify_doclaynet_page,
    generate_combined_classification_labels,
    load_doclaynet_annotations,
    sample_doclaynet_by_class,
    sample_rvl_cdip,
)


class TestClassConstants:
    """Tests for class constant definitions."""

    def test_doclaynet_classes_count(self) -> None:
        """Test DocLayNet has 11 classes."""
        assert len(DOCLAYNET_CLASSES) == 11

    def test_text_classes(self) -> None:
        """Test text classes are defined correctly."""
        # All except Picture (7)
        expected = {1, 2, 3, 4, 5, 6, 8, 9, 10, 11}
        assert expected == TEXT_CLASSES

    def test_image_classes(self) -> None:
        """Test image classes contain Picture."""
        assert {7} == IMAGE_CLASSES

    def test_class_names(self) -> None:
        """Test some class names."""
        assert DOCLAYNET_CLASSES[7] == "Picture"
        assert DOCLAYNET_CLASSES[10] == "Text"
        assert DOCLAYNET_CLASSES[9] == "Table"


class TestLoadDoclaynetAnnotations:
    """Tests for load_doclaynet_annotations function."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid COCO JSON."""
        coco_file = tmp_path / "train.json"
        coco_data = {
            "images": [{"id": 1, "file_name": "doc.png"}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 10}],
        }
        coco_file.write_text(json.dumps(coco_data))

        result = load_doclaynet_annotations(coco_file)

        assert len(result["images"]) == 1
        assert len(result["annotations"]) == 1

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that missing file raises error."""
        with pytest.raises(FileNotFoundError):
            load_doclaynet_annotations(tmp_path / "missing.json")


class TestClassifyDoclaynetPage:
    """Tests for classify_doclaynet_page function."""

    def test_classify_text_only_as_born_digital(self) -> None:
        """Test page with only text is born_digital."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 11},  # Title
        ]

        classification, counts = classify_doclaynet_page(1, annotations)

        assert classification == "born_digital"
        assert counts["Text"] == 1
        assert counts["Title"] == 1

    def test_classify_with_picture_as_hybrid(self) -> None:
        """Test page with text and picture is hybrid."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 7},  # Picture
        ]

        classification, counts = classify_doclaynet_page(1, annotations)

        assert classification == "hybrid"
        assert counts["Text"] == 1
        assert counts["Picture"] == 1

    def test_classify_empty_annotations(self) -> None:
        """Test page with no annotations."""
        classification, counts = classify_doclaynet_page(1, [])

        assert classification == "born_digital"
        assert counts == {}

    def test_classify_ignores_other_images(self) -> None:
        """Test that annotations for other images are ignored."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # This image
            {"image_id": 2, "category_id": 7},  # Different image
        ]

        classification, counts = classify_doclaynet_page(1, annotations)

        assert classification == "born_digital"
        assert "Picture" not in counts


class TestSampleDoclaynetByClass:
    """Tests for sample_doclaynet_by_class function."""

    @pytest.fixture
    def mock_doclaynet(self, tmp_path: Path) -> Path:
        """Create mock DocLayNet directory."""
        doclaynet_dir = tmp_path / "doclaynet"
        coco_dir = doclaynet_dir / "ground_truth" / "coco"
        coco_dir.mkdir(parents=True)

        # Create COCO JSON with mixed pages
        coco_data = {
            "images": [
                {"id": i, "file_name": f"doc{i}.png", "width": 800, "height": 1000}
                for i in range(1, 11)
            ],
            "annotations": [
                # First 5 images: text only (born_digital)
                *[{"id": i, "image_id": i, "category_id": 10} for i in range(1, 6)],
                # Last 5 images: text + picture (hybrid)
                *[
                    {"id": i + 10, "image_id": i, "category_id": 10}
                    for i in range(6, 11)
                ],
                *[
                    {"id": i + 20, "image_id": i, "category_id": 7}
                    for i in range(6, 11)
                ],
            ],
        }

        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        return doclaynet_dir

    def test_sample_born_digital(self, mock_doclaynet: Path) -> None:
        """Test sampling born_digital pages."""
        result = sample_doclaynet_by_class(
            mock_doclaynet, "train", born_digital_count=3, hybrid_count=0
        )

        born_digital = [e for e in result if e["classification"] == "born_digital"]
        assert len(born_digital) == 3

    def test_sample_hybrid(self, mock_doclaynet: Path) -> None:
        """Test sampling hybrid pages."""
        result = sample_doclaynet_by_class(
            mock_doclaynet, "train", born_digital_count=0, hybrid_count=3
        )

        hybrid = [e for e in result if e["classification"] == "hybrid"]
        assert len(hybrid) == 3

    def test_sample_both_classes(self, mock_doclaynet: Path) -> None:
        """Test sampling both classes."""
        result = sample_doclaynet_by_class(
            mock_doclaynet, "train", born_digital_count=2, hybrid_count=2
        )

        assert len(result) == 4

    def test_sample_missing_coco_raises(self, tmp_path: Path) -> None:
        """Test that missing COCO file raises error."""
        with pytest.raises(FileNotFoundError):
            sample_doclaynet_by_class(
                tmp_path, "train", born_digital_count=1, hybrid_count=1
            )


class TestSampleRvlCdip:
    """Tests for sample_rvl_cdip function."""

    @pytest.fixture
    def mock_rvl_cdip(self, tmp_path: Path) -> Path:
        """Create mock RVL-CDIP directory."""
        rvl_dir = tmp_path / "rvl-cdip"
        labels_dir = rvl_dir / "labels"
        labels_dir.mkdir(parents=True)

        # Create labels file
        labels = "\n".join([f"images/doc{i}.tif {i % 16}" for i in range(100)])
        (labels_dir / "train.txt").write_text(labels)

        return rvl_dir

    def test_sample_image_only(self, mock_rvl_cdip: Path) -> None:
        """Test sampling image_only pages."""
        result = sample_rvl_cdip(mock_rvl_cdip, "train", image_only_count=10)

        assert len(result) == 10
        assert all(e["classification"] == "image_only" for e in result)
        assert all(e["source"] == "rvl-cdip" for e in result)

    def test_sample_respects_count(self, mock_rvl_cdip: Path) -> None:
        """Test that sampling respects count limit."""
        result = sample_rvl_cdip(mock_rvl_cdip, "train", image_only_count=5)

        assert len(result) == 5

    def test_sample_missing_labels_raises(self, tmp_path: Path) -> None:
        """Test that missing labels file raises error."""
        with pytest.raises(FileNotFoundError):
            sample_rvl_cdip(tmp_path, "train", image_only_count=10)

    def test_sample_has_rvl_class(self, mock_rvl_cdip: Path) -> None:
        """Test that samples include RVL-CDIP class."""
        result = sample_rvl_cdip(mock_rvl_cdip, "train", image_only_count=5)

        assert all("rvl_cdip_class" in e for e in result)


class TestGenerateCombinedClassificationLabels:
    """Tests for generate_combined_classification_labels function."""

    @pytest.fixture
    def mock_datasets(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create mock DocLayNet and RVL-CDIP directories."""
        # DocLayNet
        doclaynet_dir = tmp_path / "doclaynet"
        coco_dir = doclaynet_dir / "ground_truth" / "coco"
        coco_dir.mkdir(parents=True)

        coco_data = {
            "images": [
                {"id": i, "file_name": f"doc{i}.png", "width": 800, "height": 1000}
                for i in range(1, 21)
            ],
            "annotations": [
                *[{"id": i, "image_id": i, "category_id": 10} for i in range(1, 11)],
                *[
                    {"id": i + 20, "image_id": i, "category_id": 10}
                    for i in range(11, 21)
                ],
                *[
                    {"id": i + 40, "image_id": i, "category_id": 7}
                    for i in range(11, 21)
                ],
            ],
        }
        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        # RVL-CDIP
        rvl_dir = tmp_path / "rvl-cdip"
        labels_dir = rvl_dir / "labels"
        labels_dir.mkdir(parents=True)
        labels = "\n".join([f"images/doc{i}.tif {i % 16}" for i in range(100)])
        (labels_dir / "train.txt").write_text(labels)

        return doclaynet_dir, rvl_dir

    def test_generates_output_file(
        self, mock_datasets: tuple[Path, Path], tmp_path: Path
    ) -> None:
        """Test that output file is generated."""
        doclaynet_dir, rvl_dir = mock_datasets
        output_dir = tmp_path / "output"

        generate_combined_classification_labels(
            doclaynet_dir, rvl_dir, output_dir, "train", samples_per_class=5
        )

        output_file = output_dir / "train_combined_classification.json"
        assert output_file.exists()

    def test_output_has_all_classes(
        self, mock_datasets: tuple[Path, Path], tmp_path: Path
    ) -> None:
        """Test output contains all three classes."""
        doclaynet_dir, rvl_dir = mock_datasets
        output_dir = tmp_path / "output"

        generate_combined_classification_labels(
            doclaynet_dir, rvl_dir, output_dir, "train", samples_per_class=5
        )

        with open(output_dir / "train_combined_classification.json") as f:
            data = json.load(f)

        assert "image_only" in data["classes"]
        assert "born_digital" in data["classes"]
        assert "hybrid" in data["classes"]

    def test_output_structure(
        self, mock_datasets: tuple[Path, Path], tmp_path: Path
    ) -> None:
        """Test output JSON structure."""
        doclaynet_dir, rvl_dir = mock_datasets
        output_dir = tmp_path / "output"

        generate_combined_classification_labels(
            doclaynet_dir, rvl_dir, output_dir, "train", samples_per_class=5
        )

        with open(output_dir / "train_combined_classification.json") as f:
            data = json.load(f)

        assert "info" in data
        assert "classes" in data
        assert "class_distribution" in data
        assert "classifications" in data

    def test_works_without_rvl_cdip(
        self, mock_datasets: tuple[Path, Path], tmp_path: Path
    ) -> None:
        """Test that function works without RVL-CDIP directory."""
        doclaynet_dir, _ = mock_datasets
        output_dir = tmp_path / "output"

        # Should not raise even with missing RVL-CDIP
        generate_combined_classification_labels(
            doclaynet_dir, None, output_dir, "train", samples_per_class=5
        )

        output_file = output_dir / "train_combined_classification.json"
        assert output_file.exists()
