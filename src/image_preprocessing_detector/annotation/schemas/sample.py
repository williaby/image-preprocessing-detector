# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Sample aggregate schema for the annotation system.

This module contains the SampleMetadata class which aggregates the
immutable and enrichment layers into a complete metadata record for
a single sample.

Example:
    >>> from image_preprocessing_detector.annotation.schemas.sample import (
    ...     SampleMetadata,
    ... )
    >>> from image_preprocessing_detector.annotation.schemas.immutable import (
    ...     OriginalFileMetadata,
    ...     OriginalLabels,
    ... )
    >>>
    >>> sample = SampleMetadata(
    ...     id="abc123def456",
    ...     file_hash="sha256:...",
    ...     dataset_name="diqa-5000",
    ...     dataset_version="1.0",
    ...     original_path="train/img001.png",
    ...     original_filename="img001.png",
    ...     download_date="2025-01-15",
    ...     original_labels=OriginalLabels(),
    ...     original_file=OriginalFileMetadata(...),
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .enrichment import EnrichmentData, EnrichmentVersion
from .immutable import OriginalFileMetadata, OriginalLabels

if TYPE_CHECKING:
    pass

# Schema version for tracking changes
SCHEMA_VERSION = "2.1"
SCRIPT_VERSION = "0.1.0"


def _get_git_sha() -> str:
    """Get current git commit SHA for reproducibility.

    Returns:
        Short (12 char) git SHA or "unknown" if not in a git repo.
    """
    import subprocess
    from pathlib import Path

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            check=True,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


@dataclass
class SampleMetadata:
    """Complete metadata record for a single sample.

    Aggregates the immutable layer (original_labels, original_file) and
    enrichment layer (enrichment_versions) into a complete metadata record.

    Attributes:
        # Identity
        id: Deterministic sample ID (from compute_sample_id)
        file_hash: Full SHA256 hash of file content

        # Source information (immutable)
        dataset_name: Name of source dataset
        dataset_version: Version of source dataset
        original_path: Path relative to dataset root
        original_filename: Original filename
        download_date: Date dataset was downloaded

        # Original labels (immutable)
        original_labels: OriginalLabels instance

        # Original file metadata (immutable)
        original_file: OriginalFileMetadata instance

        # Enrichment history (versioned)
        current_version: Current active enrichment version number
        enrichment_versions: List of all enrichment versions

        # Record metadata
        created_at: ISO 8601 timestamp of record creation
        schema_version: Schema version for migration support
    """

    # Identity
    id: str
    file_hash: str

    # Source information (immutable)
    dataset_name: str
    dataset_version: str
    original_path: str
    original_filename: str
    download_date: str

    # Original labels (immutable)
    original_labels: OriginalLabels

    # Original file metadata (immutable)
    original_file: OriginalFileMetadata

    # Enrichment history (versioned)
    current_version: int = 0
    enrichment_versions: list[EnrichmentVersion] = field(default_factory=list)

    # Record metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    schema_version: str = SCHEMA_VERSION

    def add_enrichment(
        self,
        data: EnrichmentData,
        created_by: str,
        method: str,
        description: str,
        git_sha: str | None = None,
        model_checkpoint: str | None = None,
        config_hash: str | None = None,
    ) -> int:
        """Add new enrichment version.

        Creates a new enrichment version with full provenance metadata
        and appends it to the version history.

        Args:
            data: EnrichmentData containing annotations
            created_by: Identifier for creator
            method: Enrichment method (EnrichmentTier value)
            description: Human-readable description
            git_sha: Git commit SHA (auto-detected if None)
            model_checkpoint: Model checkpoint used
            config_hash: Hash of configuration

        Returns:
            New version number (1-indexed)
        """
        new_version = len(self.enrichment_versions) + 1
        enrichment = EnrichmentVersion(
            version=new_version,
            created_at=datetime.now(UTC).isoformat(),
            created_by=created_by,
            method=method,
            description=description,
            data=data,
            git_sha=git_sha or _get_git_sha(),
            model_checkpoint=model_checkpoint,
            config_hash=config_hash,
            script_version=SCRIPT_VERSION,
        )
        self.enrichment_versions.append(enrichment)
        self.current_version = new_version
        return new_version

    def get_current_enrichment(self) -> EnrichmentData | None:
        """Get the current active enrichment data.

        Returns:
            EnrichmentData for current version, or None if no enrichments.
        """
        if not self.enrichment_versions or self.current_version == 0:
            return None
        # Find the version matching current_version
        for version in self.enrichment_versions:
            if version.version == self.current_version:
                return version.data
        return None

    def get_enrichment_version(self, version: int) -> EnrichmentVersion | None:
        """Get a specific enrichment version.

        Args:
            version: Version number to retrieve (1-indexed)

        Returns:
            EnrichmentVersion if found, None otherwise.
        """
        for enrichment in self.enrichment_versions:
            if enrichment.version == version:
                return enrichment
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON output.
        """
        return {
            "id": self.id,
            "file_hash": self.file_hash,
            "source": {
                "dataset_name": self.dataset_name,
                "dataset_version": self.dataset_version,
                "original_path": self.original_path,
                "original_filename": self.original_filename,
                "download_date": self.download_date,
            },
            "original_labels": {
                k: v for k, v in self.original_labels.__dict__.items() if v is not None
            },
            "original_file": self.original_file.__dict__,
            "enrichments": {
                "current_version": self.current_version,
                "versions": [
                    {
                        "version": v.version,
                        "created_at": v.created_at,
                        "created_by": v.created_by,
                        "method": v.method,
                        "description": v.description,
                        "git_sha": v.git_sha,
                        "model_checkpoint": v.model_checkpoint,
                        "config_hash": v.config_hash,
                        "script_version": v.script_version,
                        "data": {
                            k: val
                            for k, val in v.data.__dict__.items()
                            if val is not None
                        },
                    }
                    for v in self.enrichment_versions
                ],
            },
            "record_meta": {
                "created_at": self.created_at,
                "schema_version": self.schema_version,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SampleMetadata:
        """Create SampleMetadata from dictionary.

        Args:
            data: Dictionary representation (e.g., from JSON)

        Returns:
            SampleMetadata instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is malformed
        """
        source = data["source"]
        original_labels_data = data.get("original_labels", {})
        original_file_data = data["original_file"]
        enrichments = data.get("enrichments", {})

        # Reconstruct original labels
        original_labels = OriginalLabels(**original_labels_data)

        # Reconstruct original file metadata
        original_file = OriginalFileMetadata(**original_file_data)

        # Reconstruct enrichment versions
        enrichment_versions = []
        for v_data in enrichments.get("versions", []):
            enrichment_data = EnrichmentData(**v_data.get("data", {}))
            version = EnrichmentVersion(
                version=v_data["version"],
                created_at=v_data["created_at"],
                created_by=v_data["created_by"],
                method=v_data["method"],
                description=v_data["description"],
                data=enrichment_data,
                git_sha=v_data.get("git_sha"),
                model_checkpoint=v_data.get("model_checkpoint"),
                config_hash=v_data.get("config_hash"),
                script_version=v_data.get("script_version"),
            )
            enrichment_versions.append(version)

        record_meta = data.get("record_meta", {})

        return cls(
            id=data["id"],
            file_hash=data["file_hash"],
            dataset_name=source["dataset_name"],
            dataset_version=source["dataset_version"],
            original_path=source["original_path"],
            original_filename=source["original_filename"],
            download_date=source["download_date"],
            original_labels=original_labels,
            original_file=original_file,
            current_version=enrichments.get("current_version", 0),
            enrichment_versions=enrichment_versions,
            created_at=record_meta.get("created_at", datetime.now(UTC).isoformat()),
            schema_version=record_meta.get("schema_version", SCHEMA_VERSION),
        )


__all__ = [
    "SCHEMA_VERSION",
    "SCRIPT_VERSION",
    "SampleMetadata",
]
