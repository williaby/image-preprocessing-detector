"""Multi-dataset annotation orchestrator.

Replaces subprocess-based incremental wrapper with direct library calls.
Fixes P0-3 (shlex.quote bug) by eliminating subprocess entirely.

This module coordinates annotation across multiple datasets:
    - Discovers images using dataset-specific patterns
    - Processes through the CPU/GPU pipeline
    - Writes to Parquet and JSON storage
    - Tracks progress with checkpointing

Example:
    >>> from image_preprocessing_detector.annotation.workflow.orchestrator import (
    ...     AnnotationOrchestrator,
    ...     create_orchestrator,
    ... )
    >>>
    >>> # Use factory for default configuration
    >>> orchestrator = create_orchestrator(use_yolo=True)
    >>>
    >>> # Process single dataset
    >>> result = orchestrator.process_dataset("diqa-5000")
    >>> print(f"Processed {result.samples_processed} samples")
    >>>
    >>> # Or process all datasets
    >>> results = orchestrator.process_all(resume=True)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..config.datasets import DATASET_CONFIGS, DatasetConfig, get_dataset_path
from ..config.settings import AnnotationSettings
from ..integrity.checkpointing import CheckpointManager
from ..storage.parquet_writer import PartitionedParquetWriter
from .pipeline import AnnotationPipeline, PipelineResult
from .progress import ProgressTracker

if TYPE_CHECKING:
    from ..enrichment.manager import EnrichmentManager
    from ..parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Result Data Classes
# ============================================================================


@dataclass
class DatasetResult:
    """Result of processing a single dataset.

    Attributes:
        dataset_name: Name of the processed dataset
        success: True if processing completed without fatal errors
        samples_processed: Number of samples successfully processed
        samples_failed: Number of samples that failed processing
        errors: List of error messages
        duration_seconds: Total processing time
    """

    dataset_name: str
    success: bool
    samples_processed: int
    samples_failed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class OrchestrationResult:
    """Result of processing multiple datasets.

    Attributes:
        dataset_results: Results for each processed dataset
        total_samples: Total samples across all datasets
        total_errors: Total errors across all datasets
        duration_seconds: Total orchestration time
    """

    dataset_results: list[DatasetResult] = field(default_factory=list)
    total_samples: int = 0
    total_errors: int = 0
    duration_seconds: float = 0.0

    @property
    def success_count(self) -> int:
        """Number of datasets that completed successfully."""
        return sum(1 for r in self.dataset_results if r.success)

    @property
    def failure_count(self) -> int:
        """Number of datasets that failed."""
        return sum(1 for r in self.dataset_results if not r.success)


# ============================================================================
# Main Orchestrator Class
# ============================================================================


class AnnotationOrchestrator:
    """Orchestrate multi-dataset annotation.

    Direct replacement for subprocess-based incremental processing.
    All configuration and state managed in-process.

    Attributes:
        settings: Annotation configuration settings
        parsers: Parser registry for label extraction
        enrichment: Enrichment manager for ML inference
        checkpoints: Checkpoint manager for resumable processing
        parquet_writer: Writer for Parquet output
        progress: Progress tracker for monitoring
    """

    def __init__(
        self,
        settings: AnnotationSettings,
        parser_registry: ParserRegistry,
        enrichment_manager: EnrichmentManager,
        checkpoint_manager: CheckpointManager | None = None,
        parquet_writer: PartitionedParquetWriter | None = None,
        progress_tracker: ProgressTracker | None = None,
    ):
        """Initialize orchestrator with dependencies.

        Args:
            settings: Annotation configuration settings
            parser_registry: Registry of dataset parsers
            enrichment_manager: Manager for ML enrichment providers
            checkpoint_manager: Optional checkpoint manager (created if None)
            parquet_writer: Optional Parquet writer (created if None)
            progress_tracker: Optional progress tracker (created if None)
        """
        self.settings = settings
        self.parsers = parser_registry
        self.enrichment = enrichment_manager

        # Create optional components if not provided
        self.checkpoints = checkpoint_manager or CheckpointManager(
            settings.checkpoint_dir
        )
        self.parquet_writer = parquet_writer or PartitionedParquetWriter(
            settings.metadata_root / "parquet"
        )
        self.progress = progress_tracker or ProgressTracker()

        logger.info("AnnotationOrchestrator initialized")

    def process_dataset(
        self,
        dataset_name: str,
        use_yolo: bool = True,
        max_samples: int | None = None,
    ) -> DatasetResult:
        """Process a single dataset.

        Directly callable - no subprocess involved (P0-3 fix).

        Args:
            dataset_name: Name of dataset from DATASET_CONFIGS
            use_yolo: Whether to use YOLO enrichment
            max_samples: Optional limit on samples to process

        Returns:
            DatasetResult with processing status and metrics
        """
        start_time = time.perf_counter()

        # Validate dataset exists
        if dataset_name not in DATASET_CONFIGS:
            return DatasetResult(
                dataset_name=dataset_name,
                success=False,
                samples_processed=0,
                errors=[f"Unknown dataset: {dataset_name}"],
                duration_seconds=time.perf_counter() - start_time,
            )

        config = DATASET_CONFIGS[dataset_name]

        logger.info(f"Processing dataset: {dataset_name}")

        try:
            # Discover images
            image_paths = self._discover_images(config, max_samples)
            if not image_paths:
                logger.warning(f"No images found for {dataset_name}")
                return DatasetResult(
                    dataset_name=dataset_name,
                    success=True,  # Not an error, just empty
                    samples_processed=0,
                    errors=[],
                    duration_seconds=time.perf_counter() - start_time,
                )

            logger.info(f"Found {len(image_paths)} images in {dataset_name}")

            # Build enrichment manager (disable YOLO if requested)
            enrichment = self.enrichment if use_yolo else self._empty_enrichment()

            # Build pipeline
            pipeline = AnnotationPipeline(
                settings=self.settings,
                parser_registry=self.parsers,
                enrichment_manager=enrichment,
                checkpoint_manager=self.checkpoints,
            )

            # Process through pipeline
            result: PipelineResult = pipeline.process_dataset(
                dataset_name=dataset_name,
                image_paths=image_paths,
                dataset_config=self._config_to_dict(config),
            )

            # Write outputs
            if result.samples:
                self._write_outputs(dataset_name, result)

            # Build result
            # P0 Fix: Partial failures should NOT be marked as complete success.
            # A dataset is only successful if ALL samples processed without errors.
            error_messages = [str(err) for _, err in result.errors]
            is_complete_success = result.error_count == 0 and result.success_count > 0
            return DatasetResult(
                dataset_name=dataset_name,
                success=is_complete_success,
                samples_processed=result.success_count,
                samples_failed=result.error_count,
                errors=error_messages,
                duration_seconds=time.perf_counter() - start_time,
            )

        except Exception as e:
            logger.exception(f"Failed to process {dataset_name}")
            return DatasetResult(
                dataset_name=dataset_name,
                success=False,
                samples_processed=0,
                errors=[str(e)],
                duration_seconds=time.perf_counter() - start_time,
            )

    def process_all(
        self,
        dataset_names: list[str] | None = None,
        resume: bool = True,
        use_yolo: bool = True,
        max_samples_per_dataset: int | None = None,
    ) -> OrchestrationResult:
        """Process multiple datasets.

        Args:
            dataset_names: List of datasets to process (all if None)
            resume: Skip already-completed datasets
            use_yolo: Whether to use YOLO enrichment
            max_samples_per_dataset: Optional per-dataset sample limit

        Returns:
            OrchestrationResult with aggregate statistics
        """
        start_time = time.perf_counter()

        # Determine which datasets to process
        datasets = dataset_names or list(DATASET_CONFIGS.keys())
        results: list[DatasetResult] = []

        for dataset_name in datasets:
            # Check if already completed (if resuming)
            if resume and self._is_completed(dataset_name):
                logger.info(f"Skipping completed dataset: {dataset_name}")
                continue

            # Process dataset
            result = self.process_dataset(
                dataset_name=dataset_name,
                use_yolo=use_yolo,
                max_samples=max_samples_per_dataset,
            )
            results.append(result)

            # Mark completion status
            if result.success:
                self._mark_completed(dataset_name)
            else:
                self._mark_failed(dataset_name, result.errors)

        # Build aggregate result
        total_samples = sum(r.samples_processed for r in results)
        total_errors = sum(r.samples_failed for r in results)

        return OrchestrationResult(
            dataset_results=results,
            total_samples=total_samples,
            total_errors=total_errors,
            duration_seconds=time.perf_counter() - start_time,
        )

    def get_pending_datasets(self) -> list[str]:
        """Get list of datasets that haven't been processed.

        Returns:
            List of dataset names not yet completed
        """
        return [name for name in DATASET_CONFIGS if not self._is_completed(name)]

    def reset_dataset(self, dataset_name: str) -> bool:
        """Reset a dataset for reprocessing.

        Removes checkpoints and Parquet data.

        Args:
            dataset_name: Dataset to reset

        Returns:
            True if reset successful
        """
        try:
            # Clear checkpoint
            self.checkpoints.clear_checkpoint(dataset_name)
            # Clear Parquet data
            self.parquet_writer.delete_dataset(dataset_name)
        except Exception:
            logger.exception(f"Failed to reset {dataset_name}")
            return False
        else:
            return True

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _discover_images(
        self,
        config: DatasetConfig,
        max_samples: int | None = None,
    ) -> list[Path]:
        """Discover images in a dataset directory.

        Args:
            config: Dataset configuration
            max_samples: Optional limit on number of images

        Returns:
            Sorted list of image paths
        """
        dataset_path = get_dataset_path(config, self.settings)

        if not dataset_path.exists():
            logger.warning(f"Dataset path does not exist: {dataset_path}")
            return []

        # Glob for images using dataset pattern
        pattern = config.pattern
        image_paths = sorted(dataset_path.glob(pattern))

        # Apply sample limit if specified
        if max_samples is not None and len(image_paths) > max_samples:
            image_paths = image_paths[:max_samples]

        return image_paths

    def _config_to_dict(self, config: DatasetConfig) -> dict:
        """Convert DatasetConfig to dict for pipeline.

        Args:
            config: Dataset configuration

        Returns:
            Dictionary with configuration values
        """
        return {
            "name": config.name,
            "path_suffix": config.path_suffix,
            "pattern": config.pattern,
            "capture_method": config.capture_method,
            "domain": config.domain,
            "is_benchmark": config.is_benchmark,
            "has_human_mos": config.has_human_mos,
            "has_table": config.has_table,
            "has_formula": config.has_formula,
            "has_handwriting": config.has_handwriting,
            "has_signature": config.has_signature,
            "parser_name": config.parser_name,
            "has_coco_annotations": config.has_coco_annotations,
            "arrow_format": config.arrow_format,
            "has_paired_gt": config.has_paired_gt,
            "iso639_language": config.iso639_language,
            "iso15924_script": config.iso15924_script,
            "text_scope": config.text_scope,
            "paper_size": config.paper_size,
            "mos_file": config.mos_file,
        }

    def _write_outputs(self, dataset_name: str, result: PipelineResult) -> None:
        """Write pipeline results to storage.

        Args:
            dataset_name: Name of the dataset
            result: Pipeline processing result
        """
        # Write to Parquet
        count = self.parquet_writer.write_dataset(dataset_name, result.samples)
        logger.info(f"Wrote {count} samples to Parquet for {dataset_name}")

    def _empty_enrichment(self) -> EnrichmentManager:
        """Create an empty enrichment manager (no providers)."""
        from ..enrichment.manager import EnrichmentManager

        return EnrichmentManager([])

    def _is_completed(self, dataset_name: str) -> bool:
        """Check if a dataset has been completed.

        Uses Parquet storage to determine completion - if data exists,
        the dataset has been processed.
        """
        # Check if dataset has data in Parquet storage
        return dataset_name in self.parquet_writer.list_datasets()

    def _mark_completed(self, dataset_name: str) -> None:
        """Mark a dataset as completed.

        Clears the checkpoint since processing is complete.
        """
        # Clear checkpoint on successful completion
        self.checkpoints.clear_checkpoint(dataset_name)
        logger.info(f"Dataset {dataset_name} marked as completed")

    def _mark_failed(self, dataset_name: str, errors: list[str]) -> None:
        """Mark a dataset as failed with errors.

        Logs the errors but preserves checkpoint for retry.
        """
        error_msg = "; ".join(errors[:3])  # Truncate to first 3 errors
        logger.error(f"Dataset {dataset_name} failed: {error_msg}")


# ============================================================================
# Factory Function
# ============================================================================


def create_orchestrator(
    settings: AnnotationSettings | None = None,
    use_yolo: bool = True,
) -> AnnotationOrchestrator:
    """Factory function to create fully-configured orchestrator.

    Centralizes dependency creation for testability.
    This is the primary entry point for using the annotation system.

    Args:
        settings: Optional settings (loaded from env if None)
        use_yolo: Whether to configure YOLO enrichment provider

    Returns:
        Configured AnnotationOrchestrator instance

    Example:
        >>> orchestrator = create_orchestrator()
        >>> result = orchestrator.process_dataset("diqa-5000")
    """
    # Load settings from environment if not provided
    if settings is None:
        settings = AnnotationSettings.from_env()

    # Create parser registry with all dataset parsers
    from ..parsers.registry import ParserRegistry

    parser_registry = ParserRegistry.create_default()

    # Create enrichment manager with optional YOLO
    from ..enrichment.manager import EnrichmentManager
    from ..enrichment.providers.base import EnrichmentProvider

    providers: list[EnrichmentProvider] = []

    if use_yolo:
        from ..enrichment.providers.yolo import YOLOProvider

        yolo = YOLOProvider(
            model_path=str(settings.yolo_model_path)
            if settings.yolo_model_path
            else None,
            confidence_threshold=settings.yolo_confidence_threshold,
        )
        if yolo.is_available():
            providers.append(yolo)
            logger.info("YOLO provider enabled")
        else:
            logger.warning("YOLO provider not available (model not found or no GPU)")

    enrichment_manager = EnrichmentManager(providers)

    # Create checkpoint manager
    checkpoint_manager = CheckpointManager(settings.checkpoint_dir)

    # Create Parquet writer
    parquet_writer = PartitionedParquetWriter(settings.metadata_root / "parquet")

    return AnnotationOrchestrator(
        settings=settings,
        parser_registry=parser_registry,
        enrichment_manager=enrichment_manager,
        checkpoint_manager=checkpoint_manager,
        parquet_writer=parquet_writer,
    )


__all__ = [
    "AnnotationOrchestrator",
    "DatasetResult",
    "OrchestrationResult",
    "create_orchestrator",
]
