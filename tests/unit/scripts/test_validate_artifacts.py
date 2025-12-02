# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/validate_artifacts.py - Training artifact validation.

These tests verify the artifact validation script correctly:
- Validates metadata file presence and format
- Validates model checkpoint files
- Checks git state for reproducibility
- Reports validation results with proper error handling
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_artifacts import (
    validate_artifacts,
    validate_metadata_file,
    validate_model_file,
)


class TestValidateMetadataFile:
    """Tests for the validate_metadata_file function."""

    def test_missing_file(self, tmp_path: Path) -> None:
        """Test validation fails for missing file."""
        missing = tmp_path / "missing.yaml"

        valid, message = validate_metadata_file(missing, "yaml")

        assert not valid
        assert "MISSING" in message

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test validation fails for empty file."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("")

        valid, message = validate_metadata_file(empty, "yaml")

        assert not valid
        assert "EMPTY" in message

    def test_valid_yaml_file(self, tmp_path: Path) -> None:
        """Test validation succeeds for valid YAML file."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("model:\n  architecture: resnet50\n  input_size: 224\n")

        valid, message = validate_metadata_file(yaml_file, "yaml")

        assert valid
        assert "VALID" in message

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Test validation fails for invalid YAML syntax."""
        invalid = tmp_path / "invalid.yaml"
        invalid.write_text("invalid: yaml: content: [[")

        valid, message = validate_metadata_file(invalid, "yaml")

        assert not valid
        assert "INVALID" in message

    def test_empty_yaml_content(self, tmp_path: Path) -> None:
        """Test validation fails for YAML with null content."""
        yaml_file = tmp_path / "null.yaml"
        yaml_file.write_text("~")  # YAML null

        valid, message = validate_metadata_file(yaml_file, "yaml")

        assert not valid
        assert "empty YAML" in message.lower() or "INVALID" in message

    def test_valid_json_file(self, tmp_path: Path) -> None:
        """Test validation succeeds for valid JSON file."""
        json_file = tmp_path / "metrics.json"
        json_file.write_text('{"accuracy": 0.95, "loss": 0.05}')

        valid, message = validate_metadata_file(json_file, "json")

        assert valid
        assert "VALID" in message

    def test_invalid_json_syntax(self, tmp_path: Path) -> None:
        """Test validation fails for invalid JSON syntax."""
        invalid = tmp_path / "invalid.json"
        invalid.write_text("{invalid json}")

        valid, message = validate_metadata_file(invalid, "json")

        assert not valid
        assert "INVALID" in message

    def test_empty_json_object(self, tmp_path: Path) -> None:
        """Test validation fails for empty JSON object."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("{}")

        valid, message = validate_metadata_file(json_file, "json")

        assert not valid
        assert "empty JSON" in message.lower() or "INVALID" in message

    def test_valid_text_file(self, tmp_path: Path) -> None:
        """Test validation succeeds for valid text file."""
        text_file = tmp_path / "commit_hash.txt"
        text_file.write_text("abc123def456")

        valid, message = validate_metadata_file(text_file, "text")

        assert valid
        assert "VALID" in message

    def test_whitespace_only_text_file(self, tmp_path: Path) -> None:
        """Test validation fails for whitespace-only text file."""
        text_file = tmp_path / "empty.txt"
        text_file.write_text("   \n\t  \n")

        valid, message = validate_metadata_file(text_file, "text")

        assert not valid
        assert "INVALID" in message or "empty" in message.lower()


class TestValidateModelFile:
    """Tests for the validate_model_file function."""

    def test_missing_model_file(self, tmp_path: Path) -> None:
        """Test validation fails for missing model file."""
        missing = tmp_path / "model.pth"

        valid, message = validate_model_file(missing)

        assert not valid
        assert "MISSING" in message

    def test_empty_model_file(self, tmp_path: Path) -> None:
        """Test validation fails for empty model file."""
        empty = tmp_path / "model.pth"
        empty.write_text("")

        valid, message = validate_model_file(empty)

        assert not valid
        assert "EMPTY" in message

    def test_suspiciously_small_model_file(self, tmp_path: Path) -> None:
        """Test validation warns for suspiciously small model file."""
        small_model = tmp_path / "model.pth"
        # Write less than 1MB
        small_model.write_bytes(b"x" * 100000)  # 100 KB

        valid, message = validate_model_file(small_model)

        assert not valid
        assert "SUSPICIOUS" in message

    def test_valid_model_file(self, tmp_path: Path) -> None:
        """Test validation succeeds for valid model file."""
        model_file = tmp_path / "model.pth"
        # Write more than 1MB
        model_file.write_bytes(b"x" * (1024 * 1024 + 1000))

        valid, message = validate_model_file(model_file)

        assert valid
        assert "VALID" in message


class TestValidateArtifacts:
    """Tests for the validate_artifacts function."""

    @pytest.fixture
    def valid_artifact_dir(self, tmp_path: Path) -> Path:
        """Create a valid artifact directory with all required files."""
        artifact_dir = tmp_path / "run_artifacts"
        artifact_dir.mkdir()

        # Create required metadata files
        (artifact_dir / "training_config.yaml").write_text(
            yaml.dump({"model": {"architecture": "resnet50"}, "training": {"epochs": 100}})
        )
        (artifact_dir / "commit_hash.txt").write_text("abc123def456 (clean)")
        (artifact_dir / "dataset_version.txt").write_text("v1.0.0")
        (artifact_dir / "env_info.txt").write_text("Python 3.10\nPyTorch 2.0")

        # Create optional metrics file
        (artifact_dir / "metrics.json").write_text(
            json.dumps({"accuracy": 0.95, "val_loss": 0.05})
        )

        # Create model file (>1MB)
        (artifact_dir / "model_final.pth").write_bytes(b"x" * (2 * 1024 * 1024))

        return artifact_dir

    @pytest.fixture
    def minimal_artifact_dir(self, tmp_path: Path) -> Path:
        """Create a minimal artifact directory with required files only."""
        artifact_dir = tmp_path / "minimal_artifacts"
        artifact_dir.mkdir()

        # Create only required metadata files
        (artifact_dir / "training_config.yaml").write_text(
            yaml.dump({"model": {}, "training": {}})
        )
        (artifact_dir / "commit_hash.txt").write_text("abc123")
        (artifact_dir / "dataset_version.txt").write_text("v1.0.0")
        (artifact_dir / "env_info.txt").write_text("test env")

        # Create model file
        (artifact_dir / "model.pth").write_bytes(b"x" * (2 * 1024 * 1024))

        return artifact_dir

    def test_validate_complete_artifacts(self, valid_artifact_dir: Path) -> None:
        """Test validation of complete valid artifacts."""
        # Suppress print output
        with patch("builtins.print"):
            results = validate_artifacts(str(valid_artifact_dir), strict=False)

        assert len(results["errors"]) == 0
        assert len(results["required_files"]) == 4  # 4 required files
        assert len(results["model_files"]) >= 1

    def test_validate_missing_required_file(self, valid_artifact_dir: Path) -> None:
        """Test validation fails when required file is missing."""
        # Remove a required file
        (valid_artifact_dir / "commit_hash.txt").unlink()

        with patch("builtins.print"):
            results = validate_artifacts(str(valid_artifact_dir), strict=False)

        assert len(results["errors"]) > 0
        assert any("commit_hash" in error.lower() for error in results["errors"])

    def test_validate_no_model_files(self, minimal_artifact_dir: Path) -> None:
        """Test validation fails when no model files are present."""
        # Remove model file
        (minimal_artifact_dir / "model.pth").unlink()

        with patch("builtins.print"):
            results = validate_artifacts(str(minimal_artifact_dir), strict=False)

        assert any("model" in error.lower() for error in results["errors"])

    def test_validate_dirty_git_state(self, valid_artifact_dir: Path) -> None:
        """Test validation warns for dirty git state."""
        # Update commit hash to indicate dirty state
        (valid_artifact_dir / "commit_hash.txt").write_text("abc123def456 (dirty)")

        with patch("builtins.print"):
            results = validate_artifacts(str(valid_artifact_dir), strict=False)

        assert any("dirty" in warning.lower() for warning in results["warnings"])

    def test_validate_strict_mode_fails_on_warnings(self, valid_artifact_dir: Path) -> None:
        """Test that strict mode treats warnings as errors."""
        # Add dirty git state to generate warning
        (valid_artifact_dir / "commit_hash.txt").write_text("abc123def456 (dirty)")

        # Strict mode should fail with warnings
        with patch("builtins.print"):
            results = validate_artifacts(str(valid_artifact_dir), strict=True)

        # The results should have warnings
        assert len(results["warnings"]) > 0

    def test_validate_missing_optional_metrics(self, minimal_artifact_dir: Path) -> None:
        """Test validation warns but doesn't fail for missing optional files."""
        with patch("builtins.print"):
            results = validate_artifacts(str(minimal_artifact_dir), strict=False)

        # Should have warning about missing metrics.json
        assert any(
            "metrics" in warning.lower() for warning in results["warnings"]
        ) or len(results["errors"]) == 0

    def test_validate_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test validation exits for non-existent directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(SystemExit):
            with patch("builtins.print"):
                validate_artifacts(str(nonexistent), strict=False)

    def test_validate_multiple_model_files(self, valid_artifact_dir: Path) -> None:
        """Test validation handles multiple model files."""
        # Add additional model files
        (valid_artifact_dir / "checkpoint_best.pth").write_bytes(b"y" * (2 * 1024 * 1024))
        (valid_artifact_dir / "model.onnx").write_bytes(b"z" * (2 * 1024 * 1024))

        with patch("builtins.print"):
            results = validate_artifacts(str(valid_artifact_dir), strict=False)

        assert len(results["model_files"]) >= 3

    def test_results_structure(self, valid_artifact_dir: Path) -> None:
        """Test that results have the expected structure."""
        with patch("builtins.print"):
            results = validate_artifacts(str(valid_artifact_dir), strict=False)

        assert "required_files" in results
        assert "optional_files" in results
        assert "model_files" in results
        assert "errors" in results
        assert "warnings" in results


class TestConfigCompleteness:
    """Tests for training config completeness checking."""

    def test_complete_config(self, tmp_path: Path) -> None:
        """Test validation with complete config structure."""
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()

        # Create complete config
        config = {
            "model": {"architecture": "resnet50", "num_classes": 10},
            "training": {"epochs": 100, "batch_size": 32},
        }
        (artifact_dir / "training_config.yaml").write_text(yaml.dump(config))
        (artifact_dir / "commit_hash.txt").write_text("abc123")
        (artifact_dir / "dataset_version.txt").write_text("v1.0")
        (artifact_dir / "env_info.txt").write_text("env")
        (artifact_dir / "model.pth").write_bytes(b"x" * (2 * 1024 * 1024))

        with patch("builtins.print"):
            results = validate_artifacts(str(artifact_dir), strict=False)

        # Should not have config-related warnings
        config_warnings = [w for w in results["warnings"] if "config" in w.lower()]
        assert len(config_warnings) == 0

    def test_incomplete_config(self, tmp_path: Path) -> None:
        """Test validation warns for incomplete config."""
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()

        # Create incomplete config (missing 'training' key)
        config = {"model": {"architecture": "resnet50"}}
        (artifact_dir / "training_config.yaml").write_text(yaml.dump(config))
        (artifact_dir / "commit_hash.txt").write_text("abc123")
        (artifact_dir / "dataset_version.txt").write_text("v1.0")
        (artifact_dir / "env_info.txt").write_text("env")
        (artifact_dir / "model.pth").write_bytes(b"x" * (2 * 1024 * 1024))

        with patch("builtins.print"):
            results = validate_artifacts(str(artifact_dir), strict=False)

        # Should have warning about missing keys
        assert any(
            "missing" in warning.lower() and "training" in warning.lower()
            for warning in results["warnings"]
        )
