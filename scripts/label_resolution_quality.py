#!/usr/bin/env python3
"""Label document images with resolution quality scores.

Two-stage measurement pipeline:
  Stage 1: PaddleOCR text detection (DBNet) for robust text line identification.
  Stage 2: Connected component analysis within detected regions for precise
           character height measurement.

Outputs per-image JSON with resolution_quality_score, confidence, range, and
coarse bucket classification.

Requires: paddleocr (pip install paddleocr paddlepaddle)

Usage:
    python scripts/label_resolution_quality.py \\
        --input-dir /path/to/images \\
        --output-json results/resolution_quality_labels.json \\
        --gpu

    # Process DIQA-5000 specifically
    python scripts/label_resolution_quality.py \\
        --input-dir /mnt/e/image_detection/datasets/diqa-5000 \\
        --output-json results/diqa5000_resolution_labels.json \\
        --gpu --fix-orientation
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}


def _setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _find_images(input_dir: Path, recursive: bool) -> list[Path]:
    """Find all image files in directory."""
    pattern = "**/*" if recursive else "*"
    images = []
    for p in input_dir.glob(pattern):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(p)
    images.sort()
    return images


def _load_paddleocr(use_gpu: bool, fix_orientation: bool) -> object:
    """Initialize PaddleOCR with text detection only.

    Args:
        use_gpu: Whether to use GPU acceleration.
        fix_orientation: Whether to enable orientation classification.

    Returns:
        PaddleOCR instance configured for detection-only mode.

    Raises:
        ImportError: If paddleocr is not installed.
    """
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        msg = (
            "PaddleOCR is required for resolution quality labeling.\n"
            "Install with: pip install paddleocr paddlepaddle\n"
            "For GPU: pip install paddleocr paddlepaddle-gpu"
        )
        raise ImportError(msg) from exc

    ocr = PaddleOCR(
        use_angle_cls=fix_orientation,
        lang="ch",  # Chinese model handles both CJK and Latin
        det=True,
        rec=False,  # Detection only - no recognition needed
        cls=fix_orientation,
        use_gpu=use_gpu,
        show_log=False,
    )
    return ocr


def _detect_text_regions(
    ocr: object,
    image_path: Path,
) -> list[list[list[float]]]:
    """Run PaddleOCR text detection on an image.

    Args:
        ocr: PaddleOCR instance.
        image_path: Path to image file.

    Returns:
        List of 4-point polygons [[x,y], ...] for each detected text line.
    """
    result = ocr.ocr(str(image_path), det=True, rec=False, cls=False)

    if result is None or len(result) == 0:
        return []

    # PaddleOCR returns nested list: [[polygons_page1], [polygons_page2], ...]
    polygons = []
    for page_result in result:
        if page_result is None:
            continue
        for detection in page_result:
            # detection is a polygon: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            if isinstance(detection, (list, tuple)) and len(detection) >= 4:
                polygons.append(detection)
            elif isinstance(detection, dict) and "points" in detection:
                polygons.append(detection["points"])

    return polygons


def _process_single_image(
    ocr: object,
    image_path: Path,
    input_dir: Path,
) -> dict:
    """Process a single image through the two-stage pipeline.

    Args:
        ocr: PaddleOCR instance.
        image_path: Path to image.
        input_dir: Base input directory (for relative path computation).

    Returns:
        Dictionary with image_path and ResolutionQualityResult fields.
    """
    import cv2
    import numpy as np

    from image_preprocessing_detector.schema_utils.resolution_quality import (
        aggregate_measurements,
        crop_polygon_region,
        extract_line_height_from_polygon,
        measure_char_height_in_region,
    )

    start_time = time.monotonic()

    # Load image as grayscale for Stage 2
    image_gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image_gray is None:
        logger.warning("Failed to load image: %s", image_path)
        return {
            "image_path": str(image_path.relative_to(input_dir)),
            "error": "failed_to_load",
        }

    # Stage 1: Text detection via PaddleOCR DBNet
    polygons = _detect_text_regions(ocr, image_path)

    if len(polygons) == 0:
        elapsed = time.monotonic() - start_time
        result = aggregate_measurements([], [], [], [])
        output = result.to_dict()
        output["image_path"] = str(image_path.relative_to(input_dir))
        output["processing_time_ms"] = round(elapsed * 1000, 1)
        return output

    # Stage 2: CC analysis within each detected region
    region_heights: list[float] = []
    bbox_heights: list[float] = []
    cc_success_flags: list[bool] = []
    region_areas: list[float] = []

    for polygon in polygons:
        # Stage 1 measurement: bbox height from polygon
        bbox_h = extract_line_height_from_polygon(polygon)
        bbox_heights.append(bbox_h)

        # Compute region area for weighting
        pts = np.array(polygon, dtype=np.float64)
        area = float(cv2.contourArea(pts.astype(np.int32)))
        region_areas.append(max(area, 1.0))

        # Stage 2: Crop region and run CC analysis
        cropped = crop_polygon_region(image_gray, polygon)
        if cropped is None:
            region_heights.append(bbox_h)  # Fallback to Stage 1
            cc_success_flags.append(False)
            continue

        cc_height, _component_heights = measure_char_height_in_region(cropped)
        if cc_height is not None:
            region_heights.append(cc_height)
            cc_success_flags.append(True)
        else:
            region_heights.append(bbox_h)  # Fallback to Stage 1
            cc_success_flags.append(False)

    # Aggregate into single result
    result = aggregate_measurements(
        region_heights, bbox_heights, cc_success_flags, region_areas
    )

    elapsed = time.monotonic() - start_time
    output = result.to_dict()
    output["image_path"] = str(image_path.relative_to(input_dir))
    output["processing_time_ms"] = round(elapsed * 1000, 1)
    output["image_dimensions"] = [int(image_gray.shape[1]), int(image_gray.shape[0])]

    return output


def main() -> int:
    """CLI entry point for resolution quality labeling."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Label document images with resolution quality scores.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing document images.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        help="Output JSON file path for labels.",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        default=False,
        help="Use GPU for PaddleOCR text detection.",
    )
    parser.add_argument(
        "--fix-orientation",
        action="store_true",
        default=False,
        help="Enable PaddleOCR orientation classifier to correct rotated images.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively search subdirectories (default: True).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of images to process (0 = all).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable debug logging.",
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)

    # Validate input
    if not args.input_dir.is_dir():
        logger.error("Input directory does not exist: %s", args.input_dir)
        return 1

    # Find images
    images = _find_images(args.input_dir, args.recursive)
    if not images:
        logger.error("No images found in %s", args.input_dir)
        return 1

    if args.limit > 0:
        images = images[: args.limit]

    logger.info("Found %d images in %s", len(images), args.input_dir)

    # Initialize PaddleOCR
    logger.info(
        "Initializing PaddleOCR (GPU=%s, orientation=%s)...",
        args.gpu,
        args.fix_orientation,
    )
    ocr = _load_paddleocr(args.gpu, args.fix_orientation)

    # Process images
    results: list[dict] = []
    errors = 0
    flagged = 0

    try:
        from tqdm import tqdm

        progress = tqdm(images, desc="Labeling", unit="img")
    except ImportError:
        progress = images
        logger.info("Install tqdm for progress bar: pip install tqdm")

    for image_path in progress:
        try:
            result = _process_single_image(ocr, image_path, args.input_dir)
            results.append(result)
            if result.get("error"):
                errors += 1
            elif result.get("flagged_for_review"):
                flagged += 1
        except Exception:
            logger.exception("Failed to process %s", image_path)
            results.append({
                "image_path": str(image_path.relative_to(args.input_dir)),
                "error": "processing_exception",
            })
            errors += 1

    # Write output
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "tool": "label_resolution_quality.py",
            "input_dir": str(args.input_dir),
            "total_images": len(results),
            "errors": errors,
            "flagged_for_review": flagged,
            "gpu": args.gpu,
            "fix_orientation": args.fix_orientation,
        },
        "results": results,
    }

    with open(args.output_json, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(
        "Done. %d images labeled, %d errors, %d flagged. Output: %s",
        len(results) - errors,
        errors,
        flagged,
        args.output_json,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
