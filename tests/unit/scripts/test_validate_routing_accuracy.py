# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/validate_routing_accuracy.py - Routing accuracy validation.

These tests verify the routing accuracy validation script correctly:
- Tracks validation results
- Calculates accuracy metrics
- Generates confusion matrix
- Handles test set loading
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_routing_accuracy import (
    RoutingValidationResult,
    load_test_set,
)


class TestRoutingValidationResult:
    """Tests for RoutingValidationResult class."""

    def test_init(self) -> None:
        """Test initialization."""
        result = RoutingValidationResult()

        assert result.total_documents == 0
        assert result.correct_predictions == 0
        assert result.predictions == []
        assert result.confusion_matrix == {}

    def test_add_correct_prediction(self) -> None:
        """Test adding a correct prediction."""
        result = RoutingValidationResult()

        # Mock OCRRoutingRecommendation
        mock_routing = MagicMock()
        mock_routing.value = "ocr_fast"

        result.add_prediction(
            document_id="doc-001",
            ground_truth=mock_routing,
            predicted=mock_routing,
            rationale="High quality document",
        )

        assert result.total_documents == 1
        assert result.correct_predictions == 1
        assert len(result.predictions) == 1
        assert result.predictions[0]["correct"] is True

    def test_add_incorrect_prediction(self) -> None:
        """Test adding an incorrect prediction."""
        result = RoutingValidationResult()

        mock_gt = MagicMock()
        mock_gt.value = "ocr_fast"

        mock_pred = MagicMock()
        mock_pred.value = "ocr_advanced"

        result.add_prediction(
            document_id="doc-002",
            ground_truth=mock_gt,
            predicted=mock_pred,
            rationale="Low quality document",
        )

        assert result.total_documents == 1
        assert result.correct_predictions == 0
        assert result.predictions[0]["correct"] is False

    def test_accuracy_calculation(self) -> None:
        """Test accuracy calculation."""
        result = RoutingValidationResult()

        mock_routing = MagicMock()
        mock_routing.value = "ocr_fast"

        # Add 3 correct predictions
        for i in range(3):
            result.add_prediction(
                document_id=f"doc-{i}",
                ground_truth=mock_routing,
                predicted=mock_routing,
                rationale="Test",
            )

        # Add 2 incorrect predictions
        mock_other = MagicMock()
        mock_other.value = "ocr_advanced"

        for i in range(3, 5):
            result.add_prediction(
                document_id=f"doc-{i}",
                ground_truth=mock_routing,
                predicted=mock_other,
                rationale="Test",
            )

        assert result.accuracy == 0.6  # 3/5

    def test_accuracy_zero_documents(self) -> None:
        """Test accuracy with zero documents."""
        result = RoutingValidationResult()

        assert result.accuracy == 0.0

    def test_confusion_matrix_updated(self) -> None:
        """Test confusion matrix is updated on predictions."""
        result = RoutingValidationResult()

        mock_gt = MagicMock()
        mock_gt.value = "ocr_fast"

        mock_pred = MagicMock()
        mock_pred.value = "ocr_advanced"

        result.add_prediction(
            document_id="doc-001",
            ground_truth=mock_gt,
            predicted=mock_pred,
            rationale="Test",
        )

        assert "ocr_fast" in result.confusion_matrix
        assert "ocr_advanced" in result.confusion_matrix["ocr_fast"]
        assert result.confusion_matrix["ocr_fast"]["ocr_advanced"] == 1

    def test_print_report(self, capsys) -> None:
        """Test print_report outputs to console."""
        result = RoutingValidationResult()

        mock_routing = MagicMock()
        mock_routing.value = "ocr_fast"

        result.add_prediction(
            document_id="doc-001",
            ground_truth=mock_routing,
            predicted=mock_routing,
            rationale="Test",
        )

        result.print_report()

        captured = capsys.readouterr()
        assert "ROUTING RECOMMENDATION ENGINE VALIDATION REPORT" in captured.out
        assert "Accuracy" in captured.out


class TestLoadTestSet:
    """Tests for load_test_set function."""

    def test_not_implemented(self, tmp_path: Path) -> None:
        """Test that load_test_set raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            load_test_set(tmp_path / "test_set.json")


class TestRunValidation:
    """Tests for run_validation function."""

    def test_function_exists(self) -> None:
        """Test that function exists."""
        from validate_routing_accuracy import run_validation

        assert callable(run_validation)


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from validate_routing_accuracy import main

        assert callable(main)

    def test_main_requires_test_set_path(self) -> None:
        """Test that main exits without test set path."""
        from validate_routing_accuracy import main

        with patch("sys.argv", ["validate_routing_accuracy.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_main_handles_missing_file(self, tmp_path: Path) -> None:
        """Test that main exits if test set file not found."""
        from validate_routing_accuracy import main

        missing_path = tmp_path / "nonexistent.json"

        with patch("sys.argv", ["validate_routing_accuracy.py", str(missing_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
