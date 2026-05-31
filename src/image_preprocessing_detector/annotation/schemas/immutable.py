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
        format (str): Image format (png, jpg, tiff, etc.).
        width_px (int): Image width in pixels.
        height_px (int): Image height in pixels.
        channels (int): Number of color channels (1=grayscale, 3=RGB, 4=RGBA).
        bit_depth (int): Bits per channel (typically 8 or 16).
        file_size_bytes (int): File size on disk.
        dpi (int | None): Resolution in dots per inch (if available from metadata).
        color_space (str | None): Color space (RGB, CMYK, grayscale, etc.).
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
        diqa_overall (float | None): DIQA overall quality MOS (1-5 scale, higher=better).
        diqa_sharpness (float | None): DIQA sharpness quality MOS.
        diqa_color_fidelity (float | None): DIQA color fidelity MOS.
        diqa_original_image (str | None): Reference to original (ori) image.
        diqa_mos (float | None): Legacy alias for diqa_overall.
        diqa_mos_std (float | None): Standard deviation (if available).
        diqa_distortion_type (str | None): Distortion category.
        ocr_quality_score (int | None): Human quality score (1-4, 1=best, inverted).
        ocr_quality_source (str | None): Source of quality annotation.
        ocr_quality_text (str | None): Associated text content.
        smartdoc_mos (float | None): SmartDoc mean opinion score.
        smartdoc_capture_device (str | None): Capture device used.
        smartdoc_lighting (str | None): Lighting conditions.
        doclaynet_annotations (list[dict[str, Any]] | None): DocLayNet COCO annotations.
        tablebank_annotations (list[dict[str, Any]] | None): TableBank COCO annotations.
        funsd_annotations (dict[str, Any] | None): FUNSD annotations (dict, P0-4 FIX).
        pubtabnet_annotations (list[dict[str, Any]] | None): PubTabNet COCO annotations.
        signatr_writer_id (str | None): Writer ID for signature datasets.
        signatr_is_genuine (bool | None): Whether signature is genuine.
        writer_id (str | None): Generic writer ID (IAM, NIST-SD19).
        transcription (str | None): Ground truth text transcription.
        language_code (str | None): Original language label (e.g., "ur", "jp").
        script_name (str | None): Original script label (e.g., "Arabic", "Devanagari").
        iso15924_script_code (str | None): Standardized 4-letter ISO 15924 code.
        text_instances (list[dict[str, Any]] | None): List of text instance annotations.
        table_html (str | None): HTML representation of table structure.
        cell_annotations (list[dict[str, Any]] | None): Cell-level annotations.
        raw_labels (dict[str, Any] | None): Raw labels dict for unsupported formats.
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
