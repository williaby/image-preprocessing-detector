# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/prepare_phase2_data.py - Phase 2 dataset preparation.

These tests verify the Phase 2 dataset preparation script correctly:
- Converts PDF to images
- Collects source images
- Generates augmented datasets
- Prints dataset summaries
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

# Mock albumentations and data modules before importing
sys.modules["albumentations"] = MagicMock()
sys.modules["data"] = MagicMock()
sys.modules["data.augmentation"] = MagicMock()
sys.modules["data.weak_supervision"] = MagicMock()

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from prepare_phase2_data import (
    VALID_IMAGE_EXTENSIONS,
    _convert_pdfs_from_directory,
    _load_images_from_directory,
    convert_pdf_to_images,
    print_dataset_summary,
)


class TestValidImageExtensions:
    """Tests for VALID_IMAGE_EXTENSIONS constant."""

    def test_extensions_defined(self) -> None:
        """Test that valid extensions are defined."""
        assert len(VALID_IMAGE_EXTENSIONS) >= 4

    def test_common_extensions_included(self) -> None:
        """Test common extensions are included."""
        assert ".png" in VALID_IMAGE_EXTENSIONS
        assert ".jpg" in VALID_IMAGE_EXTENSIONS
        assert ".jpeg" in VALID_IMAGE_EXTENSIONS
        assert ".tiff" in VALID_IMAGE_EXTENSIONS


class TestConvertPdfToImages:
    """Tests for convert_pdf_to_images function."""

    def test_returns_list(self, tmp_path: Path) -> None:
        """Test that function returns a list."""
        # Use a mock since we don't have real PDFs
        with patch("prepare_phase2_data.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__ = lambda self: 0
            mock_fitz.open.return_value = mock_doc

            result = convert_pdf_to_images(tmp_path / "test.pdf")

            assert isinstance(result, list)

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Test handling of missing file."""
        result = convert_pdf_to_images(tmp_path / "missing.pdf")

        assert result == []


class TestLoadImagesFromDirectory:
    """Tests for _load_images_from_directory function."""

    def test_loads_images(self, tmp_path: Path) -> None:
        """Test loading images from directory."""
        # Create test images
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        # Create a simple test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(images_dir / "test.png"), img)

        images, limit_reached = _load_images_from_directory(images_dir, None, 0)

        assert len(images) == 1
        assert limit_reached is False

    def test_respects_max_limit(self, tmp_path: Path) -> None:
        """Test that max images limit is respected."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()

        # Create multiple test images
        for i in range(5):
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.imwrite(str(images_dir / f"test{i}.png"), img)

        images, limit_reached = _load_images_from_directory(images_dir, 3, 0)

        assert len(images) <= 3
        assert limit_reached is True

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test loading from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        images, limit_reached = _load_images_from_directory(empty_dir, None, 0)

        assert images == []
        assert limit_reached is False


class TestConvertPdfsFromDirectory:
    """Tests for _convert_pdfs_from_directory function."""

    def test_returns_tuple(self, tmp_path: Path) -> None:
        """Test that function returns tuple."""
        result = _convert_pdfs_from_directory(tmp_path, None, 0)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test converting from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        images, limit_reached = _convert_pdfs_from_directory(empty_dir, None, 0)

        assert images == []
        assert limit_reached is False


class TestPrintDatasetSummary:
    """Tests for print_dataset_summary function."""

    def test_prints_summary(self, tmp_path: Path, capsys) -> None:
        """Test that summary is printed."""
        stats = {
            "train": {
                "num_samples": 100,
                "issue_counts": {"blur": 20, "noise": 15},
                "issue_frequencies": {"blur": 0.2, "noise": 0.15},
            }
        }

        print_dataset_summary(stats, tmp_path)

        captured = capsys.readouterr()
        assert "DATASET GENERATION COMPLETE" in captured.out
        assert "TRAIN SET" in captured.out

    def test_prints_total_samples(self, tmp_path: Path, capsys) -> None:
        """Test that total samples is printed."""
        stats = {
            "train": {"num_samples": 70, "issue_counts": {}, "issue_frequencies": {}},
            "val": {"num_samples": 15, "issue_counts": {}, "issue_frequencies": {}},
            "test": {"num_samples": 15, "issue_counts": {}, "issue_frequencies": {}},
        }

        print_dataset_summary(stats, tmp_path)

        captured = capsys.readouterr()
        assert "Total samples: 100" in captured.out


class TestCollectSourceImages:
    """Tests for collect_source_images function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from prepare_phase2_data import collect_source_images

        assert callable(collect_source_images)


class TestGenerateAugmentedDataset:
    """Tests for generate_augmented_dataset function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from prepare_phase2_data import generate_augmented_dataset

        assert callable(generate_augmented_dataset)


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from prepare_phase2_data import main

        assert callable(main)
