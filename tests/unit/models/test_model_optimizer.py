"""Tests for model optimization module.

This module tests:
- ONNX export configuration and validation
- INT8 quantization configuration
- Threshold tuning logic
- Model deployment package creation
- Model registry operations
- Benchmark result structures
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

# Import directly from the module to avoid torch dependency via __init__.py
from image_preprocessing_detector.models.model_optimizer import (
    BenchmarkResult,
    CalibrationDataset,
    ModelDeploymentPackage,
    ModelManifest,
    ModelOptimizer,
    ModelRegistry,
    ONNXExportConfig,
    QuantizationConfig,
    ThresholdConfig,
    ThresholdTuner,
)


class TestONNXExportConfig:
    """Tests for ONNXExportConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ONNXExportConfig()
        assert config.opset_version == 17
        assert config.dynamic_batch is True
        assert config.optimize is True
        assert config.verify_output is True
        assert config.input_shape == (1, 3, 224, 224)

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ONNXExportConfig(
            opset_version=14,
            dynamic_batch=False,
            optimize=False,
            verify_output=False,
            input_shape=(4, 3, 256, 256),
        )
        assert config.opset_version == 14
        assert config.dynamic_batch is False
        assert config.optimize is False
        assert config.verify_output is False
        assert config.input_shape == (4, 3, 256, 256)


class TestQuantizationConfig:
    """Tests for QuantizationConfig dataclass."""

    def test_default_config(self):
        """Test default quantization configuration."""
        config = QuantizationConfig()
        assert config.quant_format == "QInt8"
        assert config.per_channel is True
        assert config.calibration_method == "MinMax"
        assert config.num_calibration_samples == 1000
        assert config.accuracy_tolerance == 0.02

    def test_custom_config(self):
        """Test custom quantization configuration."""
        config = QuantizationConfig(
            quant_format="QUInt8",
            per_channel=False,
            calibration_method="Entropy",
            num_calibration_samples=500,
            accuracy_tolerance=0.05,
        )
        assert config.quant_format == "QUInt8"
        assert config.per_channel is False
        assert config.calibration_method == "Entropy"
        assert config.num_calibration_samples == 500
        assert config.accuracy_tolerance == 0.05


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_benchmark_result_creation(self):
        """Test creating benchmark result."""
        result = BenchmarkResult(
            model_path="/path/to/model.onnx",
            model_format="onnx",
            device="cpu",
            mean_latency_ms=25.5,
            std_latency_ms=2.3,
            p50_latency_ms=24.0,
            p95_latency_ms=30.0,
            p99_latency_ms=35.0,
            throughput_per_sec=40.0,
            memory_mb=128.0,
            num_samples=100,
        )
        assert result.model_path == "/path/to/model.onnx"
        assert result.model_format == "onnx"
        assert result.device == "cpu"
        assert result.mean_latency_ms == 25.5
        assert result.throughput_per_sec == 40.0
        assert result.num_samples == 100


class TestThresholdConfig:
    """Tests for ThresholdConfig dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        config = ThresholdConfig()
        assert config.blur_threshold == 0.5
        assert config.noise_threshold == 0.5
        assert config.skew_threshold == 0.5
        assert config.illumination_threshold == 0.5
        assert config.artifacts_threshold == 0.5
        assert config.optimized_for == "f1"

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        config = ThresholdConfig(
            blur_threshold=0.6,
            noise_threshold=0.4,
            skew_threshold=0.55,
            illumination_threshold=0.45,
            artifacts_threshold=0.7,
            optimized_for="precision",
        )
        assert config.blur_threshold == 0.6
        assert config.noise_threshold == 0.4
        assert config.optimized_for == "precision"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = ThresholdConfig(
            blur_threshold=0.6,
            noise_threshold=0.4,
        )
        d = config.to_dict()
        assert d["blur_threshold"] == 0.6
        assert d["noise_threshold"] == 0.4
        assert "optimized_for" in d

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "blur_threshold": 0.7,
            "noise_threshold": 0.3,
            "skew_threshold": 0.6,
            "illumination_threshold": 0.5,
            "artifacts_threshold": 0.4,
            "optimized_for": "recall",
        }
        config = ThresholdConfig.from_dict(data)
        assert config.blur_threshold == 0.7
        assert config.noise_threshold == 0.3
        assert config.optimized_for == "recall"

    def test_from_dict_missing_keys(self):
        """Test creation from partial dictionary."""
        data = {"blur_threshold": 0.8}
        config = ThresholdConfig.from_dict(data)
        assert config.blur_threshold == 0.8
        assert config.noise_threshold == 0.5  # default


class TestModelManifest:
    """Tests for ModelManifest dataclass."""

    def test_manifest_creation(self):
        """Test creating model manifest."""
        thresholds = ThresholdConfig()
        manifest = ModelManifest(
            model_name="student_iqa_resnet18",
            version="1.0.0",
            model_files={"onnx": "model.onnx", "int8": "model_int8.onnx"},
            thresholds=thresholds,
            metrics={"mAP": 0.88, "f1": 0.85},
            checksums={"onnx": "abc123", "int8": "def456"},
            created_at="2025-01-15T10:00:00Z",
            requirements={"onnxruntime": ">=1.15.0"},
        )
        assert manifest.model_name == "student_iqa_resnet18"
        assert manifest.version == "1.0.0"
        assert len(manifest.model_files) == 2
        assert manifest.metrics["mAP"] == 0.88

    def test_manifest_to_dict(self):
        """Test manifest to dictionary conversion."""
        thresholds = ThresholdConfig(blur_threshold=0.6)
        manifest = ModelManifest(
            model_name="test_model",
            version="1.0.0",
            model_files={"onnx": "model.onnx"},
            thresholds=thresholds,
            metrics={"accuracy": 0.95},
            checksums={"onnx": "checksum123"},
            created_at="2025-01-15T10:00:00Z",
        )
        d = manifest.to_dict()
        assert d["model_name"] == "test_model"
        assert d["version"] == "1.0.0"
        assert d["thresholds"]["blur_threshold"] == 0.6
        assert d["metrics"]["accuracy"] == 0.95

    def test_manifest_from_dict(self):
        """Test manifest from dictionary."""
        data = {
            "model_name": "test_model",
            "version": "2.0.0",
            "model_files": {"onnx": "model.onnx"},
            "thresholds": {"blur_threshold": 0.7},
            "metrics": {"f1": 0.9},
            "checksums": {"onnx": "hash123"},
            "created_at": "2025-01-15T12:00:00Z",
            "requirements": {},
        }
        manifest = ModelManifest.from_dict(data)
        assert manifest.model_name == "test_model"
        assert manifest.version == "2.0.0"
        assert manifest.thresholds.blur_threshold == 0.7
        assert manifest.metrics["f1"] == 0.9


class TestCalibrationDataset:
    """Tests for CalibrationDataset class."""

    def test_creation_with_precomputed_data(self):
        """Test creation with precomputed numpy data."""
        data = np.random.randn(10, 1, 3, 224, 224).astype(np.float32)
        dataset = CalibrationDataset(
            precomputed_data=data,
            input_name="input",
        )
        assert len(dataset) == 10

    def test_get_next_returns_dict(self):
        """Test that get_next returns proper dictionary."""
        data = np.random.randn(3, 1, 3, 224, 224).astype(np.float32)
        dataset = CalibrationDataset(precomputed_data=data, input_name="input")

        result = dataset.get_next()
        assert result is not None
        assert "input" in result
        assert result["input"].shape == (1, 3, 224, 224)

    def test_get_next_exhaustion(self):
        """Test that get_next returns None when exhausted."""
        data = np.random.randn(2, 1, 3, 224, 224).astype(np.float32)
        dataset = CalibrationDataset(precomputed_data=data, input_name="input")

        dataset.get_next()
        dataset.get_next()
        result = dataset.get_next()
        assert result is None

    def test_rewind(self):
        """Test rewind functionality."""
        data = np.random.randn(2, 1, 3, 224, 224).astype(np.float32)
        dataset = CalibrationDataset(precomputed_data=data, input_name="input")

        dataset.get_next()
        dataset.get_next()
        assert dataset.get_next() is None

        dataset.rewind()
        assert dataset.get_next() is not None


class TestThresholdTuner:
    """Tests for ThresholdTuner class."""

    def test_init(self):
        """Test threshold tuner initialization."""
        tuner = ThresholdTuner(metric="f1", search_range=(0.2, 0.8), num_steps=61)
        assert tuner.metric == "f1"
        assert tuner.search_range == (0.2, 0.8)
        assert tuner.num_steps == 61

    def test_find_optimal_threshold(self):
        """Test finding optimal threshold for single head."""
        tuner = ThresholdTuner(metric="f1", num_steps=21)

        # Create synthetic predictions and labels
        np.random.seed(42)
        # Create separable data
        predictions = np.concatenate(
            [
                np.random.uniform(0.0, 0.4, 50),  # Negatives
                np.random.uniform(0.6, 1.0, 50),  # Positives
            ]
        )
        labels = np.concatenate(
            [
                np.zeros(50),
                np.ones(50),
            ]
        )

        threshold, metrics = tuner.find_optimal_threshold(predictions, labels, "blur")

        assert 0.3 <= threshold <= 0.7
        assert "f1" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert metrics["f1"] > 0.8  # Should achieve high F1 with separable data

    def test_compute_metrics(self):
        """Test metric computation."""
        tuner = ThresholdTuner()

        # Perfect predictions
        predictions = np.array([0, 0, 1, 1])
        labels = np.array([0, 0, 1, 1])
        metrics = tuner._compute_metrics(predictions, labels)

        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0

    def test_compute_metrics_with_errors(self):
        """Test metric computation with errors."""
        tuner = ThresholdTuner()

        # Some errors
        predictions = np.array([0, 1, 1, 0])  # 2 errors
        labels = np.array([0, 0, 1, 1])
        metrics = tuner._compute_metrics(predictions, labels)

        assert metrics["accuracy"] == 0.5
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0

    def test_tune_all_heads(self):
        """Test tuning all heads."""
        tuner = ThresholdTuner(metric="f1", num_steps=11)

        predictions_dict = {
            "blur": np.concatenate(
                [np.random.uniform(0, 0.3, 30), np.random.uniform(0.7, 1, 30)]
            ),
            "noise": np.concatenate(
                [np.random.uniform(0, 0.4, 30), np.random.uniform(0.6, 1, 30)]
            ),
        }
        labels_dict = {
            "blur": np.concatenate([np.zeros(30), np.ones(30)]),
            "noise": np.concatenate([np.zeros(30), np.ones(30)]),
        }

        config = tuner.tune_all_heads(predictions_dict, labels_dict)

        assert isinstance(config, ThresholdConfig)
        assert config.blur_threshold != 0.5 or config.noise_threshold != 0.5
        assert config.optimized_for == "f1"


class TestModelOptimizer:
    """Tests for ModelOptimizer class."""

    def test_init(self):
        """Test optimizer initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            optimizer = ModelOptimizer(output_dir=tmpdir, device="cpu")
            assert optimizer.device == "cpu"
            assert optimizer.output_dir == Path(tmpdir)
            assert optimizer.output_dir.exists()

    def test_init_creates_directory(self):
        """Test that init creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "output"
            _ = ModelOptimizer(output_dir=output_dir)
            assert output_dir.exists()

    @patch("image_preprocessing_detector.models.model_optimizer.HAS_ORT", new=False)
    def test_benchmark_raises_without_ort(self):
        """Test that benchmarking raises without ONNX Runtime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            optimizer = ModelOptimizer(output_dir=tmpdir)

            with pytest.raises(RuntimeError, match="ONNX Runtime not available"):
                optimizer._benchmark_onnx(Path("model.onnx"), 10, 2, 1)


class TestModelDeploymentPackage:
    """Tests for ModelDeploymentPackage class."""

    def test_init(self):
        """Test package builder initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            package = ModelDeploymentPackage(output_dir=tmpdir)
            assert package.output_dir == Path(tmpdir)

    def test_compute_checksum(self):
        """Test checksum computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            package = ModelDeploymentPackage(output_dir=tmpdir)

            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello, World!")

            checksum = package._compute_checksum(test_file)
            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA256 hex digest

    def test_create_package(self):
        """Test creating deployment package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            package = ModelDeploymentPackage(output_dir=tmpdir)

            # Create dummy model file
            model_file = Path(tmpdir) / "model.onnx"
            model_file.write_bytes(b"dummy model content")

            thresholds = ThresholdConfig(blur_threshold=0.6)
            metrics = {"mAP": 0.88, "f1": 0.85}

            manifest = package.create_package(
                model_name="test_model",
                version="1.0.0",
                model_files={"onnx": model_file},
                thresholds=thresholds,
                metrics=metrics,
            )

            assert manifest.model_name == "test_model"
            assert manifest.version == "1.0.0"
            assert "onnx" in manifest.checksums
            assert (Path(tmpdir) / "manifest.json").exists()
            assert (Path(tmpdir) / "thresholds.json").exists()

    def test_load_manifest(self):
        """Test loading manifest from package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manifest file
            manifest_data = {
                "model_name": "test_model",
                "version": "1.0.0",
                "model_files": {"onnx": "model.onnx"},
                "thresholds": {"blur_threshold": 0.6},
                "metrics": {"accuracy": 0.95},
                "checksums": {"onnx": "abc123"},
                "created_at": "2025-01-15T10:00:00Z",
                "requirements": {},
            }
            manifest_path = Path(tmpdir) / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest_data, f)

            package = ModelDeploymentPackage(output_dir=tmpdir)
            loaded = package.load_manifest()

            assert loaded.model_name == "test_model"
            assert loaded.version == "1.0.0"
            assert loaded.thresholds.blur_threshold == 0.6

    def test_verify_package_success(self):
        """Test package verification with valid checksums."""
        with tempfile.TemporaryDirectory() as tmpdir:
            package = ModelDeploymentPackage(output_dir=tmpdir)

            # Create model file
            model_file = Path(tmpdir) / "model.onnx"
            model_file.write_bytes(b"dummy content")

            # Create package
            thresholds = ThresholdConfig()
            manifest = package.create_package(
                model_name="test_model",
                version="1.0.0",
                model_files={"onnx": model_file},
                thresholds=thresholds,
                metrics={},
            )

            # Verify
            assert package.verify_package(manifest) is True

    def test_verify_package_failure(self):
        """Test package verification with corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            package = ModelDeploymentPackage(output_dir=tmpdir)

            # Create model file
            model_file = Path(tmpdir) / "model.onnx"
            model_file.write_bytes(b"original content")

            # Create package
            thresholds = ThresholdConfig()
            manifest = package.create_package(
                model_name="test_model",
                version="1.0.0",
                model_files={"onnx": model_file},
                thresholds=thresholds,
                metrics={},
            )

            # Corrupt the file
            model_file.write_bytes(b"corrupted content")

            # Verify should fail
            assert package.verify_package(manifest) is False


class TestModelRegistry:
    """Tests for ModelRegistry class."""

    def test_init(self):
        """Test registry initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)
            assert registry.registry_dir == Path(tmpdir)
            # Registry file is created lazily on first save, or may not exist yet
            assert registry._registry is not None

    def test_register_model(self):
        """Test registering a model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)

            thresholds = ThresholdConfig()
            manifest = ModelManifest(
                model_name="test_model",
                version="1.0.0",
                model_files={"onnx": "model.onnx"},
                thresholds=thresholds,
                metrics={"accuracy": 0.95},
                checksums={"onnx": "abc123"},
                created_at="2025-01-15T10:00:00Z",
            )

            model_id = registry.register_model(
                manifest,
                package_path="/path/to/package",
                tags=["production", "v1"],
            )

            assert model_id == "test_model:1.0.0"

    def test_get_latest_version(self):
        """Test getting latest version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)

            thresholds = ThresholdConfig()

            # Register multiple versions
            for version in ["1.0.0", "1.1.0", "2.0.0"]:
                manifest = ModelManifest(
                    model_name="test_model",
                    version=version,
                    model_files={},
                    thresholds=thresholds,
                    metrics={},
                    checksums={},
                    created_at="2025-01-15T10:00:00Z",
                )
                registry.register_model(manifest, "/path")

            latest = registry.get_latest_version("test_model")
            assert latest == "2.0.0"

    def test_get_latest_version_not_found(self):
        """Test getting latest version for non-existent model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)
            latest = registry.get_latest_version("non_existent")
            assert latest is None

    def test_get_model_info(self):
        """Test getting model information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)

            thresholds = ThresholdConfig()
            manifest = ModelManifest(
                model_name="test_model",
                version="1.0.0",
                model_files={"onnx": "model.onnx"},
                thresholds=thresholds,
                metrics={"accuracy": 0.95},
                checksums={},
                created_at="2025-01-15T10:00:00Z",
            )
            registry.register_model(manifest, "/path")

            info = registry.get_model_info("test_model", "1.0.0")
            assert info is not None
            assert info["manifest"]["model_name"] == "test_model"
            assert info["manifest"]["metrics"]["accuracy"] == 0.95

    def test_list_models(self):
        """Test listing all models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)

            thresholds = ThresholdConfig()

            # Register models
            for name in ["model_a", "model_b"]:
                manifest = ModelManifest(
                    model_name=name,
                    version="1.0.0",
                    model_files={},
                    thresholds=thresholds,
                    metrics={},
                    checksums={},
                    created_at="2025-01-15T10:00:00Z",
                )
                registry.register_model(manifest, "/path")

            models = registry.list_models()
            assert len(models) == 2
            names = [m["name"] for m in models]
            assert "model_a" in names
            assert "model_b" in names

    def test_compare_versions(self):
        """Test comparing model versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)

            thresholds = ThresholdConfig()

            # Register v1
            manifest_v1 = ModelManifest(
                model_name="test_model",
                version="1.0.0",
                model_files={},
                thresholds=thresholds,
                metrics={"accuracy": 0.90, "f1": 0.85},
                checksums={},
                created_at="2025-01-15T10:00:00Z",
            )
            registry.register_model(manifest_v1, "/path")

            # Register v2
            manifest_v2 = ModelManifest(
                model_name="test_model",
                version="2.0.0",
                model_files={},
                thresholds=thresholds,
                metrics={"accuracy": 0.95, "f1": 0.90},
                checksums={},
                created_at="2025-01-15T12:00:00Z",
            )
            registry.register_model(manifest_v2, "/path")

            comparison = registry.compare_versions("test_model", "1.0.0", "2.0.0")

            assert comparison["version1"] == "1.0.0"
            assert comparison["version2"] == "2.0.0"
            # Use pytest.approx for floating point comparison
            assert comparison["metrics_diff"]["accuracy"]["diff"] == pytest.approx(0.05)
            assert comparison["metrics_diff"]["f1"]["diff"] == pytest.approx(0.05)

    def test_compare_versions_not_found(self):
        """Test comparing non-existent versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ModelRegistry(registry_dir=tmpdir)

            with pytest.raises(ValueError, match="Version not found"):
                registry.compare_versions("test_model", "1.0.0", "2.0.0")


class TestIntegration:
    """Integration tests for model optimization workflow."""

    def test_full_threshold_tuning_workflow(self):
        """Test complete threshold tuning workflow."""
        # Generate synthetic data
        np.random.seed(42)
        heads = ["blur", "noise", "skew", "illumination", "artifacts"]

        predictions_dict = {}
        labels_dict = {}

        for head in heads:
            predictions_dict[head] = np.concatenate(
                [
                    np.random.uniform(0.0, 0.4, 100),
                    np.random.uniform(0.6, 1.0, 100),
                ]
            )
            labels_dict[head] = np.concatenate(
                [
                    np.zeros(100),
                    np.ones(100),
                ]
            )

        # Tune thresholds
        tuner = ThresholdTuner(metric="f1", num_steps=21)
        config = tuner.tune_all_heads(predictions_dict, labels_dict)

        # Verify all thresholds are reasonable
        assert 0.3 <= config.blur_threshold <= 0.7
        assert 0.3 <= config.noise_threshold <= 0.7
        assert 0.3 <= config.skew_threshold <= 0.7
        assert config.optimized_for == "f1"

    def test_full_package_workflow(self):
        """Test complete package creation and verification workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create package builder
            package = ModelDeploymentPackage(output_dir=tmpdir)

            # Create dummy model files
            models_dir = Path(tmpdir) / "models"
            models_dir.mkdir()
            (models_dir / "student.onnx").write_bytes(b"onnx model")
            (models_dir / "student_int8.onnx").write_bytes(b"int8 model")

            # Create thresholds via tuning
            thresholds = ThresholdConfig(
                blur_threshold=0.55,
                noise_threshold=0.45,
            )

            # Create package
            manifest = package.create_package(
                model_name="student_iqa_resnet18",
                version="1.0.0",
                model_files={
                    "onnx": models_dir / "student.onnx",
                    "int8": models_dir / "student_int8.onnx",
                },
                thresholds=thresholds,
                metrics={"mAP": 0.88, "f1_avg": 0.85},
            )

            # Verify package
            assert package.verify_package(manifest) is True

            # Register in registry
            registry = ModelRegistry(registry_dir=Path(tmpdir) / "registry")
            model_id = registry.register_model(
                manifest,
                package_path=tmpdir,
                tags=["production"],
            )

            assert model_id == "student_iqa_resnet18:1.0.0"

            # Load and verify
            loaded_manifest = package.load_manifest()
            assert loaded_manifest.model_name == manifest.model_name
            assert loaded_manifest.version == manifest.version
