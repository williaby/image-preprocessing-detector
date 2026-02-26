# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Multi-model VLM scoring for handwriting legibility and presence assessment.

Uses OpenRouter vision models with a contact-sheet approach: grids of labeled
handwriting images are sent to multiple models, and per-image scores are
aggregated into a consensus rating stored as Layer 2 metadata.

Submodules:
    config:        LegibilityScorerConfig and model roster.
    prompts:       Contact-sheet prompt builder and response parser.
    contact_sheet: Labeled grid image generator.
    scorer:        HwLegibilityScorer orchestrating per-sheet multi-model scoring.
    aggregator:    Consensus aggregation across model responses.

Typical flow::

    from image_preprocessing_detector.labeling.handwriting.scorer import (
        HwLegibilityScorer,
    )
    from image_preprocessing_detector.labeling.handwriting.config import (
        get_default_config,
    )

    scorer = HwLegibilityScorer(get_default_config())
    results = scorer.score_sheet(sheet_path)
"""
