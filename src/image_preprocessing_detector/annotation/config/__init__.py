"""Configuration management for the annotation system.

Modules:
    - settings.py: AnnotationSettings dataclass with environment loading
    - datasets.py: DATASET_CONFIGS registry for dataset-specific config
    - tiers.py: TIER_0_DATASETS, TIER_1_DATASETS definitions
    - validators.py: Comprehensive dataset config validation

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

Validation:
    >>> from image_preprocessing_detector.annotation.config import (
    ...     validate_dataset_config,
    ...     validate_all_configs,
    ... )
    >>>
    >>> # Validate single config
    >>> result = validate_dataset_config(diqa_config)
    >>> if not result.is_valid:
    ...     print(result.format())
    >>>
    >>> # Validate all configs
    >>> report = validate_all_configs(DATASET_CONFIGS)
    >>> print(report.summary())
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

# Phase 3.1.2: Comprehensive Validators
from .validators import (
    BatchValidationReport,
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
    quick_validate,
    validate_all_configs,
    validate_dataset_config,
)

__all__: list[str] = [
    # Tiers
    "CONTENT_FLAG_KEYS",
    # Datasets
    "DATASET_CONFIGS",
    "TIER_0_DATASETS",
    "TIER_1_DATASETS",
    # Settings
    "AnnotationSettings",
    # Validators
    "BatchValidationReport",
    "DatasetConfig",
    "ValidationMessage",
    "ValidationResult",
    "ValidationSeverity",
    "get_dataset_path",
    "get_parser_module_name",
    "get_tier_0_flags",
    "get_tier_for_dataset",
    "is_benchmark_dataset",
    "is_tier_0",
    "is_tier_1",
    "quick_validate",
    "validate_all_configs",
    "validate_dataset_config",
    "validate_dataset_configs",
]
