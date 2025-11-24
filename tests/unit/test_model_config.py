# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for model configuration utilities.

This module tests the centralized model configuration loading from
configs/models/ directory.
"""

from pathlib import Path

import pytest

from image_preprocessing_detector.utils.model_config import (
    _find_project_root,
    _load_yaml_config,
    get_active_doclayout_yolo_model_id,
    get_doclayout_yolo_common_config,
    get_doclayout_yolo_config,
    list_available_doclayout_yolo_models,
)


class TestFindProjectRoot:
    """Tests for _find_project_root function."""

    def test_finds_project_root(self) -> None:
        """Should find the project root containing pyproject.toml."""
        root = _find_project_root()
        assert root.exists()
        assert (root / "pyproject.toml").exists()

    def test_returns_path_object(self) -> None:
        """Should return a Path object."""
        root = _find_project_root()
        assert isinstance(root, Path)


class TestLoadYamlConfig:
    """Tests for _load_yaml_config function."""

    def test_loads_existing_config(self) -> None:
        """Should load an existing YAML config file."""
        root = _find_project_root()
        config_path = root / "configs" / "models" / "doclayout_yolo.yaml"
        config = _load_yaml_config(config_path)
        assert isinstance(config, dict)
        assert "active_model" in config
        assert "models" in config

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing config files."""
        missing_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            _load_yaml_config(missing_path)


class TestGetDoclayoutYoloConfig:
    """Tests for get_doclayout_yolo_config function."""

    def test_gets_active_model_config(self) -> None:
        """Should return config for the active model when no key specified."""
        config = get_doclayout_yolo_config()
        assert isinstance(config, dict)
        assert "huggingface_id" in config
        assert "recommended_image_size" in config
        assert "confidence_threshold" in config
        assert "name" in config

    def test_gets_specific_model_config(self) -> None:
        """Should return config for a specific model key."""
        config = get_doclayout_yolo_config("docstructbench")
        assert config["name"] == "DocStructBench"
        assert "juliozhao/DocLayout-YOLO-DocStructBench" in config["huggingface_id"]

    def test_gets_d4la_pretrained_config(self) -> None:
        """Should return config for d4la_pretrained model."""
        config = get_doclayout_yolo_config("d4la_pretrained")
        assert config["name"] == "D4LA (DocSynth300K pretrained)"
        assert config["recommended_image_size"] == 1600

    def test_gets_d4la_scratch_config(self) -> None:
        """Should return config for d4la_scratch model."""
        config = get_doclayout_yolo_config("d4la_scratch")
        assert config["name"] == "D4LA (from scratch)"
        assert config["performance"]["pretrained"] is False

    def test_raises_for_unknown_model_key(self) -> None:
        """Should raise ValueError for unknown model keys."""
        with pytest.raises(ValueError, match="Unknown model key"):
            get_doclayout_yolo_config("nonexistent_model")

    def test_error_message_includes_available_models(self) -> None:
        """Error message should list available model keys."""
        with pytest.raises(ValueError, match="docstructbench"):
            get_doclayout_yolo_config("invalid")


class TestGetDoclayoutYoloCommonConfig:
    """Tests for get_doclayout_yolo_common_config function."""

    def test_returns_common_settings(self) -> None:
        """Should return common settings dictionary."""
        config = get_doclayout_yolo_common_config()
        assert isinstance(config, dict)
        assert "architecture" in config
        assert "package" in config
        assert "import_statement" in config

    def test_includes_training_defaults(self) -> None:
        """Should include training default settings."""
        config = get_doclayout_yolo_common_config()
        assert "training_defaults" in config
        assert "batch_size" in config["training_defaults"]
        assert "epochs" in config["training_defaults"]

    def test_architecture_is_yolov10(self) -> None:
        """Architecture should be YOLOv10."""
        config = get_doclayout_yolo_common_config()
        assert config["architecture"] == "YOLOv10"


class TestGetActiveDoclayoutYoloModelId:
    """Tests for get_active_doclayout_yolo_model_id function."""

    def test_returns_string(self) -> None:
        """Should return a string model ID."""
        model_id = get_active_doclayout_yolo_model_id()
        assert isinstance(model_id, str)

    def test_returns_huggingface_id(self) -> None:
        """Should return a valid HuggingFace model identifier."""
        model_id = get_active_doclayout_yolo_model_id()
        assert "juliozhao/" in model_id
        assert "DocLayout-YOLO" in model_id


class TestListAvailableDoclayoutYoloModels:
    """Tests for list_available_doclayout_yolo_models function."""

    def test_returns_list(self) -> None:
        """Should return a list."""
        models = list_available_doclayout_yolo_models()
        assert isinstance(models, list)

    def test_includes_expected_models(self) -> None:
        """Should include known model keys."""
        models = list_available_doclayout_yolo_models()
        assert "docstructbench" in models
        assert "d4la_scratch" in models
        assert "d4la_pretrained" in models

    def test_list_not_empty(self) -> None:
        """Should return non-empty list."""
        models = list_available_doclayout_yolo_models()
        assert len(models) > 0
