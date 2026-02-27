"""Centralized model configuration utilities.

This module provides easy access to model configurations from the central
configs/models/ directory. Change model selection in ONE place.

Usage:
    from image_preprocessing_detector.utils.model_config import get_doclayout_yolo_config

    config = get_doclayout_yolo_config()
    model_id = config["huggingface_id"]  # e.g., "juliozhao/DocLayout-YOLO-DocStructBench"
    img_size = config["recommended_image_size"]  # e.g., 1024
"""

from pathlib import Path
from typing import Any, cast

import yaml

# Config file name constant to avoid duplication
_DOCLAYOUT_YOLO_CONFIG = "doclayout_yolo.yaml"


def _find_project_root() -> Path:
    """Find the project root directory by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find project root (no pyproject.toml found)")


def _load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Load a YAML configuration file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def get_doclayout_yolo_config(
    model_key: str | None = None,
) -> dict[str, Any]:
    """Get DocLayout-YOLO model configuration.

    Args:
        model_key: Specific model to get (e.g., "docstructbench", "d4la_pretrained").
                   If None, uses the active_model from config.

    Returns:
        Dictionary with model configuration including:
        - huggingface_id: HuggingFace model identifier
        - recommended_image_size: Recommended input image size
        - confidence_threshold: Default confidence threshold
        - name: Human-readable model name
        - description: Model description
        - use_case: Recommended use case

    Example:
        >>> config = get_doclayout_yolo_config()
        >>> config["huggingface_id"]
        'juliozhao/DocLayout-YOLO-DocStructBench'

        >>> config = get_doclayout_yolo_config("d4la_pretrained")
        >>> config["huggingface_id"]
        'juliozhao/DocLayout-YOLO-D4LA-Docsynth300K_pretrained'
    """
    project_root = _find_project_root()
    config_path = project_root / "configs" / "models" / _DOCLAYOUT_YOLO_CONFIG

    full_config = _load_yaml_config(config_path)

    # Determine which model to use
    if model_key is None:
        model_key = full_config["active_model"]

    if model_key not in full_config["models"]:
        available = list(full_config["models"].keys())
        raise ValueError(f"Unknown model key '{model_key}'. Available: {available}")

    return cast(dict[str, Any], full_config["models"][model_key])


def get_doclayout_yolo_common_config() -> dict[str, Any]:
    """Get common DocLayout-YOLO settings that apply to all models.

    Returns:
        Dictionary with common settings including:
        - architecture: Base architecture (YOLOv10)
        - package: pip package name
        - import_statement: Python import statement
        - training_defaults: Default training hyperparameters
    """
    project_root = _find_project_root()
    config_path = project_root / "configs" / "models" / _DOCLAYOUT_YOLO_CONFIG

    full_config = _load_yaml_config(config_path)
    return cast(dict[str, Any], full_config["common"])


def get_active_doclayout_yolo_model_id() -> str:
    """Get the HuggingFace model ID for the currently active DocLayout-YOLO model.

    This is a convenience function for the most common use case.

    Returns:
        HuggingFace model identifier string.

    Example:
        >>> get_active_doclayout_yolo_model_id()
        'juliozhao/DocLayout-YOLO-DocStructBench'
    """
    config = get_doclayout_yolo_config()
    return cast(str, config["huggingface_id"])


def list_available_doclayout_yolo_models() -> list[str]:
    """List all available DocLayout-YOLO model keys.

    Returns:
        List of model keys that can be passed to get_doclayout_yolo_config().

    Example:
        >>> list_available_doclayout_yolo_models()
        ['docstructbench', 'd4la_scratch', 'd4la_pretrained']
    """
    project_root = _find_project_root()
    config_path = project_root / "configs" / "models" / _DOCLAYOUT_YOLO_CONFIG

    full_config = _load_yaml_config(config_path)
    return list(full_config["models"].keys())
