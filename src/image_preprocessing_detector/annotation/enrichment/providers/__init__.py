# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Enrichment providers for the annotation system.

This module contains provider implementations for different enrichment methods,
such as DocLayout-YOLO for layout detection and SigLIP for quality prediction.

Available Providers:
    - YOLOProvider: DocLayout-YOLO layout detection with batch inference
    - (Future) SigLIPProvider: Quality score prediction

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers import (
    ...     YOLOProvider,
    ... )
    >>>
    >>> provider = YOLOProvider(model_path="checkpoints/yolo.pt")
    >>> if provider.is_available():
    ...     enrichment = provider.enrich(image_path)
"""

from __future__ import annotations

from .base import EnrichmentProvider, QualityScoreProvider

__all__ = [
    "EnrichmentProvider",
    "QualityScoreProvider",
]
