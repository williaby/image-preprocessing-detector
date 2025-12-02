# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/validate_layout_lite.py - Layout-lite validation.

These tests verify the layout-lite validation script correctly:
- Loads ground truth labels
- Analyzes layout-lite attributes
- Calculates presence flag metrics
- Validates layout-lite accuracy
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_layout_lite import (
    FLAG_NAMES,
    _calculate_flag_results,
    _collect_page_flags,
    calculate_presence_flag_metrics,
    load_ground_truth,
)


class TestFlagNames:
    """Tests for flag name constants."""

    def test_flag_names_count(self) -> None:
        """Test that 7 flag names are defined."""
        assert len(FLAG_NAMES) == 7

    def test_flag_names_content(self) -> None:
        """Test flag names include expected values."""
        assert "has_tables" in FLAG_NAMES
        assert "has_figures" in FLAG_NAMES
        assert "has_dense_math" in FLAG_NAMES
        assert "has_handwriting" in FLAG_NAMES
        assert "fuzzy_scan" in FLAG_NAMES
        assert "watermark" in FLAG_NAMES
        assert "colorful_background" in FLAG_NAMES


class TestLoadGroundTruth:
    """Tests for load_ground_truth function."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid ground truth JSON."""
        labels_file = tmp_path / "layout_labels.json"
        labels_data = {
            "document_001.pdf": {
                "page_1": {
                    "has_tables": True,
                    "has_figures": False,
                }
            }
        }
        labels_file.write_text(json.dumps(labels_data))

        result = load_ground_truth(labels_file)

        assert "document_001.pdf" in result
        assert result["document_001.pdf"]["page_1"]["has_tables"] is True

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that missing file raises error."""
        with pytest.raises(FileNotFoundError):
            load_ground_truth(tmp_path / "missing.json")


class TestCalculatePresenceFlagMetrics:
    """Tests for calculate_presence_flag_metrics function."""

    def test_perfect_predictions(self) -> None:
        """Test metrics for perfect predictions."""
        y_true = [True, True, False, False, True]
        y_pred = [True, True, False, False, True]

        result = calculate_presence_flag_metrics(y_true, y_pred, "test_flag")

        assert result["f1"] == 1.0
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0

    def test_all_wrong_predictions(self) -> None:
        """Test metrics for all wrong predictions."""
        y_true = [True, True, True]
        y_pred = [False, False, False]

        result = calculate_presence_flag_metrics(y_true, y_pred, "test_flag")

        assert result["f1"] == 0.0
        assert result["recall"] == 0.0

    def test_empty_samples(self) -> None:
        """Test metrics for empty sample list."""
        result = calculate_presence_flag_metrics([], [], "test_flag")

        assert result["f1"] == 0.0
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0

    def test_all_same_label(self) -> None:
        """Test metrics when all samples have same label."""
        y_true = [True, True, True]
        y_pred = [True, True, True]

        result = calculate_presence_flag_metrics(y_true, y_pred, "test_flag")

        # All predictions match, so perfect score
        assert result["f1"] == 1.0

    def test_partial_correct(self) -> None:
        """Test metrics for partially correct predictions."""
        y_true = [True, True, False, False]
        y_pred = [True, False, False, False]

        result = calculate_presence_flag_metrics(y_true, y_pred, "test_flag")

        assert 0 < result["f1"] < 1.0


class TestCollectPageFlags:
    """Tests for _collect_page_flags function."""

    def test_collect_flags(self) -> None:
        """Test collecting flags from page data."""
        page_labels = {
            "has_tables": True,
            "has_figures": False,
            "fuzzy_scan": True,
        }
        page_preds = {
            "has_tables": True,
            "has_figures": True,
            "fuzzy_scan": False,
        }
        flag_data = {flag: {"y_true": [], "y_pred": []} for flag in FLAG_NAMES}

        _collect_page_flags(page_labels, page_preds, flag_data)

        assert flag_data["has_tables"]["y_true"] == [True]
        assert flag_data["has_tables"]["y_pred"] == [True]
        assert flag_data["has_figures"]["y_true"] == [False]
        assert flag_data["has_figures"]["y_pred"] == [True]
        assert flag_data["fuzzy_scan"]["y_true"] == [True]
        assert flag_data["fuzzy_scan"]["y_pred"] == [False]

    def test_collect_missing_flags_default_false(self) -> None:
        """Test that missing flags default to False."""
        page_labels = {"has_tables": True}
        page_preds = {}
        flag_data = {flag: {"y_true": [], "y_pred": []} for flag in FLAG_NAMES}

        _collect_page_flags(page_labels, page_preds, flag_data)

        # Missing flags should default to False
        assert flag_data["has_figures"]["y_true"] == [False]
        assert flag_data["has_figures"]["y_pred"] == [False]


class TestCalculateFlagResults:
    """Tests for _calculate_flag_results function."""

    def test_calculate_all_flags(self) -> None:
        """Test calculating results for all flags."""
        flag_data = {
            flag: {
                "y_true": [True, False, True],
                "y_pred": [True, False, True],
            }
            for flag in FLAG_NAMES
        }

        result = _calculate_flag_results(flag_data)

        assert len(result) == len(FLAG_NAMES)
        for flag_name in FLAG_NAMES:
            assert flag_name in result
            assert "f1" in result[flag_name]
            assert "precision" in result[flag_name]
            assert "recall" in result[flag_name]
            assert "target_met" in result[flag_name]
            assert "num_samples" in result[flag_name]
            assert "num_positive" in result[flag_name]

    def test_target_met_threshold(self) -> None:
        """Test that target_met uses 0.85 threshold."""
        # Perfect predictions - should meet target
        flag_data = {
            flag: {
                "y_true": [True, False, True],
                "y_pred": [True, False, True],
            }
            for flag in FLAG_NAMES
        }

        result = _calculate_flag_results(flag_data)

        # All perfect predictions should meet 0.85 target
        for flag_name in FLAG_NAMES:
            assert result[flag_name]["target_met"] is True


class TestValidateLayoutLite:
    """Tests for validate_layout_lite function integration."""

    @pytest.fixture
    def mock_test_data(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create mock test data directory and labels file."""
        test_dir = tmp_path / "test_pdfs"
        test_dir.mkdir()

        labels_file = tmp_path / "layout_labels.json"
        labels_data = {
            "doc1.pdf": {
                "page_1": {
                    "has_tables": True,
                    "has_figures": False,
                    "has_dense_math": False,
                    "has_handwriting": False,
                    "fuzzy_scan": False,
                    "watermark": False,
                    "colorful_background": False,
                }
            }
        }
        labels_file.write_text(json.dumps(labels_data))

        return test_dir, labels_file

    def test_missing_labels_file_returns_results(
        self, mock_test_data: tuple[Path, Path]
    ) -> None:
        """Test that validation handles missing labels gracefully."""
        from validate_layout_lite import validate_layout_lite

        test_dir, _ = mock_test_data

        with pytest.raises(FileNotFoundError):
            validate_layout_lite(test_dir, test_dir / "nonexistent.json")

    def test_saves_output_file(
        self, mock_test_data: tuple[Path, Path], tmp_path: Path
    ) -> None:
        """Test that results are saved to output file."""
        from validate_layout_lite import validate_layout_lite

        test_dir, labels_file = mock_test_data
        output_file = tmp_path / "results.json"

        with patch("validate_layout_lite.LayoutLiteAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = {}
            mock_analyzer_class.return_value = mock_analyzer

            with patch("validate_layout_lite.load_pdf") as mock_load:
                mock_load.return_value = []

                validate_layout_lite(test_dir, labels_file, output_file)

        # Output file should be created
        assert output_file.exists()


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from validate_layout_lite import main

        assert callable(main)

    def test_main_missing_labels_returns_1(self, tmp_path: Path) -> None:
        """Test that missing labels file causes exit code 1."""
        from validate_layout_lite import main

        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("sys.argv", ["validate_layout_lite.py", str(test_dir)]):
            result = main()

            assert result == 1
