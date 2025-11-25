"""Model Optimization Module for ONNX Export and INT8 Quantization.

This module provides utilities for:
- Exporting PyTorch models to ONNX format
- INT8 quantization using ONNX Runtime
- TensorRT optimization for GPU deployment (optional)
- Threshold tuning per head for optimal F1 scores
- Model validation and benchmark utilities

Architecture Support:
    - ResNet-50 Teacher Model
    - ResNet-18 Student Model (primary target)

Performance Targets:
    - INT8 CPU speedup: 2-3x over FP32
    - INT8 accuracy drop: <2% mAP
    - TensorRT FP16 GPU speedup: 1.5-2x

Phase 4 Implementation - Milestone 14.1
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Optional ML dependencies
if TYPE_CHECKING:
    import onnx
    import torch
    from onnx import checker

    HAS_TORCH = True
    HAS_ONNX = True
else:
    try:
        import torch

        HAS_TORCH = True
    except ImportError:
        HAS_TORCH = False
        torch: Any = None

    try:
        import onnx
        from onnx import checker

        HAS_ONNX = True
    except ImportError:
        HAS_ONNX = False
        onnx: Any = None
        checker: Any = None

# Use lowercase _has_ort to avoid BasedPyright reportConstantRedefinition
try:
    import onnxruntime as ort
    from onnxruntime.quantization import (
        CalibrationDataReader,
        QuantType,
        quantize_static,
    )

    _has_ort = True
except ImportError:
    _has_ort = False
    ort = None
    QuantType = None
    quantize_static = None
    CalibrationDataReader = object

HAS_ORT = _has_ort


@dataclass
class ONNXExportConfig:
    """Configuration for ONNX model export.

    Attributes:
        opset_version: ONNX opset version (default: 17)
        dynamic_batch: Enable dynamic batch size
        optimize: Apply ONNX optimizer passes
        verify_output: Verify ONNX output matches PyTorch
        input_shape: Input tensor shape (B, C, H, W)
    """

    opset_version: int = 17
    dynamic_batch: bool = True
    optimize: bool = True
    verify_output: bool = True
    input_shape: tuple[int, int, int, int] = (1, 3, 224, 224)


@dataclass
class QuantizationConfig:
    """Configuration for INT8 quantization.

    Attributes:
        quant_format: Quantization format (QInt8, QUInt8)
        per_channel: Use per-channel quantization
        calibration_method: Calibration method (MinMax, Entropy)
        num_calibration_samples: Number of samples for calibration
        accuracy_tolerance: Maximum allowed accuracy drop (as fraction)
    """

    quant_format: str = "QInt8"
    per_channel: bool = True
    calibration_method: str = "MinMax"
    num_calibration_samples: int = 1000
    accuracy_tolerance: float = 0.02  # 2% max accuracy drop


@dataclass
class BenchmarkResult:
    """Results from model benchmarking.

    Attributes:
        model_path: Path to the model file
        model_format: Format (pytorch, onnx, onnx_int8, tensorrt)
        device: Device used (cpu, cuda)
        mean_latency_ms: Mean inference latency
        std_latency_ms: Standard deviation of latency
        p50_latency_ms: 50th percentile latency
        p95_latency_ms: 95th percentile latency
        p99_latency_ms: 99th percentile latency
        throughput_per_sec: Images processed per second
        memory_mb: Peak memory usage in MB
        num_samples: Number of benchmark iterations
    """

    model_path: str
    model_format: str
    device: str
    mean_latency_ms: float
    std_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_per_sec: float
    memory_mb: float
    num_samples: int


@dataclass
class ThresholdConfig:
    """Per-head decision thresholds.

    Attributes:
        blur_threshold: Decision threshold for blur detection
        noise_threshold: Decision threshold for noise detection
        skew_threshold: Decision threshold for skew detection
        illumination_threshold: Decision threshold for illumination issues
        artifacts_threshold: Decision threshold for artifacts detection
        optimized_for: Metric these thresholds were optimized for (f1, precision, recall)
    """

    blur_threshold: float = 0.5
    noise_threshold: float = 0.5
    skew_threshold: float = 0.5
    illumination_threshold: float = 0.5
    artifacts_threshold: float = 0.5
    optimized_for: str = "f1"

    def to_dict(self) -> dict[str, float | str]:
        """Convert to dictionary for serialization."""
        return {
            "blur_threshold": self.blur_threshold,
            "noise_threshold": self.noise_threshold,
            "skew_threshold": self.skew_threshold,
            "illumination_threshold": self.illumination_threshold,
            "artifacts_threshold": self.artifacts_threshold,
            "optimized_for": self.optimized_for,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThresholdConfig":
        """Create from dictionary."""
        return cls(
            blur_threshold=float(data.get("blur_threshold", 0.5)),
            noise_threshold=float(data.get("noise_threshold", 0.5)),
            skew_threshold=float(data.get("skew_threshold", 0.5)),
            illumination_threshold=float(data.get("illumination_threshold", 0.5)),
            artifacts_threshold=float(data.get("artifacts_threshold", 0.5)),
            optimized_for=str(data.get("optimized_for", "f1")),
        )


@dataclass
class ModelManifest:
    """Model deployment manifest with metadata.

    Attributes:
        model_name: Name of the model (e.g., "student_iqa_resnet18")
        version: Model version string
        model_files: Dictionary mapping format to file paths
        thresholds: Per-head decision thresholds
        metrics: Model performance metrics
        checksums: SHA256 checksums for each model file
        created_at: Timestamp of manifest creation
        requirements: Runtime requirements (e.g., onnxruntime version)
    """

    model_name: str
    version: str
    model_files: dict[str, str]
    thresholds: ThresholdConfig
    metrics: dict[str, float]
    checksums: dict[str, str]
    created_at: str
    requirements: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "model_files": self.model_files,
            "thresholds": self.thresholds.to_dict(),
            "metrics": self.metrics,
            "checksums": self.checksums,
            "created_at": self.created_at,
            "requirements": self.requirements,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelManifest":
        """Create from dictionary."""
        return cls(
            model_name=data["model_name"],
            version=data["version"],
            model_files=data["model_files"],
            thresholds=ThresholdConfig.from_dict(data["thresholds"]),
            metrics=data["metrics"],
            checksums=data["checksums"],
            created_at=data["created_at"],
            requirements=data.get("requirements", {}),
        )


class CalibrationDataset(CalibrationDataReader):  # pyright: ignore[reportGeneralTypeIssues]
    """Calibration dataset reader for ONNX Runtime quantization.

    Provides representative data for INT8 calibration.

    Args:
        data_dir: Directory containing calibration images
        num_samples: Maximum number of samples to use
        input_name: Name of the model input tensor
    """

    def __init__(
        self,
        data_dir: str | Path | None = None,
        num_samples: int = 1000,
        input_name: str = "input",
        precomputed_data: np.ndarray | None = None,
    ) -> None:
        """Initialize calibration dataset.

        Args:
            data_dir: Directory containing calibration images
            num_samples: Maximum number of samples to use
            input_name: Name of the model input tensor
            precomputed_data: Precomputed numpy array of calibration data
        """
        self.data_dir = Path(data_dir) if data_dir else None
        self.num_samples = num_samples
        self.input_name = input_name
        self.precomputed_data = precomputed_data
        self._index = 0
        self._data: list[np.ndarray] = []

        if precomputed_data is not None:
            self._data = [precomputed_data[i] for i in range(len(precomputed_data))]
        elif self.data_dir is not None:
            self._load_data()

    def _load_data(self) -> None:
        """Load calibration data from directory."""
        if self.data_dir is None:
            return

        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV not available for loading calibration data")
            return

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        image_files = [
            f for f in self.data_dir.iterdir() if f.suffix.lower() in image_extensions
        ][: self.num_samples]

        for img_path in image_files:
            img = cv2.imread(str(img_path))
            if img is not None:
                preprocessed = self._preprocess_image(img)
                self._data.append(preprocessed)

        logger.info(
            "Loaded calibration data",
            num_samples=len(self._data),
            data_dir=str(self.data_dir),
        )

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input.

        Args:
            image: BGR image array

        Returns:
            Preprocessed array (1, 3, 224, 224), float32
        """
        import cv2

        # Resize to 224x224
        resized = cv2.resize(image, (224, 224), interpolation=cv2.INTER_LINEAR)

        # BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0

        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (normalized - mean) / std

        # HWC to CHW, add batch dimension
        transposed = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(transposed, axis=0)

    def get_next(self) -> dict[str, np.ndarray] | None:
        """Get next calibration sample.

        Returns:
            Dictionary with input name and data, or None if exhausted
        """
        if self._index >= len(self._data):
            return None

        data = self._data[self._index]
        self._index += 1
        return {self.input_name: data}

    def rewind(self) -> None:
        """Reset iterator to beginning."""
        self._index = 0

    def __len__(self) -> int:
        """Return number of samples."""
        return len(self._data)


class ModelOptimizer:
    """Model optimization utilities for export, quantization, and deployment.

    Provides methods for:
    - ONNX export from PyTorch models
    - INT8 quantization via ONNX Runtime
    - TensorRT conversion (optional, GPU)
    - Latency benchmarking
    - Output verification
    """

    def __init__(
        self,
        output_dir: str | Path = "models/optimized",
        device: str = "cpu",
    ) -> None:
        """Initialize model optimizer.

        Args:
            output_dir: Directory for saving optimized models
            device: Target device for benchmarking (cpu, cuda)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = device

        logger.info(
            "ModelOptimizer initialized",
            output_dir=str(self.output_dir),
            device=device,
        )

    def export_to_onnx(
        self,
        model: Any,
        output_path: str | Path,
        config: ONNXExportConfig | None = None,
        model_name: str = "model",
    ) -> Path:
        """Export PyTorch model to ONNX format.

        Args:
            model: PyTorch model (nn.Module)
            output_path: Path for ONNX output file
            config: Export configuration
            model_name: Name for logging

        Returns:
            Path to exported ONNX model

        Raises:
            RuntimeError: If PyTorch or ONNX not available
            ValueError: If model export fails
        """
        if not HAS_TORCH:
            raise RuntimeError("PyTorch not available for ONNX export")
        if not HAS_ONNX:
            raise RuntimeError("ONNX not available for model verification")

        config = config or ONNXExportConfig()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Set model to eval mode
        model.eval()

        # Create dummy input
        dummy_input = torch.randn(config.input_shape)

        # Dynamic axes for batch size
        dynamic_axes = None
        if config.dynamic_batch:
            dynamic_axes = {
                "input": {0: "batch_size"},
            }
            # Add output dynamic axes for multi-head model
            for head_name in ("blur", "noise", "skew", "illumination", "artifacts"):
                dynamic_axes[f"{head_name}_logits"] = {0: "batch_size"}
                dynamic_axes[f"{head_name}_confidence"] = {0: "batch_size"}

        # Export to ONNX
        logger.info(
            "Exporting model to ONNX",
            model_name=model_name,
            output_path=str(output_path),
            opset_version=config.opset_version,
        )

        # Get output names from model architecture
        output_names = []
        for head_name in ("blur", "noise", "skew", "illumination", "artifacts"):
            output_names.extend([f"{head_name}_logits", f"{head_name}_confidence"])

        torch.onnx.export(
            model,
            (dummy_input,),
            str(output_path),
            opset_version=config.opset_version,
            input_names=["input"],
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            do_constant_folding=config.optimize,
        )

        # Verify ONNX model
        onnx_model = onnx.load(str(output_path))
        checker.check_model(onnx_model)

        # Verify output matches PyTorch
        if config.verify_output:
            self._verify_onnx_output(model, output_path, dummy_input)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "ONNX export successful",
            model_name=model_name,
            output_path=str(output_path),
            file_size_mb=f"{file_size_mb:.2f}",
        )

        return output_path

    def _verify_onnx_output(
        self,
        pytorch_model: Any,
        onnx_path: Path,
        test_input: Any,
        rtol: float = 1e-3,
        atol: float = 1e-5,
    ) -> bool:
        """Verify ONNX output matches PyTorch output.

        Args:
            pytorch_model: Original PyTorch model
            onnx_path: Path to ONNX model
            test_input: Test input tensor
            rtol: Relative tolerance
            atol: Absolute tolerance

        Returns:
            True if outputs match within tolerance
        """
        if not HAS_ORT:
            logger.warning("ONNX Runtime not available, skipping verification")
            return True

        # Type narrowing for BasedPyright - after HAS_ORT check, ort is guaranteed non-None
        assert ort is not None  # nosec B101 - type narrowing, not runtime check

        # Get PyTorch output
        pytorch_model.eval()
        with torch.no_grad():
            pytorch_output = pytorch_model(test_input)

        # Get ONNX output
        session = ort.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"]
        )
        input_name = session.get_inputs()[0].name
        onnx_outputs = session.run(None, {input_name: test_input.numpy()})

        # Compare outputs (multi-head model returns dict)
        output_idx = 0
        for head_name in ("blur", "noise", "skew", "illumination", "artifacts"):
            pt_logits = pytorch_output[head_name]["logits"].numpy()
            pt_conf = pytorch_output[head_name]["confidence"].numpy()

            # ONNX Runtime returns numpy arrays
            onnx_logits: np.ndarray = onnx_outputs[output_idx]  # pyright: ignore[reportAssignmentType]
            onnx_conf: np.ndarray = onnx_outputs[output_idx + 1]  # pyright: ignore[reportAssignmentType]
            output_idx += 2

            if not np.allclose(pt_logits, onnx_logits, rtol=rtol, atol=atol):
                logger.error(
                    "ONNX verification failed",
                    head=head_name,
                    output="logits",
                    max_diff=float(np.max(np.abs(pt_logits - onnx_logits))),
                )
                return False

            if not np.allclose(pt_conf, onnx_conf, rtol=rtol, atol=atol):
                logger.error(
                    "ONNX verification failed",
                    head=head_name,
                    output="confidence",
                    max_diff=float(np.max(np.abs(pt_conf - onnx_conf))),
                )
                return False

        logger.info("ONNX verification passed", rtol=rtol, atol=atol)
        return True

    def quantize_int8(
        self,
        onnx_path: str | Path,
        output_path: str | Path,
        config: QuantizationConfig | None = None,
        calibration_data: CalibrationDataset | None = None,
    ) -> Path:
        """Quantize ONNX model to INT8.

        Args:
            onnx_path: Path to input ONNX model (FP32)
            output_path: Path for INT8 quantized output
            config: Quantization configuration
            calibration_data: Calibration dataset for static quantization

        Returns:
            Path to quantized ONNX model

        Raises:
            RuntimeError: If ONNX Runtime quantization not available
        """
        if not HAS_ORT:
            raise RuntimeError("ONNX Runtime not available for quantization")

        # Type narrowing for BasedPyright - after HAS_ORT check, these are guaranteed non-None
        assert QuantType is not None  # nosec B101 - type narrowing, not runtime check
        assert quantize_static is not None  # nosec B101 - type narrowing, not runtime check

        config = config or QuantizationConfig()
        onnx_path = Path(onnx_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting INT8 quantization",
            input_path=str(onnx_path),
            output_path=str(output_path),
            quant_format=config.quant_format,
            per_channel=config.per_channel,
        )

        # Generate synthetic calibration data if not provided
        if calibration_data is None:
            logger.info("Generating synthetic calibration data")
            rng = np.random.default_rng(seed=42)  # Fixed seed for reproducibility
            synthetic_data = rng.standard_normal(
                (config.num_calibration_samples, 3, 224, 224)
            ).astype(np.float32)
            calibration_data = CalibrationDataset(
                precomputed_data=synthetic_data,
                input_name="input",
            )

        # Determine quantization type
        quant_type = (
            QuantType.QInt8 if config.quant_format == "QInt8" else QuantType.QUInt8
        )

        # Run static quantization
        quantize_static(
            model_input=str(onnx_path),
            model_output=str(output_path),
            calibration_data_reader=calibration_data,
            quant_format=quant_type,  # pyright: ignore[reportArgumentType]  # ORT API variance
            per_channel=config.per_channel,
            weight_type=quant_type,
        )

        # Log results
        original_size = onnx_path.stat().st_size / (1024 * 1024)
        quantized_size = output_path.stat().st_size / (1024 * 1024)
        compression_ratio = original_size / quantized_size

        logger.info(
            "INT8 quantization complete",
            original_size_mb=f"{original_size:.2f}",
            quantized_size_mb=f"{quantized_size:.2f}",
            compression_ratio=f"{compression_ratio:.2f}x",
        )

        return output_path

    def convert_to_tensorrt(
        self,
        onnx_path: str | Path,
        output_path: str | Path,
        fp16: bool = True,
        int8: bool = False,
        max_batch_size: int = 8,
    ) -> Path | None:
        """Convert ONNX model to TensorRT engine.

        Args:
            onnx_path: Path to ONNX model
            output_path: Path for TensorRT engine output
            fp16: Enable FP16 precision
            int8: Enable INT8 precision
            max_batch_size: Maximum batch size for optimization

        Returns:
            Path to TensorRT engine, or None if TensorRT unavailable

        Note:
            TensorRT requires NVIDIA GPU and tensorrt package.
        """
        try:
            import tensorrt as trt
        except ImportError:
            logger.warning("TensorRT not available, skipping conversion")
            return None

        onnx_path = Path(onnx_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Converting to TensorRT",
            input_path=str(onnx_path),
            output_path=str(output_path),
            fp16=fp16,
            int8=int8,
        )

        # Create TensorRT builder
        trt_logger = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(trt_logger)
        config = builder.create_builder_config()

        # Set memory pool limit
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB

        # Enable precision modes
        if fp16:
            config.set_flag(trt.BuilderFlag.FP16)
        if int8:
            config.set_flag(trt.BuilderFlag.INT8)

        # Parse ONNX
        network = builder.create_network(
            1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        )
        parser = trt.OnnxParser(network, trt_logger)

        with open(onnx_path, "rb") as f:
            if not parser.parse(f.read()):
                for i in range(parser.num_errors):
                    logger.error("TensorRT parse error", error=parser.get_error(i))
                return None

        # Set optimization profile for dynamic batch size
        profile = builder.create_optimization_profile()
        input_name = network.get_input(0).name
        profile.set_shape(
            input_name,
            min=(1, 3, 224, 224),
            opt=(4, 3, 224, 224),
            max=(max_batch_size, 3, 224, 224),
        )
        config.add_optimization_profile(profile)

        # Build engine
        serialized_engine = builder.build_serialized_network(network, config)
        if serialized_engine is None:
            logger.error("Failed to build TensorRT engine")
            return None

        # Save engine
        with open(output_path, "wb") as f:
            f.write(serialized_engine)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "TensorRT conversion complete",
            output_path=str(output_path),
            file_size_mb=f"{file_size_mb:.2f}",
        )

        return output_path

    def benchmark_model(
        self,
        model_path: str | Path,
        model_format: str = "onnx",
        num_iterations: int = 100,
        warmup_iterations: int = 10,
        batch_size: int = 1,
    ) -> BenchmarkResult:
        """Benchmark model inference latency.

        Args:
            model_path: Path to model file
            model_format: Format (onnx, onnx_int8, tensorrt)
            num_iterations: Number of benchmark iterations
            warmup_iterations: Number of warmup iterations
            batch_size: Input batch size

        Returns:
            BenchmarkResult with latency statistics
        """
        model_path = Path(model_path)

        if model_format in ("onnx", "onnx_int8"):
            return self._benchmark_onnx(
                model_path, num_iterations, warmup_iterations, batch_size
            )
        if model_format == "tensorrt":
            return self._benchmark_tensorrt(
                model_path, num_iterations, warmup_iterations, batch_size
            )
        raise ValueError(f"Unknown model format: {model_format}")

    def _benchmark_onnx(
        self,
        model_path: Path,
        num_iterations: int,
        warmup_iterations: int,
        batch_size: int,
    ) -> BenchmarkResult:
        """Benchmark ONNX model."""
        if not HAS_ORT:
            raise RuntimeError("ONNX Runtime not available for benchmarking")

        # Type narrowing for BasedPyright
        assert ort is not None  # nosec B101 - type narrowing, not runtime check

        # Create session
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if self.device == "cuda"
            else ["CPUExecutionProvider"]
        )
        session = ort.InferenceSession(str(model_path), providers=providers)

        # Get actual provider
        actual_device = "cuda" if "CUDA" in str(session.get_providers()) else "cpu"

        # Create dummy input
        input_name = session.get_inputs()[0].name
        rng = np.random.default_rng(seed=42)  # Fixed seed for reproducibility
        dummy_input = rng.standard_normal((batch_size, 3, 224, 224)).astype(np.float32)

        # Warmup
        for _ in range(warmup_iterations):
            session.run(None, {input_name: dummy_input})

        # Benchmark
        latencies = []
        for _ in range(num_iterations):
            start = time.perf_counter()
            session.run(None, {input_name: dummy_input})
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        latencies_np = np.array(latencies)

        return BenchmarkResult(
            model_path=str(model_path),
            model_format="onnx",
            device=actual_device,
            mean_latency_ms=float(np.mean(latencies_np)),
            std_latency_ms=float(np.std(latencies_np)),
            p50_latency_ms=float(np.percentile(latencies_np, 50)),
            p95_latency_ms=float(np.percentile(latencies_np, 95)),
            p99_latency_ms=float(np.percentile(latencies_np, 99)),
            throughput_per_sec=1000.0 / float(np.mean(latencies_np)) * batch_size,
            memory_mb=0.0,  # Memory tracking requires additional setup
            num_samples=num_iterations,
        )

    def _benchmark_tensorrt(
        self,
        model_path: Path,
        num_iterations: int,
        warmup_iterations: int,
        batch_size: int,
    ) -> BenchmarkResult:
        """Benchmark TensorRT model."""
        try:
            import pycuda.autoinit  # noqa: F401  # pyright: ignore[reportUnusedImport]
            import pycuda.driver as cuda
            import tensorrt as trt
        except ImportError as e:
            raise RuntimeError("TensorRT/PyCUDA not available for benchmarking") from e

        # Load engine
        trt_logger = trt.Logger(trt.Logger.WARNING)
        with open(model_path, "rb") as f:
            engine = trt.Runtime(trt_logger).deserialize_cuda_engine(f.read())

        context = engine.create_execution_context()

        # Allocate buffers
        input_shape = (batch_size, 3, 224, 224)
        input_size = int(np.prod(input_shape) * 4)  # float32

        d_input = cuda.mem_alloc(input_size)
        outputs = []
        d_outputs = []

        for i in range(engine.num_io_tensors):
            name = engine.get_tensor_name(i)
            if engine.get_tensor_mode(name) == trt.TensorIOMode.OUTPUT:
                tensor_shape = engine.get_tensor_shape(name)
                output_shape = (batch_size, *tuple(tensor_shape[1:]))
                size = int(np.prod(output_shape) * 4)
                outputs.append(np.zeros(output_shape, dtype=np.float32))
                d_outputs.append(cuda.mem_alloc(size))

        # Dummy input
        rng = np.random.default_rng(seed=42)  # Fixed seed for reproducibility
        dummy_input = rng.standard_normal(input_shape).astype(np.float32)

        stream = cuda.Stream()

        # Warmup
        for _ in range(warmup_iterations):
            cuda.memcpy_htod_async(d_input, dummy_input, stream)
            context.execute_async_v2(
                [int(d_input)] + [int(d) for d in d_outputs], stream.handle
            )
            stream.synchronize()

        # Benchmark
        latencies = []
        for _ in range(num_iterations):
            start = time.perf_counter()
            cuda.memcpy_htod_async(d_input, dummy_input, stream)
            context.execute_async_v2(
                [int(d_input)] + [int(d) for d in d_outputs], stream.handle
            )
            stream.synchronize()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        latencies_np = np.array(latencies)

        return BenchmarkResult(
            model_path=str(model_path),
            model_format="tensorrt",
            device="cuda",
            mean_latency_ms=float(np.mean(latencies_np)),
            std_latency_ms=float(np.std(latencies_np)),
            p50_latency_ms=float(np.percentile(latencies_np, 50)),
            p95_latency_ms=float(np.percentile(latencies_np, 95)),
            p99_latency_ms=float(np.percentile(latencies_np, 99)),
            throughput_per_sec=1000.0 / float(np.mean(latencies_np)) * batch_size,
            memory_mb=0.0,
            num_samples=num_iterations,
        )


class ThresholdTuner:
    """Threshold tuning utilities for per-head decision optimization.

    Optimizes binary classification thresholds per head to maximize
    F1 score (or other metrics) on validation data.
    """

    def __init__(
        self,
        metric: str = "f1",
        search_range: tuple[float, float] = (0.1, 0.9),
        num_steps: int = 81,
    ) -> None:
        """Initialize threshold tuner.

        Args:
            metric: Metric to optimize (f1, precision, recall)
            search_range: Range of thresholds to search
            num_steps: Number of threshold values to evaluate
        """
        self.metric = metric
        self.search_range = search_range
        self.num_steps = num_steps

        logger.info(
            "ThresholdTuner initialized",
            metric=metric,
            search_range=search_range,
            num_steps=num_steps,
        )

    def find_optimal_threshold(
        self,
        predictions: np.ndarray,
        labels: np.ndarray,
        head_name: str,
    ) -> tuple[float, dict[str, float]]:
        """Find optimal threshold for a single head.

        Args:
            predictions: Model predictions (probabilities), shape (N,)
            labels: Ground truth labels (0 or 1), shape (N,)
            head_name: Name of the head (for logging)

        Returns:
            Tuple of (optimal_threshold, metrics_dict)
        """
        thresholds = np.linspace(
            self.search_range[0], self.search_range[1], self.num_steps
        )

        best_threshold = 0.5
        best_metric = 0.0
        best_metrics = {}

        for threshold in thresholds:
            binary_preds = (predictions >= threshold).astype(int)
            metrics = self._compute_metrics(binary_preds, labels)

            if metrics[self.metric] > best_metric:
                best_metric = metrics[self.metric]
                best_threshold = float(threshold)
                best_metrics = metrics

        logger.info(
            "Found optimal threshold",
            head=head_name,
            threshold=f"{best_threshold:.3f}",
            metric=self.metric,
            value=f"{best_metric:.4f}",
        )

        return best_threshold, best_metrics

    def _compute_metrics(
        self, predictions: np.ndarray, labels: np.ndarray
    ) -> dict[str, float]:
        """Compute classification metrics.

        Args:
            predictions: Binary predictions (0 or 1)
            labels: Ground truth labels (0 or 1)

        Returns:
            Dictionary with precision, recall, f1, accuracy
        """
        tp = np.sum((predictions == 1) & (labels == 1))
        fp = np.sum((predictions == 1) & (labels == 0))
        fn = np.sum((predictions == 0) & (labels == 1))
        tn = np.sum((predictions == 0) & (labels == 0))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (tp + tn) / len(labels) if len(labels) > 0 else 0.0

        return {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "accuracy": float(accuracy),
        }

    def tune_all_heads(
        self,
        predictions_dict: dict[str, np.ndarray],
        labels_dict: dict[str, np.ndarray],
    ) -> ThresholdConfig:
        """Tune thresholds for all heads.

        Args:
            predictions_dict: Dict mapping head name to predictions
            labels_dict: Dict mapping head name to labels

        Returns:
            ThresholdConfig with optimal thresholds
        """
        thresholds = {}
        all_metrics = {}

        for head_name in predictions_dict:
            threshold, metrics = self.find_optimal_threshold(
                predictions_dict[head_name],
                labels_dict[head_name],
                head_name,
            )
            thresholds[head_name] = threshold
            all_metrics[head_name] = metrics

        config = ThresholdConfig(
            blur_threshold=thresholds.get("blur", 0.5),
            noise_threshold=thresholds.get("noise", 0.5),
            skew_threshold=thresholds.get("skew", 0.5),
            illumination_threshold=thresholds.get("illumination", 0.5),
            artifacts_threshold=thresholds.get("artifacts", 0.5),
            optimized_for=self.metric,
        )

        logger.info(
            "Threshold tuning complete",
            thresholds=config.to_dict(),
            avg_f1=np.mean([m["f1"] for m in all_metrics.values()]),
        )

        return config


class ModelDeploymentPackage:
    """Create and manage model deployment packages.

    Packages include:
    - Model files (PyTorch, ONNX, INT8, TensorRT)
    - Configuration files (thresholds, temperature scaling)
    - Manifest with metadata (version, checksums, metrics)
    """

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize deployment package builder.

        Args:
            output_dir: Directory for deployment package
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "ModelDeploymentPackage initialized",
            output_dir=str(self.output_dir),
        )

    def create_package(
        self,
        model_name: str,
        version: str,
        model_files: dict[str, Path],
        thresholds: ThresholdConfig,
        metrics: dict[str, float],
        requirements: dict[str, str] | None = None,
    ) -> ModelManifest:
        """Create deployment package with manifest.

        Args:
            model_name: Name of the model
            version: Model version string
            model_files: Dict mapping format to file paths
            thresholds: Per-head decision thresholds
            metrics: Model performance metrics
            requirements: Runtime requirements

        Returns:
            ModelManifest with package metadata
        """
        requirements = requirements or {
            "onnxruntime": ">=1.15.0",
            "numpy": ">=1.24.0",
        }

        # Copy files and compute checksums
        checksums = {}
        copied_files = {}

        for format_name, source_path in model_files.items():
            source_path = Path(source_path)
            if not source_path.exists():
                logger.warning(f"Model file not found: {source_path}")
                continue

            # Copy to package directory
            dest_path = self.output_dir / source_path.name
            if source_path != dest_path:
                dest_path.write_bytes(source_path.read_bytes())

            # Compute checksum
            checksum = self._compute_checksum(dest_path)
            checksums[format_name] = checksum
            copied_files[format_name] = str(dest_path.name)

        # Create timestamp
        from image_preprocessing_detector.utils.datetime_compat import utc_now

        timestamp = utc_now().isoformat()

        # Create manifest
        manifest = ModelManifest(
            model_name=model_name,
            version=version,
            model_files=copied_files,
            thresholds=thresholds,
            metrics=metrics,
            checksums=checksums,
            created_at=timestamp,
            requirements=requirements,
        )

        # Save manifest
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        # Save thresholds config separately
        thresholds_path = self.output_dir / "thresholds.json"
        with open(thresholds_path, "w") as f:
            json.dump(thresholds.to_dict(), f, indent=2)

        logger.info(
            "Deployment package created",
            model_name=model_name,
            version=version,
            output_dir=str(self.output_dir),
            num_files=len(copied_files),
        )

        return manifest

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def load_manifest(self, manifest_path: str | Path | None = None) -> ModelManifest:
        """Load manifest from package.

        Args:
            manifest_path: Path to manifest.json (default: output_dir/manifest.json)

        Returns:
            ModelManifest instance
        """
        if manifest_path is None:
            manifest_path = self.output_dir / "manifest.json"
        else:
            manifest_path = Path(manifest_path)

        with open(manifest_path) as f:
            data = json.load(f)

        return ModelManifest.from_dict(data)

    def verify_package(self, manifest: ModelManifest | None = None) -> bool:
        """Verify package integrity using checksums.

        Args:
            manifest: Manifest to verify (loads from package if None)

        Returns:
            True if all checksums match
        """
        if manifest is None:
            manifest = self.load_manifest()

        all_valid = True

        for format_name, expected_checksum in manifest.checksums.items():
            file_name = manifest.model_files.get(format_name)
            if file_name is None:
                logger.error(f"Missing file for format: {format_name}")
                all_valid = False
                continue

            file_path = self.output_dir / file_name
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                all_valid = False
                continue

            actual_checksum = self._compute_checksum(file_path)
            if actual_checksum != expected_checksum:
                logger.error(
                    "Checksum mismatch",
                    format=format_name,
                    expected=expected_checksum[:16] + "...",
                    actual=actual_checksum[:16] + "...",
                )
                all_valid = False
            else:
                logger.debug(f"Checksum verified: {format_name}")

        if all_valid:
            logger.info("Package verification passed")
        else:
            logger.error("Package verification failed")

        return all_valid


class ModelRegistry:
    """Model registry for versioning and tracking optimized models.

    Provides:
    - Version management
    - Model comparison
    - Deployment history
    """

    def __init__(self, registry_dir: str | Path = "models/registry") -> None:
        """Initialize model registry.

        Args:
            registry_dir: Directory for registry storage
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "registry.json"

        # Load or initialize registry
        self._registry: dict[str, Any] = self._load_registry()

        logger.info(
            "ModelRegistry initialized",
            registry_dir=str(self.registry_dir),
            num_models=len(self._registry.get("models", {})),
        )

    def _load_registry(self) -> dict[str, Any]:
        """Load registry from disk."""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                data: dict[str, Any] = json.load(f)
                return data
        return {"models": {}, "deployments": []}

    def _save_registry(self) -> None:
        """Save registry to disk."""
        with open(self.registry_file, "w") as f:
            json.dump(self._registry, f, indent=2)

    def register_model(
        self,
        manifest: ModelManifest,
        package_path: str | Path,
        tags: list[str] | None = None,
    ) -> str:
        """Register a new model version.

        Args:
            manifest: Model manifest
            package_path: Path to deployment package
            tags: Optional tags for this version

        Returns:
            Registered model ID
        """
        model_id = f"{manifest.model_name}:{manifest.version}"

        if manifest.model_name not in self._registry["models"]:
            self._registry["models"][manifest.model_name] = {"versions": {}}

        self._registry["models"][manifest.model_name]["versions"][manifest.version] = {
            "manifest": manifest.to_dict(),
            "package_path": str(package_path),
            "tags": tags or [],
            "registered_at": manifest.created_at,
        }

        self._save_registry()

        logger.info(
            "Model registered",
            model_id=model_id,
            tags=tags,
        )

        return model_id

    def get_latest_version(self, model_name: str) -> str | None:
        """Get latest version of a model.

        Args:
            model_name: Name of the model

        Returns:
            Latest version string, or None if not found
        """
        if model_name not in self._registry["models"]:
            return None

        versions: list[str] = list(
            self._registry["models"][model_name]["versions"].keys()
        )
        if not versions:
            return None

        # Sort versions (assumes semantic versioning)
        versions.sort(key=lambda v: [int(x) for x in v.split(".")])
        return versions[-1]

    def get_model_info(
        self, model_name: str, version: str | None = None
    ) -> dict[str, Any] | None:
        """Get model information.

        Args:
            model_name: Name of the model
            version: Version (default: latest)

        Returns:
            Model information dict, or None if not found
        """
        if model_name not in self._registry["models"]:
            return None

        if version is None:
            version = self.get_latest_version(model_name)

        if version is None:
            return None

        result: dict[str, Any] | None = self._registry["models"][model_name][
            "versions"
        ].get(version)
        return result

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered models.

        Returns:
            List of model summaries
        """
        models = []
        for model_name, model_data in self._registry["models"].items():
            versions = list(model_data["versions"].keys())
            latest = self.get_latest_version(model_name)
            models.append(
                {
                    "name": model_name,
                    "versions": versions,
                    "latest_version": latest,
                    "num_versions": len(versions),
                }
            )
        return models

    def compare_versions(
        self, model_name: str, version1: str, version2: str
    ) -> dict[str, Any]:
        """Compare two model versions.

        Args:
            model_name: Name of the model
            version1: First version
            version2: Second version

        Returns:
            Comparison results
        """
        info1 = self.get_model_info(model_name, version1)
        info2 = self.get_model_info(model_name, version2)

        if info1 is None or info2 is None:
            raise ValueError(
                f"Version not found: {model_name}:{version1} or {version2}"
            )

        metrics1 = info1["manifest"]["metrics"]
        metrics2 = info2["manifest"]["metrics"]

        comparison: dict[str, Any] = {
            "version1": version1,
            "version2": version2,
            "metrics_diff": {},
        }

        all_metrics: set[str] = set(metrics1.keys()) | set(metrics2.keys())
        for metric in all_metrics:
            v1 = metrics1.get(metric, 0.0)
            v2 = metrics2.get(metric, 0.0)
            comparison["metrics_diff"][metric] = {
                "version1": v1,
                "version2": v2,
                "diff": v2 - v1,
                "pct_change": ((v2 - v1) / v1 * 100) if v1 != 0 else 0.0,
            }

        return comparison
