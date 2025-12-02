# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/promote_to_hf.py - Model promotion to HuggingFace Hub.

These tests verify the model promotion script correctly:
- Downloads artifacts from GCS
- Validates artifacts meet promotion criteria
- Generates model cards
- Uploads to HuggingFace Hub
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Skip entire module if google-cloud-storage is not installed
pytest.importorskip("google.cloud.storage", reason="google-cloud-storage not installed")

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from promote_to_hf import (
    check_promotion_criteria,
    generate_model_card,
    validate_artifacts,
)


class TestValidateArtifacts:
    """Tests for the validate_artifacts function in promote_to_hf."""

    @pytest.fixture
    def valid_artifact_dir(self, tmp_path: Path) -> Path:
        """Create a valid artifact directory."""
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()

        # Create required metadata files
        (artifact_dir / "training_config.yaml").write_text(
            yaml.dump(
                {
                    "model": {"architecture": "resnet50", "num_classes": 10},
                    "training": {"epochs": 100, "batch_size": 32},
                }
            )
        )
        (artifact_dir / "commit_hash.txt").write_text("abc123def456")
        (artifact_dir / "dataset_version.txt").write_text("v1.0.0")
        (artifact_dir / "env_info.txt").write_text("Python 3.10\nPyTorch 2.0")
        (artifact_dir / "metrics.json").write_text(
            json.dumps({"accuracy": 0.95, "val_loss": 0.05})
        )

        # Create model file
        (artifact_dir / "model_final.pth").write_bytes(b"x" * (2 * 1024 * 1024))

        return artifact_dir

    def test_validate_complete_artifacts(self, valid_artifact_dir: Path) -> None:
        """Test validation of complete artifact directory."""
        with patch("builtins.print"):
            metadata = validate_artifacts(str(valid_artifact_dir))

        assert "config" in metadata
        assert "metrics" in metadata
        assert "commit_info" in metadata
        assert "dataset_version" in metadata
        assert "model_files" in metadata
        assert len(metadata["model_files"]) >= 1

    def test_validate_missing_required_raises(self, tmp_path: Path) -> None:
        """Test that missing required files raises ValueError."""
        artifact_dir = tmp_path / "incomplete"
        artifact_dir.mkdir()

        # Only create some files
        (artifact_dir / "training_config.yaml").write_text(yaml.dump({"model": {}}))

        with pytest.raises(ValueError, match="Missing required"):
            with patch("builtins.print"):
                validate_artifacts(str(artifact_dir))

    def test_validate_without_metrics(self, valid_artifact_dir: Path) -> None:
        """Test validation succeeds without optional metrics file."""
        # Remove metrics file
        (valid_artifact_dir / "metrics.json").unlink()

        with patch("builtins.print"):
            metadata = validate_artifacts(str(valid_artifact_dir))

        assert metadata["metrics"] == {}

    def test_validate_multiple_model_formats(self, valid_artifact_dir: Path) -> None:
        """Test detection of multiple model file formats."""
        # Add additional model formats
        (valid_artifact_dir / "model.onnx").write_bytes(b"y" * (2 * 1024 * 1024))

        with patch("builtins.print"):
            metadata = validate_artifacts(str(valid_artifact_dir))

        # Should find both .pth and .onnx
        assert len(metadata["model_files"]) >= 2


class TestCheckPromotionCriteria:
    """Tests for the check_promotion_criteria function."""

    def test_criteria_met_with_valid_metadata(self) -> None:
        """Test criteria check passes with valid metadata."""
        metadata = {
            "metrics": {"accuracy": 0.95, "val_loss": 0.05},
            "model_files": ["/path/to/model.pth"],
            "commit_info": "abc123def456",
        }

        with patch("builtins.print"):
            result = check_promotion_criteria(metadata)

        assert result is True

    def test_criteria_fails_without_metrics(self) -> None:
        """Test criteria check fails without metrics."""
        metadata = {
            "metrics": {},
            "model_files": ["/path/to/model.pth"],
            "commit_info": "abc123",
        }

        with patch("builtins.print"):
            result = check_promotion_criteria(metadata)

        assert result is False

    def test_criteria_fails_without_model_files(self) -> None:
        """Test criteria check fails without model files."""
        metadata = {
            "metrics": {"accuracy": 0.95},
            "model_files": [],
            "commit_info": "abc123",
        }

        with patch("builtins.print"):
            result = check_promotion_criteria(metadata)

        assert result is False

    def test_criteria_warns_on_dirty_git(self) -> None:
        """Test criteria check warns on dirty git state."""
        metadata = {
            "metrics": {"accuracy": 0.95},
            "model_files": ["/path/to/model.pth"],
            "commit_info": "abc123 (dirty)",
        }

        with patch("builtins.print"):
            result = check_promotion_criteria(metadata)

        # Should still return False due to dirty state
        assert result is False


class TestGenerateModelCard:
    """Tests for the generate_model_card function."""

    @pytest.fixture
    def sample_metadata(self) -> dict[str, Any]:
        """Create sample metadata for model card generation."""
        return {
            "config": {
                "model": {
                    "architecture": "resnet50",
                    "input_size": 224,
                    "num_classes": 10,
                },
                "training": {
                    "batch_size": 32,
                    "epochs": 100,
                    "learning_rate": 0.001,
                    "optimizer": "Adam",
                },
            },
            "metrics": {
                "accuracy": 0.95,
                "val_accuracy": 0.93,
                "val_loss": 0.05,
                "val_macro_f1": 0.92,
            },
            "dataset_version": "OHR-Bench v1.0.0",
            "env_info": "Python 3.10, PyTorch 2.0, CUDA 11.8",
            "commit_info": "abc123def456 (clean)",
        }

    def test_model_card_contains_version(self, sample_metadata: dict) -> None:
        """Test that model card contains version information."""
        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=sample_metadata,
        )

        assert "v1.0.0" in card
        assert "Version" in card or "version" in card.lower()

    def test_model_card_contains_architecture(self, sample_metadata: dict) -> None:
        """Test that model card contains architecture details."""
        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=sample_metadata,
        )

        assert "resnet50" in card
        assert "224" in card  # input_size

    def test_model_card_contains_metrics(self, sample_metadata: dict) -> None:
        """Test that model card contains metrics."""
        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=sample_metadata,
        )

        assert "Accuracy" in card or "accuracy" in card.lower()
        assert "0.93" in card or "0.95" in card  # accuracy values

    def test_model_card_contains_training_config(self, sample_metadata: dict) -> None:
        """Test that model card contains training configuration."""
        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=sample_metadata,
        )

        assert "32" in card  # batch_size
        assert "100" in card  # epochs
        assert "Adam" in card  # optimizer

    def test_model_card_contains_usage_example(self, sample_metadata: dict) -> None:
        """Test that model card contains usage example."""
        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=sample_metadata,
        )

        assert "```python" in card
        assert "torch" in card

    def test_model_card_contains_citation(self, sample_metadata: dict) -> None:
        """Test that model card contains citation block."""
        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=sample_metadata,
        )

        assert "@software" in card or "Citation" in card

    def test_model_card_with_missing_metrics(self) -> None:
        """Test model card generation with missing metrics."""
        metadata: dict[str, Any] = {
            "config": {},
            "metrics": {},
            "dataset_version": "v1.0",
            "env_info": "test",
            "commit_info": "abc",
        }

        card = generate_model_card(
            model_name="test-model",
            version="v1.0.0",
            metadata=metadata,
        )

        # Should still generate a card
        assert "test-model" in card
        assert "N/A" in card  # Missing values should show N/A


class TestPushToHuggingface:
    """Tests for the push_to_huggingface function."""

    @pytest.fixture
    def mock_artifact_dir(self, tmp_path: Path) -> Path:
        """Create a mock artifact directory for testing."""
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()

        (artifact_dir / "model_final.pth").write_bytes(b"x" * 100)

        return artifact_dir

    def test_dry_run_creates_readme(self, mock_artifact_dir: Path) -> None:
        """Test that dry run creates README.md without uploading."""
        from promote_to_hf import push_to_huggingface

        metadata: dict[str, Any] = {
            "config": {"model": {}, "training": {}},
            "metrics": {},
            "model_files": [str(mock_artifact_dir / "model_final.pth")],
            "dataset_version": "v1.0",
            "env_info": "test",
            "commit_info": "abc",
        }

        with patch("builtins.print"):
            push_to_huggingface(
                artifact_dir=str(mock_artifact_dir),
                hf_repo="test/repo",
                version="v1.0.0",
                metadata=metadata,
                token="fake_token",
                dry_run=True,
            )

        # README should be created
        readme = mock_artifact_dir / "README.md"
        assert readme.exists()

    def test_push_calls_hf_api(self, mock_artifact_dir: Path) -> None:
        """Test that actual push calls HuggingFace API."""
        from promote_to_hf import push_to_huggingface

        metadata: dict[str, Any] = {
            "config": {"model": {}, "training": {}},
            "metrics": {},
            "model_files": [str(mock_artifact_dir / "model_final.pth")],
            "dataset_version": "v1.0",
            "env_info": "test",
            "commit_info": "abc",
        }

        with patch("promote_to_hf.create_repo") as mock_create:
            with patch("promote_to_hf.HfApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api
                mock_create.return_value = "https://huggingface.co/test/repo"

                with patch("builtins.print"):
                    push_to_huggingface(
                        artifact_dir=str(mock_artifact_dir),
                        hf_repo="test/repo",
                        version="v1.0.0",
                        metadata=metadata,
                        token="fake_token",
                        dry_run=False,
                    )

        # Should have called create_repo
        mock_create.assert_called_once()

        # Should have called upload_file for model and README
        assert mock_api.upload_file.called


class TestListAvailableRuns:
    """Tests for the list_available_runs function."""

    def test_list_runs_empty(self) -> None:
        """Test listing runs when none exist."""
        from promote_to_hf import list_available_runs

        with patch("promote_to_hf.storage.Client") as mock_client:
            mock_bucket = MagicMock()
            mock_client.return_value.bucket.return_value = mock_bucket

            mock_blobs = MagicMock()
            mock_blobs.prefixes = []
            mock_bucket.list_blobs.return_value = mock_blobs

            with patch("builtins.print") as mock_print:
                list_available_runs(
                    bucket_name="test-bucket",
                    project_name="test-project",
                    model_name="test-model",
                )

        # Should print "No runs found"
        print_calls = " ".join(str(call) for call in mock_print.call_args_list)
        assert "no runs" in print_calls.lower() or "No runs" in print_calls

    def test_list_runs_with_results(self) -> None:
        """Test listing runs when they exist."""
        from promote_to_hf import list_available_runs

        with patch("promote_to_hf.storage.Client") as mock_client:
            mock_bucket = MagicMock()
            mock_client.return_value.bucket.return_value = mock_bucket

            mock_blobs = MagicMock()
            mock_blobs.prefixes = [
                "project/model/runs/run-001/",
                "project/model/runs/run-002/",
            ]
            mock_bucket.list_blobs.return_value = mock_blobs

            with patch("builtins.print") as mock_print:
                list_available_runs(
                    bucket_name="test-bucket",
                    project_name="project",
                    model_name="model",
                )

        # Should print found runs
        print_calls = " ".join(str(call) for call in mock_print.call_args_list)
        assert "2" in print_calls or "run" in print_calls.lower()
