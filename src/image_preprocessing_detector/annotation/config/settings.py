"""Configurable settings for the annotation system.

This module provides externalized configuration, replacing hardcoded
paths and values in the original monolith (issue P2-3).

Configuration Sources (priority order):
    1. Explicit AnnotationSettings instance
    2. Environment variables (ANNOTATION_* prefix)
    3. YAML configuration file (optional)
    4. Default values

Example:
    >>> from image_preprocessing_detector.annotation.config.settings import (
    ...     AnnotationSettings,
    ... )
    >>>
    >>> # Load from environment
    >>> settings = AnnotationSettings.from_env()
    >>>
    >>> # Load from YAML
    >>> settings = AnnotationSettings.from_yaml("config.yaml")
    >>>
    >>> # Create with custom values
    >>> settings = AnnotationSettings(
    ...     batch_size=200,
    ...     workers=8,
    ... )
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default path constants (S1192: avoid duplicate string literals)
DEFAULT_BASE_DIR = "/mnt/e/image_detection"
DEFAULT_REGISTRY_DIR = "/mnt/e/image_detection/metadata_registry"
DEFAULT_CHECKPOINT_DIR = "/mnt/e/image_detection/metadata_registry/.checkpoints"


@dataclass(frozen=True)
class AnnotationSettings:
    """Configurable annotation settings.

    All paths and thresholds externalized for portability.
    Frozen dataclass ensures settings are immutable after creation.

    Attributes:
        e_drive_root (Path): Root path for image detection data
        metadata_root (Path): Root path for metadata registry output
        checkpoint_dir (Path): Directory for checkpoint files
        cache_size_limit (int): Maximum LRU cache entries
        batch_size (int): Images per batch for GPU inference
        checkpoint_interval (int): Batches between checkpoints
        workers (int): CPU worker processes for parallel parsing
        hash_full_file (bool): Always True - enables full-file SHA256
        atomic_fsync (bool): Enable fsync for critical data durability
        yolo_confidence_threshold (float): Minimum YOLO detection confidence
        yolo_model_path (Path | None): Path to YOLO model weights (None = default)
        siglip_model_path (Path | None): Path to SigLIP model checkpoint (HuggingFace format)
        siglip_batch_size (int): Batch size for SigLIP inference
    """

    # Paths
    e_drive_root: Path = field(default_factory=lambda: Path(DEFAULT_BASE_DIR))
    metadata_root: Path = field(default_factory=lambda: Path(DEFAULT_REGISTRY_DIR))
    checkpoint_dir: Path = field(default_factory=lambda: Path(DEFAULT_CHECKPOINT_DIR))

    # Processing
    cache_size_limit: int = 10_000
    batch_size: int = 100
    checkpoint_interval: int = 100
    workers: int = 4

    # Integrity (P0-1, P2-2 fixes)
    hash_full_file: bool = True  # P0-1 fix - always True
    atomic_fsync: bool = False  # Enable for critical data

    # ML Providers
    yolo_confidence_threshold: float = 0.25
    yolo_model_path: Path | None = None
    siglip_model_path: Path | None = None
    siglip_batch_size: int = 32

    @classmethod
    def from_env(cls) -> AnnotationSettings:
        """Load settings from environment variables.

        Environment variables use ANNOTATION_ prefix:
            - ANNOTATION_E_DRIVE_ROOT
            - ANNOTATION_METADATA_ROOT
            - ANNOTATION_CHECKPOINT_DIR
            - ANNOTATION_CACHE_SIZE
            - ANNOTATION_BATCH_SIZE
            - ANNOTATION_CHECKPOINT_INTERVAL
            - ANNOTATION_WORKERS
            - ANNOTATION_ATOMIC_FSYNC
            - ANNOTATION_YOLO_CONFIDENCE
            - ANNOTATION_YOLO_MODEL_PATH
            - ANNOTATION_SIGLIP_MODEL_PATH
            - ANNOTATION_SIGLIP_BATCH_SIZE

        Returns:
            AnnotationSettings: AnnotationSettings instance with values from environment"""

        def get_path(key: str, default: str) -> Path:
            return Path(os.getenv(f"ANNOTATION_{key}", default))

        def get_int(key: str, default: int) -> int:
            return int(os.getenv(f"ANNOTATION_{key}", str(default)))

        def get_float(key: str, default: float) -> float:
            return float(os.getenv(f"ANNOTATION_{key}", str(default)))

        def get_bool(key: str, default: bool) -> bool:
            val = os.getenv(f"ANNOTATION_{key}", str(default)).lower()
            return val in ("true", "1", "yes")

        def get_optional_path(key: str) -> Path | None:
            val = os.getenv(f"ANNOTATION_{key}")
            return Path(val) if val else None

        return cls(
            e_drive_root=get_path("E_DRIVE_ROOT", DEFAULT_BASE_DIR),
            metadata_root=get_path("METADATA_ROOT", DEFAULT_REGISTRY_DIR),
            checkpoint_dir=get_path(
                "CHECKPOINT_DIR",
                DEFAULT_CHECKPOINT_DIR,
            ),
            cache_size_limit=get_int("CACHE_SIZE", 10_000),
            batch_size=get_int("BATCH_SIZE", 100),
            checkpoint_interval=get_int("CHECKPOINT_INTERVAL", 100),
            workers=get_int("WORKERS", 4),
            hash_full_file=True,  # Always True - P0-1 fix
            atomic_fsync=get_bool("ATOMIC_FSYNC", default=False),
            yolo_confidence_threshold=get_float("YOLO_CONFIDENCE", 0.25),
            yolo_model_path=get_optional_path("YOLO_MODEL_PATH"),
            siglip_model_path=get_optional_path("SIGLIP_MODEL_PATH"),
            siglip_batch_size=get_int("SIGLIP_BATCH_SIZE", 32),
        )

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> AnnotationSettings:
        """Load settings from YAML configuration file.

        YAML structure:
            ```yaml
            annotation:
              e_drive_root: /mnt/e/image_detection
              metadata_root: /mnt/e/image_detection/metadata_registry
              batch_size: 100
              workers: 4
              yolo:
                confidence_threshold: 0.25
                model_path: null
            ```

        Args:
            config_path (str | Path): Path to YAML configuration file

        Returns:
            AnnotationSettings: AnnotationSettings instance

        Raises:
            TypeError: If config file is not a valid mapping.
        """
        config_path = Path(config_path)
        with open(config_path) as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise TypeError(f"Config file must contain a mapping, got {type(raw)}")

        # Support both nested and flat structure
        config = raw.get("annotation", raw)

        # Handle nested YOLO config
        yolo_config = config.get("yolo", {})

        def get_path(key: str, default: str) -> Path:
            val = config.get(key, default)
            return Path(val) if val else Path(default)

        def get_optional_path(key: str, nested_key: str | None = None) -> Path | None:
            val = config.get(key, {}).get(nested_key) if nested_key else config.get(key)
            return Path(val) if val else None

        return cls(
            e_drive_root=get_path("e_drive_root", DEFAULT_BASE_DIR),
            metadata_root=get_path("metadata_root", DEFAULT_REGISTRY_DIR),
            checkpoint_dir=get_path(
                "checkpoint_dir",
                DEFAULT_CHECKPOINT_DIR,
            ),
            cache_size_limit=config.get(
                "cache_size_limit", config.get("cache_size", 10_000)
            ),
            batch_size=config.get("batch_size", 100),
            checkpoint_interval=config.get("checkpoint_interval", 100),
            workers=config.get("workers", 4),
            hash_full_file=True,  # Always True - P0-1 fix
            atomic_fsync=config.get("atomic_fsync", False),
            yolo_confidence_threshold=yolo_config.get(
                "confidence_threshold", config.get("yolo_confidence_threshold", 0.25)
            ),
            yolo_model_path=get_optional_path("yolo", "model_path"),
            siglip_model_path=get_optional_path("siglip", "model_path"),
            siglip_batch_size=config.get("siglip_batch_size", 32),
        )

    def validate(self) -> list[str]:
        """Validate settings and return list of issues.

        Returns:
            list[str]: List of validation error messages (empty if valid)"""
        issues: list[str] = []

        # Path validations (warnings only - may not exist yet)
        if not self.e_drive_root.exists():
            issues.append(f"e_drive_root does not exist: {self.e_drive_root}")

        # Value range validations
        if self.batch_size < 1:
            issues.append(f"batch_size must be positive, got {self.batch_size}")

        if self.workers < 1:
            issues.append(f"workers must be positive, got {self.workers}")

        if self.cache_size_limit < 1:
            issues.append(
                f"cache_size_limit must be positive, got {self.cache_size_limit}"
            )

        if not 0 < self.yolo_confidence_threshold <= 1:
            issues.append(
                f"yolo_confidence_threshold must be (0, 1], got {self.yolo_confidence_threshold}"
            )

        if self.yolo_model_path and not self.yolo_model_path.exists():
            issues.append(f"yolo_model_path does not exist: {self.yolo_model_path}")

        if self.siglip_model_path and not self.siglip_model_path.exists():
            issues.append(f"siglip_model_path does not exist: {self.siglip_model_path}")

        if self.siglip_batch_size < 1:
            issues.append(
                f"siglip_batch_size must be positive, got {self.siglip_batch_size}"
            )

        # P0-1 fix validation
        if not self.hash_full_file:
            issues.append("hash_full_file must be True (P0-1 fix)")

        return issues

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary for serialization.

        Returns:
            dict[str, Any]: Dictionary representation of settings"""
        return {
            "e_drive_root": str(self.e_drive_root),
            "metadata_root": str(self.metadata_root),
            "checkpoint_dir": str(self.checkpoint_dir),
            "cache_size_limit": self.cache_size_limit,
            "batch_size": self.batch_size,
            "checkpoint_interval": self.checkpoint_interval,
            "workers": self.workers,
            "hash_full_file": self.hash_full_file,
            "atomic_fsync": self.atomic_fsync,
            "yolo_confidence_threshold": self.yolo_confidence_threshold,
            "yolo_model_path": str(self.yolo_model_path)
            if self.yolo_model_path
            else None,
            "siglip_model_path": str(self.siglip_model_path)
            if self.siglip_model_path
            else None,
            "siglip_batch_size": self.siglip_batch_size,
        }


__all__ = [
    "AnnotationSettings",
]
