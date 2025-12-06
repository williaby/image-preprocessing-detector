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
from image_preprocessing_detector.utils.path_security import validate_safe_path
from image_preprocessing_detector.utils.tensor_cache import (
    CacheMetrics,
    LRUCache,
    clear_all_caches,
    compute_page_key,
    compute_tensor_key,
    get_array_size_bytes,
    get_combined_cache_metrics,
    get_page_cache,
    get_tensor_cache,
    reset_cache_instances,
)

# Optional GCS utilities (Phase 2+) - require google-cloud-storage
# Use lowercase to avoid BasedPyright reportConstantRedefinition
try:
    from image_preprocessing_detector.utils.gcs_uploader import (
        download_run_from_gcs,
        list_runs,
        upload_dir_to_gcs,
        upload_file_to_gcs,
        upload_run_to_gcs,
    )

    _has_gcs = True
except ImportError:
    _has_gcs = False

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

    _has_metadata = True
except ImportError:
    _has_metadata = False

# Build __all__ dynamically based on available imports
__all__ = [
    "UTC",
    "CacheMetrics",
    "DeviceCapabilities",
    "LRUCache",
    "MockDatetime",
    "aware_to_naive",
    "clear_all_caches",
    "clear_device_cache",
    "compute_page_key",
    "compute_tensor_key",
    "ensure_aware",
    "get_array_size_bytes",
    "get_combined_cache_metrics",
    "get_logger",
    "get_page_cache",
    "get_recommended_device",
    "get_tensor_cache",
    "is_aware",
    "is_naive",
    "local_now",
    "mock_now",
    "naive_to_aware",
    "parse_iso",
    "probe_device_capabilities",
    "reset_cache_instances",
    "safe_compare",
    "setup_logging",
    "timestamp_now",
    "to_iso",
    "utc_from_timestamp",
    "utc_now",
    "validate_safe_path",
]

if _has_gcs:
    __all__.extend(
        [
            "download_run_from_gcs",
            "list_runs",
            "upload_dir_to_gcs",
            "upload_file_to_gcs",
            "upload_run_to_gcs",
        ]
    )

if _has_metadata:
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
