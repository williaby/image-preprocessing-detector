"""
JSON output generation for document metadata.

Aggregates detection results and corrections into structured JSON output
using Pydantic schema validation.
"""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from image_preprocessing_detector.correction.corrections import CorrectionResult
from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetectionResult,
    ContrastDetectionResult,
    SkewDetectionResult,
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

logger = get_logger(__name__)


class MetadataBuilder:
    """
    Builds document metadata from detection and correction results.

    Aggregates per-page results into a complete DocumentMetadata object.
    """

    def __init__(self, document_id: str, file_name: str) -> None:
        """
        Initialize metadata builder.

        Args:
            document_id: Unique document identifier
            file_name: Original filename
        """
        self.document_id = document_id
        self.file_name = file_name
        self.pages: list[PageMetadata] = []

        logger.info(
            "Metadata builder initialized",
            document_id=document_id,
            file_name=file_name,
        )

    def add_page(
        self,
        page_number: int,
        page_data: PageImage | tuple[np.ndarray, ImageMetadata],
        text_result: TextDetectionResult | None = None,  # noqa: ARG002
        skew_result: SkewDetectionResult | None = None,
        blur_result: BlurDetectionResult | None = None,
        contrast_result: ContrastDetectionResult | None = None,
        skew_correction: CorrectionResult | None = None,
        contrast_correction: CorrectionResult | None = None,
        blur_correction: CorrectionResult | None = None,
        elements: list[DocumentElement] | None = None,
    ) -> None:
        """
        Add page metadata from detection and correction results.

        Args:
            page_number: Zero-based page index
            page_data: PageImage from PDF or (image, metadata) tuple from direct image
            text_result: Text detection result (optional)
            skew_result: Skew detection result (optional)
            blur_result: Blur detection result (optional)
            contrast_result: Contrast detection result (optional)
            skew_correction: Skew correction result (optional)
            contrast_correction: Contrast correction result (optional)
            blur_correction: Blur correction result (optional)
            elements: Document elements (tables, images, etc.) (optional)
        """
        # Extract page dimensions and DPI
        if isinstance(page_data, PageImage):
            width = page_data.width
            height = page_data.height
            dpi_input = int(page_data.dpi_input)
            dpi_effective = int(page_data.dpi_effective)
        else:
            image, metadata = page_data
            width = metadata.width
            height = metadata.height
            dpi_input = int(metadata.dpi or 72.0)
            dpi_effective = dpi_input

        # Collect detected issues
        detected_issues: list[DetectedIssue] = []

        if skew_result and skew_result.is_skewed:
            # Convert Severity to IssueSeverity
            severity = IssueSeverity(skew_result.severity.value)
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.SKEW,
                    severity=severity,
                    confidence=skew_result.confidence,
                    metrics={"angle": skew_result.angle, "method": skew_result.method},
                )
            )

        if blur_result and blur_result.is_blurred:
            severity = IssueSeverity(blur_result.severity.value)
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.BLUR,
                    severity=severity,
                    confidence=blur_result.confidence,
                    metrics={"score": blur_result.score},
                )
            )

        if contrast_result and contrast_result.is_low_contrast:
            severity = IssueSeverity(contrast_result.severity.value)
            detected_issues.append(
                DetectedIssue(
                    type=IssueType.LOW_CONTRAST,
                    severity=severity,
                    confidence=contrast_result.confidence,
                    metrics={"score": contrast_result.score},
                )
            )

        # Build planned actions
        planned_actions: list[PlannedAction] = []
        if skew_result and skew_result.is_skewed:
            planned_actions.append(
                PlannedAction(
                    action=ActionType.DESKEW,
                    params={"angle": skew_result.angle},
                    confidence=skew_result.confidence,
                    reason=f"Detected skew of {abs(skew_result.angle):.2f}°",
                )
            )
        if contrast_result and contrast_result.is_low_contrast:
            planned_actions.append(
                PlannedAction(
                    action=ActionType.CLAHE,
                    params={"score": contrast_result.score},
                    confidence=contrast_result.confidence,
                    reason=f"Low contrast detected (score: {contrast_result.score:.2f})",
                )
            )
        if blur_result and blur_result.is_blurred:
            planned_actions.append(
                PlannedAction(
                    action=ActionType.SHARPEN,
                    params={"blur_score": blur_result.score},
                    confidence=blur_result.confidence,
                    reason=f"Blur detected (score: {blur_result.score:.1f})",
                )
            )

        # Build transform history
        transform_history: list[TransformHistory] = []

        if skew_correction and skew_correction.applied:
            now = datetime.now(UTC)
            transform_history.append(
                TransformHistory(
                    action="deskew",
                    params=skew_correction.parameters,
                    started_at=now,
                    finished_at=now,
                    status="success",
                    error_message=None,
                )
            )

        if contrast_correction and contrast_correction.applied:
            now = datetime.now(UTC)
            transform_history.append(
                TransformHistory(
                    action="clahe_contrast_enhancement",
                    params=contrast_correction.parameters,
                    started_at=now,
                    finished_at=now,
                    status="success",
                    error_message=None,
                )
            )

        if blur_correction and blur_correction.applied:
            now = datetime.now(UTC)
            transform_history.append(
                TransformHistory(
                    action="unsharp_mask_sharpening",
                    params=blur_correction.parameters,
                    started_at=now,
                    finished_at=now,
                    status="success",
                    error_message=None,
                )
            )

        # Create page metadata
        page_metadata = PageMetadata(
            page_index=page_number,
            width_px=width,
            height_px=height,
            dpi_input=dpi_input,
            dpi_effective=dpi_effective,
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
        """
        Build final DocumentMetadata object.

        Args:
            processing_version: Version of processing pipeline

        Returns:
            Complete DocumentMetadata object

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

        metadata = DocumentMetadata(
            document_id=self.document_id,
            file_name=self.file_name,
            source_mime=source_mime,
            num_pages=len(self.pages),
            processing_version=proc_version,
            pages=self.pages,
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
    """
    Generate JSON output file from DocumentMetadata.

    Args:
        metadata: Complete document metadata
        output_path: Path to write JSON file
        pretty: Use pretty printing (default: True)

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
    """
    Load DocumentMetadata from JSON file.

    Args:
        input_path: Path to JSON file

    Returns:
        DocumentMetadata object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid

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
