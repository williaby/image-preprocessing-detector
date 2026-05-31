"""Script ML Class Mapping (Tier 2 of Three-Tier Script Architecture).

This module provides configurable mapping from ISO 15924 script codes
to ML training classes. The mapping is loaded from config/script_ml_classes.yaml
and supports hot-reload without restart.

Three-tier architecture:
- Tier 1 (Storage): Full ISO 15924 codes stored in schema.py
- Tier 2 (ML Training): Grouped classes defined in config and mapped here
- Tier 3 (Routing): OCR engine selection in script_router.py

Example:
    >>> from image_preprocessing_detector.schema_utils.script_ml_mapping import (
    ...     ScriptMLMapping,
    ... )
    >>> mapping = ScriptMLMapping()
    >>> mapping.to_ml_class("Latn")  # Returns "LATN"
    >>> mapping.to_ml_class("Gujr")  # Returns "INDIC_OTHER"
    >>> mapping.to_ml_class("Zzz1")  # Returns "OTHER" (unmapped default)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


class ScriptMLMapping:
    """Configurable ISO 15924 -> ML class mapping.

    Loads mapping from config/script_ml_classes.yaml and provides
    methods to convert ISO 15924 codes to ML training classes.

    Attributes:
        DEFAULT_CONFIG_PATH: Default config path relative to project root.

    Args:
        config_path (Path | str | None): Path to config YAML. If None, uses default path. Searches relative to package, then project root.
    """

    # Default config path relative to project root
    DEFAULT_CONFIG_PATH = Path("config/script_ml_classes.yaml")

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = self._resolve_config_path(config_path)
        self._load_config()

    def _resolve_config_path(self, config_path: Path | str | None) -> Path:
        """Resolve config path, searching multiple locations."""
        if config_path is not None:
            return Path(config_path)

        # Try relative to package
        package_dir = Path(__file__).parent.parent.parent.parent.parent
        config_from_package = package_dir / self.DEFAULT_CONFIG_PATH
        if config_from_package.exists():
            return config_from_package

        # Try current working directory
        cwd_config = Path.cwd() / self.DEFAULT_CONFIG_PATH
        if cwd_config.exists():
            return cwd_config

        # Default to package-relative path even if it doesn't exist
        return config_from_package

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            # Provide sensible defaults if config doesn't exist
            self._set_defaults()
            return

        with open(self.config_path, encoding="utf-8") as f:
            self.config: dict[str, Any] = yaml.safe_load(f) or {}

        self.ml_classes: set[str] = set(self.config.get("ml_classes", []))
        self.mapping: dict[str, str] = self.config.get("iso15924_to_ml_class", {})
        self.default: str = self.config.get("unmapped_default", "OTHER")
        self.class_weights: dict[str, float] = self.config.get("class_weights", {})
        self.version: str = self.config.get("version", "unknown")

        # Clear any cached results
        self._get_cached_ml_class.cache_clear()

    def _set_defaults(self) -> None:
        """Set default values when config file is missing."""
        self.config = {}
        self.ml_classes = {
            "LATN",
            "CYRL",
            "GREK",
            "ARAB",
            "HEBR",
            "DEVA",
            "BENG",
            "TAML",
            "TELU",
            "HANS",
            "HANT",
            "JPAN",
            "KORE",
            "THAI",
            "TIBT",
            "INDIC_OTHER",
            "SE_ASIAN_OTHER",
            "OTHER",
            "UNKNOWN",
        }
        # Basic mapping for common scripts
        self.mapping = {
            "Latn": "LATN",
            "Cyrl": "CYRL",
            "Grek": "GREK",
            "Arab": "ARAB",
            "Hebr": "HEBR",
            "Deva": "DEVA",
            "Beng": "BENG",
            "Taml": "TAML",
            "Telu": "TELU",
            "Hans": "HANS",
            "Hant": "HANT",
            "Jpan": "JPAN",
            "Kore": "KORE",
            "Thai": "THAI",
            "Tibt": "TIBT",
            "Zzzz": "UNKNOWN",
        }
        self.default = "OTHER"
        self.class_weights = {}
        self.version = "default"

    @lru_cache(maxsize=256)  # noqa: B019 - Intentional caching for config lookups
    def _get_cached_ml_class(self, iso15924_code: str) -> str:
        """Cached mapping lookup."""
        return self.mapping.get(iso15924_code, self.default)

    def to_ml_class(self, iso15924_code: str) -> str:
        """Map ISO 15924 code to ML training class.

        Args:
            iso15924_code (str): 4-letter ISO 15924 script code (e.g., "Latn", "Deva")

        Returns:
            str: ML class string (e.g., "LATN", "INDIC_OTHER", "UNKNOWN")"""
        return self._get_cached_ml_class(iso15924_code)

    def get_all_codes_for_class(self, ml_class: str) -> list[str]:
        """Get all ISO 15924 codes that map to an ML class.

        Args:
            ml_class (str): ML class name (e.g., "LATN", "INDIC_OTHER")

        Returns:
            list[str]: List of ISO 15924 codes mapping to this class"""
        return [k for k, v in self.mapping.items() if v == ml_class]

    def get_class_weight(self, ml_class: str) -> float:
        """Get training weight for ML class.

        Args:
            ml_class (str): ML class name

        Returns:
            float: Weight for training (default 1.0)"""
        return self.class_weights.get(ml_class, 1.0)

    def get_all_ml_classes(self) -> list[str]:
        """Get list of all ML classes in order.

        Returns:
            list[str]: List of ML class names"""
        return list(self.ml_classes)

    def get_num_classes(self) -> int:
        """Get number of ML classes for model output dimension.

        Returns:
            int: Number of ML classes"""
        return len(self.ml_classes)

    def ml_class_to_index(self, ml_class: str) -> int:
        """Convert ML class to integer index.

        Args:
            ml_class (str): ML class name

        Returns:
            int: Integer index for model output

        Raises:
            ValueError: If ml_class is not valid
        """
        classes = list(self.ml_classes)
        if ml_class not in classes:
            raise ValueError(f"Unknown ML class: {ml_class}")
        return classes.index(ml_class)

    def index_to_ml_class(self, index: int) -> str:
        """Convert integer index to ML class name.

        Args:
            index (int): Integer index from model output

        Returns:
            str: ML class name
        """
        classes = list(self.ml_classes)
        return classes[index]

    def reload(self) -> None:
        """Hot-reload config without restart.

        Call this method to reload the config file if it has been
        modified. Clears cached mappings.
        """
        self._load_config()

    def is_valid_iso15924(self, code: str) -> bool:
        """Check if code is a known ISO 15924 script.

        Args:
            code (str): Potential ISO 15924 code

        Returns:
            bool: True if code is in mapping (directly known)"""
        return code in self.mapping

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ScriptMLMapping(version={self.version!r}, "
            f"num_classes={len(self.ml_classes)}, "
            f"num_mappings={len(self.mapping)})"
        )


# Module-level singleton for convenience
_default_mapping: ScriptMLMapping | None = None


def get_default_mapping() -> ScriptMLMapping:
    """Get default ScriptMLMapping singleton.

    Returns:
        ScriptMLMapping: ScriptMLMapping instance with default config"""
    global _default_mapping
    if _default_mapping is None:
        _default_mapping = ScriptMLMapping()
    return _default_mapping


def reset_default_mapping() -> None:
    """Reset the default mapping singleton.

    Call this after modifying config to force reload.
    """
    global _default_mapping
    _default_mapping = None


__all__ = [
    "ScriptMLMapping",
    "get_default_mapping",
    "reset_default_mapping",
]
