"""Tests for arena schemas module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from image_preprocessing_detector.labeling.arena.schemas import (
    BenchmarkResult,
    DatasetInfo,
    DIQAGroundTruth,
    DIQAPrediction,
    ExecutionInfo,
    ProvenanceInfo,
    ReproducibilityManifest,
    RunStatus,
    SampleResult,
)


class TestDIQAPrediction:
    """Tests for DIQAPrediction dataclass."""

    def test_valid_prediction(self) -> None:
        """Test creating valid prediction."""
        pred = DIQAPrediction(
            overall=0.85,
            sharpness=0.78,
            color=0.92,
            image_id="img_001",
            inference_time_ms=25.5,
        )
        assert pred.overall == 0.85
        assert pred.sharpness == 0.78
        assert pred.color == 0.92

    def test_boundary_values(self) -> None:
        """Test boundary values [0, 1]."""
        pred = DIQAPrediction(overall=0.0, sharpness=1.0, color=0.5)
        assert pred.overall == 0.0
        assert pred.sharpness == 1.0

    def test_invalid_value_raises(self) -> None:
        """Test that out-of-range values raise ValueError."""
        with pytest.raises(ValueError, match="overall must be in"):
            DIQAPrediction(overall=1.5, sharpness=0.5, color=0.5)

        with pytest.raises(ValueError, match="sharpness must be in"):
            DIQAPrediction(overall=0.5, sharpness=-0.1, color=0.5)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        pred = DIQAPrediction(
            overall=0.85,
            sharpness=0.78,
            color=0.92,
            image_id="img_001",
            inference_time_ms=25.5,
        )
        d = pred.to_dict()

        assert d["overall"] == 0.85
        assert d["sharpness"] == 0.78
        assert d["color"] == 0.92
        assert d["image_id"] == "img_001"
        assert d["inference_time_ms"] == 25.5


class TestDIQAGroundTruth:
    """Tests for DIQAGroundTruth dataclass."""

    def test_valid_ground_truth(self) -> None:
        """Test creating valid ground truth."""
        gt = DIQAGroundTruth(
            overall=0.85,
            sharpness=0.78,
            color=0.92,
            image_id="img_001",
            image_path="/path/to/img.png",
        )
        assert gt.overall == 0.85
        assert gt.image_id == "img_001"


class TestSampleResult:
    """Tests for SampleResult dataclass."""

    def test_auto_compute_error(self) -> None:
        """Test automatic error computation."""
        pred = DIQAPrediction(overall=0.8, sharpness=0.7, color=0.9)
        gt = DIQAGroundTruth(overall=0.85, sharpness=0.75, color=0.88)

        result = SampleResult(
            image_id="img_001",
            prediction=pred,
            ground_truth=gt,
        )

        assert result.per_dimension_error["overall"] == pytest.approx(0.05)
        assert result.per_dimension_error["sharpness"] == pytest.approx(0.05)
        assert result.per_dimension_error["color"] == pytest.approx(0.02)


class TestDatasetInfo:
    """Tests for DatasetInfo dataclass."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        info = DatasetInfo(
            name="diqa5000",
            version="1.0.0",
            split="test",
            num_samples=750,
            checksum="sha256:abc123",
        )
        d = info.to_dict()

        assert d["name"] == "diqa5000"
        assert d["version"] == "1.0.0"
        assert d["split"] == "test"
        assert d["num_samples"] == 750


class TestExecutionInfo:
    """Tests for ExecutionInfo dataclass."""

    def test_auto_timestamp(self) -> None:
        """Test automatic timestamp generation."""
        info = ExecutionInfo(
            hardware="RTX 4090",
            duration_seconds=45.5,
            batch_size=8,
        )
        assert info.timestamp != ""
        assert "T" in info.timestamp  # ISO format

    def test_provided_timestamp(self) -> None:
        """Test using provided timestamp."""
        info = ExecutionInfo(
            hardware="RTX 4090",
            duration_seconds=45.5,
            batch_size=8,
            timestamp="2024-01-15T10:30:00+00:00",
        )
        assert info.timestamp == "2024-01-15T10:30:00+00:00"


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    @pytest.fixture
    def sample_result(self) -> BenchmarkResult:
        """Create a sample benchmark result."""
        return BenchmarkResult(
            run_id="abc123",
            status=RunStatus.COMPLETED,
            model_spec={"id": "test-model", "source": "huggingface"},
            dataset=DatasetInfo(
                name="diqa5000",
                version="1.0.0",
                split="test",
                num_samples=750,
            ),
            metrics={
                "overall": {"plcc": 0.9, "srcc": 0.85, "mae": 0.05, "rmse": 0.07},
                "aggregate": {"plcc": 0.88, "srcc": 0.83, "mae": 0.06, "rmse": 0.08},
            },
            execution=ExecutionInfo(
                hardware="RTX 4090",
                duration_seconds=45.5,
                batch_size=8,
            ),
            provenance=ProvenanceInfo(model_checksum="sha256:abc"),
        )

    def test_to_dict(self, sample_result: BenchmarkResult) -> None:
        """Test serialization to dictionary."""
        d = sample_result.to_dict()

        assert d["run_id"] == "abc123"
        assert d["status"] == "completed"
        assert d["model_spec"]["id"] == "test-model"

    def test_to_json_string(self, sample_result: BenchmarkResult) -> None:
        """Test JSON string serialization."""
        json_str = sample_result.to_json()

        data = json.loads(json_str)
        assert data["run_id"] == "abc123"

    def test_to_json_file(self, sample_result: BenchmarkResult) -> None:
        """Test JSON file serialization."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            sample_result.to_json(path)
            assert path.exists()

            loaded = json.loads(path.read_text())
            assert loaded["run_id"] == "abc123"
        finally:
            path.unlink(missing_ok=True)

    def test_from_json(self, sample_result: BenchmarkResult) -> None:
        """Test loading from JSON."""
        json_str = sample_result.to_json()
        loaded = BenchmarkResult.from_json(json_str)

        assert loaded.run_id == sample_result.run_id
        assert loaded.status == sample_result.status

    def test_compute_content_hash(self, sample_result: BenchmarkResult) -> None:
        """Test content hash computation."""
        hash1 = sample_result.compute_content_hash()
        hash2 = sample_result.compute_content_hash()

        assert hash1 == hash2
        assert len(hash1) == 16


class TestReproducibilityManifest:
    """Tests for ReproducibilityManifest dataclass."""

    def test_auto_created_at(self) -> None:
        """Test automatic created_at timestamp."""
        manifest = ReproducibilityManifest(
            run_id="abc123",
            model={"spec": {"id": "test"}},
            dataset={"name": "diqa5000"},
            environment={"hardware": "RTX 4090"},
            seeds={"random": 42, "numpy": 42},
            result_hash="abc123def456",
        )
        assert manifest.created_at != ""

    def test_to_yaml(self) -> None:
        """Test YAML serialization."""
        manifest = ReproducibilityManifest(
            run_id="abc123",
            model={"spec": {"id": "test"}},
            dataset={"name": "diqa5000"},
            environment={"hardware": "RTX 4090"},
            seeds={"random": 42, "numpy": 42},
            result_hash="abc123def456",
        )
        yaml_str = manifest.to_yaml()

        assert "run_id: abc123" in yaml_str
        assert "result_hash:" in yaml_str

    def test_yaml_roundtrip(self) -> None:
        """Test YAML serialization roundtrip."""
        manifest = ReproducibilityManifest(
            run_id="abc123",
            model={"spec": {"id": "test"}},
            dataset={"name": "diqa5000"},
            environment={"hardware": "RTX 4090"},
            seeds={"random": 42, "numpy": 42, "torch": 42},
            result_hash="abc123def456",
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)

        try:
            manifest.to_yaml(path)
            loaded = ReproducibilityManifest.from_yaml(path)

            assert loaded.run_id == manifest.run_id
            assert loaded.result_hash == manifest.result_hash
            assert loaded.seeds == manifest.seeds
        finally:
            path.unlink(missing_ok=True)

    def test_from_benchmark_result(self) -> None:
        """Test creating manifest from benchmark result."""
        result = BenchmarkResult(
            run_id="abc123",
            status=RunStatus.COMPLETED,
            model_spec={"id": "test-model"},
            dataset=DatasetInfo(
                name="diqa5000",
                version="1.0.0",
                split="test",
                num_samples=750,
            ),
            metrics={"aggregate": {"plcc": 0.9}},
            execution=ExecutionInfo(
                hardware="RTX 4090",
                duration_seconds=45.5,
                batch_size=8,
                seed=42,
            ),
            provenance=ProvenanceInfo(model_checksum="sha256:abc"),
        )

        manifest = ReproducibilityManifest.from_benchmark_result(result)

        assert manifest.run_id == "abc123"
        assert manifest.seeds["random"] == 42
        assert manifest.result_hash == result.compute_content_hash()


class TestRunStatus:
    """Tests for RunStatus enum."""

    def test_status_values(self) -> None:
        """Test enum values."""
        assert RunStatus.PENDING.value == "pending"
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.CANCELLED.value == "cancelled"

    def test_from_string(self) -> None:
        """Test creating from string."""
        status = RunStatus("completed")
        assert status == RunStatus.COMPLETED
