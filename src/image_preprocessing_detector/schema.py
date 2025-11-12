"""
JSON Schema for Image Preprocessing Detector Output.

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


class ElementRelation(BaseModel):
    """Represents a relationship between document elements (OmniDocBench)."""

    type: str = Field(..., description="Relationship type (e.g., 'parent_son')")
    target_id: str = Field(..., description="ID of the target element")


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
        description=(
            "Additional attributes (script, handwriting_prob, etc.). "
            "OmniDocBench attributes: handwriting (bool), table_layout (str), "
            "with_span (bool)"
        ),
    )
    relations: list[ElementRelation] = Field(
        default_factory=list,
        description="OmniDocBench: Relationships to other elements (parent_son, etc.)",
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


class ReadingOrder(BaseModel):
    """Represents reading order between elements (OmniDocBench)."""

    anno_id: int = Field(..., description="ID of current annotation/element")
    next_id: int = Field(..., description="ID of next element in reading order")


class PageMetadata(BaseModel):
    """Metadata for a single page in the document."""

    page_index: int = Field(..., ge=0, description="Zero-based page index")
    width_px: int = Field(..., gt=0, description="Page width in pixels")
    height_px: int = Field(..., gt=0, description="Page height in pixels")
    dpi_input: int = Field(..., gt=0, description="Input DPI of the page")
    dpi_effective: int = Field(..., gt=0, description="Effective DPI after processing")

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
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "OmniDocBench: Page-level attributes (data_source, language, layout, "
            "watermark, fuzzy_scan, colorful_background)"
        ),
    )
    reading_order: list[ReadingOrder] = Field(
        default_factory=list,
        description="OmniDocBench: Reading order graph between elements",
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


class DocumentMetadata(BaseModel):
    """Complete metadata for a processed document."""

    document_id: str = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original filename")
    source_mime: str = Field(..., description="Source MIME type")
    num_pages: int = Field(..., gt=0, description="Total number of pages")
    upscaling: dict[str, Any] | None = Field(
        None,
        description="Phase 1B: DPI upscaling metadata (if performed)",
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
