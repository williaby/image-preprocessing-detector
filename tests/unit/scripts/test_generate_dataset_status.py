# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/generate_dataset_status.py - Dataset status report generation.

These tests verify the dataset status report generation correctly:
- Gets dataset sizes
- Counts files by type
- Checks GCS status
- Generates reports
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# Scripts directory added to sys.path via tests/conftest.py
from generate_dataset_status import (
    check_gcs_status,
    count_files,
    get_dataset_size,
)


class TestGetDatasetSize:
    """Tests for get_dataset_size function."""

    def test_returns_tuple(self, tmp_path: Path) -> None:
        """Test that function returns tuple of (str, int)."""
        # Create test directory with a file
        test_dir = tmp_path / "test_dataset"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test content")

        result = get_dataset_size(test_dir)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_human_readable_size(self, tmp_path: Path) -> None:
        """Test that size is human readable."""
        test_dir = tmp_path / "test_dataset"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test content" * 100)

        human_size, _ = get_dataset_size(test_dir)

        assert isinstance(human_size, str)
        assert any(unit in human_size for unit in ["B", "KB", "MB", "GB", "TB"])

    def test_bytes_size_numeric(self, tmp_path: Path) -> None:
        """Test that bytes size is numeric."""
        test_dir = tmp_path / "test_dataset"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test content")

        _, bytes_size = get_dataset_size(test_dir)

        assert isinstance(bytes_size, int)
        assert bytes_size >= 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test handling of nonexistent directory."""
        result = get_dataset_size(tmp_path / "nonexistent")

        human_size, bytes_size = result
        assert human_size == "Unknown"
        assert bytes_size == 0


class TestCountFiles:
    """Tests for count_files function."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test counting files in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        counts = count_files(empty_dir)

        assert counts.get("total", 0) == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test counting files in nonexistent directory."""
        counts = count_files(tmp_path / "nonexistent")

        assert counts == {}

    def test_counts_by_extension(self, tmp_path: Path) -> None:
        """Test counting files by extension."""
        test_dir = tmp_path / "test_dataset"
        test_dir.mkdir()

        # Create files with different extensions
        (test_dir / "image1.jpg").write_text("jpg1")
        (test_dir / "image2.jpg").write_text("jpg2")
        (test_dir / "data.json").write_text("{}")
        (test_dir / "readme.txt").write_text("readme")

        counts = count_files(test_dir)

        assert counts.get(".jpg", 0) == 2
        assert counts.get(".json", 0) == 1
        assert counts.get(".txt", 0) == 1

    def test_total_count(self, tmp_path: Path) -> None:
        """Test total file count."""
        test_dir = tmp_path / "test_dataset"
        test_dir.mkdir()

        # Create multiple files
        for i in range(5):
            (test_dir / f"file{i}.txt").write_text(f"content{i}")

        counts = count_files(test_dir)

        assert counts.get("total", 0) == 5

    def test_custom_extensions(self, tmp_path: Path) -> None:
        """Test counting with custom extensions."""
        test_dir = tmp_path / "test_dataset"
        test_dir.mkdir()

        (test_dir / "model.onnx").write_text("model")
        (test_dir / "weights.pt").write_text("weights")

        counts = count_files(test_dir, extensions=[".onnx", ".pt"])

        assert counts.get(".onnx", 0) == 1
        assert counts.get(".pt", 0) == 1


class TestCheckGcsStatus:
    """Tests for check_gcs_status function."""

    def test_returns_tuple(self) -> None:
        """Test that function returns tuple of (bool, str)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            result = check_gcs_status("test_dataset")

            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_exists_true_when_found(self) -> None:
        """Test exists is True when dataset found in GCS."""
        with patch("subprocess.run") as mock_run:
            # First call (ls) returns success
            mock_ls = MagicMock(returncode=0)
            # Second call (du) returns size
            mock_du = MagicMock(returncode=0, stdout="10G gs://bucket/dataset/")
            mock_run.side_effect = [mock_ls, mock_du]

            exists, size = check_gcs_status("test_dataset")

            assert exists is True
            assert size == "10G"

    def test_exists_false_when_not_found(self) -> None:
        """Test exists is False when dataset not in GCS."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            exists, size = check_gcs_status("test_dataset")

            assert exists is False
            assert size == "Not uploaded"

    def test_handles_exception(self) -> None:
        """Test handling of subprocess exceptions."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Network error")

            exists, size = check_gcs_status("test_dataset")

            assert exists is False
            assert size == "Unknown"


class TestConstants:
    """Tests for module constants."""

    def test_nfs_root_defined(self) -> None:
        """Test NFS_ROOT is defined."""
        from generate_dataset_status import NFS_ROOT

        assert isinstance(NFS_ROOT, Path)

    def test_gcs_bucket_defined(self) -> None:
        """Test GCS_BUCKET is defined."""
        from generate_dataset_status import GCS_BUCKET

        assert isinstance(GCS_BUCKET, str)
        assert GCS_BUCKET.startswith("gs://")

    def test_gcs_credentials_defined(self) -> None:
        """Test GCS_CREDENTIALS is defined and points to expected path."""
        from generate_dataset_status import GCS_CREDENTIALS

        assert isinstance(GCS_CREDENTIALS, Path)
        assert GCS_CREDENTIALS.name == "service-account.json"
        assert ".gcp" in str(GCS_CREDENTIALS)


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from generate_dataset_status import main

        assert callable(main)
