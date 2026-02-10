#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Convert datasets with non-standard formats to images for annotation pipeline.

Handles:
1. Yarmouk OCR: Convert scanned PDF documents to PNG images
2. CC-OCR: Extract base64-encoded images from TSV files
3. OHR-Bench: Convert benchmark PDF documents to PNG images
4. FinanceBench: Convert SEC filing PDFs to PNG images

Usage:
    python scripts/convert_datasets_to_images.py --dataset yarmouk
    python scripts/convert_datasets_to_images.py --dataset cc-ocr
    python scripts/convert_datasets_to_images.py --dataset ohr-bench
    python scripts/convert_datasets_to_images.py --dataset financebench
    python scripts/convert_datasets_to_images.py --all
"""

from __future__ import annotations

import argparse
import base64
import csv
import logging
import sys
from pathlib import Path

# Increase CSV field size limit for base64-encoded images
csv.field_size_limit(sys.maxsize)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default paths
BASE_DATA_PATH = Path("/mnt/e/image_detection/01_base_data")
BENCHMARK_PATH = Path("/mnt/e/image_detection/02_benchmark_only")
YARMOUK_PATH = BASE_DATA_PATH / "language/yarmouk_ocr"
CC_OCR_PATH = BASE_DATA_PATH / "language/huggingface_downloads/CC-OCR"
OHR_BENCH_PATH = BENCHMARK_PATH / "ohr-bench"
FINANCEBENCH_PATH = BENCHMARK_PATH / "financebench"


def convert_yarmouk_pdfs(
    input_path: Path = YARMOUK_PATH,
    output_subdir: str = "extracted_images",
    target_dpi: int = 300,
    dry_run: bool = False,
) -> dict[str, int]:
    """Convert Yarmouk OCR PDF files to PNG images.

    Args:
        input_path: Root path of Yarmouk OCR dataset
        output_subdir: Subdirectory name for extracted images
        target_dpi: Target DPI for rendering (default: 300)
        dry_run: If True, only count files without converting

    Returns:
        Dictionary with conversion statistics
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        return {"error": "missing_dependency"}

    stats = {"found": 0, "converted": 0, "skipped": 0, "errors": 0}

    # Find all PDF files
    pdf_files = list(input_path.rglob("*.pdf"))
    stats["found"] = len(pdf_files)

    if dry_run:
        logger.info(f"[DRY RUN] Found {len(pdf_files)} PDF files to convert")
        return stats

    logger.info(f"Converting {len(pdf_files)} PDF files from Yarmouk OCR...")

    for pdf_path in pdf_files:
        try:
            # Create output directory mirroring input structure
            rel_path = pdf_path.relative_to(input_path)
            output_dir = input_path / output_subdir / rel_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Output filename (replace .pdf with .png)
            output_path = output_dir / f"{pdf_path.stem}.png"

            # Skip if already converted
            if output_path.exists():
                stats["skipped"] += 1
                continue

            # Open PDF and render first page
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                logger.warning(f"Empty PDF: {pdf_path}")
                stats["errors"] += 1
                continue

            # Render page at target DPI
            page = doc[0]
            # Calculate zoom factor for target DPI (default PDF is 72 DPI)
            zoom = target_dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Save as PNG
            pix.save(str(output_path))
            doc.close()

            stats["converted"] += 1

            if stats["converted"] % 500 == 0:
                logger.info(f"Converted {stats['converted']}/{stats['found']} files...")

        except Exception as e:
            logger.error(f"Error converting {pdf_path}: {e}")
            stats["errors"] += 1

    logger.info(
        f"Yarmouk conversion complete: "
        f"{stats['converted']} converted, "
        f"{stats['skipped']} skipped, "
        f"{stats['errors']} errors"
    )
    return stats


def extract_ccor_images(
    input_path: Path = CC_OCR_PATH,
    output_subdir: str = "extracted_images",
    dry_run: bool = False,
) -> dict[str, int]:
    """Extract base64-encoded images from CC-OCR TSV files.

    Args:
        input_path: Root path of CC-OCR dataset
        output_subdir: Subdirectory name for extracted images
        dry_run: If True, only count records without extracting

    Returns:
        Dictionary with extraction statistics
    """
    stats = {"found": 0, "extracted": 0, "skipped": 0, "errors": 0}

    # Find all TSV files
    tsv_files = list(input_path.rglob("*.tsv"))
    logger.info(f"Found {len(tsv_files)} TSV files in CC-OCR")

    if dry_run:
        # Count records in each file
        for tsv_path in tsv_files:
            try:
                with open(tsv_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for _ in reader:
                        stats["found"] += 1
            except Exception as e:
                logger.error(f"Error reading {tsv_path}: {e}")
        logger.info(f"[DRY RUN] Found {stats['found']} images to extract")
        return stats

    for tsv_path in tsv_files:
        try:
            # Create output directory based on TSV location
            rel_path = tsv_path.relative_to(input_path)
            output_dir = input_path / output_subdir / rel_path.parent / tsv_path.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            with open(tsv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")

                for row in reader:
                    stats["found"] += 1

                    try:
                        # Get image data and name
                        image_b64 = row.get("image", "")
                        image_name = row.get("image_name", f"image_{stats['found']}")
                        index = row.get("index", stats["found"])

                        if not image_b64:
                            logger.warning(f"No image data for index {index}")
                            stats["errors"] += 1
                            continue

                        # Determine output filename
                        # Clean image_name if it has path components
                        clean_name = (
                            Path(image_name).name if image_name else f"{index}.jpg"
                        )
                        if not clean_name.lower().endswith((".jpg", ".jpeg", ".png")):
                            clean_name = f"{clean_name}.jpg"

                        output_path = output_dir / clean_name

                        # Skip if already extracted
                        if output_path.exists():
                            stats["skipped"] += 1
                            continue

                        # Decode and save image
                        image_data = base64.b64decode(image_b64)
                        with open(output_path, "wb") as img_file:
                            img_file.write(image_data)

                        stats["extracted"] += 1

                        if stats["extracted"] % 1000 == 0:
                            logger.info(
                                f"Extracted {stats['extracted']}/{stats['found']} images..."
                            )

                    except Exception as e:
                        logger.error(f"Error extracting image at index {index}: {e}")
                        stats["errors"] += 1

        except Exception as e:
            logger.error(f"Error processing {tsv_path}: {e}")
            stats["errors"] += 1

    logger.info(
        f"CC-OCR extraction complete: "
        f"{stats['extracted']} extracted, "
        f"{stats['skipped']} skipped, "
        f"{stats['errors']} errors"
    )
    return stats


def convert_ohr_bench_pdfs(
    input_path: Path = OHR_BENCH_PATH,
    output_subdir: str = "extracted_images",
    target_dpi: int = 300,
    dry_run: bool = False,
) -> dict[str, int]:
    """Convert OHR-Bench PDF files to PNG images.

    OHR-Bench contains PDFs across 7 categories:
    - academic, administration, finance, law, manual, news, textbook

    Args:
        input_path: Root path of OHR-Bench dataset
        output_subdir: Subdirectory name for extracted images
        target_dpi: Target DPI for rendering (default: 300)
        dry_run: If True, only count files without converting

    Returns:
        Dictionary with conversion statistics
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        return {"error": "missing_dependency"}

    stats = {"found": 0, "converted": 0, "skipped": 0, "errors": 0, "pages": 0}

    # PDFs are in the pdfs/ subdirectory
    pdfs_path = input_path / "pdfs"
    if not pdfs_path.exists():
        logger.error(f"OHR-Bench pdfs directory not found at {pdfs_path}")
        return {"error": "path_not_found"}

    # Find all PDF files
    pdf_files = list(pdfs_path.rglob("*.pdf"))
    stats["found"] = len(pdf_files)

    if dry_run:
        # Count total pages
        for pdf_path in pdf_files:
            try:
                doc = fitz.open(pdf_path)
                stats["pages"] += len(doc)
                doc.close()
            except Exception as e:
                logger.warning(f"Error counting pages in {pdf_path}: {e}")
        logger.info(
            f"[DRY RUN] Found {len(pdf_files)} PDF files "
            f"with {stats['pages']} total pages to convert"
        )
        return stats

    logger.info(f"Converting {len(pdf_files)} PDF files from OHR-Bench...")

    for pdf_path in pdf_files:
        try:
            # Create output directory mirroring input structure
            rel_path = pdf_path.relative_to(pdfs_path)
            output_dir = input_path / output_subdir / rel_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Open PDF
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                logger.warning(f"Empty PDF: {pdf_path}")
                stats["errors"] += 1
                continue

            # Convert each page
            for page_num in range(len(doc)):
                # Output filename includes page number for multi-page PDFs
                if len(doc) == 1:
                    output_path = output_dir / f"{pdf_path.stem}.png"
                else:
                    output_path = (
                        output_dir / f"{pdf_path.stem}_p{page_num + 1:03d}.png"
                    )

                # Skip if already converted
                if output_path.exists():
                    stats["skipped"] += 1
                    continue

                # Render page at target DPI
                page = doc[page_num]
                zoom = target_dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                # Save as PNG
                pix.save(str(output_path))
                stats["pages"] += 1

            doc.close()
            stats["converted"] += 1

            if stats["converted"] % 100 == 0:
                logger.info(
                    f"Converted {stats['converted']}/{stats['found']} PDFs "
                    f"({stats['pages']} pages)..."
                )

        except Exception as e:
            logger.error(f"Error converting {pdf_path}: {e}")
            stats["errors"] += 1

    logger.info(
        f"OHR-Bench conversion complete: "
        f"{stats['converted']} PDFs converted ({stats['pages']} pages), "
        f"{stats['skipped']} pages skipped, "
        f"{stats['errors']} errors"
    )
    return stats


def convert_financebench_pdfs(
    input_path: Path = FINANCEBENCH_PATH,
    output_subdir: str = "extracted_images",
    target_dpi: int = 300,
    dry_run: bool = False,
) -> dict[str, int]:
    """Convert FinanceBench SEC filing PDFs to PNG images.

    FinanceBench contains 368 PDFs (10K, 10Q, 8K, Earnings reports)
    from publicly traded companies for financial Q&A benchmarking.

    Args:
        input_path: Root path of FinanceBench dataset
        output_subdir: Subdirectory name for extracted images
        target_dpi: Target DPI for rendering (default: 300)
        dry_run: If True, only count files without converting

    Returns:
        Dictionary with conversion statistics
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        return {"error": "missing_dependency"}

    stats = {"found": 0, "converted": 0, "skipped": 0, "errors": 0, "pages": 0}

    # PDFs are in the pdfs/ subdirectory
    pdfs_path = input_path / "pdfs"
    if not pdfs_path.exists():
        logger.error(f"FinanceBench pdfs directory not found at {pdfs_path}")
        return {"error": "path_not_found"}

    # Find all PDF files
    pdf_files = list(pdfs_path.rglob("*.pdf"))
    stats["found"] = len(pdf_files)

    if dry_run:
        # Count total pages
        for pdf_path in pdf_files:
            try:
                doc = fitz.open(pdf_path)
                stats["pages"] += len(doc)
                doc.close()
            except Exception as e:
                logger.warning(f"Error counting pages in {pdf_path}: {e}")
        logger.info(
            f"[DRY RUN] Found {len(pdf_files)} PDF files "
            f"with {stats['pages']} total pages to convert"
        )
        return stats

    logger.info(f"Converting {len(pdf_files)} PDF files from FinanceBench...")

    for pdf_path in pdf_files:
        try:
            # Create output directory (flat structure since PDFs are in single dir)
            output_dir = input_path / output_subdir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Open PDF
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                logger.warning(f"Empty PDF: {pdf_path}")
                stats["errors"] += 1
                continue

            # Convert each page
            for page_num in range(len(doc)):
                # Output filename includes page number for multi-page PDFs
                if len(doc) == 1:
                    output_path = output_dir / f"{pdf_path.stem}.png"
                else:
                    output_path = (
                        output_dir / f"{pdf_path.stem}_p{page_num + 1:03d}.png"
                    )

                # Skip if already converted
                if output_path.exists():
                    stats["skipped"] += 1
                    continue

                # Render page at target DPI
                page = doc[page_num]
                zoom = target_dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                # Save as PNG
                pix.save(str(output_path))
                stats["pages"] += 1

            doc.close()
            stats["converted"] += 1

            if stats["converted"] % 50 == 0:
                logger.info(
                    f"Converted {stats['converted']}/{stats['found']} PDFs "
                    f"({stats['pages']} pages)..."
                )

        except Exception as e:
            logger.error(f"Error converting {pdf_path}: {e}")
            stats["errors"] += 1

    logger.info(
        f"FinanceBench conversion complete: "
        f"{stats['converted']} PDFs converted ({stats['pages']} pages), "
        f"{stats['skipped']} pages skipped, "
        f"{stats['errors']} errors"
    )
    return stats


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert datasets to images for annotation pipeline"
    )
    parser.add_argument(
        "--dataset",
        choices=["yarmouk", "cc-ocr", "ohr-bench", "financebench"],
        help="Dataset to convert",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Convert all supported datasets",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count files without converting",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Target DPI for PDF rendering (default: 300)",
    )
    parser.add_argument(
        "--output-subdir",
        default="extracted_images",
        help="Subdirectory for extracted images (default: extracted_images)",
    )

    args = parser.parse_args()

    if not args.dataset and not args.all:
        parser.print_help()
        return 1

    results = {}

    if args.all or args.dataset == "yarmouk":
        logger.info("=" * 60)
        logger.info("Processing Yarmouk OCR (PDF to PNG)")
        logger.info("=" * 60)
        results["yarmouk"] = convert_yarmouk_pdfs(
            output_subdir=args.output_subdir,
            target_dpi=args.dpi,
            dry_run=args.dry_run,
        )

    if args.all or args.dataset == "cc-ocr":
        logger.info("=" * 60)
        logger.info("Processing CC-OCR (TSV base64 to images)")
        logger.info("=" * 60)
        results["cc-ocr"] = extract_ccor_images(
            output_subdir=args.output_subdir,
            dry_run=args.dry_run,
        )

    if args.all or args.dataset == "ohr-bench":
        logger.info("=" * 60)
        logger.info("Processing OHR-Bench (PDF to PNG)")
        logger.info("=" * 60)
        results["ohr-bench"] = convert_ohr_bench_pdfs(
            output_subdir=args.output_subdir,
            target_dpi=args.dpi,
            dry_run=args.dry_run,
        )

    if args.all or args.dataset == "financebench":
        logger.info("=" * 60)
        logger.info("Processing FinanceBench (SEC filings PDF to PNG)")
        logger.info("=" * 60)
        results["financebench"] = convert_financebench_pdfs(
            output_subdir=args.output_subdir,
            target_dpi=args.dpi,
            dry_run=args.dry_run,
        )

    # Print summary
    logger.info("=" * 60)
    logger.info("CONVERSION SUMMARY")
    logger.info("=" * 60)
    for dataset, stats in results.items():
        logger.info(f"{dataset}: {stats}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
