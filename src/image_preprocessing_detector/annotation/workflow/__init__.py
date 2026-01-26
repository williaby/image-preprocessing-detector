# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Workflow orchestration for the annotation system.

This package provides the annotation pipeline and orchestration logic:

Modules:
    - pipeline.py: Three-stage CPU/GPU/IO pipeline
    - progress.py: Progress tracking and reporting
    - orchestrator.py: Multi-dataset coordination (Phase 2.5)

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
    >>> # Process dataset
    >>> results = pipeline.process_dataset(
    ...     dataset_name="diqa-5000",
    ...     image_paths=paths,
    ...     dataset_config=config,
    ... )
"""

from __future__ import annotations

from .pipeline import (
    AnnotationPipeline,
    EnrichedSample,
    ParsedSample,
    PipelineResult,
    PipelineStats,
)
from .progress import (
    ProgressCallback,
    ProgressTracker,
)

__all__: list[str] = [
    "AnnotationPipeline",
    "EnrichedSample",
    "ParsedSample",
    "PipelineResult",
    "PipelineStats",
    "ProgressCallback",
    "ProgressTracker",
]
