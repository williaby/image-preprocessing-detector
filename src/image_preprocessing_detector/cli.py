"""Command-line interface for Image Preprocessing Detector.

Provides commands for processing single files and batches of documents.
"""

import sys
from pathlib import Path
from typing import Any

import click
import numpy as np

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.correction.corrections import (
    correct_skew,
    enhance_contrast,
    sharpen_image,
)
from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    NoiseDetector,
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import detect_text
from image_preprocessing_detector.ingestion.image_loader import (
    ImageMetadata,
    load_image,
)
from image_preprocessing_detector.ingestion.pdf_analyzer import PDFDocumentAnalyzer
from image_preprocessing_detector.ingestion.pdf_loader import PageImage, load_pdf
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
)
from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)

# Supported image file extensions
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}


def _parse_roi_string(roi: str | None) -> tuple[int, int, int, int] | None:
    """Parse ROI string to bbox tuple.

    Args:
        roi: ROI string in format 'x,y,width,height' or None

    Returns:
        Tuple of (x, y, width, height) or None if no ROI

    Raises:
        SystemExit: If ROI format is invalid
    """
    if not roi:
        return None

    parts = [x.strip() for x in roi.split(",")]
    if len(parts) != 4:
        click.echo("Error: Invalid ROI format: ROI must have 4 values", err=True)
        click.echo("Expected format: 'x,y,width,height'", err=True)
        sys.exit(1)
    try:
        return tuple(int(x) for x in parts)  # type: ignore[return-value]
    except ValueError:
        click.echo("Error: Invalid ROI format: values must be integers", err=True)
        click.echo("Expected format: 'x,y,width,height'", err=True)
        sys.exit(1)


def _load_image_for_check(input_path: Path) -> Any:
    """Load image for detection check commands.

    Args:
        input_path: Path to image file

    Returns:
        Loaded image array

    Raises:
        SystemExit: If image cannot be loaded
    """
    import cv2

    image = cv2.imread(str(input_path))
    if image is None:
        click.echo(f"Error: Could not load image: {input_path}", err=True)
        sys.exit(1)
    return image


def _output_check_result(
    output_data: dict[str, Any],
    json_output: Path | None,
    print_fn: Any,
) -> None:
    """Output detection check result as JSON or pretty print.

    Args:
        output_data: Result data dictionary
        json_output: Path to JSON output file or None for console output
        print_fn: Function to call for pretty printing (takes output_data)
    """
    import json

    if json_output:
        with open(json_output, "w") as f:
            json.dump(output_data, f, indent=2)
        click.echo(f"Results saved to: {json_output}")
    else:
        print_fn(output_data)


def _print_blur_results(output_data: dict[str, Any]) -> None:
    """Pretty print blur detection results."""
    click.echo("\n" + "=" * 50)
    click.echo("BLUR DETECTION RESULTS")
    click.echo("=" * 50)
    click.echo(f"File: {Path(output_data['file']).name}")
    click.echo("-" * 50)

    severity_icons = {
        "low": "✓ SHARP",
        "medium": "~ SLIGHT BLUR",
        "high": "! BLURRED",
        "critical": "✗ SEVERELY BLURRED",
    }
    severity_display = severity_icons.get(
        output_data["severity"], output_data["severity"]
    )
    click.echo(f"Status: {severity_display}")
    click.echo(f"Blurred: {'Yes' if output_data['is_blurred'] else 'No'}")
    click.echo(f"Severity: {output_data['severity'].upper()}")
    click.echo("-" * 50)
    click.echo(f"Laplacian Variance: {output_data['laplacian_variance']:.2f}")
    click.echo(f"Blur Score (0-1): {output_data['blur_score']:.3f}")
    click.echo(f"Confidence: {output_data['confidence']:.3f}")

    if "metrics" in output_data:
        click.echo("-" * 50)
        click.echo("DETAILED METRICS:")
        metrics = output_data["metrics"]
        click.echo(f"  Local Variance Mean: {metrics['local_variance_mean']:.2f}")
        click.echo(f"  Local Variance Std: {metrics['local_variance_std']:.2f}")
        click.echo(f"  Edge Density: {metrics['edge_density']:.4f}")

    click.echo("=" * 50)
    click.echo("\nInterpretation:")
    blur_score = output_data["blur_score"]
    if blur_score >= 0.8:
        click.echo("  Image is very sharp with well-defined edges.")
    elif blur_score >= 0.5:
        click.echo("  Image has acceptable sharpness for most use cases.")
    elif blur_score >= 0.2:
        click.echo("  Image shows noticeable blur. Consider re-scanning or correction.")
    else:
        click.echo("  Image is heavily blurred. Re-acquisition recommended.")


def _print_noise_results(output_data: dict[str, Any], wavelet: str) -> None:
    """Pretty print noise detection results."""
    click.echo("\n" + "=" * 50)
    click.echo("NOISE DETECTION RESULTS")
    click.echo("=" * 50)
    click.echo(f"File: {Path(output_data['file']).name}")
    click.echo(f"Wavelet: {wavelet}")
    click.echo("-" * 50)

    severity_icons = {
        "low": "✓ CLEAN",
        "medium": "~ SLIGHT NOISE",
        "high": "! NOISY",
        "critical": "✗ SEVERELY NOISY",
    }
    severity_display = severity_icons.get(
        output_data["severity"], output_data["severity"]
    )
    click.echo(f"Status: {severity_display}")
    click.echo(f"Noisy: {'Yes' if output_data['is_noisy'] else 'No'}")
    click.echo(f"Severity: {output_data['severity'].upper()}")
    click.echo("-" * 50)
    click.echo(f"Noise Sigma: {output_data['noise_sigma']:.3f}")
    click.echo(f"Noise Score (0-1): {output_data['noise_score']:.3f}")
    click.echo(f"Confidence: {output_data['confidence']:.3f}")

    if "metrics" in output_data:
        click.echo("-" * 50)
        click.echo("DETAILED METRICS:")
        metrics = output_data["metrics"]
        click.echo(f"  Wavelet Detail Energy: {metrics['wavelet_detail_energy']:.4f}")
        click.echo(f"  SNR Estimate: {metrics['snr_estimate_db']:.2f} dB")
        click.echo(f"  Noise Type Hint: {metrics['noise_type_hint']}")

    click.echo("=" * 50)
    click.echo("\nInterpretation:")
    noise_score = output_data["noise_score"]
    if noise_score >= 0.8:
        click.echo("  Image is very clean with minimal noise.")
    elif noise_score >= 0.5:
        click.echo("  Image has acceptable noise levels for most use cases.")
    elif noise_score >= 0.2:
        click.echo("  Image shows noticeable noise. Consider denoising.")
    else:
        click.echo("  Image is heavily affected by noise. Denoising recommended.")


def _load_pdf_with_preflight(
    input_path: Path, builder: MetadataBuilder
) -> list[PageImage]:
    """Load PDF with pre-flight analysis for DPI upscaling."""
    settings = Settings()
    analyzer = PDFDocumentAnalyzer(settings)
    preflight = analyzer.analyze(input_path)

    logger.info(
        "PDF pre-flight analysis complete",
        needs_upscaling=preflight.needs_upscaling,
        should_use_upscaled=preflight.should_use_upscaled,
        processing_time=f"{preflight.processing_time:.2f}s",
    )

    pdf_to_process = preflight.recommended_path or str(input_path)

    if preflight.should_use_upscaled:
        builder.set_upscaling_metadata(preflight.upscaling_result)
        logger.info(f"Using upscaled PDF: {pdf_to_process}")
    else:
        logger.info("Using original PDF (upscaling not needed or disabled)")

    pages = load_pdf(pdf_to_process)
    logger.info(f"Loaded {len(pages)} pages from PDF")
    return pages


def _load_document_pages(input_path: Path, builder: MetadataBuilder) -> list[Any]:
    """Load document pages based on file type."""
    suffix = input_path.suffix.lower()

    if suffix == ".pdf":
        return _load_pdf_with_preflight(input_path, builder)

    if suffix in _IMAGE_EXTENSIONS:
        img, img_meta = load_image(str(input_path))
        logger.info("Loaded single image")
        return [(img, img_meta)]

    raise ValueError(f"Unsupported file format: {suffix}")


def _run_iqa_detection(image: np.ndarray, has_text: bool) -> tuple[Any, Any, Any]:
    """Run IQA detection if page has text.

    Returns:
        Tuple of (skew_result, blur_result, contrast_result), all None if no text.
    """
    if not has_text:
        return None, None, None

    skew_result = detect_skew(image)
    blur_result = detect_blur(image)
    contrast_result = detect_contrast(image)

    logger.debug(
        f"IQA results: skew={skew_result.is_skewed}, "
        f"blur={blur_result.is_blurred}, "
        f"contrast={contrast_result.is_low_contrast}"
    )

    return skew_result, blur_result, contrast_result


def _apply_skew_correction(
    image: np.ndarray, skew_result: Any, threshold: float
) -> tuple[np.ndarray, Any]:
    """Apply skew correction if needed."""
    if not (skew_result and skew_result.is_skewed):
        return image, None
    if skew_result.confidence < threshold:
        return image, None

    correction = correct_skew(image, skew_result.angle, skew_result.confidence)
    if correction.applied:
        logger.info(f"Applied skew correction: {skew_result.angle:.2f}°")
        return correction.corrected_image, correction
    return image, None


def _apply_contrast_correction(
    image: np.ndarray, contrast_result: Any, threshold: float
) -> tuple[np.ndarray, Any]:
    """Apply contrast correction if needed."""
    if not (contrast_result and contrast_result.is_low_contrast):
        return image, None
    if contrast_result.confidence < threshold:
        return image, None

    correction = enhance_contrast(
        image, contrast_result.score, contrast_result.severity
    )
    if correction.applied:
        logger.info("Applied contrast enhancement")
        return correction.corrected_image, correction
    return image, None


def _apply_blur_correction(
    image: np.ndarray, blur_result: Any, threshold: float
) -> tuple[np.ndarray, Any]:
    """Apply blur correction (sharpening) if needed."""
    if not (blur_result and blur_result.is_blurred):
        return image, None
    if blur_result.confidence < threshold:
        return image, None

    correction = sharpen_image(image, blur_result.score, blur_result.severity)
    if correction.applied:
        logger.info("Applied sharpening")
        return correction.corrected_image, correction
    return image, None


def _apply_all_corrections(
    image: np.ndarray,
    skew_result: Any,
    blur_result: Any,
    contrast_result: Any,
    skew_threshold: float,
    blur_threshold: float,
    contrast_threshold: float,
) -> tuple[np.ndarray, Any, Any, Any]:
    """Apply all corrections and return corrected image with correction results."""
    image, skew_correction = _apply_skew_correction(image, skew_result, skew_threshold)
    image, contrast_correction = _apply_contrast_correction(
        image, contrast_result, contrast_threshold
    )
    image, blur_correction = _apply_blur_correction(image, blur_result, blur_threshold)
    return image, skew_correction, contrast_correction, blur_correction


def _extract_page_image_data(
    page_data: Any,
) -> tuple[np.ndarray, PageImage | None, ImageMetadata | None]:
    """Extract image and metadata from page data."""
    if isinstance(page_data, PageImage):
        return page_data.image, page_data, None
    # Direct image tuple
    image, img_metadata = page_data
    return image, None, img_metadata


def process_single_file(
    input_path: Path,
    output: Path,
    dry_run: bool,
    blur_threshold: float,
    skew_threshold: float,
    contrast_threshold: float,
) -> None:
    """Process a single file with image preprocessing detection.

    Args:
        input_path: Path to input PDF or image file
        output: Path to output JSON file
        dry_run: If True, skip corrections (detection only)
        blur_threshold: Blur detection threshold (0.0-1.0)
        skew_threshold: Skew detection threshold (0.0-1.0)
        contrast_threshold: Contrast detection threshold (0.0-1.0)

    Raises:
        ValueError: If file format is unsupported
        Exception: If processing fails
    """
    logger.info(
        "Processing file",
        input_path=str(input_path),
        output=str(output),
        dry_run=dry_run,
    )

    doc_id = input_path.stem
    file_name = input_path.name
    builder = MetadataBuilder(document_id=doc_id, file_name=file_name)
    pages = _load_document_pages(input_path, builder)

    for page_idx, page_data in enumerate(pages):
        logger.info(f"Processing page {page_idx + 1}/{len(pages)}")

        image, page_image, img_metadata = _extract_page_image_data(page_data)
        text_result = detect_text(image)
        logger.debug(
            f"Text detection: has_text={text_result.has_text}, "
            f"confidence={text_result.confidence:.2f}"
        )

        skew_result, blur_result, contrast_result = _run_iqa_detection(
            image, text_result.has_text
        )

        skew_correction = blur_correction = contrast_correction = None
        if not dry_run and text_result.has_text:
            image, skew_correction, contrast_correction, blur_correction = (
                _apply_all_corrections(
                    image,
                    skew_result,
                    blur_result,
                    contrast_result,
                    skew_threshold,
                    blur_threshold,
                    contrast_threshold,
                )
            )

        page_data_arg: PageImage | tuple[np.ndarray, ImageMetadata] | None = page_image
        if page_data_arg is None and img_metadata is not None:
            page_data_arg = (image, img_metadata)

        if page_data_arg is not None:
            builder.add_page(
                page_number=page_idx,
                page_data=page_data_arg,
                _text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
                skew_correction=skew_correction,
                contrast_correction=contrast_correction,
                blur_correction=blur_correction,
            )

    metadata = builder.build()
    generate_json(metadata, output)
    logger.info("Processing complete", output=str(output))


@click.group()
@click.version_option(version="1.0.0", prog_name="imgprep")
def cli() -> None:
    """Image Preprocessing Detector - Detect and correct image quality issues."""


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output JSON file path",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Detection only (skip corrections)",
)
@click.option(
    "--blur-threshold",
    type=float,
    default=0.8,
    help="Blur detection threshold (0.0-1.0)",
)
@click.option(
    "--skew-threshold",
    type=float,
    default=0.7,
    help="Skew detection threshold (0.0-1.0)",
)
@click.option(
    "--contrast-threshold",
    type=float,
    default=0.7,
    help="Contrast detection threshold (0.0-1.0)",
)
def process(
    input_path: Path,
    output: Path,
    dry_run: bool,
    blur_threshold: float,
    skew_threshold: float,
    contrast_threshold: float,
) -> None:
    """Process a single PDF or image file.

    Examples:
        imgprep process input.pdf --output result.json
        imgprep process image.jpg --output result.json --dry-run
    """
    try:
        process_single_file(
            input_path=input_path,
            output=output,
            dry_run=dry_run,
            blur_threshold=blur_threshold,
            skew_threshold=skew_threshold,
            contrast_threshold=contrast_threshold,
        )
        click.echo(f"✓ Processing complete: {output}")

    except Exception as e:
        # CLI entry point: catch all exceptions to provide user-friendly error message
        logger.error("Processing failed", error=str(e), exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output directory for JSON files",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Detection only (skip corrections)",
)
@click.option(
    "--blur-threshold",
    type=float,
    default=0.8,
    help="Blur detection threshold (0.0-1.0)",
)
@click.option(
    "--skew-threshold",
    type=float,
    default=0.7,
    help="Skew detection threshold (0.0-1.0)",
)
@click.option(
    "--contrast-threshold",
    type=float,
    default=0.7,
    help="Contrast detection threshold (0.0-1.0)",
)
def batch(
    input_dir: Path,
    output_dir: Path,
    dry_run: bool,
    blur_threshold: float,
    skew_threshold: float,
    contrast_threshold: float,
) -> None:
    """Process a directory of PDF and image files.

    Examples:
        imgprep batch input_dir/ --output-dir results/
        imgprep batch docs/ --output-dir output/ --dry-run
    """
    try:
        logger.info(
            "Batch processing",
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            dry_run=dry_run,
        )

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all supported files
        supported_extensions = {
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".tiff",
            ".tif",
            ".bmp",
            ".webp",
        }
        files = [
            f
            for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        if not files:
            click.echo(f"No supported files found in {input_dir}", err=True)
            sys.exit(1)

        click.echo(f"Found {len(files)} files to process")

        # Process each file
        success_count = 0
        error_count = 0

        for file_idx, file_path in enumerate(files, 1):
            try:
                output_path = output_dir / f"{file_path.stem}.json"

                click.echo(f"[{file_idx}/{len(files)}] Processing {file_path.name}...")

                # Process the file using shared logic
                process_single_file(
                    input_path=file_path,
                    output=output_path,
                    dry_run=dry_run,
                    blur_threshold=blur_threshold,
                    skew_threshold=skew_threshold,
                    contrast_threshold=contrast_threshold,
                )

                success_count += 1
                click.echo(f"  ✓ Success: {output_path.name}")

            except Exception as e:
                # Per-file handler: continue processing other files on error
                error_count += 1
                logger.exception("Failed to process file: %s", file_path)
                click.echo(f"  ✗ Error: {e}", err=True)

        # Summary
        click.echo("\nBatch processing complete:")
        click.echo(f"  ✓ Successful: {success_count}")
        click.echo(f"  ✗ Failed: {error_count}")
        click.echo(f"  Total: {len(files)}")

        if error_count > 0:
            sys.exit(1)

    except Exception as e:
        # CLI entry point: catch all exceptions to provide user-friendly error message
        logger.error("Batch processing failed", error=str(e), exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("blur-check")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--threshold-critical",
    type=float,
    default=50.0,
    help="Critical blur threshold (variance < 50 = severe blur)",
)
@click.option(
    "--threshold-high",
    type=float,
    default=100.0,
    help="High blur threshold (variance < 100 = noticeable blur)",
)
@click.option(
    "--threshold-medium",
    type=float,
    default=200.0,
    help="Medium blur threshold (variance < 200 = slight blur)",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed blur metrics (local variance, edge density)",
)
@click.option(
    "--json-output",
    "-j",
    type=click.Path(path_type=Path),
    help="Output results to JSON file",
)
@click.option(
    "--roi",
    type=str,
    help="Region of interest as 'x,y,width,height' (COCO format)",
)
def blur_check(
    input_path: Path,
    threshold_critical: float,
    threshold_high: float,
    threshold_medium: float,
    detailed: bool,
    json_output: Path | None,
    roi: str | None,
) -> None:
    """Check blur levels in an image using Laplacian variance.

    Analyzes image sharpness and provides blur severity assessment.
    Higher variance values indicate sharper images.

    Examples:
        imgprep blur-check image.jpg
        imgprep blur-check scan.png --detailed
        imgprep blur-check photo.jpg --roi "100,100,200,200"
        imgprep blur-check document.jpg --json-output result.json
    """
    try:
        # Load image using helper
        image = _load_image_for_check(input_path)

        # Create detector with custom thresholds
        detector = BlurDetector(
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

        # Parse ROI using helper
        bbox = _parse_roi_string(roi)

        # Run detection
        if bbox:
            result = detector.detect_roi(image, bbox)
            click.echo(
                f"Analyzing ROI: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}"
            )
        else:
            result = detector.detect(image, compute_detailed_metrics=detailed)

        # Prepare output data
        output_data: dict[str, Any] = {
            "file": str(input_path),
            "is_blurred": result.is_blurred,
            "severity": result.severity.value,
            "laplacian_variance": round(result.score, 2),
            "blur_score": round(result.blur_score, 3),
            "confidence": round(result.confidence, 3),
        }

        if detailed and result.metrics:
            output_data["metrics"] = {
                "local_variance_mean": round(result.metrics.local_variance_mean, 2),
                "local_variance_std": round(result.metrics.local_variance_std, 2),
                "edge_density": round(result.metrics.edge_density, 4),
            }

        if roi:
            output_data["roi"] = bbox

        # Output results using helper
        _output_check_result(output_data, json_output, _print_blur_results)

    except Exception as e:
        # CLI entry point: catch all exceptions to provide user-friendly error message
        logger.error("Blur check failed", error=str(e), exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("noise-check")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--threshold-critical",
    type=float,
    default=20.0,
    help="Critical noise threshold (sigma > 20 = severe noise)",
)
@click.option(
    "--threshold-high",
    type=float,
    default=12.0,
    help="High noise threshold (sigma > 12 = noticeable noise)",
)
@click.option(
    "--threshold-medium",
    type=float,
    default=5.0,
    help="Medium noise threshold (sigma > 5 = slight noise)",
)
@click.option(
    "--wavelet",
    type=click.Choice(["db1", "db2", "haar", "sym2", "sym4"]),
    default="db1",
    help="Wavelet family to use for decomposition",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed noise metrics (SNR, noise type)",
)
@click.option(
    "--json-output",
    "-j",
    type=click.Path(path_type=Path),
    help="Output results to JSON file",
)
@click.option(
    "--roi",
    type=str,
    help="Region of interest as 'x,y,width,height' (COCO format)",
)
def noise_check(
    input_path: Path,
    threshold_critical: float,
    threshold_high: float,
    threshold_medium: float,
    wavelet: str,
    detailed: bool,
    json_output: Path | None,
    roi: str | None,
) -> None:
    """Check noise levels in an image using wavelet-based MAD estimation.

    Analyzes image noise using discrete wavelet transform and Median
    Absolute Deviation (MAD) to estimate noise standard deviation.

    Examples:
        imgprep noise-check image.jpg
        imgprep noise-check scan.png --detailed
        imgprep noise-check photo.jpg --wavelet haar
        imgprep noise-check document.jpg --json-output result.json
    """
    try:
        # Load image using helper
        image = _load_image_for_check(input_path)

        # Create detector with custom thresholds
        detector = NoiseDetector(
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
            wavelet=wavelet,
        )

        # Parse ROI using helper
        bbox = _parse_roi_string(roi)

        # Run detection
        if bbox:
            result = detector.detect_roi(image, bbox)
            click.echo(
                f"Analyzing ROI: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}"
            )
        else:
            result = detector.detect(image, compute_detailed_metrics=detailed)

        # Prepare output data
        output_data: dict[str, Any] = {
            "file": str(input_path),
            "is_noisy": result.is_noisy,
            "severity": result.severity.value,
            "noise_sigma": round(result.noise_sigma, 3),
            "noise_score": round(result.noise_score, 3),
            "confidence": round(result.confidence, 3),
        }

        if detailed and result.metrics:
            output_data["metrics"] = {
                "wavelet_detail_energy": round(result.metrics.wavelet_detail_energy, 4),
                "snr_estimate_db": round(result.metrics.snr_estimate, 2),
                "noise_type_hint": result.metrics.noise_type_hint,
            }

        if roi:
            output_data["roi"] = bbox

        # Output results using helper (pass wavelet to print function via lambda)
        _output_check_result(
            output_data,
            json_output,
            lambda data: _print_noise_results(data, wavelet),
        )

    except Exception as e:
        # CLI entry point: catch all exceptions to provide user-friendly error message
        logger.error("Noise check failed", error=str(e), exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Register deskew command
@cli.command("deskew")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON file path (default: stdout)",
)
@click.option(
    "--save-image",
    type=click.Path(path_type=Path),
    default=None,
    help="Save corrected image to this path",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to skew_estimation.yaml config",
)
@click.option(
    "--classical-only",
    is_flag=True,
    help="Force classical Hough+Projection detection (skip ML)",
)
def deskew_cmd(
    input_path: Path,
    output: Path | None,
    save_image: Path | None,
    config: Path | None,
    classical_only: bool,
) -> None:
    """Detect and correct skew in a document image.

    Runs the ML-based SkewNet pipeline (orientation + fine skew) with
    classical fallback. Reports detected angles, confidence, and
    whether correction was applied.

    Examples:
        imgprep deskew scan.png
        imgprep deskew scan.png --save-image corrected.png -o result.json
        imgprep deskew scan.png --classical-only
    """
    import json

    import cv2

    from image_preprocessing_detector.detection.deskew_pipeline import (
        DeskewConfig,
        DeskewPipeline,
    )

    try:
        image = cv2.imread(str(input_path))
        if image is None:
            click.echo(f"Error: Could not read image: {input_path}", err=True)
            sys.exit(1)

        if classical_only:
            pipeline_config = DeskewConfig(
                model_path=None,
                fallback_enabled=True,
            )
        else:
            pipeline_config = (
                DeskewConfig.from_yaml(config) if config else DeskewConfig()
            )

        pipeline = DeskewPipeline(config=pipeline_config)
        result = pipeline.process(image)

        # Build result dict
        result_data = {
            "input": str(input_path),
            "orientation_angle": result.orientation_angle,
            "orientation_confidence": round(result.orientation_confidence, 4),
            "orientation_corrected": result.orientation_applied,
            "skew_angle": round(result.skew_angle, 4),
            "skew_confidence": round(result.skew_confidence, 4),
            "skew_uncertainty": round(result.skew_uncertainty, 4),
            "correction_applied": result.correction_applied,
            "method": result.method,
            "latency_ms": result.latency_ms,
        }
        if result.skipped_reason:
            result_data["skipped_reason"] = result.skipped_reason

        # Output
        json_str = json.dumps(result_data, indent=2)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json_str)
            click.echo(f"Result saved to {output}")
        else:
            click.echo(json_str)

        # Save corrected image
        if save_image and result.correction_applied:
            save_image.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(save_image), result.corrected_image)
            click.echo(f"Corrected image saved to {save_image}")

        pipeline.close()

    except Exception as e:
        logger.error("Deskew failed", error=str(e), exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Register layout taxonomy command group
try:
    from image_preprocessing_detector.cli_layout import layout

    cli.add_command(layout)
except ImportError:
    # Layout taxonomy module not available
    pass

# Register synthetic generation command group
try:
    from image_preprocessing_detector.synthetic.cli import synthetic

    cli.add_command(synthetic)
except ImportError:
    # Synthetic module not available (missing optional dependencies)
    pass


if __name__ == "__main__":
    cli()
