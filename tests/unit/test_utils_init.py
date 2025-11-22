"""Unit tests for utils/__init__.py conditional imports and __all__ generation."""

import importlib
import sys
from unittest import mock


class TestUtilsInitImports:
    """Test conditional imports in utils/__init__.py."""

    def test_core_utilities_always_available(self) -> None:
        """Test that core utilities are always available."""
        # Re-import to ensure fresh import
        if "image_preprocessing_detector.utils" in sys.modules:
            del sys.modules["image_preprocessing_detector.utils"]

        from image_preprocessing_detector import utils

        # Core utilities should always be in __all__
        assert "get_logger" in utils.__all__
        assert "setup_logging" in utils.__all__

    def test_gcs_utilities_conditional_availability(self) -> None:
        """Test GCS utilities availability depends on google-cloud-storage.

        When google-cloud-storage IS installed (ml extra), utilities are exported.
        When google-cloud-storage is NOT installed, utilities are not exported.
        """
        # Re-import to ensure fresh import
        if "image_preprocessing_detector.utils" in sys.modules:
            del sys.modules["image_preprocessing_detector.utils"]

        from image_preprocessing_detector import utils

        # Check if google-cloud-storage is installed
        try:
            import google.cloud.storage  # noqa: F401

            gcs_available = True
        except ImportError:
            gcs_available = False

        if gcs_available:
            # GCS utilities should be in __all__ when google-cloud-storage is installed
            assert "upload_file_to_gcs" in utils.__all__
            assert "upload_dir_to_gcs" in utils.__all__
            assert "upload_run_to_gcs" in utils.__all__
            assert "download_run_from_gcs" in utils.__all__
            assert "list_runs" in utils.__all__
        else:
            # GCS utilities should not be in __all__ when not installed
            assert "upload_file_to_gcs" not in utils.__all__
            assert "upload_dir_to_gcs" not in utils.__all__
            assert "upload_run_to_gcs" not in utils.__all__
            assert "download_run_from_gcs" not in utils.__all__
            assert "list_runs" not in utils.__all__

    def test_metadata_utilities_available_in_dev_environment(self) -> None:
        """Test that metadata utilities are available in dev environment (yaml is installed)."""
        # Re-import to ensure fresh import
        if "image_preprocessing_detector.utils" in sys.modules:
            del sys.modules["image_preprocessing_detector.utils"]

        from image_preprocessing_detector import utils

        # Metadata utilities should be in __all__ when yaml is available (dev environment)
        assert "generate_run_id" in utils.__all__
        assert "generate_run_metadata" in utils.__all__
        assert "generate_commit_hash_file" in utils.__all__
        assert "generate_dataset_version_file" in utils.__all__
        assert "generate_env_info_file" in utils.__all__
        assert "generate_metrics_file" in utils.__all__
        assert "generate_training_config_file" in utils.__all__

    def test_gcs_utilities_available_when_imported(self) -> None:
        """Test that GCS utilities are added to __all__ when successfully imported."""
        # Clean up any existing imports
        modules_to_clean = [
            "image_preprocessing_detector.utils",
            "image_preprocessing_detector.utils.gcs_uploader",
        ]
        for mod in modules_to_clean:
            if mod in sys.modules:
                del sys.modules[mod]

        # Mock the GCS uploader module to simulate successful import
        mock_gcs = mock.MagicMock()
        mock_gcs.upload_file_to_gcs = mock.MagicMock()
        mock_gcs.upload_dir_to_gcs = mock.MagicMock()
        mock_gcs.upload_run_to_gcs = mock.MagicMock()
        mock_gcs.download_run_from_gcs = mock.MagicMock()
        mock_gcs.list_runs = mock.MagicMock()

        with mock.patch.dict(
            "sys.modules",
            {"image_preprocessing_detector.utils.gcs_uploader": mock_gcs},
        ):
            # Import should now succeed
            import image_preprocessing_detector.utils as utils

            # Force re-evaluation by reloading
            importlib.reload(utils)

            # GCS utilities should be in __all__
            assert "upload_file_to_gcs" in utils.__all__
            assert "upload_dir_to_gcs" in utils.__all__
            assert "upload_run_to_gcs" in utils.__all__
            assert "download_run_from_gcs" in utils.__all__
            assert "list_runs" in utils.__all__

    def test_metadata_utilities_available_when_imported(self) -> None:
        """Test that metadata utilities are added to __all__ when successfully imported."""
        # Clean up any existing imports
        modules_to_clean = [
            "image_preprocessing_detector.utils",
            "image_preprocessing_detector.utils.metadata_generator",
        ]
        for mod in modules_to_clean:
            if mod in sys.modules:
                del sys.modules[mod]

        # Mock the metadata generator module to simulate successful import
        mock_metadata = mock.MagicMock()
        mock_metadata.generate_run_id = mock.MagicMock()
        mock_metadata.generate_run_metadata = mock.MagicMock()
        mock_metadata.generate_commit_hash_file = mock.MagicMock()
        mock_metadata.generate_dataset_version_file = mock.MagicMock()
        mock_metadata.generate_env_info_file = mock.MagicMock()
        mock_metadata.generate_metrics_file = mock.MagicMock()
        mock_metadata.generate_training_config_file = mock.MagicMock()

        with mock.patch.dict(
            "sys.modules",
            {"image_preprocessing_detector.utils.metadata_generator": mock_metadata},
        ):
            # Import should now succeed
            import image_preprocessing_detector.utils as utils

            # Force re-evaluation by reloading
            importlib.reload(utils)

            # Metadata utilities should be in __all__
            assert "generate_run_id" in utils.__all__
            assert "generate_run_metadata" in utils.__all__
            assert "generate_commit_hash_file" in utils.__all__
            assert "generate_dataset_version_file" in utils.__all__
            assert "generate_env_info_file" in utils.__all__
            assert "generate_metrics_file" in utils.__all__
            assert "generate_training_config_file" in utils.__all__

    def test_all_utilities_available_when_all_imported(self) -> None:
        """Test that all utilities are available when all dependencies are present."""
        # Clean up any existing imports
        modules_to_clean = [
            "image_preprocessing_detector.utils",
            "image_preprocessing_detector.utils.gcs_uploader",
            "image_preprocessing_detector.utils.metadata_generator",
        ]
        for mod in modules_to_clean:
            if mod in sys.modules:
                del sys.modules[mod]

        # Mock both modules
        mock_gcs = mock.MagicMock()
        mock_gcs.upload_file_to_gcs = mock.MagicMock()
        mock_gcs.upload_dir_to_gcs = mock.MagicMock()
        mock_gcs.upload_run_to_gcs = mock.MagicMock()
        mock_gcs.download_run_from_gcs = mock.MagicMock()
        mock_gcs.list_runs = mock.MagicMock()

        mock_metadata = mock.MagicMock()
        mock_metadata.generate_run_id = mock.MagicMock()
        mock_metadata.generate_run_metadata = mock.MagicMock()
        mock_metadata.generate_commit_hash_file = mock.MagicMock()
        mock_metadata.generate_dataset_version_file = mock.MagicMock()
        mock_metadata.generate_env_info_file = mock.MagicMock()
        mock_metadata.generate_metrics_file = mock.MagicMock()
        mock_metadata.generate_training_config_file = mock.MagicMock()

        with mock.patch.dict(
            "sys.modules",
            {
                "image_preprocessing_detector.utils.gcs_uploader": mock_gcs,
                "image_preprocessing_detector.utils.metadata_generator": mock_metadata,
            },
        ):
            # Import should now succeed
            import image_preprocessing_detector.utils as utils

            # Force re-evaluation by reloading
            importlib.reload(utils)

            # All utilities should be in __all__
            expected_functions = [
                "get_logger",
                "setup_logging",
                "upload_file_to_gcs",
                "upload_dir_to_gcs",
                "upload_run_to_gcs",
                "download_run_from_gcs",
                "list_runs",
                "generate_run_id",
                "generate_run_metadata",
                "generate_commit_hash_file",
                "generate_dataset_version_file",
                "generate_env_info_file",
                "generate_metrics_file",
                "generate_training_config_file",
            ]

            for func in expected_functions:
                assert func in utils.__all__, f"{func} should be in __all__"
