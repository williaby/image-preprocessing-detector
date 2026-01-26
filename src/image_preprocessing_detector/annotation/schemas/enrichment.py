# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Enrichment layer schemas for the annotation system.

This module contains dataclasses for the ENRICHMENT LAYER of the three-layer
metadata architecture. These are derived annotations with full provenance
tracking, versioned for reproducibility.

Classes:
    LayoutDetection: Single layout detection result
    EnrichmentData: Enrichment data for a single version
    EnrichmentVersion: Versioned enrichment with provenance metadata

Example:
    >>> from image_preprocessing_detector.annotation.schemas.enrichment import (
    ...     LayoutDetection,
    ...     EnrichmentData,
    ...     EnrichmentVersion,
    ... )
    >>>
    >>> detection = LayoutDetection(
    ...     class_name="table",
    ...     bbox=[100.0, 200.0, 300.0, 400.0],
    ...     confidence=0.95,
    ...     source="doclayout_yolo",
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayoutDetection:
    """Single layout detection from DocLayout-YOLO or COCO annotations.

    Represents a detected document element with its bounding box,
    confidence score, and source information.

    Attributes:
        class_name: Detected element class (table, figure, text, etc.)
        bbox: Bounding box coordinates [x1, y1, x2, y2] or [x, y, w, h]
        confidence: Detection confidence score (0.0-1.0)
        source: Detection source ("doclayout_yolo", "coco_annotation", etc.)
    """

    class_name: str
    bbox: list[float]
    confidence: float
    source: str


@dataclass
class EnrichmentData:
    """Single enrichment version data.

    Contains all derived annotations for a single enrichment version.
    Fields are grouped by category and include provenance information.

    Attributes:
        # Capture method detection
        capture_method: Detected capture method (CaptureMethod value)
        capture_confidence: Confidence in capture method detection
        capture_detection_method: How capture method was determined

        # Resolution analysis
        resolution_dpi: Detected DPI
        resolution_category: ResolutionCategory value
        resolution_pixels: (width, height) tuple

        # Domain classification
        domain_level1: DomainLevel1 value (3-letter code)
        domain_level2: Secondary domain classification
        domain_level3: Tertiary domain classification
        domain_confidence: Classification confidence

        # Structure analysis
        text_density: Text density classification
        layout_type: Layout type (single-column, multi-column, etc.)
        element_types: List of detected element types

        # Quality/degradation
        quality_overall: Overall quality score (0.0-1.0)
        degradations: List of detected degradations

        # Language detection (legacy)
        primary_language: Detected primary language
        language_confidence: Language detection confidence
        script_type: Detected script type

        # Language/Script (ISO-compliant, v2.1+)
        iso639_language: ISO 639-1/3 language code
        iso15924_script: ISO 15924 script code
        script_family: Script family classification
        bcp47_tag: Full BCP 47 language tag

        # Text Scope (v2.1+)
        text_scope: Text scope level
        text_scope_content_type: Content type classification
        text_scope_estimated_chars: Estimated character count
        text_scope_estimated_words: Estimated word count
        text_scope_detection_method: How scope was determined

        # Paper Size (ISO 216, v2.1+)
        paper_size: Detected paper size (A4, Letter, etc.)
        paper_size_standard: Size standard (iso, ansi, jis)
        paper_size_orientation: portrait/landscape
        paper_size_confidence: Detection confidence
        paper_size_is_exact: Whether exact match found

        # Dataset Source (v2.1+)
        dataset_short_code: Standardized dataset short code

        # LLM perceptual scores
        llm_predicted_mos: LLM-predicted MOS
        llm_predicted_normalized: Normalized LLM prediction
        llm_prediction_confidence: Prediction confidence
        llm_model_name: Model used for prediction

        # Content flags with provenance
        has_table: Whether document contains tables
        has_formula: Whether document contains formulas
        has_handwriting: Whether document contains handwriting
        has_signature: Whether document contains signatures
        has_figure: Whether document contains figures
        content_flags_tier: EnrichmentTier value for flags
        content_flags_source: Source of content flag detection

        # Layout detections
        layout_detections: List of LayoutDetection dicts
    """

    # Capture method detection
    capture_method: str | None = None
    capture_confidence: float | None = None
    capture_detection_method: str | None = None

    # Resolution analysis (aligned with taxonomy v4.0)
    resolution_dpi: int | None = None
    resolution_category: str | None = None
    resolution_pixels: tuple[int, int] | None = None

    # Domain classification
    domain_level1: str | None = None
    domain_level2: str | None = None
    domain_level3: str | None = None
    domain_confidence: float | None = None

    # Structure analysis
    text_density: str | None = None
    layout_type: str | None = None
    element_types: list[str] | None = None

    # Quality/degradation (list of detected degradations)
    quality_overall: float | None = None
    degradations: list[dict[str, Any]] | None = None

    # Language detection (legacy fields)
    primary_language: str | None = None
    language_confidence: float | None = None
    script_type: str | None = None

    # Language/Script (ISO-compliant, added v2.1)
    iso639_language: str | None = None
    iso15924_script: str | None = None
    script_family: str | None = None
    bcp47_tag: str | None = None

    # Text Scope (added v2.1)
    text_scope: str | None = None
    text_scope_content_type: str | None = None
    text_scope_estimated_chars: int | None = None
    text_scope_estimated_words: int | None = None
    text_scope_detection_method: str | None = None

    # Paper Size (ISO 216, added v2.1)
    paper_size: str | None = None
    paper_size_standard: str | None = None
    paper_size_orientation: str | None = None
    paper_size_confidence: float | None = None
    paper_size_is_exact: bool | None = None

    # Dataset Source (added v2.1)
    dataset_short_code: str | None = None

    # LLM perceptual scores (added in later versions)
    llm_predicted_mos: float | None = None
    llm_predicted_normalized: float | None = None
    llm_prediction_confidence: float | None = None
    llm_model_name: str | None = None

    # Content flags with provenance
    has_table: bool | None = None
    has_formula: bool | None = None
    has_handwriting: bool | None = None
    has_signature: bool | None = None
    has_figure: bool | None = None
    content_flags_tier: str | None = None
    content_flags_source: str | None = None

    # Layout detections (for Tier 1/2)
    layout_detections: list[dict[str, Any]] | None = None


@dataclass
class EnrichmentVersion:
    """Single version of enrichment with provenance and reproducibility.

    Each enrichment version captures the complete state of derived
    annotations at a point in time, with full provenance metadata
    for reproducibility.

    Attributes:
        version: Version number (1-indexed)
        created_at: ISO 8601 timestamp of creation
        created_by: Identifier for creator (script name, model, etc.)
        method: Enrichment method (EnrichmentTier value)
        description: Human-readable description of this version
        data: EnrichmentData containing actual annotations
        git_sha: Git commit SHA for reproducibility
        model_checkpoint: Model checkpoint used (if applicable)
        config_hash: Hash of configuration used
        script_version: Version of annotation script
    """

    version: int
    created_at: str
    created_by: str
    method: (
        str  # "tier_0_exact", "tier_1_annotation", "tier_2_model", "tier_3_heuristic"
    )
    description: str
    data: EnrichmentData = field(default_factory=EnrichmentData)

    # Reproducibility fields (consensus recommendation)
    git_sha: str | None = None
    model_checkpoint: str | None = None
    config_hash: str | None = None
    script_version: str | None = None


__all__ = [
    "EnrichmentData",
    "EnrichmentVersion",
    "LayoutDetection",
]
