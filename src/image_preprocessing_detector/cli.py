"""Command-line interface for Image Preprocessing Detector.

Provides commands for processing single files and batches of documents.
"""

import sys
from pathlib import Path
from typing import Any

import click

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.correction.corrections import (
    correct_skew,
    enhance_contrast,
    sharpen_image,
)
from image_preprocessing_detector.detection.iqa_classical import (
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
            click.echo(f"Error: Unsupported file format: {suffix}", err=True)
            sys.exit(1)

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
                        logger.info(
                            f"Applied skew correction: {skew_result.angle:.2f}°"
                        )

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
            if page_image is not None:
                builder.add_page(
                    page_number=page_idx,
                    page_data=page_image,
                    text_result=text_result,
                    skew_result=skew_result,
                    blur_result=blur_result,
                    contrast_result=contrast_result,
                    skew_correction=skew_correction,
                    contrast_correction=contrast_correction,
                    blur_correction=blur_correction,
                )
            elif img_metadata is not None:
                builder.add_page(
                    page_number=page_idx,
                    page_data=(image, img_metadata),
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

        click.echo(f"✓ Processing complete: {output}")
        logger.info("Processing complete", output=str(output))

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

                # Call process command logic (reuse the same code)
                from click.testing import CliRunner

                runner = CliRunner()
                result = runner.invoke(
                    process,
                    [
                        str(file_path),
                        "--output",
                        str(output_path),
                        "--blur-threshold",
                        str(blur_threshold),
                        "--skew-threshold",
                        str(skew_threshold),
                        "--contrast-threshold",
                        str(contrast_threshold),
                    ]
                    + (["--dry-run"] if dry_run else []),
                )

                if result.exit_code == 0:
                    success_count += 1
                    click.echo(f"  ✓ Success: {output_path.name}")
                else:
                    error_count += 1
                    click.echo(f"  ✗ Failed: {result.exception}", err=True)

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


if __name__ == "__main__":
    cli()
