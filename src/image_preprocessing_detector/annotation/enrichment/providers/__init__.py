# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Enrichment providers for the annotation system.

This module contains provider implementations for different enrichment methods,
such as DocLayout-YOLO for layout detection and SigLIP for quality prediction.

Available Providers:
    - YOLOProvider: DocLayout-YOLO layout detection with batch inference
    - SigLIPProvider: Quality score prediction with MOS scores

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers import (
    ...     YOLOProvider,
    ...     SigLIPProvider,
    ... )
    >>>
    >>> yolo = YOLOProvider(model_path="checkpoints/yolo.pt")
    >>> siglip = SigLIPProvider(model_path="checkpoints/siglip2-iqa")
    >>>
    >>> if yolo.is_available():
    ...     enrichment = yolo.enrich(image_path)
    >>> if siglip.is_available():
    ...     quality = siglip.enrich(image_path)
    ...     print(f"MOS: {quality.llm_predicted_mos}")
"""

from __future__ import annotations

from .base import EnrichmentProvider, QualityScoreProvider
from .siglip import SigLIPProvider
from .yolo import YOLOProvider

__all__ = [
    "EnrichmentProvider",
    "QualityScoreProvider",
    "SigLIPProvider",
    "YOLOProvider",
]
