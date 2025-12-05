"""Model retraining automation module - Sprint 6.3.5.

Automates model retraining from harvested samples.

This module provides:
- RetrainingJob: Defines a retraining job specification
- RetrainingOrchestrator: Manages retraining workflow
- DatasetBuilder: Creates training datasets from approved samples
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from image_preprocessing_detector.drift.active_learning import (
    HarvestedSample,
    HarvestManifest,
    ManifestGenerator,
    PrivacyStatus,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_RETRAINING_OUTPUT_DIR = "data/retraining"
DEFAULT_DATASET_OUTPUT_DIR = "data/retraining/datasets"
DEFAULT_MIN_SAMPLES_FOR_RETRAINING = 50
DEFAULT_TRAIN_RATIO = 0.8
DEFAULT_VAL_RATIO = 0.1
DEFAULT_TEST_RATIO = 0.1


class RetrainingStatus(Enum):
    """Status of a retraining job."""

    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetrainingTrigger(Enum):
    """Trigger for retraining."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    DRIFT_DETECTED = "drift_detected"
    SAMPLE_THRESHOLD = "sample_threshold"
    PERFORMANCE_DROP = "performance_drop"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class DatasetSplit:
    """Dataset split information."""

    name: str  # train, val, test
    sample_ids: list[str] = field(default_factory=list)
    sample_paths: list[str] = field(default_factory=list)
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "sample_ids": self.sample_ids,
            "sample_paths": self.sample_paths,
            "count": self.count,
        }


@dataclass
class RetrainingDataset:
    """Dataset prepared for retraining."""

    dataset_id: str
    created_at: datetime
    source_manifests: list[str]
    train: DatasetSplit
    val: DatasetSplit
    test: DatasetSplit
    total_samples: int
    output_path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dataset_id": self.dataset_id,
            "created_at": self.created_at.isoformat(),
            "source_manifests": self.source_manifests,
            "train": self.train.to_dict(),
            "val": self.val.to_dict(),
            "test": self.test.to_dict(),
            "total_samples": self.total_samples,
            "output_path": self.output_path,
            "metadata": self.metadata,
        }


@dataclass
class RetrainingJob:
    """Retraining job specification."""

    job_id: str
    created_at: datetime
    trigger: RetrainingTrigger
    status: RetrainingStatus = RetrainingStatus.PENDING
    dataset_id: str | None = None
    model_name: str = "student"
    base_model_path: str | None = None
    output_model_path: str | None = None
    training_config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat(),
            "trigger": self.trigger.value,
            "status": self.status.value,
            "dataset_id": self.dataset_id,
            "model_name": self.model_name,
            "base_model_path": self.base_model_path,
            "output_model_path": self.output_model_path,
            "training_config": self.training_config,
            "metrics": self.metrics,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "metadata": self.metadata,
        }


@dataclass
class RetrainingConfig:
    """Configuration for retraining orchestrator."""

    output_dir: str = DEFAULT_RETRAINING_OUTPUT_DIR
    dataset_dir: str = DEFAULT_DATASET_OUTPUT_DIR
    min_samples: int = DEFAULT_MIN_SAMPLES_FOR_RETRAINING
    train_ratio: float = DEFAULT_TRAIN_RATIO
    val_ratio: float = DEFAULT_VAL_RATIO
    test_ratio: float = DEFAULT_TEST_RATIO
    auto_trigger_on_drift: bool = True
    auto_trigger_on_threshold: bool = True
    copy_sample_files: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "output_dir": self.output_dir,
            "dataset_dir": self.dataset_dir,
            "min_samples": self.min_samples,
            "train_ratio": self.train_ratio,
            "val_ratio": self.val_ratio,
            "test_ratio": self.test_ratio,
            "auto_trigger_on_drift": self.auto_trigger_on_drift,
            "auto_trigger_on_threshold": self.auto_trigger_on_threshold,
            "copy_sample_files": self.copy_sample_files,
        }


# ============================================================================
# Dataset Builder
# ============================================================================


class DatasetBuilder:
    """Builds training datasets from harvested samples."""

    def __init__(self, config: RetrainingConfig | None = None):
        """Initialize dataset builder.

        Args:
            config: Retraining configuration
        """
        self.config = config or RetrainingConfig()
        self.output_path = Path(self.config.dataset_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self._dataset_counter = 0

    def build_dataset(
        self,
        manifests: list[HarvestManifest],
        metadata: dict[str, Any] | None = None,
    ) -> RetrainingDataset | None:
        """Build a training dataset from manifests.

        Only includes approved samples.

        Args:
            manifests: List of harvest manifests
            metadata: Optional additional metadata

        Returns:
            RetrainingDataset or None if insufficient samples
        """
        # Collect all approved samples
        approved_samples: list[HarvestedSample] = []
        manifest_ids: list[str] = []

        for manifest in manifests:
            manifest_ids.append(manifest.manifest_id)
            approved_samples.extend(
                sample
                for sample in manifest.samples
                if sample.privacy_status == PrivacyStatus.APPROVED
            )

        if len(approved_samples) < self.config.min_samples:
            logger.warning(
                f"Insufficient approved samples: {len(approved_samples)} < {self.config.min_samples}"
            )
            return None

        # Generate dataset ID
        self._dataset_counter += 1
        dataset_id = (
            f"dataset_{utc_now().strftime('%Y%m%d_%H%M%S')}_{self._dataset_counter:04d}"
        )

        # Create dataset directory
        dataset_path = self.output_path / dataset_id
        dataset_path.mkdir(parents=True, exist_ok=True)

        # Split samples
        total = len(approved_samples)
        train_end = int(total * self.config.train_ratio)
        val_end = train_end + int(total * self.config.val_ratio)

        train_samples = approved_samples[:train_end]
        val_samples = approved_samples[train_end:val_end]
        test_samples = approved_samples[val_end:]

        # Create splits
        train_split = self._create_split("train", train_samples, dataset_path)
        val_split = self._create_split("val", val_samples, dataset_path)
        test_split = self._create_split("test", test_samples, dataset_path)

        # Create dataset object
        dataset = RetrainingDataset(
            dataset_id=dataset_id,
            created_at=utc_now(),
            source_manifests=manifest_ids,
            train=train_split,
            val=val_split,
            test=test_split,
            total_samples=total,
            output_path=str(dataset_path),
            metadata=metadata or {},
        )

        # Save dataset manifest
        self._save_dataset_manifest(dataset)

        logger.info(
            f"Created dataset {dataset_id} with {total} samples "
            f"(train: {train_split.count}, val: {val_split.count}, test: {test_split.count})"
        )

        return dataset

    def _create_split(
        self,
        name: str,
        samples: list[HarvestedSample],
        dataset_path: Path,
    ) -> DatasetSplit:
        """Create a dataset split.

        Args:
            name: Split name (train, val, test)
            samples: Samples for this split
            dataset_path: Base dataset path

        Returns:
            DatasetSplit object
        """
        split_path = dataset_path / name
        split_path.mkdir(exist_ok=True)

        sample_ids: list[str] = []
        sample_paths: list[str] = []

        for sample in samples:
            sample_ids.append(sample.sample_id)

            # Copy sample file if configured
            if self.config.copy_sample_files:
                source = Path(sample.source_path)
                if source.exists():
                    dest = split_path / f"{sample.sample_id}{source.suffix}"
                    try:
                        shutil.copy2(source, dest)
                        sample_paths.append(str(dest))
                    except Exception:
                        logger.exception(f"Failed to copy sample {sample.sample_id}")
                        sample_paths.append(sample.source_path)
                else:
                    # Use original path if file doesn't exist
                    sample_paths.append(sample.source_path)
            else:
                sample_paths.append(sample.source_path)

        # Save split manifest
        split_manifest = {
            "name": name,
            "count": len(samples),
            "samples": [
                {"id": sid, "path": spath}
                for sid, spath in zip(sample_ids, sample_paths, strict=True)
            ],
        }

        with open(split_path / "manifest.json", "w") as f:
            json.dump(split_manifest, f, indent=2)

        return DatasetSplit(
            name=name,
            sample_ids=sample_ids,
            sample_paths=sample_paths,
            count=len(samples),
        )

    def _save_dataset_manifest(self, dataset: RetrainingDataset) -> None:
        """Save dataset manifest to disk."""
        manifest_path = Path(dataset.output_path) / "dataset_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(dataset.to_dict(), f, indent=2)


# ============================================================================
# Retraining Orchestrator
# ============================================================================


class RetrainingOrchestrator:
    """Orchestrates model retraining workflow.

    Manages the full retraining lifecycle:
    1. Collect approved samples from manifests
    2. Build training dataset
    3. Create and track retraining jobs
    4. Update job status
    """

    def __init__(
        self,
        config: RetrainingConfig | None = None,
        manifest_generator: ManifestGenerator | None = None,
    ):
        """Initialize orchestrator.

        Args:
            config: Retraining configuration
            manifest_generator: Manifest generator for loading manifests
        """
        self.config = config or RetrainingConfig()
        self.output_path = Path(self.config.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.manifest_generator = manifest_generator
        self.dataset_builder = DatasetBuilder(self.config)

        self._jobs: dict[str, RetrainingJob] = {}
        self._job_counter = 0

        # Load existing jobs
        self._load_jobs()

    def _load_jobs(self) -> None:
        """Load existing jobs from disk."""
        jobs_dir = self.output_path / "jobs"
        if not jobs_dir.exists():
            return

        for job_file in jobs_dir.glob("*.json"):
            try:
                with open(job_file) as f:
                    data = json.load(f)
                job = self._job_from_dict(data)
                self._jobs[job.job_id] = job
            except Exception:
                logger.exception(f"Failed to load job from {job_file}")

    def _job_from_dict(self, data: dict[str, Any]) -> RetrainingJob:
        """Create job from dictionary."""
        from image_preprocessing_detector.utils.datetime_compat import ensure_aware

        return RetrainingJob(
            job_id=data["job_id"],
            created_at=ensure_aware(datetime.fromisoformat(data["created_at"])),
            trigger=RetrainingTrigger(data["trigger"]),
            status=RetrainingStatus(data["status"]),
            dataset_id=data.get("dataset_id"),
            model_name=data.get("model_name", "student"),
            base_model_path=data.get("base_model_path"),
            output_model_path=data.get("output_model_path"),
            training_config=data.get("training_config", {}),
            metrics=data.get("metrics", {}),
            error_message=data.get("error_message"),
            started_at=(
                ensure_aware(datetime.fromisoformat(data["started_at"]))
                if data.get("started_at")
                else None
            ),
            completed_at=(
                ensure_aware(datetime.fromisoformat(data["completed_at"]))
                if data.get("completed_at")
                else None
            ),
            metadata=data.get("metadata", {}),
        )

    def _save_job(self, job: RetrainingJob) -> None:
        """Save job to disk."""
        jobs_dir = self.output_path / "jobs"
        jobs_dir.mkdir(exist_ok=True)

        job_path = jobs_dir / f"{job.job_id}.json"
        with open(job_path, "w") as f:
            json.dump(job.to_dict(), f, indent=2)

    def create_job(
        self,
        trigger: RetrainingTrigger,
        model_name: str = "student",
        base_model_path: str | None = None,
        training_config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RetrainingJob:
        """Create a new retraining job.

        Args:
            trigger: Trigger for retraining
            model_name: Name of model to retrain
            base_model_path: Path to base model (for fine-tuning)
            training_config: Training hyperparameters
            metadata: Additional metadata

        Returns:
            RetrainingJob object
        """
        self._job_counter += 1
        job_id = (
            f"retrain_{utc_now().strftime('%Y%m%d_%H%M%S')}_{self._job_counter:04d}"
        )

        job = RetrainingJob(
            job_id=job_id,
            created_at=utc_now(),
            trigger=trigger,
            model_name=model_name,
            base_model_path=base_model_path,
            training_config=training_config or {},
            metadata=metadata or {},
        )

        self._jobs[job_id] = job
        self._save_job(job)

        logger.info(f"Created retraining job {job_id} for model {model_name}")

        return job

    def prepare_job(
        self,
        job: RetrainingJob,
        manifests: list[HarvestManifest],
    ) -> bool:
        """Prepare a job by building the dataset.

        Args:
            job: Retraining job
            manifests: Harvest manifests to use

        Returns:
            True if preparation succeeded
        """
        job.status = RetrainingStatus.PREPARING
        self._save_job(job)

        try:
            dataset = self.dataset_builder.build_dataset(
                manifests,
                metadata={"job_id": job.job_id},
            )

            if dataset is None:
                job.status = RetrainingStatus.FAILED
                job.error_message = "Insufficient approved samples for retraining"
                self._save_job(job)
                return False

            job.dataset_id = dataset.dataset_id
            job.metadata["dataset_path"] = dataset.output_path
            job.metadata["train_samples"] = dataset.train.count
            job.metadata["val_samples"] = dataset.val.count
            job.metadata["test_samples"] = dataset.test.count
            self._save_job(job)

            logger.info(f"Job {job.job_id} prepared with dataset {dataset.dataset_id}")

        except Exception as e:
            job.status = RetrainingStatus.FAILED
            job.error_message = str(e)
            self._save_job(job)
            logger.exception(f"Failed to prepare job {job.job_id}")
            return False

        else:
            return True

    def start_job(self, job: RetrainingJob) -> bool:
        """Start a retraining job.

        Note: Actual training execution would integrate with Modal or
        other training infrastructure. This method marks the job as
        started and returns training configuration.

        Args:
            job: Retraining job to start

        Returns:
            True if job started successfully
        """
        if job.dataset_id is None:
            logger.error(f"Job {job.job_id} has no dataset, cannot start")
            return False

        job.status = RetrainingStatus.TRAINING
        job.started_at = utc_now()
        self._save_job(job)

        logger.info(f"Started retraining job {job.job_id}")

        # In production, this would trigger Modal training job
        # For now, we just mark it as training

        return True

    def complete_job(
        self,
        job: RetrainingJob,
        success: bool,
        metrics: dict[str, float] | None = None,
        output_model_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Mark a job as completed.

        Args:
            job: Retraining job
            success: Whether training succeeded
            metrics: Training metrics (loss, accuracy, etc.)
            output_model_path: Path to trained model
            error_message: Error message if failed
        """
        job.completed_at = utc_now()

        if success:
            job.status = RetrainingStatus.COMPLETED
            job.metrics = metrics or {}
            job.output_model_path = output_model_path
        else:
            job.status = RetrainingStatus.FAILED
            job.error_message = error_message

        self._save_job(job)

        logger.info(f"Job {job.job_id} completed with status {job.status.value}")

    def cancel_job(self, job: RetrainingJob, reason: str = "") -> None:
        """Cancel a retraining job.

        Args:
            job: Job to cancel
            reason: Reason for cancellation
        """
        job.status = RetrainingStatus.CANCELLED
        job.error_message = reason or "Cancelled by user"
        job.completed_at = utc_now()
        self._save_job(job)

        logger.info(f"Cancelled job {job.job_id}: {reason}")

    def get_job(self, job_id: str) -> RetrainingJob | None:
        """Get a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            RetrainingJob or None
        """
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: RetrainingStatus | None = None,
        limit: int = 100,
    ) -> list[RetrainingJob]:
        """List retraining jobs.

        Args:
            status: Filter by status
            limit: Maximum jobs to return

        Returns:
            List of jobs, newest first
        """
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by creation time, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def get_pending_sample_count(self) -> int:
        """Get count of approved samples not yet used in retraining.

        Returns:
            Number of pending samples
        """
        if not self.manifest_generator:
            return 0

        # Get all manifests
        manifests = self.manifest_generator.list_manifests()

        # Count approved samples not in any dataset
        used_sample_ids: set[str] = set()
        for job in self._jobs.values():
            if job.dataset_id and job.metadata.get("sample_ids"):
                used_sample_ids.update(job.metadata["sample_ids"])

        pending_count = 0
        for manifest_path in manifests:
            manifest = self.manifest_generator.load_manifest(manifest_path)
            for sample in manifest.samples:
                if (
                    sample.privacy_status == PrivacyStatus.APPROVED
                    and sample.sample_id not in used_sample_ids
                ):
                    pending_count += 1

        return pending_count

    def should_trigger_retraining(self) -> tuple[bool, RetrainingTrigger | None]:
        """Check if retraining should be triggered.

        Returns:
            Tuple of (should_trigger, trigger_reason)
        """
        if not self.config.auto_trigger_on_threshold:
            return False, None

        pending = self.get_pending_sample_count()
        if pending >= self.config.min_samples:
            return True, RetrainingTrigger.SAMPLE_THRESHOLD

        return False, None


# ============================================================================
# Convenience Functions
# ============================================================================


def create_retraining_orchestrator(
    output_dir: str = DEFAULT_RETRAINING_OUTPUT_DIR,
    manifest_dir: str | None = None,
    min_samples: int = DEFAULT_MIN_SAMPLES_FOR_RETRAINING,
) -> RetrainingOrchestrator:
    """Create a retraining orchestrator.

    Args:
        output_dir: Output directory for retraining artifacts
        manifest_dir: Directory containing harvest manifests
        min_samples: Minimum samples required for retraining

    Returns:
        Configured RetrainingOrchestrator
    """
    config = RetrainingConfig(
        output_dir=output_dir,
        min_samples=min_samples,
    )

    manifest_generator = None
    if manifest_dir:
        manifest_generator = ManifestGenerator(manifest_dir)

    return RetrainingOrchestrator(config, manifest_generator)


__all__ = [
    "DEFAULT_DATASET_OUTPUT_DIR",
    "DEFAULT_MIN_SAMPLES_FOR_RETRAINING",
    "DEFAULT_RETRAINING_OUTPUT_DIR",
    "DEFAULT_TEST_RATIO",
    "DEFAULT_TRAIN_RATIO",
    "DEFAULT_VAL_RATIO",
    "DatasetBuilder",
    "DatasetSplit",
    "RetrainingConfig",
    "RetrainingDataset",
    "RetrainingJob",
    "RetrainingOrchestrator",
    "RetrainingStatus",
    "RetrainingTrigger",
    "create_retraining_orchestrator",
]
