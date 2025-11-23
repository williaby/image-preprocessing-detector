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

    # Determine document ID and file type
    doc_id = input_path.stem
    file_name = input_path.name
    suffix = input_path.suffix.lower()

    # Create metadata builder
    builder = MetadataBuilder(document_id=doc_id, file_name=file_name)

    # Load pages based on file type
    pages: list[Any]  # PageImage or tuple[np.ndarray, ImageMetadata]
    if suffix == ".pdf":
        # Phase 1B: Perform pre-flight analysis for DPI upscaling
        settings = Settings()
        analyzer = PDFDocumentAnalyzer(settings)
        preflight = analyzer.analyze(input_path)

        logger.info(
            "PDF pre-flight analysis complete",
            needs_upscaling=preflight.needs_upscaling,
            should_use_upscaled=preflight.should_use_upscaled,
            processing_time=f"{preflight.processing_time:.2f}s",
        )

        # Use upscaled version if available, otherwise original
        pdf_to_process = preflight.recommended_path or str(input_path)

        # Add upscaling metadata to builder if upscaling was performed
        if preflight.should_use_upscaled:
            builder.set_upscaling_metadata(preflight.upscaling_result)
            logger.info(f"Using upscaled PDF: {pdf_to_process}")
        else:
            logger.info("Using original PDF (upscaling not needed or disabled)")

        pages = load_pdf(pdf_to_process)
        logger.info(f"Loaded {len(pages)} pages from PDF")
    elif suffix in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}:
        img, img_meta = load_image(str(input_path))
        pages = [(img, img_meta)]
        logger.info("Loaded single image")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # Process each page
    for page_idx, page_data in enumerate(pages):
        page_image: PageImage | None
        img_metadata: ImageMetadata | None

        if isinstance(page_data, PageImage):
            # PDF page
            page_image = page_data
            image = page_image.image
            img_metadata = None
        else:
            # Direct image tuple
            image, img_metadata = page_data
            page_image = None

        logger.info(f"Processing page {page_idx + 1}/{len(pages)}")

        # Text detection gate
        text_result = detect_text(image)
        logger.debug(
            f"Text detection: has_text={text_result.has_text}, "
            f"confidence={text_result.confidence:.2f}"
        )

        # IQA detection
        skew_result = None
        blur_result = None
        contrast_result = None

        if text_result.has_text:
            # Only run IQA on text-heavy pages
            skew_result = detect_skew(image)
            blur_result = detect_blur(image)
            contrast_result = detect_contrast(image)

            logger.debug(
                f"IQA results: skew={skew_result.is_skewed}, "
                f"blur={blur_result.is_blurred}, "
                f"contrast={contrast_result.is_low_contrast}"
            )

        # Apply corrections (if not dry-run)
        skew_correction = None
        blur_correction = None
        contrast_correction = None

        if not dry_run and text_result.has_text:
            if (
                skew_result
                and skew_result.is_skewed
                and skew_result.confidence >= skew_threshold
            ):
                skew_correction = correct_skew(
                    image, skew_result.angle, skew_result.confidence
                )
                if skew_correction.applied:
                    image = skew_correction.corrected_image
                    logger.info(f"Applied skew correction: {skew_result.angle:.2f}°")

            if (
                contrast_result
                and contrast_result.is_low_contrast
                and contrast_result.confidence >= contrast_threshold
            ):
                contrast_correction = enhance_contrast(
                    image, contrast_result.score, contrast_result.severity
                )
                if contrast_correction.applied:
                    image = contrast_correction.corrected_image
                    logger.info("Applied contrast enhancement")

            if (
                blur_result
                and blur_result.is_blurred
                and blur_result.confidence >= blur_threshold
            ):
                blur_correction = sharpen_image(
                    image, blur_result.score, blur_result.severity
                )
                if blur_correction.applied:
                    image = blur_correction.corrected_image
                    logger.info("Applied sharpening")

        # Add page to metadata builder
        page_data_arg: PageImage | tuple[np.ndarray, ImageMetadata] | None = page_image
        if page_data_arg is None and img_metadata is not None:
            page_data_arg = (image, img_metadata)

        if page_data_arg is not None:
            builder.add_page(
                page_number=page_idx,
                page_data=page_data_arg,
                text_result=text_result,
                skew_result=skew_result,
                blur_result=blur_result,
                contrast_result=contrast_result,
                skew_correction=skew_correction,
                contrast_correction=contrast_correction,
                blur_correction=blur_correction,
            )

    # Build metadata and generate JSON
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
    import json

    import cv2

    try:
        # Load image
        image = cv2.imread(str(input_path))
        if image is None:
            click.echo(f"Error: Could not load image: {input_path}", err=True)
            sys.exit(1)

        # Create detector with custom thresholds
        detector = BlurDetector(
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
        )

        # Parse ROI if provided
        bbox = None
        if roi:
            parts = [x.strip() for x in roi.split(",")]
            if len(parts) != 4:
                click.echo("Error: Invalid ROI format: ROI must have 4 values", err=True)
                click.echo("Expected format: 'x,y,width,height'", err=True)
                sys.exit(1)
            try:
                bbox = tuple(int(x) for x in parts)
            except ValueError:
                click.echo("Error: Invalid ROI format: values must be integers", err=True)
                click.echo("Expected format: 'x,y,width,height'", err=True)
                sys.exit(1)

        # Run detection
        if bbox:
            result = detector.detect_roi(image, bbox)  # type: ignore[arg-type]
            click.echo(f"Analyzing ROI: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
        else:
            result = detector.detect(image, compute_detailed_metrics=detailed)

        # Prepare output
        output_data = {
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

        # Output results
        if json_output:
            with open(json_output, "w") as f:
                json.dump(output_data, f, indent=2)
            click.echo(f"Results saved to: {json_output}")
        else:
            # Pretty print results
            click.echo("\n" + "=" * 50)
            click.echo("BLUR DETECTION RESULTS")
            click.echo("=" * 50)
            click.echo(f"File: {input_path.name}")
            click.echo(f"Image size: {image.shape[1]}x{image.shape[0]}")
            click.echo("-" * 50)

            # Severity indicator
            severity_icons = {
                "low": "✓ SHARP",
                "medium": "~ SLIGHT BLUR",
                "high": "! BLURRED",
                "critical": "✗ SEVERELY BLURRED",
            }
            severity_display = severity_icons.get(result.severity.value, result.severity.value)
            click.echo(f"Status: {severity_display}")
            click.echo(f"Blurred: {'Yes' if result.is_blurred else 'No'}")
            click.echo(f"Severity: {result.severity.value.upper()}")
            click.echo("-" * 50)
            click.echo(f"Laplacian Variance: {result.score:.2f}")
            click.echo(f"Blur Score (0-1): {result.blur_score:.3f}")
            click.echo(f"Confidence: {result.confidence:.3f}")

            if detailed and result.metrics:
                click.echo("-" * 50)
                click.echo("DETAILED METRICS:")
                click.echo(f"  Local Variance Mean: {result.metrics.local_variance_mean:.2f}")
                click.echo(f"  Local Variance Std: {result.metrics.local_variance_std:.2f}")
                click.echo(f"  Edge Density: {result.metrics.edge_density:.4f}")

            click.echo("=" * 50)

            # Interpretation
            click.echo("\nInterpretation:")
            if result.blur_score >= 0.8:
                click.echo("  Image is very sharp with well-defined edges.")
            elif result.blur_score >= 0.5:
                click.echo("  Image has acceptable sharpness for most use cases.")
            elif result.blur_score >= 0.2:
                click.echo("  Image shows noticeable blur. Consider re-scanning or correction.")
            else:
                click.echo("  Image is heavily blurred. Re-acquisition recommended.")

    except Exception as e:
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
    import json

    import cv2

    try:
        # Load image
        image = cv2.imread(str(input_path))
        if image is None:
            click.echo(f"Error: Could not load image: {input_path}", err=True)
            sys.exit(1)

        # Create detector with custom thresholds
        detector = NoiseDetector(
            threshold_critical=threshold_critical,
            threshold_high=threshold_high,
            threshold_medium=threshold_medium,
            wavelet=wavelet,
        )

        # Parse ROI if provided
        bbox = None
        if roi:
            parts = [x.strip() for x in roi.split(",")]
            if len(parts) != 4:
                click.echo("Error: Invalid ROI format: ROI must have 4 values", err=True)
                click.echo("Expected format: 'x,y,width,height'", err=True)
                sys.exit(1)
            try:
                bbox = tuple(int(x) for x in parts)
            except ValueError:
                click.echo("Error: Invalid ROI format: values must be integers", err=True)
                click.echo("Expected format: 'x,y,width,height'", err=True)
                sys.exit(1)

        # Run detection
        if bbox:
            result = detector.detect_roi(image, bbox)  # type: ignore[arg-type]
            click.echo(f"Analyzing ROI: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
        else:
            result = detector.detect(image, compute_detailed_metrics=detailed)

        # Prepare output
        output_data = {
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

        # Output results
        if json_output:
            with open(json_output, "w") as f:
                json.dump(output_data, f, indent=2)
            click.echo(f"Results saved to: {json_output}")
        else:
            # Pretty print results
            click.echo("\n" + "=" * 50)
            click.echo("NOISE DETECTION RESULTS")
            click.echo("=" * 50)
            click.echo(f"File: {input_path.name}")
            click.echo(f"Image size: {image.shape[1]}x{image.shape[0]}")
            click.echo(f"Wavelet: {wavelet}")
            click.echo("-" * 50)

            # Severity indicator
            severity_icons = {
                "low": "✓ CLEAN",
                "medium": "~ SLIGHT NOISE",
                "high": "! NOISY",
                "critical": "✗ SEVERELY NOISY",
            }
            severity_display = severity_icons.get(result.severity.value, result.severity.value)
            click.echo(f"Status: {severity_display}")
            click.echo(f"Noisy: {'Yes' if result.is_noisy else 'No'}")
            click.echo(f"Severity: {result.severity.value.upper()}")
            click.echo("-" * 50)
            click.echo(f"Noise Sigma: {result.noise_sigma:.3f}")
            click.echo(f"Noise Score (0-1): {result.noise_score:.3f}")
            click.echo(f"Confidence: {result.confidence:.3f}")

            if detailed and result.metrics:
                click.echo("-" * 50)
                click.echo("DETAILED METRICS:")
                click.echo(f"  Wavelet Detail Energy: {result.metrics.wavelet_detail_energy:.4f}")
                click.echo(f"  SNR Estimate: {result.metrics.snr_estimate:.2f} dB")
                click.echo(f"  Noise Type Hint: {result.metrics.noise_type_hint}")

            click.echo("=" * 50)

            # Interpretation
            click.echo("\nInterpretation:")
            if result.noise_score >= 0.8:
                click.echo("  Image is very clean with minimal noise.")
            elif result.noise_score >= 0.5:
                click.echo("  Image has acceptable noise levels for most use cases.")
            elif result.noise_score >= 0.2:
                click.echo("  Image shows noticeable noise. Consider denoising.")
            else:
                click.echo("  Image is heavily affected by noise. Denoising recommended.")

    except Exception as e:
        logger.error("Noise check failed", error=str(e), exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
