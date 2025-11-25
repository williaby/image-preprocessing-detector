"""Utility modules for logging, telemetry, and common functions."""

# Core utilities (Phase 0/1) - always available
from image_preprocessing_detector.utils.datetime_compat import (
    UTC,
    MockDatetime,
    aware_to_naive,
    ensure_aware,
    is_aware,
    is_naive,
    local_now,
    mock_now,
    naive_to_aware,
    parse_iso,
    safe_compare,
    timestamp_now,
    to_iso,
    utc_from_timestamp,
    utc_now,
)
from image_preprocessing_detector.utils.device_probe import (
    DeviceCapabilities,
    clear_device_cache,
    get_recommended_device,
    probe_device_capabilities,
)
from image_preprocessing_detector.utils.log_config import get_logger, setup_logging

# Optional GCS utilities (Phase 2+) - require google-cloud-storage
try:
    from image_preprocessing_detector.utils.gcs_uploader import (
        download_run_from_gcs,
        list_runs,
        upload_dir_to_gcs,
        upload_file_to_gcs,
        upload_run_to_gcs,
    )

    _HAS_GCS = True
except ImportError:
    _HAS_GCS = False

# Optional metadata utilities (Phase 2+) - require additional dependencies
try:
    from image_preprocessing_detector.utils.metadata_generator import (
        generate_commit_hash_file,
        generate_dataset_version_file,
        generate_env_info_file,
        generate_metrics_file,
        generate_run_id,
        generate_run_metadata,
        generate_training_config_file,
    )

    _HAS_METADATA = True
except ImportError:
    _HAS_METADATA = False

# Build __all__ dynamically based on available imports
__all__ = [
    "UTC",
    "DeviceCapabilities",
    "MockDatetime",
    "aware_to_naive",
    "clear_device_cache",
    "ensure_aware",
    "get_logger",
    "get_recommended_device",
    "is_aware",
    "is_naive",
    "local_now",
    "mock_now",
    "naive_to_aware",
    "parse_iso",
    "probe_device_capabilities",
    "safe_compare",
    "setup_logging",
    "timestamp_now",
    "to_iso",
    "utc_from_timestamp",
    "utc_now",
]

if _HAS_GCS:
    __all__.extend(
        [
            "download_run_from_gcs",
            "list_runs",
            "upload_dir_to_gcs",
            "upload_file_to_gcs",
            "upload_run_to_gcs",
        ]
    )

if _HAS_METADATA:
    __all__.extend(
        [
            "generate_commit_hash_file",
            "generate_dataset_version_file",
            "generate_env_info_file",
            "generate_metrics_file",
            "generate_run_id",
            "generate_run_metadata",
            "generate_training_config_file",
        ]
    )
