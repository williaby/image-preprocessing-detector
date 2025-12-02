# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/download_phase3_datasets.py - Phase 3 dataset downloader.

These tests verify the Phase 3 dataset download script correctly:
- Validates dataset configurations
- Downloads from HuggingFace
- Clones from GitHub with URL validation
- Handles errors appropriately
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock huggingface_hub before importing
sys.modules["huggingface_hub"] = MagicMock()

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from download_phase3_datasets import (
    DATASETS,
    download_dataset,
    download_from_github,
    download_from_huggingface,
)


class TestDatasetConfigurations:
    """Tests for dataset configuration constants."""

    def test_datasets_defined(self) -> None:
        """Test that datasets dictionary is defined."""
        assert len(DATASETS) >= 4

    def test_ohr_bench_config(self) -> None:
        """Test OHR-Bench configuration."""
        assert "ohr-bench" in DATASETS
        config = DATASETS["ohr-bench"]
        assert config["source"] == "huggingface"
        assert config["repo_id"] == "opendatalab/OHR-Bench"
        assert config["priority"] == 1

    def test_docsynth_config(self) -> None:
        """Test DocSynth300K configuration."""
        assert "docsynth300k" in DATASETS
        config = DATASETS["docsynth300k"]
        assert config["source"] == "huggingface"
        assert config["size_gb"] == 113

    def test_pubtables_config(self) -> None:
        """Test PubTables-1M configuration."""
        assert "pubtables1m" in DATASETS
        config = DATASETS["pubtables1m"]
        assert config["source"] == "huggingface"
        assert "CDLA" in config["license"]

    def test_iam_config(self) -> None:
        """Test IAM Handwriting configuration."""
        assert "iam" in DATASETS
        config = DATASETS["iam"]
        assert config["source"] == "huggingface"
        assert config["license"] == "MIT"

    def test_all_configs_have_required_fields(self) -> None:
        """Test all configs have required fields."""
        required_fields = [
            "source",
            "local_dir",
            "size_gb",
            "priority",
            "license",
            "description",
        ]

        for name, config in DATASETS.items():
            for field in required_fields:
                assert field in config, f"{name} missing {field}"


class TestDownloadFromHuggingface:
    """Tests for download_from_huggingface function."""

    def test_dry_run_returns_true(self, tmp_path: Path) -> None:
        """Test that dry run returns True without downloading."""
        result = download_from_huggingface(
            repo_id="test/repo",
            local_dir=tmp_path / "test",
            dry_run=True,
        )

        assert result is True

    def test_creates_local_directory(self, tmp_path: Path) -> None:
        """Test that local directory is created."""
        local_dir = tmp_path / "test_dataset"

        with patch("huggingface_hub.snapshot_download"):
            download_from_huggingface(
                repo_id="test/repo",
                local_dir=local_dir,
                dry_run=False,
            )

        assert local_dir.exists()

    def test_calls_snapshot_download(self, tmp_path: Path) -> None:
        """Test that snapshot_download is called with correct params."""
        local_dir = tmp_path / "test_dataset"

        with patch("huggingface_hub.snapshot_download") as mock_download:
            download_from_huggingface(
                repo_id="opendatalab/OHR-Bench",
                local_dir=local_dir,
                dry_run=False,
            )

            mock_download.assert_called_once()
            call_kwargs = mock_download.call_args[1]
            assert call_kwargs["repo_id"] == "opendatalab/OHR-Bench"
            assert call_kwargs["repo_type"] == "dataset"
            assert call_kwargs["local_dir"] == str(local_dir)

    def test_returns_false_on_error(self, tmp_path: Path) -> None:
        """Test that errors return False."""
        with patch("huggingface_hub.snapshot_download") as mock_download:
            mock_download.side_effect = Exception("Network error")

            result = download_from_huggingface(
                repo_id="test/repo",
                local_dir=tmp_path / "test",
                dry_run=False,
            )

            assert result is False


class TestDownloadFromGithub:
    """Tests for download_from_github function."""

    def test_dry_run_returns_true(self, tmp_path: Path) -> None:
        """Test that dry run returns True without cloning."""
        result = download_from_github(
            repo_url="https://github.com/test/repo",
            local_dir=tmp_path / "test",
            dry_run=True,
        )

        assert result is True

    def test_validates_github_url(self, tmp_path: Path) -> None:
        """Test that non-GitHub URLs are rejected."""
        with pytest.raises(ValueError, match=r"Only https://github\.com URLs"):
            download_from_github(
                repo_url="https://gitlab.com/test/repo",
                local_dir=tmp_path / "test",
                dry_run=False,
            )

    def test_validates_https_scheme(self, tmp_path: Path) -> None:
        """Test that non-HTTPS URLs are rejected."""
        with pytest.raises(ValueError, match=r"Only https://github\.com URLs"):
            download_from_github(
                repo_url="http://github.com/test/repo",
                local_dir=tmp_path / "test",
                dry_run=False,
            )

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that parent directory is created."""
        local_dir = tmp_path / "parent" / "child"

        with patch("git.Repo") as mock_repo:
            download_from_github(
                repo_url="https://github.com/test/repo",
                local_dir=local_dir,
                dry_run=False,
            )

        assert local_dir.parent.exists()

    def test_calls_git_clone(self, tmp_path: Path) -> None:
        """Test that git clone is called."""
        local_dir = tmp_path / "test"

        with patch("git.Repo") as mock_repo:
            download_from_github(
                repo_url="https://github.com/test/repo",
                local_dir=local_dir,
                dry_run=False,
            )

            mock_repo.clone_from.assert_called_once_with(
                "https://github.com/test/repo",
                str(local_dir),
            )

    def test_returns_false_on_error(self, tmp_path: Path) -> None:
        """Test that errors return False."""
        with patch("git.Repo") as mock_repo:
            mock_repo.clone_from.side_effect = Exception("Clone failed")

            result = download_from_github(
                repo_url="https://github.com/test/repo",
                local_dir=tmp_path / "test",
                dry_run=False,
            )

            assert result is False


class TestDownloadDataset:
    """Tests for download_dataset function."""

    def test_unknown_dataset_returns_false(self) -> None:
        """Test that unknown dataset name returns False."""
        result = download_dataset("unknown_dataset")

        assert result is False

    def test_dry_run_known_dataset(self, tmp_path: Path) -> None:
        """Test dry run with known dataset."""
        with patch.dict(
            DATASETS,
            {
                "test-dataset": {
                    "source": "huggingface",
                    "repo_id": "test/repo",
                    "local_dir": tmp_path / "test",
                    "size_gb": 1,
                    "priority": 1,
                    "license": "MIT",
                    "description": "Test dataset",
                }
            },
        ):
            result = download_dataset("test-dataset", dry_run=True)

            assert result is True

    def test_huggingface_source(self, tmp_path: Path) -> None:
        """Test downloading from HuggingFace source."""
        with patch.dict(
            DATASETS,
            {
                "test-hf": {
                    "source": "huggingface",
                    "repo_id": "test/repo",
                    "local_dir": tmp_path / "test",
                    "size_gb": 1,
                    "priority": 1,
                    "license": "MIT",
                    "description": "Test",
                }
            },
        ):
            with patch(
                "download_phase3_datasets.download_from_huggingface"
            ) as mock_download:
                mock_download.return_value = True

                result = download_dataset("test-hf", dry_run=True)

                assert result is True


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from download_phase3_datasets import main

        assert callable(main)
