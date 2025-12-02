# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/generate_parasitic_content_labels.py - Parasitic content detection.

These tests verify the parasitic content label generation correctly:
- Extracts text from bounding boxes
- Computes text similarity
- Groups pages by document
- Identifies repeating patterns
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

# Mock pytesseract before importing the script
sys.modules["pytesseract"] = MagicMock()

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_parasitic_content_labels import (
    CLASS_PAGE_FOOTER,
    CLASS_PAGE_HEADER,
    PatternConfig,
    ProcessingContext,
    _find_repeating_patterns,
    compute_similarity,
    group_pages_by_document,
)


class TestClassConstants:
    """Tests for class ID constants."""

    def test_header_class_id(self) -> None:
        """Test page header class ID."""
        assert CLASS_PAGE_HEADER == 6

    def test_footer_class_id(self) -> None:
        """Test page footer class ID."""
        assert CLASS_PAGE_FOOTER == 5


class TestProcessingContext:
    """Tests for ProcessingContext dataclass."""

    def test_create_context(self) -> None:
        """Test creating processing context."""
        context = ProcessingContext(
            img_id_to_path={1: Path("/test/img1.png")},
            img_to_anns={1: [{"id": 1}]},
            parasitic_annotations={},
        )

        assert 1 in context.img_id_to_path
        assert 1 in context.img_to_anns
        assert context.parasitic_annotations == {}


class TestPatternConfig:
    """Tests for PatternConfig dataclass."""

    def test_create_config(self) -> None:
        """Test creating pattern config."""
        config = PatternConfig(
            similarity_threshold=0.85,
            min_occurrences=3,
        )

        assert config.similarity_threshold == pytest.approx(0.85)
        assert config.min_occurrences == 3


class TestComputeSimilarity:
    """Tests for compute_similarity function."""

    def test_identical_strings(self) -> None:
        """Test similarity of identical strings."""
        result = compute_similarity("hello world", "hello world")

        assert result == pytest.approx(1.0)

    def test_completely_different(self) -> None:
        """Test similarity of completely different strings."""
        result = compute_similarity("abc", "xyz")

        assert result < 0.5

    def test_similar_strings(self) -> None:
        """Test similarity of similar strings."""
        result = compute_similarity("page 1 of 10", "page 2 of 10")

        assert result > 0.7

    def test_empty_string_first(self) -> None:
        """Test similarity with empty first string."""
        result = compute_similarity("", "hello")

        assert result == pytest.approx(0.0)

    def test_empty_string_second(self) -> None:
        """Test similarity with empty second string."""
        result = compute_similarity("hello", "")

        assert result == pytest.approx(0.0)

    def test_both_empty(self) -> None:
        """Test similarity with both strings empty."""
        result = compute_similarity("", "")

        assert result == pytest.approx(0.0)

    def test_case_sensitivity(self) -> None:
        """Test that similarity is case sensitive."""
        result = compute_similarity("Hello", "hello")

        assert result < 1.0

    def test_whitespace_handling(self) -> None:
        """Test similarity with different whitespace."""
        result = compute_similarity("hello world", "hello  world")

        assert result > 0.8


class TestGroupPagesByDocument:
    """Tests for group_pages_by_document function."""

    def test_group_with_doc_name(self) -> None:
        """Test grouping pages by doc_name field."""
        coco_data = {
            "images": [
                {"id": 1, "file_name": "doc1_p1.png", "doc_name": "document_1"},
                {"id": 2, "file_name": "doc1_p2.png", "doc_name": "document_1"},
                {"id": 3, "file_name": "doc2_p1.png", "doc_name": "document_2"},
            ]
        }

        result = group_pages_by_document(coco_data)

        assert len(result) == 2
        assert len(result["document_1"]) == 2
        assert len(result["document_2"]) == 1

    def test_group_without_doc_name(self) -> None:
        """Test grouping pages without doc_name field (uses filename stem)."""
        coco_data = {
            "images": [
                {"id": 1, "file_name": "doc1.png"},
                {"id": 2, "file_name": "doc2.png"},
            ]
        }

        result = group_pages_by_document(coco_data)

        assert "doc1" in result
        assert "doc2" in result

    def test_group_empty_images(self) -> None:
        """Test grouping with no images."""
        coco_data = {"images": []}

        result = group_pages_by_document(coco_data)

        assert result == {}

    def test_group_preserves_image_ids(self) -> None:
        """Test that image IDs are preserved in groups."""
        coco_data = {
            "images": [
                {"id": 100, "file_name": "doc.png", "doc_name": "test_doc"},
                {"id": 200, "file_name": "doc2.png", "doc_name": "test_doc"},
            ]
        }

        result = group_pages_by_document(coco_data)

        assert 100 in result["test_doc"]
        assert 200 in result["test_doc"]


class TestFindRepeatingPatterns:
    """Tests for _find_repeating_patterns function."""

    def test_find_identical_patterns(self) -> None:
        """Test finding identical repeating patterns."""
        texts = ["page 1", "page 1", "page 1", "page 1"]
        config = PatternConfig(similarity_threshold=0.85, min_occurrences=3)

        result = _find_repeating_patterns(texts, config)

        assert len(result) == 1
        assert len(result[0]) == 4

    def test_find_similar_patterns(self) -> None:
        """Test finding similar repeating patterns."""
        texts = ["page 1 of 10", "page 2 of 10", "page 3 of 10", "page 4 of 10"]
        config = PatternConfig(similarity_threshold=0.7, min_occurrences=3)

        result = _find_repeating_patterns(texts, config)

        assert len(result) >= 1

    def test_no_patterns_below_threshold(self) -> None:
        """Test no patterns found below minimum occurrences."""
        texts = ["unique text 1", "unique text 2"]
        config = PatternConfig(similarity_threshold=0.85, min_occurrences=3)

        result = _find_repeating_patterns(texts, config)

        assert len(result) == 0

    def test_multiple_pattern_groups(self) -> None:
        """Test finding multiple distinct pattern groups."""
        texts = [
            "header 1",
            "header 1",
            "header 1",
            "footer 1",
            "footer 1",
            "footer 1",
        ]
        config = PatternConfig(similarity_threshold=0.85, min_occurrences=3)

        result = _find_repeating_patterns(texts, config)

        assert len(result) == 2

    def test_empty_texts(self) -> None:
        """Test with empty text list."""
        texts = []
        config = PatternConfig(similarity_threshold=0.85, min_occurrences=3)

        result = _find_repeating_patterns(texts, config)

        assert result == []


class TestExtractTextFromBbox:
    """Tests for extract_text_from_bbox function."""

    def test_extract_with_mock_tesseract(self, tmp_path: Path) -> None:
        """Test text extraction with mocked Tesseract."""
        from generate_parasitic_content_labels import extract_text_from_bbox

        # Create a test image
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[20:80, 20:180] = 255  # White rectangle
        img_path = tmp_path / "test.png"
        cv2.imwrite(str(img_path), img)

        # Mock pytesseract
        with patch("generate_parasitic_content_labels.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "  Test Text  "

            result = extract_text_from_bbox(img_path, [20, 20, 160, 60])

            assert result == "test text"

    def test_extract_missing_image(self, tmp_path: Path) -> None:
        """Test extraction with missing image file."""
        from generate_parasitic_content_labels import extract_text_from_bbox

        result = extract_text_from_bbox(tmp_path / "missing.png", [0, 0, 100, 100])

        assert result == ""

    def test_extract_normalizes_text(self, tmp_path: Path) -> None:
        """Test that extracted text is normalized."""
        from generate_parasitic_content_labels import extract_text_from_bbox

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img_path = tmp_path / "test.png"
        cv2.imwrite(str(img_path), img)

        with patch("generate_parasitic_content_labels.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "  HELLO   WORLD  "

            result = extract_text_from_bbox(img_path, [0, 0, 100, 100])

            assert result == "hello world"


class TestGenerateDataset:
    """Tests for generate_dataset function."""

    def test_missing_coco_file_raises(self, tmp_path: Path) -> None:
        """Test that missing COCO file raises error."""
        from generate_parasitic_content_labels import generate_dataset

        with pytest.raises(FileNotFoundError):
            generate_dataset(tmp_path, tmp_path / "output", "train")

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

        # Create COCO JSON with header/footer annotations
        coco_data = {
            "images": [
                {
                    "id": 1,
                    "file_name": "doc1_p1.png",
                    "doc_name": "doc1",
                    "width": 800,
                    "height": 1000,
                },
                {
                    "id": 2,
                    "file_name": "doc1_p2.png",
                    "doc_name": "doc1",
                    "width": 800,
                    "height": 1000,
                },
                {
                    "id": 3,
                    "file_name": "doc1_p3.png",
                    "doc_name": "doc1",
                    "width": 800,
                    "height": 1000,
                },
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 6,
                    "bbox": [100, 10, 600, 50],
                },  # Header
                {
                    "id": 2,
                    "image_id": 2,
                    "category_id": 6,
                    "bbox": [100, 10, 600, 50],
                },  # Header
                {
                    "id": 3,
                    "image_id": 3,
                    "category_id": 6,
                    "bbox": [100, 10, 600, 50],
                },  # Header
            ],
            "categories": [
                {"id": 5, "name": "page-footer"},
                {"id": 6, "name": "page-header"},
            ],
        }

        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        # Create sample images
        for img_info in coco_data["images"]:
            img = np.zeros((1000, 800, 3), dtype=np.uint8)
            cv2.imwrite(str(images_dir / img_info["file_name"]), img)

        return doclaynet_dir

    def test_generate_creates_output(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test that generate_dataset creates output file."""
        from generate_parasitic_content_labels import generate_dataset

        output_dir = tmp_path / "output"

        with patch("generate_parasitic_content_labels.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "Company Header"

            generate_dataset(
                mock_doclaynet,
                output_dir,
                "train",
                similarity_threshold=0.85,
                min_occurrences=3,
            )

        assert output_dir.exists()
        output_file = output_dir / "train_parasitic_content.json"
        assert output_file.exists()

    def test_output_structure(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test that output has correct structure."""
        from generate_parasitic_content_labels import generate_dataset

        output_dir = tmp_path / "output"

        with patch("generate_parasitic_content_labels.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "Repeating Header"

            generate_dataset(
                mock_doclaynet,
                output_dir,
                "train",
                similarity_threshold=0.85,
                min_occurrences=3,
            )

        with open(output_dir / "train_parasitic_content.json") as f:
            data = json.load(f)

        assert "info" in data
        assert "parasitic_annotations" in data
        assert "statistics" in data
        assert "similarity_threshold" in data["info"]
        assert "min_occurrences" in data["info"]
