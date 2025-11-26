"""Active learning loop stub - Sprint 6.3.4.

Harvests high-entropy/low-agreement samples for re-training.

This module provides:
- SampleHarvester: Identifies and stores valuable samples
- ManifestGenerator: Creates metadata manifest for re-training
- PrivacyChecker: Validates samples against privacy requirements
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from image_preprocessing_detector.utils.datetime_compat import ensure_aware, utc_now

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_OUTPUT_DIR = "data/drift_samples"
DEFAULT_ENTROPY_THRESHOLD = 0.7  # High entropy indicates uncertainty
DEFAULT_AGREEMENT_THRESHOLD = 0.5  # Low agreement between models
DEFAULT_MAX_SAMPLES_PER_BATCH = 100
DEFAULT_RETENTION_DAYS = 90


class HarvestReason(Enum):
    """Reasons for harvesting a sample."""

    HIGH_ENTROPY = "high_entropy"
    LOW_AGREEMENT = "low_agreement"
    TEACHER_ESCALATION = "teacher_escalation"
    QUALITY_OUTLIER = "quality_outlier"
    DRIFT_DETECTED = "drift_detected"
    MANUAL_SELECTION = "manual_selection"


class PrivacyStatus(Enum):
    """Privacy review status for samples."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class HarvestedSample:
    """Metadata for a harvested sample."""

    sample_id: str
    source_path: str
    harvest_time: datetime
    harvest_reason: HarvestReason
    entropy: float | None = None
    agreement_score: float | None = None
    model_predictions: dict[str, float] = field(default_factory=dict)
    quality_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    privacy_status: PrivacyStatus = PrivacyStatus.PENDING
    privacy_notes: str = ""
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sample_id": self.sample_id,
            "source_path": self.source_path,
            "harvest_time": self.harvest_time.isoformat(),
            "harvest_reason": self.harvest_reason.value,
            "entropy": self.entropy,
            "agreement_score": self.agreement_score,
            "model_predictions": self.model_predictions,
            "quality_scores": self.quality_scores,
            "metadata": self.metadata,
            "privacy_status": self.privacy_status.value,
            "privacy_notes": self.privacy_notes,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarvestedSample:
        """Create from dictionary."""
        return cls(
            sample_id=data["sample_id"],
            source_path=data["source_path"],
            harvest_time=ensure_aware(datetime.fromisoformat(data["harvest_time"])),
            harvest_reason=HarvestReason(data["harvest_reason"]),
            entropy=data.get("entropy"),
            agreement_score=data.get("agreement_score"),
            model_predictions=data.get("model_predictions", {}),
            quality_scores=data.get("quality_scores", {}),
            metadata=data.get("metadata", {}),
            privacy_status=PrivacyStatus(data.get("privacy_status", "pending")),
            privacy_notes=data.get("privacy_notes", ""),
            checksum=data.get("checksum", ""),
        )


@dataclass
class HarvestManifest:
    """Manifest for a batch of harvested samples."""

    manifest_id: str
    created_at: datetime
    samples: list[HarvestedSample]
    total_count: int
    approved_count: int = 0
    rejected_count: int = 0
    pending_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "manifest_id": self.manifest_id,
            "created_at": self.created_at.isoformat(),
            "samples": [s.to_dict() for s in self.samples],
            "total_count": self.total_count,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "pending_count": self.pending_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarvestManifest:
        """Create from dictionary."""
        samples = [HarvestedSample.from_dict(s) for s in data.get("samples", [])]
        return cls(
            manifest_id=data["manifest_id"],
            created_at=ensure_aware(datetime.fromisoformat(data["created_at"])),
            samples=samples,
            total_count=data["total_count"],
            approved_count=data.get("approved_count", 0),
            rejected_count=data.get("rejected_count", 0),
            pending_count=data.get("pending_count", 0),
            metadata=data.get("metadata", {}),
        )

    def update_counts(self) -> None:
        """Update status counts from samples."""
        self.total_count = len(self.samples)
        self.approved_count = sum(
            1 for s in self.samples if s.privacy_status == PrivacyStatus.APPROVED
        )
        self.rejected_count = sum(
            1 for s in self.samples if s.privacy_status == PrivacyStatus.REJECTED
        )
        self.pending_count = sum(
            1
            for s in self.samples
            if s.privacy_status
            in [PrivacyStatus.PENDING, PrivacyStatus.REQUIRES_REVIEW]
        )


@dataclass
class HarvesterConfig:
    """Configuration for sample harvester."""

    output_dir: str = DEFAULT_OUTPUT_DIR
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD
    agreement_threshold: float = DEFAULT_AGREEMENT_THRESHOLD
    max_samples_per_batch: int = DEFAULT_MAX_SAMPLES_PER_BATCH
    copy_sample_files: bool = True
    compute_checksums: bool = True
    auto_privacy_check: bool = True
    retention_days: int = DEFAULT_RETENTION_DAYS

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "output_dir": self.output_dir,
            "entropy_threshold": self.entropy_threshold,
            "agreement_threshold": self.agreement_threshold,
            "max_samples_per_batch": self.max_samples_per_batch,
            "copy_sample_files": self.copy_sample_files,
            "compute_checksums": self.compute_checksums,
            "auto_privacy_check": self.auto_privacy_check,
            "retention_days": self.retention_days,
        }


# ============================================================================
# Privacy Checker
# ============================================================================


class PrivacyChecker:
    """Validates samples against privacy requirements.

    This is a stub implementation. In production, this would integrate
    with actual privacy scanning and PII detection systems.
    """

    # Keywords that might indicate PII
    PII_INDICATORS = [
        "ssn",
        "social_security",
        "passport",
        "driver_license",
        "credit_card",
        "bank_account",
        "medical_record",
        "health_record",
        "personal_id",
        "national_id",
    ]

    # File patterns that require review
    SENSITIVE_PATTERNS = [
        "**/personal/**",
        "**/private/**",
        "**/confidential/**",
        "**/pii/**",
        "**/hipaa/**",
    ]

    def __init__(
        self, custom_rules: list[Callable[[HarvestedSample], bool]] | None = None
    ):
        """Initialize privacy checker.

        Args:
            custom_rules: Optional list of custom validation functions
        """
        self.custom_rules = custom_rules or []

    def check_sample(self, sample: HarvestedSample) -> tuple[PrivacyStatus, str]:
        """Check sample against privacy requirements.

        Args:
            sample: Sample to check

        Returns:
            Tuple of (status, notes)
        """
        notes = []

        # Check source path for sensitive patterns
        source_lower = sample.source_path.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if any(
                keyword in source_lower
                for keyword in pattern.replace("**/", "").replace("/**", "").split("/")
                if keyword
            ):
                notes.append(f"Path matches sensitive pattern: {pattern}")
                return PrivacyStatus.REQUIRES_REVIEW, "; ".join(notes)

        # Check metadata for PII indicators
        metadata_str = json.dumps(sample.metadata).lower()
        for indicator in self.PII_INDICATORS:
            if indicator in metadata_str:
                notes.append(f"Metadata contains PII indicator: {indicator}")
                return PrivacyStatus.REQUIRES_REVIEW, "; ".join(notes)

        # Run custom rules
        for rule in self.custom_rules:
            try:
                if not rule(sample):
                    notes.append("Failed custom privacy rule")
                    return PrivacyStatus.REQUIRES_REVIEW, "; ".join(notes)
            except Exception as e:
                logger.warning(f"Custom privacy rule raised exception: {e}")
                notes.append(f"Custom rule error: {e}")

        # No issues found
        return PrivacyStatus.APPROVED, "Automated privacy check passed"

    def check_batch(
        self, samples: list[HarvestedSample]
    ) -> dict[str, tuple[PrivacyStatus, str]]:
        """Check multiple samples.

        Args:
            samples: List of samples to check

        Returns:
            Dict mapping sample_id to (status, notes)
        """
        results = {}
        for sample in samples:
            status, notes = self.check_sample(sample)
            results[sample.sample_id] = (status, notes)
        return results


# ============================================================================
# Sample Harvester
# ============================================================================


class SampleHarvester:
    """Harvests high-value samples for re-training.

    Identifies samples with:
    - High entropy (model uncertainty)
    - Low agreement (model disagreement)
    - Quality outliers
    - Drift indicators
    """

    def __init__(
        self,
        config: HarvesterConfig | None = None,
        privacy_checker: PrivacyChecker | None = None,
    ):
        """Initialize harvester.

        Args:
            config: Harvester configuration
            privacy_checker: Optional privacy checker
        """
        self.config = config or HarvesterConfig()
        self.privacy_checker = privacy_checker or PrivacyChecker()
        self._sample_counter = 0
        self._current_batch: list[HarvestedSample] = []

        # Ensure output directory exists
        self.output_path = Path(self.config.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def should_harvest(
        self,
        entropy: float | None = None,
        agreement: float | None = None,
        is_teacher_escalation: bool = False,
        quality_scores: dict[str, float] | None = None,
    ) -> tuple[bool, HarvestReason | None]:
        """Determine if a sample should be harvested.

        Args:
            entropy: Model prediction entropy (higher = more uncertain)
            agreement: Agreement between models (lower = more disagreement)
            is_teacher_escalation: Whether teacher was invoked
            quality_scores: Quality assessment scores

        Returns:
            Tuple of (should_harvest, reason)
        """
        # Check entropy threshold
        if entropy is not None and entropy >= self.config.entropy_threshold:
            return True, HarvestReason.HIGH_ENTROPY

        # Check agreement threshold
        if agreement is not None and agreement <= self.config.agreement_threshold:
            return True, HarvestReason.LOW_AGREEMENT

        # Check teacher escalation
        if is_teacher_escalation:
            return True, HarvestReason.TEACHER_ESCALATION

        # Check for quality outliers (z-score > 2)
        if quality_scores:
            for score_name, score_value in quality_scores.items():
                if score_value < 0.1 or score_value > 0.9:  # Extreme values
                    return True, HarvestReason.QUALITY_OUTLIER

        return False, None

    def harvest_sample(
        self,
        source_path: str,
        reason: HarvestReason,
        entropy: float | None = None,
        agreement: float | None = None,
        model_predictions: dict[str, float] | None = None,
        quality_scores: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HarvestedSample:
        """Harvest a sample.

        Args:
            source_path: Path to source file
            reason: Reason for harvesting
            entropy: Model entropy value
            agreement: Model agreement score
            model_predictions: Dict of model -> prediction
            quality_scores: Dict of quality metrics
            metadata: Additional metadata

        Returns:
            HarvestedSample object
        """
        self._sample_counter += 1
        sample_id = (
            f"sample_{utc_now().strftime('%Y%m%d_%H%M%S')}_{self._sample_counter:04d}"
        )

        # Compute checksum if enabled
        checksum = ""
        if self.config.compute_checksums and Path(source_path).exists():
            checksum = self._compute_file_checksum(source_path)

        sample = HarvestedSample(
            sample_id=sample_id,
            source_path=source_path,
            harvest_time=utc_now(),
            harvest_reason=reason,
            entropy=entropy,
            agreement_score=agreement,
            model_predictions=model_predictions or {},
            quality_scores=quality_scores or {},
            metadata=metadata or {},
            checksum=checksum,
        )

        # Run privacy check if enabled
        if self.config.auto_privacy_check:
            status, notes = self.privacy_checker.check_sample(sample)
            sample.privacy_status = status
            sample.privacy_notes = notes

        # Add to current batch
        self._current_batch.append(sample)

        # Copy file if enabled
        if self.config.copy_sample_files:
            self._copy_sample_file(sample)

        logger.info(f"Harvested sample {sample_id} for reason: {reason.value}")

        return sample

    def _compute_file_checksum(self, file_path: str) -> str:
        """Compute SHA-256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _copy_sample_file(self, sample: HarvestedSample) -> bool:
        """Copy sample file to output directory.

        Args:
            sample: Sample to copy

        Returns:
            True if successful
        """
        source = Path(sample.source_path)
        if not source.exists():
            logger.warning(f"Source file not found: {source}")
            return False

        # Create batch subdirectory
        batch_dir = self.output_path / utc_now().strftime("%Y%m%d")
        batch_dir.mkdir(exist_ok=True)

        # Copy with sample_id prefix
        dest = batch_dir / f"{sample.sample_id}{source.suffix}"
        try:
            shutil.copy2(source, dest)
            sample.metadata["harvested_path"] = str(dest)
            return True
        except Exception as e:
            logger.error(f"Failed to copy sample file: {e}")
            return False

    def get_current_batch(self) -> list[HarvestedSample]:
        """Get current batch of harvested samples."""
        return list(self._current_batch)

    def clear_batch(self) -> None:
        """Clear current batch."""
        self._current_batch.clear()

    def get_batch_size(self) -> int:
        """Get current batch size."""
        return len(self._current_batch)

    def is_batch_full(self) -> bool:
        """Check if batch has reached maximum size."""
        return len(self._current_batch) >= self.config.max_samples_per_batch


# ============================================================================
# Manifest Generator
# ============================================================================


class ManifestGenerator:
    """Generates metadata manifests for re-training pipeline.

    Creates structured manifests compatible with ML training workflows.
    """

    def __init__(self, output_dir: str | Path):
        """Initialize manifest generator.

        Args:
            output_dir: Directory to write manifests
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_counter = 0

    def create_manifest(
        self,
        samples: list[HarvestedSample],
        metadata: dict[str, Any] | None = None,
    ) -> HarvestManifest:
        """Create a manifest for a batch of samples.

        Args:
            samples: List of harvested samples
            metadata: Optional additional metadata

        Returns:
            HarvestManifest object
        """
        self._manifest_counter += 1
        manifest_id = f"manifest_{utc_now().strftime('%Y%m%d_%H%M%S')}_{self._manifest_counter:04d}"

        manifest = HarvestManifest(
            manifest_id=manifest_id,
            created_at=utc_now(),
            samples=samples,
            total_count=len(samples),
            metadata=metadata or {},
        )

        manifest.update_counts()

        return manifest

    def save_manifest(self, manifest: HarvestManifest) -> Path:
        """Save manifest to disk.

        Args:
            manifest: Manifest to save

        Returns:
            Path to saved manifest file
        """
        # Save to dated subdirectory
        date_dir = self.output_dir / utc_now().strftime("%Y%m")
        date_dir.mkdir(exist_ok=True)

        manifest_path = date_dir / f"{manifest.manifest_id}.json"

        with open(manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        # Also update latest symlink/file
        latest_path = self.output_dir / "latest_manifest.json"
        with open(latest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        logger.info(f"Saved manifest: {manifest_path}")

        return manifest_path

    def load_manifest(self, manifest_path: str | Path) -> HarvestManifest:
        """Load manifest from disk.

        Args:
            manifest_path: Path to manifest file

        Returns:
            HarvestManifest object
        """
        with open(manifest_path) as f:
            data = json.load(f)

        return HarvestManifest.from_dict(data)

    def get_latest_manifest(self) -> HarvestManifest | None:
        """Get the most recent manifest.

        Returns:
            Latest manifest or None if not found
        """
        latest_path = self.output_dir / "latest_manifest.json"

        if not latest_path.exists():
            return None

        return self.load_manifest(latest_path)

    def list_manifests(self, days: int = 30) -> list[Path]:
        """List manifest files within a time range.

        Args:
            days: Number of days to look back

        Returns:
            List of manifest file paths
        """
        manifests = []

        for month_dir in sorted(self.output_dir.iterdir()):
            if month_dir.is_dir() and month_dir.name.isdigit():
                for manifest_file in month_dir.glob("manifest_*.json"):
                    manifests.append(manifest_file)

        return sorted(manifests, key=lambda p: p.name, reverse=True)

    def generate_training_split(
        self,
        manifest: HarvestManifest,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
    ) -> dict[str, list[str]]:
        """Generate train/val/test split from manifest.

        Only includes approved samples.

        Args:
            manifest: Source manifest
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            test_ratio: Test set ratio

        Returns:
            Dict with train/val/test sample IDs
        """
        # Filter to approved samples only
        approved_samples = [
            s for s in manifest.samples if s.privacy_status == PrivacyStatus.APPROVED
        ]

        if not approved_samples:
            return {"train": [], "val": [], "test": []}

        # Simple sequential split (in production, use proper random split)
        total = len(approved_samples)
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)

        return {
            "train": [s.sample_id for s in approved_samples[:train_end]],
            "val": [s.sample_id for s in approved_samples[train_end:val_end]],
            "test": [s.sample_id for s in approved_samples[val_end:]],
        }


# ============================================================================
# Privacy Review Checklist
# ============================================================================

PRIVACY_REVIEW_CHECKLIST = """
# Privacy Review Checklist for Harvested Samples

## Pre-Harvest Checks
- [ ] Confirm data collection is authorized for training purposes
- [ ] Verify data retention policy compliance
- [ ] Check that source data doesn't contain explicit PII markers

## Sample-Level Review
For each sample requiring manual review:

### 1. PII Detection
- [ ] No visible personal identifiable information
- [ ] No names, addresses, phone numbers, or email addresses
- [ ] No government ID numbers (SSN, passport, driver's license)
- [ ] No financial information (credit cards, bank accounts)
- [ ] No medical/health records

### 2. Sensitive Content
- [ ] No confidential business information
- [ ] No proprietary third-party content
- [ ] No copyrighted material without license
- [ ] No content from restricted/private sources

### 3. Consent Verification
- [ ] Data was collected with appropriate consent
- [ ] Usage for ML training is within consent scope
- [ ] Re-training usage doesn't violate original purpose

### 4. Anonymization (if needed)
- [ ] Personal details redacted/masked
- [ ] Identifying metadata removed
- [ ] File paths anonymized
- [ ] Timestamps generalized if sensitive

## Batch-Level Approval
- [ ] Overall sample distribution reviewed
- [ ] No systematic PII exposure identified
- [ ] Compliance officer sign-off (if required)
- [ ] Audit trail documented

## Post-Approval
- [ ] Approved samples moved to training queue
- [ ] Rejected samples scheduled for deletion
- [ ] Privacy review documented in manifest
- [ ] Notification sent to data governance team

---
Reviewed by: ______________________
Date: ______________________
Batch ID: ______________________
Approval Status: [ ] APPROVED  [ ] REJECTED  [ ] PARTIAL
"""


def get_privacy_checklist() -> str:
    """Get the privacy review checklist template.

    Returns:
        Checklist markdown text
    """
    return PRIVACY_REVIEW_CHECKLIST


def save_privacy_checklist(output_path: str | Path) -> None:
    """Save privacy checklist to file.

    Args:
        output_path: Path to save checklist
    """
    with open(output_path, "w") as f:
        f.write(PRIVACY_REVIEW_CHECKLIST)


# ============================================================================
# Convenience Functions
# ============================================================================


def create_harvester(
    output_dir: str = DEFAULT_OUTPUT_DIR,
    entropy_threshold: float = DEFAULT_ENTROPY_THRESHOLD,
    agreement_threshold: float = DEFAULT_AGREEMENT_THRESHOLD,
) -> SampleHarvester:
    """Create a sample harvester with default configuration.

    Args:
        output_dir: Directory for harvested samples
        entropy_threshold: Entropy threshold for harvesting
        agreement_threshold: Agreement threshold for harvesting

    Returns:
        Configured SampleHarvester
    """
    config = HarvesterConfig(
        output_dir=output_dir,
        entropy_threshold=entropy_threshold,
        agreement_threshold=agreement_threshold,
    )
    return SampleHarvester(config)


def harvest_and_manifest(
    harvester: SampleHarvester,
    manifest_generator: ManifestGenerator,
    samples_to_harvest: list[dict[str, Any]],
) -> HarvestManifest | None:
    """Harvest samples and generate manifest.

    Convenience function for batch harvesting.

    Args:
        harvester: Sample harvester
        manifest_generator: Manifest generator
        samples_to_harvest: List of sample dicts with keys:
            - source_path: str
            - entropy: float (optional)
            - agreement: float (optional)
            - model_predictions: dict (optional)
            - quality_scores: dict (optional)
            - metadata: dict (optional)

    Returns:
        Generated manifest or None if no samples harvested
    """
    for sample_data in samples_to_harvest:
        source_path = sample_data.get("source_path", "")
        if not source_path:
            continue

        should_harvest, reason = harvester.should_harvest(
            entropy=sample_data.get("entropy"),
            agreement=sample_data.get("agreement"),
            quality_scores=sample_data.get("quality_scores"),
        )

        if should_harvest and reason:
            harvester.harvest_sample(
                source_path=source_path,
                reason=reason,
                entropy=sample_data.get("entropy"),
                agreement=sample_data.get("agreement"),
                model_predictions=sample_data.get("model_predictions"),
                quality_scores=sample_data.get("quality_scores"),
                metadata=sample_data.get("metadata"),
            )

    # Generate manifest if we have samples
    samples = harvester.get_current_batch()
    if samples:
        manifest = manifest_generator.create_manifest(samples)
        manifest_generator.save_manifest(manifest)
        harvester.clear_batch()
        return manifest

    return None


__all__ = [
    # Classes
    "HarvesterConfig",
    "HarvestedSample",
    "HarvestManifest",
    "ManifestGenerator",
    "PrivacyChecker",
    "SampleHarvester",
    # Enums
    "HarvestReason",
    "PrivacyStatus",
    # Functions
    "create_harvester",
    "get_privacy_checklist",
    "harvest_and_manifest",
    "save_privacy_checklist",
    # Constants
    "DEFAULT_AGREEMENT_THRESHOLD",
    "DEFAULT_ENTROPY_THRESHOLD",
    "DEFAULT_MAX_SAMPLES_PER_BATCH",
    "DEFAULT_OUTPUT_DIR",
    "PRIVACY_REVIEW_CHECKLIST",
]
