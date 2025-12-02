# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/visualize_risk_distribution.py - Risk distribution visualization.

These tests verify the risk distribution visualization script correctly:
- Collects risk scores
- Calculates statistics
- Plots distributions
- Saves statistics to JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from visualize_risk_distribution import (
    calculate_statistics,
    save_statistics,
)


class TestCalculateStatistics:
    """Tests for calculate_statistics function."""

    def test_basic_statistics(self) -> None:
        """Test basic statistics calculation."""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]

        result = calculate_statistics(scores)

        assert result["mean"] == 3.0
        assert result["median"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0

    def test_empty_scores(self) -> None:
        """Test statistics for empty scores list."""
        result = calculate_statistics([])

        assert result["mean"] == 0.0
        assert result["median"] == 0.0
        assert result["std"] == 0.0
        assert result["min"] == 0.0
        assert result["max"] == 0.0

    def test_single_value(self) -> None:
        """Test statistics for single value."""
        scores = [0.5]

        result = calculate_statistics(scores)

        assert result["mean"] == 0.5
        assert result["median"] == 0.5
        assert result["std"] == 0.0

    def test_quartiles(self) -> None:
        """Test quartile calculations."""
        scores = list(range(1, 101))  # 1 to 100

        result = calculate_statistics(scores)

        assert result["q25"] == 25.75
        assert result["q75"] == 75.25

    def test_std_calculation(self) -> None:
        """Test standard deviation calculation."""
        scores = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]

        result = calculate_statistics(scores)

        assert abs(result["std"] - np.std(scores)) < 0.001


class TestSaveStatistics:
    """Tests for save_statistics function."""

    def test_saves_json_file(self, tmp_path: Path) -> None:
        """Test that statistics are saved to JSON file."""
        data = {
            "risk_scores": [0.1, 0.2, 0.3],
            "degradation_scores": [0.8, 0.9, 0.7],
            "complexity_scores": [0.2, 0.3, 0.1],
            "pdf_types": ["born_digital", "born_digital", "hybrid"],
            "doc_ids": ["doc1", "doc2", "doc3"],
        }

        output_path = tmp_path / "stats.json"
        save_statistics(data, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            saved = json.load(f)

        assert "pre_ocr_risk" in saved
        assert "degradation_score" in saved
        assert "structural_complexity" in saved
        assert "pdf_type_distribution" in saved
        assert "total_documents" in saved

    def test_pdf_type_distribution(self, tmp_path: Path) -> None:
        """Test PDF type distribution is calculated correctly."""
        data = {
            "risk_scores": [0.1, 0.2, 0.3, 0.4],
            "degradation_scores": [0.8, 0.9, 0.7, 0.6],
            "complexity_scores": [0.2, 0.3, 0.1, 0.2],
            "pdf_types": ["born_digital", "born_digital", "hybrid", "image_only"],
            "doc_ids": ["doc1", "doc2", "doc3", "doc4"],
        }

        output_path = tmp_path / "stats.json"
        save_statistics(data, output_path)

        with open(output_path) as f:
            saved = json.load(f)

        assert saved["pdf_type_distribution"]["born_digital"] == 2
        assert saved["pdf_type_distribution"]["hybrid"] == 1
        assert saved["pdf_type_distribution"]["image_only"] == 1

    def test_total_documents_count(self, tmp_path: Path) -> None:
        """Test total documents count is correct."""
        data = {
            "risk_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
            "degradation_scores": [0.8] * 5,
            "complexity_scores": [0.2] * 5,
            "pdf_types": ["born_digital"] * 5,
            "doc_ids": ["doc1", "doc2", "doc3", "doc4", "doc5"],
        }

        output_path = tmp_path / "stats.json"
        save_statistics(data, output_path)

        with open(output_path) as f:
            saved = json.load(f)

        assert saved["total_documents"] == 5


class TestCollectRiskScores:
    """Tests for collect_risk_scores function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from visualize_risk_distribution import collect_risk_scores

        assert callable(collect_risk_scores)

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        """Test that empty directory returns empty results."""
        from visualize_risk_distribution import collect_risk_scores

        result = collect_risk_scores(tmp_path, max_documents=10)

        assert result["risk_scores"] == []
        assert result["degradation_scores"] == []


class TestPlotRiskDistribution:
    """Tests for plot_risk_distribution function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from visualize_risk_distribution import plot_risk_distribution

        assert callable(plot_risk_distribution)


class TestPlotDqsDistribution:
    """Tests for plot_dqs_distribution function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from visualize_risk_distribution import plot_dqs_distribution

        assert callable(plot_dqs_distribution)


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from visualize_risk_distribution import main

        assert callable(main)

    def test_main_exits_without_input_dir(self) -> None:
        """Test that main exits if input dir doesn't exist."""
        from visualize_risk_distribution import main

        with patch(
            "sys.argv",
            ["visualize_risk_distribution.py", "--input-dir", "/nonexistent/path"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
