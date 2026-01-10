"""Arena benchmark runner for standardized model evaluation.

This module provides the ArenaRunner class that orchestrates benchmark
execution with deterministic inference, metric computation, and
reproducibility manifest generation.
"""

from __future__ import annotations

import contextlib
import platform
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import structlog
from PIL import Image

from image_preprocessing_detector.labeling.arena.datasets.base import (
    BenchmarkDataset,
    DatasetSample,
)
from image_preprocessing_detector.labeling.arena.inference.base import (
    InferenceBackend,
    InferenceConfig,
    InferenceError,
    ModelLoadError,
    create_backend,
)
from image_preprocessing_detector.labeling.arena.metrics import ArenaMetrics
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
from image_preprocessing_detector.labeling.model_spec import ModelSpec

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = structlog.get_logger(__name__)


@dataclass
class RunConfig:
    """Configuration for a benchmark run.

    Attributes:
        output_dir: Directory for saving results and manifests.
        save_sample_results: Whether to include per-sample results.
        save_manifest: Whether to generate reproducibility manifest.
        warmup_iterations: Number of warmup inference passes.
        progress_interval: Log progress every N samples.
        max_samples: Maximum samples to process (None for all).
        fail_fast: Stop on first inference error.
    """

    output_dir: Path | None = None
    save_sample_results: bool = False
    save_manifest: bool = True
    warmup_iterations: int = 3
    progress_interval: int = 100
    max_samples: int | None = None
    fail_fast: bool = False

    def __post_init__(self) -> None:
        """Convert output_dir to Path if string."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)


@dataclass
class RunContext:
    """Internal context for tracking run state.

    Attributes:
        run_id: Unique identifier for this run.
        start_time: Unix timestamp when run started.
        predictions: Dict mapping dimension to list of predictions.
        ground_truth: Dict mapping dimension to list of ground truth.
        sample_results: Per-sample detailed results.
        inference_times: List of inference times in ms.
        errors: List of (sample_id, error_message) tuples.
    """

    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    start_time: float = 0.0
    predictions: dict[str, list[float]] = field(default_factory=dict)
    ground_truth: dict[str, list[float]] = field(default_factory=dict)
    sample_results: list[SampleResult] = field(default_factory=list)
    inference_times: list[float] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize prediction and ground truth dicts."""
        for dim in ["overall", "sharpness", "color"]:
            self.predictions[dim] = []
            self.ground_truth[dim] = []


class ArenaRunner:
    """Orchestrates benchmark execution for model evaluation.

    The ArenaRunner handles:
    - Model loading via inference backends
    - Dataset iteration with batching
    - Deterministic inference execution
    - Metric computation (PLCC, SRCC, MAE, RMSE)
    - Result serialization and manifest generation

    Example:
        >>> from image_preprocessing_detector.labeling.arena.runner import ArenaRunner
        >>> from image_preprocessing_detector.labeling.arena.datasets.diqa5000 import (
        ...     DIQA5000Dataset,
        ... )
        >>> from image_preprocessing_detector.labeling.model_spec import (
        ...     ModelSpec,
        ...     ModelSource,
        ... )
        >>>
        >>> spec = ModelSpec(
        ...     source=ModelSource.HUGGINGFACE,
        ...     id="your-model/diqa-scorer",
        ...     revision="main",
        ... )
        >>> dataset = DIQA5000Dataset("/data/diqa5000", split="test")
        >>> runner = ArenaRunner()
        >>> result = runner.run(spec, dataset)
        >>> print(result.metrics["aggregate"])
    """

    def __init__(
        self,
        inference_config: InferenceConfig | None = None,
        run_config: RunConfig | None = None,
    ) -> None:
        """Initialize the ArenaRunner.

        Args:
            inference_config: Configuration for inference execution.
            run_config: Configuration for the benchmark run.
        """
        self._inference_config = inference_config or InferenceConfig()
        self._run_config = run_config or RunConfig()
        self._backend: InferenceBackend | None = None

    def run(
        self,
        model_spec: ModelSpec,
        dataset: BenchmarkDataset,
        inference_config: InferenceConfig | None = None,
        run_config: RunConfig | None = None,
    ) -> BenchmarkResult:
        """Execute a complete benchmark run.

        Args:
            model_spec: Specification of the model to evaluate.
            dataset: Benchmark dataset to evaluate on.
            inference_config: Override inference configuration.
            run_config: Override run configuration.

        Returns:
            BenchmarkResult with metrics and metadata.

        Raises:
            ModelLoadError: If model cannot be loaded.
            InferenceError: If inference fails and fail_fast is True.
        """
        config = inference_config or self._inference_config
        run_cfg = run_config or self._run_config
        context = RunContext()

        logger.info(
            "arena_run_starting",
            run_id=context.run_id,
            model_id=model_spec.id,
            model_variant=model_spec.variant.value,
            dataset=dataset.name,
            num_samples=len(dataset),
        )

        context.start_time = time.perf_counter()

        try:
            # Step 1: Load model
            self._load_model(model_spec, config)

            # Step 2: Warmup inference
            self._warmup(run_cfg.warmup_iterations)

            # Step 3: Run inference on dataset
            self._run_inference(dataset, config, run_cfg, context)

            # Step 4: Compute metrics
            metrics = self._compute_metrics(context)

            # Step 5: Build result
            result = self._build_result(
                context=context,
                model_spec=model_spec,
                dataset=dataset,
                config=config,
                metrics=metrics,
                status=RunStatus.COMPLETED,
            )

            # Step 6: Save outputs
            if run_cfg.output_dir:
                self._save_outputs(result, run_cfg)

            logger.info(
                "arena_run_completed",
                run_id=context.run_id,
                duration_seconds=f"{result.execution.duration_seconds:.2f}",
                aggregate_plcc=f"{metrics.aggregate.plcc:.4f}",
            )

            return result  # noqa: TRY300

        except ModelLoadError as e:
            logger.exception(
                "arena_run_failed_load", run_id=context.run_id, error=str(e)
            )
            return self._build_error_result(
                context, model_spec, dataset, config, str(e)
            )

        except InferenceError as e:
            logger.exception(
                "arena_run_failed_inference", run_id=context.run_id, error=str(e)
            )
            return self._build_error_result(
                context, model_spec, dataset, config, str(e)
            )

        except Exception as e:
            logger.exception("arena_run_failed_unexpected", run_id=context.run_id)
            return self._build_error_result(
                context, model_spec, dataset, config, str(e)
            )

        finally:
            self._unload_model()

    def _load_model(self, spec: ModelSpec, config: InferenceConfig) -> None:
        """Load the model using the appropriate backend."""
        logger.info("loading_model", model_id=spec.id, source=spec.source.value)

        self._backend = create_backend(spec.source.value)
        self._backend.load(spec, config)

        logger.info("model_loaded", model_id=spec.id)

    def _unload_model(self) -> None:
        """Unload the model and free resources."""
        if self._backend is not None:
            with contextlib.suppress(Exception):
                self._backend.unload()
            self._backend = None

    def _warmup(self, iterations: int) -> None:
        """Run warmup inference passes."""
        if self._backend is not None and iterations > 0:
            logger.debug("running_warmup", iterations=iterations)
            self._backend.warmup(iterations)

    def _run_inference(
        self,
        dataset: BenchmarkDataset,
        config: InferenceConfig,
        run_cfg: RunConfig,
        context: RunContext,
    ) -> None:
        """Run inference on all dataset samples."""
        if self._backend is None:
            msg = "Backend not loaded"
            raise InferenceError(msg)

        samples = list(dataset)
        if run_cfg.max_samples:
            samples = samples[: run_cfg.max_samples]

        total_samples = len(samples)
        batch_size = config.batch_size

        logger.info(
            "starting_inference",
            total_samples=total_samples,
            batch_size=batch_size,
        )

        processed = 0
        for batch_start in range(0, total_samples, batch_size):
            batch_end = min(batch_start + batch_size, total_samples)
            batch_samples = samples[batch_start:batch_end]

            try:
                self._process_batch(batch_samples, context, run_cfg.save_sample_results)
            except InferenceError as e:
                if run_cfg.fail_fast:
                    raise
                for sample in batch_samples:
                    context.errors.append((sample.image_id, str(e)))

            processed = batch_end
            if processed % run_cfg.progress_interval == 0 or processed == total_samples:
                logger.info(
                    "inference_progress",
                    processed=processed,
                    total=total_samples,
                    percent=f"{100 * processed / total_samples:.1f}%",
                )

    def _process_batch(
        self,
        samples: list[DatasetSample],
        context: RunContext,
        save_sample_results: bool,
    ) -> None:
        """Process a batch of samples."""
        if self._backend is None:
            msg = "Backend not loaded"
            raise InferenceError(msg)

        # Load images
        images: list[NDArray[np.uint8] | Image.Image] = []
        for sample in samples:
            img = self._load_image(sample)
            if img is not None:
                images.append(img)

        if not images:
            return

        # Run batch inference
        predictions = self._backend.predict_batch(images)

        # Record results
        for sample, pred in zip(samples, predictions, strict=False):
            self._record_result(sample, pred, context, save_sample_results)

    def _load_image(self, sample: DatasetSample) -> NDArray[np.uint8] | None:
        """Load image from sample."""
        # Check if image is already loaded
        if sample.image is not None:
            return sample.image

        # Try to load from path
        if sample.image_path.exists():
            try:
                img = Image.open(sample.image_path)
                return np.array(img.convert("RGB"))
            except Exception as e:
                logger.warning(
                    "failed_to_load_image",
                    image_id=sample.image_id,
                    path=str(sample.image_path),
                    error=str(e),
                )
                return None

        # For synthetic samples, generate a dummy image
        if sample.metadata.get("synthetic"):
            # Generate deterministic dummy image
            seed = hash(sample.image_id) % (2**32)
            rng = np.random.default_rng(seed)
            return rng.integers(0, 255, (224, 224, 3), dtype=np.uint8)

        return None

    def _record_result(
        self,
        sample: DatasetSample,
        prediction: DIQAPrediction,
        context: RunContext,
        save_sample_results: bool,
    ) -> None:
        """Record prediction result for a sample."""
        # Record predictions and ground truth
        for dim in ["overall", "sharpness", "color"]:
            context.predictions[dim].append(getattr(prediction, dim))
            context.ground_truth[dim].append(sample.labels.get(dim, 0.5))

        # Record inference time
        context.inference_times.append(prediction.inference_time_ms)

        # Optionally save detailed sample result
        if save_sample_results:
            gt = DIQAGroundTruth(
                overall=sample.labels.get("overall", 0.5),
                sharpness=sample.labels.get("sharpness", 0.5),
                color=sample.labels.get("color", 0.5),
                image_id=sample.image_id,
                image_path=str(sample.image_path),
                metadata=sample.metadata,
            )
            context.sample_results.append(
                SampleResult(
                    image_id=sample.image_id,
                    prediction=prediction,
                    ground_truth=gt,
                )
            )

    def _compute_metrics(self, context: RunContext) -> ArenaMetrics:
        """Compute arena metrics from predictions."""
        return ArenaMetrics.compute(
            predictions=context.predictions,  # type: ignore[arg-type]
            ground_truth=context.ground_truth,  # type: ignore[arg-type]
        )

    def _build_result(
        self,
        context: RunContext,
        model_spec: ModelSpec,
        dataset: BenchmarkDataset,
        config: InferenceConfig,
        metrics: ArenaMetrics,
        status: RunStatus,
    ) -> BenchmarkResult:
        """Build the benchmark result object."""
        duration = time.perf_counter() - context.start_time

        # Get provenance from backend
        provenance = ProvenanceInfo()
        if self._backend is not None:
            with contextlib.suppress(Exception):
                provenance = self._backend.get_provenance()

        # Build execution info
        execution = ExecutionInfo(
            hardware=self._get_hardware_info(),
            duration_seconds=duration,
            batch_size=config.batch_size,
            seed=config.seed,
            python_version=sys.version.split()[0],
            cuda_version=self._get_cuda_version(),
        )

        # Build dataset info
        dataset_info = DatasetInfo(
            name=dataset.name,
            version=dataset.version,
            split=dataset.current_split,
            num_samples=len(context.predictions["overall"]),
            checksum=dataset.compute_checksum(),
        )

        return BenchmarkResult(
            run_id=context.run_id,
            status=status,
            model_spec=model_spec.to_dict(),
            dataset=dataset_info,
            metrics=metrics.to_dict(),
            execution=execution,
            provenance=provenance,
            sample_results=context.sample_results,
            error_message=None,
        )

    def _build_error_result(
        self,
        context: RunContext,
        model_spec: ModelSpec,
        dataset: BenchmarkDataset,
        config: InferenceConfig,
        error_message: str,
    ) -> BenchmarkResult:
        """Build a result object for a failed run."""
        duration = time.perf_counter() - context.start_time

        execution = ExecutionInfo(
            hardware=self._get_hardware_info(),
            duration_seconds=duration,
            batch_size=config.batch_size,
            seed=config.seed,
            python_version=sys.version.split()[0],
            cuda_version=self._get_cuda_version(),
        )

        dataset_info = DatasetInfo(
            name=dataset.name,
            version=dataset.version,
            split=dataset.current_split,
            num_samples=0,
            checksum=None,
        )

        return BenchmarkResult(
            run_id=context.run_id,
            status=RunStatus.FAILED,
            model_spec=model_spec.to_dict(),
            dataset=dataset_info,
            metrics={},
            execution=execution,
            provenance=ProvenanceInfo(),
            sample_results=[],
            error_message=error_message,
        )

    def _save_outputs(self, result: BenchmarkResult, run_cfg: RunConfig) -> None:
        """Save result and manifest files."""
        if run_cfg.output_dir is None:
            return

        output_dir = run_cfg.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save result JSON
        result_path = output_dir / f"result_{result.run_id}.json"
        result.to_json(result_path)
        result.manifest_path = str(result_path)

        logger.info("result_saved", path=str(result_path))

        # Save reproducibility manifest
        if run_cfg.save_manifest:
            manifest = ReproducibilityManifest.from_benchmark_result(result)
            manifest_path = output_dir / f"manifest_{result.run_id}.yaml"
            manifest.to_yaml(manifest_path)

            logger.info("manifest_saved", path=str(manifest_path))

    def _get_hardware_info(self) -> str:
        """Get hardware description string."""
        info_parts = [platform.processor() or platform.machine()]

        # Try to get GPU info
        try:
            import torch

            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                info_parts.append(f"GPU: {gpu_name}")
        except ImportError:
            pass

        return " | ".join(info_parts)

    def _get_cuda_version(self) -> str | None:
        """Get CUDA version if available."""
        try:
            import torch

            if torch.cuda.is_available():
                return torch.version.cuda
        except ImportError:
            pass

        # Try nvidia-smi fallback
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return f"driver:{result.stdout.strip()}"
        except Exception:  # noqa: S110
            pass

        return None


def run_benchmark(
    model_spec: ModelSpec | dict[str, Any],
    dataset: BenchmarkDataset,
    output_dir: Path | str | None = None,
    batch_size: int = 8,
    device: str = "cuda",
    seed: int = 42,
    save_samples: bool = False,
) -> BenchmarkResult:
    """Convenience function for running a benchmark.

    Args:
        model_spec: ModelSpec or dict representation.
        dataset: Dataset to benchmark on.
        output_dir: Optional output directory.
        batch_size: Batch size for inference.
        device: Device to run on.
        seed: Random seed.
        save_samples: Whether to save per-sample results.

    Returns:
        BenchmarkResult with metrics and metadata.

    Example:
        >>> from image_preprocessing_detector.labeling.arena.runner import run_benchmark
        >>> from image_preprocessing_detector.labeling.arena.datasets.diqa5000 import (
        ...     DIQA5000Dataset,
        ... )
        >>>
        >>> dataset = DIQA5000Dataset("/data/diqa5000")
        >>> spec = {"source": "huggingface", "id": "model/name", "revision": "main"}
        >>> result = run_benchmark(spec, dataset, output_dir="./results")
    """
    # Convert dict to ModelSpec if needed
    if isinstance(model_spec, dict):
        model_spec = ModelSpec.from_dict(model_spec)

    # Create configs
    inference_config = InferenceConfig(
        batch_size=batch_size,
        device=device,
        seed=seed,
        deterministic=True,
    )

    run_config = RunConfig(
        output_dir=Path(output_dir) if output_dir else None,
        save_sample_results=save_samples,
        save_manifest=True,
    )

    # Run benchmark
    runner = ArenaRunner(inference_config, run_config)
    return runner.run(model_spec, dataset)
