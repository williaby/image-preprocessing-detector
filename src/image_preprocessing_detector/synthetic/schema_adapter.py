# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Schema adapter for converting synthetic generator output to Layer 2 format.

This module provides conversion utilities to transform the internal synthetic
document generator output into the Layer 2 enrichment metadata schema used
by Project A's annotation system.

Key conversions:
- IQA labels (8 dimensions) → Degradation objects (45-type taxonomy)
- Generator LayoutType → Layer 2 layout_type
- Generator TextDensity → Layer 2 text_density
- Script/language info → LanguageInfo with BCP47 tags

Example:
    >>> from image_preprocessing_detector.synthetic.schema_adapter import (
    ...     Layer2SchemaAdapter,
    ... )
    >>> adapter = Layer2SchemaAdapter()
    >>> enrichment = adapter.build_enrichment_metadata(sample_data)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.annotation.schemas.enums import (
    CaptureMethod,
    EnrichmentTier,
)
from image_preprocessing_detector.synthetic.config import (
    DENSITY_TO_LAYER2,
    LAYOUT_TO_LAYER2,
    LayoutType,
    TextDensity,
    get_script_config,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# IQA to Degradation Mapping
# =============================================================================

# Maps synthetic generator IQA dimensions to Layer 2 degradation types
# Each IQA dimension can map to multiple specific degradation types
IQA_TO_DEGRADATION_MAPPING: dict[str, list[str]] = {
    "blur": ["motion_blur", "defocus_blur", "gaussian_blur"],
    "noise": ["gaussian_noise", "salt_pepper_noise", "sensor_noise"],
    "compression": ["jpeg_artifacts", "low_bitrate"],
    "ink_degradation": ["faint_text", "broken_characters"],
    "paper_degradation": ["paper_yellowing", "foxing", "staining"],
    "geometric_distortion": ["skew", "perspective", "page_curl"],
    "bleed_through": ["bleed_through"],
    "overall_quality": [],  # Meta-dimension, not a specific degradation
}

# Severity thresholds for converting numeric values to categorical
SEVERITY_THRESHOLDS: dict[str, tuple[float, float, float]] = {
    # (mild_threshold, moderate_threshold, severe_threshold)
    "default": (0.2, 0.5, 0.8),
}


def numeric_to_categorical_severity(
    value: float,
    thresholds: tuple[float, float, float] = (0.2, 0.5, 0.8),
) -> str:
    """Convert numeric severity (0-1) to categorical (none/mild/moderate/severe).

    Args:
        value: Numeric severity value in range [0, 1]
        thresholds: Tuple of (mild, moderate, severe) thresholds

    Returns:
        Categorical severity string
    """
    mild, moderate, severe = thresholds
    if value < mild:
        return "none"
    if value < moderate:
        return "mild"
    if value < severe:
        return "moderate"
    return "severe"


@dataclass
class IQALabels:
    """IQA labels from synthetic document generation.

    These represent the ground truth degradation values applied
    during document generation via Augraphy.

    All values are in range [0.0, 1.0] where 0 = pristine, 1 = severe.
    """

    blur: float = 0.0
    noise: float = 0.0
    compression: float = 0.0
    ink_degradation: float = 0.0
    paper_degradation: float = 0.0
    geometric_distortion: float = 0.0
    bleed_through: float = 0.0
    overall_quality: float = 1.0  # 1.0 = perfect quality, 0.0 = worst

    @classmethod
    def get_label_names(cls) -> list[str]:
        """Return list of IQA label names."""
        return [
            "blur",
            "noise",
            "compression",
            "ink_degradation",
            "paper_degradation",
            "geometric_distortion",
            "bleed_through",
            "overall_quality",
        ]

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "blur": self.blur,
            "noise": self.noise,
            "compression": self.compression,
            "ink_degradation": self.ink_degradation,
            "paper_degradation": self.paper_degradation,
            "geometric_distortion": self.geometric_distortion,
            "bleed_through": self.bleed_through,
            "overall_quality": self.overall_quality,
        }

    def to_vector(self) -> list[float]:
        """Convert to ordered vector for ML training."""
        return [
            self.blur,
            self.noise,
            self.compression,
            self.ink_degradation,
            self.paper_degradation,
            self.geometric_distortion,
            self.bleed_through,
            self.overall_quality,
        ]


@dataclass
class TextBlock:
    """Information about a rendered text block.

    Used for tracking layout detection ground truth.
    """

    text: str
    script_code: str
    language_code: str
    bbox: tuple[int, int, int, int]  # (x, y, width, height) COCO format
    font_size: int
    is_header: bool = False
    is_caption: bool = False


@dataclass
class GeneratedSample:
    """Output from single sample generation.

    Contains all metadata needed to create Layer 2 enrichment.

    Attributes:
        image: PIL Image object
        sample_id: Unique identifier (UUID)
        scripts: Set of ISO 15924 script codes present
        language_codes: List of ISO 639-3 language codes (OpenLID format)
        layout_type: Document layout type
        text_density: Text density level
        iqa_labels: 8-dimension IQA quality labels
        text_blocks: List of rendered text blocks with bounding boxes
        resolution_dpi: Output resolution (72/150/300)
        width_px: Image width in pixels
        height_px: Image height in pixels
        generation_params: Additional generation parameters
        is_pristine: True if no degradation applied
        resolution_tier: Resolution tier (LOW/MEDIUM/HIGH) for NaFlex
        quality_tier: Quality tier (PRISTINE/HIGH/MEDIUM/LOW/DEGRADED)
        split: Dataset split assignment (train/val/test)
    """

    image: Any  # PIL.Image.Image
    sample_id: str
    scripts: set[str]  # ISO 15924 codes
    language_codes: list[str]  # ISO 639-3 codes (OpenLID format: xxx_Yyyy)
    layout_type: LayoutType
    text_density: TextDensity
    iqa_labels: IQALabels
    text_blocks: list[TextBlock] = field(default_factory=list)
    resolution_dpi: int = 300
    width_px: int = 0
    height_px: int = 0
    generation_params: dict[str, Any] = field(default_factory=dict)
    is_pristine: bool = False
    resolution_tier: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    quality_tier: str = "MEDIUM"  # PRISTINE, HIGH, MEDIUM, LOW, DEGRADED
    split: str | None = None  # train, val, test


# =============================================================================
# Layer 2 Schema Adapter
# =============================================================================


class Layer2SchemaAdapter:
    """Convert synthetic generator output to Layer 2 enrichment schema.

    This adapter transforms the internal GeneratedSample representation
    into the Layer 2 enrichment metadata format used by Project A's
    annotation system.
    """

    def __init__(
        self,
        generator_version: str = "1.0.0",
        git_sha: str | None = None,
    ) -> None:
        """Initialize the schema adapter.

        Args:
            generator_version: Semantic version of the generator
            git_sha: Git commit SHA for provenance tracking
        """
        self.generator_version = generator_version
        self.git_sha = git_sha

    def convert_iqa_to_degradations(
        self,
        iqa_labels: IQALabels,
        augmentation_source: str = "synthetic",
    ) -> list[dict[str, Any]]:
        """Map IQA dimensions to Layer 2 Degradation objects.

        Args:
            iqa_labels: IQA labels from synthetic generation
            augmentation_source: Source of augmentation ("augraphy", "albumentations", "hybrid")

        Returns:
            List of Degradation dictionaries
        """
        degradations: list[dict[str, Any]] = []
        iqa_dict = iqa_labels.to_dict()

        # FIX BUG #6: Use actual augmentation source, not hardcoded value
        detection_method = f"{augmentation_source}_synthetic"

        for iqa_key, degradation_types in IQA_TO_DEGRADATION_MAPPING.items():
            if iqa_key == "overall_quality":
                continue  # Not a degradation

            severity_numeric = iqa_dict.get(iqa_key, 0.0)
            if severity_numeric < 0.1:  # Skip negligible degradations
                continue

            severity_categorical = numeric_to_categorical_severity(severity_numeric)

            # Create degradation entries for each mapped type
            # Use the first type as primary, or create one per type
            if degradation_types:
                primary_type = degradation_types[0]
                degradations.append(
                    {
                        "type": primary_type,
                        "severity": severity_categorical,
                        "severity_numeric": round(severity_numeric, 4),
                        "confidence": 1.0,  # Ground truth
                        "detection_method": detection_method,
                        "location": "global",
                        "region": None,
                    }
                )

        return degradations

    def _parse_openlid_code(self, openlid_code: str) -> tuple[str, str | None]:
        """Parse OpenLID format (xxx_Yyyy) into ISO 639-3 and ISO 15924 components.

        OpenLID format: language_code_script (e.g., "eng_Latn", "ara_Arab")

        Args:
            openlid_code: OpenLID format language code (e.g., "ace_Latn")

        Returns:
            Tuple of (iso639_code, iso15924_code or None)
            Example: ("ace", "Latn") or ("en", None) if already ISO format
        """
        if "_" in openlid_code:
            parts = openlid_code.split("_", 1)
            return parts[0], parts[1] if len(parts) > 1 else None
        # Already in ISO 639 format (2-3 letter code)
        return openlid_code, None

    def build_language_info(
        self,
        script_code: str,
        language_code: str,
        is_primary: bool = True,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Build LanguageInfo dictionary from script/language codes.

        Handles OpenLID format (xxx_Yyyy) by parsing into ISO components.
        The script_code from the corpus sample is authoritative; the script
        embedded in OpenLID is used only for validation/logging.

        Args:
            script_code: ISO 15924 script code (authoritative)
            language_code: Language code in OpenLID format (xxx_Yyyy) or ISO 639-1/3
            is_primary: Whether this is the primary/dominant language
            confidence: Detection confidence (1.0 for synthetic ground truth)

        Returns:
            LanguageInfo dictionary matching Layer 2 schema
        """
        # Parse OpenLID format to extract ISO 639 code
        iso639_code, embedded_script = self._parse_openlid_code(language_code)

        script_config = get_script_config(script_code)

        # Determine script family
        script_family = "other"
        if script_config:
            script_family = script_config.script_family.value

        # Determine RTL
        is_rtl = script_config.is_rtl if script_config else False

        # Build BCP47 tag (language-script format)
        # Use the authoritative script_code, not the embedded one
        bcp47_tag = f"{iso639_code}-{script_code}"

        return {
            "language_code": iso639_code,  # ISO 639-3 only, not OpenLID format
            "script_code": script_code,
            "bcp47_tag": bcp47_tag,
            "script_family": script_family,
            "confidence": confidence,
            "detection_method": "synthetic_ground_truth",
            "is_rtl": is_rtl,
            "is_primary": is_primary,
        }

    def build_layout_detections(
        self,
        text_blocks: list[TextBlock],
    ) -> list[dict[str, Any]]:
        """Build LayoutDetection array from text blocks.

        Args:
            text_blocks: List of TextBlock objects from rendering

        Returns:
            List of LayoutDetection dictionaries in COCO format
        """
        detections: list[dict[str, Any]] = []

        for block in text_blocks:
            # Determine class based on block properties
            if block.is_header:
                class_name = "Section-Header"
            elif block.is_caption:
                class_name = "Caption"
            else:
                class_name = "Text"

            # Calculate area
            _, _, width, height = block.bbox
            area = width * height

            detections.append(
                {
                    "class_name": class_name,
                    "bbox": list(block.bbox),  # COCO format [x, y, w, h]
                    "bbox_original": None,
                    "bbox_source_format": "coco_xywh",
                    "confidence": 1.0,  # Ground truth
                    "source": "synthetic_text_block",
                    "area": area,
                }
            )

        return detections

    def build_enrichment_metadata(
        self,
        sample: GeneratedSample,
        augmentation_source: str = "synthetic",
    ) -> dict[str, Any]:
        """Build complete Layer 2 enrichment metadata from GeneratedSample.

        Args:
            sample: Generated sample with all metadata
            augmentation_source: Source of augmentation ("augraphy", "albumentations", "hybrid")

        Returns:
            Complete Layer2EnrichmentMetadata dictionary
        """
        # Generate UUID if not provided or convert existing ID
        if sample.sample_id.startswith("syn-"):
            # Legacy format - generate new UUID
            sample_uuid = str(uuid.uuid4())
        else:
            try:
                # Validate existing UUID
                uuid.UUID(sample.sample_id)
                sample_uuid = sample.sample_id
            except ValueError:
                sample_uuid = str(uuid.uuid4())

        # Build primary language info (first script/language)
        # FIX BUG #4: Use sorted() to ensure deterministic ordering from set
        scripts_list = sorted(sample.scripts)
        primary_script = scripts_list[0] if scripts_list else "Latn"
        primary_language = sample.language_codes[0] if sample.language_codes else "en"

        # Build languages array for multi-script documents
        languages: list[dict[str, Any]] = []
        for i, script_code in enumerate(scripts_list):
            lang_code = (
                sample.language_codes[i]
                if i < len(sample.language_codes)
                else "und"  # Undetermined
            )
            languages.append(
                self.build_language_info(
                    script_code=script_code,
                    language_code=lang_code,
                    is_primary=(i == 0),
                )
            )

        # Determine resolution category
        dpi = sample.resolution_dpi
        if dpi < 150:
            resolution_category = "low_<150"
        elif dpi < 300:
            resolution_category = "medium_150-299"
        elif dpi == 300:
            resolution_category = "standard_300"
        else:
            resolution_category = "high_>300"

        # Build structure info
        layer2_layout = LAYOUT_TO_LAYER2.get(sample.layout_type, "unknown")
        layer2_density = DENSITY_TO_LAYER2.get(sample.text_density, "moderate")

        # Determine element types from text blocks
        element_types: set[str] = set()
        for block in sample.text_blocks:
            if block.is_header:
                element_types.add("Section-Header")
            elif block.is_caption:
                element_types.add("Caption")
            else:
                element_types.add("Text")

        # Build the complete metadata
        return {
            "sample_id": sample_uuid,
            "enrichment_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": f"synthetic_generator_v{self.generator_version}",
            "method": EnrichmentTier.TIER_0_EXACT.value,
            "description": "Synthetically generated multi-script document",
            "provenance": {
                "git_sha": self.git_sha,
                "script_version": self.generator_version,
                "model_checkpoint": None,
                "config_hash": None,
            },
            "data": {
                "capture_method": {
                    "method": CaptureMethod.SYNTHETIC.value,
                    "confidence": 1.0,
                    "detection_method": "synthetic_generator",
                },
                "resolution": {
                    "dpi": sample.resolution_dpi,
                    "category": resolution_category,
                    "pixels": [sample.width_px, sample.height_px],
                },
                "domain": {
                    "level1": "UNK",  # Synthetic text has no specific domain
                    "level2": None,
                    "level3": None,
                    "confidence": 1.0,
                },
                "structure": {
                    "text_density": layer2_density,
                    "layout_type": layer2_layout,
                    "element_types": list(element_types),
                },
                "quality": {
                    "overall_score": sample.iqa_labels.overall_quality,
                    "degradations": self.convert_iqa_to_degradations(
                        sample.iqa_labels, augmentation_source
                    ),
                },
                "language": self.build_language_info(
                    primary_script, primary_language, is_primary=True
                ),
                # FIX BUG #2: Only include 'languages' if there are multiple languages
                # Schema requires valid objects, not null
                **({"languages": languages} if len(languages) > 1 else {}),
                "text_scope": {
                    "scope": "paragraph",
                    "content_type": "synthetic",
                    "density": layer2_density,
                    "estimated_chars": sum(len(b.text) for b in sample.text_blocks),
                    "estimated_words": sum(
                        len(b.text.split()) for b in sample.text_blocks
                    ),
                    "confidence": 1.0,
                    "detection_method": "synthetic_generator",
                },
                # FIX BUG #2: Omit paper_size entirely instead of setting to null
                # Schema doesn't allow null for this field
                "content_flags": {
                    "has_table": False,
                    "has_formula": False,
                    "has_handwriting": False,
                    "has_signature": False,
                    "has_figure": False,
                    "tier": EnrichmentTier.TIER_0_EXACT.value,
                    "source": "synthetic_generator",
                },
                "llm_scores": None,
                "layout_detections": self.build_layout_detections(sample.text_blocks),
            },
        }


__all__ = [
    "IQA_TO_DEGRADATION_MAPPING",
    "GeneratedSample",
    "IQALabels",
    "Layer2SchemaAdapter",
    "TextBlock",
    "numeric_to_categorical_severity",
]
