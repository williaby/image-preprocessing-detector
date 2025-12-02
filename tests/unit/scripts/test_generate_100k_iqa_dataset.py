# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/generate_100k_iqa_dataset.py - 100K IQA dataset generation.

These tests verify the 100K IQA dataset generation script correctly:
- Configures dataset generation
- Applies augmentations
- Tracks distributions
- Generates weak supervision labels
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
from PIL import Image

# Mock albumentations and datasets before importing
sys.modules["albumentations"] = MagicMock()
sys.modules["datasets"] = MagicMock()

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_100k_iqa_dataset import (
    AugmentationPipeline,
    DatasetConfig,
    DatasetGenerator,
)


class TestDatasetConfig:
    """Tests for DatasetConfig class."""

    def test_total_samples(self) -> None:
        """Test total samples constant."""
        assert DatasetConfig.TOTAL_SAMPLES == 100_000

    def test_composition_defined(self) -> None:
        """Test composition is defined."""
        assert len(DatasetConfig.COMPOSITION) >= 4

    def test_composition_sums_to_target(self) -> None:
        """Test composition sums to total samples."""
        total = sum(DatasetConfig.COMPOSITION.values())

        assert total == DatasetConfig.TOTAL_SAMPLES

    def test_distributions_defined(self) -> None:
        """Test distributions are defined."""
        assert len(DatasetConfig.DISTRIBUTIONS) >= 10

    def test_defect_type_distribution(self) -> None:
        """Test defect type distribution."""
        defect_dist = DatasetConfig.DISTRIBUTIONS["defect_type"]

        assert "blur" in defect_dist
        assert "noise" in defect_dist
        assert "skew" in defect_dist
        assert "illumination" in defect_dist
        assert "artifacts" in defect_dist

    def test_severity_distribution(self) -> None:
        """Test severity distribution."""
        severity_dist = DatasetConfig.DISTRIBUTIONS["severity"]

        assert "mild" in severity_dist
        assert "moderate" in severity_dist
        assert "severe" in severity_dist

    def test_color_mode_distribution(self) -> None:
        """Test color mode distribution sums to 1."""
        color_dist = DatasetConfig.DISTRIBUTIONS["color_mode"]
        total = sum(color_dist.values())

        assert abs(total - 1.0) < 0.01


class TestAugmentationPipeline:
    """Tests for AugmentationPipeline class."""

    def test_init(self) -> None:
        """Test pipeline initialization."""
        pipeline = AugmentationPipeline()

        assert hasattr(pipeline, "defect_transforms")

    def test_defect_transforms_defined(self) -> None:
        """Test defect transforms are defined."""
        pipeline = AugmentationPipeline()

        assert "blur" in pipeline.defect_transforms
        assert "noise" in pipeline.defect_transforms
        assert "skew" in pipeline.defect_transforms
        assert "illumination" in pipeline.defect_transforms
        assert "artifacts" in pipeline.defect_transforms

    def test_apply_zero_defects(self) -> None:
        """Test applying zero defects returns unchanged image."""
        pipeline = AugmentationPipeline()
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        result_image, applied = pipeline.apply_defects(image, 0)

        assert applied == []
        assert np.array_equal(result_image, image)


class TestDatasetGenerator:
    """Tests for DatasetGenerator class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test generator initialization."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        assert generator.output_dir == tmp_path
        assert generator.config == config

    def test_setup_output_directories(self, tmp_path: Path) -> None:
        """Test output directory creation."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        assert (tmp_path / "images").exists()
        assert (tmp_path / "metadata").exists()

    def test_estimate_dpi(self, tmp_path: Path) -> None:
        """Test DPI estimation."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        # Create portrait image 850x1100 (100 DPI at 8.5x11)
        image = Image.new("RGB", (850, 1100))
        dpi = generator.estimate_dpi(image)

        assert dpi == 100  # 850 / 8.5 = 100

    def test_infer_layout_type(self, tmp_path: Path) -> None:
        """Test layout type inference."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        assert generator.infer_layout_type("tablebank") == "single_column"
        assert generator.infer_layout_type("pubtabnet") == "single_column"

    def test_infer_document_type(self, tmp_path: Path) -> None:
        """Test document type inference."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        assert generator.infer_document_type("tablebank") == "born_digital"
        assert generator.infer_document_type("iam") == "image_only"

    def test_infer_category(self, tmp_path: Path) -> None:
        """Test category inference."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        assert generator.infer_category("tablebank") == "tables"
        assert generator.infer_category("iam") == "handwriting"
        assert generator.infer_category("funsd_plus") == "forms"

    def test_choose_num_defects(self, tmp_path: Path) -> None:
        """Test number of defects is in valid range."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        for _ in range(100):
            num = generator.choose_num_defects()
            assert 0 <= num <= 3

    def test_choose_jpeg_quality(self, tmp_path: Path) -> None:
        """Test JPEG quality is in valid range."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        for _ in range(100):
            quality = generator.choose_jpeg_quality()
            assert 30 <= quality <= 100

    def test_generate_weak_supervision_labels(self, tmp_path: Path) -> None:
        """Test weak supervision label generation."""
        config = DatasetConfig()
        generator = DatasetGenerator(tmp_path, config)

        image = np.zeros((100, 100, 3), dtype=np.uint8)
        labels = generator.generate_weak_supervision_labels(image, ["blur", "noise"])

        assert labels["blur"] == 1.0
        assert labels["noise"] == 1.0
        assert labels["skew"] == 0.0


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from generate_100k_iqa_dataset import main

        assert callable(main)
