"""Tests for scripts/generate_vertical_text_labels.py - Vertical text generation.

These tests verify the vertical text label generation correctly:
- Rotates images at various angles
- Adjusts bounding boxes for rotation
- Generates COCO-format annotations
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

# Scripts directory added to sys.path via tests/conftest.py
from generate_vertical_text_labels import (
    ORIENTATIONS,
    _build_annotation_mappings,
    _create_output_coco_structure,
    adjust_bbox_for_rotation,
    get_rotated_image_dimensions,
    rotate_image,
)


class TestOrientations:
    """Tests for orientation constants."""

    def test_orientation_count(self) -> None:
        """Test that 4 orientations are defined."""
        assert len(ORIENTATIONS) == 4

    def test_orientation_angles(self) -> None:
        """Test that correct angles are defined."""
        assert 0 in ORIENTATIONS
        assert 90 in ORIENTATIONS
        assert 180 in ORIENTATIONS
        assert 270 in ORIENTATIONS

    def test_orientation_names(self) -> None:
        """Test orientation names."""
        assert ORIENTATIONS[0] == "horizontal"
        assert ORIENTATIONS[90] == "vertical_right"
        assert ORIENTATIONS[180] == "upside_down"
        assert ORIENTATIONS[270] == "vertical_left"


class TestRotateImage:
    """Tests for rotate_image function."""

    @pytest.fixture
    def test_image(self) -> np.ndarray:
        """Create a test image with asymmetric content."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        # Mark top-left corner
        img[0:20, 0:40] = [255, 0, 0]  # Blue in BGR
        return img

    def test_rotate_0_degrees(self, test_image: np.ndarray) -> None:
        """Test 0 degree rotation (no change)."""
        result = rotate_image(test_image, 0)

        assert result.shape == test_image.shape
        assert np.array_equal(result, test_image)

    def test_rotate_90_degrees(self, test_image: np.ndarray) -> None:
        """Test 90 degree rotation."""
        result = rotate_image(test_image, 90)

        # Width and height should swap
        assert result.shape == (200, 100, 3)

    def test_rotate_180_degrees(self, test_image: np.ndarray) -> None:
        """Test 180 degree rotation."""
        result = rotate_image(test_image, 180)

        # Shape should be same
        assert result.shape == test_image.shape

    def test_rotate_270_degrees(self, test_image: np.ndarray) -> None:
        """Test 270 degree rotation."""
        result = rotate_image(test_image, 270)

        # Width and height should swap
        assert result.shape == (200, 100, 3)

    def test_rotate_invalid_angle(self, test_image: np.ndarray) -> None:
        """Test that invalid angle raises error."""
        with pytest.raises(ValueError, match="Invalid angle"):
            rotate_image(test_image, 45)


class TestAdjustBboxForRotation:
    """Tests for adjust_bbox_for_rotation function."""

    def test_adjust_0_degrees(self) -> None:
        """Test bbox adjustment for 0 degrees."""
        bbox = [10, 20, 100, 50]

        result = adjust_bbox_for_rotation(bbox, 800, 600, 0)

        assert result == [10, 20, 100, 50]

    def test_adjust_90_degrees(self) -> None:
        """Test bbox adjustment for 90 degrees."""
        # Original: top-left corner at (10, 20), size 100x50
        bbox = [10, 20, 100, 50]
        img_width = 800
        img_height = 600

        result = adjust_bbox_for_rotation(bbox, img_width, img_height, 90)

        # After 90° clockwise: new_x = height - (y + h), new_y = x
        expected_x = img_height - (20 + 50)  # 530
        expected_y = 10
        expected_w = 50  # height becomes width
        expected_h = 100  # width becomes height

        assert result == [expected_x, expected_y, expected_w, expected_h]

    def test_adjust_180_degrees(self) -> None:
        """Test bbox adjustment for 180 degrees."""
        bbox = [10, 20, 100, 50]
        img_width = 800
        img_height = 600

        result = adjust_bbox_for_rotation(bbox, img_width, img_height, 180)

        # After 180°: both x and y flip
        expected_x = img_width - (10 + 100)  # 690
        expected_y = img_height - (20 + 50)  # 530

        assert result == [expected_x, expected_y, 100, 50]

    def test_adjust_270_degrees(self) -> None:
        """Test bbox adjustment for 270 degrees."""
        bbox = [10, 20, 100, 50]
        img_width = 800
        img_height = 600

        result = adjust_bbox_for_rotation(bbox, img_width, img_height, 270)

        # After 270° (or 90° counter-clockwise)
        expected_x = 20
        expected_y = img_width - (10 + 100)  # 690
        expected_w = 50
        expected_h = 100

        assert result == [expected_x, expected_y, expected_w, expected_h]

    def test_adjust_invalid_angle(self) -> None:
        """Test that invalid angle raises error."""
        with pytest.raises(ValueError):
            adjust_bbox_for_rotation([0, 0, 10, 10], 100, 100, 45)


class TestGetRotatedImageDimensions:
    """Tests for get_rotated_image_dimensions function."""

    def test_dimensions_0_degrees(self) -> None:
        """Test dimensions for 0 degree rotation."""
        result = get_rotated_image_dimensions(800, 600, 0)

        assert result == (800, 600)

    def test_dimensions_90_degrees(self) -> None:
        """Test dimensions for 90 degree rotation."""
        result = get_rotated_image_dimensions(800, 600, 90)

        # Dimensions swap
        assert result == (600, 800)

    def test_dimensions_180_degrees(self) -> None:
        """Test dimensions for 180 degree rotation."""
        result = get_rotated_image_dimensions(800, 600, 180)

        # Dimensions stay same
        assert result == (800, 600)

    def test_dimensions_270_degrees(self) -> None:
        """Test dimensions for 270 degree rotation."""
        result = get_rotated_image_dimensions(800, 600, 270)

        # Dimensions swap
        assert result == (600, 800)


class TestBuildAnnotationMappings:
    """Tests for _build_annotation_mappings function."""

    def test_build_mappings(self) -> None:
        """Test building annotation mappings."""
        coco_data = {
            "images": [
                {"id": 1, "file_name": "img1.png", "width": 800, "height": 600},
                {"id": 2, "file_name": "img2.png", "width": 800, "height": 600},
            ],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 10},  # Text
                {"id": 2, "image_id": 1, "category_id": 11},  # Title
                {"id": 3, "image_id": 2, "category_id": 10},  # Text
            ],
        }
        text_category_ids = [10, 11]

        img_id_to_info, img_to_anns, text_images = _build_annotation_mappings(
            coco_data, text_category_ids
        )

        assert len(img_id_to_info) == 2
        assert len(img_to_anns) == 2
        assert len(text_images) == 2

    def test_build_mappings_filters_categories(self) -> None:
        """Test that mappings filter by category IDs."""
        coco_data = {
            "images": [{"id": 1, "file_name": "img1.png"}],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 10},  # Included
                {"id": 2, "image_id": 1, "category_id": 99},  # Excluded
            ],
        }

        _, img_to_anns, _ = _build_annotation_mappings(coco_data, [10])

        assert len(img_to_anns[1]) == 1

    def test_build_mappings_empty_data(self) -> None:
        """Test building mappings with empty data."""
        coco_data = {"images": [], "annotations": []}

        img_id_to_info, img_to_anns, text_images = _build_annotation_mappings(
            coco_data, [10]
        )

        assert img_id_to_info == {}
        assert img_to_anns == {}
        assert text_images == []


class TestCreateOutputCocoStructure:
    """Tests for _create_output_coco_structure function."""

    def test_create_structure(self) -> None:
        """Test creating output COCO structure."""
        result = _create_output_coco_structure()

        assert "info" in result
        assert "images" in result
        assert "annotations" in result
        assert "categories" in result

    def test_categories_for_orientations(self) -> None:
        """Test that categories include all orientations."""
        result = _create_output_coco_structure()

        category_ids = [c["id"] for c in result["categories"]]

        assert 0 in category_ids
        assert 90 in category_ids
        assert 180 in category_ids
        assert 270 in category_ids

    def test_category_names(self) -> None:
        """Test category names match orientations."""
        result = _create_output_coco_structure()

        for category in result["categories"]:
            angle = category["id"]
            assert category["name"] == ORIENTATIONS[angle]


class TestGenerateDataset:
    """Tests for generate_dataset function."""

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

        # Create COCO JSON with text annotations
        coco_data = {
            "images": [
                {"id": 1, "file_name": "doc1.png", "width": 800, "height": 1000},
                {"id": 2, "file_name": "doc2.png", "width": 800, "height": 1000},
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 10,
                    "bbox": [100, 100, 600, 100],
                },
                {
                    "id": 2,
                    "image_id": 2,
                    "category_id": 10,
                    "bbox": [100, 200, 600, 100],
                },
            ],
            "categories": [
                {"id": 10, "name": "Text"},
            ],
        }

        with open(coco_dir / "train.json", "w") as f:
            json.dump(coco_data, f)

        # Create sample images
        for img_info in coco_data["images"]:
            img = np.zeros((1000, 800, 3), dtype=np.uint8)
            cv2.imwrite(str(images_dir / img_info["file_name"]), img)

        return doclaynet_dir

    def test_missing_coco_file_raises(self, tmp_path: Path) -> None:
        """Test that missing COCO file raises error."""
        from generate_vertical_text_labels import generate_dataset

        with pytest.raises(FileNotFoundError):
            generate_dataset(tmp_path, tmp_path / "output", "train")

    def test_generate_creates_output(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test that generate_dataset creates output."""
        from generate_vertical_text_labels import generate_dataset

        output_dir = tmp_path / "output"

        generate_dataset(
            mock_doclaynet,
            output_dir,
            "train",
            num_samples_per_orientation=1,
            text_category_ids=[10],
        )

        assert output_dir.exists()
        assert (output_dir / "train_vertical_text.json").exists()
        assert (output_dir / "images").exists()

    def test_generate_creates_rotated_images(
        self, mock_doclaynet: Path, tmp_path: Path
    ) -> None:
        """Test that rotated images are created."""
        from generate_vertical_text_labels import generate_dataset

        output_dir = tmp_path / "output"

        generate_dataset(
            mock_doclaynet,
            output_dir,
            "train",
            num_samples_per_orientation=1,
            text_category_ids=[10],
        )

        images = list((output_dir / "images").glob("*.png"))
        assert len(images) >= 4  # At least 4 orientations

    def test_output_json_structure(self, mock_doclaynet: Path, tmp_path: Path) -> None:
        """Test output JSON structure."""
        from generate_vertical_text_labels import generate_dataset

        output_dir = tmp_path / "output"

        generate_dataset(
            mock_doclaynet,
            output_dir,
            "train",
            num_samples_per_orientation=1,
            text_category_ids=[10],
        )

        with open(output_dir / "train_vertical_text.json") as f:
            data = json.load(f)

        assert "info" in data
        assert "images" in data
        assert "annotations" in data
        assert "categories" in data

        # Check image entries have orientation info
        for img in data["images"]:
            assert "orientation_angle" in img

        # Check annotation entries have orientation info
        for ann in data["annotations"]:
            assert "orientation_angle" in ann
            assert "orientation_label" in ann
