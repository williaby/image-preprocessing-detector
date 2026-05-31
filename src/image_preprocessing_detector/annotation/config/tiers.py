"""Tier definitions for enrichment provenance tracking.

This module defines which datasets belong to each enrichment tier,
enabling automatic provenance tracking based on data source.

Tier Definitions:
    - Tier 0 (Exact): Dataset IS 100% this content type by construction
    - Tier 1 (Annotation): Has COCO/JSON annotations for extraction
    - Tier 2 (Model): Requires ML model inference
    - Tier 3 (Heuristic): Dataset-level defaults only

Example:
    >>> from image_preprocessing_detector.annotation.config.tiers import (
    ...     TIER_0_DATASETS,
    ...     TIER_1_DATASETS,
    ...     get_tier_for_dataset,
    ... )
    >>>
    >>> # Check if dataset has exact content flags
    >>> if "tablebank" in TIER_0_DATASETS:
    ...     flags = TIER_0_DATASETS["tablebank"]
    ...     print(f"Has table: {flags['has_table']}")
    >>>
    >>> # Get tier for any dataset
    >>> tier = get_tier_for_dataset("doclaynet")  # Returns "tier_1_annotation"
"""

from __future__ import annotations

from typing import Any

from ..schemas.enums import EnrichmentTier

# =============================================================================
# Tier 0: Exact by Construction
# =============================================================================
# These datasets are 100% guaranteed to contain the specified content type
# because the dataset was specifically created for that content.

TIER_0_DATASETS: dict[str, dict[str, Any]] = {
    # Tables (100% table content)
    "tablebank": {
        "has_table": True,
        "text_scope": "page",
        "description": "Large-scale table detection benchmark",
    },
    "pubtabnet": {
        "has_table": True,
        "text_scope": "page",
        "description": "Scientific publication tables with structure",
    },
    "fintabnet": {
        "has_table": True,
        "text_scope": "page",
        "description": "Financial document tables",
    },
    # Formulas (100% formula content)
    "im2latex": {
        "has_formula": True,
        "text_scope": "phrase",
        "description": "LaTeX formula images",
    },
    "mathverse": {
        "has_formula": True,
        "text_scope": "paragraph",
        "description": "Mathematical expressions and diagrams",
    },
    "maths_handwriting": {
        "has_formula": True,
        "has_handwriting": True,
        "text_scope": "phrase",
        "description": "Handwritten mathematical expressions",
    },
    # Handwriting (100% handwritten content)
    "signatr6k": {
        "has_signature": True,
        "has_handwriting": True,
        "text_scope": "word",
        "description": "Signature verification dataset",
    },
    "nist_sd19": {
        "has_handwriting": True,
        "text_scope": "page",
        "description": "NIST handwriting samples",
    },
    "pucit_ohul": {
        "has_handwriting": True,
        "text_scope": "word",
        "description": "Urdu handwriting dataset",
    },
}


# =============================================================================
# Tier 1: Annotation-based
# =============================================================================
# These datasets have COCO or other structured annotations that can be
# parsed to extract content flags.

TIER_1_DATASETS: set[str] = {
    "doclaynet",
    "tablebank",
    "funsd",
    "pubtabnet",
}


# =============================================================================
# Content Flag Keys
# =============================================================================
# Standard content flag keys used across all tiers

CONTENT_FLAG_KEYS: list[str] = [
    "has_table",
    "has_formula",
    "has_handwriting",
    "has_signature",
    "has_figure",
]


def get_tier_for_dataset(dataset_name: str) -> EnrichmentTier:
    """Determine the enrichment tier for a dataset.

    Args:
        dataset_name (str): Name of the dataset

    Returns:
        EnrichmentTier: EnrichmentTier value for the dataset"""
    if dataset_name in TIER_0_DATASETS:
        return EnrichmentTier.TIER_0_EXACT
    if dataset_name in TIER_1_DATASETS:
        return EnrichmentTier.TIER_1_ANNOTATION
    # Default to model-based or heuristic
    return EnrichmentTier.TIER_2_MODEL


def get_tier_0_flags(dataset_name: str) -> dict[str, Any] | None:
    """Get Tier 0 content flags for a dataset.

    Args:
        dataset_name (str): Name of the dataset

    Returns:
        dict[str, Any] | None: Content flags dict if Tier 0, None otherwise"""
    return TIER_0_DATASETS.get(dataset_name)


def is_tier_0(dataset_name: str) -> bool:
    """Check if dataset is Tier 0 (exact by construction).

    Args:
        dataset_name (str): Name of the dataset

    Returns:
        bool: True if Tier 0, False otherwise"""
    return dataset_name in TIER_0_DATASETS


def is_tier_1(dataset_name: str) -> bool:
    """Check if dataset is Tier 1 (has COCO annotations).

    Args:
        dataset_name (str): Name of the dataset

    Returns:
        bool: True if Tier 1, False otherwise"""
    return dataset_name in TIER_1_DATASETS


__all__ = [
    "CONTENT_FLAG_KEYS",
    "TIER_0_DATASETS",
    "TIER_1_DATASETS",
    "get_tier_0_flags",
    "get_tier_for_dataset",
    "is_tier_0",
    "is_tier_1",
]
