"""Unit tests for retraining automation module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from image_preprocessing_detector.drift.active_learning import (
    HarvestManifest,
    HarvestedSample,
    HarvestReason,
    ManifestGenerator,
    PrivacyStatus,
)
from image_preprocessing_detector.drift.retraining import (
    DatasetBuilder,
    RetrainingConfig,
    RetrainingJob,
    RetrainingOrchestrator,
    RetrainingStatus,
    RetrainingTrigger,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_manifest(temp_dir: Path) -> HarvestManifest:
    """Create a sample manifest with approved samples."""
    samples = []
    for i in range(100):
        sample = HarvestedSample(
            sample_id=f"sample_{i:04d}",
            source_path=str(temp_dir / f"sample_{i:04d}.png"),
            harvest_time=utc_now(),
            harvest_reason=HarvestReason.HIGH_ENTROPY,
            entropy=0.8,
            privacy_status=PrivacyStatus.APPROVED if i < 80 else PrivacyStatus.PENDING,
        )
        samples.append(sample)
        # Create dummy file
        (temp_dir / f"sample_{i:04d}.png").touch()

    return HarvestManifest(
        manifest_id="test_manifest",
        created_at=utc_now(),
        samples=samples,
        total_count=len(samples),
        approved_count=80,
        pending_count=20,
    )


class TestRetrainingConfig:
    """Tests for RetrainingConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = RetrainingConfig()

        assert config.min_samples == 50
        assert config.train_ratio == 0.8
        assert config.val_ratio == 0.1
        assert config.test_ratio == 0.1
        assert config.auto_trigger_on_drift is True

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = RetrainingConfig(
            min_samples=100,
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15,
        )

        assert config.min_samples == 100
        assert config.train_ratio == 0.7

    def test_config_to_dict(self) -> None:
        """Test configuration serialization."""
        config = RetrainingConfig()
        data = config.to_dict()

        assert "min_samples" in data
        assert "train_ratio" in data
        assert data["min_samples"] == 50


class TestDatasetBuilder:
    """Tests for DatasetBuilder."""

    def test_build_dataset(self, temp_dir: Path, sample_manifest: HarvestManifest) -> None:
        """Test building a dataset from manifest."""
        config = RetrainingConfig(
            dataset_dir=str(temp_dir / "datasets"),
            min_samples=10,
            copy_sample_files=False,  # Skip file copy for test
        )
        builder = DatasetBuilder(config)

        dataset = builder.build_dataset([sample_manifest])

        assert dataset is not None
        assert dataset.total_samples == 80  # Only approved
        assert dataset.train.count > 0
        assert dataset.val.count > 0
        assert dataset.test.count > 0

    def test_build_dataset_insufficient_samples(self, temp_dir: Path) -> None:
        """Test building dataset with insufficient samples."""
        config = RetrainingConfig(
            dataset_dir=str(temp_dir / "datasets"),
            min_samples=100,
        )
        builder = DatasetBuilder(config)

        # Create manifest with few samples
        samples = [
            HarvestedSample(
                sample_id=f"sample_{i}",
                source_path=f"/tmp/sample_{i}.png",
                harvest_time=utc_now(),
                harvest_reason=HarvestReason.HIGH_ENTROPY,
                privacy_status=PrivacyStatus.APPROVED,
            )
            for i in range(10)
        ]

        manifest = HarvestManifest(
            manifest_id="small_manifest",
            created_at=utc_now(),
            samples=samples,
            total_count=10,
            approved_count=10,
        )

        dataset = builder.build_dataset([manifest])

        assert dataset is None  # Not enough samples

    def test_dataset_split_ratios(self, temp_dir: Path, sample_manifest: HarvestManifest) -> None:
        """Test dataset split ratios are correct."""
        config = RetrainingConfig(
            dataset_dir=str(temp_dir / "datasets"),
            min_samples=10,
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            copy_sample_files=False,
        )
        builder = DatasetBuilder(config)

        dataset = builder.build_dataset([sample_manifest])

        total = dataset.total_samples
        train_expected = int(total * 0.8)
        val_expected = int(total * 0.1)

        assert dataset.train.count == train_expected
        assert dataset.val.count == val_expected


class TestRetrainingJob:
    """Tests for RetrainingJob."""

    def test_job_creation(self) -> None:
        """Test creating a retraining job."""
        job = RetrainingJob(
            job_id="test_job",
            created_at=utc_now(),
            trigger=RetrainingTrigger.MANUAL,
            model_name="student",
        )

        assert job.job_id == "test_job"
        assert job.status == RetrainingStatus.PENDING
        assert job.trigger == RetrainingTrigger.MANUAL

    def test_job_to_dict(self) -> None:
        """Test job serialization."""
        job = RetrainingJob(
            job_id="test_job",
            created_at=utc_now(),
            trigger=RetrainingTrigger.DRIFT_DETECTED,
        )

        data = job.to_dict()

        assert data["job_id"] == "test_job"
        assert data["status"] == "pending"
        assert data["trigger"] == "drift_detected"


class TestRetrainingOrchestrator:
    """Tests for RetrainingOrchestrator."""

    def test_orchestrator_creation(self, temp_dir: Path) -> None:
        """Test creating orchestrator."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        assert orchestrator.config == config
        assert len(orchestrator._jobs) == 0

    def test_create_job(self, temp_dir: Path) -> None:
        """Test creating a retraining job."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(
            trigger=RetrainingTrigger.MANUAL,
            model_name="student",
        )

        assert job.job_id is not None
        assert job.status == RetrainingStatus.PENDING
        assert job.model_name == "student"

    def test_prepare_job(self, temp_dir: Path, sample_manifest: HarvestManifest) -> None:
        """Test preparing a job with dataset."""
        config = RetrainingConfig(
            output_dir=str(temp_dir / "retraining"),
            dataset_dir=str(temp_dir / "datasets"),
            min_samples=10,
            copy_sample_files=False,
        )
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        success = orchestrator.prepare_job(job, [sample_manifest])

        assert success is True
        assert job.dataset_id is not None

    def test_start_job(self, temp_dir: Path, sample_manifest: HarvestManifest) -> None:
        """Test starting a job."""
        config = RetrainingConfig(
            output_dir=str(temp_dir / "retraining"),
            dataset_dir=str(temp_dir / "datasets"),
            min_samples=10,
            copy_sample_files=False,
        )
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        orchestrator.prepare_job(job, [sample_manifest])
        success = orchestrator.start_job(job)

        assert success is True
        assert job.status == RetrainingStatus.TRAINING
        assert job.started_at is not None

    def test_complete_job_success(self, temp_dir: Path) -> None:
        """Test completing a job successfully."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        job.dataset_id = "test_dataset"

        orchestrator.complete_job(
            job,
            success=True,
            metrics={"loss": 0.1, "accuracy": 0.95},
            output_model_path="/models/new_model.pth",
        )

        assert job.status == RetrainingStatus.COMPLETED
        assert job.metrics["accuracy"] == 0.95
        assert job.completed_at is not None

    def test_complete_job_failure(self, temp_dir: Path) -> None:
        """Test completing a job with failure."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)

        orchestrator.complete_job(
            job,
            success=False,
            error_message="Training failed: OOM",
        )

        assert job.status == RetrainingStatus.FAILED
        assert job.error_message == "Training failed: OOM"

    def test_cancel_job(self, temp_dir: Path) -> None:
        """Test cancelling a job."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        orchestrator.cancel_job(job, "No longer needed")

        assert job.status == RetrainingStatus.CANCELLED
        assert "No longer needed" in str(job.error_message)

    def test_list_jobs(self, temp_dir: Path) -> None:
        """Test listing jobs."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        # Create multiple jobs
        for _ in range(5):
            orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)

        jobs = orchestrator.list_jobs()

        assert len(jobs) == 5

    def test_list_jobs_filtered(self, temp_dir: Path) -> None:
        """Test listing jobs with status filter."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        # Create jobs with different statuses
        job1 = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        job2 = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        orchestrator.cancel_job(job2)

        pending = orchestrator.list_jobs(status=RetrainingStatus.PENDING)
        cancelled = orchestrator.list_jobs(status=RetrainingStatus.CANCELLED)

        assert len(pending) == 1
        assert len(cancelled) == 1

    def test_get_job(self, temp_dir: Path) -> None:
        """Test getting a job by ID."""
        config = RetrainingConfig(output_dir=str(temp_dir / "retraining"))
        orchestrator = RetrainingOrchestrator(config)

        job = orchestrator.create_job(trigger=RetrainingTrigger.MANUAL)
        retrieved = orchestrator.get_job(job.job_id)

        assert retrieved is not None
        assert retrieved.job_id == job.job_id


class TestRetrainingTriggers:
    """Tests for retraining triggers."""

    def test_all_trigger_types(self) -> None:
        """Test all trigger types are valid."""
        triggers = [
            RetrainingTrigger.MANUAL,
            RetrainingTrigger.SCHEDULED,
            RetrainingTrigger.DRIFT_DETECTED,
            RetrainingTrigger.SAMPLE_THRESHOLD,
            RetrainingTrigger.PERFORMANCE_DROP,
        ]

        for trigger in triggers:
            job = RetrainingJob(
                job_id="test",
                created_at=utc_now(),
                trigger=trigger,
            )
            assert job.trigger == trigger


class TestRetrainingStatus:
    """Tests for retraining status."""

    def test_all_status_types(self) -> None:
        """Test all status types."""
        statuses = [
            RetrainingStatus.PENDING,
            RetrainingStatus.PREPARING,
            RetrainingStatus.TRAINING,
            RetrainingStatus.VALIDATING,
            RetrainingStatus.COMPLETED,
            RetrainingStatus.FAILED,
            RetrainingStatus.CANCELLED,
        ]

        for status in statuses:
            job = RetrainingJob(
                job_id="test",
                created_at=utc_now(),
                trigger=RetrainingTrigger.MANUAL,
                status=status,
            )
            assert job.status == status
