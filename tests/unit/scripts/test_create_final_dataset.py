"""Tests for scripts/create_final_dataset.py - Training dataset creation.

These tests verify the dataset creation script correctly:
- Merges weak supervision labels with manual corrections
- Creates train/val/test splits with proper ratios
- Validates dataset integrity (no overlaps)
- Calculates label distributions
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Scripts directory added to sys.path via tests/conftest.py
from create_final_dataset import (
    QUALITY_ISSUES,
    calculate_label_distribution,
    merge_labels,
    split_dataset,
    verify_dataset_integrity,
)


class TestQualityIssuesConfig:
    """Tests for the QUALITY_ISSUES configuration."""

    def test_quality_issues_contains_expected(self) -> None:
        """Test that QUALITY_ISSUES contains expected issue types."""
        expected = [
            "noise",
            "blur",
            "skew",
            "perspective",
            "low_contrast",
            "orientation",
        ]

        for issue in expected:
            assert issue in QUALITY_ISSUES, f"Missing quality issue: {issue}"

    def test_quality_issues_no_duplicates(self) -> None:
        """Test that QUALITY_ISSUES has no duplicates."""
        assert len(QUALITY_ISSUES) == len(set(QUALITY_ISSUES))


class TestMergeLabels:
    """Tests for the merge_labels function."""

    @pytest.fixture
    def weak_supervision_dir(self, tmp_path: Path) -> Path:
        """Create a temporary weak supervision labels directory."""
        ws_dir = tmp_path / "weak_supervision_labels"
        ws_dir.mkdir()
        return ws_dir

    @pytest.fixture
    def corrected_labels_dir(self, tmp_path: Path) -> Path:
        """Create a temporary corrected labels directory."""
        corrected_dir = tmp_path / "corrected_labels"
        corrected_dir.mkdir()
        return corrected_dir

    def test_merge_weak_supervision_only(
        self, tmp_path: Path, weak_supervision_dir: Path, corrected_labels_dir: Path
    ) -> None:
        """Test merging when only weak supervision labels exist."""
        # Create weak supervision labels
        ws_labels = {
            "image_path": str(tmp_path / "image1.jpg"),
            "labels": {
                "blur": {"value": 1, "confidence": 0.8},
                "noise": {"value": 0, "confidence": 0.9},
            },
            "quality_scores": {"overall": 0.7},
        }
        (weak_supervision_dir / "image1_labels.json").write_text(json.dumps(ws_labels))

        # Create the image file so integrity check passes
        (tmp_path / "image1.jpg").write_text("fake image")

        with patch("rich.console.Console.print"):
            with patch("rich.progress.track", lambda x, **kwargs: x):
                merged = merge_labels(weak_supervision_dir, corrected_labels_dir)

        assert len(merged) == 1
        assert merged[0]["label_source"] == "weak_supervision"

    def test_merge_corrected_takes_precedence(
        self, tmp_path: Path, weak_supervision_dir: Path, corrected_labels_dir: Path
    ) -> None:
        """Test that corrected labels take precedence over weak supervision."""
        # Create weak supervision labels
        ws_labels = {
            "image_path": str(tmp_path / "image1.jpg"),
            "labels": {
                "blur": {"value": 1, "confidence": 0.8},
            },
        }
        (weak_supervision_dir / "image1_labels.json").write_text(json.dumps(ws_labels))

        # Create corrected labels (overriding blur)
        # NOTE: Corrected files use pattern *_corrected.json
        # The stem replacement "_corrected" -> "_labels" maps to the WS file stem
        corrected = {
            "image_path": str(tmp_path / "image1.jpg"),
            "corrected_labels": {"blur": 0, "noise": 1},  # Changed blur to 0
            "quality_scores": {"overall": 0.9},
            "annotator_notes": "Blur was false positive",
        }
        (corrected_labels_dir / "image1_corrected.json").write_text(
            json.dumps(corrected)
        )

        # Create the image file
        (tmp_path / "image1.jpg").write_text("fake image")

        with patch("rich.console.Console.print"):
            with patch("rich.progress.track", lambda x, **kwargs: x):
                merged = merge_labels(weak_supervision_dir, corrected_labels_dir)

        assert len(merged) == 1
        assert merged[0]["label_source"] == "manual_correction"
        assert merged[0]["corrected_labels"]["blur"] == 0

    def test_merge_handles_empty_directories(
        self, tmp_path: Path, weak_supervision_dir: Path, corrected_labels_dir: Path
    ) -> None:
        """Test merging with empty directories."""
        with patch("rich.console.Console.print"):
            with patch("rich.progress.track", lambda x, **kwargs: x):
                merged = merge_labels(weak_supervision_dir, corrected_labels_dir)

        assert len(merged) == 0


class TestSplitDataset:
    """Tests for the split_dataset function."""

    @pytest.fixture
    def sample_labels(self) -> list[dict[str, Any]]:
        """Create sample label data for splitting."""
        return [
            {
                "image_path": f"/path/to/image{i}.jpg",
                "label_path": f"/path/to/label{i}.json",
                "label_source": "weak_supervision",
                "corrected_labels": {
                    "blur": i % 2,
                    "noise": (i + 1) % 2,
                },
            }
            for i in range(100)
        ]

    def test_split_default_ratios(self, sample_labels: list[dict]) -> None:
        """Test splitting with default 80/10/10 ratios."""
        with patch("rich.console.Console.print"):
            train, val, test = split_dataset(sample_labels)

        assert len(train) == 80
        assert len(val) == 10
        assert len(test) == 10

    def test_split_custom_ratios(self, sample_labels: list[dict]) -> None:
        """Test splitting with custom ratios."""
        with patch("rich.console.Console.print"):
            train, val, test = split_dataset(
                sample_labels,
                train_ratio=0.7,
                val_ratio=0.15,
                test_ratio=0.15,
            )

        assert len(train) == 70
        assert len(val) == 15
        assert len(test) == 15

    def test_split_invalid_ratios_raises(self, sample_labels: list[dict]) -> None:
        """Test that invalid ratios raise ValueError."""
        with pytest.raises(ValueError, match=r"sum to 1\.0"):
            split_dataset(
                sample_labels,
                train_ratio=0.5,
                val_ratio=0.3,
                test_ratio=0.3,  # ratios sum to 1.1, exceeding 1.0
            )

    def test_split_reproducibility(self, sample_labels: list[dict]) -> None:
        """Test that same seed produces same split."""
        with patch("rich.console.Console.print"):
            train1, val1, test1 = split_dataset(sample_labels, random_seed=42)
            train2, val2, test2 = split_dataset(sample_labels, random_seed=42)

        assert train1 == train2
        assert val1 == val2
        assert test1 == test2

    def test_split_different_seeds_different_results(
        self, sample_labels: list[dict]
    ) -> None:
        """Test that different seeds produce different splits."""
        with patch("rich.console.Console.print"):
            train1, _, _ = split_dataset(sample_labels, random_seed=42)
            train2, _, _ = split_dataset(sample_labels, random_seed=123)

        assert train1 != train2


class TestVerifyDatasetIntegrity:
    """Tests for the verify_dataset_integrity function."""

    def test_valid_non_overlapping_splits(self, tmp_path: Path) -> None:
        """Test verification passes for non-overlapping splits."""
        # Create sample files
        for i in range(10):
            (tmp_path / f"image{i}.jpg").write_text("fake")
            (tmp_path / f"label{i}.json").write_text("{}")

        train = [
            {
                "image_path": str(tmp_path / f"image{i}.jpg"),
                "label_path": str(tmp_path / f"label{i}.json"),
            }
            for i in range(6)
        ]
        val = [
            {
                "image_path": str(tmp_path / f"image{i}.jpg"),
                "label_path": str(tmp_path / f"label{i}.json"),
            }
            for i in range(6, 8)
        ]
        test = [
            {
                "image_path": str(tmp_path / f"image{i}.jpg"),
                "label_path": str(tmp_path / f"label{i}.json"),
            }
            for i in range(8, 10)
        ]

        with patch("rich.console.Console.print"):
            result = verify_dataset_integrity(train, val, test)

        assert result is True

    def test_overlapping_train_val_fails(self, tmp_path: Path) -> None:
        """Test verification fails for overlapping train and val."""
        # Create files
        (tmp_path / "image0.jpg").write_text("fake")
        (tmp_path / "label0.json").write_text("{}")

        # Same image in both train and val
        train = [
            {
                "image_path": str(tmp_path / "image0.jpg"),
                "label_path": str(tmp_path / "label0.json"),
            }
        ]
        val = [
            {
                "image_path": str(tmp_path / "image0.jpg"),
                "label_path": str(tmp_path / "label0.json"),
            }
        ]
        test: list[dict] = []

        with patch("rich.console.Console.print"):
            result = verify_dataset_integrity(train, val, test)

        assert result is False

    def test_missing_image_fails(self, tmp_path: Path) -> None:
        """Test verification fails for missing image files."""
        train = [
            {
                "image_path": str(tmp_path / "nonexistent.jpg"),
                "label_path": str(tmp_path / "label.json"),
            }
        ]
        val: list[dict] = []
        test: list[dict] = []

        with patch("rich.console.Console.print"):
            result = verify_dataset_integrity(train, val, test)

        assert result is False


class TestCalculateLabelDistribution:
    """Tests for the calculate_label_distribution function."""

    def test_distribution_structure(self) -> None:
        """Test that distribution has expected structure."""
        samples = [
            {"corrected_labels": {"blur": 1, "noise": 0}},
            {"corrected_labels": {"blur": 0, "noise": 1}},
        ]

        stats = calculate_label_distribution(samples)

        assert "total_samples" in stats
        assert "label_counts" in stats
        assert "label_percentages" in stats
        assert "average_issues_per_image" in stats

    def test_distribution_counts(self) -> None:
        """Test label counting accuracy."""
        samples = [
            {"corrected_labels": {"blur": 1, "noise": 0, "skew": 1}},
            {"corrected_labels": {"blur": 1, "noise": 1, "skew": 0}},
            {"corrected_labels": {"blur": 0, "noise": 0, "skew": 0}},
        ]

        stats = calculate_label_distribution(samples)

        assert stats["total_samples"] == 3
        assert stats["label_counts"]["blur"] == 2
        assert stats["label_counts"]["noise"] == 1
        assert stats["label_counts"]["skew"] == 1

    def test_distribution_percentages(self) -> None:
        """Test percentage calculation accuracy."""
        samples = [
            {"corrected_labels": {"blur": 1}},
            {"corrected_labels": {"blur": 0}},
        ]

        stats = calculate_label_distribution(samples)

        assert stats["label_percentages"]["blur"] == pytest.approx(50.0)

    def test_distribution_empty_samples(self) -> None:
        """Test distribution with empty samples."""
        stats = calculate_label_distribution([])

        assert stats["total_samples"] == 0
        assert stats["average_issues_per_image"] == 0

    def test_average_issues_per_image(self) -> None:
        """Test average issues calculation."""
        # Each sample has 2 issues
        samples = [
            {"corrected_labels": {"blur": 1, "noise": 1, "skew": 0}},
            {"corrected_labels": {"blur": 1, "noise": 1, "skew": 0}},
        ]

        stats = calculate_label_distribution(samples)

        assert stats["average_issues_per_image"] == pytest.approx(2.0)
