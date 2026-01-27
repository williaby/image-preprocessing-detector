# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""CPU/GPU separated annotation pipeline.

CRITICAL: ML providers MUST NOT run inside ProcessPoolExecutor.
GPU models cannot be pickled/forked - they must run in main thread
or a dedicated GPU process.

Pipeline Architecture:
  Stage 1 (CPU Pool): Hash files + parse labels → emit ParsedSample
  Stage 2 (GPU Thread): Batch inference → emit EnrichedSample
  Stage 3 (IO Thread): Write results → checkpoint

Design Notes:
    - CPU stage uses ProcessPoolExecutor for true parallelism
    - GPU stage uses single thread (CUDA cannot be forked)
    - IO stage uses single thread for sequential writes
    - Queues are bounded to prevent memory exhaustion
    - Checkpointing enables resumable processing

Example:
    >>> from image_preprocessing_detector.annotation.workflow.pipeline import (
    ...     AnnotationPipeline,
    ... )
    >>>
    >>> pipeline = AnnotationPipeline(
    ...     settings=settings,
    ...     parser_registry=parsers,
    ...     enrichment_manager=enrichment,
    ...     checkpoint_manager=checkpoints,
    ... )
    >>>
    >>> result = pipeline.process_dataset(
    ...     dataset_name="diqa-5000",
    ...     image_paths=paths,
    ...     dataset_config=config,
    ... )
    >>> print(f"Processed {result.success_count} images")
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any

from ..config.settings import AnnotationSettings
from ..integrity.checkpointing import CheckpointManager
from ..integrity.hashing import compute_full_sha256
from ..monitoring.metrics import get_annotation_metrics
from ..schemas.enrichment import EnrichmentData
from ..schemas.immutable import OriginalLabels
from ..schemas.sample import SampleMetadata

if TYPE_CHECKING:
    from ..enrichment.manager import EnrichmentManager
    from ..monitoring.metrics import AnnotationMetrics
    from ..parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes for Pipeline Stages
# ============================================================================


@dataclass
class ParsedSample:
    """Output from CPU parsing stage.

    Contains the raw parsed data before ML enrichment.

    Attributes:
        image_path: Absolute path to the image file
        relative_path: Path relative to dataset root
        file_hash: Full-file SHA256 hash
        original_labels: Parsed labels from dataset source
        dataset_name: Name of the source dataset
    """

    image_path: Path
    relative_path: str
    file_hash: str
    original_labels: OriginalLabels
    dataset_name: str


@dataclass
class EnrichedSample:
    """Output from GPU enrichment stage.

    Contains parsed data plus ML-derived enrichments.

    Attributes:
        parsed: Original ParsedSample
        enrichment: ML enrichment results
        enrichment_errors: Any errors during enrichment
    """

    parsed: ParsedSample
    enrichment: EnrichmentData
    enrichment_errors: list[str] = field(default_factory=list)


@dataclass
class PipelineStats:
    """Statistics from pipeline execution.

    Attributes:
        total_images: Total images submitted
        success_count: Successfully processed images
        error_count: Images with errors
        cpu_time_seconds: Time spent in CPU stage
        parse_time_seconds: Time spent in parse stage
        gpu_time_seconds: Time spent in GPU stage
        io_time_seconds: Time spent in IO stage
        images_per_second: Throughput metric
    """

    total_images: int = 0
    success_count: int = 0
    error_count: int = 0
    cpu_time_seconds: float = 0.0
    parse_time_seconds: float = 0.0
    gpu_time_seconds: float = 0.0
    io_time_seconds: float = 0.0
    images_per_second: float = 0.0


@dataclass
class PipelineResult:
    """Result of processing a dataset through the pipeline.

    Attributes:
        dataset_name: Name of processed dataset
        samples: List of processed SampleMetadata
        errors: List of (path, error) tuples for failed images
        stats: Pipeline execution statistics
    """

    dataset_name: str
    samples: list[SampleMetadata] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    stats: PipelineStats = field(default_factory=PipelineStats)

    @property
    def success_count(self) -> int:
        """Number of successfully processed images."""
        return len(self.samples)

    @property
    def error_count(self) -> int:
        """Number of failed images."""
        return len(self.errors)


# ============================================================================
# CPU Stage Worker Function (Must be top-level for ProcessPoolExecutor)
# ============================================================================


def _parse_single_image(
    image_path: Path,
    dataset_path: Path,
    dataset_name: str,
    _parser_config: dict[str, Any],
) -> ParsedSample | tuple[Path, str]:
    """Parse a single image (runs in worker process).

    This function is called by ProcessPoolExecutor workers.
    It must be a top-level function (not a method) for pickling.

    Args:
        image_path: Absolute path to the image
        dataset_path: Root path of the dataset
        dataset_name: Name of the source dataset
        _parser_config: Configuration for the parser (unused, parsing happens in main)

    Returns:
        ParsedSample on success, or (path, error_message) tuple on failure
    """
    try:
        # Compute file hash (P0-1 fix: full-file SHA256)
        file_hash = compute_full_sha256(image_path)

        # Compute relative path
        try:
            relative_path = str(image_path.relative_to(dataset_path))
        except ValueError:
            relative_path = str(image_path)

        # Create empty OriginalLabels - actual parsing happens in main process
        # (parsers may have state that can't be pickled)
        original_labels = OriginalLabels()

        return ParsedSample(
            image_path=image_path,
            relative_path=relative_path,
            file_hash=file_hash,
            original_labels=original_labels,
            dataset_name=dataset_name,
        )

    except Exception as e:
        logger.exception(f"Failed to hash {image_path}")
        return (image_path, str(e))


# ============================================================================
# Main Pipeline Class
# ============================================================================


class AnnotationPipeline:
    """Three-stage pipeline with CPU/GPU separation.

    Stage 1 (CPU): Parallel file hashing (ProcessPoolExecutor)
    Stage 2 (CPU): Sequential label parsing (main thread - parsers may have state)
    Stage 3 (GPU): Single-thread batched ML inference
    Stage 4 (IO): Batch result assembly with checkpointing

    Note: Label parsing happens in main thread because parsers may:
    - Have cached annotation files (COCO JSON, etc.)
    - Maintain internal state
    - Use non-picklable objects

    Attributes:
        settings: Configuration settings
        parsers: Parser registry for dataset-specific parsing
        enrichment: Enrichment manager for ML inference
        checkpoints: Checkpoint manager for resumability
    """

    def __init__(
        self,
        settings: AnnotationSettings,
        parser_registry: ParserRegistry,
        enrichment_manager: EnrichmentManager,
        checkpoint_manager: CheckpointManager,
    ):
        """Initialize the pipeline.

        Args:
            settings: Annotation configuration settings
            parser_registry: Registry of dataset parsers
            enrichment_manager: Manager for ML enrichment providers
            checkpoint_manager: Manager for checkpointing
        """
        self.settings = settings
        self.parsers = parser_registry
        self.enrichment = enrichment_manager
        self.checkpoints = checkpoint_manager

        # Metrics collection
        self._metrics: AnnotationMetrics = get_annotation_metrics()

        # Inter-stage queues with bounded capacity
        # Bounded queues prevent memory exhaustion
        self._hash_queue: Queue[list[ParsedSample] | None] = Queue(maxsize=4)
        self._parse_queue: Queue[list[ParsedSample] | None] = Queue(maxsize=4)
        self._enrich_queue: Queue[list[EnrichedSample] | None] = Queue(maxsize=4)

        # Pipeline state
        self._errors: list[tuple[Path, str]] = []
        self._stats = PipelineStats()

    def process_dataset(
        self,
        dataset_name: str,
        image_paths: list[Path],
        dataset_config: dict[str, Any],
    ) -> PipelineResult:
        """Process dataset through three-stage pipeline.

        Args:
            dataset_name: Name of the dataset
            image_paths: List of absolute paths to images
            dataset_config: Dataset configuration dictionary

        Returns:
            PipelineResult with processed samples and statistics
        """
        start_time = time.perf_counter()

        # Track active pipelines
        self._metrics.active_pipelines.inc()

        # Reset state
        self._errors = []
        self._stats = PipelineStats(total_images=len(image_paths))

        # Check for resume point
        resume_info = self.checkpoints.get_resume_point(dataset_name)
        if resume_info:
            start_idx = self._find_resume_index(image_paths, resume_info.last_path)
            if start_idx > 0:
                logger.info(
                    f"Resuming {dataset_name} from index {start_idx} "
                    f"(last: {resume_info.last_path})"
                )
                image_paths = image_paths[start_idx:]

        # Result storage
        results: list[SampleMetadata] = []

        # Get parser for this dataset
        parser = self.parsers.get_parser(dataset_name)
        if parser is None:
            logger.error(f"No parser registered for dataset: {dataset_name}")
            return PipelineResult(
                dataset_name=dataset_name,
                errors=[(Path(), f"No parser for {dataset_name}")],
                stats=self._stats,
            )

        # Get dataset path from config
        dataset_path = Path(dataset_config.get("path", self.settings.e_drive_root))

        # Start pipeline stages as threads
        io_thread = threading.Thread(
            target=self._io_stage,
            args=(dataset_name, results),
            name="io-stage",
            daemon=True,
        )
        io_thread.start()

        gpu_thread = threading.Thread(
            target=self._gpu_stage,
            name="gpu-stage",
            daemon=True,
        )
        gpu_thread.start()

        parse_thread = threading.Thread(
            target=self._parse_stage,
            args=(dataset_name, parser, dataset_path, dataset_config),
            name="parse-stage",
            daemon=True,
        )
        parse_thread.start()

        # Stage 1: CPU hashing (runs in main orchestration context)
        cpu_start = time.perf_counter()
        self._cpu_stage(dataset_name, image_paths, dataset_path, dataset_config)
        self._stats.cpu_time_seconds = time.perf_counter() - cpu_start
        self._metrics.record_pipeline_stage("cpu_hash", self._stats.cpu_time_seconds)

        # Wait for pipeline to drain
        parse_thread.join()
        gpu_thread.join()
        io_thread.join()

        # Calculate final stats
        total_time = time.perf_counter() - start_time
        self._stats.success_count = len(results)
        self._stats.error_count = len(self._errors)
        if total_time > 0:
            self._stats.images_per_second = len(results) / total_time

        # Clear checkpoint on success
        if not self._errors:
            self.checkpoints.clear_checkpoint(dataset_name)

        # Track pipeline completion
        self._metrics.active_pipelines.dec()

        logger.info(
            f"Pipeline completed for {dataset_name}: "
            f"{self._stats.success_count} success, "
            f"{self._stats.error_count} errors, "
            f"{self._stats.images_per_second:.1f} img/s"
        )

        return PipelineResult(
            dataset_name=dataset_name,
            samples=results,
            errors=self._errors,
            stats=self._stats,
        )

    def _cpu_stage(
        self,
        dataset_name: str,
        image_paths: list[Path],
        dataset_path: Path,
        config: dict[str, Any],
    ) -> None:
        """Stage 1: Parallel CPU hashing.

        Uses ProcessPoolExecutor for true parallelism.
        Only does file hashing - parsing happens in parse_stage.
        """
        logger.debug(f"CPU stage starting: {len(image_paths)} images")

        with ProcessPoolExecutor(max_workers=self.settings.workers) as executor:
            for batch in self._batches(image_paths, self.settings.batch_size):
                # Submit batch to workers
                futures = {
                    executor.submit(
                        _parse_single_image,
                        p,
                        dataset_path,
                        dataset_name,
                        config,
                    ): p
                    for p in batch
                }

                # Collect results in SUBMISSION ORDER (not completion order)
                # P0 Fix: as_completed() returns non-deterministic order which breaks
                # checkpoint resume. We maintain submission order for deterministic resume.
                hashed_batch: list[ParsedSample] = []
                for original_path in batch:
                    # Find the future for this path
                    future = next(f for f, p in futures.items() if p == original_path)
                    result = future.result()
                    if isinstance(result, ParsedSample):
                        hashed_batch.append(result)
                    else:
                        # Error case: (path, error_message)
                        path, error = result
                        self._errors.append((path, error))
                        self._metrics.pipeline_errors.labels(
                            stage="cpu_hash", error_type="HashError"
                        ).inc()

                # Send to parse stage
                if hashed_batch:
                    self._hash_queue.put(hashed_batch)

        # Signal end of CPU stage
        self._hash_queue.put(None)
        logger.debug("CPU stage complete")

    def _parse_stage(
        self,
        dataset_name: str,
        parser: Any,
        dataset_path: Path,
        _config: dict[str, Any],
    ) -> None:
        """Stage 2: Sequential label parsing.

        Runs in main thread because parsers may have:
        - Cached annotation files
        - Internal state
        - Non-picklable objects
        """
        logger.debug("Parse stage starting")
        parse_start = time.perf_counter()

        while True:
            try:
                batch = self._hash_queue.get(timeout=1.0)
            except Empty:
                continue

            if batch is None:
                break

            # Parse labels for each sample
            parsed_batch: list[ParsedSample] = []
            for sample in batch:
                try:
                    labels = parser.parse(
                        dataset_path,
                        sample.image_path,
                        _config,
                    )
                    # Update with parsed labels
                    parsed_sample = ParsedSample(
                        image_path=sample.image_path,
                        relative_path=sample.relative_path,
                        file_hash=sample.file_hash,
                        original_labels=labels,
                        dataset_name=sample.dataset_name,
                    )
                    parsed_batch.append(parsed_sample)
                except Exception as e:
                    logger.warning(f"Parse failed for {sample.image_path}: {e}")
                    self._errors.append((sample.image_path, str(e)))
                    self._metrics.pipeline_errors.labels(
                        stage="parse", error_type=type(e).__name__
                    ).inc()

            # Send to GPU stage
            if parsed_batch:
                self._parse_queue.put(parsed_batch)

        # Record parse stage timing
        self._stats.parse_time_seconds = time.perf_counter() - parse_start
        self._metrics.record_pipeline_stage("parse", self._stats.parse_time_seconds)

        # Signal end of parse stage
        self._parse_queue.put(None)
        logger.debug("Parse stage complete")

    def _gpu_stage(self) -> None:
        """Stage 3: Single-thread GPU batched inference.

        CRITICAL: Runs in single thread - GPU models cannot be parallelized
        via ProcessPoolExecutor (pickle/fork issues with CUDA).
        """
        logger.debug("GPU stage starting")
        gpu_start = time.perf_counter()

        while True:
            try:
                batch = self._parse_queue.get(timeout=1.0)
            except Empty:
                continue

            if batch is None:
                break

            # Run ML enrichment on batch
            image_paths = [p.image_path for p in batch]

            try:
                enrichment_results = self.enrichment.enrich_batch(image_paths)

                enriched_batch = []
                for parsed, enrich_result in zip(
                    batch, enrichment_results, strict=True
                ):
                    enriched = EnrichedSample(
                        parsed=parsed,
                        enrichment=enrich_result.data,
                        enrichment_errors=enrich_result.errors,
                    )
                    enriched_batch.append(enriched)

                self._enrich_queue.put(enriched_batch)

            except Exception as e:
                logger.exception("GPU enrichment failed for batch")
                # Record error metric
                self._metrics.pipeline_errors.labels(
                    stage="gpu", error_type=type(e).__name__
                ).inc()
                # Put samples with empty enrichment
                enriched_batch = [
                    EnrichedSample(
                        parsed=p,
                        enrichment=EnrichmentData(),
                        enrichment_errors=[str(e)],
                    )
                    for p in batch
                ]
                self._enrich_queue.put(enriched_batch)

        self._stats.gpu_time_seconds = time.perf_counter() - gpu_start
        self._metrics.record_pipeline_stage("gpu", self._stats.gpu_time_seconds)

        # Signal end of GPU stage
        self._enrich_queue.put(None)
        logger.debug("GPU stage complete")

    def _io_stage(
        self,
        dataset_name: str,
        results: list[SampleMetadata],
    ) -> None:
        """Stage 4: Write results with checkpointing.

        Assembles final SampleMetadata and handles checkpointing.
        """
        logger.debug("IO stage starting")
        io_start = time.perf_counter()
        batch_count = 0

        while True:
            try:
                batch = self._enrich_queue.get(timeout=1.0)
            except Empty:
                continue

            if batch is None:
                break

            # Track batch processing time
            batch_start = time.perf_counter()
            batch_errors = 0

            # Convert to SampleMetadata
            for sample in batch:
                try:
                    metadata = self._create_sample_metadata(sample)
                    results.append(metadata)
                except Exception as e:
                    logger.exception(
                        f"Failed to create metadata for {sample.parsed.image_path}"
                    )
                    self._errors.append((sample.parsed.image_path, str(e)))
                    batch_errors += 1
                    self._metrics.pipeline_errors.labels(
                        stage="io", error_type=type(e).__name__
                    ).inc()

            batch_count += 1
            batch_duration = time.perf_counter() - batch_start

            # Record batch metrics
            self._metrics.record_batch_processed(
                dataset=dataset_name,
                batch_size=len(batch),
                duration_seconds=batch_duration,
                success=(batch_errors == 0),
            )

            # Checkpoint every N batches
            if batch_count % self.settings.checkpoint_interval == 0:
                last = batch[-1]
                self.checkpoints.save_checkpoint(
                    dataset_name=dataset_name,
                    processed_count=len(results),
                    last_path=last.parsed.relative_path,
                    last_hash=last.parsed.file_hash,
                )

        self._stats.io_time_seconds = time.perf_counter() - io_start
        self._metrics.record_pipeline_stage("io", self._stats.io_time_seconds)
        logger.debug(f"IO stage complete: {len(results)} samples")

    def _create_sample_metadata(self, sample: EnrichedSample) -> SampleMetadata:
        """Create SampleMetadata from enriched sample.

        Args:
            sample: EnrichedSample with parsed data and enrichment

        Returns:
            Complete SampleMetadata instance
        """
        from datetime import datetime

        from ..integrity.hashing import compute_sample_id
        from ..schemas.immutable import OriginalFileMetadata

        # Generate deterministic sample ID
        sample_id = compute_sample_id(
            sample.parsed.dataset_name,
            sample.parsed.relative_path,
            sample.parsed.file_hash,
        )

        # Create original file metadata with placeholder values
        # (actual image dimensions would require reading the file)
        file_size = (
            sample.parsed.image_path.stat().st_size
            if sample.parsed.image_path.exists()
            else 0
        )
        original_file = OriginalFileMetadata(
            format=sample.parsed.image_path.suffix.lstrip(".").lower(),
            width_px=0,  # Placeholder - actual value requires reading image
            height_px=0,  # Placeholder
            channels=3,  # Default RGB
            bit_depth=8,  # Default 8-bit
            file_size_bytes=file_size,
            dpi=None,
        )

        # Create SampleMetadata with all required fields
        metadata = SampleMetadata(
            id=sample_id,
            file_hash=sample.parsed.file_hash,
            dataset_name=sample.parsed.dataset_name,
            dataset_version="1.0",  # Default version
            original_path=sample.parsed.relative_path,
            original_filename=sample.parsed.image_path.name,
            download_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            original_labels=sample.parsed.original_labels,
            original_file=original_file,
        )

        # Add enrichment if present
        if sample.enrichment.layout_detections or sample.enrichment.quality_overall:
            metadata.add_enrichment(
                data=sample.enrichment,
                created_by="annotation-pipeline",
                method="tier_2_model",
                description="Automated ML enrichment",
            )

        return metadata

    def _find_resume_index(
        self,
        image_paths: list[Path],
        last_path: str,
    ) -> int:
        """Find index to resume from based on last processed path.

        Args:
            image_paths: List of image paths
            last_path: Relative path of last processed image

        Returns:
            Index to resume from (0 if not found)
        """
        for i, path in enumerate(image_paths):
            if str(path).endswith(last_path) or last_path in str(path):
                # Resume from next item
                return i + 1
        return 0

    @staticmethod
    def _batches(items: list[Any], size: int) -> Iterator[list[Any]]:
        """Yield successive batches from items.

        Args:
            items: List of items to batch
            size: Batch size

        Yields:
            Batches of items
        """
        for i in range(0, len(items), size):
            yield items[i : i + size]


__all__ = [
    "AnnotationPipeline",
    "EnrichedSample",
    "ParsedSample",
    "PipelineResult",
    "PipelineStats",
]
