"""Tests for scripts/validate_pdf_classification.py - PDF classification validation.

These tests verify the PDF classification validation script correctly:
- Validates paths securely
- Loads ground truth labels
- Classifies PDFs
- Reports accuracy metrics
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Scripts directory added to sys.path via tests/conftest.py
from _path_security import validate_path
from validate_pdf_classification import (
    _find_expected_type,
    load_ground_truth,
    print_summary,
    validate_classifications,
)


class TestValidatePath:
    """Tests for validate_path function."""

    def test_validate_existing_path(self, tmp_path: Path) -> None:
        """Test validating an existing path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = validate_path(test_file, must_exist=True)

        assert result.exists()

    def test_validate_nonexistent_path_raises(self, tmp_path: Path) -> None:
        """Test that nonexistent path raises error when must_exist=True."""
        with pytest.raises(ValueError):
            validate_path(tmp_path / "nonexistent", must_exist=True)

    def test_validate_path_with_null_bytes_raises(self, tmp_path: Path) -> None:
        """Test that path with null bytes raises error."""
        # This is a security check - paths with null bytes are suspicious
        with pytest.raises(ValueError):
            validate_path(Path(str(tmp_path) + "\x00evil"), must_exist=False)


class TestLoadGroundTruth:
    """Tests for load_ground_truth function."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid ground truth JSON."""
        labels_file = tmp_path / "labels.json"
        labels_data = {
            "born_digital": ["doc1.pdf", "doc2.pdf"],
            "image_only": ["scan1.pdf"],
            "hybrid": ["report1.pdf"],
        }
        labels_file.write_text(json.dumps(labels_data))

        result = load_ground_truth(labels_file)

        assert "born_digital" in result
        assert len(result["born_digital"]) == 2
        assert "doc1.pdf" in result["born_digital"]

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that missing file raises error."""
        with pytest.raises(ValueError):
            load_ground_truth(tmp_path / "missing.json")


class TestFindExpectedType:
    """Tests for _find_expected_type function."""

    def test_find_born_digital(self) -> None:
        """Test finding born_digital type."""
        ground_truth = {
            "born_digital": ["doc1.pdf", "doc2.pdf"],
            "image_only": ["scan1.pdf"],
        }

        result = _find_expected_type("doc1.pdf", ground_truth)

        assert result == "born_digital"

    def test_find_image_only(self) -> None:
        """Test finding image_only type."""
        ground_truth = {
            "born_digital": ["doc1.pdf"],
            "image_only": ["scan1.pdf"],
        }

        result = _find_expected_type("scan1.pdf", ground_truth)

        assert result == "image_only"

    def test_not_found_returns_none(self) -> None:
        """Test that unknown file returns None."""
        ground_truth = {
            "born_digital": ["doc1.pdf"],
        }

        result = _find_expected_type("unknown.pdf", ground_truth)

        assert result is None


class TestValidateClassifications:
    """Tests for validate_classifications function."""

    @pytest.fixture
    def mock_pdf_dir(self, tmp_path: Path) -> Path:
        """Create mock PDF directory."""
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "doc1.pdf").write_bytes(b"%PDF-1.4 test")
        (pdf_dir / "doc2.pdf").write_bytes(b"%PDF-1.4 test2")
        return pdf_dir

    def test_empty_directory_returns_empty_results(self, tmp_path: Path) -> None:
        """Test validation with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = validate_classifications(empty_dir)

        assert result["total_pdfs"] == 0
        assert result["details"] == []

    def test_counts_pdfs(self, mock_pdf_dir: Path) -> None:
        """Test that PDFs are counted correctly."""
        with patch("validate_pdf_classification.classify_pdf_type") as mock_classify:
            mock_type = MagicMock()
            mock_type.value = "born_digital"
            mock_classify.return_value = mock_type

            result = validate_classifications(mock_pdf_dir)

            assert result["total_pdfs"] == 2

    def test_records_classifications(self, mock_pdf_dir: Path) -> None:
        """Test that classifications are recorded."""
        with patch("validate_pdf_classification.classify_pdf_type") as mock_classify:
            mock_type = MagicMock()
            mock_type.value = "born_digital"
            mock_classify.return_value = mock_type

            result = validate_classifications(mock_pdf_dir)

            assert result["classifications"]["born_digital"] == 2

    def test_tracks_correct_predictions(
        self, mock_pdf_dir: Path, tmp_path: Path
    ) -> None:
        """Test tracking of correct predictions."""
        labels_file = tmp_path / "labels.json"
        labels_data = {
            "born_digital": ["doc1.pdf", "doc2.pdf"],
        }
        labels_file.write_text(json.dumps(labels_data))

        with patch("validate_pdf_classification.classify_pdf_type") as mock_classify:
            mock_type = MagicMock()
            mock_type.value = "born_digital"
            mock_classify.return_value = mock_type

            result = validate_classifications(mock_pdf_dir, labels_file)

            assert result["correct"] == 2
            assert result["incorrect"] == 0

    def test_tracks_incorrect_predictions(
        self, mock_pdf_dir: Path, tmp_path: Path
    ) -> None:
        """Test tracking of incorrect predictions."""
        labels_file = tmp_path / "labels.json"
        labels_data = {
            "image_only": ["doc1.pdf", "doc2.pdf"],  # Expected image_only
        }
        labels_file.write_text(json.dumps(labels_data))

        with patch("validate_pdf_classification.classify_pdf_type") as mock_classify:
            mock_type = MagicMock()
            mock_type.value = "born_digital"  # But predicted born_digital
            mock_classify.return_value = mock_type

            result = validate_classifications(mock_pdf_dir, labels_file)

            assert result["incorrect"] == 2

    def test_handles_classification_errors(self, mock_pdf_dir: Path) -> None:
        """Test handling of classification errors."""
        with patch("validate_pdf_classification.classify_pdf_type") as mock_classify:
            mock_classify.side_effect = Exception("Classification failed")

            result = validate_classifications(mock_pdf_dir)

            assert len(result["errors"]) == 2


class TestPrintSummary:
    """Tests for print_summary function."""

    def test_print_basic_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test printing basic summary."""
        results = {
            "total_pdfs": 10,
            "classifications": {"born_digital": 5, "image_only": 3, "hybrid": 2},
            "correct": 0,
            "incorrect": 0,
            "errors": [],
        }

        print_summary(results)
        captured = capsys.readouterr()

        assert "Total PDFs processed: 10" in captured.out
        assert "born_digital" in captured.out

    def test_print_accuracy_when_available(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing accuracy when ground truth available."""
        results = {
            "total_pdfs": 10,
            "classifications": {"born_digital": 10},
            "correct": 9,
            "incorrect": 1,
            "errors": [],
        }

        print_summary(results)
        captured = capsys.readouterr()

        assert "Correct predictions" in captured.out
        assert "90.00%" in captured.out

    def test_print_errors_when_present(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test printing errors when present."""
        results = {
            "total_pdfs": 2,
            "classifications": {},
            "correct": 0,
            "incorrect": 0,
            "errors": ["Error 1", "Error 2"],
        }

        print_summary(results)
        captured = capsys.readouterr()

        assert "Errors encountered: 2" in captured.out


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from validate_pdf_classification import main

        assert callable(main)

    def test_main_invalid_directory_exits(self, tmp_path: Path) -> None:
        """Test that invalid directory causes exit."""
        from validate_pdf_classification import main

        with patch(
            "sys.argv", ["validate_pdf_classification.py", str(tmp_path / "invalid")]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
