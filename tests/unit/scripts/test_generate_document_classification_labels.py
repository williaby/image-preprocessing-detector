# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/generate_document_classification_labels.py.

These tests verify the document classification label generation correctly:
- Loads COCO format annotations
- Classifies documents based on layout elements
- Handles different document types (image_only, born_digital, hybrid)
- Generates proper output format
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_document_classification_labels import (
    DOCLAYNET_CLASSES,
    IMAGE_CLASSES,
    TEXT_CLASSES,
    classify_document_type,
    generate_classification_labels,
    load_coco_annotations,
)


class TestDocLayNetClasses:
    """Tests for DocLayNet class constants."""

    def test_doclaynet_classes_count(self) -> None:
        """Test that all 11 DocLayNet classes are defined."""
        assert len(DOCLAYNET_CLASSES) == 11

    def test_class_ids_1_to_11(self) -> None:
        """Test class IDs are 1-11."""
        assert set(DOCLAYNET_CLASSES.keys()) == set(range(1, 12))

    def test_text_classes_defined(self) -> None:
        """Test TEXT_CLASSES includes expected classes."""
        # All except Picture (7)
        expected = {1, 2, 3, 4, 5, 6, 8, 9, 10, 11}
        assert expected == TEXT_CLASSES

    def test_image_classes_defined(self) -> None:
        """Test IMAGE_CLASSES includes only Picture."""
        assert {7} == IMAGE_CLASSES

    def test_text_and_image_classes_no_overlap(self) -> None:
        """Test that text and image classes don't overlap."""
        assert TEXT_CLASSES.isdisjoint(IMAGE_CLASSES)

    def test_picture_class_exists(self) -> None:
        """Test Picture class is properly defined."""
        assert 7 in DOCLAYNET_CLASSES
        assert DOCLAYNET_CLASSES[7] == "Picture"


class TestClassifyDocumentType:
    """Tests for classify_document_type function."""

    def test_no_annotations_returns_image_only(self) -> None:
        """Test empty annotations classified as image_only."""
        classification, class_counts = classify_document_type(1, [])

        assert classification == "image_only"
        assert class_counts == {}

    def test_text_only_returns_born_digital(self) -> None:
        """Test text-only annotations classified as born_digital."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 11},  # Title
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert classification == "born_digital"
        assert "Text" in class_counts
        assert "Title" in class_counts

    def test_picture_only_returns_image_only(self) -> None:
        """Test picture-only annotations classified as image_only."""
        annotations = [
            {"image_id": 1, "category_id": 7},  # Picture
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert classification == "image_only"
        assert "Picture" in class_counts

    def test_text_and_picture_returns_hybrid(self) -> None:
        """Test text + picture annotations classified as hybrid."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 7},  # Picture
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert classification == "hybrid"
        assert "Text" in class_counts
        assert "Picture" in class_counts

    def test_filters_by_image_id(self) -> None:
        """Test that only annotations for the given image_id are counted."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # For image 1
            {"image_id": 2, "category_id": 7},  # For image 2 - should be ignored
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert classification == "born_digital"
        assert "Picture" not in class_counts

    def test_counts_multiple_elements(self) -> None:
        """Test that multiple elements of same type are counted."""
        annotations = [
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 10},  # Text
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert class_counts["Text"] == 3

    def test_all_text_classes_count_as_text(self) -> None:
        """Test all TEXT_CLASSES categories count as text."""
        for cat_id in TEXT_CLASSES:
            annotations = [{"image_id": 1, "category_id": cat_id}]
            classification, _ = classify_document_type(1, annotations)
            assert classification == "born_digital", f"Category {cat_id} should be text"

    def test_unknown_category_handled(self) -> None:
        """Test unknown category ID is handled."""
        annotations = [
            {"image_id": 1, "category_id": 999},  # Unknown
        ]

        classification, class_counts = classify_document_type(1, annotations)

        # Unknown class should be recorded but not affect classification
        assert "Unknown" in class_counts
        assert classification == "image_only"  # No text or image detected


class TestLoadCocoAnnotations:
    """Tests for load_coco_annotations function."""

    def test_load_valid_coco_file(self, tmp_path: Path) -> None:
        """Test loading valid COCO format file."""
        coco_data = {
            "images": [{"id": 1, "file_name": "test.png"}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 10}],
        }

        coco_file = tmp_path / "test.json"
        with open(coco_file, "w") as f:
            json.dump(coco_data, f)

        result = load_coco_annotations(coco_file)

        assert len(result["images"]) == 1
        assert len(result["annotations"]) == 1

    def test_load_empty_coco_file(self, tmp_path: Path) -> None:
        """Test loading empty COCO file."""
        coco_data = {"images": [], "annotations": []}

        coco_file = tmp_path / "empty.json"
        with open(coco_file, "w") as f:
            json.dump(coco_data, f)

        result = load_coco_annotations(coco_file)

        assert result["images"] == []
        assert result["annotations"] == []

    def test_load_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Test loading non-existent file raises error."""
        fake_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_coco_annotations(fake_path)


class TestGenerateClassificationLabels:
    """Tests for generate_classification_labels function."""

    @pytest.fixture
    def mock_doclaynet(self, tmp_path: Path) -> Path:
        """Create mock DocLayNet directory structure."""
        doclaynet_dir = tmp_path / "doclaynet"
        coco_dir = doclaynet_dir / "ground_truth" / "coco"
        coco_dir.mkdir(parents=True)

        coco_data = {
            "images": [
                {"id": 1, "file_name": "doc1.png", "width": 100, "height": 100},
                {"id": 2, "file_name": "doc2.png", "width": 200, "height": 200},
            ],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 10},  # Text for doc1
                {"id": 2, "image_id": 2, "category_id": 7},  # Picture for doc2
                {"id": 3, "image_id": 2, "category_id": 10},  # Text for doc2
            ],
        }

        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        return doclaynet_dir

    def test_generates_output_file(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test that output file is generated."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        assert output_file.exists()

    def test_output_structure(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test output file has correct structure."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        assert "info" in data
        assert "classes" in data
        assert "class_distribution" in data
        assert "classifications" in data

    def test_classifies_documents_correctly(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test documents are classified correctly."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        classifications = {
            c["image_id"]: c["classification"] for c in data["classifications"]
        }

        # doc1 has only text -> born_digital
        assert classifications[1] == "born_digital"
        # doc2 has text + picture -> hybrid
        assert classifications[2] == "hybrid"

    def test_class_distribution_calculated(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test class distribution is calculated."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        assert data["class_distribution"]["born_digital"] == 1
        assert data["class_distribution"]["hybrid"] == 1

    def test_creates_output_directory(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test output directory is created if not exists."""
        output_dir = tmp_path / "nested" / "output" / "dir"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        assert output_dir.exists()

    def test_missing_coco_file_raises(self, tmp_path: Path) -> None:
        """Test missing COCO file raises error."""
        fake_doclaynet = tmp_path / "fake_doclaynet"
        fake_doclaynet.mkdir()
        output_dir = tmp_path / "output"

        with pytest.raises(FileNotFoundError):
            generate_classification_labels(fake_doclaynet, output_dir, "train")

    def test_info_metadata_complete(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test info metadata is complete."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        info = data["info"]
        assert info["split"] == "train"
        assert info["total_documents"] == 2
        assert info["classification_method"] == "weak_supervision"
        assert "DocLayNet" in info["source"]


class TestClassificationLogic:
    """Tests for classification logic edge cases."""

    def test_all_text_types_trigger_text(self) -> None:
        """Test all text-like classes trigger has_text."""
        for cat_id in TEXT_CLASSES:
            annotations = [{"image_id": 1, "category_id": cat_id}]
            classification, _ = classify_document_type(1, annotations)
            assert classification == "born_digital"

    def test_complex_document_with_many_elements(self) -> None:
        """Test complex document with many element types."""
        annotations = [
            {"image_id": 1, "category_id": 1},  # Caption
            {"image_id": 1, "category_id": 4},  # List
            {"image_id": 1, "category_id": 7},  # Picture
            {"image_id": 1, "category_id": 9},  # Table
            {"image_id": 1, "category_id": 10},  # Text
            {"image_id": 1, "category_id": 11},  # Title
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert classification == "hybrid"
        assert len(class_counts) == 6

    def test_document_with_only_footers(self) -> None:
        """Test document with only page footers."""
        annotations = [
            {"image_id": 1, "category_id": 5},  # Page-footer
        ]

        classification, _ = classify_document_type(1, annotations)

        # Footer is text-like
        assert classification == "born_digital"

    def test_document_with_formulas_only(self) -> None:
        """Test document with only formulas."""
        annotations = [
            {"image_id": 1, "category_id": 3},  # Formula
            {"image_id": 1, "category_id": 3},  # Formula
        ]

        classification, class_counts = classify_document_type(1, annotations)

        assert classification == "born_digital"
        assert class_counts["Formula"] == 2


class TestOutputFormat:
    """Tests for output format compliance."""

    @pytest.fixture
    def mock_doclaynet(self, tmp_path: Path) -> Path:
        """Create minimal mock DocLayNet."""
        doclaynet_dir = tmp_path / "doclaynet"
        coco_dir = doclaynet_dir / "ground_truth" / "coco"
        coco_dir.mkdir(parents=True)

        coco_data = {
            "images": [
                {
                    "id": 1,
                    "file_name": "test.png",
                    "width": 800,
                    "height": 600,
                    "doc_name": "test_doc",
                }
            ],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 10}],
        }

        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        return doclaynet_dir

    def test_classification_entry_structure(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test classification entry has all required fields."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        entry = data["classifications"][0]

        assert "image_id" in entry
        assert "file_name" in entry
        assert "doc_name" in entry
        assert "classification" in entry
        assert "layout_elements" in entry
        assert "width" in entry
        assert "height" in entry

    def test_classes_list_complete(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test classes list contains all classification types."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        expected_classes = ["image_only", "born_digital", "hybrid"]
        assert data["classes"] == expected_classes

    def test_file_name_preserved(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test file name from COCO is preserved."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        assert data["classifications"][0]["file_name"] == "test.png"

    def test_doc_name_extracted(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test doc_name is extracted from COCO or file name."""
        output_dir = tmp_path / "output"

        generate_classification_labels(mock_doclaynet, output_dir, "train")

        output_file = output_dir / "train_document_classification.json"
        with open(output_file) as f:
            data = json.load(f)

        assert data["classifications"][0]["doc_name"] == "test_doc"
