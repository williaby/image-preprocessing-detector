# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Workflow orchestration for the annotation system.

This package provides the annotation pipeline and orchestration logic:

Modules:
    - pipeline.py: Three-stage CPU/GPU/IO pipeline
    - progress.py: Progress tracking and reporting
    - orchestrator.py: Multi-dataset coordination (Phase 2.5)
    - scanner.py: Batch-aware file scanner with checkpointing (Phase 5)

Pipeline Architecture:
    Stage 1 (CPU Pool): Parallel file hashing + label parsing
    Stage 2 (GPU Thread): Single-thread batched ML inference
    Stage 3 (IO Thread): Batch result writing with checkpointing

Design Principles:
    1. CPU/GPU Separation: ML models CANNOT be parallelized via ProcessPoolExecutor
       (pickle/fork issues with CUDA). GPU work runs in a single thread.
    2. Queue-Based Communication: Stages communicate via bounded queues
    3. Checkpointing: Resumable processing with intra-dataset checkpoints
    4. Fail-Safe: Graceful degradation on errors, continue processing

Example:
    >>> from image_preprocessing_detector.annotation.workflow import (
    ...     AnnotationPipeline,
    ...     ParsedSample,
    ...     EnrichedSample,
    ...     BatchScanner,
    ...     ScanConfig,
    ... )
    >>>
    >>> # Create pipeline
    >>> pipeline = AnnotationPipeline(
    ...     settings=settings,
    ...     parser_registry=parsers,
    ...     enrichment_manager=enrichment,
    ...     checkpoint_manager=checkpoints,
    ... )
    >>>
    >>> # Scan dataset with batch accumulation (Phase 5)
    >>> scanner = BatchScanner(ScanConfig(batch_size=100))
    >>> for batch in scanner.scan(dataset_path):
    ...     results = pipeline.process_dataset(
    ...         dataset_name=batch.dataset_name,
    ...         image_paths=batch.paths,
    ...         dataset_config=config,
    ...     )
    ...     scanner.mark_batch_complete(batch)
"""

from __future__ import annotations

from .orchestrator import (
    AnnotationOrchestrator,
    DatasetResult,
    OrchestrationResult,
    create_orchestrator,
)
from .pipeline import (
    AnnotationPipeline,
    EnrichedSample,
    ParsedSample,
    PipelineResult,
    PipelineStats,
)
from .preflight import (
    CheckCategory,
    CheckResult,
    CheckSeverity,
    PreflightChecker,
    PreflightConfig,
    PreflightResult,
    run_preflight_checks,
)
from .progress import (
    ProgressCallback,
    ProgressTracker,
)
from .scanner import (
    BatchScanner,
    LoggingProgressCallback,
    ScanBatch,
    ScanCheckpoint,
    ScanConfig,
    ScanProgress,
)

# Rename to avoid conflict with progress.ProgressCallback
ScannerProgressCallback = LoggingProgressCallback

__all__: list[str] = [
    # Orchestration
    "AnnotationOrchestrator",
    # Pipeline
    "AnnotationPipeline",
    # Scanner (Phase 5)
    "BatchScanner",
    # Pre-flight checks (Phase 5)
    "CheckCategory",
    "CheckResult",
    "CheckSeverity",
    "DatasetResult",
    "EnrichedSample",
    "LoggingProgressCallback",
    "OrchestrationResult",
    "ParsedSample",
    "PipelineResult",
    "PipelineStats",
    "PreflightChecker",
    "PreflightConfig",
    "PreflightResult",
    # Progress
    "ProgressCallback",
    "ProgressTracker",
    "ScanBatch",
    "ScanCheckpoint",
    "ScanConfig",
    "ScanProgress",
    "ScannerProgressCallback",
    "create_orchestrator",
    "run_preflight_checks",
]
