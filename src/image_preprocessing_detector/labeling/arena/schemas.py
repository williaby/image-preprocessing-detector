"""Arena data schemas and result types.

This module defines the data structures used throughout the Arena
benchmarking system, including predictions, results, and run metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from image_preprocessing_detector.utils.datetime_compat import UTC


class RunStatus(str, Enum):
    """Status of a benchmark run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DIQAPrediction:
    """Model prediction for a single document image.

    Attributes:
        overall: Overall quality score [0, 1]
        sharpness: Sharpness score [0, 1]
        color: Color fidelity score [0, 1]
        image_id: Identifier for the source image
        inference_time_ms: Time taken for inference in milliseconds
    """

    overall: float
    sharpness: float
    color: float
    image_id: str = ""
    inference_time_ms: float = 0.0

    def __post_init__(self) -> None:
        """Validate prediction values are in valid range."""
        for attr in ("overall", "sharpness", "color"):
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                msg = f"{attr} must be in [0, 1], got {value}"
                raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall": self.overall,
            "sharpness": self.sharpness,
            "color": self.color,
            "image_id": self.image_id,
            "inference_time_ms": self.inference_time_ms,
        }


@dataclass
class DIQAGroundTruth:
    """Ground truth labels for a single document image.

    Attributes:
        overall: Overall quality score [0, 1]
        sharpness: Sharpness score [0, 1]
        color: Color fidelity score [0, 1]
        image_id: Identifier for the source image
        image_path: Path to the image file
        metadata: Additional metadata from dataset
    """

    overall: float
    sharpness: float
    color: float
    image_id: str = ""
    image_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall": self.overall,
            "sharpness": self.sharpness,
            "color": self.color,
            "image_id": self.image_id,
            "image_path": self.image_path,
            "metadata": self.metadata,
        }


@dataclass
class DatasetInfo:
    """Information about the benchmark dataset.

    Attributes:
        name: Dataset name (e.g., "diqa5000")
        version: Dataset version
        split: Data split used (train/val/test)
        num_samples: Number of samples in the split
        checksum: Hash of the dataset for verification
    """

    name: str
    version: str
    split: str
    num_samples: int
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "version": self.version,
            "split": self.split,
            "num_samples": self.num_samples,
            "checksum": self.checksum,
        }


@dataclass
class ExecutionInfo:
    """Information about the execution environment.

    Attributes:
        hardware: GPU/CPU description
        duration_seconds: Total execution time
        batch_size: Batch size used for inference
        seed: Random seed for reproducibility
        python_version: Python version
        cuda_version: CUDA version (if applicable)
        timestamp: Execution start timestamp
    """

    hardware: str
    duration_seconds: float
    batch_size: int
    seed: int = 42
    python_version: str = ""
    cuda_version: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "hardware": self.hardware,
            "duration_seconds": self.duration_seconds,
            "batch_size": self.batch_size,
            "seed": self.seed,
            "python_version": self.python_version,
            "cuda_version": self.cuda_version,
            "timestamp": self.timestamp,
        }


@dataclass
class ProvenanceInfo:
    """Provenance information for reproducibility.

    Attributes:
        model_checksum: SHA256 of model weights
        config_hash: Hash of model configuration
        tokenizer_hash: Hash of tokenizer files
        code_version: Git commit hash of the code
        dependencies_hash: Hash of requirements lock file
    """

    model_checksum: str | None = None
    config_hash: str | None = None
    tokenizer_hash: str | None = None
    code_version: str | None = None
    dependencies_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "model_checksum": self.model_checksum,
            "config_hash": self.config_hash,
            "tokenizer_hash": self.tokenizer_hash,
            "code_version": self.code_version,
            "dependencies_hash": self.dependencies_hash,
        }


@dataclass
class SampleResult:
    """Result for a single sample in the benchmark.

    Attributes:
        image_id: Sample identifier
        prediction: Model prediction
        ground_truth: Ground truth values
        per_dimension_error: Absolute error per dimension
    """

    image_id: str
    prediction: DIQAPrediction
    ground_truth: DIQAGroundTruth
    per_dimension_error: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute per-dimension errors."""
        if not self.per_dimension_error:
            self.per_dimension_error = {
                "overall": abs(self.prediction.overall - self.ground_truth.overall),
                "sharpness": abs(
                    self.prediction.sharpness - self.ground_truth.sharpness
                ),
                "color": abs(self.prediction.color - self.ground_truth.color),
            }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "image_id": self.image_id,
            "prediction": self.prediction.to_dict(),
            "ground_truth": self.ground_truth.to_dict(),
            "per_dimension_error": self.per_dimension_error,
        }


@dataclass
class BenchmarkResult:
    """Complete result of a benchmark run.

    This is the primary output structure of the Arena runner.

    Attributes:
        run_id: Unique identifier for this run
        status: Run status (completed, failed, etc.)
        model_spec: ModelSpec dictionary
        dataset: Dataset information
        metrics: Computed arena metrics
        execution: Execution environment info
        provenance: Provenance for reproducibility
        sample_results: Per-sample results (optional, for detailed analysis)
        manifest_path: Path to reproducibility manifest
        error_message: Error message if run failed
    """

    run_id: str
    status: RunStatus
    model_spec: dict[str, Any]
    dataset: DatasetInfo
    metrics: dict[str, Any]  # ArenaMetrics.to_dict()
    execution: ExecutionInfo
    provenance: ProvenanceInfo
    sample_results: list[SampleResult] = field(default_factory=list)
    manifest_path: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON serialization."""
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "model_spec": self.model_spec,
            "dataset": self.dataset.to_dict(),
            "metrics": self.metrics,
            "execution": self.execution.to_dict(),
            "provenance": self.provenance.to_dict(),
            "sample_results": [r.to_dict() for r in self.sample_results],
            "manifest_path": self.manifest_path,
            "error_message": self.error_message,
        }

    def to_json(self, path: Path | str | None = None, indent: int = 2) -> str:
        """Serialize to JSON string or file.

        Args:
            path: Optional path to write JSON file.
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        json_str = json.dumps(self.to_dict(), indent=indent, default=str)

        if path is not None:
            Path(path).write_text(json_str, encoding="utf-8")

        return json_str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkResult:
        """Create from dictionary representation.

        Args:
            data: Dictionary with result data.

        Returns:
            BenchmarkResult instance.
        """
        return cls(
            run_id=data["run_id"],
            status=RunStatus(data["status"]),
            model_spec=data["model_spec"],
            dataset=DatasetInfo(**data["dataset"]),
            metrics=data["metrics"],
            execution=ExecutionInfo(**data["execution"]),
            provenance=ProvenanceInfo(**data["provenance"]),
            sample_results=[],  # Optionally reconstruct
            manifest_path=data.get("manifest_path"),
            error_message=data.get("error_message"),
        )

    @classmethod
    def from_json(cls, source: Path | str) -> BenchmarkResult:
        """Load from JSON file or string.

        Args:
            source: Path to JSON file or JSON string.

        Returns:
            BenchmarkResult instance.
        """
        # Check if source looks like a path (doesn't start with '{')
        if isinstance(source, (str, Path)):
            source_str = str(source)
            if source_str.strip().startswith("{"):
                # It's a JSON string
                data = json.loads(source_str)
            else:
                # Try as a file path
                path = Path(source)
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    # Fallback to parsing as JSON string
                    data = json.loads(source_str)
        else:
            data = json.loads(str(source))

        return cls.from_dict(data)

    def compute_content_hash(self) -> str:
        """Compute a hash of the result content for verification.

        Returns:
            SHA256 hash of the result's core content.
        """
        content = {
            "run_id": self.run_id,
            "model_spec": self.model_spec,
            "dataset": self.dataset.to_dict(),
            "metrics": self.metrics,
        }
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]


@dataclass
class ReproducibilityManifest:
    """Manifest for reproducing a benchmark run.

    Contains all information needed to reproduce the exact same
    benchmark results.

    Attributes:
        run_id: Unique identifier for the run
        model: Model specification details
        dataset: Dataset details
        environment: Environment details
        seeds: Random seeds used
        result_hash: Hash of the results for verification
    """

    run_id: str
    model: dict[str, Any]
    dataset: dict[str, Any]
    environment: dict[str, Any]
    seeds: dict[str, int]
    result_hash: str
    created_at: str = ""

    def __post_init__(self) -> None:
        """Set created_at if not provided."""
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "run_id": self.run_id,
            "model": self.model,
            "dataset": self.dataset,
            "environment": self.environment,
            "seeds": self.seeds,
            "result_hash": self.result_hash,
            "created_at": self.created_at,
        }

    def to_yaml(self, path: Path | str | None = None) -> str:
        """Serialize to YAML string or file.

        Args:
            path: Optional path to write YAML file.

        Returns:
            YAML string representation.
        """
        yaml_str = yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        if path is not None:
            Path(path).write_text(yaml_str, encoding="utf-8")

        return yaml_str

    @classmethod
    def from_yaml(cls, source: Path | str) -> ReproducibilityManifest:
        """Load from YAML file or string.

        Args:
            source: Path to YAML file or YAML string.

        Returns:
            ReproducibilityManifest instance.
        """
        path = Path(source)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            data = yaml.safe_load(source)  # type: ignore[arg-type]

        return cls(**data)

    @classmethod
    def from_benchmark_result(
        cls,
        result: BenchmarkResult,
        environment: dict[str, Any] | None = None,
    ) -> ReproducibilityManifest:
        """Create manifest from a benchmark result.

        Args:
            result: Completed benchmark result.
            environment: Additional environment details.

        Returns:
            ReproducibilityManifest instance.
        """
        return cls(
            run_id=result.run_id,
            model={
                "spec": result.model_spec,
                "provenance": result.provenance.to_dict(),
            },
            dataset=result.dataset.to_dict(),
            environment=environment
            or {
                "hardware": result.execution.hardware,
                "python_version": result.execution.python_version,
                "cuda_version": result.execution.cuda_version,
            },
            seeds={
                "random": result.execution.seed,
                "numpy": result.execution.seed,
                "torch": result.execution.seed,
            },
            result_hash=result.compute_content_hash(),
        )
