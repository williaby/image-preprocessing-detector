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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from image_preprocessing_detector.annotation.schemas.enums import (
    CaptureMethod,
    EnrichmentTier,
)
from image_preprocessing_detector.schema_utils.resolution_quality import (
    classify_coarse_bucket,
)
from image_preprocessing_detector.synthetic.config import (
    DENSITY_TO_LAYER2,
    LAYOUT_TO_LAYER2,
    LayoutType,
    TextDensity,
    get_script_config,
)

if TYPE_CHECKING:
    pass  # No type-only imports needed yet; guard kept for future additions


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


def numeric_to_categorical_severity(
    value: float,
    thresholds: tuple[float, float, float] = (0.2, 0.5, 0.8),
) -> str:
    """Convert numeric severity (0-1) to categorical (none/mild/moderate/severe).

    Args:
        value (float): Numeric severity value in range [0, 1]
        thresholds (tuple[float, float, float]): Tuple of (mild, moderate, severe) thresholds

    Returns:
        str: Categorical severity string

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
        image (Any): PIL Image object
        sample_id (str): Unique identifier (UUID)
        scripts (set[str]): Set of ISO 15924 script codes present
        language_codes (list[str]): List of ISO 639-3 language codes (OpenLID format)
        layout_type (LayoutType): Document layout type
        text_density (TextDensity): Text density level
        iqa_labels (IQALabels): 8-dimension IQA quality labels
        text_blocks (list[TextBlock]): List of rendered text blocks with bounding boxes
        resolution_dpi (int): Output resolution (72-600)
        width_px (int): Image width in pixels
        height_px (int): Image height in pixels
        generation_params (dict[str, Any]): Additional generation parameters
        is_pristine (bool): True if no degradation applied
        resolution_tier (str): Resolution tier for NaFlex
        quality_tier (str): Quality tier (PRISTINE/HIGH/MEDIUM/LOW/DEGRADED)
        split (str | None): Dataset split assignment (train/val/test)
        color_mode (str): Color mode applied (color/grayscale/binarized)
        skew_angle_degrees (float | None): Exact skew angle if skew augmentation applied
        orientation_class (int | None): Orientation class (0/90/180/270) if orientation augmentation applied
        char_height_px (float | None): Measured character height in pixels
        char_height_quality_score (float | None): Quality score derived from character height (0-1)
        document_age (str | None): Simulated document age (modern/aged/historical)
        font_size_pt (float | None): Pillow font size used during rendering
        target_dpi (int | None): DPI tier target (72-600)
        char_height_clean_px (float | None): Pre-degradation character height measurement
        char_height_degraded_px (float | None): Post-degradation character height measurement
        char_height_analytical_px (float | None): Analytically computed character height
        char_height_rendered_px (float | None): Measured character height from pristine image
        output_size_px (int | None): Derived view output size in pixels
        text_directions (dict[str, str] | None): Script code to text direction mapping

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
    resolution_tier: str = "MEDIUM"
    quality_tier: str = "MEDIUM"
    split: str | None = None
    color_mode: str = "color"
    skew_angle_degrees: float | None = None
    orientation_class: int | None = None
    char_height_px: float | None = None
    char_height_quality_score: float | None = None
    document_age: str | None = None

    # Ground-truth generation parameters for resolution quality (v2.2)
    font_size_pt: float | None = None  # Pillow font size used during rendering
    target_dpi: int | None = None  # DPI tier target (72-600)
    char_height_clean_px: float | None = None  # Pre-degradation measurement
    char_height_degraded_px: float | None = None  # Post-degradation measurement
    char_height_analytical_px: float | None = None  # font_size_pt * target_dpi / 72
    char_height_rendered_px: float | None = None  # Measured from pristine image (v2.3)
    output_size_px: int | None = None  # Derived view output size (v2.3)
    text_directions: dict[str, str] | None = (
        None  # script_code -> direction used (v2.3)
    )


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
        self.generator_version = generator_version
        self.git_sha = git_sha

    def convert_iqa_to_degradations(
        self,
        iqa_labels: IQALabels,
        augmentation_source: str = "synthetic",
    ) -> list[dict[str, Any]]:
        """Map IQA dimensions to Layer 2 Degradation objects.

        Args:
            iqa_labels (IQALabels): IQA labels from synthetic generation
            augmentation_source (str): Source of augmentation ("augraphy", "albumentations", "hybrid")

        Returns:
            list[dict[str, Any]]: List of Degradation dictionaries

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
            openlid_code (str): OpenLID format language code (e.g., "ace_Latn")

        Returns:
            tuple[str, str | None]: Tuple of (iso639_code, iso15924_code or None)
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
        text_direction: str | None = None,
    ) -> dict[str, Any]:
        """Build LanguageInfo dictionary from script/language codes.

        Handles OpenLID format (xxx_Yyyy) by parsing into ISO components.
        The script_code from the corpus sample is authoritative; the script
        embedded in OpenLID is used only for validation/logging.

        Args:
            script_code (str): ISO 15924 script code (authoritative)
            language_code (str): Language code in OpenLID format (xxx_Yyyy) or ISO 639-1/3
            is_primary (bool): Whether this is the primary/dominant language
            confidence (float): Detection confidence (1.0 for synthetic ground truth)
            text_direction (str | None): Writing direction used ("ltr", "rtl", "ttb") or None

        Returns:
            dict[str, Any]: LanguageInfo dictionary matching Layer 2 schema

        """
        # Parse OpenLID format to extract ISO 639 code
        iso639_code, _embedded_script = self._parse_openlid_code(language_code)

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

        result: dict[str, Any] = {
            "language_code": iso639_code,  # ISO 639-3 only, not OpenLID format
            "script_code": script_code,
            "bcp47_tag": bcp47_tag,
            "script_family": script_family,
            "confidence": confidence,
            "detection_method": "synthetic_ground_truth",
            "is_rtl": is_rtl,
            "is_primary": is_primary,
        }
        # v2.3.0: text_direction (per-language writing direction)
        if text_direction is not None:
            result["text_direction"] = text_direction
        return result

    def build_layout_detections(
        self,
        text_blocks: list[TextBlock],
    ) -> list[dict[str, Any]]:
        """Build LayoutDetection array from text blocks.

        Args:
            text_blocks (list[TextBlock]): List of TextBlock objects from rendering

        Returns:
            list[dict[str, Any]]: List of LayoutDetection dictionaries in COCO format

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
            sample (GeneratedSample): Generated sample with all metadata
            augmentation_source (str): Source of augmentation ("augraphy", "albumentations", "hybrid")

        Returns:
            dict[str, Any]: Complete Layer2EnrichmentMetadata dictionary

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
            # v2.3.0: per-language text direction
            text_dir: str | None = None
            if sample.text_directions:
                text_dir = sample.text_directions.get(script_code)
            languages.append(
                self.build_language_info(
                    script_code=script_code,
                    language_code=lang_code,
                    is_primary=(i == 0),
                    text_direction=text_dir,
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
        data: dict[str, Any] = {
            "capture_method": {
                "method": CaptureMethod.SYNTHETIC.value,
                "confidence": 1.0,
                "detection_method": "synthetic_generator",
            },
            "resolution": {
                "dpi": sample.resolution_dpi,
                "category": resolution_category,
                "pixels": [sample.width_px, sample.height_px],
                # v2.1.0: character height (prefer clean measurement)
                **(
                    {
                        "character_height_px": round(
                            sample.char_height_clean_px or sample.char_height_px or 0.0,
                            2,
                        )
                    }
                    if (sample.char_height_clean_px or sample.char_height_px)
                    is not None
                    else {}
                ),
                **(
                    {
                        "resolution_quality_score": round(
                            sample.char_height_quality_score, 4
                        )
                    }
                    if sample.char_height_quality_score is not None
                    else {}
                ),
                "effective_dpi": sample.resolution_dpi,
                # v2.2: DPI provenance + measurement detail (synthetic)
                **(
                    {"character_height_clean_px": round(sample.char_height_clean_px, 2)}
                    if sample.char_height_clean_px is not None
                    else {}
                ),
                **(
                    {
                        "character_height_degraded_px": round(
                            sample.char_height_degraded_px, 2
                        )
                    }
                    if sample.char_height_degraded_px is not None
                    else {}
                ),
                **(
                    {
                        "character_height_analytical_px": round(
                            sample.char_height_analytical_px, 2
                        )
                    }
                    if sample.char_height_analytical_px is not None
                    else {}
                ),
                **(
                    {"font_size_pt": sample.font_size_pt}
                    if sample.font_size_pt is not None
                    else {}
                ),
                **(
                    {"target_dpi": sample.target_dpi}
                    if sample.target_dpi is not None
                    else {}
                ),
                # v2.3.0: Measured rendered character height (ground truth)
                **(
                    {
                        "character_height_rendered_px": round(
                            sample.char_height_rendered_px, 2
                        )
                    }
                    if sample.char_height_rendered_px is not None
                    else {}
                ),
                # v2.3.0: Output size for derived views
                **(
                    {"output_size_px": sample.output_size_px}
                    if sample.output_size_px is not None
                    else {}
                ),
                **(
                    {
                        "coarse_bucket": classify_coarse_bucket(
                            sample.char_height_clean_px or sample.char_height_px or 0.0
                        )
                    }
                    if (sample.char_height_clean_px or sample.char_height_px)
                    is not None
                    else {}
                ),
                "measurement_method": "sauvola_cc_v2",
                "label_provenance": "tier_0_exact",
                "label_source": "synthetic_exact",
                "label_confidence": 1.0,
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
                # v2.3.0: text_directions_present (all directions in document)
                **(
                    {
                        "text_directions_present": sorted(
                            set(sample.text_directions.values())
                        )
                    }
                    if sample.text_directions
                    else {}
                ),
            },
            "quality": {
                "overall_score": sample.iqa_labels.overall_quality,
                "degradations": self.convert_iqa_to_degradations(
                    sample.iqa_labels, augmentation_source
                ),
            },
            "language": self.build_language_info(
                primary_script,
                primary_language,
                is_primary=True,
                text_direction=(
                    sample.text_directions.get(primary_script)
                    if sample.text_directions
                    else None
                ),
            ),
            # Only include 'languages' if there are multiple languages
            **({"languages": languages} if len(languages) > 1 else {}),
            "text_scope": {
                "scope": "paragraph",
                "content_type": "synthetic",
                "density": layer2_density,
                "estimated_chars": sum(len(b.text) for b in sample.text_blocks),
                "estimated_words": sum(len(b.text.split()) for b in sample.text_blocks),
                "confidence": 1.0,
                "detection_method": "synthetic_generator",
            },
            "content_flags": {
                "has_table": False,
                "has_formula": False,
                "has_handwriting": False,
                "has_signature": False,
                "has_figure": False,
                "has_code": False,  # v2.1.0
                "code_confidence": 1.0,  # v2.1.0 (ground truth: no code)
                "tier": EnrichmentTier.TIER_0_EXACT.value,
                "source": "synthetic_generator",
            },
            "llm_scores": None,
            "layout_detections": self.build_layout_detections(sample.text_blocks),
        }

        # v2.1.0: Geometric info (orientation + skew)
        geometric = self._build_geometric_info(sample)
        if geometric:
            data["geometric"] = geometric

        # v2.1.0: ML IQA 6-dim scores from synthetic IQA labels
        data["ml_image_quality"] = self._build_ml_iqa_info(sample)

        # v2.1.0: Image properties (color mode, document age)
        image_props = self._build_image_properties(sample)
        if image_props:
            data["image_properties"] = image_props

        return {
            "sample_id": sample_uuid,
            "enrichment_version": 1,
            "schema_version": "2.3.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": f"synthetic_generator_v{self.generator_version}",
            "method": EnrichmentTier.TIER_0_EXACT.value,
            "description": "Synthetically generated multi-script document",
            "provenance": {
                "git_sha": self.git_sha,
                "script_version": self.generator_version,
                "model_checkpoint": None,
                "config_hash": None,
            },
            "data": data,
        }

    def _build_geometric_info(
        self,
        sample: GeneratedSample,
    ) -> dict[str, Any] | None:
        """Build GeometricInfo from sample orientation and skew data.

        Args:
            sample (GeneratedSample): Generated sample with orientation/skew fields

        Returns:
            dict[str, Any] | None: GeometricInfo dictionary or None if no geometric data

        """
        has_data = (
            sample.orientation_class is not None
            or sample.skew_angle_degrees is not None
        )
        if not has_data:
            return None

        info: dict[str, Any] = {
            "provenance_tier": "tier_0_exact",
            "is_soft_label": False,
            "detection_method": "synthetic_exact",
        }

        if sample.orientation_class is not None:
            info["orientation_class"] = sample.orientation_class
            info["orientation_confidence"] = 1.0
            info["orientation_corrected"] = False
            info["orientation_detection_method"] = "synthetic_exact"

        if sample.skew_angle_degrees is not None:
            info["skew_angle_degrees"] = round(sample.skew_angle_degrees, 4)
            info["skew_confidence"] = 1.0
            info["skew_detection_method"] = "synthetic_exact"

        return info

    def _build_ml_iqa_info(
        self,
        sample: GeneratedSample,
    ) -> dict[str, Any]:
        """Build MLImageQualityInfo from synthetic IQA labels.

        Maps the 8-dim synthetic IQA to the 6-dim ML IQA schema fields.

        Args:
            sample (GeneratedSample): Generated sample with IQA labels

        Returns:
            dict[str, Any]: MLImageQualityInfo dictionary

        """
        iqa = sample.iqa_labels
        return {
            "blur_score": round(iqa.blur, 4),
            "noise_score": round(iqa.noise, 4),
            "contrast_score": round(
                iqa.ink_degradation, 4
            ),  # Map ink_degradation -> contrast
            "compression_score": round(iqa.compression, 4),
            "skew_score": round(iqa.geometric_distortion, 4),
            "overall_score": round(
                1.0 - iqa.overall_quality, 4
            ),  # Invert: IQA=1 is good, schema 0=best quality issue
            "model_name": "synthetic_ground_truth",
            "model_version": self.generator_version,
            "confidence": 1.0,
            "provenance_tier": "tier_0_exact",
            "is_soft_label": False,
            "detection_method": "synthetic_exact",
        }

    def _build_image_properties(
        self,
        sample: GeneratedSample,
    ) -> dict[str, Any] | None:
        """Build ImagePropertiesInfo from sample properties.

        Args:
            sample (GeneratedSample): Generated sample with color mode and document age

        Returns:
            dict[str, Any] | None: ImagePropertiesInfo dictionary or None if defaults only

        """
        has_data = sample.color_mode != "color" or sample.document_age is not None
        if not has_data:
            return None

        info: dict[str, Any] = {
            "color_mode": sample.color_mode,
            "provenance_tier": "tier_0_exact",
            "is_soft_label": False,
            "detection_method": "synthetic_exact",
        }

        if sample.document_age is not None:
            info["document_age"] = sample.document_age

        return info


__all__ = [
    "IQA_TO_DEGRADATION_MAPPING",
    "GeneratedSample",
    "IQALabels",
    "Layer2SchemaAdapter",
    "TextBlock",
    "numeric_to_categorical_severity",
]
