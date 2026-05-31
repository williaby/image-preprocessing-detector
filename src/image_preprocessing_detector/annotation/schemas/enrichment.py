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
    ...     canonical_class="TABLE",
    ...     source_schema="docstructbench",
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayoutDetection:
    """Single layout detection from DocLayout-YOLO or COCO annotations.

    Represents a detected document element with its bounding box,
    confidence score, and source information. After taxonomy
    standardization, includes canonical class mapping metadata.

    Attributes:
        class_name (str): Detected element class (table, figure, text, etc.).
        bbox (list[float]): Bounding box coordinates [x1, y1, x2, y2] or [x, y, w, h].
        confidence (float): Detection confidence score (0.0-1.0).
        source (str): Detection source ("doclayout_yolo", "coco_annotation", etc.).
        canonical_class (str | None): Canonical taxonomy class (e.g., "TABLE", "FIGURE_CAPTION").
            Set by layout taxonomy standardization (v2.2+).
        source_schema (str | None): Layout schema that produced the class_name
            (e.g., "doclaynet", "docstructbench", "docling"). Set by standardization.
        source_label (str | None): Original label before conversion (preserved for traceability).
        is_lossy (bool | None): Whether the canonical mapping lost information (e.g.,
            "figure_caption" -> "Caption" loses figure context).
        conversion_confidence (float | None): Confidence of the taxonomy conversion (1.0 = exact,
            <1.0 = ambiguous expansion).
        loss_description (str | None): Human-readable description of information lost, if any.
    """

    class_name: str
    bbox: list[float]
    confidence: float
    source: str

    # Layout taxonomy standardization fields (added v2.2)
    canonical_class: str | None = None
    source_schema: str | None = None
    source_label: str | None = None
    is_lossy: bool | None = None
    conversion_confidence: float | None = None
    loss_description: str | None = None


@dataclass
class EnrichmentData:
    """Single enrichment version data.

    Contains all derived annotations for a single enrichment version.
    Fields are grouped by category and include provenance information.

    Attributes:
        capture_method (str | None): Detected capture method (CaptureMethod value).
        capture_confidence (float | None): Confidence in capture method detection.
        capture_detection_method (str | None): How capture method was determined.
        resolution_dpi (int | None): Detected DPI.
        resolution_category (str | None): ResolutionCategory value.
        resolution_pixels (tuple[int, int] | None): (width, height) tuple.
        domain_level1 (str | None): DomainLevel1 value (3-letter code).
        domain_level2 (str | None): Secondary domain classification.
        domain_level3 (str | None): Tertiary domain classification.
        domain_confidence (float | None): Classification confidence.
        text_density (str | None): Text density classification.
        layout_type (str | None): Layout type (single-column, multi-column, etc.).
        element_types (list[str] | None): List of detected element types.
        text_directions_present (list[str] | None): Text directions present (v2.3).
        quality_overall (float | None): Overall quality score (0.0-1.0).
        degradations (list[dict[str, Any]] | None): List of detected degradations.
        primary_language (str | None): Detected primary language (legacy).
        language_confidence (float | None): Language detection confidence (legacy).
        script_type (str | None): Detected script type (legacy).
        iso639_language (str | None): ISO 639-1/3 language code (v2.1+).
        iso15924_script (str | None): ISO 15924 script code (v2.1+).
        script_family (str | None): Script family classification (v2.1+).
        bcp47_tag (str | None): Full BCP 47 language tag (v2.1+).
        text_direction (str | None): Text direction "ltr", "rtl", "ttb" (v2.3).
        text_scope (str | None): Text scope level (v2.1+).
        text_scope_content_type (str | None): Content type classification (v2.1+).
        text_scope_estimated_chars (int | None): Estimated character count (v2.1+).
        text_scope_estimated_words (int | None): Estimated word count (v2.1+).
        text_scope_detection_method (str | None): How scope was determined (v2.1+).
        paper_size (str | None): Detected paper size (A4, Letter, etc.) (v2.1+).
        paper_size_standard (str | None): Size standard (iso, ansi, jis) (v2.1+).
        paper_size_orientation (str | None): portrait/landscape (v2.1+).
        paper_size_confidence (float | None): Detection confidence (v2.1+).
        paper_size_is_exact (bool | None): Whether exact match found (v2.1+).
        dataset_short_code (str | None): Standardized dataset short code (v2.1+).
        llm_predicted_mos (float | None): LLM-predicted MOS.
        llm_predicted_normalized (float | None): Normalized LLM prediction.
        llm_prediction_confidence (float | None): Prediction confidence.
        llm_model_name (str | None): Model used for prediction.
        has_table (bool | None): Whether document contains tables.
        has_formula (bool | None): Whether document contains formulas.
        has_handwriting (bool | None): Whether document contains handwriting.
        has_signature (bool | None): Whether document contains signatures.
        has_figure (bool | None): Whether document contains figures.
        content_flags_tier (str | None): EnrichmentTier value for flags.
        content_flags_source (str | None): Source of content flag detection.
        layout_detections (list[dict[str, Any]] | None): List of LayoutDetection dicts.
        orientation_class (int | None): Orientation class 0/90/180/270 (v2.1+).
        orientation_confidence (float | None): Orientation detection confidence (v2.1+).
        orientation_corrected (bool | None): Whether orientation was corrected (v2.1+).
        orientation_detection_method (str | None): How orientation was detected (v2.1+).
        skew_angle_degrees (float | None): Skew angle in degrees +-180 (v2.1+).
        skew_confidence (float | None): Skew detection confidence (v2.1+).
        skew_detection_method (str | None): How skew was detected (v2.1+).
        shadow_severity (float | None): Shadow severity 0-1 (v2.1+).
        shadow_type (str | None): Shadow type (v2.1+).
        shadow_confidence (float | None): Shadow detection confidence (v2.1+).
        warping_severity (float | None): Warping severity 0-1 (v2.1+).
        warping_type (str | None): Warping type (v2.1+).
        warping_confidence (float | None): Warping detection confidence (v2.1+).
        watermark_severity (float | None): Watermark severity 0-1 (v2.1+).
        watermark_type (str | None): Watermark type (v2.1+).
        watermark_confidence (float | None): Watermark detection confidence (v2.1+).
        fuzzy_scan_score (float | None): Fuzzy scan score 0-1 (v2.1+).
        ml_iqa_blur (float | None): ML IQA blur score 0-1 (v2.1+).
        ml_iqa_noise (float | None): ML IQA noise score 0-1 (v2.1+).
        ml_iqa_contrast (float | None): ML IQA contrast score 0-1 (v2.1+).
        ml_iqa_compression (float | None): ML IQA compression score 0-1 (v2.1+).
        ml_iqa_skew (float | None): ML IQA skew score 0-1 (v2.1+).
        ml_iqa_overall (float | None): ML IQA overall score 0-1 (v2.1+).
        ml_iqa_model_name (str | None): ML IQA model name (v2.1+).
        ml_iqa_model_version (str | None): ML IQA model version (v2.1+).
        vlm_iqa_sharpness (float | None): VLM IQA sharpness 1-5 (v2.2+).
        vlm_iqa_noise (float | None): VLM IQA noise 1-5 (v2.2+).
        vlm_iqa_contrast (float | None): VLM IQA contrast 1-5 (v2.2+).
        vlm_iqa_illumination (float | None): VLM IQA illumination 1-5 (v2.2+).
        vlm_iqa_compression (float | None): VLM IQA compression 1-5 (v2.2+).
        vlm_iqa_overall (float | None): VLM IQA overall 1-5 (v2.2+).
        vlm_iqa_model_name (str | None): VLM IQA model name (v2.2+).
        vlm_iqa_model_version (str | None): VLM IQA model version (v2.2+).
        vlm_iqa_prompt_version (str | None): VLM IQA prompt version (v2.2+).
        has_code (bool | None): Whether document contains code (v2.1+).
        code_confidence (float | None): Code detection confidence 0-1 (v2.1+).
        code_language (str | None): Detected code language (v2.1+).
        code_rendering_style (str | None): Code rendering style (v2.1+).
        character_height_px (float | None): Character height in pixels (v2.1+).
        resolution_quality_score (float | None): Resolution quality score 0-1 (v2.1+).
        effective_dpi (int | None): Effective DPI (v2.1+).
        character_height_clean_px (float | None): Pre-degradation character height (v2.2+).
        character_height_degraded_px (float | None): Post-degradation character height (v2.2+).
        character_height_analytical_px (float | None): Analytical character height (v2.2+).
        character_height_rendered_px (float | None): Rendered character height (v2.3+).
        resolution_quality_coarse_bucket (str | None): CoarseBucket value (v2.2+).
        resolution_quality_measurement_method (str | None): Measurement method (v2.2+).
        font_size_pt (float | None): Pillow font size in points (synthetic only).
        target_dpi (int | None): DPI tier target (synthetic only).
        output_size_px (int | None): Derived view output size (v2.3+).
        resolution_quality_label_provenance (str | None): Label provenance (v2.2+).
        resolution_quality_label_source (str | None): Label source (v2.2+).
        resolution_quality_label_confidence (float | None): Label confidence 0-1 (v2.2+).
        resolution_quality_script_used (str | None): Script used ISO 15924 (v2.2+).
        resolution_quality_script_confidence (float | None): Script detection confidence (v2.2+).
        resolution_quality_bucket_probabilities (dict[str, float] | None): 5-bucket distribution (v2.2+).
        resolution_quality_score_std (float | None): Teacher quality score uncertainty (v2.2+).
        resolution_quality_char_height_std (float | None): Teacher char height uncertainty (v2.2+).
        color_mode (str | None): Color mode "color", "grayscale", "binarized" (v2.1+).
        document_age (str | None): Document age "modern", "aged", "historical" (v2.1+).
        ocr_engine (str | None): OCR engine used (future, v2.1+).
        ocr_engine_version (str | None): OCR engine version (future, v2.1+).
        ocr_char_error_rate (float | None): OCR character error rate (future, v2.1+).
        ocr_word_error_rate (float | None): OCR word error rate (future, v2.1+).
        ocr_quality_before_correction (float | None): OCR quality before correction (future, v2.1+).
        ocr_quality_after_correction (float | None): OCR quality after correction (future, v2.1+).
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
    text_directions_present: list[str] | None = None  # ["ltr","rtl","ttb"] v2.3

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
    text_direction: str | None = None  # "ltr", "rtl", "ttb" v2.3

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

    # --- v2.1.0 additions below ---

    # Geometric attributes (orientation, skew) -- v2.1
    orientation_class: int | None = None  # 0/90/180/270
    orientation_confidence: float | None = None
    orientation_corrected: bool | None = None
    orientation_detection_method: str | None = None
    skew_angle_degrees: float | None = None  # exact angle +-180
    skew_confidence: float | None = None
    skew_detection_method: str | None = None

    # Physical degradation (shadow, warping, watermark) -- v2.1
    shadow_severity: float | None = None  # 0-1
    shadow_type: str | None = None
    shadow_confidence: float | None = None
    warping_severity: float | None = None  # 0-1
    warping_type: str | None = None
    warping_confidence: float | None = None
    watermark_severity: float | None = None  # 0-1
    watermark_type: str | None = None
    watermark_confidence: float | None = None
    fuzzy_scan_score: float | None = None  # 0-1

    # ML IQA 6-dim scores -- v2.1
    ml_iqa_blur: float | None = None  # 0-1
    ml_iqa_noise: float | None = None  # 0-1
    ml_iqa_contrast: float | None = None  # 0-1
    ml_iqa_compression: float | None = None  # 0-1
    ml_iqa_skew: float | None = None  # 0-1
    ml_iqa_overall: float | None = None  # 0-1
    ml_iqa_model_name: str | None = None
    ml_iqa_model_version: str | None = None

    # VLM quality assessment -- v2.2 (per-dimension quality from VLM evaluation)
    vlm_iqa_sharpness: float | None = None  # 1-5 scale
    vlm_iqa_noise: float | None = None  # 1-5 scale
    vlm_iqa_contrast: float | None = None  # 1-5 scale
    vlm_iqa_illumination: float | None = None  # 1-5 scale
    vlm_iqa_compression: float | None = None  # 1-5 scale
    vlm_iqa_overall: float | None = None  # 1-5 scale
    vlm_iqa_model_name: str | None = None
    vlm_iqa_model_version: str | None = None
    vlm_iqa_prompt_version: str | None = None

    # Code detection -- v2.1 (ContentFlags + StructureInfo in JSON schema)
    has_code: bool | None = None
    code_confidence: float | None = None  # 0-1
    code_language: str | None = None
    code_rendering_style: str | None = None

    # Resolution enhancement -- v2.1
    character_height_px: float | None = None
    resolution_quality_score: float | None = None  # 0-1
    effective_dpi: int | None = None

    # DPI provenance + measurement detail -- v2.2
    character_height_clean_px: float | None = None  # Pre-degradation (synthetic only)
    character_height_degraded_px: float | None = None  # Post-degradation measurement
    character_height_analytical_px: float | None = None  # font_size_pt * DPI / 72
    character_height_rendered_px: float | None = (
        None  # Measured from pristine image v2.3
    )
    resolution_quality_coarse_bucket: str | None = None  # CoarseBucket value
    resolution_quality_measurement_method: str | None = (
        None  # sauvola_cc_v2 | paddleocr_dbnet_cc_v1
    )
    font_size_pt: float | None = None  # Pillow font size (synthetic only)
    target_dpi: int | None = None  # DPI tier target (synthetic only)
    output_size_px: int | None = None  # Derived view output size (224/384/512) v2.3

    # Weak label provenance -- v2.2
    resolution_quality_label_provenance: str | None = (
        None  # tier_0_exact | tier_2_model | tier_3_heuristic
    )
    resolution_quality_label_source: str | None = (
        None  # synthetic_exact | weak_label_model_v1
    )
    resolution_quality_label_confidence: float | None = None  # 0-1
    resolution_quality_script_used: str | None = None  # ISO 15924 code
    resolution_quality_script_confidence: float | None = (
        None  # script detection confidence
    )

    # Soft label fields for teacher-student transfer -- v2.2
    resolution_quality_bucket_probabilities: dict[str, float] | None = (
        None  # 5-bucket distribution
    )
    resolution_quality_score_std: float | None = (
        None  # teacher quality_score uncertainty
    )
    resolution_quality_char_height_std: float | None = (
        None  # teacher char_height uncertainty
    )

    # Image properties (color mode, document age) -- v2.1
    color_mode: str | None = None  # "color", "grayscale", "binarized"
    document_age: str | None = None  # "modern", "aged", "historical"

    # OCR impact (future: populated by Project B) -- v2.1
    ocr_engine: str | None = None
    ocr_engine_version: str | None = None
    ocr_char_error_rate: float | None = None
    ocr_word_error_rate: float | None = None
    ocr_quality_before_correction: float | None = None
    ocr_quality_after_correction: float | None = None


@dataclass
class EnrichmentVersion:
    """Single version of enrichment with provenance and reproducibility.

    Each enrichment version captures the complete state of derived
    annotations at a point in time, with full provenance metadata
    for reproducibility.

    Attributes:
        version (int): Version number (1-indexed).
        created_at (str): ISO 8601 timestamp of creation.
        created_by (str): Identifier for creator (script name, model, etc.).
        method (str): Enrichment method (EnrichmentTier value).
        description (str): Human-readable description of this version.
        data (EnrichmentData): EnrichmentData containing actual annotations.
        git_sha (str | None): Git commit SHA for reproducibility.
        model_checkpoint (str | None): Model checkpoint used (if applicable).
        config_hash (str | None): Hash of configuration used.
        script_version (str | None): Version of annotation script.
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
