# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/extract_wili_samples.py - WiLI language sample extraction.

These tests verify the WiLI sample extraction correctly:
- Defines target languages
- Loads labels mapping
- Extracts language samples
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Scripts directory added to sys.path via tests/conftest.py
from extract_wili_samples import (
    LANGUAGE_CODE_MAP,
    TARGET_LANGUAGES,
    extract_language_samples,
    load_labels_mapping,
)


class TestTargetLanguages:
    """Tests for target language definitions."""

    def test_target_languages_count(self) -> None:
        """Test that 10 target languages are defined."""
        assert len(TARGET_LANGUAGES) == 10

    def test_target_languages_include_diverse_scripts(self) -> None:
        """Test that target languages include diverse scripts."""
        # Latin script
        assert "eng" in TARGET_LANGUAGES
        assert "fra" in TARGET_LANGUAGES
        assert "deu" in TARGET_LANGUAGES

        # Non-Latin scripts
        assert "zho" in TARGET_LANGUAGES  # Chinese
        assert "ara" in TARGET_LANGUAGES  # Arabic
        assert "jpn" in TARGET_LANGUAGES  # Japanese
        assert "kor" in TARGET_LANGUAGES  # Korean

    def test_language_names_correct(self) -> None:
        """Test that language names are correct."""
        assert TARGET_LANGUAGES["eng"] == "English"
        assert TARGET_LANGUAGES["fra"] == "French"
        assert TARGET_LANGUAGES["zho"] == "Chinese"


class TestLanguageCodeMap:
    """Tests for language code mapping."""

    def test_code_map_has_same_keys(self) -> None:
        """Test that code map has same keys as target languages."""
        assert set(LANGUAGE_CODE_MAP.keys()) == set(TARGET_LANGUAGES.keys())

    def test_code_map_values_are_valid(self) -> None:
        """Test that code map values are valid 3-letter codes."""
        for code in LANGUAGE_CODE_MAP.values():
            assert len(code) == 3
            assert code.isalpha()


class TestLoadLabelsMapping:
    """Tests for load_labels_mapping function."""

    def test_load_valid_labels(self, tmp_path: Path) -> None:
        """Test loading valid labels CSV."""
        labels_file = tmp_path / "labels.csv"
        labels_file.write_text("Label;English\neng;English\nfra;French\n")

        result = load_labels_mapping(labels_file)

        assert result["eng"] == "English"
        assert result["fra"] == "French"

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty labels file."""
        labels_file = tmp_path / "labels.csv"
        labels_file.write_text("Label;English\n")

        result = load_labels_mapping(labels_file)

        assert result == {}

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that missing file raises error."""
        with pytest.raises(FileNotFoundError):
            load_labels_mapping(tmp_path / "nonexistent.csv")


class TestExtractLanguageSamples:
    """Tests for extract_language_samples function."""

    @pytest.fixture
    def mock_wili_dataset(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """Create mock WiLI dataset files."""
        x_file = tmp_path / "x_test.txt"
        y_file = tmp_path / "y_test.txt"
        output_dir = tmp_path / "output"

        # Create sample data with different languages
        x_content = [
            "This is English text.",
            "Ceci est du texte français.",
            "Dies ist deutscher Text.",
            "Este es texto en español.",
            "这是中文文本。",
            "هذا نص عربي.",
            "Это русский текст.",
            "これは日本語のテキストです。",
            "이것은 한국어 텍스트입니다.",
            "यह हिंदी पाठ है।",
        ]
        y_content = [
            "eng",
            "fra",
            "deu",
            "spa",
            "zho",
            "ara",
            "rus",
            "jpn",
            "kor",
            "hin",
        ]

        x_file.write_text("\n".join(x_content) + "\n")
        y_file.write_text("\n".join(y_content) + "\n")

        return x_file, y_file, output_dir

    def test_extract_all_target_languages(
        self, mock_wili_dataset: tuple[Path, Path, Path]
    ) -> None:
        """Test extracting all target languages."""
        x_file, y_file, output_dir = mock_wili_dataset

        result = extract_language_samples(
            x_file, y_file, output_dir, LANGUAGE_CODE_MAP, max_samples_per_lang=1
        )

        assert result["extracted"] == 10
        assert result["missing"] == []

    def test_extract_creates_output_files(
        self, mock_wili_dataset: tuple[Path, Path, Path]
    ) -> None:
        """Test that extraction creates output files."""
        x_file, y_file, output_dir = mock_wili_dataset

        extract_language_samples(
            x_file, y_file, output_dir, LANGUAGE_CODE_MAP, max_samples_per_lang=1
        )

        assert output_dir.exists()
        output_files = list(output_dir.glob("*.txt"))
        assert len(output_files) == 10

    def test_extract_file_naming(
        self, mock_wili_dataset: tuple[Path, Path, Path]
    ) -> None:
        """Test that output files are named correctly."""
        x_file, y_file, output_dir = mock_wili_dataset

        extract_language_samples(
            x_file, y_file, output_dir, {"eng": "English"}, max_samples_per_lang=1
        )

        # Should create english_eng.txt
        english_file = output_dir / "english_eng.txt"
        assert english_file.exists()

    def test_extract_file_content(
        self, mock_wili_dataset: tuple[Path, Path, Path]
    ) -> None:
        """Test that extracted files contain correct content."""
        x_file, y_file, output_dir = mock_wili_dataset

        extract_language_samples(
            x_file, y_file, output_dir, {"eng": "English"}, max_samples_per_lang=1
        )

        english_file = output_dir / "english_eng.txt"
        content = english_file.read_text()
        assert "This is English text." in content

    def test_extract_respects_max_samples(
        self, mock_wili_dataset: tuple[Path, Path, Path]
    ) -> None:
        """Test that extraction respects max_samples_per_lang."""
        x_file, y_file, output_dir = mock_wili_dataset

        # Add more English samples
        x_content = x_file.read_text().strip() + "\nAnother English sentence.\n"
        y_content = y_file.read_text().strip() + "\neng\n"
        x_file.write_text(x_content)
        y_file.write_text(y_content)

        result = extract_language_samples(
            x_file, y_file, output_dir, {"eng": "English"}, max_samples_per_lang=1
        )

        assert result["extracted"] == 1  # Only 1 sample extracted

    def test_extract_returns_correct_structure(
        self, mock_wili_dataset: tuple[Path, Path, Path]
    ) -> None:
        """Test that result has correct structure."""
        x_file, y_file, output_dir = mock_wili_dataset

        result = extract_language_samples(
            x_file, y_file, output_dir, {"eng": "English"}, max_samples_per_lang=1
        )

        assert "extracted" in result
        assert "samples" in result
        assert "missing" in result
        assert "eng" in result["samples"]
        assert "name" in result["samples"]["eng"]
        assert "file" in result["samples"]["eng"]
        assert "length" in result["samples"]["eng"]

    def test_extract_missing_languages_reported(self, tmp_path: Path) -> None:
        """Test that missing languages are reported."""
        x_file = tmp_path / "x_test.txt"
        y_file = tmp_path / "y_test.txt"
        output_dir = tmp_path / "output"

        # Create data with only English
        x_file.write_text("This is English text.\n")
        y_file.write_text("eng\n")

        result = extract_language_samples(
            x_file,
            y_file,
            output_dir,
            {"eng": "English", "fra": "French"},
            max_samples_per_lang=1,
        )

        assert result["extracted"] == 1
        assert len(result["missing"]) == 1
        assert "fra (French)" in result["missing"]

    def test_extract_empty_files(self, tmp_path: Path) -> None:
        """Test handling of empty input files."""
        x_file = tmp_path / "x_test.txt"
        y_file = tmp_path / "y_test.txt"
        output_dir = tmp_path / "output"

        x_file.write_text("")
        y_file.write_text("")

        result = extract_language_samples(
            x_file, y_file, output_dir, {"eng": "English"}, max_samples_per_lang=1
        )

        assert result["extracted"] == 0
        assert "eng (English)" in result["missing"]

    def test_extract_creates_output_directory(self, tmp_path: Path) -> None:
        """Test that output directory is created if it doesn't exist."""
        x_file = tmp_path / "x_test.txt"
        y_file = tmp_path / "y_test.txt"
        output_dir = tmp_path / "nested" / "output"

        x_file.write_text("Test\n")
        y_file.write_text("eng\n")

        extract_language_samples(
            x_file, y_file, output_dir, {"eng": "English"}, max_samples_per_lang=1
        )

        assert output_dir.exists()
