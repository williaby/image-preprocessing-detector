#!/usr/bin/env python3
"""Label document images with skew angle and orientation predictions.

Uses the trained MobileNetV4-Conv-S ONNX model (3-head: orientation,
skew bins, skew regression) for CPU-only inference. No Modal, no GPU,
no torch required.

Outputs per-image JSON with orientation class, skew angle, and confidence
scores suitable for Layer 2 metadata integration.

Requirements: onnxruntime, opencv-python-headless, numpy (all in base deps)

Usage:
    # Quick smoke test
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python scripts/label_skew_orientation.py \
        --input-dir /mnt/e/image_detection/01_source_datasets/diqa-5000/test/ori \
        --output-json results/diqa5000_skew_labels.json \
        --limit 10 --verbose

    # Full dataset run
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python scripts/label_skew_orientation.py \
        --input-dir /mnt/e/image_detection/01_source_datasets/diqa-5000 \
        --output-json results/diqa5000_skew_labels.json
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

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
    """Find all image files in directory.

    Args:
        input_dir: Root directory to search.
        recursive: Whether to search subdirectories.

    Returns:
        Sorted list of image file paths.
    """
    pattern = "**/*" if recursive else "*"
    images = [
        p for p in input_dir.glob(pattern)
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    images.sort()
    return images


def _process_single_image(
    inference: object,
    image_path: Path,
    input_dir: Path,
) -> dict:
    """Run skew/orientation inference on a single image.

    Args:
        inference: SkewEstimatorInference instance.
        image_path: Path to image file.
        input_dir: Base directory for relative path computation.

    Returns:
        Dict with prediction fields and timing.
    """
    import cv2

    start = time.monotonic()

    image = cv2.imread(str(image_path))
    if image is None:
        logger.warning("Failed to load image: %s", image_path)
        return {
            "image_path": str(image_path.relative_to(input_dir)),
            "error": "failed_to_load",
        }

    result = inference.predict(image)  # type: ignore[union-attr]
    elapsed_ms = (time.monotonic() - start) * 1000

    return {
        "image_path": str(image_path.relative_to(input_dir)),
        "orientation_class": result.orientation_class,
        "orientation_confidence": round(result.orientation_confidence, 4),
        "skew_angle_degrees": round(result.final_angle, 4),
        "skew_bin": result.skew_bin,
        "skew_bin_confidence": round(result.skew_bin_confidence, 4),
        "skew_residual": round(result.skew_residual, 4),
        "skew_uncertainty": round(result.skew_uncertainty, 4),
        "processing_time_ms": round(elapsed_ms, 1),
        "image_dimensions": [int(image.shape[1]), int(image.shape[0])],
    }


def main() -> int:
    """CLI entry point for skew/orientation labeling."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Label document images with skew angle and orientation.",
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
        "--model-path",
        type=Path,
        default=None,
        help="Path to ONNX model file (defaults to config YAML path).",
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

    # Validate input directory
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

    # Resolve model path
    from image_preprocessing_detector.models.skew_estimator import (
        BinConfig,
        SkewEstimatorInference,
    )

    bin_config = BinConfig.from_yaml()

    if args.model_path:
        model_path = args.model_path
    else:
        # Load from config YAML
        import yaml

        config_path = Path(__file__).resolve().parents[1] / "config" / "skew_estimation.yaml"
        with config_path.open() as f:
            cfg = yaml.safe_load(f)
        model_rel = cfg["model"]["onnx_fp32_path"]
        model_path = Path(__file__).resolve().parents[1] / model_rel

    if not model_path.is_file():
        logger.error("ONNX model not found: %s", model_path)
        return 1

    input_size = bin_config.zones[0].count  # Will use from config
    # Read input_size from config
    import yaml

    config_path = Path(__file__).resolve().parents[1] / "config" / "skew_estimation.yaml"
    with config_path.open() as f:
        cfg = yaml.safe_load(f)
    input_size = int(cfg["model"]["input_size"])

    logger.info(
        "Loading ONNX model from %s (input_size=%d, bins=%d)",
        model_path,
        input_size,
        bin_config.total_bins,
    )

    inference = SkewEstimatorInference(
        model_path=model_path,
        bin_config=bin_config,
        input_size=input_size,
    )

    # Process images
    results: list[dict] = []
    errors = 0
    total_time_ms = 0.0

    try:
        from tqdm import tqdm

        progress = tqdm(images, desc="Labeling", unit="img")
    except ImportError:
        progress = images
        logger.info("Install tqdm for progress bar: pip install tqdm")

    for image_path in progress:
        try:
            result = _process_single_image(inference, image_path, args.input_dir)
            results.append(result)
            if result.get("error"):
                errors += 1
            else:
                total_time_ms += result.get("processing_time_ms", 0.0)
        except Exception:
            logger.exception("Failed to process %s", image_path)
            results.append({
                "image_path": str(image_path.relative_to(args.input_dir)),
                "error": "processing_exception",
            })
            errors += 1

    # Compute summary stats
    successful = len(results) - errors
    avg_time_ms = total_time_ms / max(successful, 1)

    # Orientation distribution
    orient_counts: dict[int, int] = {}
    for r in results:
        if "orientation_class" in r:
            oc = r["orientation_class"]
            orient_counts[oc] = orient_counts.get(oc, 0) + 1

    # Write output
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "tool": "label_skew_orientation.py",
            "model": str(model_path),
            "input_size": input_size,
            "input_dir": str(args.input_dir),
            "total_images": len(results),
            "successful": successful,
            "errors": errors,
            "avg_processing_time_ms": round(avg_time_ms, 1),
            "orientation_distribution": orient_counts,
        },
        "results": results,
    }

    with open(args.output_json, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(
        "Done. %d images labeled, %d errors. Avg %.1fms/img. Output: %s",
        successful,
        errors,
        avg_time_ms,
        args.output_json,
    )

    # Cleanup
    inference.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
