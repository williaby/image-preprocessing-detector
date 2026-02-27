"""Shared utilities for Modal applications.

This package provides common functionality used across Modal
benchmark and training scripts to reduce code duplication.

Modules:
    constants: GCS configuration, volumes, secrets, prompts
    gcs_utils: GCS credential setup and dataset download/upload
    metrics_utils: Correlation metrics, bootstrapping, result formatting
    dataset_utils: Dataset loading utilities
"""

from modal.shared.constants import (
    DATASET_CACHE_DIR,
    GCS_ARCHIVE,
    GCS_BUCKET,
    IQA_PROMPT,
    arena_data_volume,
    arena_model_volume,
    checkpoint_volume,
    gcs_secret,
    training_data_volume,
)
from modal.shared.dataset_utils import load_diqa5000_dataset
from modal.shared.gcs_utils import (
    download_dataset_from_gcs,
    setup_gcs_credentials,
    upload_to_gcs,
)
from modal.shared.metrics_utils import (
    bootstrap_correlation_ci,
    compute_metrics,
    print_results,
)

__all__ = [
    "DATASET_CACHE_DIR",
    "GCS_ARCHIVE",
    # Constants
    "GCS_BUCKET",
    "IQA_PROMPT",
    "arena_data_volume",
    # Volumes
    "arena_model_volume",
    # Metrics utilities
    "bootstrap_correlation_ci",
    "checkpoint_volume",
    "compute_metrics",
    "download_dataset_from_gcs",
    # Secrets
    "gcs_secret",
    # Dataset utilities
    "load_diqa5000_dataset",
    "print_results",
    # GCS utilities
    "setup_gcs_credentials",
    "training_data_volume",
    "upload_to_gcs",
]
