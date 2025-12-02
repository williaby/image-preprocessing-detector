# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/extract_test_fixtures.py - Test fixture extraction.

These tests verify the test fixture extraction correctly:
- Calculates file sizes
- Finds files by extension
- Samples diverse files by size
- Extracts fixtures for datasets
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from extract_test_fixtures import (
    DATASET_CONFIGS,
    MAX_TOTAL_SIZE_MB,
    MB_TO_BYTES,
    _fill_remaining_samples,
    _filter_files_by_size,
    _sample_from_quartiles,
    extract_all_fixtures,
    extract_fixtures_for_dataset,
    find_files_by_extension,
    get_file_size_mb,
    sample_diverse_files,
)


class TestConstants:
    """Tests for module constants."""

    def test_max_total_size(self) -> None:
        """Test maximum total size is reasonable."""
        assert MAX_TOTAL_SIZE_MB == 50

    def test_mb_to_bytes(self) -> None:
        """Test MB conversion constant."""
        assert MB_TO_BYTES == 1024 * 1024

    def test_dataset_configs_exist(self) -> None:
        """Test that dataset configs are defined."""
        assert len(DATASET_CONFIGS) >= 5
        assert "doclaynet" in DATASET_CONFIGS
        assert "tablebank" in DATASET_CONFIGS


class TestDatasetConfigs:
    """Tests for dataset configuration structure."""

    def test_doclaynet_config(self) -> None:
        """Test DocLayNet configuration."""
        config = DATASET_CONFIGS["doclaynet"]
        assert "source_dir" in config
        assert "target_dir" in config
        assert "extensions" in config
        assert ".pdf" in config["extensions"]
        assert config["count"] == 5
        assert config["max_size_mb"] == 10

    def test_tablebank_config(self) -> None:
        """Test TableBank configuration."""
        config = DATASET_CONFIGS["tablebank"]
        assert ".jpg" in config["extensions"] or ".png" in config["extensions"]
        assert config["count"] == 5

    def test_all_configs_have_required_fields(self) -> None:
        """Test all configs have required fields."""
        required_fields = [
            "source_dir",
            "target_dir",
            "extensions",
            "count",
            "max_size_mb",
            "criteria",
        ]
        for name, config in DATASET_CONFIGS.items():
            for field in required_fields:
                assert field in config, f"{name} missing {field}"


class TestGetFileSizeMb:
    """Tests for get_file_size_mb function."""

    def test_size_small_file(self, tmp_path: Path) -> None:
        """Test size calculation for small file."""
        test_file = tmp_path / "small.txt"
        test_file.write_bytes(b"x" * 1024)  # 1 KB

        size = get_file_size_mb(test_file)

        assert size == pytest.approx(1024 / MB_TO_BYTES, rel=0.01)

    def test_size_1mb_file(self, tmp_path: Path) -> None:
        """Test size calculation for 1 MB file."""
        test_file = tmp_path / "onemb.bin"
        test_file.write_bytes(b"x" * MB_TO_BYTES)

        size = get_file_size_mb(test_file)

        assert size == pytest.approx(1.0, rel=0.01)

    def test_size_empty_file(self, tmp_path: Path) -> None:
        """Test size calculation for empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        size = get_file_size_mb(test_file)

        assert size == pytest.approx(0.0)


class TestFindFilesByExtension:
    """Tests for find_files_by_extension function."""

    def test_find_single_extension(self, tmp_path: Path) -> None:
        """Test finding files with single extension."""
        (tmp_path / "file1.pdf").write_text("pdf1")
        (tmp_path / "file2.pdf").write_text("pdf2")
        (tmp_path / "file3.txt").write_text("txt")

        files = find_files_by_extension(tmp_path, [".pdf"])

        assert len(files) == 2
        assert all(f.suffix == ".pdf" for f in files)

    def test_find_multiple_extensions(self, tmp_path: Path) -> None:
        """Test finding files with multiple extensions."""
        (tmp_path / "file1.jpg").write_text("jpg")
        (tmp_path / "file2.png").write_text("png")
        (tmp_path / "file3.txt").write_text("txt")

        files = find_files_by_extension(tmp_path, [".jpg", ".png"])

        assert len(files) == 2

    def test_find_recursive(self, tmp_path: Path) -> None:
        """Test finding files recursively."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.pdf").write_text("pdf1")
        (subdir / "file2.pdf").write_text("pdf2")

        files = find_files_by_extension(tmp_path, [".pdf"])

        assert len(files) == 2

    def test_find_no_matches(self, tmp_path: Path) -> None:
        """Test finding no matching files."""
        (tmp_path / "file.txt").write_text("txt")

        files = find_files_by_extension(tmp_path, [".pdf"])

        assert len(files) == 0

    def test_find_empty_directory(self, tmp_path: Path) -> None:
        """Test finding files in empty directory."""
        files = find_files_by_extension(tmp_path, [".pdf"])

        assert len(files) == 0


class TestFilterFilesBySize:
    """Tests for _filter_files_by_size function."""

    def test_filter_within_limit(self, tmp_path: Path) -> None:
        """Test filtering files within size limit."""
        small = tmp_path / "small.txt"
        small.write_bytes(b"x" * 100)
        large = tmp_path / "large.txt"
        large.write_bytes(b"x" * (2 * MB_TO_BYTES))

        files = [small, large]
        result = _filter_files_by_size(files, max_individual_size_mb=1.0)

        assert len(result) == 1
        assert result[0][0] == small

    def test_filter_sorted_by_size(self, tmp_path: Path) -> None:
        """Test that filtered files are sorted by size."""
        medium = tmp_path / "medium.txt"
        medium.write_bytes(b"x" * 500)
        small = tmp_path / "small.txt"
        small.write_bytes(b"x" * 100)
        large = tmp_path / "large.txt"
        large.write_bytes(b"x" * 1000)

        files = [medium, small, large]
        result = _filter_files_by_size(files, max_individual_size_mb=1.0)

        # Should be sorted by size ascending
        sizes = [s for _, s in result]
        assert sizes == sorted(sizes)


class TestSampleFromQuartiles:
    """Tests for _sample_from_quartiles function."""

    def test_sample_from_quartiles(self, tmp_path: Path) -> None:
        """Test sampling from different size quartiles."""
        # Create files of different sizes
        files_with_size = []
        for i in range(20):
            f = tmp_path / f"file{i}.txt"
            f.write_bytes(b"x" * ((i + 1) * 100))
            files_with_size.append((f, (i + 1) * 100 / MB_TO_BYTES))

        sampled, total_size = _sample_from_quartiles(
            files_with_size, count=4, max_size_mb=1.0
        )

        assert len(sampled) <= 4
        assert total_size <= 1.0

    def test_sample_respects_size_limit(self, tmp_path: Path) -> None:
        """Test that sampling respects size limit."""
        files_with_size = []
        for i in range(10):
            f = tmp_path / f"file{i}.txt"
            size_mb = 0.5  # Each file is 0.5 MB
            f.write_bytes(b"x" * int(size_mb * MB_TO_BYTES))
            files_with_size.append((f, size_mb))

        sampled, total_size = _sample_from_quartiles(
            files_with_size, count=4, max_size_mb=1.0
        )

        assert total_size <= 1.0


class TestFillRemainingSamples:
    """Tests for _fill_remaining_samples function."""

    def test_fill_to_target(self, tmp_path: Path) -> None:
        """Test filling remaining samples to reach target."""
        files_with_size = []
        for i in range(10):
            f = tmp_path / f"file{i}.txt"
            f.write_bytes(b"x" * 100)
            files_with_size.append((f, 100 / MB_TO_BYTES))

        initial = [files_with_size[0][0]]
        sampled, total = _fill_remaining_samples(
            files_with_size, initial, count=5, total_size=0.0001, max_size_mb=1.0
        )

        assert len(sampled) <= 5


class TestSampleDiverseFiles:
    """Tests for sample_diverse_files function."""

    def test_sample_empty_list(self) -> None:
        """Test sampling from empty file list."""
        result = sample_diverse_files([], count=5, max_size_mb=10)

        assert result == []

    def test_sample_respects_count(self, tmp_path: Path) -> None:
        """Test that sampling respects count limit."""
        files = []
        for i in range(20):
            f = tmp_path / f"file{i}.txt"
            f.write_bytes(b"x" * 100)
            files.append(f)

        result = sample_diverse_files(files, count=5, max_size_mb=10)

        assert len(result) <= 5

    def test_sample_returns_paths(self, tmp_path: Path) -> None:
        """Test that sampling returns Path objects."""
        f = tmp_path / "file.txt"
        f.write_bytes(b"x" * 100)

        result = sample_diverse_files([f], count=1, max_size_mb=10)

        assert all(isinstance(p, Path) for p in result)


class TestExtractFixturesForDataset:
    """Tests for extract_fixtures_for_dataset function."""

    def test_unknown_dataset_raises(self) -> None:
        """Test that unknown dataset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown dataset"):
            extract_fixtures_for_dataset("nonexistent_dataset")

    def test_missing_source_dir(self, tmp_path: Path) -> None:
        """Test handling of missing source directory."""
        with patch.dict(
            "extract_test_fixtures.DATASET_CONFIGS",
            {
                "test_dataset": {
                    "source_dir": tmp_path / "nonexistent",
                    "target_dir": tmp_path / "target",
                    "extensions": [".pdf"],
                    "count": 5,
                    "max_size_mb": 10,
                    "criteria": ["test"],
                }
            },
        ):
            result = extract_fixtures_for_dataset("test_dataset")

            assert result["status"] == "error"
            assert "not found" in result["message"]

    def test_no_candidate_files(self, tmp_path: Path) -> None:
        """Test handling of no candidate files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        with patch.dict(
            "extract_test_fixtures.DATASET_CONFIGS",
            {
                "test_dataset": {
                    "source_dir": source_dir,
                    "target_dir": tmp_path / "target",
                    "extensions": [".pdf"],
                    "count": 5,
                    "max_size_mb": 10,
                    "criteria": ["test"],
                }
            },
        ):
            result = extract_fixtures_for_dataset("test_dataset")

            assert result["status"] == "warning"
            assert "No candidate files" in result["message"]

    def test_dry_run_does_not_copy(self, tmp_path: Path) -> None:
        """Test that dry run doesn't copy files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.pdf").write_text("test")

        target_dir = tmp_path / "target"

        with patch.dict(
            "extract_test_fixtures.DATASET_CONFIGS",
            {
                "test_dataset": {
                    "source_dir": source_dir,
                    "target_dir": target_dir,
                    "extensions": [".pdf"],
                    "count": 5,
                    "max_size_mb": 10,
                    "criteria": ["test"],
                }
            },
        ):
            result = extract_fixtures_for_dataset("test_dataset", dry_run=True)

            assert not target_dir.exists()

    def test_successful_extraction(self, tmp_path: Path) -> None:
        """Test successful fixture extraction."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "doc1.pdf").write_text("pdf content 1")
        (source_dir / "doc2.pdf").write_text("pdf content 2")

        target_dir = tmp_path / "target"

        with patch.dict(
            "extract_test_fixtures.DATASET_CONFIGS",
            {
                "test_dataset": {
                    "source_dir": source_dir,
                    "target_dir": target_dir,
                    "extensions": [".pdf"],
                    "count": 2,
                    "max_size_mb": 10,
                    "criteria": ["criterion1", "criterion2"],
                }
            },
        ):
            result = extract_fixtures_for_dataset("test_dataset")

            assert result["status"] == "success"
            assert result["extracted"] > 0
            assert target_dir.exists()
            assert (target_dir / "manifest.json").exists()

    def test_manifest_created(self, tmp_path: Path) -> None:
        """Test that manifest file is created correctly."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.pdf").write_text("pdf content")

        target_dir = tmp_path / "target"

        with patch.dict(
            "extract_test_fixtures.DATASET_CONFIGS",
            {
                "test_dataset": {
                    "source_dir": source_dir,
                    "target_dir": target_dir,
                    "extensions": [".pdf"],
                    "count": 1,
                    "max_size_mb": 10,
                    "criteria": ["criterion1"],
                }
            },
        ):
            extract_fixtures_for_dataset("test_dataset")

            manifest_path = target_dir / "manifest.json"
            assert manifest_path.exists()

            with open(manifest_path) as f:
                manifest = json.load(f)

            assert "dataset" in manifest
            assert "files" in manifest
            assert "count" in manifest


class TestExtractAllFixtures:
    """Tests for extract_all_fixtures function."""

    def test_extract_all_dry_run(self) -> None:
        """Test extracting all fixtures in dry run mode."""
        result = extract_all_fixtures(dry_run=True)

        assert isinstance(result, dict)
        # Should attempt all configured datasets
        assert len(result) > 0

    def test_returns_results_for_each_dataset(self) -> None:
        """Test that results are returned for each dataset."""
        result = extract_all_fixtures(dry_run=True)

        for dataset_name, dataset_result in result.items():
            assert "status" in dataset_result
            assert "extracted" in dataset_result
