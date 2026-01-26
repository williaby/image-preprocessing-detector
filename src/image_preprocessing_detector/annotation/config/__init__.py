# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Configuration management for the annotation system.

Modules:
    - settings.py: AnnotationSettings dataclass with environment loading
    - datasets.py: DATASET_CONFIGS registry for dataset-specific config
    - tiers.py: TIER_0_DATASETS, TIER_1_DATASETS definitions

Configuration Sources (priority order):
    1. Explicit AnnotationSettings instance
    2. Environment variables (ANNOTATION_* prefix)
    3. YAML configuration file (optional)
    4. Default values

Example:
    >>> from image_preprocessing_detector.annotation.config import (
    ...     AnnotationSettings,
    ...     DATASET_CONFIGS,
    ...     DatasetConfig,
    ...     TIER_0_DATASETS,
    ...     get_dataset_path,
    ... )
    >>>
    >>> # Load from environment
    >>> settings = AnnotationSettings.from_env()
    >>>
    >>> # Load from YAML
    >>> settings = AnnotationSettings.from_yaml("config.yaml")
    >>>
    >>> # Get dataset configuration
    >>> diqa_config = DATASET_CONFIGS["diqa-5000"]
    >>> full_path = get_dataset_path(diqa_config, settings)
"""

from __future__ import annotations

# Phase 1.4.3: Datasets
from .datasets import (
    DATASET_CONFIGS,
    DatasetConfig,
    get_dataset_path,
    get_parser_module_name,
    is_benchmark_dataset,
    validate_dataset_configs,
)

# Phase 1.4.1-1.4.2: Settings
from .settings import AnnotationSettings

# Phase 1.4.4: Tiers
from .tiers import (
    CONTENT_FLAG_KEYS,
    TIER_0_DATASETS,
    TIER_1_DATASETS,
    get_tier_0_flags,
    get_tier_for_dataset,
    is_tier_0,
    is_tier_1,
)

__all__: list[str] = [
    "CONTENT_FLAG_KEYS",
    "DATASET_CONFIGS",
    "TIER_0_DATASETS",
    "TIER_1_DATASETS",
    "AnnotationSettings",
    "DatasetConfig",
    "get_dataset_path",
    "get_parser_module_name",
    "get_tier_0_flags",
    "get_tier_for_dataset",
    "is_benchmark_dataset",
    "is_tier_0",
    "is_tier_1",
    "validate_dataset_configs",
]
