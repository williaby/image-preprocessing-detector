"""JSON Schema for Image Preprocessing Detector Output.

Defines Pydantic models for structured metadata output including detected issues,
document elements, planned actions, and transform history.

Stream 1 (Phase 10/11): Added three-tier script architecture, continuous detection
scores, and Docling routing support. See docs/planning/STREAM_1_SCHEMA_ANALYSIS.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, field_validator

# Bridge existing enums from annotation schemas and schema_utils
from image_preprocessing_detector.annotation.schemas.enums import CaptureMethod
from image_preprocessing_detector.schema_utils.iso_language_script import (
    SCRIPT_TO_FAMILY,
    ISO15924Script,
    ScriptFamily,
    normalize_legacy_script,
)

if TYPE_CHECKING:
    from image_preprocessing_detector.routing.script_router import ScriptRouter
    from image_preprocessing_detector.schema_utils.script_ml_mapping import (
        ScriptMLMapping,
    )


class IssueType(str, Enum):
    """Types of image quality issues that can be detected."""

    NOISE = "noise"
    BLUR = "blur"
    SKEW = "skew"
    PERSPECTIVE = "perspective"
    LOW_CONTRAST = "low_contrast"
    ORIENTATION = "orientation"
    LOW_DPI = "low_dpi"


class DocumentType(str, Enum):
    """Document type classification (Phase 8 + Office Support)."""

    IMAGE = "image"
    PDF = "pdf"
    OFFICE_WORD = "office_word"
    OFFICE_EXCEL = "office_excel"
    OFFICE_POWERPOINT = "office_powerpoint"


class OrientationAngle(int, Enum):
    """Detected document orientation angles (degrees clockwise from upright)."""

    UPRIGHT = 0
    ROTATED_90 = 90
    ROTATED_180 = 180
    ROTATED_270 = 270


class IssueSeverity(str, Enum):
    """Severity levels for detected issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ElementCategory(str, Enum):
    """Categories of document elements that can be detected.

    Includes all 11 DocLayNet classes plus additional project-specific categories.
    Reference: https://github.com/DS4SD/DocLayNet
    """

    # DocLayNet standard classes (11 classes)
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    LIST_ITEM = "list_item"
    PAGE_FOOTER = "page_footer"
    PAGE_HEADER = "page_header"
    PICTURE = "picture"
    SECTION_HEADER = "section_header"
    TABLE = "table"
    TEXT = "text"
    TITLE = "title"

    # Additional project-specific categories
    IMAGE = "image"  # Generic image element (legacy compatibility)
    HANDWRITING = "handwriting"  # Handwritten content detection
    TEXT_BLOCK = "text_block"  # Legacy text block (maps to TEXT)
    FIGURE = "figure"  # DocStructBench figure class (maps to PICTURE)

    @classmethod
    def from_canonical(cls, canonical_class: str) -> ElementCategory:
        """Map canonical taxonomy class to ElementCategory.

        Uses LayoutTaxonomy to convert a canonical class name (e.g.
        "FIGURE_CAPTION") to its DocLayNet equivalent, then maps to
        the corresponding ElementCategory enum value.

        Args:
            canonical_class: Canonical taxonomy class name (UPPERCASE).

        Returns:
            Matching ElementCategory, or TEXT as safe fallback.
        """
        from image_preprocessing_detector.schema_utils.layout_taxonomy import (
            get_default_taxonomy,
        )

        taxonomy = get_default_taxonomy()
        doclaynet_label = taxonomy.to_doclaynet(canonical_class)
        # Map DocLayNet label to ElementCategory value (lowercase with underscores)
        normalized = doclaynet_label.lower().replace("-", "_")
        try:
            return cls(normalized)
        except ValueError:
            return cls.TEXT  # safe fallback

    @property
    def canonical_name(self) -> str:
        """Return canonical taxonomy name for this category.

        Maps ElementCategory values (lowercase with underscores) to
        canonical UPPERCASE taxonomy class names via LayoutTaxonomy.

        Returns:
            Canonical class name (e.g. "CAPTION", "TABLE").
        """
        from image_preprocessing_detector.schema_utils.layout_taxonomy import (
            get_default_taxonomy,
        )

        taxonomy = get_default_taxonomy()
        # ElementCategory uses lowercase underscore values that match
        # DocLayNet labels when normalized. Restore hyphen form for DocLayNet.
        doclaynet_form = self.value.replace("_", "-").title()
        # Special cases: some values don't map cleanly to DocLayNet title case
        _value_to_doclaynet: dict[str, str] = {
            "caption": "Caption",
            "footnote": "Footnote",
            "formula": "Formula",
            "list_item": "List-item",
            "page_footer": "Page-footer",
            "page_header": "Page-header",
            "picture": "Picture",
            "section_header": "Section-header",
            "table": "Table",
            "text": "Text",
            "title": "Title",
            "image": "Picture",
            "handwriting": "Text",
            "text_block": "Text",
            "figure": "Picture",
        }
        doclaynet_label = _value_to_doclaynet.get(self.value, doclaynet_form)
        return taxonomy.to_canonical(doclaynet_label, "doclaynet")


class PDFType(str, Enum):
    """PDF document type classification (Phase 8)."""

    IMAGE_ONLY = "image_only"
    BORN_DIGITAL = "born_digital"
    HYBRID = "hybrid"


class OCRRoutingStrategy(str, Enum):
    """OCR routing recommendation strategies (Phase 8)."""

    OCR_FAST = "ocr_fast"
    OCR_ADVANCED = "ocr_advanced"
    VISION_SIMPLE = "vision_simple"
    VISION_STRUCTURED = "vision_structured"


class LayoutType(str, Enum):
    """Coarse page layout classification (Phase 6 - Layout-Lite)."""

    SINGLE_COLUMN = "single_column"
    MULTI_COLUMN = "multi_column"
    THREE_COLUMN = "three_column"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


# =============================================================================
# Graded Handwriting Assessment (Consensus-validated schema extension)
# =============================================================================


class HandwritingPresence(IntEnum):
    """Graded handwriting presence - QUANTITY of handwriting on page.

    Orthogonal to content type (what) and legibility (quality).
    Derived from HierText/COCO-Text word-level annotations via area ratios.

    Training data source: HierText (11K images), COCO-Text (63K images)
    Label derivation: Count handwritten words / total words per page
    """

    NONE = 0  # No handwriting detected
    SPARSE = 1  # <10% of page area contains handwriting
    MODERATE = 2  # 10-30% of page area
    SUBSTANTIAL = 3  # 30-60% of page area
    DOMINANT = 4  # >60% of page area


class HandwritingLegibility(IntEnum):
    """Graded handwriting legibility - how READABLE the handwriting is.

    Based on clinical Handwriting Legibility Scale (HLS) but simplified
    for OCR routing purposes. Higher values = harder to read.

    Training data source: HierText `legible` field, OCR confidence as proxy
    Label derivation: OCR confidence correlation with HLS clinical standards
    """

    NOT_APPLICABLE = 0  # No handwriting to assess
    EXCELLENT = 1  # Block print, very neat (OCR conf > 0.9)
    GOOD = 2  # Neat cursive, easily readable (OCR conf 0.7-0.9)
    FAIR = 3  # Readable with effort (OCR conf 0.5-0.7)
    POOR = 4  # Many words unclear (OCR conf 0.3-0.5)
    ILLEGIBLE = 5  # Historical/severely degraded (OCR conf < 0.3)


class HandwritingContentType(str, Enum):
    """Handwriting content type classification - WHAT is written.

    Orthogonal to presence (quantity) and legibility (quality).
    Important for routing: numeric-only handwriting routes differently than prose.
    """

    NOT_APPLICABLE = "not_applicable"  # No handwriting present
    SIGNATURES_MARKS = "signatures_marks"  # Signatures, initials, checkmarks
    NUMERIC = "numeric"  # Numbers only (dates, amounts, IDs)
    ALPHANUMERIC = "alphanumeric"  # Mixed letters and numbers (short)
    PROSE = "prose"  # Sentences, paragraphs (long-form text)
    MIXED = "mixed"  # Multiple types on same page
    SPECIALIZED = "specialized"  # Math, symbols, non-Latin scripts


class ActionType(str, Enum):
    """Types of correction actions that can be applied."""

    DESKEW = "deskew"
    PERSPECTIVE_CORRECTION = "perspective_correction"
    SHARPEN = "sharpen"
    DENOISE = "denoise"
    CLAHE = "clahe"
    BACKGROUND_NORMALIZATION = "background_normalization"
    UPSAMPLE = "upsample"
    ROTATE = "rotate"
    ORIENTATION_CORRECTION = "orientation_correction"


class DetectedIssue(BaseModel):
    """Represents a detected image quality issue."""

    type: IssueType = Field(..., description="Type of issue detected")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for detection"
    )
    severity: IssueSeverity = Field(..., description="Severity level of the issue")
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metrics specific to the issue type",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class PlannedAction(BaseModel):
    """Represents a correction action planned for an issue."""

    action: ActionType = Field(..., description="Type of correction action")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the correction action"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in this action"
    )
    reason: str = Field(..., description="Reason for this action")


class DocumentElement(BaseModel):
    """Represents a detected document element (table, image, etc.)."""

    id: str = Field(..., description="Unique identifier for this element")
    category: ElementCategory = Field(..., description="Category of the element")
    bbox: list[int] = Field(..., description="Bounding box [x, y, width, height]")
    polygon: list[list[int]] | None = Field(
        None, description="Optional polygon points for irregular shapes"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes (script, handwriting_prob, etc.)",
    )
    quality_issues: list[DetectedIssue] = Field(
        default_factory=list,
        description="Quality issues specific to this element (for images)",
    )
    needs_correction: bool = Field(
        default=False,
        description="Whether this element requires quality correction",
    )
    correction_applied: dict[str, Any] | None = Field(
        None, description="Details of correction applied to this element"
    )

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: list[int]) -> list[int]:
        """Ensure bbox has exactly 4 values."""
        if len(v) != 4:
            raise ValueError("Bounding box must have exactly 4 values [x, y, w, h]")
        if any(val < 0 for val in v):
            raise ValueError("Bounding box values must be non-negative")
        return v


class LanguageInfo(BaseModel):
    """Information about detected language/script in a document.

    Updated in Stream 1 to use typed ISO15924Script enum instead of free-form string.
    Maintains backward compatibility via script_str property.
    """

    script: ISO15924Script = Field(
        ...,
        description="Script code (ISO 15924 enum)",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in script detection"
    )
    language_code: str | None = Field(
        None,
        description="ISO 639-1/3 language code if known",
    )

    @property
    def script_str(self) -> str:
        """Backward-compatible string representation of script."""
        return self.script.value

    @classmethod
    def from_legacy(cls, script_name: str, confidence: float = 1.0) -> LanguageInfo:
        """Create LanguageInfo from legacy string script name.

        Args:
            script_name: Legacy script name (e.g., "Latin", "CJK", "Arabic")
            confidence: Detection confidence

        Returns:
            LanguageInfo with typed script enum
        """
        iso_code = normalize_legacy_script(script_name)
        try:
            script_enum = ISO15924Script(iso_code)
        except ValueError:
            script_enum = ISO15924Script.ZZZZ
        return cls(script=script_enum, confidence=confidence, language_code=None)


# =============================================================================
# Stream 1: Three-Tier Script Detection Architecture
# =============================================================================


class ScriptDetectionResult(BaseModel):
    """Script detection output preserving full ISO 15924 granularity (Tier 1).

    Three-tier architecture:
    - Tier 1 (Storage): Exact ISO 15924 code stored here - NEVER aggregate
    - Tier 2 (ML Training): Grouped classes via config (script_ml_classes.yaml)
    - Tier 3 (Routing): OCR engine selection via config (script_routing.yaml)

    Design principle: Store maximum granularity, compute aggregations from config.
    """

    # TIER 1: Exact ISO 15924 code (NEVER aggregate here)
    detected_script: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exact ISO 15924 4-letter code (e.g., 'Gujr', not 'Deva')",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Source provenance (preserve original labels for debugging)
    detection_method: str = Field(
        ...,
        description="Method: 'heuristic', 'siglip2_multitask', 'ocr_langdetect', 'dataset_ground_truth'",
    )
    source_label: str | None = Field(
        None,
        description="Original label from source data before normalization",
    )

    # Full probability distribution over ISO 15924 codes (for soft routing)
    script_probabilities: dict[str, float] = Field(
        default_factory=dict,
        description="Probability distribution over ISO 15924 codes",
    )

    # Unknown handling
    is_unknown: bool = Field(default=False)
    unknown_reason: str | None = Field(None)

    # For region-level detection (mixed-script documents)
    bbox: list[int] | None = Field(None, description="[x, y, w, h] if localized")
    page_index: int | None = Field(None, description="Page number if multi-page")

    def get_ml_class(self, mapping: ScriptMLMapping) -> str:
        """Get ML training class (Tier 2) via config mapping.

        Args:
            mapping: ScriptMLMapping instance with loaded config

        Returns:
            ML class string (e.g., "LATN", "INDIC_OTHER", "UNKNOWN")
        """
        return mapping.to_ml_class(self.detected_script)

    def get_routing_config(self, router: ScriptRouter) -> dict[str, Any]:
        """Get OCR routing config (Tier 3) via config.

        Args:
            router: ScriptRouter instance with loaded config

        Returns:
            Dict with engine, batch_size, and other routing params
        """
        return router.get_engine_config(self.detected_script)

    def get_script_family(self) -> ScriptFamily:
        """Get script family for high-level routing decisions."""
        return SCRIPT_TO_FAMILY.get(self.detected_script, ScriptFamily.OTHER)

    @classmethod
    def unknown(
        cls,
        reason: str,
        method: str = "heuristic",
        source_label: str | None = None,
    ) -> ScriptDetectionResult:
        """Factory for unknown script results."""
        return cls(
            detected_script="Zzzz",
            confidence=0.0,
            detection_method=method,
            source_label=source_label,
            script_probabilities={"Zzzz": 1.0},
            is_unknown=True,
            unknown_reason=reason,
            bbox=None,
            page_index=None,
        )

    @classmethod
    def from_source_label(
        cls,
        source_label: str,
        confidence: float = 1.0,
        method: str = "dataset_ground_truth",
    ) -> ScriptDetectionResult:
        """Create from source dataset label, normalizing to ISO 15924.

        Args:
            source_label: Original label from dataset
            confidence: Confidence in the label
            method: Detection method identifier

        Returns:
            ScriptDetectionResult with normalized ISO 15924 code
        """
        iso_code = normalize_legacy_script(source_label)
        return cls(
            detected_script=iso_code,
            confidence=confidence,
            detection_method=method,
            source_label=source_label,  # Preserve original!
            script_probabilities={iso_code: confidence},
            is_unknown=(iso_code == "Zzzz"),
            unknown_reason="unmapped_source_label" if iso_code == "Zzzz" else None,
            bbox=None,
            page_index=None,
        )


class DocumentScriptDetection(BaseModel):
    """Document-level script detection with full granularity preserved.

    Aggregates page/region-level detections while preserving all ISO 15924 detail.
    Multi-script documents are fully supported with per-instance tracking.
    """

    # ALL detected scripts with full detail (Tier 1 - preserve everything)
    script_instances: list[ScriptDetectionResult] = Field(
        default_factory=list,
        description="All script detections with full ISO 15924 codes",
    )

    # Document-level summary (computed from instances)
    dominant_script: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Most prevalent ISO 15924 code",
    )
    dominant_confidence: float = Field(..., ge=0.0, le=1.0)

    # Full distribution over ISO 15924 codes (not ML classes!)
    script_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage of pages/area per ISO 15924 code",
    )

    # Multi-script indicators
    is_multilingual: bool = Field(default=False)
    unique_scripts: list[str] = Field(
        default_factory=list,
        description="All unique ISO 15924 codes detected",
    )

    # Provenance
    detection_method: str = Field(default="aggregated")
    page_count: int = Field(default=0)
    region_count: int = Field(default=0)

    def get_ml_class_distribution(self, mapping: ScriptMLMapping) -> dict[str, float]:
        """Get distribution over ML classes (Tier 2) for training/routing.

        Args:
            mapping: ScriptMLMapping instance

        Returns:
            Dict mapping ML class names to percentages
        """
        ml_dist: dict[str, float] = {}
        for iso_code, pct in self.script_distribution.items():
            ml_class = mapping.to_ml_class(iso_code)
            ml_dist[ml_class] = ml_dist.get(ml_class, 0.0) + pct
        return ml_dist

    def get_dominant_script_family(self) -> ScriptFamily:
        """Get script family of dominant script."""
        return SCRIPT_TO_FAMILY.get(self.dominant_script, ScriptFamily.OTHER)

    @property
    def needs_multi_engine(self) -> bool:
        """Check if multiple OCR engines might be needed.

        Note: Actual routing determined by ScriptRouter config at runtime.
        """
        return len(self.unique_scripts) > 1

    @classmethod
    def from_instances(
        cls,
        instances: list[ScriptDetectionResult],
    ) -> DocumentScriptDetection:
        """Aggregate script instances to document level.

        Args:
            instances: List of per-region/per-page script detections

        Returns:
            DocumentScriptDetection with aggregated statistics
        """
        if not instances:
            return cls(
                script_instances=[],
                dominant_script="Zzzz",
                dominant_confidence=0.0,
                is_multilingual=False,
                detection_method="empty",
            )

        # Count by ISO 15924 code (preserve full granularity!)
        script_counts: dict[str, float] = {}
        confidence_sums: dict[str, float] = {}

        for inst in instances:
            code = inst.detected_script
            script_counts[code] = script_counts.get(code, 0) + 1
            confidence_sums[code] = confidence_sums.get(code, 0.0) + inst.confidence

        total = sum(script_counts.values())
        distribution = {k: v / total for k, v in script_counts.items()}

        # Find dominant (by count, not confidence)
        dominant = max(script_counts.keys(), key=lambda k: script_counts[k])
        dominant_conf = confidence_sums[dominant] / script_counts[dominant]

        unique = sorted(script_counts.keys(), key=lambda k: -script_counts[k])

        return cls(
            script_instances=instances,
            dominant_script=dominant,
            dominant_confidence=round(dominant_conf, 4),
            script_distribution=distribution,
            is_multilingual=len(unique) > 1,
            unique_scripts=unique,
            detection_method="aggregated",
            page_count=len(
                {i.page_index for i in instances if i.page_index is not None}
            ),
            region_count=len(instances),
        )


# =============================================================================
# Stream 1: Continuous Detection Scores
# =============================================================================


class TableComplexity(BaseModel):
    """Table structure complexity indicators for routing decisions.

    Used to determine fast vs accurate table extraction mode in Docling.
    """

    has_borders: bool = Field(default=True, description="Table has visible borders")
    estimated_rows: int = Field(default=0, ge=0)
    estimated_columns: int = Field(default=0, ge=0)
    has_merged_cells: bool = Field(default=False)
    complexity_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Overall complexity (0=simple grid, 1=complex merged cells)",
    )


class HandwritingAssessment(BaseModel):
    """Graded handwriting assessment with orthogonal dimensions.

    Three-dimensional assessment following consensus-validated schema:
    - Presence: How much handwriting? (quantity)
    - Legibility: How readable? (quality)
    - ContentType: What kind? (category)

    Design principle: Store discrete classifications + continuous scores.
    Continuous scores enable DQS weighting; discrete values enable routing rules.

    Training architecture: SigLIP v2 NaFlex multi-task head
    - 3 classification heads (presence, legibility, content_type)
    - 2 regression heads (presence_score, legibility_score)

    Backward compatibility: has_handwriting = (presence > NONE)
    """

    # Discrete classifications
    presence: HandwritingPresence = Field(
        default=HandwritingPresence.NONE,
        description="Graded handwriting presence (quantity)",
    )
    legibility: HandwritingLegibility = Field(
        default=HandwritingLegibility.NOT_APPLICABLE,
        description="Graded legibility (readability quality)",
    )
    content_type: HandwritingContentType = Field(
        default=HandwritingContentType.NOT_APPLICABLE,
        description="Content type classification (what is written)",
    )

    # Continuous scores for DQS integration.
    # Inference output is always >= 0.0 (absence expressed via presence=NONE enum).
    # Training manifests use -1.0 as the N_A masked sentinel; the data loader maps
    # -1.0 → task_mask=0 so MultiTaskLoss skips those samples.  This schema is
    # inference-only; the ge=0.0 constraint correctly rejects the training sentinel.
    presence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Continuous presence score (area ratio 0-1). "
            "Inference: 0.0 when presence=NONE. "
            "Training manifests use -1.0 as N_A sentinel (masked loss, not stored here)."
        ),
    )
    legibility_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Continuous legibility score (0=illegible, 1=excellent). "
            "Inference: 0.0 when legibility=NOT_APPLICABLE. "
            "Training manifests use -1.0 as N_A sentinel (masked loss, not stored here)."
        ),
    )

    # Confidence in predictions
    presence_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in presence classification",
    )
    legibility_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in legibility classification",
    )
    content_type_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in content type classification",
    )

    # Detection provenance
    detection_method: str = Field(
        default="none",
        description="Detection method: 'siglip2_multitask', 'heuristic', 'ground_truth'",
    )

    @property
    def has_handwriting(self) -> bool:
        """Backward-compatible binary handwriting flag."""
        return self.presence != HandwritingPresence.NONE

    @property
    def needs_advanced_ocr(self) -> bool:
        """Check if handwriting characteristics require advanced OCR.

        Triggers advanced OCR routing when:
        - Substantial+ handwriting presence (>30% of page)
        - Poor+ legibility (OCR confidence <0.5)
        - Specialized content (math, symbols)
        """
        return (
            self.presence >= HandwritingPresence.SUBSTANTIAL
            or self.legibility >= HandwritingLegibility.POOR
            or self.content_type == HandwritingContentType.SPECIALIZED
        )


class DoclingRoutingParams(BaseModel):
    """Docling CLI parameters derived from Project A analysis.

    Used to generate Docling command-line arguments for Project B handoff.
    """

    pipeline: Literal["standard", "vlm", "legacy"] = Field(
        default="standard",
        description="Docling pipeline selection",
    )
    vlm_model: str | None = Field(
        None,
        description="VLM model for vlm pipeline (e.g., 'deepseekocr_ollama')",
    )

    # OCR settings
    ocr_enabled: bool = Field(default=True)
    ocr_force: bool = Field(
        default=False,
        description="Force OCR even on born-digital with text layer",
    )
    ocr_engine: str = Field(
        default="auto",
        description="OCR engine: 'auto', 'rapidocr', 'tesseract' (note: 'paddleocr' is not a valid Docling engine key)",
    )
    ocr_lang: str | None = Field(
        None,
        description="OCR language hint (e.g., 'ch', 'ara+fas')",
    )
    psm: int | None = Field(
        None,
        ge=0,
        le=13,
        description="Tesseract Page Segmentation Mode (0-13)",
    )

    # Table settings
    tables_enabled: bool = Field(default=True)
    table_mode: Literal["fast", "accurate"] = Field(default="accurate")

    # Enrichment settings
    enrich_code: bool = Field(default=False)
    enrich_formula: bool = Field(default=False)

    # Performance settings
    page_batch_size: int = Field(
        default=4,
        ge=1,
        description="Pages to process per batch (reduce for CJK/memory)",
    )

    def to_cli_args(self) -> list[str]:
        """Convert to Docling CLI arguments.

        Returns:
            List of CLI argument strings
        """
        args = [f"--pipeline={self.pipeline}"]

        if self.vlm_model:
            args.append(f"--vlm-model={self.vlm_model}")

        if not self.ocr_enabled:
            args.append("--no-ocr")
        elif self.ocr_force:
            args.append("--force-ocr")

        if self.ocr_engine != "auto":
            args.append(f"--ocr-engine={self.ocr_engine}")

        if self.ocr_lang:
            args.append(f"--ocr-lang={self.ocr_lang}")

        if self.psm is not None:
            args.append(f"--psm={self.psm}")

        if not self.tables_enabled:
            args.append("--no-tables")
        else:
            args.append(f"--table-mode={self.table_mode}")

        if self.enrich_code:
            args.append("--enrich-code")

        if self.enrich_formula:
            args.append("--enrich-formula")

        args.append(f"--page-batch-size={self.page_batch_size}")

        return args

    def to_yaml(self) -> str:
        """Export as YAML configuration string."""
        import yaml

        return yaml.dump(self.model_dump(exclude_none=True), default_flow_style=False)


class OrientationDetection(BaseModel):
    """Document orientation detection result (Phase 8 - Orientation Detection).

    Detects if document pages are rotated 90°, 180°, or 270° from upright orientation.
    Common in scanned/photographed documents where the scanner or camera orientation
    doesn't match the document orientation.
    """

    detected_angle: OrientationAngle = Field(
        default=OrientationAngle.UPRIGHT,
        description="Detected orientation angle in degrees clockwise (0, 90, 180, 270)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for orientation detection",
    )
    detection_method: str = Field(
        ...,
        description="Detection method used (text_line_analysis, edge_histogram, ensemble)",
    )
    auto_corrected: bool = Field(
        default=False,
        description="Whether automatic orientation correction was applied",
    )
    needs_correction: bool = Field(
        default=False,
        description="Whether the page needs orientation correction (angle != 0)",
    )
    method_votes: dict[str, int] | None = Field(
        default=None,
        description="Votes from each detection method (for ensemble)",
        examples=[
            {"text_line_analysis": 90, "edge_histogram": 90, "component_ratio": 90}
        ],
    )


class DeskewDetection(BaseModel):
    """ML-based deskew detection result from SkewNet pipeline.

    Records both the coarse orientation correction and fine skew angle,
    along with confidence, uncertainty, and whether correction was applied.
    """

    orientation_angle: OrientationAngle = Field(
        default=OrientationAngle.UPRIGHT,
        description="Detected coarse orientation (0, 90, 180, 270 degrees)",
    )
    orientation_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence for orientation classification",
    )
    orientation_corrected: bool = Field(
        default=False,
        description="Whether 90-degree orientation correction was applied",
    )
    skew_angle: float = Field(
        default=0.0,
        description="Fine skew angle in degrees (positive = clockwise)",
    )
    skew_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence for skew bin classification",
    )
    skew_uncertainty: float = Field(
        default=0.0,
        ge=0.0,
        description="Predicted uncertainty (sigma) from regression head",
    )
    skew_corrected: bool = Field(
        default=False,
        description="Whether fine skew correction was applied",
    )
    detection_method: str = Field(
        default="ml",
        description="Detection method: ml, classical, ml+fallback, none",
    )
    skipped_reason: str | None = Field(
        default=None,
        description="Reason correction was skipped, if applicable",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total deskew pipeline latency in milliseconds",
    )


class TransformHistory(BaseModel):
    """Records a single transformation applied to the image."""

    action: str = Field(..., description="Name of the action performed")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters used for the action"
    )
    started_at: datetime = Field(..., description="When the action started")
    finished_at: datetime = Field(..., description="When the action finished")
    status: str = Field(..., description="Status: success, failed, skipped")
    error_message: str | None = Field(None, description="Error message if failed")

    @field_validator("finished_at")
    @classmethod
    def validate_finished_after_started(cls, v: datetime, info: Any) -> datetime:
        """Ensure finished_at is after started_at."""
        if "started_at" in info.data and v < info.data["started_at"]:
            raise ValueError("finished_at must be after started_at")
        return v


class DQSMetadata(BaseModel):
    """Document Quality Score metadata (Phase 8).

    Combines degradation (from IQA metrics) and structural complexity (from layout-lite)
    to provide holistic quality assessment for routing decisions.
    """

    degradation_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="IQA degradation score 0-1 (0=pristine, 1=severely degraded)",
    )
    structural_complexity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Layout complexity score 0-1 (0=simple, 1=very complex)",
    )


class PageLayoutSummary(BaseModel):
    """Coarse page-level layout attributes (Phase 6 - Layout-Lite).

    NOTE: This is NOT full semantic layout detection (which is Project B's responsibility).
    This provides only coarse page attributes for routing decisions.

    DocLayNet classes detected: Caption, Footnote, Formula, List-item, Page-footer,
    Page-header, Picture, Section-header, Table, Text, Title

    Stream 1: Added continuous scores for shadow, warping, code detection.
    Binary flags retained for convenience; continuous scores required for ML training.
    """

    page_number: int = Field(..., ge=1, description="1-based page number")
    layout_type: LayoutType = Field(..., description="Coarse layout classification")
    has_tables: bool = Field(default=False, description="Page contains table blocks")
    has_figures: bool = Field(default=False, description="Page contains figure blocks")
    has_dense_math: bool = Field(
        default=False, description="Page contains dense mathematical notation"
    )
    has_handwriting: bool = Field(
        default=False, description="Page contains handwritten content"
    )
    has_list_items: bool = Field(
        default=False,
        description="Page contains list items (DocLayNet List-item class)",
    )
    has_headers_footers: bool = Field(
        default=False,
        description="Page contains headers or footers (DocLayNet Page-header/Page-footer)",
    )
    fuzzy_scan: bool = Field(
        default=False, description="Page is a low-quality fuzzy scan"
    )
    watermark: bool = Field(default=False, description="Page contains watermark")
    colorful_background: bool = Field(
        default=False, description="Page has colorful/patterned background"
    )
    complexity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Structural complexity score 0-1 for routing",
    )

    # ==========================================================================
    # Stream 1: Continuous detection scores (required for gradient-based training)
    # ==========================================================================

    # Shadow detection (continuous)
    has_shadows: bool = Field(default=False, description="Page has shadow artifacts")
    shadow_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Shadow severity 0-1 (0=none, 1=severe)",
    )
    shadow_severity: Literal["none", "mild", "moderate", "severe"] = Field(
        default="none",
        description="Categorical shadow severity for display",
    )

    # Warping detection (continuous)
    has_warping: bool = Field(default=False, description="Page has warping/curvature")
    warping_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Warping severity 0-1 (>0.75 = extreme, needs VLM)",
    )
    warping_type: str | None = Field(
        None,
        description="Type: 'barrel', 'pincushion', 'perspective', 'wave'",
    )

    # Code detection (continuous)
    has_code: bool = Field(default=False, description="Page contains code blocks")
    code_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in code detection",
    )

    # Table complexity (when has_tables=True)
    table_complexity: TableComplexity | None = Field(
        None,
        description="Table structure complexity (if tables detected)",
    )

    # Handwriting confidence (continuous) - legacy field, use handwriting_assessment
    handwriting_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="DEPRECATED: Use handwriting_assessment.presence_score instead",
    )

    # Graded handwriting assessment (consensus-validated multi-dimensional)
    handwriting_assessment: HandwritingAssessment | None = Field(
        None,
        description="Graded handwriting assessment (presence, legibility, content_type)",
    )

    # Orientation info (populated from OrientationDetection)
    orientation_angle: int = Field(
        default=0,
        description="Detected orientation angle (0, 90, 180, 270)",
    )
    orientation_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in orientation detection",
    )
    orientation_corrected: bool = Field(
        default=False,
        description="Whether orientation correction was applied",
    )

    # Degradations list (for VLM escalation)
    degradations: list[str] = Field(
        default_factory=list,
        description="Detected degradation types (e.g., 'water_damage', 'torn', 'faded')",
    )


class PageMetadata(BaseModel):
    """Metadata for a single page in the document."""

    page_index: int = Field(..., ge=0, description="Zero-based page index")
    width_px: int = Field(..., gt=0, description="Page width in pixels")
    height_px: int = Field(..., gt=0, description="Page height in pixels")
    dpi_input: int = Field(..., gt=0, description="Input DPI of the page")
    dpi_effective: int = Field(..., gt=0, description="Effective DPI after processing")

    # Phase 2: ML IQA scores (Milestone 14.2)
    ml_iqa: dict[str, Any] | None = Field(
        None,
        description="Student model ML IQA scores (ResNet-18) - default inference",
        examples=[
            {
                "source": "student",
                "blur_score": 0.82,
                "noise_score": 0.78,
                "contrast_score": 0.85,
                "skew_score": 0.91,
                "compression_score": 0.87,
                "overall_quality": 0.85,
                "confidences": {
                    "blur": 0.82,
                    "noise": 0.78,
                    "contrast": 0.85,
                    "skew": 0.91,
                    "compression": 0.87,
                },
                "device": "cuda",
                "inference_time_ms": 15.3,
            }
        ],
    )

    # Phase 2: Teacher IQA scores (Milestone 14.2)
    teacher_iqa: dict[str, Any] | None = Field(
        None,
        description="Teacher model IQA scores (ResNet-50) for high-risk pages",
        examples=[
            {
                "source": "teacher",
                "blur_score": 0.85,
                "noise_score": 0.72,
                "contrast_score": 0.91,
                "skew_score": 0.88,
                "compression_score": 0.89,
                "overall_quality": 0.86,
                "escalation_reason": "high_entropy (0.850 >= 0.800); low_min_confidence (0.580 < 0.600)",
                "device": "cuda",
                "inference_time_ms": 28.7,
            }
        ],
    )

    # Phase 8: Orientation detection (for rotated scans/photos)
    orientation: OrientationDetection | None = Field(
        None,
        description="Phase 8: Orientation detection result (0°, 90°, 180°, 270° rotation)",
    )

    # ML-based deskew (SkewNet pipeline)
    deskew: DeskewDetection | None = Field(
        None,
        description="ML-based deskew detection and correction result (orientation + fine skew)",
    )

    detected_issues: list[DetectedIssue] = Field(
        default_factory=list, description="Page-level quality issues detected"
    )
    planned_actions: list[PlannedAction] = Field(
        default_factory=list, description="Planned correction actions"
    )
    elements: list[DocumentElement] = Field(
        default_factory=list, description="Detected document elements"
    )
    languages: list[LanguageInfo] = Field(
        default_factory=list, description="Detected languages/scripts"
    )
    transform_history: list[TransformHistory] = Field(
        default_factory=list, description="History of transformations applied"
    )


class ProcessingVersion(BaseModel):
    """Version information for the processing pipeline."""

    pipeline_version: str = Field(..., description="Version of the pipeline")
    iqa_model_hash: str | None = Field(
        None, description="Hash of the IQA model weights"
    )
    layout_model_hash: str | None = Field(
        None, description="Hash of the layout detection model weights"
    )
    thresholds: dict[str, Any] = Field(
        default_factory=dict, description="Threshold values used"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Processing timestamp"
    )


class TeacherUsage(BaseModel):
    """Metadata for teacher model usage during processing (Sprint 2.1.5).

    Tracks when and why the teacher model (more expensive/accurate) was invoked
    for specific pages that failed initial processing with the student model.
    """

    pages_with_teacher: list[int] = Field(
        default_factory=list,
        description="List of page indices where teacher model was used",
    )
    escalation_reasons: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of page index to escalation reason (e.g., 'low_confidence', 'detection_failure')",
    )
    teacher_device: str | None = Field(
        None,
        description="Device used for teacher model inference (e.g., 'cuda:0', 'cpu', 'modal')",
    )
    total_teacher_time_ms: int = Field(
        0,
        ge=0,
        description="Total time spent on teacher model inference in milliseconds",
    )


# Type aliases for backward compatibility and clearer naming
DocumentQualityScore = DQSMetadata  # Alias for routing module
OCRRoutingRecommendation = OCRRoutingStrategy  # Alias for routing module


class DocumentMetadata(BaseModel):
    """Complete metadata for a processed document.

    This schema represents Project A's output, which serves as input to Project B
    (OCR Orchestration) in the four-project RAG Pipeline.
    """

    document_id: str = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original filename")
    source_mime: str = Field(..., description="Source MIME type")
    document_type: DocumentType = Field(
        default=DocumentType.PDF,
        description="Document type classification (image, pdf, office_word, office_excel, office_powerpoint)",
    )
    num_pages: int = Field(..., gt=0, description="Total number of pages")

    # Phase 4: DPI Upscaling (optional - only if upscaling was performed)
    upscaling: dict[str, Any] | None = Field(
        None,
        description="Phase 4: DPI upscaling metadata (if performed)",
        examples=[
            {
                "performed": True,
                "upscaled_path": "/tmp/upscaled_doc.pdf",  # nosec B108
                "original_dpi": 150,
                "target_dpi": 300,
                "algorithm": "lanczos",
                "processing_time_ms": 345,
                "file_size_before": 1024000,
                "file_size_after": 2048000,
            }
        ],
    )

    # Phase 8: Routing Metadata (Optional until Phase 8 implementation, then REQUIRED for Project B handoff)
    pdf_type: PDFType | None = Field(
        None,
        description="Phase 8: PDF type classification (image_only/born_digital/hybrid)",
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Phase 8: ISO 639-1 language codes detected in document",
    )
    has_non_latin: bool = Field(
        default=False, description="Phase 8: Document contains non-Latin scripts"
    )
    pre_ocr_risk: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Phase 8: Pre-OCR processing risk score 0-1 (for routing decisions)",
    )
    dqs: DQSMetadata | None = Field(
        None, description="Phase 8: Document Quality Score (degradation + complexity)"
    )
    ocr_routing_recommendation: OCRRoutingStrategy | None = Field(
        None,
        description="Phase 8: Recommended OCR strategy for Project B",
    )
    page_layout_summary: list[PageLayoutSummary] = Field(
        default_factory=list,
        description="Phase 6: Per-page coarse layout attributes (layout-lite, NOT full semantic layout)",
    )

    # Phase 2.1.5: Teacher model usage tracking (Sprint 2.1.5)
    teacher_usage: TeacherUsage | None = Field(
        None,
        description="Phase 2: Metadata for teacher model usage (tracks escalation from student to teacher model)",
    )

    # ==========================================================================
    # Stream 1 (Phase 10/11): Enhanced routing and script detection
    # ==========================================================================

    # Capture method (different from pdf_type! See STREAM_1_SCHEMA_ANALYSIS.md)
    capture_method: CaptureMethod | None = Field(
        None,
        description="How document was captured (scanner, camera, born_digital). Different from pdf_type!",
    )
    capture_method_confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in capture method classification",
    )

    # Script detection (three-tier architecture)
    script_detection: DocumentScriptDetection | None = Field(
        None,
        description="Full script detection with ISO 15924 codes and multi-script support",
    )

    # Text layer quality (for born_digital/hybrid PDFs)
    text_layer_quality: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="PDF text layer quality (1.0 = perfect, can skip OCR)",
    )
    text_layer_skip_ocr: bool = Field(
        default=False,
        description="True if text layer is good enough to skip OCR",
    )

    # Degradation severity (for DocRes routing)
    degradation_severity: Literal["simple", "complex"] = Field(
        default="simple",
        description="simple = classical CV sufficient, complex = needs DocRes/VLM",
    )

    # Docling routing parameters
    docling_params: DoclingRoutingParams | None = Field(
        None,
        description="Generated Docling CLI parameters for Project B",
    )

    # PSM recommendation (Tesseract Page Segmentation Mode)
    recommended_psm: int | None = Field(
        None,
        ge=0,
        le=13,
        description="Recommended Tesseract PSM based on layout analysis",
    )

    # VLM escalation tracking
    vlm_escalation_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for VLM pipeline escalation (for debugging/telemetry)",
    )

    # Existing fields
    processing_version: ProcessingVersion = Field(
        ..., description="Version information"
    )
    pages: list[PageMetadata] = Field(..., description="Metadata for each page")

    @field_validator("pages")
    @classmethod
    def validate_pages_count(
        cls, v: list[PageMetadata], info: Any
    ) -> list[PageMetadata]:
        """Ensure number of pages matches num_pages field."""
        if "num_pages" in info.data and len(v) != info.data["num_pages"]:
            raise ValueError(
                f"Number of page metadata entries ({len(v)}) must match "
                f"num_pages ({info.data['num_pages']})"
            )
        return v

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON with datetime handling."""
        return super().model_dump_json(exclude_none=True, by_alias=True, **kwargs)

    @classmethod
    def from_json_file(cls, path: str) -> DocumentMetadata:
        """Load document metadata from JSON file."""
        with open(path, encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

    def to_json_file(self, path: str) -> None:
        """Save document metadata to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
