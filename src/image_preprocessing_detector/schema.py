"""JSON Schema for Image Preprocessing Detector Output.

Defines Pydantic models for structured metadata output including detected issues,
document elements, planned actions, and transform history.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class IssueType(str, Enum):
    """Types of image quality issues that can be detected."""

    NOISE = "noise"
    BLUR = "blur"
    SKEW = "skew"
    PERSPECTIVE = "perspective"
    LOW_CONTRAST = "low_contrast"
    ORIENTATION = "orientation"
    LOW_DPI = "low_dpi"


class IssueSeverity(str, Enum):
    """Severity levels for detected issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ElementCategory(str, Enum):
    """Categories of document elements that can be detected."""

    TABLE = "table"
    IMAGE = "image"
    HANDWRITING = "handwriting"
    FORMULA = "formula"
    TEXT_BLOCK = "text_block"
    FIGURE = "figure"


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
    """Information about detected language/script in a document."""

    script: str = Field(..., description="Script name (e.g., Latin, CJK, Arabic)")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in script detection"
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


class PageMetadata(BaseModel):
    """Metadata for a single page in the document."""

    page_index: int = Field(..., ge=0, description="Zero-based page index")
    width_px: int = Field(..., gt=0, description="Page width in pixels")
    height_px: int = Field(..., gt=0, description="Page height in pixels")
    dpi_input: int = Field(..., gt=0, description="Input DPI of the page")
    dpi_effective: int = Field(..., gt=0, description="Effective DPI after processing")

    # Phase 2.1.6: Teacher IQA scores (Sprint 2.1.6)
    teacher_iqa: dict[str, float] | None = Field(
        None,
        description="Teacher model IQA scores (ResNet-50) for high-risk pages",
        examples=[
            {
                "blur_score": 0.85,
                "noise_score": 0.72,
                "contrast_score": 0.91,
                "overall_quality": 0.83,
            }
        ],
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


class DocumentMetadata(BaseModel):
    """Complete metadata for a processed document.

    This schema represents Project A's output, which serves as input to Project B
    (OCR Orchestration) in the four-project RAG Pipeline.
    """

    document_id: str = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original filename")
    source_mime: str = Field(..., description="Source MIME type")
    num_pages: int = Field(..., gt=0, description="Total number of pages")

    # Phase 4: DPI Upscaling (optional - only if upscaling was performed)
    upscaling: dict[str, Any] | None = Field(
        None,
        description="Phase 4: DPI upscaling metadata (if performed)",
        examples=[
            {
                "performed": True,
                "upscaled_path": "/tmp/upscaled_doc.pdf",  # nosec B108  # noqa: S108
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
    def from_json_file(cls, path: str) -> "DocumentMetadata":
        """Load document metadata from JSON file."""
        with open(path, encoding="utf-8") as f:
            return cls.model_validate_json(f.read())

    def to_json_file(self, path: str) -> None:
        """Save document metadata to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
