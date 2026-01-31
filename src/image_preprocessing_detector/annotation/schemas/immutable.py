# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Immutable layer schemas for the annotation system.

This module contains dataclasses for the IMMUTABLE LAYER of the three-layer
metadata architecture. These fields are set at ingestion time and NEVER
modified afterward.

Classes:
    OriginalFileMetadata: Physical file properties (dimensions, format, etc.)
    OriginalLabels: Ground truth labels from source datasets

Critical Fix P0-4:
    The FUNSD annotation format is a dict (object), NOT a list.
    Type annotation corrected from `list[dict]` to `dict`.

Example:
    >>> from image_preprocessing_detector.annotation.schemas.immutable import (
    ...     OriginalFileMetadata,
    ...     OriginalLabels,
    ... )
    >>>
    >>> file_meta = OriginalFileMetadata(
    ...     format="png",
    ...     width_px=2480,
    ...     height_px=3508,
    ...     channels=3,
    ...     bit_depth=8,
    ...     file_size_bytes=1_500_000,
    ...     dpi=300,
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OriginalFileMetadata:
    """Immutable file metadata extracted at ingestion.

    Physical properties of the source image file that are
    captured once and never modified.

    Attributes:
        format: Image format (png, jpg, tiff, etc.)
        width_px: Image width in pixels
        height_px: Image height in pixels
        channels: Number of color channels (1=grayscale, 3=RGB, 4=RGBA)
        bit_depth: Bits per channel (typically 8 or 16)
        file_size_bytes: File size on disk
        dpi: Resolution in dots per inch (if available from metadata)
        color_space: Color space (RGB, CMYK, grayscale, etc.)
    """

    format: str
    width_px: int
    height_px: int
    channels: int
    bit_depth: int
    file_size_bytes: int
    dpi: int | None = None
    color_space: str | None = None


@dataclass
class OriginalLabels:
    """Immutable labels from source dataset (preserved exactly).

    Ground truth annotations as provided by the original dataset,
    preserved without modification. Different datasets populate
    different fields based on their annotation schemas.

    See docs/schema/LABEL_MAPPING_SPECIFICATION.md for field mappings.

    Attributes:
        # Quality Scores (dataset-specific)
        diqa_overall: DIQA overall quality MOS (1-5 scale, higher=better)
        diqa_sharpness: DIQA sharpness quality MOS
        diqa_color_fidelity: DIQA color fidelity MOS
        diqa_original_image: Reference to original (ori) image
        diqa_mos: Legacy alias for diqa_overall
        diqa_mos_std: Standard deviation (if available)
        diqa_distortion_type: Distortion category

        # OCR-Quality human scores (1-4 scale, 1=best - INVERTED!)
        ocr_quality_score: Human quality score
        ocr_quality_source: Source of quality annotation
        ocr_quality_text: Associated text content

        # SmartDoc quality scores
        smartdoc_mos: SmartDoc mean opinion score
        smartdoc_capture_device: Capture device used
        smartdoc_lighting: Lighting conditions

        # Layout Annotations (COCO/FUNSD format)
        doclaynet_annotations: DocLayNet COCO annotations (list)
        tablebank_annotations: TableBank COCO annotations (list)
        funsd_annotations: FUNSD annotations (dict - P0-4 FIX)
        pubtabnet_annotations: PubTabNet COCO annotations (list)

        # Handwriting Datasets
        signatr_writer_id: Writer ID for signature datasets
        signatr_is_genuine: Whether signature is genuine
        writer_id: Generic writer ID (IAM, NIST-SD19)
        transcription: Ground truth text transcription

        # Multilingual/Script Datasets
        language_code: Original language label (e.g., "ur", "jp")
        script_name: Original script label (e.g., "Arabic", "Devanagari")
        iso15924_script_code: Standardized 4-letter ISO 15924 code (e.g., "Arab", "Deva")

        # Scene Text Datasets (MLT-19 style)
        text_instances: List of text instance annotations

        # Table Structure (PubTabNet)
        table_html: HTML representation of table structure
        cell_annotations: Cell-level annotations

        # Generic Fallback
        raw_labels: Raw labels dict for unsupported formats
    """

    # === Quality Scores (dataset-specific) ===
    # DIQA-5000: 3-dimension quality assessment (1-5 scale, higher is better)
    diqa_overall: float | None = None
    diqa_sharpness: float | None = None
    diqa_color_fidelity: float | None = None
    diqa_original_image: str | None = None
    # Legacy field (alias for diqa_overall, for backward compatibility)
    diqa_mos: float | None = None
    diqa_mos_std: float | None = None
    diqa_distortion_type: str | None = None

    # OCR-Quality human scores (1-4 scale, 1=best - INVERTED!)
    ocr_quality_score: int | None = None
    ocr_quality_source: str | None = None
    ocr_quality_text: str | None = None

    smartdoc_mos: float | None = None
    smartdoc_capture_device: str | None = None
    smartdoc_lighting: str | None = None

    # === Layout Annotations ===
    # CRITICAL FIX P0-4: FUNSD format is dict (object), NOT list
    # DocLayNet and TableBank use COCO format (list of dicts)
    doclaynet_annotations: list[dict[str, Any]] | None = None
    tablebank_annotations: list[dict[str, Any]] | None = None
    funsd_annotations: dict[str, Any] | None = None  # P0-4 FIX: dict, not list
    pubtabnet_annotations: list[dict[str, Any]] | None = None

    # === Handwriting Datasets ===
    signatr_writer_id: str | None = None
    signatr_is_genuine: bool | None = None
    writer_id: str | None = None
    transcription: str | None = None

    # === Multilingual/Script Datasets ===
    language_code: str | None = None
    script_name: str | None = None
    # ISO 15924 4-letter script code (e.g., "Arab", "Deva", "Latn")
    # This is the STANDARDIZED code; script_name may contain full names
    iso15924_script_code: str | None = None

    # === Scene Text Datasets (MLT-19 style) ===
    text_instances: list[dict[str, Any]] | None = None

    # === Table Structure (PubTabNet) ===
    table_html: str | None = None
    cell_annotations: list[dict[str, Any]] | None = None

    # === Generic Fallback ===
    raw_labels: dict[str, Any] | None = None


__all__ = [
    "OriginalFileMetadata",
    "OriginalLabels",
]
