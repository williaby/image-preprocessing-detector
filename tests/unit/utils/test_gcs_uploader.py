"""Unit tests for gcs_uploader.py.

Tests cover:
- Directory upload functionality
- Single file upload
- Training run upload with canonical structure
- Run listing
- Run download
- Error handling for missing files/directories
"""

import pytest

# Skip entire module if google-cloud-storage is not available
pytest.importorskip(
    "google.cloud.storage", reason="google-cloud-storage required for GCS tests"
)

from pathlib import Path
from unittest.mock import MagicMock, patch

import image_preprocessing_detector.utils.gcs_uploader as _gcs_module
from image_preprocessing_detector.utils.gcs_uploader import (
    GCSRunConfig,
    download_run_from_gcs,
    list_runs,
    upload_dir_to_gcs,
    upload_file_to_gcs,
    upload_run_to_gcs,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_storage_client() -> MagicMock:
    """Create a mock GCS storage client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    return mock_client


@pytest.fixture
def sample_directory(tmp_path: Path) -> Path:
    """Create a sample directory with test files."""
    # Create directory structure
    (tmp_path / "checkpoints").mkdir()
    (tmp_path / "logs").mkdir()

    # Create sample files
    (tmp_path / "model.pt").write_bytes(b"model weights" * 100)
    (tmp_path / "config.yaml").write_text("learning_rate: 0.001")
    (tmp_path / "checkpoints" / "epoch_10.pt").write_bytes(b"checkpoint" * 50)
    (tmp_path / "logs" / "train.log").write_text("epoch 1: loss=0.5\nepoch 2: loss=0.4")

    return tmp_path


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample file for upload."""
    file_path = tmp_path / "test_model.pt"
    file_path.write_bytes(b"test model weights" * 1000)
    return file_path


# =============================================================================
# upload_dir_to_gcs Tests
# =============================================================================


@pytest.mark.unit
class TestUploadDirToGcs:
    """Tests for upload_dir_to_gcs function."""

    def test_uploads_all_files(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test uploads all files in directory."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            stats = upload_dir_to_gcs(
                local_dir=str(sample_directory),
                bucket_name="test-bucket",
                gcs_prefix="test/prefix",
                verbose=False,
            )

            assert stats["files_uploaded"] == 4
            assert stats["total_bytes"] > 0

    def test_preserves_directory_structure(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test preserves directory structure in GCS path."""
        uploaded_paths = []

        def capture_blob_name(name: str) -> MagicMock:
            uploaded_paths.append(name)
            return MagicMock()

        mock_storage_client.bucket.return_value.blob.side_effect = capture_blob_name

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            upload_dir_to_gcs(
                local_dir=str(sample_directory),
                bucket_name="test-bucket",
                gcs_prefix="project/model",
                verbose=False,
            )

        # Check that nested paths are preserved
        assert any("checkpoints/epoch_10.pt" in path for path in uploaded_paths)
        assert any("logs/train.log" in path for path in uploaded_paths)

    def test_raises_for_nonexistent_directory(self) -> None:
        """Test raises ValueError for nonexistent directory."""
        with pytest.raises(ValueError, match="does not exist"):
            upload_dir_to_gcs(
                local_dir="/nonexistent/path",
                bucket_name="test-bucket",
                gcs_prefix="test",
            )

    def test_returns_correct_stats(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test returns correct upload statistics."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            stats = upload_dir_to_gcs(
                local_dir=str(sample_directory),
                bucket_name="test-bucket",
                gcs_prefix="test",
                verbose=False,
            )

            assert "files_uploaded" in stats
            assert "total_bytes" in stats
            assert isinstance(stats["files_uploaded"], int)
            assert isinstance(stats["total_bytes"], int)

    def test_skips_directories(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test skips directory entries (only uploads files)."""
        upload_calls = []

        def track_upload(_filename: str) -> None:
            upload_calls.append(_filename)

        mock_blob = MagicMock()
        mock_blob.upload_from_filename.side_effect = track_upload
        mock_storage_client.bucket.return_value.blob.return_value = mock_blob

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            stats = upload_dir_to_gcs(
                local_dir=str(sample_directory),
                bucket_name="test-bucket",
                gcs_prefix="test",
                verbose=False,
            )

        # Should only upload files, not directories
        assert stats["files_uploaded"] == 4


# =============================================================================
# upload_file_to_gcs Tests
# =============================================================================


@pytest.mark.unit
class TestUploadFileToGcs:
    """Tests for upload_file_to_gcs function."""

    def test_uploads_single_file(
        self, sample_file: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test uploads a single file to GCS."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            result = upload_file_to_gcs(
                local_file=str(sample_file),
                bucket_name="test-bucket",
                gcs_path="models/test_model.pt",
                verbose=False,
            )

            assert result == "gs://test-bucket/models/test_model.pt"
            mock_storage_client.bucket.return_value.blob.assert_called_with(
                "models/test_model.pt"
            )

    def test_raises_for_nonexistent_file(self) -> None:
        """Test raises ValueError for nonexistent file."""
        with pytest.raises(ValueError, match="does not exist"):
            upload_file_to_gcs(
                local_file="/nonexistent/file.pt",
                bucket_name="test-bucket",
                gcs_path="test.pt",
            )

    def test_returns_full_gcs_path(
        self, sample_file: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test returns full GCS path with gs:// prefix."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            result = upload_file_to_gcs(
                local_file=str(sample_file),
                bucket_name="my-bucket",
                gcs_path="path/to/file.pt",
                verbose=False,
            )

            assert result.startswith("gs://")
            assert "my-bucket" in result
            assert "path/to/file.pt" in result


# =============================================================================
# upload_run_to_gcs Tests
# =============================================================================


@pytest.mark.unit
class TestUploadRunToGcs:
    """Tests for upload_run_to_gcs function."""

    def test_constructs_canonical_path(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test constructs canonical GCS path structure."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="rag-pipeline-models",
                project_name="image-preprocessing-detector",
                model_name="resnet50_teacher",
            )
            result = upload_run_to_gcs(
                config=config,
                run_id="2025-11-15T01-20Z_run-abc123",
                local_dir=str(sample_directory),
                verbose=False,
            )

            expected = (
                "gs://rag-pipeline-models/image-preprocessing-detector/"
                "resnet50_teacher/runs/2025-11-15T01-20Z_run-abc123"
            )
            assert result == expected

    def test_uploads_all_artifacts(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test uploads all training artifacts."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="test-project",
                model_name="test-model",
            )
            result = upload_run_to_gcs(
                config=config,
                run_id="test-run",
                local_dir=str(sample_directory),
                verbose=False,
            )

            assert result is not None
            # Verify bucket and blob methods were called
            assert mock_storage_client.bucket.called

    def test_returns_gcs_path(
        self, sample_directory: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test returns the full GCS path."""
        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="bucket",
                project_name="project",
                model_name="model",
            )
            result = upload_run_to_gcs(
                config=config,
                run_id="run-123",
                local_dir=str(sample_directory),
                verbose=False,
            )

            assert result.startswith("gs://")
            assert "bucket" in result
            assert "project" in result
            assert "model" in result
            assert "run-123" in result


# =============================================================================
# list_runs Tests
# =============================================================================


@pytest.mark.unit
class TestListRuns:
    """Tests for list_runs function."""

    def test_lists_all_runs(self, mock_storage_client: MagicMock) -> None:
        """Test lists all runs for a model."""
        # Mock the blob listing
        mock_blobs = MagicMock()
        mock_blobs.prefixes = [
            "project/model/runs/2025-11-15T01-20Z_run-abc123/",
            "project/model/runs/2025-11-14T10-00Z_run-def456/",
            "project/model/runs/2025-11-13T08-30Z_run-ghi789/",
        ]
        mock_storage_client.bucket.return_value.list_blobs.return_value = mock_blobs

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            runs = list_runs(config=config)

            assert len(runs) == 3
            assert "2025-11-15T01-20Z_run-abc123" in runs
            assert "2025-11-14T10-00Z_run-def456" in runs

    def test_sorts_newest_first(self, mock_storage_client: MagicMock) -> None:
        """Test runs are sorted newest first."""
        mock_blobs = MagicMock()
        mock_blobs.prefixes = [
            "project/model/runs/2025-11-13T08-30Z_run-old/",
            "project/model/runs/2025-11-15T01-20Z_run-new/",
            "project/model/runs/2025-11-14T10-00Z_run-mid/",
        ]
        mock_storage_client.bucket.return_value.list_blobs.return_value = mock_blobs

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            runs = list_runs(config=config)

            # Should be sorted newest first
            assert runs[0] == "2025-11-15T01-20Z_run-new"
            assert runs[2] == "2025-11-13T08-30Z_run-old"

    def test_limits_results(self, mock_storage_client: MagicMock) -> None:
        """Test max_results limits the number of runs returned."""
        mock_blobs = MagicMock()
        mock_blobs.prefixes = [
            f"project/model/runs/2025-11-{i:02d}T00-00Z_run-{i}/" for i in range(1, 11)
        ]
        mock_storage_client.bucket.return_value.list_blobs.return_value = mock_blobs

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            runs = list_runs(config=config, max_results=3)

            assert len(runs) == 3

    def test_returns_empty_for_no_runs(self, mock_storage_client: MagicMock) -> None:
        """Test returns empty list when no runs exist."""
        mock_blobs = MagicMock()
        mock_blobs.prefixes = []
        mock_storage_client.bucket.return_value.list_blobs.return_value = mock_blobs

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            runs = list_runs(config=config)

            assert runs == []


# =============================================================================
# download_run_from_gcs Tests
# =============================================================================


@pytest.mark.unit
class TestDownloadRunFromGcs:
    """Tests for download_run_from_gcs function."""

    def test_downloads_all_files(
        self, tmp_path: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test downloads all files from a run."""
        # Mock blobs to download
        mock_blob1 = MagicMock()
        mock_blob1.name = "project/model/runs/run-123/model.pt"
        mock_blob1.size = 1000

        mock_blob2 = MagicMock()
        mock_blob2.name = "project/model/runs/run-123/config.yaml"
        mock_blob2.size = 100

        mock_storage_client.bucket.return_value.list_blobs.return_value = [
            mock_blob1,
            mock_blob2,
        ]

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            result = download_run_from_gcs(
                config=config,
                run_id="run-123",
                local_dir=str(tmp_path),
                verbose=False,
            )

            assert "run-123" in result
            assert mock_blob1.download_to_filename.called
            assert mock_blob2.download_to_filename.called

    def test_creates_local_directory(
        self, tmp_path: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test creates local directory structure."""
        mock_storage_client.bucket.return_value.list_blobs.return_value = []

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            result = download_run_from_gcs(
                config=config,
                run_id="new-run",
                local_dir=str(tmp_path),
                verbose=False,
            )

            # Directory should be created
            assert Path(result).exists()

    def test_preserves_nested_structure(
        self, tmp_path: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test preserves nested directory structure when downloading."""
        # Mock blob with nested path
        mock_blob = MagicMock()
        mock_blob.name = "project/model/runs/run-123/checkpoints/epoch_10.pt"
        mock_blob.size = 500

        mock_storage_client.bucket.return_value.list_blobs.return_value = [mock_blob]

        download_paths = []

        def capture_download(path: str) -> None:
            download_paths.append(path)
            # Create the file
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).touch()

        mock_blob.download_to_filename.side_effect = capture_download

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            download_run_from_gcs(
                config=config,
                run_id="run-123",
                local_dir=str(tmp_path),
                verbose=False,
            )

        # Check nested structure was preserved
        assert any("checkpoints" in path for path in download_paths)

    def test_returns_local_path(
        self, tmp_path: Path, mock_storage_client: MagicMock
    ) -> None:
        """Test returns local path to downloaded run."""
        mock_storage_client.bucket.return_value.list_blobs.return_value = []

        with patch.object(
            _gcs_module.storage,
            "Client",
            return_value=mock_storage_client,
        ):
            config = GCSRunConfig(
                bucket_name="test-bucket",
                project_name="project",
                model_name="model",
            )
            result = download_run_from_gcs(
                config=config,
                run_id="my-run-id",
                local_dir=str(tmp_path),
                verbose=False,
            )

            assert result.endswith("my-run-id")


# =============================================================================
# Parametrized Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    ("project", "model", "run_id"),
    [
        (
            "image-preprocessing-detector",
            "resnet50_teacher",
            "2025-11-15T01-20Z_run-abc",
        ),
        ("ocr-pipeline", "bert_base", "2025-01-01T00-00Z_run-xyz"),
        ("my-project", "my-model", "simple-run-id"),
    ],
)
def test_canonical_path_construction(
    sample_directory: Path,
    mock_storage_client: MagicMock,
    project: str,
    model: str,
    run_id: str,
) -> None:
    """Test canonical path is correctly constructed for various inputs."""
    with patch.object(
        _gcs_module.storage,
        "Client",
        return_value=mock_storage_client,
    ):
        config = GCSRunConfig(
            bucket_name="bucket",
            project_name=project,
            model_name=model,
        )
        result = upload_run_to_gcs(
            config=config,
            run_id=run_id,
            local_dir=str(sample_directory),
            verbose=False,
        )

        assert project in result
        assert model in result
        assert run_id in result
        assert "/runs/" in result


@pytest.mark.unit
@pytest.mark.parametrize(
    ("bucket_name", "expected_prefix"),
    [
        ("my-bucket", "gs://my-bucket/"),
        ("rag-pipeline-models", "gs://rag-pipeline-models/"),
        ("test-bucket-123", "gs://test-bucket-123/"),
    ],
)
def test_gcs_path_format(
    sample_file: Path,
    mock_storage_client: MagicMock,
    bucket_name: str,
    expected_prefix: str,
) -> None:
    """Test GCS path starts with correct gs:// prefix."""
    with patch.object(
        _gcs_module.storage,
        "Client",
        return_value=mock_storage_client,
    ):
        result = upload_file_to_gcs(
            local_file=str(sample_file),
            bucket_name=bucket_name,
            gcs_path="test.pt",
            verbose=False,
        )

        assert result.startswith(expected_prefix)
