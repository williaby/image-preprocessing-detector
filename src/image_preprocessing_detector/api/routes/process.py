"""Document processing endpoint.

Sprint 5.2.2: POST /process endpoint
- Single file upload with size/type validation
- Async pipeline call
- Response contract with metadata summary and links
- Error handling with structured codes
"""

import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse

from image_preprocessing_detector.api.config import get_api_settings
from image_preprocessing_detector.api.middleware import get_correlation_id
from image_preprocessing_detector.api.models import (
    DQSSummary,
    ErrorCode,
    ErrorResponse,
    IQAScoreSummary,
    PageSummary,
    ProcessingOptions,
    ProcessingResult,
    ProcessingStatus,
    ProcessResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/process", tags=["process"])

# Supported file types
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/webp",
}

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"}


def validate_file(file: UploadFile, _max_size_mb: int) -> ErrorResponse | None:
    """Validate uploaded file.

    Args:
        file: The uploaded file.
        _max_size_mb: Maximum allowed file size in MB (reserved for future use).

    Returns:
        ErrorResponse if validation fails, None if valid.
    """
    # Check file name
    if not file.filename:
        return ErrorResponse(
            error=ErrorCode.INVALID_PARAMETERS,
            message="File name is required",
        )

    # Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return ErrorResponse(
            error=ErrorCode.INVALID_FILE_TYPE,
            message=f"Unsupported file type: {ext}",
            details={"supported_extensions": list(SUPPORTED_EXTENSIONS)},
        )

    # Check MIME type if available
    if file.content_type and file.content_type not in SUPPORTED_MIME_TYPES:
        # Allow if extension is valid (MIME type detection can be unreliable)
        logger.debug(
            "mime_type_mismatch",
            content_type=file.content_type,
            extension=ext,
        )

    return None


async def process_document(
    file_path: Path,
    file_name: str,
    options: ProcessingOptions,
) -> ProcessingResult:
    """Process a document through the IQA pipeline.

    Args:
        file_path: Path to the uploaded file.
        file_name: Original file name.
        options: Processing options.

    Returns:
        ProcessingResult with analysis data.
    """
    start_time = time.perf_counter()
    document_id = str(uuid.uuid4())

    # Initialize result containers
    pages: list[PageSummary] = []
    dqs: DQSSummary | None = None
    pdf_type: str | None = None
    ocr_recommendation: str | None = None

    try:
        # Import processing modules
        from image_preprocessing_detector.detection.iqa_classical import (
            BlurDetector,
            ContrastDetector,
            NoiseDetector,
        )
        from image_preprocessing_detector.ingestion.image_loader import ImageLoader
        from image_preprocessing_detector.metrics.dqs_calculator import (
            calculate_degradation_score,
            normalize_classical_iqa,
        )
        from image_preprocessing_detector.utils.device_probe import (
            get_recommended_device,
        )

        # Determine device
        device_used = get_recommended_device(
            prefer_gpu=options.prefer_gpu,
            allow_cpu_fallback=True,
        )

        # Load and process the document
        loader = ImageLoader()
        ext = Path(file_name).suffix.lower()

        # List to store (image_array, width, height) tuples
        page_data: list[tuple[Any, int, int]] = []

        if ext == ".pdf":
            # PDF processing
            from image_preprocessing_detector.classification.pdf_type_classifier import (
                classify_pdf_type,
            )
            from image_preprocessing_detector.ingestion.pdf_loader import PDFLoader

            pdf_loader = PDFLoader()

            # Classify PDF type
            pdf_type_result = classify_pdf_type(file_path)
            pdf_type = pdf_type_result.value if pdf_type_result else None

            # Load pages - PDFLoader.load() returns PageImage objects
            for page_obj in pdf_loader.load(file_path):
                page_data.append((page_obj.image, page_obj.width, page_obj.height))
                if len(page_data) >= 100:
                    break
        else:
            # Single image processing
            # ImageLoader.load() returns (np.ndarray, ImageMetadata)
            image_array, _metadata = loader.load(file_path)
            if image_array is not None:
                h, w = image_array.shape[:2]
                page_data.append((image_array, w, h))

        # Initialize detectors
        blur_detector = BlurDetector()
        noise_detector = NoiseDetector()
        contrast_detector = ContrastDetector()

        # Process each page
        total_degradation = 0.0
        for idx, (page_image, width, height) in enumerate(page_data):
            # Run IQA detectors
            blur_result = blur_detector.detect(page_image)
            noise_result = noise_detector.detect(page_image)
            contrast_result = contrast_detector.detect(page_image)

            # Calculate normalized scores
            iqa_metrics = normalize_classical_iqa(
                blur_result=blur_result,
                contrast_result=contrast_result,
                noise_result=noise_result,
            )

            # Calculate degradation
            degradation = calculate_degradation_score(iqa_metrics)
            total_degradation += degradation

            # Build IQA summary
            iqa_summary = IQAScoreSummary(
                blur_score=iqa_metrics.get("blur_score"),
                noise_score=iqa_metrics.get("noise_score"),
                contrast_score=iqa_metrics.get("contrast_score"),
            )

            # Count issues and corrections
            issues_count = sum(
                [
                    1 if blur_result.is_blurred else 0,
                    1 if noise_result.is_noisy else 0,
                    1 if contrast_result.is_low_contrast else 0,
                ]
            )

            # Build page summary (width/height already extracted from page_data)
            page_summary = PageSummary(
                page_index=idx,
                width_px=width,
                height_px=height,
                issues_detected=issues_count,
                corrections_applied=0,  # Corrections not applied in this pass
                iqa_scores=iqa_summary,
            )
            pages.append(page_summary)

        # Calculate DQS
        if pages:
            avg_degradation = total_degradation / len(pages)
            dqs = DQSSummary(
                degradation_score=avg_degradation,
                structural_complexity_score=0.3,  # Default for now
            )

            # Simple routing recommendation based on degradation
            if avg_degradation < 0.3:
                ocr_recommendation = "ocr_fast"
            elif avg_degradation < 0.6:
                ocr_recommendation = "ocr_advanced"
            else:
                ocr_recommendation = "vision_structured"

    except Exception as e:
        logger.exception("document_processing_failed", error=str(e))
        raise

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return ProcessingResult(
        document_id=document_id,
        file_name=file_name,
        num_pages=len(pages),
        pdf_type=pdf_type,
        dqs=dqs,
        ocr_routing_recommendation=ocr_recommendation,
        pages=pages,
        processing_time_ms=elapsed_ms,
        device_used=device_used,
    )


@router.post(
    "",
    response_model=ProcessResponse,
    summary="Process a single document",
    description="Upload and process a single PDF or image file for IQA analysis.",
    responses={
        200: {"description": "Document processed successfully"},
        400: {"description": "Invalid request (file type, size, etc.)"},
        422: {"description": "Processing failed"},
        500: {"description": "Internal server error"},
    },
)
async def process_single_document(
    file: UploadFile = File(..., description="Document to process (PDF or image)"),
    prefer_gpu: bool = True,
    enable_corrections: bool = True,
    enable_teacher: bool = False,
) -> ProcessResponse | JSONResponse:
    """Process a single document.

    Args:
        file: The uploaded document file.
        prefer_gpu: Whether to prefer GPU for processing.
        enable_corrections: Whether to apply automatic corrections.
        enable_teacher: Whether to enable teacher model inference.

    Returns:
        ProcessResponse with processing results.
    """
    settings = get_api_settings()
    correlation_id = get_correlation_id()

    logger.info(
        "process_request_received",
        filename=file.filename,
        content_type=file.content_type,
        prefer_gpu=prefer_gpu,
        correlation_id=correlation_id,
    )

    # Validate file
    validation_error = validate_file(file, settings.max_file_size_mb)
    if validation_error:
        validation_error.correlation_id = correlation_id
        logger.warning(
            "file_validation_failed",
            error=validation_error.error,
            message=validation_error.message,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ProcessResponse(
                status=ProcessingStatus.FAILED,
                error=validation_error,
            ).model_dump(),
        )

    # Create processing options
    options = ProcessingOptions(
        prefer_gpu=prefer_gpu,
        enable_corrections=enable_corrections,
        enable_teacher=enable_teacher,
    )

    # Save file to temp location and process
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(file.filename or "document").suffix,
        ) as tmp_file:
            # Read file content
            content = await file.read()

            # Check file size
            file_size_mb = len(content) / (1024 * 1024)
            if file_size_mb > settings.max_file_size_mb:
                error = ErrorResponse(
                    error=ErrorCode.FILE_TOO_LARGE,
                    message=f"File size {file_size_mb:.1f}MB exceeds limit of {settings.max_file_size_mb}MB",
                    correlation_id=correlation_id,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=ProcessResponse(
                        status=ProcessingStatus.FAILED,
                        error=error,
                    ).model_dump(),
                )

            # Check for empty file
            if len(content) == 0:
                error = ErrorResponse(
                    error=ErrorCode.EMPTY_FILE,
                    message="Uploaded file is empty",
                    correlation_id=correlation_id,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=ProcessResponse(
                        status=ProcessingStatus.FAILED,
                        error=error,
                    ).model_dump(),
                )

            # Write to temp file
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        # Process the document
        result = await process_document(
            file_path=tmp_path,
            file_name=file.filename or "document",
            options=options,
        )

        logger.info(
            "process_completed",
            document_id=result.document_id,
            num_pages=result.num_pages,
            processing_time_ms=result.processing_time_ms,
        )

        return ProcessResponse(
            status=ProcessingStatus.COMPLETED,
            result=result,
        )

    except Exception as e:
        logger.exception("process_failed", error=str(e))
        error = ErrorResponse(
            error=ErrorCode.PROCESSING_FAILED,
            message=f"Document processing failed: {e!s}",
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ProcessResponse(
                status=ProcessingStatus.FAILED,
                error=error,
            ).model_dump(),
        )

    finally:
        # Cleanup temp file
        try:
            if "tmp_path" in locals():
                tmp_path.unlink(missing_ok=True)
        except Exception as e:
            logger.debug("temp_file_cleanup_failed", error=str(e))
