"""JSON output generation for document metadata.

Aggregates detection results and corrections into structured JSON output
using Pydantic schema validation.
"""

from pathlib import Path
from typing import Any

import numpy as np

from image_preprocessing_detector.correction.corrections import CorrectionResult
from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
    SkewDetectionResult,
)
from image_preprocessing_detector.detection.iqa_ml import (
    MLIQAScores,
    ml_iqa_scores_to_dict,
    teacher_iqa_to_dict,
)
from image_preprocessing_detector.detection.text_gate import TextDetectionResult
from image_preprocessing_detector.ingestion.image_loader import ImageMetadata
from image_preprocessing_detector.ingestion.pdf_loader import PageImage
from image_preprocessing_detector.schema import (
    ActionType,
    DetectedIssue,
    DocumentElement,
    DocumentMetadata,
    IssueSeverity,
    IssueType,
    PageMetadata,
    PlannedAction,
    ProcessingVersion,
    TransformHistory,
)
from image_preprocessing_detector.utils import get_logger
from image_preprocessing_detector.utils.datetime_compat import UTC, datetime

logger = get_logger(__name__)


def _extract_page_dimensions(
    page_data: "PageImage | tuple[np.ndarray, ImageMetadata]",
) -> tuple[int, int, int, int]:
    """Extract page dimensions and DPI from page data.

    Args:
        page_data ('PageImage | tuple[np.ndarray, ImageMetadata]'): PageImage from PDF or (image, metadata) tuple from direct image

    Returns:
        tuple[int, int, int, int]: Tuple of (width, height, dpi_input, dpi_effective)
    """
    if isinstance(page_data, PageImage):
        return (
            page_data.width,
            page_data.height,
            int(page_data.dpi_input),
            int(page_data.dpi_effective),
        )
    _image, metadata = page_data
    dpi_input = int(metadata.dpi or 72.0)
    return metadata.width, metadata.height, dpi_input, dpi_input


def _collect_detected_issues(
    skew_result: "SkewDetectionResult | None",
    blur_result: "BlurDetectionResult | None",
    contrast_result: "ContrastDetectionResult | None",
) -> list[DetectedIssue]:
    """Collect detected issues from detection results.

    Args:
        skew_result ('SkewDetectionResult | None'): Skew detection result
        blur_result ('BlurDetectionResult | None'): Blur detection result
        contrast_result ('ContrastDetectionResult | None'): Contrast detection result

    Returns:
        list[DetectedIssue]: List of detected issues
    """
    issues: list[DetectedIssue] = []

    if skew_result and skew_result.is_skewed:
        severity = IssueSeverity(skew_result.severity.value)
        issues.append(
            DetectedIssue(
                type=IssueType.SKEW,
                severity=severity,
                confidence=skew_result.confidence,
                metrics={"angle": skew_result.angle, "method": skew_result.method},
            )
        )

    if blur_result and blur_result.is_blurred:
        severity = IssueSeverity(blur_result.severity.value)
        issues.append(
            DetectedIssue(
                type=IssueType.BLUR,
                severity=severity,
                confidence=blur_result.confidence,
                metrics={"score": blur_result.score},
            )
        )

    if contrast_result and contrast_result.is_low_contrast:
        severity = IssueSeverity(contrast_result.severity.value)
        issues.append(
            DetectedIssue(
                type=IssueType.LOW_CONTRAST,
                severity=severity,
                confidence=contrast_result.confidence,
                metrics={"score": contrast_result.score},
            )
        )

    return issues


def _build_planned_actions(
    skew_result: "SkewDetectionResult | None",
    blur_result: "BlurDetectionResult | None",
    contrast_result: "ContrastDetectionResult | None",
) -> list[PlannedAction]:
    """Build planned actions from detection results.

    Args:
        skew_result ('SkewDetectionResult | None'): Skew detection result
        blur_result ('BlurDetectionResult | None'): Blur detection result
        contrast_result ('ContrastDetectionResult | None'): Contrast detection result

    Returns:
        list[PlannedAction]: List of planned actions
    """
    actions: list[PlannedAction] = []

    if skew_result and skew_result.is_skewed:
        actions.append(
            PlannedAction(
                action=ActionType.DESKEW,
                params={"angle": skew_result.angle},
                confidence=skew_result.confidence,
                reason=f"Detected skew of {abs(skew_result.angle):.2f}°",
            )
        )

    if contrast_result and contrast_result.is_low_contrast:
        actions.append(
            PlannedAction(
                action=ActionType.CLAHE,
                params={"score": contrast_result.score},
                confidence=contrast_result.confidence,
                reason=f"Low contrast detected (score: {contrast_result.score:.2f})",
            )
        )

    if blur_result and blur_result.is_blurred:
        actions.append(
            PlannedAction(
                action=ActionType.SHARPEN,
                params={"blur_score": blur_result.score},
                confidence=blur_result.confidence,
                reason=f"Blur detected (score: {blur_result.score:.1f})",
            )
        )

    return actions


def _add_transform_entry(
    correction: "CorrectionResult | None",
    action_name: str,
) -> TransformHistory | None:
    """Create a transform history entry if correction was applied.

    Args:
        correction ('CorrectionResult | None'): Correction result
        action_name (str): Name of the transform action

    Returns:
        TransformHistory | None: TransformHistory entry or None if not applied
    """
    if not correction or not correction.applied:
        return None
    now = datetime.now(UTC)
    return TransformHistory(
        action=action_name,
        params=correction.parameters,
        started_at=now,
        finished_at=now,
        status="success",
        error_message=None,
    )


def _build_transform_history(
    skew_correction: "CorrectionResult | None",
    contrast_correction: "CorrectionResult | None",
    blur_correction: "CorrectionResult | None",
) -> list[TransformHistory]:
    """Build transform history from correction results.

    Args:
        skew_correction ('CorrectionResult | None'): Skew correction result
        contrast_correction ('CorrectionResult | None'): Contrast correction result
        blur_correction ('CorrectionResult | None'): Blur correction result

    Returns:
        list[TransformHistory]: List of transform history entries
    """
    history: list[TransformHistory] = []

    if entry := _add_transform_entry(skew_correction, "deskew"):
        history.append(entry)
    if entry := _add_transform_entry(contrast_correction, "clahe_contrast_enhancement"):
        history.append(entry)
    if entry := _add_transform_entry(blur_correction, "unsharp_mask_sharpening"):
        history.append(entry)

    return history


class MetadataBuilder:
    """Builds document metadata from detection and correction results.

    Aggregates per-page results into a complete DocumentMetadata object.

    Args:
        document_id (str): Unique document identifier
        file_name (str): Original filename
    """

    def __init__(self, document_id: str, file_name: str) -> None:
        self.document_id = document_id
        self.file_name = file_name
        self.pages: list[PageMetadata] = []
        self.upscaling_metadata: dict[str, Any] | None = None

        logger.info(
            "Metadata builder initialized",
            document_id=document_id,
            file_name=file_name,
        )

    def set_upscaling_metadata(self, upscaling_result: dict[str, Any]) -> None:
        """Set PDF upscaling metadata (Phase 1B).

        Args:
            upscaling_result (dict[str, Any]): Upscaling result from PDFUpscaler
        """
        self.upscaling_metadata = upscaling_result
        logger.info(
            "Upscaling metadata added",
            performed=upscaling_result.get("success", False),
            processing_time=upscaling_result.get("processing_time_seconds"),
        )

    def add_page(
        self,
        page_number: int,
        page_data: PageImage | tuple[np.ndarray, ImageMetadata],
        _text_result: TextDetectionResult | None = None,  # Reserved for future use
        skew_result: SkewDetectionResult | None = None,
        blur_result: BlurDetectionResult | None = None,
        contrast_result: ContrastDetectionResult | None = None,
        skew_correction: CorrectionResult | None = None,
        contrast_correction: CorrectionResult | None = None,
        blur_correction: CorrectionResult | None = None,
        elements: list[DocumentElement] | None = None,
        ml_iqa_student: MLIQAScores | None = None,
        ml_iqa_teacher: MLIQAScores | None = None,
        ml_iqa_escalation_reason: str | None = None,
    ) -> None:
        """Add page metadata from detection and correction results.

        Args:
            page_number (int): Zero-based page index
            page_data (PageImage | tuple[np.ndarray, ImageMetadata]): PageImage from PDF or (image, metadata) tuple from direct image
            _text_result (TextDetectionResult | None): Text detection result (reserved for future use)
            skew_result (SkewDetectionResult | None): Skew detection result (optional)
            blur_result (BlurDetectionResult | None): Blur detection result (optional)
            contrast_result (ContrastDetectionResult | None): Contrast detection result (optional)
            skew_correction (CorrectionResult | None): Skew correction result (optional)
            contrast_correction (CorrectionResult | None): Contrast correction result (optional)
            blur_correction (CorrectionResult | None): Blur correction result (optional)
            elements (list[DocumentElement] | None): Document elements (tables, images, etc.) (optional)
            ml_iqa_student (MLIQAScores | None): Student ML IQA scores (Phase 2) (optional)
            ml_iqa_teacher (MLIQAScores | None): Teacher ML IQA scores if escalated (Phase 2) (optional)
            ml_iqa_escalation_reason (str | None): Reason for teacher escalation (Phase 2) (optional)
        """
        # Extract page dimensions using helper
        width, height, dpi_input, dpi_effective = _extract_page_dimensions(page_data)

        # Collect detected issues using helper
        detected_issues = _collect_detected_issues(
            skew_result, blur_result, contrast_result
        )

        # Build planned actions using helper
        planned_actions = _build_planned_actions(
            skew_result, blur_result, contrast_result
        )

        # Build transform history using helper
        transform_history = _build_transform_history(
            skew_correction, contrast_correction, blur_correction
        )

        # Convert ML IQA scores to dict format if provided
        ml_iqa_dict = ml_iqa_scores_to_dict(ml_iqa_student) if ml_iqa_student else None
        teacher_iqa_dict = (
            teacher_iqa_to_dict(ml_iqa_teacher, ml_iqa_escalation_reason)
            if ml_iqa_teacher
            else None
        )

        # Create page metadata
        page_metadata = PageMetadata(
            page_index=page_number,
            width_px=width,
            height_px=height,
            dpi_input=dpi_input,
            dpi_effective=dpi_effective,
            ml_iqa=ml_iqa_dict,
            teacher_iqa=teacher_iqa_dict,
            detected_issues=detected_issues,
            planned_actions=planned_actions,
            elements=elements or [],
            transform_history=transform_history,
        )

        self.pages.append(page_metadata)

        logger.debug(
            "Page metadata added",
            page_number=page_number,
            issues=len(detected_issues),
            actions=len(planned_actions),
            transforms=len(transform_history),
        )

    def build(self, processing_version: str = "1.0.0") -> DocumentMetadata:
        """Build final DocumentMetadata object.

        Args:
            processing_version (str): Version of processing pipeline

        Returns:
            DocumentMetadata: Complete DocumentMetadata object

        Raises:
            ValueError: If no pages have been added
        """
        if not self.pages:
            raise ValueError("Cannot build metadata: no pages added")

        # Detect MIME type from file extension
        file_path = Path(self.file_name)
        suffix = file_path.suffix.lower()
        mime_type_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        source_mime = mime_type_map.get(suffix, "application/octet-stream")

        # Create ProcessingVersion object
        proc_version = ProcessingVersion(
            pipeline_version=processing_version,
            iqa_model_hash=None,
            layout_model_hash=None,
            thresholds={},
        )

        # Phase 8 fields: Set to None until Phase 6-8 implementations complete
        # These will be populated by:
        # - pdf_type: Phase 8 PDF classifier
        # - pre_ocr_risk: Phase 8 risk scorer
        # - dqs: Phase 8 DQS calculator
        # - ocr_routing_recommendation: Phase 8 routing engine
        # - page_layout_summary: Phase 6 layout-lite detector (already defaults to empty list)

        metadata = DocumentMetadata(
            document_id=self.document_id,
            file_name=self.file_name,
            source_mime=source_mime,
            num_pages=len(self.pages),
            upscaling=self.upscaling_metadata,  # Phase 1B: Use upscaling metadata if set
            processing_version=proc_version,
            pages=self.pages,
            # Phase 8 fields (optional until implementation)
            pdf_type=None,
            pre_ocr_risk=None,
            dqs=None,
            ocr_routing_recommendation=None,
            teacher_usage=None,  # Phase 2: Will be populated if teacher model is used
            # page_layout_summary defaults to empty list (will be populated in Phase 6)
        )

        logger.info(
            "Document metadata built",
            document_id=self.document_id,
            num_pages=len(self.pages),
            total_issues=sum(len(p.detected_issues) for p in self.pages),
        )

        return metadata


def generate_json(
    metadata: DocumentMetadata,
    output_path: str | Path,
    pretty: bool = True,
) -> None:
    """Generate JSON output file from DocumentMetadata.

    Args:
        metadata (DocumentMetadata): Complete document metadata
        output_path (str | Path): Path to write JSON file
        pretty (bool): Use pretty printing (default: True)

    Example:
        >>> metadata = MetadataBuilder("doc_001", "sample.pdf").build()
        >>> generate_json(metadata, "output.json")
    """
    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON file using Pydantic's built-in serialization
    if pretty:
        # Use built-in method with indent=2
        metadata.to_json_file(str(output_path))
    else:
        # Write compact JSON
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json())

    logger.info(
        "JSON output generated",
        output_path=str(output_path),
        pages=len(metadata.pages),
        size_bytes=output_path.stat().st_size,
    )


def load_json(input_path: str | Path) -> DocumentMetadata:
    """Load DocumentMetadata from JSON file.

    Args:
        input_path (str | Path): Path to JSON file

    Returns:
        DocumentMetadata: DocumentMetadata object

    Raises:
        FileNotFoundError: If file doesn't exist

    Example:
        >>> metadata = load_json("output.json")
        >>> print(f"Loaded {len(metadata.pages)} pages")
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"JSON file not found: {input_path}")

    metadata = DocumentMetadata.from_json_file(str(input_path))

    logger.info(
        "JSON metadata loaded",
        input_path=str(input_path),
        document_id=metadata.document_id,
        pages=len(metadata.pages),
    )

    return metadata
