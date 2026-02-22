#!/usr/bin/env python3
"""Generate multi-task pseudo-labels using the SigLIP2 teacher model.

Runs the multi-task teacher in eval mode on unlabeled document corpora,
producing per-image predictions with full softmax distributions and
uncertainty estimates suitable for knowledge distillation (Stream 8)
and active learning.

Output Format:
    JSON file with per-image records containing:
    - All 8 task predictions (IQA overall/sharpness/color, script,
      source, orientation, shadow, warping)
    - Full classification distributions (not just argmax)
    - Regression uncertainty (sigma_sq)
    - Entropy-based active learning flags

Usage:
    # Label a local image directory
    python scripts/generate_multitask_labels.py \\
        --input-dir /path/to/images \\
        --checkpoint best_model.pt \\
        --output-json results/multitask_labels.json

    # With GPU and custom entropy threshold
    python scripts/generate_multitask_labels.py \\
        --input-dir /mnt/e/datasets/unlabeled_docs \\
        --checkpoint models/siglip2_multitask_best.pt \\
        --output-json results/corpus_labels.json \\
        --device cuda \\
        --entropy-threshold 1.5 \\
        --verbose

    # Parallel processing with batch output
    python scripts/generate_multitask_labels.py \\
        --input-dir /mnt/e/datasets/large_corpus \\
        --checkpoint models/siglip2_multitask_best.pt \\
        --output-json results/large_corpus_labels.json \\
        --workers 4

Requires: torch, transformers, opencv-python, Pillow
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}

# Default entropy threshold for flagging uncertain predictions
DEFAULT_ENTROPY_THRESHOLD = 1.5


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


def _compute_classification_entropy(distribution: dict[str, float]) -> float:
    """Compute Shannon entropy of a classification distribution.

    Higher entropy → more uncertain prediction → candidate for active learning.

    Args:
        distribution: Class name → probability mapping.

    Returns:
        Shannon entropy in nats. Zero if degenerate.
    """
    entropy = 0.0
    for prob in distribution.values():
        if prob > 0:
            entropy -= prob * math.log(prob)
    return entropy


def _compute_regression_uncertainty_flag(
    sigma_sq: float,
    threshold: float = 0.1,
) -> bool:
    """Flag regression predictions with high uncertainty.

    Args:
        sigma_sq: Predicted variance (uncertainty).
        threshold: Variance above this is flagged.

    Returns:
        True if prediction should be reviewed.
    """
    return sigma_sq > threshold


def _load_image(image_path: Path) -> np.ndarray | None:
    """Load image as BGR numpy array.

    Args:
        image_path: Path to image file.

    Returns:
        BGR numpy array, or None if loading fails.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        logger.warning("Failed to load image: %s", image_path)
    return img


def _prediction_to_label_record(
    image_path: Path,
    input_dir: Path,
    prediction: Any,
    entropy_threshold: float,
) -> dict[str, Any]:
    """Convert MultiTaskPrediction to a label record for output.

    Stores full softmax distributions for knowledge distillation,
    computes entropy for active learning flagging.

    Args:
        image_path: Absolute path to the image.
        input_dir: Root directory (for relative path computation).
        prediction: MultiTaskPrediction from the detector.
        entropy_threshold: Entropy above this flags for active learning.

    Returns:
        Dict with all predictions, distributions, and flags.
    """
    # Classification entropy
    script_entropy = _compute_classification_entropy(
        prediction.script.distribution,
    )
    source_entropy = _compute_classification_entropy(
        prediction.source.distribution,
    )
    orient_entropy = _compute_classification_entropy(
        prediction.orientation.distribution,
    )

    # Active learning flags
    script_flag = script_entropy > entropy_threshold
    source_flag = source_entropy > entropy_threshold
    shadow_flag = _compute_regression_uncertainty_flag(
        prediction.shadow.sigma_sq,
    )
    warping_flag = _compute_regression_uncertainty_flag(
        prediction.warping.sigma_sq,
    )
    any_flag = script_flag or source_flag or shadow_flag or warping_flag

    return {
        "image_path": str(image_path.relative_to(input_dir)),
        "predictions": {
            "iqa": {
                "overall": {
                    "mu": prediction.iqa_overall.mu,
                    "sigma_sq": prediction.iqa_overall.sigma_sq,
                },
                "sharpness": {
                    "mu": prediction.iqa_sharpness.mu,
                    "sigma_sq": prediction.iqa_sharpness.sigma_sq,
                },
                "color": {
                    "mu": prediction.iqa_color.mu,
                    "sigma_sq": prediction.iqa_color.sigma_sq,
                },
            },
            "script": {
                "predicted": prediction.script.predicted_class,
                "confidence": prediction.script.confidence,
                "distribution": prediction.script.distribution,
                "entropy": script_entropy,
            },
            "source": {
                "predicted": prediction.source.predicted_class,
                "confidence": prediction.source.confidence,
                "distribution": prediction.source.distribution,
                "entropy": source_entropy,
            },
            "orientation": {
                "degrees": prediction.orientation_degrees,
                "confidence": prediction.orientation.confidence,
                "distribution": prediction.orientation.distribution,
                "entropy": orient_entropy,
            },
            "shadow": {
                "severity": prediction.shadow.value,
                "sigma_sq": prediction.shadow.sigma_sq,
            },
            "warping": {
                "severity": prediction.warping.value,
                "sigma_sq": prediction.warping.sigma_sq,
            },
        },
        "active_learning": {
            "flagged": any_flag,
            "script_uncertain": script_flag,
            "source_uncertain": source_flag,
            "shadow_uncertain": shadow_flag,
            "warping_uncertain": warping_flag,
            "max_classification_entropy": max(
                script_entropy, source_entropy, orient_entropy,
            ),
        },
        "inference_time_ms": prediction.inference_time_ms,
        "device": prediction.device,
    }


def _process_single_image(
    detector: Any,
    image_path: Path,
    input_dir: Path,
    entropy_threshold: float,
) -> dict[str, Any]:
    """Process a single image through the multi-task detector.

    Args:
        detector: SigLIP2MultiTaskDetector instance.
        image_path: Path to the image.
        input_dir: Root directory for relative path.
        entropy_threshold: Entropy threshold for active learning.

    Returns:
        Label record dict.
    """
    image = _load_image(image_path)
    if image is None:
        return {
            "image_path": str(image_path.relative_to(input_dir)),
            "error": "load_failed",
        }

    prediction = detector.predict(image)
    return _prediction_to_label_record(
        image_path, input_dir, prediction, entropy_threshold,
    )


def _process_batch_worker(
    image_paths: list[str],
    input_dir_str: str,
    checkpoint_path: str,
    device: str | None,
    entropy_threshold: float,
) -> list[dict[str, Any]]:
    """Process a batch of images in a worker process.

    Args:
        image_paths: List of image path strings.
        input_dir_str: Root directory string.
        checkpoint_path: Model checkpoint path.
        device: Device override.
        entropy_threshold: Entropy threshold.

    Returns:
        List of label records.
    """
    from image_preprocessing_detector.detection.siglip2_multitask import (
        SigLIP2MultiTaskConfig,
        SigLIP2MultiTaskDetector,
    )

    config = SigLIP2MultiTaskConfig(device=device) if device else None
    detector = SigLIP2MultiTaskDetector(
        checkpoint_path=checkpoint_path, config=config,
    )

    input_dir = Path(input_dir_str)
    results = []
    for path_str in image_paths:
        try:
            record = _process_single_image(
                detector, Path(path_str), input_dir, entropy_threshold,
            )
            results.append(record)
        except Exception:
            logger.exception("Failed to process %s", path_str)
            results.append({
                "image_path": str(Path(path_str).relative_to(input_dir)),
                "error": "processing_exception",
            })
    return results


def _chunk_list(lst: list[Any], num_chunks: int) -> list[list[Any]]:
    """Split a list into approximately equal chunks.

    Args:
        lst: List to split.
        num_chunks: Number of chunks.

    Returns:
        List of sublists.
    """
    chunk_size = max(1, len(lst) // num_chunks)
    chunks = []
    for i in range(0, len(lst), chunk_size):
        chunks.append(lst[i : i + chunk_size])
    return chunks


def run_labeling(args: argparse.Namespace) -> int:
    """Run the multi-task pseudo-labeling pipeline.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 = success).
    """
    _setup_logging(args.verbose)
    start_time = time.time()

    # Find images
    images = _find_images(args.input_dir, recursive=args.recursive)
    if not images:
        logger.error("No images found in %s", args.input_dir)
        return 1

    logger.info(
        "Found %d images in %s (recursive=%s)",
        len(images), args.input_dir, args.recursive,
    )

    results: list[dict[str, Any]] = []
    errors = 0
    flagged_count = 0

    if args.workers > 1:
        # Multi-process mode
        logger.info("Using %d worker processes", args.workers)
        image_str_paths = [str(p) for p in images]
        chunks = _chunk_list(image_str_paths, args.workers)

        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    _process_batch_worker,
                    chunk,
                    str(args.input_dir),
                    str(args.checkpoint),
                    args.device,
                    args.entropy_threshold,
                ): i
                for i, chunk in enumerate(chunks)
            }
            for future in as_completed(futures):
                batch_results = future.result()
                results.extend(batch_results)
    else:
        # Single-process mode with progress bar
        from image_preprocessing_detector.detection.siglip2_multitask import (
            SigLIP2MultiTaskConfig,
            SigLIP2MultiTaskDetector,
        )

        config = SigLIP2MultiTaskConfig(device=args.device) if args.device else None
        detector = SigLIP2MultiTaskDetector(
            checkpoint_path=args.checkpoint, config=config,
        )

        try:
            from tqdm import tqdm
            progress: Any = tqdm(images, desc="Labeling", unit="img")
        except ImportError:
            progress = images
            logger.info("Install tqdm for progress bar: pip install tqdm")

        for image_path in progress:
            try:
                record = _process_single_image(
                    detector, image_path, args.input_dir, args.entropy_threshold,
                )
                results.append(record)
            except Exception:
                logger.exception("Failed to process %s", image_path)
                results.append({
                    "image_path": str(image_path.relative_to(args.input_dir)),
                    "error": "processing_exception",
                })

    # Compute summary statistics
    for record in results:
        if record.get("error"):
            errors += 1
        elif record.get("active_learning", {}).get("flagged"):
            flagged_count += 1

    elapsed = time.time() - start_time
    throughput = len(results) / elapsed if elapsed > 0 else 0

    # Write output
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "tool": "generate_multitask_labels.py",
            "version": "1.0.0",
            "input_dir": str(args.input_dir),
            "checkpoint": str(args.checkpoint),
            "device": args.device or "auto",
            "total_images": len(results),
            "successful": len(results) - errors,
            "errors": errors,
            "flagged_for_active_learning": flagged_count,
            "entropy_threshold": args.entropy_threshold,
            "workers": args.workers,
            "elapsed_seconds": round(elapsed, 1),
            "throughput_img_per_sec": round(throughput, 2),
        },
        "results": results,
    }

    with open(args.output_json, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(
        "Done. %d images labeled, %d errors, %d flagged for active learning. "
        "Output: %s (%.1fs, %.2f img/s)",
        len(results) - errors,
        errors,
        flagged_count,
        args.output_json,
        elapsed,
        throughput,
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Generate multi-task pseudo-labels using SigLIP2 teacher model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing document images to label.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="Path to trained SigLIP2 multi-task model checkpoint (.pt).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        help="Path for output JSON file with pseudo-labels.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device override (e.g., 'cuda', 'cpu'). Default: auto-detect.",
    )
    parser.add_argument(
        "--entropy-threshold",
        type=float,
        default=DEFAULT_ENTROPY_THRESHOLD,
        help=(
            "Shannon entropy threshold for active learning flagging. "
            f"Default: {DEFAULT_ENTROPY_THRESHOLD}"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes for parallel labeling. Default: 1.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search subdirectories for images.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def main() -> int:
    """Entry point for CLI execution.

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        logger.error("Input directory does not exist: %s", args.input_dir)
        return 1

    if not args.checkpoint.exists():
        logger.error("Checkpoint file not found: %s", args.checkpoint)
        return 1

    return run_labeling(args)


if __name__ == "__main__":
    sys.exit(main())
