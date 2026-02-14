#!/usr/bin/env python3
"""Benchmark HandwritingDetector against COCO-Text handwriting annotations.

COCO-Text provides per-annotation `class` labels: "machine printed" or "handwritten".
An image is labeled handwriting-positive if ANY annotation is "handwritten".

CAVEAT: COCO-Text is scene text (outdoor signs), not documents. Only 5 images
have handwritten annotations (29 out of 201K annotations). Results have
limited statistical significance and may not transfer to document handwriting.

Usage:
    python scripts/benchmarks/bench_handwriting.py \
        --data-dir /mnt/e/image_detection \
        --output-dir results/stream3_benchmarks \
        --max-negative 200 \
        --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from image_preprocessing_detector.detection.handwriting_detector import (
    HandwritingDetector,
)

from scripts.benchmarks.classification_metrics import (
    collect_system_info,
    compute_binary_report,
    compute_latency_stats,
    save_benchmark_result,
)
from scripts.benchmarks.stream3_config import (
    THRESHOLDS,
    ensure_output_dir,
)

logger = logging.getLogger(__name__)

MAX_IMAGE_DIM = 800


def load_cocotext_samples(
    data_dir: Path,
    max_negative: int,
    seed: int,
) -> list[tuple[Path, int]]:
    """Load COCO-Text images with binary handwriting labels.

    Positive: images with at least one "handwritten" annotation.
    Negative: images with only "machine printed" annotations (subsampled).

    Args:
        data_dir: Root data directory.
        max_negative: Maximum negative samples to include.
        seed: Random seed.

    Returns:
        List of (image_path, label) where 1=has_handwriting, 0=machine_only.
    """
    cocotext_root = data_dir / "01_base_data" / "text_detection" / "cocotext"
    ann_file = cocotext_root / "cocotext.v2.json"
    images_dir = cocotext_root / "images"

    if not ann_file.exists():
        msg = f"COCO-Text annotations not found at {ann_file}"
        raise FileNotFoundError(msg)

    with open(ann_file) as fh:
        data = json.load(fh)

    # Classify images by handwriting presence
    hw_image_ids: set[int] = set()
    mp_only_image_ids: set[int] = set()

    for ann_id, ann in data["anns"].items():
        img_id = ann["image_id"]
        if ann.get("class") == "handwritten":
            hw_image_ids.add(img_id)

    # Find machine-printed-only images (have annotations but no handwriting)
    for img_id_str, ann_ids in data["imgToAnns"].items():
        img_id = int(img_id_str)
        if img_id not in hw_image_ids and ann_ids:
            mp_only_image_ids.add(img_id)

    logger.info(
        "COCO-Text: %d handwriting images, %d machine-printed-only images",
        len(hw_image_ids), len(mp_only_image_ids),
    )

    # Map image IDs to filenames
    def img_id_to_path(img_id: int) -> Path | None:
        img_info = data["imgs"].get(str(img_id))
        if img_info is None:
            return None
        # COCO-Text v2 uses image_id to construct filename
        filename = img_info.get("file_name")
        if not filename:
            filename = f"COCO_train2014_{img_id:012d}.jpg"
        # Try direct path first, then subdirectories (train2014/, val2014/)
        path = images_dir / filename
        if path.exists():
            return path
        for subdir in ("train2014", "val2014"):
            path = images_dir / subdir / filename
            if path.exists():
                return path
        return None

    samples: list[tuple[Path, int]] = []

    # All handwriting-positive images
    for img_id in hw_image_ids:
        path = img_id_to_path(img_id)
        if path is not None:
            samples.append((path, 1))

    # Subsample machine-printed-only
    rng = np.random.default_rng(seed)
    mp_list = sorted(mp_only_image_ids)
    if len(mp_list) > max_negative:
        idx = rng.choice(len(mp_list), size=max_negative, replace=False)
        mp_list = [mp_list[i] for i in sorted(idx)]

    for img_id in mp_list:
        path = img_id_to_path(img_id)
        if path is not None:
            samples.append((path, 0))

    logger.info("Loaded %d samples (%d positive, %d negative)",
                len(samples),
                sum(1 for _, l in samples if l == 1),
                sum(1 for _, l in samples if l == 0))

    return samples


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    max_negative: int,
    seed: int,
) -> dict:
    """Run the handwriting detection benchmark.

    Args:
        data_dir: Root data directory.
        output_dir: Output directory.
        max_negative: Maximum negative samples.
        seed: Random seed.

    Returns:
        Benchmark result dictionary.
    """
    print("=" * 60)
    print("Stream 3 Benchmark: Handwriting Detection (COCO-Text)")
    print("=" * 60)
    print("CAVEAT: COCO-Text is scene text, not documents.")
    print("Only ~5 images have handwritten annotations.\n")

    samples = load_cocotext_samples(data_dir, max_negative, seed)
    if not samples:
        msg = "No COCO-Text samples found"
        raise RuntimeError(msg)

    num_positive = sum(1 for _, l in samples if l == 1)
    num_negative = sum(1 for _, l in samples if l == 0)
    print(f"Evaluating {len(samples)} images ({num_positive} hw+, {num_negative} hw-)...")

    if num_positive < 5:
        print(f"\nWARNING: Only {num_positive} positive samples. Results have very limited statistical significance.")

    detector = HandwritingDetector()
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(samples))
    samples = [samples[i] for i in perm]

    y_true: list[int] = []
    y_pred: list[int] = []
    y_scores: list[float] = []
    latencies_ms: list[float] = []
    failures = 0

    for idx, (img_path, gt_label) in enumerate(samples):
        if (idx + 1) % 50 == 0:
            print(f"  Progress: {idx + 1}/{len(samples)}")

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

        start = time.perf_counter()
        result = detector.detect(img)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)

        pred_label = 1 if result.has_handwriting else 0
        y_true.append(gt_label)
        y_pred.append(pred_label)
        y_scores.append(result.handwriting_score)

    print(f"\nProcessed {len(samples)} images ({failures} failed to load)")

    report = compute_binary_report(y_true, y_pred, y_scores=y_scores)
    print(f"\nBinary accuracy: {report['accuracy']:.1%}")
    print(f"F1: {report['f1']:.4f}")
    print(f"TP={report['tp']}, FP={report['fp']}, TN={report['tn']}, FN={report['fn']}")

    latency = compute_latency_stats(latencies_ms)

    # Go/No-Go (with caveat about limited samples)
    threshold = THRESHOLDS["handwriting"]
    metric_value = report[threshold.metric]
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"
    reliable = num_positive >= 20

    mark = "PASS" if threshold_met else "FAIL"
    reliability = "" if reliable else " (UNRELIABLE - too few positive samples)"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target){reliability}")

    result_dict: dict[str, Any] = {
        "detector": "HandwritingDetector",
        "dataset": "cocotext",
        "num_samples": len(samples),
        "num_positive": num_positive,
        "num_negative": num_negative,
        "caveat": "COCO-Text is scene text (outdoor signs), not documents. "
                  f"Only {num_positive} positive samples - results have limited statistical significance.",
        "metrics": report,
        "latency": latency,
        "failure_rate": round(failures / len(samples), 4) if samples else 0.0,
        "threshold": {
            "target": threshold.target,
            "metric": threshold.metric,
            "met": threshold_met,
            "reliable": reliable,
        },
        "go_nogo": go_nogo,
        "system_info": collect_system_info(),
    }

    out_dir = ensure_output_dir(output_dir)
    saved_path = save_benchmark_result(result_dict, out_dir, "handwriting")
    print(f"\nResults saved to {saved_path}")

    return result_dict


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark HandwritingDetector against COCO-Text"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("/mnt/e/image_detection"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/stream3_benchmarks"))
    parser.add_argument("--max-negative", type=int, default=200, help="Max negative samples")
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        run_benchmark(args.data_dir, args.output_dir, args.max_negative, args.seed)
    except FileNotFoundError as exc:
        print(f"\nDataset not found: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
