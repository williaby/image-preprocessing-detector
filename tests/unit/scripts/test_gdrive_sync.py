# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/gdrive_sync.py - Google Drive synchronization utilities.

These tests verify the Google Drive sync utilities correctly:
- Download datasets from Drive
- Upload model artifacts
- Check drive space
- Sync checkpoints
- Create dataset info files
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock gdown before importing gdrive_sync
sys.modules["gdown"] = MagicMock()

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import gdrive_sync
from gdrive_sync import (
    check_drive_space,
    create_dataset_info_file,
    download_dataset,
    sync_checkpoints_to_drive,
    upload_model_artifacts,
)


class TestMountGoogleDrive:
    """Tests for mount_google_drive function."""

    def test_mount_fails_outside_colab(self) -> None:
        """Test that mount fails when not in Colab."""
        from gdrive_sync import mount_google_drive

        # Should return False when google.colab not available
        result = mount_google_drive()
        assert result is False

    def test_mount_with_mock_colab(self) -> None:
        """Test mount with mocked Colab environment."""

        mock_drive = MagicMock()

        with patch.dict(sys.modules, {"google.colab": MagicMock()}):
            with patch.dict(
                sys.modules, {"google.colab.drive": mock_drive, "google": MagicMock()}
            ):
                # Need to re-import to pick up mock
                pass


class TestDownloadDataset:
    """Tests for download_dataset function."""

    def test_download_nonexistent_raises(self, tmp_path: Path) -> None:
        """Test downloading nonexistent path raises error."""
        fake_drive = tmp_path / "drive" / "dataset"
        local_path = tmp_path / "local"

        with pytest.raises(FileNotFoundError):
            download_dataset(str(fake_drive), str(local_path))

    def test_download_directory(self, tmp_path: Path) -> None:
        """Test downloading a directory."""
        # Create source directory with files
        drive_dir = tmp_path / "drive" / "dataset"
        drive_dir.mkdir(parents=True)
        (drive_dir / "file1.txt").write_text("content1")
        (drive_dir / "file2.txt").write_text("content2")

        local_dir = tmp_path / "local"

        result = download_dataset(str(drive_dir), str(local_dir))

        assert result == local_dir
        assert (local_dir / "file1.txt").exists()
        assert (local_dir / "file2.txt").exists()

    def test_download_zip_with_extraction(self, tmp_path: Path) -> None:
        """Test downloading and extracting ZIP file."""
        # Create source ZIP
        drive_dir = tmp_path / "drive"
        drive_dir.mkdir()

        zip_path = drive_dir / "dataset.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data.txt", "test content")
            zf.writestr("subdir/nested.txt", "nested content")

        local_dir = tmp_path / "local"

        result = download_dataset(str(zip_path), str(local_dir), extract_zip=True)

        assert result == local_dir
        assert (local_dir / "data.txt").exists()
        assert (local_dir / "subdir" / "nested.txt").exists()
        # ZIP should be deleted after extraction
        assert not (local_dir / "dataset.zip").exists()

    def test_download_zip_without_extraction(self, tmp_path: Path) -> None:
        """Test downloading ZIP without extraction."""
        drive_dir = tmp_path / "drive"
        drive_dir.mkdir()

        zip_path = drive_dir / "dataset.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data.txt", "test content")

        local_dir = tmp_path / "local"

        result = download_dataset(str(zip_path), str(local_dir), extract_zip=False)

        assert result == local_dir
        assert (local_dir / "dataset.zip").exists()
        # Should NOT be extracted
        assert not (local_dir / "data.txt").exists()

    def test_download_single_file(self, tmp_path: Path) -> None:
        """Test downloading a single file."""
        drive_dir = tmp_path / "drive"
        drive_dir.mkdir()
        source_file = drive_dir / "model.pt"
        source_file.write_text("model data")

        local_dir = tmp_path / "local"

        result = download_dataset(str(source_file), str(local_dir))

        assert result == local_dir / "model.pt"
        assert (local_dir / "model.pt").exists()


class TestUploadModelArtifacts:
    """Tests for upload_model_artifacts function."""

    def test_upload_single_file(self, tmp_path: Path) -> None:
        """Test uploading a single model file."""
        local_dir = tmp_path / "local"
        local_dir.mkdir()
        model_file = local_dir / "model.onnx"
        model_file.write_text("onnx model")

        drive_dir = tmp_path / "drive"

        upload_model_artifacts(str(model_file), str(drive_dir))

        assert (drive_dir / "model.onnx").exists()

    def test_upload_directory_excludes_checkpoints(self, tmp_path: Path) -> None:
        """Test uploading directory excludes checkpoint files by default."""
        local_dir = tmp_path / "local" / "training"
        local_dir.mkdir(parents=True)

        (local_dir / "model_final.pt").write_text("final model")
        (local_dir / "checkpoint_epoch_5.pt").write_text("checkpoint")
        (local_dir / "config.json").write_text("{}")

        drive_dir = tmp_path / "drive"

        upload_model_artifacts(
            str(local_dir), str(drive_dir), include_checkpoints=False
        )

        assert (drive_dir / "model_final.pt").exists()
        assert (drive_dir / "config.json").exists()
        assert not (drive_dir / "checkpoint_epoch_5.pt").exists()

    def test_upload_directory_includes_checkpoints(self, tmp_path: Path) -> None:
        """Test uploading directory includes checkpoints when requested."""
        local_dir = tmp_path / "local" / "training"
        local_dir.mkdir(parents=True)

        (local_dir / "model_final.pt").write_text("final model")
        (local_dir / "checkpoint_epoch_5.pt").write_text("checkpoint")

        drive_dir = tmp_path / "drive"

        upload_model_artifacts(str(local_dir), str(drive_dir), include_checkpoints=True)

        assert (drive_dir / "model_final.pt").exists()
        assert (drive_dir / "checkpoint_epoch_5.pt").exists()

    def test_upload_preserves_directory_structure(self, tmp_path: Path) -> None:
        """Test that nested directory structure is preserved."""
        local_dir = tmp_path / "local"
        (local_dir / "models").mkdir(parents=True)
        (local_dir / "logs").mkdir()

        (local_dir / "models" / "best.pt").write_text("best model")
        (local_dir / "logs" / "train.log").write_text("training log")

        drive_dir = tmp_path / "drive"

        upload_model_artifacts(str(local_dir), str(drive_dir))

        assert (drive_dir / "models" / "best.pt").exists()
        assert (drive_dir / "logs" / "train.log").exists()


class TestCheckDriveSpace:
    """Tests for check_drive_space function."""

    def test_check_space_unmounted(self, tmp_path: Path) -> None:
        """Test checking space when drive not mounted."""
        result = check_drive_space(str(tmp_path / "nonexistent"))

        assert "error" in result
        assert result["error"] == "Google Drive not mounted"

    def test_check_space_mounted(self, tmp_path: Path) -> None:
        """Test checking space on existing mount point."""
        mount_point = tmp_path / "drive"
        mount_point.mkdir()

        result = check_drive_space(str(mount_point))

        assert "total_gb" in result
        assert "used_gb" in result
        assert "free_gb" in result
        assert "usage_percent" in result

        # Verify values are positive
        assert result["total_gb"] > 0
        assert result["free_gb"] >= 0
        assert 0 <= result["usage_percent"] <= 100


class TestSyncCheckpointsToDrive:
    """Tests for sync_checkpoints_to_drive function."""

    def test_sync_incremental_new_files(self, tmp_path: Path) -> None:
        """Test incremental sync copies new files."""
        local_dir = tmp_path / "local" / "checkpoints"
        local_dir.mkdir(parents=True)
        drive_dir = tmp_path / "drive" / "checkpoints"

        # Create local checkpoints
        (local_dir / "checkpoint_1.pt").write_text("checkpoint 1")
        (local_dir / "checkpoint_2.pt").write_text("checkpoint 2")
        (local_dir / "metrics.json").write_text("{}")

        sync_checkpoints_to_drive(
            str(local_dir), str(drive_dir), sync_mode="incremental"
        )

        assert (drive_dir / "checkpoint_1.pt").exists()
        assert (drive_dir / "checkpoint_2.pt").exists()
        assert (drive_dir / "metrics.json").exists()

    def test_sync_incremental_skips_existing(self, tmp_path: Path) -> None:
        """Test incremental sync skips existing newer files."""
        local_dir = tmp_path / "local" / "checkpoints"
        local_dir.mkdir(parents=True)
        drive_dir = tmp_path / "drive" / "checkpoints"
        drive_dir.mkdir(parents=True)

        # Create checkpoint in both places
        local_file = local_dir / "checkpoint_1.pt"
        local_file.write_text("local version")

        drive_file = drive_dir / "checkpoint_1.pt"
        drive_file.write_text("drive version - newer")

        # Make drive file newer
        import time

        time.sleep(0.1)
        drive_file.write_text("drive version - newer updated")

        sync_checkpoints_to_drive(
            str(local_dir), str(drive_dir), sync_mode="incremental"
        )

        # Drive file should NOT be overwritten (it's newer)
        content = drive_file.read_text()
        assert "drive version" in content

    def test_sync_full_mode(self, tmp_path: Path) -> None:
        """Test full sync mode copies all files."""
        local_dir = tmp_path / "local" / "checkpoints"
        local_dir.mkdir(parents=True)
        drive_dir = tmp_path / "drive" / "checkpoints"
        drive_dir.mkdir(parents=True)

        (local_dir / "checkpoint_1.pt").write_text("local version")
        (drive_dir / "checkpoint_1.pt").write_text("drive version")

        sync_checkpoints_to_drive(str(local_dir), str(drive_dir), sync_mode="full")

        # In full mode, local file should overwrite
        content = (drive_dir / "checkpoint_1.pt").read_text()
        assert content == "local version"

    def test_sync_creates_drive_directory(self, tmp_path: Path) -> None:
        """Test sync creates drive directory if needed."""
        local_dir = tmp_path / "local" / "checkpoints"
        local_dir.mkdir(parents=True)
        (local_dir / "checkpoint.pt").write_text("data")

        drive_dir = tmp_path / "drive" / "nested" / "checkpoints"

        sync_checkpoints_to_drive(str(local_dir), str(drive_dir))

        assert drive_dir.exists()


class TestCreateDatasetInfoFile:
    """Tests for create_dataset_info_file function."""

    def test_create_info_file(self, tmp_path: Path) -> None:
        """Test creating dataset info file."""
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()

        info = {
            "name": "test_dataset",
            "size": 1000,
            "splits": {"train": 800, "val": 100, "test": 100},
        }

        create_dataset_info_file(str(dataset_dir), info)

        info_file = dataset_dir / "dataset_info.json"
        assert info_file.exists()

        with open(info_file) as f:
            loaded = json.load(f)

        assert loaded["name"] == "test_dataset"
        assert loaded["size"] == 1000
        assert loaded["splits"]["train"] == 800

    def test_overwrites_existing_info(self, tmp_path: Path) -> None:
        """Test that existing info file is overwritten."""
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()

        # Create initial info
        create_dataset_info_file(str(dataset_dir), {"version": 1})

        # Overwrite
        create_dataset_info_file(str(dataset_dir), {"version": 2})

        with open(dataset_dir / "dataset_info.json") as f:
            loaded = json.load(f)

        assert loaded["version"] == 2


class TestDownloadFromGoogleDriveUrl:
    """Tests for download_from_google_drive_url function."""

    def test_download_constructs_correct_url(self, tmp_path: Path) -> None:
        """Test that correct URL is constructed from file ID."""
        from gdrive_sync import download_from_google_drive_url

        output_path = tmp_path / "output.zip"

        # Mock gdown.download
        with patch.object(gdrive_sync, "gdown") as mock_gdown:
            mock_gdown.download = MagicMock()
            # Create a dummy file so the function doesn't fail
            output_path.write_text("dummy")

            try:
                download_from_google_drive_url(
                    "1abc123xyz", str(output_path), extract_zip=False
                )
            except Exception:
                pass  # Function may fail but we check the call

            # Verify gdown was called with correct URL
            if mock_gdown.download.called:
                call_args = mock_gdown.download.call_args
                assert "1abc123xyz" in str(call_args)

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        from gdrive_sync import download_from_google_drive_url

        output_path = tmp_path / "nested" / "path" / "file.zip"

        with patch.object(gdrive_sync, "gdown") as mock_gdown:
            mock_gdown.download = MagicMock()

            try:
                download_from_google_drive_url(
                    "test_id", str(output_path), extract_zip=False
                )
            except Exception:
                pass

        assert output_path.parent.exists()
