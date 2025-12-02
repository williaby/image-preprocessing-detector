# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/organize_dual_storage.py - Multi-tier storage management.

These tests verify the storage organization script correctly:
- Manages Local + NFS + GCS storage tiers
- Creates symlinks for dataset access
- Handles GCS sync operations
- Shows storage status
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from organize_dual_storage import (
    DATASETS,
    check_prerequisites,
    create_symlink,
    show_status,
)


class TestDatasetsConfig:
    """Tests for the DATASETS configuration."""

    def test_datasets_has_expected_structure(self) -> None:
        """Test that DATASETS has expected keys."""
        required_keys = {"nfs_path", "local_path", "gcs_path", "size_gb", "description"}

        for name, config in DATASETS.items():
            missing = required_keys - set(config.keys())
            assert not missing, f"Dataset {name} missing keys: {missing}"

    def test_dataset_paths_are_relative(self) -> None:
        """Test that dataset paths are relative."""
        for name, config in DATASETS.items():
            assert not config["nfs_path"].startswith("/"), f"{name} has absolute nfs_path"
            assert not config["local_path"].startswith("/"), f"{name} has absolute local_path"
            assert not config["gcs_path"].startswith("/"), f"{name} has absolute gcs_path"

    def test_all_sizes_are_positive(self) -> None:
        """Test that all dataset sizes are positive numbers."""
        for name, config in DATASETS.items():
            assert config["size_gb"] > 0, f"Dataset {name} has invalid size"


class TestCheckPrerequisites:
    """Tests for the check_prerequisites function."""

    def test_prerequisites_with_missing_nfs(self, tmp_path: Path) -> None:
        """Test prerequisites check fails when NFS is missing."""
        with patch("organize_dual_storage.NFS_ROOT", tmp_path / "nonexistent"):
            with patch("organize_dual_storage.GCS_CREDENTIALS", tmp_path / "creds.json"):
                # Create credentials file
                (tmp_path / "creds.json").write_text("{}")

                with patch("builtins.print"):
                    result = check_prerequisites()

        assert result is False

    def test_prerequisites_with_missing_credentials(self, tmp_path: Path) -> None:
        """Test prerequisites check fails when credentials are missing."""
        nfs_dir = tmp_path / "nfs"
        nfs_dir.mkdir()

        with patch("organize_dual_storage.NFS_ROOT", nfs_dir):
            with patch("organize_dual_storage.GCS_CREDENTIALS", tmp_path / "nonexistent.json"):
                with patch("builtins.print"):
                    result = check_prerequisites()

        assert result is False

    def test_prerequisites_all_present(self, tmp_path: Path) -> None:
        """Test prerequisites check passes when all present."""
        nfs_dir = tmp_path / "nfs"
        nfs_dir.mkdir()
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("{}")

        with patch("organize_dual_storage.NFS_ROOT", nfs_dir):
            with patch("organize_dual_storage.GCS_CREDENTIALS", creds_file):
                with patch("builtins.print"):
                    result = check_prerequisites()

        assert result is True


class TestCreateSymlink:
    """Tests for the create_symlink function."""

    def test_create_symlink_success(self, tmp_path: Path) -> None:
        """Test successful symlink creation."""
        # Setup NFS directory structure
        nfs_root = tmp_path / "nfs"
        nfs_dataset = nfs_root / "benchmarks" / "tablebank"
        nfs_dataset.mkdir(parents=True)
        (nfs_dataset / "data.txt").write_text("test data")

        # Setup project root
        project_root = tmp_path / "project"
        local_data = project_root / "data" / "benchmarks"
        local_data.mkdir(parents=True)

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.PROJECT_ROOT", project_root):
                with patch("builtins.print"):
                    result = create_symlink("tablebank")

        assert result is True

        # Verify symlink was created
        symlink_path = project_root / "data" / "benchmarks" / "tablebank"
        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == nfs_dataset

    def test_create_symlink_unknown_dataset(self, tmp_path: Path) -> None:
        """Test symlink creation fails for unknown dataset."""
        with patch("builtins.print"):
            result = create_symlink("nonexistent_dataset")

        assert result is False

    def test_create_symlink_missing_nfs_source(self, tmp_path: Path) -> None:
        """Test symlink creation fails when NFS source doesn't exist."""
        nfs_root = tmp_path / "nfs"
        nfs_root.mkdir()  # But don't create the dataset subdirectory

        project_root = tmp_path / "project"
        project_root.mkdir()

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.PROJECT_ROOT", project_root):
                with patch("builtins.print"):
                    result = create_symlink("tablebank")

        assert result is False

    def test_create_symlink_removes_existing_symlink(self, tmp_path: Path) -> None:
        """Test that existing symlink is replaced."""
        # Setup NFS directory
        nfs_root = tmp_path / "nfs"
        nfs_dataset = nfs_root / "benchmarks" / "tablebank"
        nfs_dataset.mkdir(parents=True)

        # Create old target and symlink
        old_target = tmp_path / "old_target"
        old_target.mkdir()

        project_root = tmp_path / "project"
        local_data = project_root / "data" / "benchmarks"
        local_data.mkdir(parents=True)

        existing_symlink = local_data / "tablebank"
        existing_symlink.symlink_to(old_target)

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.PROJECT_ROOT", project_root):
                with patch("builtins.print"):
                    result = create_symlink("tablebank")

        assert result is True

        # Verify symlink now points to new target
        assert existing_symlink.resolve() == nfs_dataset

    def test_create_symlink_fails_if_regular_dir_exists(self, tmp_path: Path) -> None:
        """Test symlink creation fails if regular directory exists."""
        # Setup NFS directory
        nfs_root = tmp_path / "nfs"
        nfs_dataset = nfs_root / "benchmarks" / "tablebank"
        nfs_dataset.mkdir(parents=True)

        # Create regular directory (not symlink) at local path
        project_root = tmp_path / "project"
        local_data = project_root / "data" / "benchmarks"
        local_data.mkdir(parents=True)
        existing_dir = local_data / "tablebank"
        existing_dir.mkdir()
        (existing_dir / "file.txt").write_text("existing content")

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.PROJECT_ROOT", project_root):
                with patch("builtins.print"):
                    result = create_symlink("tablebank")

        assert result is False

        # Original directory should still exist
        assert existing_dir.is_dir()
        assert not existing_dir.is_symlink()


class TestShowStatus:
    """Tests for the show_status function."""

    def test_show_status_outputs_table(self, tmp_path: Path, capsys) -> None:
        """Test that show_status outputs a status table."""
        nfs_root = tmp_path / "nfs"
        nfs_root.mkdir()

        project_root = tmp_path / "project"
        project_root.mkdir()

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.PROJECT_ROOT", project_root):
                show_status()

        captured = capsys.readouterr()
        output = captured.out

        # Should contain table headers
        assert "Dataset" in output or "dataset" in output.lower()
        assert "Storage Status" in output or any(
            name in output for name in DATASETS.keys()
        )


class TestPullFromGCS:
    """Tests for the pull_from_gcs function."""

    def test_pull_from_gcs_unknown_dataset(self) -> None:
        """Test pull fails for unknown dataset."""
        # Import inside test to avoid module-level issues
        from organize_dual_storage import pull_from_gcs

        with patch("builtins.print"):
            result = pull_from_gcs("nonexistent_dataset")

        assert result is False

    def test_pull_from_gcs_calls_gsutil(self, tmp_path: Path) -> None:
        """Test that pull_from_gcs calls gsutil correctly."""
        from organize_dual_storage import pull_from_gcs

        nfs_root = tmp_path / "nfs"
        nfs_root.mkdir()

        creds_file = tmp_path / "creds.json"
        creds_file.write_text("{}")

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.GCS_CREDENTIALS", creds_file):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    with patch("builtins.print"):
                        result = pull_from_gcs("tablebank")

        assert result is True
        mock_run.assert_called_once()

        # Verify gsutil command structure
        call_args = mock_run.call_args
        cmd = call_args[0][0]  # First positional arg is the command list
        assert "gsutil" in cmd
        assert "-m" in cmd
        assert "rsync" in cmd
        assert "-r" in cmd

    def test_pull_from_gcs_handles_failure(self, tmp_path: Path) -> None:
        """Test that pull_from_gcs handles gsutil failure."""
        from organize_dual_storage import pull_from_gcs

        nfs_root = tmp_path / "nfs"
        nfs_root.mkdir()

        creds_file = tmp_path / "creds.json"
        creds_file.write_text("{}")

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.GCS_CREDENTIALS", creds_file):
                with patch("subprocess.run") as mock_run:
                    mock_run.side_effect = subprocess.CalledProcessError(1, "gsutil")

                    with patch("builtins.print"):
                        result = pull_from_gcs("tablebank")

        assert result is False


class TestSyncToGCS:
    """Tests for the sync_to_gcs function."""

    def test_sync_to_gcs_unknown_dataset(self) -> None:
        """Test sync fails for unknown dataset."""
        from organize_dual_storage import sync_to_gcs

        with patch("builtins.print"):
            result = sync_to_gcs("nonexistent_dataset")

        assert result is False

    def test_sync_to_gcs_missing_nfs_path(self, tmp_path: Path) -> None:
        """Test sync fails when NFS path doesn't exist."""
        from organize_dual_storage import sync_to_gcs

        nfs_root = tmp_path / "nfs"
        nfs_root.mkdir()  # Don't create dataset subdir

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("builtins.print"):
                result = sync_to_gcs("tablebank")

        assert result is False

    def test_sync_to_gcs_calls_gsutil(self, tmp_path: Path) -> None:
        """Test that sync_to_gcs calls gsutil correctly."""
        from organize_dual_storage import sync_to_gcs

        nfs_root = tmp_path / "nfs"
        nfs_dataset = nfs_root / "benchmarks" / "tablebank"
        nfs_dataset.mkdir(parents=True)

        creds_file = tmp_path / "creds.json"
        creds_file.write_text("{}")

        with patch("organize_dual_storage.NFS_ROOT", nfs_root):
            with patch("organize_dual_storage.GCS_CREDENTIALS", creds_file):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    with patch("builtins.print"):
                        result = sync_to_gcs("tablebank")

        assert result is True
        mock_run.assert_called_once()
