#!/usr/bin/env python3
"""Label natural scan images with classical skew detection angles.

Reads the natural scan manifest produced by `select_natural_scan_skew_subset.py`
and runs the classical SkewDetector (Hough + Projection ensemble) on each image
to produce ground-truth skew angle labels with confidence scores.

Images with low confidence (< threshold) are flagged but not discarded — the
downstream training pipeline decides whether to use them.

Output:
  output_dir/
    natural_scan_skew_labels.json  # Per-image skew labels
    labeling_report.json           # Statistics

Usage:
    # Label all images in manifest
    python scripts/label_skew_classical.py \\
        --manifest /mnt/e/.../skew/natural_scan_manifest.json \\
        --output-dir /mnt/e/.../skew \\
        --workers 4

    # Dry run (process first N images only)
    python scripts/label_skew_classical.py \\
        --manifest /mnt/e/.../skew/natural_scan_manifest.json \\
        --output-dir /mnt/e/.../skew \\
        --limit 100
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def detect_skew_classical(image_path: str) -> dict[str, Any]:
    """Run classical skew detection on a single image.

    Uses the same Hough + Projection ensemble logic as the main pipeline's
    SkewDetector, but simplified for batch processing without structlog.

    Args:
        image_path: Absolute path to the image file.

    Returns:
        Dict with angle, confidence, method, and any error info.
    """
    result: dict[str, Any] = {
        "path": image_path,
        "angle": 0.0,
        "confidence": 0.0,
        "method": "none",
        "error": None,
    }

    try:
        image = cv2.imread(image_path)
        if image is None:
            result["error"] = "failed_to_read"
            return result

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, w = gray.shape

        # Hough Transform method
        angle_hough, conf_hough = _detect_hough(gray, w)

        # Projection Profile method
        angle_proj, conf_proj = _detect_projection(gray)

        # Ensemble logic (matches iqa_classical.py)
        if conf_hough > 0.3 and conf_proj > 0.3:
            angle = (angle_hough + angle_proj) / 2.0
            confidence = max(conf_hough, conf_proj)
            method = "ensemble"
        elif conf_hough >= conf_proj:
            angle = angle_hough
            confidence = conf_hough
            method = "hough"
        else:
            angle = angle_proj
            confidence = conf_proj
            method = "projection"

        result["angle"] = round(float(angle), 4)
        result["confidence"] = round(float(confidence), 4)
        result["method"] = method

    except Exception as exc:
        result["error"] = str(exc)

    return result


def _detect_hough(gray: np.ndarray, width: int) -> tuple[float, float]:
    """Detect skew using Hough Line Transform."""
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        min_line_length = max(50, width // 8)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=min_line_length,
            maxLineGap=10,
        )

        if lines is None or len(lines) == 0:
            return 0.0, 0.0

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 == 0:
                continue
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if angle > 45:
                angle -= 90
            elif angle < -45:
                angle += 90
            angles.append(angle)

        if not angles:
            return 0.0, 0.0

        angle = float(np.median(angles))
        std = float(np.std(angles))
        confidence = 1.0 / (1.0 + std / 10.0)
        return angle, confidence

    except Exception:
        return 0.0, 0.0


def _detect_projection(gray: np.ndarray) -> tuple[float, float]:
    """Detect skew using projection profile analysis."""
    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        best_angle = 0.0
        best_score = 0.0

        for angle_tenths in range(-100, 101, 5):  # -10.0 to +10.0 degrees
            angle = angle_tenths / 10.0
            h, w = binary.shape
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(binary, matrix, (w, h))
            projection = np.sum(rotated, axis=1, dtype=np.float64)
            score = float(np.var(projection))
            if score > best_score:
                best_score = score
                best_angle = angle

        # Refine around best angle
        for angle_tenths in range(
            int(best_angle * 10) - 5, int(best_angle * 10) + 6
        ):
            angle = angle_tenths / 10.0
            h, w = binary.shape
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(binary, matrix, (w, h))
            projection = np.sum(rotated, axis=1, dtype=np.float64)
            score = float(np.var(projection))
            if score > best_score:
                best_score = score
                best_angle = angle

        # Confidence: ratio of best score to mean score
        confidence = min(1.0, best_score / max(1.0, best_score * 0.5 + 1.0))
        return best_angle, confidence

    except Exception:
        return 0.0, 0.0


def process_batch(
    images: list[dict[str, Any]], num_workers: int
) -> list[dict[str, Any]]:
    """Process a batch of images with multiprocessing.

    Args:
        images: List of image records from manifest.
        num_workers: Number of parallel workers.

    Returns:
        List of skew detection results.
    """
    paths = [img["path"] for img in images]
    results: list[dict[str, Any]] = []

    if num_workers <= 1:
        for i, path in enumerate(paths):
            if i % 500 == 0 and i > 0:
                logger.info("Progress: %d/%d", i, len(paths))
            result = detect_skew_classical(path)
            results.append(result)
    else:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(detect_skew_classical, path): i
                for i, path in enumerate(paths)
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 500 == 0:
                    logger.info("Progress: %d/%d", completed, len(paths))
                results.append(future.result())

    # Sort by path to maintain deterministic ordering
    results.sort(key=lambda r: r["path"])
    return results


def generate_report(
    results: list[dict[str, Any]], confidence_threshold: float
) -> dict[str, Any]:
    """Generate labeling statistics report."""
    total = len(results)
    errors = sum(1 for r in results if r["error"] is not None)
    successful = total - errors

    confidences = [r["confidence"] for r in results if r["error"] is None]
    angles = [r["angle"] for r in results if r["error"] is None]

    high_conf = sum(1 for c in confidences if c >= confidence_threshold)
    low_conf = sum(1 for c in confidences if c < confidence_threshold)

    method_dist = Counter(r["method"] for r in results if r["error"] is None)

    # Angle distribution bins
    angle_bins = {
        "near_zero (|a|<0.5)": sum(1 for a in angles if abs(a) < 0.5),
        "mild (0.5<=|a|<2)": sum(1 for a in angles if 0.5 <= abs(a) < 2),
        "moderate (2<=|a|<5)": sum(1 for a in angles if 2 <= abs(a) < 5),
        "large (5<=|a|<15)": sum(1 for a in angles if 5 <= abs(a) < 15),
        "extreme (|a|>=15)": sum(1 for a in angles if abs(a) >= 15),
    }

    report: dict[str, Any] = {
        "total": total,
        "successful": successful,
        "errors": errors,
        "high_confidence": high_conf,
        "low_confidence": low_conf,
        "confidence_threshold": confidence_threshold,
        "method_distribution": dict(method_dist),
        "angle_distribution": angle_bins,
    }

    if confidences:
        report["confidence_stats"] = {
            "mean": round(float(np.mean(confidences)), 4),
            "median": round(float(np.median(confidences)), 4),
            "std": round(float(np.std(confidences)), 4),
            "min": round(float(min(confidences)), 4),
            "max": round(float(max(confidences)), 4),
        }

    if angles:
        report["angle_stats"] = {
            "mean": round(float(np.mean(angles)), 4),
            "median": round(float(np.median(angles)), 4),
            "std": round(float(np.std(angles)), 4),
            "min": round(float(min(angles)), 4),
            "max": round(float(max(angles)), 4),
        }

    return report


def print_report(report: dict[str, Any]) -> None:
    """Print human-readable labeling report."""
    print("\n" + "=" * 60)
    print("CLASSICAL SKEW LABELING REPORT")
    print("=" * 60)
    print(f"\nTotal: {report['total']}")
    print(f"Successful: {report['successful']}")
    print(f"Errors: {report['errors']}")
    print(
        f"High confidence (>={report['confidence_threshold']}): "
        f"{report['high_confidence']}"
    )
    print(f"Low confidence: {report['low_confidence']}")

    if "confidence_stats" in report:
        cs = report["confidence_stats"]
        print(f"\nConfidence: mean={cs['mean']}, median={cs['median']}, "
              f"std={cs['std']}")

    if "angle_stats" in report:
        a_s = report["angle_stats"]
        print(f"Angle: mean={a_s['mean']}, median={a_s['median']}, "
              f"range=[{a_s['min']}, {a_s['max']}]")

    print("\nMethod distribution:")
    for method, count in report.get("method_distribution", {}).items():
        pct = 100 * count / report["successful"] if report["successful"] else 0
        print(f"  {method:12s}: {count:6d} ({pct:5.1f}%)")

    print("\nAngle distribution:")
    for bucket, count in report.get("angle_distribution", {}).items():
        pct = 100 * count / report["successful"] if report["successful"] else 0
        bar = "#" * int(pct / 2)
        print(f"  {bucket:25s}: {count:6d} ({pct:5.1f}%) {bar}")

    print("=" * 60)


def main() -> int:
    """Run classical skew labeling on manifest images."""
    parser = argparse.ArgumentParser(
        description="Label natural scan images with classical skew detection"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to natural_scan_manifest.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for labels and report",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Minimum confidence threshold for high-quality labels (default: 0.7)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N images (0 = all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.manifest.exists():
        logger.error("Manifest not found: %s", args.manifest)
        return 1

    # Load manifest
    with open(args.manifest) as f:
        manifest = json.load(f)

    images = manifest["images"]
    if args.limit > 0:
        images = images[: args.limit]
        logger.info("Limited to first %d images", args.limit)

    logger.info("Processing %d images with %d workers...", len(images), args.workers)
    start_time = time.time()

    # Run detection
    results = process_batch(images, args.workers)

    elapsed = time.time() - start_time
    rate = len(results) / elapsed if elapsed > 0 else 0
    logger.info(
        "Labeling complete: %d images in %.1fs (%.1f img/s)",
        len(results),
        elapsed,
        rate,
    )

    # Merge results with manifest metadata
    path_to_result = {r["path"]: r for r in results}
    labeled_images: list[dict[str, Any]] = []
    for img in images:
        r = path_to_result.get(img["path"])
        if r is None:
            continue
        labeled = {**img}  # Copy manifest fields
        labeled["classical_skew_angle"] = r["angle"]
        labeled["classical_skew_confidence"] = r["confidence"]
        labeled["classical_skew_method"] = r["method"]
        labeled["classical_skew_error"] = r["error"]
        labeled_images.append(labeled)

    # Generate report
    report = generate_report(results, args.confidence_threshold)
    report["elapsed_seconds"] = round(elapsed, 1)
    report["images_per_second"] = round(rate, 1)
    print_report(report)

    # Write outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)

    labels_path = args.output_dir / "natural_scan_skew_labels.json"
    labels_data = {
        "version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_images": len(labeled_images),
        "confidence_threshold": args.confidence_threshold,
        "images": labeled_images,
    }
    with open(labels_path, "w") as f:
        json.dump(labels_data, f, indent=2)
    logger.info("Labels written: %s", labels_path)

    report_path = args.output_dir / "skew_labeling_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Report written: %s", report_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
