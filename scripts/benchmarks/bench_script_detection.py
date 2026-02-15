#!/usr/bin/env python3
"""Benchmark ScriptDetectorHeuristic against MLT-2019 and IndicDLP.

Primary: MLT-2019 (7 scripts: Arab, Beng, Deva, Hans, Jpan, Kore, Latn).
Supplementary: IndicDLP (12 Indic languages across 8 scripts + Latin).

Reports family-level (5-class) and ISO-level classification accuracy with
Go/No-Go decision based on MLT-2019 results. IndicDLP results are
supplementary and do not affect the Go/No-Go threshold.

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
from typing import Any

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

# IndicDLP: map ISO 639-1 language codes (from filenames) to ISO 15924 scripts
_INDICDLP_LANG_TO_ISO: dict[str, str] = {
    "as": "Beng",  # Assamese -> Bengali script
    "bn": "Beng",  # Bengali -> Bengali script
    "en": "Latn",  # English -> Latin script
    "gu": "Gujr",  # Gujarati -> Gujarati script
    "hi": "Deva",  # Hindi -> Devanagari
    "kn": "Knda",  # Kannada -> Kannada script
    "ml": "Mlym",  # Malayalam -> Malayalam script
    "mr": "Deva",  # Marathi -> Devanagari
    "or": "Orya",  # Odia -> Odia script
    "pa": "Guru",  # Punjabi -> Gurmukhi script
    "ta": "Taml",  # Tamil -> Tamil script
    "te": "Telu",  # Telugu -> Telugu script
}

# Extended ISO-to-family mapping (adds Indic scripts to base mapping)
_ISO_TO_FAMILY_EXTENDED: dict[str, str] = {
    **_ISO_TO_FAMILY,
    "Gujr": "devanagari",  # Brahmic scripts -> devanagari family
    "Knda": "devanagari",
    "Mlym": "devanagari",
    "Orya": "devanagari",
    "Guru": "devanagari",
    "Taml": "devanagari",
    "Telu": "devanagari",
}

# IndicDLP ISO codes present in the dataset
INDICDLP_ISO_NAMES = [
    "Beng",
    "Deva",
    "Gujr",
    "Guru",
    "Knda",
    "Latn",
    "Mlym",
    "Orya",
    "Taml",
    "Telu",
]

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


def load_indicdlp_samples(
    data_dir: Path,
    max_samples: int,
    seed: int,
) -> list[tuple[Path, str]]:
    """Load IndicDLP test images with script labels derived from filenames.

    IndicDLP filenames encode language as the second underscore-separated
    component (e.g., ``ar_en_000027_0.png`` -> ``en`` = English = Latn).

    Args:
        data_dir: Root data directory.
        max_samples: Maximum number of samples (0 = all).
        seed: Random seed for reproducible subsampling.

    Returns:
        List of (image_path, gt_iso_code) tuples.
    """
    indicdlp_root = data_dir / "01_base_data" / "layout" / "indicdlp"
    images_dir = indicdlp_root / "images" / "test"

    if not images_dir.exists():
        logger.info("IndicDLP test images not found at %s - skipping", images_dir)
        return []

    samples: list[tuple[Path, str]] = []
    for img_path in sorted(images_dir.glob("*.png")):
        parts = img_path.stem.split("_")
        if len(parts) < 2:
            continue
        lang_code = parts[1]
        iso_code = _INDICDLP_LANG_TO_ISO.get(lang_code)
        if iso_code is not None:
            samples.append((img_path, iso_code))

    logger.info("Found %d valid IndicDLP test samples", len(samples))

    if max_samples > 0 and len(samples) > max_samples:
        rng = np.random.default_rng(seed)
        indices = rng.choice(len(samples), size=max_samples, replace=False)
        indices.sort()
        samples = [samples[i] for i in indices]
        logger.info("Subsampled to %d samples", len(samples))

    return samples


def evaluate_script_samples(
    detector: ScriptDetectorHeuristic,
    samples: list[tuple[Path, str]],
    family_names: list[str],
    iso_names: list[str],
    iso_to_family: dict[str, str],
    progress_interval: int = 500,
) -> dict[str, Any]:
    """Run script detection on a set of samples and compute metrics.

    Shared evaluation logic used by both MLT-2019 and IndicDLP.

    Args:
        detector: Initialized script detector.
        samples: List of (image_path, gt_iso_code) tuples.
        family_names: Family class names for classification report.
        iso_names: ISO class names for classification report.
        iso_to_family: ISO-to-family mapping dict.
        progress_interval: Print progress every N images.

    Returns:
        Dict with family_report, iso_report (optional), latency, failures,
        and per_language breakdown.
    """
    family_true: list[int] = []
    family_pred: list[int] = []
    iso_true: list[int] = []
    iso_pred: list[int] = []
    latencies_ms: list[float] = []
    failures = 0
    per_lang_correct: dict[str, int] = {}
    per_lang_total: dict[str, int] = {}

    for idx, (img_path, gt_iso) in enumerate(samples):
        if (idx + 1) % progress_interval == 0:
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

        pred_iso = result.detected_script

        # Family-level
        gt_family = iso_to_family.get(gt_iso, "unknown")
        pred_family = iso_to_family.get(pred_iso, "unknown")
        gt_family_idx = (
            family_names.index(gt_family)
            if gt_family in family_names
            else family_names.index("unknown")
        )
        pred_family_idx = (
            family_names.index(pred_family)
            if pred_family in family_names
            else family_names.index("unknown")
        )
        family_true.append(gt_family_idx)
        family_pred.append(pred_family_idx)

        # ISO-level
        if gt_iso in iso_names:
            iso_true.append(iso_names.index(gt_iso))
            if pred_iso in iso_names:
                iso_pred.append(iso_names.index(pred_iso))
            else:
                # Map to closest ISO in same family
                pred_fam = iso_to_family.get(pred_iso, "unknown")
                fallback = next(
                    (
                        iso
                        for iso, fam in iso_to_family.items()
                        if fam == pred_fam and iso in iso_names
                    ),
                    None,
                )
                if fallback is not None:
                    iso_pred.append(iso_names.index(fallback))
                else:
                    iso_true.pop()

        # Per-language tracking
        per_lang_total[gt_iso] = per_lang_total.get(gt_iso, 0) + 1
        if gt_family == pred_family:
            per_lang_correct[gt_iso] = per_lang_correct.get(gt_iso, 0) + 1

    family_report = compute_classification_report(
        family_true, family_pred, family_names
    )
    iso_report = None
    if iso_true:
        iso_report = compute_classification_report(iso_true, iso_pred, iso_names)

    latency = compute_latency_stats(latencies_ms)

    per_language: dict[str, dict[str, Any]] = {}
    for lang_iso in sorted(per_lang_total):
        total = per_lang_total[lang_iso]
        correct = per_lang_correct.get(lang_iso, 0)
        per_language[lang_iso] = {
            "accuracy": round(correct / total, 4) if total > 0 else 0.0,
            "correct": correct,
            "total": total,
        }

    return {
        "family_report": family_report,
        "iso_report": iso_report,
        "latency": latency,
        "failures": failures,
        "per_language": per_language,
    }


def run_benchmark(
    data_dir: Path,
    output_dir: Path,
    max_samples: int,
    seed: int,
) -> dict[str, Any]:
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
    print("Stream 3 Benchmark: Script Detection (MLT-2019 + IndicDLP)")
    print("=" * 60)

    # Load MLT-2019 samples
    samples = load_mlt19_samples(data_dir, max_samples, seed)
    if not samples:
        msg = "No valid MLT-2019 samples found"
        raise RuntimeError(msg)

    print(f"\n--- MLT-2019: {len(samples)} images ---")

    # Initialize detector (shared across both datasets)
    detector = ScriptDetectorHeuristic(min_components=10)

    # Evaluate on MLT-2019 (primary)
    mlt19_eval = evaluate_script_samples(
        detector,
        samples,
        FAMILY_NAMES,
        ISO_NAMES,
        _ISO_TO_FAMILY,
        progress_interval=200,
    )

    family_report = mlt19_eval["family_report"]
    iso_report = mlt19_eval["iso_report"]
    latency = mlt19_eval["latency"]

    print(f"\nMLT-2019 Family-level accuracy: {family_report['accuracy']:.1%}")
    print(f"MLT-2019 Family-level macro F1: {family_report['macro_f1']:.4f}")
    if iso_report:
        print(f"MLT-2019 ISO-level accuracy: {iso_report['accuracy']:.1%}")
    print(f"Latency: mean={latency['mean_ms']:.1f}ms, p95={latency['p95_ms']:.1f}ms")

    # Go/No-Go decision (based on MLT-2019 only)
    threshold = THRESHOLDS["script_detection"]
    metric_value = family_report[threshold.metric]
    threshold_met = metric_value >= threshold.target
    go_nogo = "PASS" if threshold_met else "UPGRADE_ML"

    mark = "PASS" if threshold_met else "FAIL"
    print(f"\nGo/No-Go: {mark} ({metric_value:.1%} vs {threshold.target:.0%} target)")
    if not threshold_met:
        print(f"  Action: {threshold.ml_action}")

    # Compile MLT-2019 result
    result_dict: dict[str, Any] = {
        "detector": "ScriptDetectorHeuristic",
        "dataset": "mlt19",
        "timestamp": "",
        "num_samples": len(samples),
        "metrics": {
            "family_level": family_report,
        },
        "latency": latency,
        "failure_rate": round(mlt19_eval["failures"] / len(samples), 4)
        if samples
        else 0.0,
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

    # --- IndicDLP supplementary evaluation ---
    indicdlp_samples = load_indicdlp_samples(data_dir, max_samples=5000, seed=seed)
    if indicdlp_samples:
        print(f"\n--- IndicDLP (supplementary): {len(indicdlp_samples)} images ---")

        indicdlp_eval = evaluate_script_samples(
            detector,
            indicdlp_samples,
            FAMILY_NAMES,
            INDICDLP_ISO_NAMES,
            _ISO_TO_FAMILY_EXTENDED,
            progress_interval=500,
        )

        indic_family = indicdlp_eval["family_report"]
        indic_iso = indicdlp_eval["iso_report"]
        indic_latency = indicdlp_eval["latency"]

        print(f"\nIndicDLP Family-level accuracy: {indic_family['accuracy']:.1%}")
        print(f"IndicDLP Family-level macro F1: {indic_family['macro_f1']:.4f}")
        if indic_iso:
            print(f"IndicDLP ISO-level accuracy: {indic_iso['accuracy']:.1%}")
        print(
            f"Latency: mean={indic_latency['mean_ms']:.1f}ms, p95={indic_latency['p95_ms']:.1f}ms"
        )

        # Per-language breakdown
        per_lang = indicdlp_eval["per_language"]
        if per_lang:
            print("\nPer-language family accuracy:")
            for lang_iso, stats in sorted(per_lang.items()):
                print(
                    f"  {lang_iso}: {stats['accuracy']:.1%} ({stats['correct']}/{stats['total']})"
                )

        indicdlp_metrics: dict[str, Any] = {
            "family_level": indic_family,
        }
        if indic_iso is not None:
            indicdlp_metrics["iso_level"] = indic_iso

        result_dict["supplementary_indicdlp"] = {
            "dataset": "indicdlp",
            "num_samples": len(indicdlp_samples),
            "note": "Supplementary evaluation on 12 Indic languages. "
            "Does NOT affect Go/No-Go decision.",
            "metrics": indicdlp_metrics,
            "latency": indic_latency,
            "failure_rate": round(indicdlp_eval["failures"] / len(indicdlp_samples), 4),
            "per_language": per_lang,
        }
    else:
        print("\nIndicDLP not found - skipping supplementary evaluation")

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
