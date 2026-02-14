#!/usr/bin/env python3
"""Benchmark ScriptDetectorHeuristic against MLT-2019 ground truth.

Evaluates the heuristic script detector on real multilingual scene text images
from ICDAR 2019 MLT. Reports family-level (5-class) and ISO-level (7-class)
classification accuracy with Go/No-Go decision.

Usage:
    python scripts/benchmarks/bench_script_detection.py \
        --data-dir /mnt/e/image_detection \
        --output-dir results/stream3_benchmarks \
        --max-samples 2000 \
        --seed 42
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from image_preprocessing_detector.detection.script_detector import (
    ScriptDetectorHeuristic,
)

from scripts.benchmarks.classification_metrics import (
    collect_system_info,
    compute_classification_report,
    compute_latency_stats,
    save_benchmark_result,
)
from scripts.benchmarks.stream3_config import (
    THRESHOLDS,
    ensure_output_dir,
)

logger = logging.getLogger(__name__)

# Map MLT-2019 GT language labels to ISO 15924 script codes
_GT_LANGUAGE_TO_ISO: dict[str, str] = {
    "Arabic": "Arab",
    "Bangla": "Beng",
    "Chinese": "Hans",
    "Japanese": "Jpan",
    "Korean": "Kore",
    "Latin": "Latn",
    "Hindi": "Deva",
    "Devanagari": "Deva",
}

# Map ISO 15924 codes to heuristic script families (5-class)
_ISO_TO_FAMILY: dict[str, str] = {
    "Hans": "cjk",
    "Jpan": "cjk",
    "Kore": "cjk",
    "Latn": "latin",
    "Arab": "arabic",
    "Deva": "devanagari",
    "Beng": "devanagari",
    "Zzzz": "unknown",
}

FAMILY_NAMES = ["cjk", "latin", "arabic", "devanagari", "unknown"]
ISO_NAMES = ["Arab", "Beng", "Deva", "Hans", "Jpan", "Kore", "Latn"]

# Maximum image dimension before resizing (for speed)
MAX_IMAGE_DIM = 800


def parse_gt_file(gt_path: Path) -> str | None:
    """Extract the dominant script from an MLT-2019 ground truth file.

    Reads all annotation lines and returns the most frequent language label
    as an ISO 15924 script code.

    Args:
        gt_path: Path to the GT text file.

    Returns:
        ISO 15924 code of the dominant script, or None if no valid labels found.
    """
    if not gt_path.exists():
        return None

    language_counts: Counter[str] = Counter()
    try:
        text = gt_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    for line in text.strip().splitlines():
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        language = parts[8].strip()
        if language in _GT_LANGUAGE_TO_ISO:
            language_counts[language] += 1

    if not language_counts:
        return None

    dominant_language = language_counts.most_common(1)[0][0]
    return _GT_LANGUAGE_TO_ISO[dominant_language]


def load_mlt19_samples(
    data_dir: Path,
    max_samples: int,
    seed: int,
) -> list[tuple[Path, str]]:
    """Load MLT-2019 image paths with their dominant GT script codes.

    Args:
        data_dir: Root data directory (e.g., /mnt/e/image_detection).
        max_samples: Maximum number of samples (0 = all).
        seed: Random seed for reproducible subsampling.

    Returns:
        List of (image_path, gt_iso_code) tuples.

    Raises:
        FileNotFoundError: If dataset directory does not exist.
    """
    mlt19_root = data_dir / "01_base_data" / "language" / "mlt19"
    images_dir = mlt19_root / "TrainImages" / "TrainImages"
    gt_dir = mlt19_root / "TrainGT" / "TrainGT"

    if not images_dir.exists():
        msg = f"MLT-2019 images not found at {images_dir}"
        raise FileNotFoundError(msg)

    if not gt_dir.exists():
        msg = f"MLT-2019 ground truth not found at {gt_dir}"
        raise FileNotFoundError(msg)

    # Collect all valid image-GT pairs
    samples: list[tuple[Path, str]] = []
    for img_path in sorted(images_dir.glob("*.jpg")):
        gt_path = gt_dir / img_path.with_suffix(".txt").name
        gt_iso = parse_gt_file(gt_path)
        if gt_iso is not None:
            samples.append((img_path, gt_iso))

    logger.info("Found %d valid MLT-2019 samples", len(samples))

    # Subsample if requested
    if max_samples > 0 and len(samples) > max_samples:
        rng = np.random.default_rng(seed)
        indices = rng.choice(len(samples), size=max_samples, replace=False)
        indices.sort()
        samples = [samples[i] for i in indices]
        logger.info("Subsampled to %d samples", len(samples))

    return samples


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    max_samples: int,
    seed: int,
) -> dict:
    """Run the script detection benchmark.

    Args:
        data_dir: Root data directory.
        output_dir: Directory to write results to.
        max_samples: Maximum samples to evaluate (0 = all).
        seed: Random seed for subsampling.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Script Detection (MLT-2019)")
    print("=" * 60)

    # Load samples
    samples = load_mlt19_samples(data_dir, max_samples, seed)
    if not samples:
        msg = "No valid samples found"
        raise RuntimeError(msg)

    print(f"Evaluating {len(samples)} images...")

    # Initialize detector
    detector = ScriptDetectorHeuristic(min_components=10)

    # Run evaluation
    family_true: list[int] = []
    family_pred: list[int] = []
    iso_true: list[int] = []
    iso_pred: list[int] = []
    latencies_ms: list[float] = []
    failures = 0

    for idx, (img_path, gt_iso) in enumerate(samples):
        if (idx + 1) % 200 == 0:
            print(f"  Progress: {idx + 1}/{len(samples)}")

        # Load and resize image
        img = cv2.imread(str(img_path))
        if img is None:
            failures += 1
            continue

        height, width = img.shape[:2]
        if max(height, width) > MAX_IMAGE_DIM:
            scale = MAX_IMAGE_DIM / max(height, width)
            img = cv2.resize(
                img,
                (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        # Detect script
        start = time.perf_counter()
        result = detector.detect(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        pred_iso = result.detected_script

        # Map to family space (5-class)
        gt_family = _ISO_TO_FAMILY.get(gt_iso, "unknown")
        pred_family = _ISO_TO_FAMILY.get(pred_iso, "unknown")

        gt_family_idx = FAMILY_NAMES.index(gt_family)
        pred_family_idx = FAMILY_NAMES.index(pred_family)
        family_true.append(gt_family_idx)
        family_pred.append(pred_family_idx)

        # Map to ISO space (7-class) - only if both are in the known set
        if gt_iso in ISO_NAMES and pred_iso in ISO_NAMES:
            iso_true.append(ISO_NAMES.index(gt_iso))
            iso_pred.append(ISO_NAMES.index(pred_iso))
        elif gt_iso in ISO_NAMES:
            # GT is known but prediction is unknown - count as ISO evaluation
            iso_true.append(ISO_NAMES.index(gt_iso))
            # Map prediction to closest ISO code in same family
            pred_family_iso = _ISO_TO_FAMILY.get(pred_iso, "unknown")
            # Use first ISO code in same family as fallback
            fallback_iso = next(
                (iso for iso, fam in _ISO_TO_FAMILY.items() if fam == pred_family_iso and iso in ISO_NAMES),
                None,
            )
            if fallback_iso is not None:
                iso_pred.append(ISO_NAMES.index(fallback_iso))
            else:
                # Drop this sample from ISO evaluation
                iso_true.pop()

    print(f"\nProcessed {len(samples)} images ({failures} failed to load)")

    # Compute family-level metrics (primary)
    family_report = compute_classification_report(family_true, family_pred, FAMILY_NAMES)
    print(f"\nFamily-level accuracy: {family_report['accuracy']:.1%}")
    print(f"Family-level macro F1: {family_report['macro_f1']:.4f}")

    # Compute ISO-level metrics (detailed)
    iso_report = None
    if iso_true:
        iso_report = compute_classification_report(iso_true, iso_pred, ISO_NAMES)
        print(f"\nISO-level accuracy: {iso_report['accuracy']:.1%}")

    # Latency stats
    latency = compute_latency_stats(latencies_ms)
    print(f"\nLatency: mean={latency['mean_ms']:.1f}ms, p95={latency['p95_ms']:.1f}ms")

    # Go/No-Go decision
    threshold = THRESHOLDS["script_detection"]
    metric_value = family_report[threshold.metric]
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"

    mark = "PASS" if threshold_met else "FAIL"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target)")
    if not threshold_met:
        print(f"  Action: {threshold.ml_action}")

    # Compile result
    result_dict = {
        "detector": "ScriptDetectorHeuristic",
        "dataset": "mlt19",
        "timestamp": "",  # filled by save_benchmark_result filename
        "num_samples": len(samples),
        "metrics": {
            "family_level": family_report,
        },
        "latency": latency,
        "failure_rate": round(failures / len(samples), 4) if samples else 0.0,
        "threshold": {
            "target": threshold.target,
            "metric": threshold.metric,
            "met": threshold_met,
        },
        "go_nogo": go_nogo,
        "system_info": collect_system_info(),
    }
    if iso_report is not None:
        result_dict["metrics"]["iso_level"] = iso_report

    # Save
    out_dir = ensure_output_dir(output_dir)
    saved_path = save_benchmark_result(result_dict, out_dir, "script_detection")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark ScriptDetectorHeuristic against MLT-2019"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/mnt/e/image_detection"),
        help="Root data directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/stream3_benchmarks"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=2000,
        help="Maximum samples to evaluate (0 = all)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for subsampling",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        run_benchmark(args.data_dir, args.output_dir, args.max_samples, args.seed)
    except FileNotFoundError as exc:
        print(f"\nDataset not found: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
