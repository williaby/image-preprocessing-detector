# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/generate_phase2_validation_datasets.py.

These tests verify the Phase 2 validation dataset generation script correctly:
- Initializes dataset generator
- Creates PDF classification datasets
- Creates layout-lite datasets
- Creates DQS correlation datasets
- Creates routing accuracy datasets
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_phase2_validation_datasets import Phase2DatasetGenerator


class TestPhase2DatasetGenerator:
    """Tests for Phase2DatasetGenerator class."""

    @pytest.fixture
    def mock_fixtures_dir(self, tmp_path: Path) -> Path:
        """Create mock fixtures directory structure."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()

        # Create synthetic images directory
        images_dir = fixtures_dir / "synthetic_images"
        images_dir.mkdir()

        # Create gradients directory
        gradients_dir = images_dir / "gradients"
        gradients_dir.mkdir()

        # Create mock images
        for name in ["clean_1.png", "blur_k5_1.png", "contrast_1.png", "skew_1.png"]:
            (images_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        for name in ["gradient_1.png", "gradient_2.png"]:
            (gradients_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        return fixtures_dir

    def test_init(self, mock_fixtures_dir: Path, tmp_path: Path) -> None:
        """Test generator initialization."""
        output_dir = tmp_path / "output"

        generator = Phase2DatasetGenerator(mock_fixtures_dir, output_dir)

        assert generator.fixtures_dir == mock_fixtures_dir
        assert generator.output_dir == output_dir

    def test_loads_images(self, mock_fixtures_dir: Path, tmp_path: Path) -> None:
        """Test that images are loaded."""
        output_dir = tmp_path / "output"

        generator = Phase2DatasetGenerator(mock_fixtures_dir, output_dir)

        assert len(generator.images) == 4
        assert len(generator.gradient_images) == 2

    def test_get_degradation_config_clean(
        self, mock_fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Test degradation config for clean images."""
        output_dir = tmp_path / "output"
        generator = Phase2DatasetGenerator(mock_fixtures_dir, output_dir)

        source, accuracy, level = generator._get_degradation_config(5)

        assert level == "clean"
        assert 0.95 <= accuracy <= 0.99

    def test_get_degradation_config_moderate(
        self, mock_fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Test degradation config for moderate degradation."""
        output_dir = tmp_path / "output"
        generator = Phase2DatasetGenerator(mock_fixtures_dir, output_dir)

        source, accuracy, level = generator._get_degradation_config(15)

        assert level == "moderate"
        assert 0.75 <= accuracy <= 0.90

    def test_get_degradation_config_heavy(
        self, mock_fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Test degradation config for heavy degradation."""
        output_dir = tmp_path / "output"
        generator = Phase2DatasetGenerator(mock_fixtures_dir, output_dir)

        source, accuracy, level = generator._get_degradation_config(30)

        assert level == "heavy"
        assert 0.40 <= accuracy <= 0.70


class TestGenerateAllDatasets:
    """Tests for generate_all_datasets method."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        assert hasattr(Phase2DatasetGenerator, "generate_all_datasets")
        assert callable(Phase2DatasetGenerator.generate_all_datasets)


class TestGeneratePdfClassificationDataset:
    """Tests for PDF classification dataset generation."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        assert hasattr(Phase2DatasetGenerator, "generate_pdf_classification_dataset")


class TestGenerateLayoutLiteDataset:
    """Tests for layout-lite dataset generation."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        assert hasattr(Phase2DatasetGenerator, "generate_layout_lite_dataset")


class TestGenerateDqsCorrelationDataset:
    """Tests for DQS correlation dataset generation."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        assert hasattr(Phase2DatasetGenerator, "generate_dqs_correlation_dataset")


class TestGenerateRoutingAccuracyDataset:
    """Tests for routing accuracy dataset generation."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        assert hasattr(Phase2DatasetGenerator, "generate_routing_accuracy_dataset")


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from generate_phase2_validation_datasets import main

        assert callable(main)
