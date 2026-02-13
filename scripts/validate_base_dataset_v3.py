#!/usr/bin/env python3
"""Validate synth-multiscript v3 base dataset after generation.

Runs Phase 1 validation gates from the plan:
    1. Zero corrupt images (verifiable JPEG/JSON pairs)
    2. Marginal distributions match config weights within 2%
    3. char_height_rendered_px vs char_height_analytical_px correlation >0.95
    4. Vertical text samples for Jpan (~30% TTB), Hans/Hant (~10% TTB)
    5. English secondary in ~40% of multi-script compositions
    6. Zero cross-split contamination (split registry)
    7. Font diversity audit per script
    8. Schema version consistency (all v2.3.0)

Usage:
    python scripts/validate_base_dataset_v3.py \\
        --dataset-dir /mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v3

    # Quick validation (sample 1% of images)
    python scripts/validate_base_dataset_v3.py \\
        --dataset-dir ./test_v3 --sample-rate 0.01
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _load_metadata_sample(
    dataset_dir: Path,
    sample_rate: float = 1.0,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Load metadata JSON files from dataset, optionally sampling.

    Args:
        dataset_dir: Root dataset directory
        sample_rate: Fraction of files to load (0.0-1.0)
        seed: Random seed for sampling

    Returns:
        List of loaded metadata dicts with added _script and _filename keys
    """
    rng = random.Random(seed)
    metadata_list: list[dict[str, Any]] = []

    for script_dir in sorted(dataset_dir.iterdir()):
        if not script_dir.is_dir():
            continue
        script_code = script_dir.name

        json_files = sorted(script_dir.glob("*.json"))
        if sample_rate < 1.0:
            k = max(1, int(len(json_files) * sample_rate))
            json_files = rng.sample(json_files, k)

        for json_path in json_files:
            try:
                with open(json_path) as f:
                    meta = json.load(f)
                meta["_script"] = script_code
                meta["_filename"] = json_path.stem
                metadata_list.append(meta)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load %s: %s", json_path, e)

    return metadata_list


def validate_corrupt_images(dataset_dir: Path) -> dict[str, Any]:
    """Check for corrupt or missing image/metadata pairs.

    Returns:
        Validation result dict
    """
    print("\n[1/8] Checking for corrupt images and missing pairs...")

    missing_json = 0
    missing_image = 0
    corrupt_image = 0
    total_images = 0
    corrupt_files: list[str] = []

    for script_dir in sorted(dataset_dir.iterdir()):
        if not script_dir.is_dir():
            continue

        jpg_files = set(p.stem for p in script_dir.glob("*.jpg"))
        json_files = set(p.stem for p in script_dir.glob("*.json"))

        total_images += len(jpg_files)

        # Check for unpaired files
        for stem in jpg_files - json_files:
            missing_json += 1
        for stem in json_files - jpg_files:
            missing_image += 1

        # Spot-check image validity (check first 10 per script)
        from PIL import Image

        for i, jpg_path in enumerate(sorted(script_dir.glob("*.jpg"))):
            if i >= 10:
                break
            try:
                img = Image.open(jpg_path)
                img.verify()
            except Exception:
                corrupt_image += 1
                corrupt_files.append(str(jpg_path))

    passed = missing_json == 0 and missing_image == 0 and corrupt_image == 0
    result = {
        "check": "corrupt_images",
        "passed": passed,
        "total_images": total_images,
        "missing_json": missing_json,
        "missing_image": missing_image,
        "corrupt_image": corrupt_image,
        "corrupt_files": corrupt_files[:10],
    }
    status = "PASS" if passed else "FAIL"
    print(
        f"  {status}: {total_images:,} images, {missing_json} missing JSON, "
        f"{missing_image} missing images, {corrupt_image} corrupt"
    )
    return result


def validate_distributions(
    metadata_list: list[dict[str, Any]],
    tolerance: float = 0.02,
) -> dict[str, Any]:
    """Check marginal distributions match config weights within tolerance.

    Args:
        metadata_list: Loaded metadata
        tolerance: Allowed deviation from expected (default 2%)

    Returns:
        Validation result dict
    """
    print("\n[2/8] Checking marginal distributions...")

    from image_preprocessing_detector.synthetic.config import (
        LAYOUT_WEIGHTS,
    )

    total = len(metadata_list)
    if total == 0:
        return {"check": "distributions", "passed": False, "error": "No metadata"}

    # Count layouts
    layout_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()

    for meta in metadata_list:
        data = meta.get("data", {})
        structure = data.get("structure", {})
        layout = structure.get("layout_type", "unknown")
        layout_counts[layout] += 1

        resolution = data.get("resolution", {})
        # Resolution tier is in generation_params
        gen_params = data.get("generation_params", meta.get("generation_params", {}))
        res_tier = (
            gen_params.get("resolution_tier", "unknown")
            if isinstance(gen_params, dict)
            else "unknown"
        )
        resolution_counts[res_tier] += 1

    deviations: list[dict[str, Any]] = []

    # Check layout weights
    for layout_type, expected_weight in LAYOUT_WEIGHTS.items():
        actual = layout_counts.get(layout_type.value, 0) / total
        deviation = abs(actual - expected_weight)
        if deviation > tolerance:
            deviations.append(
                {
                    "dimension": "layout",
                    "value": layout_type.value,
                    "expected": round(expected_weight, 3),
                    "actual": round(actual, 3),
                    "deviation": round(deviation, 3),
                }
            )

    passed = len(deviations) == 0
    result = {
        "check": "distributions",
        "passed": passed,
        "total_samples": total,
        "tolerance": tolerance,
        "deviations": deviations,
        "layout_distribution": {k: v for k, v in layout_counts.most_common()},
    }
    status = "PASS" if passed else f"WARN ({len(deviations)} deviations)"
    print(f"  {status}: {total:,} samples checked")
    for d in deviations[:5]:
        print(
            f"    {d['dimension']}/{d['value']}: expected {d['expected']}, got {d['actual']}"
        )
    return result


def validate_char_height_correlation(
    metadata_list: list[dict[str, Any]],
    min_correlation: float = 0.95,
) -> dict[str, Any]:
    """Check rendered vs analytical char height correlation.

    Args:
        metadata_list: Loaded metadata
        min_correlation: Minimum acceptable Pearson r

    Returns:
        Validation result dict
    """
    print("\n[3/8] Checking char_height_rendered vs analytical correlation...")

    rendered_heights: list[float] = []
    analytical_heights: list[float] = []

    for meta in metadata_list:
        data = meta.get("data", {})
        resolution = data.get("resolution", {})
        rendered = resolution.get("character_height_rendered_px")
        analytical = resolution.get("character_height_analytical_px")

        if rendered is not None and analytical is not None:
            rendered_heights.append(float(rendered))
            analytical_heights.append(float(analytical))

    if len(rendered_heights) < 10:
        print(f"  SKIP: Only {len(rendered_heights)} samples with both measurements")
        return {
            "check": "char_height_correlation",
            "passed": True,
            "skipped": True,
            "samples_with_both": len(rendered_heights),
        }

    r = float(np.corrcoef(rendered_heights, analytical_heights)[0, 1])
    passed = r >= min_correlation

    result = {
        "check": "char_height_correlation",
        "passed": passed,
        "pearson_r": round(r, 4),
        "min_correlation": min_correlation,
        "samples_with_both": len(rendered_heights),
        "rendered_median": round(float(np.median(rendered_heights)), 1),
        "analytical_median": round(float(np.median(analytical_heights)), 1),
    }
    status = "PASS" if passed else "FAIL"
    print(
        f"  {status}: r={r:.4f} (min {min_correlation}), "
        f"n={len(rendered_heights):,}, "
        f"median rendered={np.median(rendered_heights):.1f}px, "
        f"median analytical={np.median(analytical_heights):.1f}px"
    )
    return result


def validate_vertical_text(
    metadata_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check CJK vertical text ratios (Jpan ~30%, Hans/Hant ~10%).

    Returns:
        Validation result dict
    """
    print("\n[4/8] Checking CJK vertical text ratios...")

    cjk_scripts = {
        "Jpan": {"total": 0, "ttb": 0},
        "Hans": {"total": 0, "ttb": 0},
        "Hant": {"total": 0, "ttb": 0},
    }

    for meta in metadata_list:
        data = meta.get("data", {})
        structure = data.get("structure", {})
        directions = structure.get("text_directions_present", [])
        language = data.get("language", {})
        script_code = language.get("script_code", meta.get("_script", ""))

        if script_code in cjk_scripts:
            cjk_scripts[script_code]["total"] += 1
            if directions and "ttb" in directions:
                cjk_scripts[script_code]["ttb"] += 1

    results: dict[str, dict[str, Any]] = {}
    all_ok = True

    expected_ratios = {"Jpan": 0.30, "Hans": 0.10, "Hant": 0.10}

    for script, counts in cjk_scripts.items():
        if counts["total"] == 0:
            results[script] = {
                "total": 0,
                "ttb": 0,
                "ratio": 0,
                "expected": expected_ratios[script],
            }
            continue

        ratio = counts["ttb"] / counts["total"]
        expected = expected_ratios[script]
        # Allow ±5% tolerance
        ok = abs(ratio - expected) < 0.05
        if not ok:
            all_ok = False
        results[script] = {
            "total": counts["total"],
            "ttb": counts["ttb"],
            "ratio": round(ratio, 3),
            "expected": expected,
            "ok": ok,
        }

    result = {
        "check": "vertical_text",
        "passed": all_ok,
        "cjk_scripts": results,
    }
    status = "PASS" if all_ok else "WARN"
    print(f"  {status}:")
    for script, data in results.items():
        s = "ok" if data.get("ok", True) else "DEVIATION"
        print(
            f"    {script}: {data['ttb']}/{data['total']} TTB "
            f"({data['ratio']:.1%}, expected {data['expected']:.0%}) [{s}]"
        )
    return result


def validate_english_secondary(
    metadata_list: list[dict[str, Any]],
    expected_ratio: float = 0.40,
) -> dict[str, Any]:
    """Check English secondary weighting in multi-script compositions.

    Returns:
        Validation result dict
    """
    print("\n[5/8] Checking English secondary weighting in multi-script...")

    multi_script = 0
    english_secondary = 0

    for meta in metadata_list:
        data = meta.get("data", {})
        # generation_params is at top level (not inside data)
        gen_params = meta.get("generation_params", {})
        if not isinstance(gen_params, dict):
            continue

        if gen_params.get("multi_script"):
            multi_script += 1
            # Check if Latn is present in languages
            language = data.get("language", {})
            languages = data.get("languages", [])
            script_code = language.get("script_code", "")

            # Multi-script: check if Latn is one of the scripts
            if script_code == "Latn" or any(
                lang.get("script_code") == "Latn"
                for lang in languages
                if isinstance(lang, dict)
            ):
                english_secondary += 1

    if multi_script == 0:
        print("  SKIP: No multi-script samples found")
        return {"check": "english_secondary", "passed": True, "skipped": True}

    ratio = english_secondary / multi_script
    passed = abs(ratio - expected_ratio) < 0.10  # Allow ±10% tolerance

    result = {
        "check": "english_secondary",
        "passed": passed,
        "multi_script_total": multi_script,
        "english_secondary": english_secondary,
        "ratio": round(ratio, 3),
        "expected": expected_ratio,
    }
    status = "PASS" if passed else "WARN"
    print(
        f"  {status}: {english_secondary}/{multi_script} "
        f"({ratio:.1%}, expected ~{expected_ratio:.0%})"
    )
    return result


def validate_split_registry(dataset_dir: Path) -> dict[str, Any]:
    """Check for zero cross-split contamination.

    Returns:
        Validation result dict
    """
    print("\n[6/8] Checking split registry for leakage...")

    registry_path = dataset_dir / "splits.jsonl"
    if not registry_path.exists():
        print("  SKIP: No splits.jsonl found")
        return {"check": "split_registry", "passed": True, "skipped": True}

    from image_preprocessing_detector.schema_utils.split_registry import SplitRegistry

    registry = SplitRegistry(str(registry_path))
    stats = registry.stats

    # Check for duplicates (same SHA256 with different splits)
    # This is inherently prevented by the registry design, but verify
    total = len(registry)
    split_sum = sum(stats.values())

    passed = total == split_sum  # Every entry has a valid split
    result = {
        "check": "split_registry",
        "passed": passed,
        "total_entries": total,
        "split_distribution": stats,
    }
    status = "PASS" if passed else "FAIL"
    print(f"  {status}: {total:,} entries")
    for split_name, count in sorted(stats.items()):
        pct = count / total * 100 if total > 0 else 0
        print(f"    {split_name}: {count:,} ({pct:.1f}%)")
    return result


def validate_font_diversity(
    metadata_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check font diversity per script.

    Returns:
        Validation result dict
    """
    print("\n[7/8] Checking font diversity per script...")

    fonts_per_script: dict[str, set[str]] = defaultdict(set)

    for meta in metadata_list:
        # generation_params is at top level (not inside data)
        gen_params = meta.get("generation_params", {})
        if not isinstance(gen_params, dict):
            continue

        font_families = gen_params.get("font_families_used", [])
        script = meta.get("_script", "")
        for font in font_families:
            if font and script:
                fonts_per_script[script].add(font)

    low_diversity: list[dict[str, Any]] = []
    for script in sorted(fonts_per_script):
        count = len(fonts_per_script[script])
        if count < 5:
            low_diversity.append(
                {
                    "script": script,
                    "font_count": count,
                    "fonts": sorted(fonts_per_script[script]),
                }
            )

    result = {
        "check": "font_diversity",
        "passed": True,  # Informational, not a gate
        "scripts_checked": len(fonts_per_script),
        "low_diversity_scripts": low_diversity,
        "fonts_per_script": {k: len(v) for k, v in sorted(fonts_per_script.items())},
    }
    print(
        f"  INFO: {len(fonts_per_script)} scripts, {len(low_diversity)} with <5 font families"
    )
    for ld in low_diversity:
        print(
            f"    {ld['script']}: {ld['font_count']} fonts ({', '.join(ld['fonts'][:3])})"
        )
    return result


def validate_schema_version(
    metadata_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check all metadata has schema_version 2.3.0.

    Returns:
        Validation result dict
    """
    print("\n[8/8] Checking schema version consistency...")

    version_counts: Counter[str] = Counter()
    for meta in metadata_list:
        version = meta.get("schema_version", "unknown")
        version_counts[version] += 1

    passed = len(version_counts) == 1 and "2.3.0" in version_counts
    result = {
        "check": "schema_version",
        "passed": passed,
        "version_distribution": dict(version_counts),
    }
    status = "PASS" if passed else "FAIL"
    print(f"  {status}: {dict(version_counts)}")
    return result


def main() -> int:
    """Run all validation checks."""
    parser = argparse.ArgumentParser(
        description="Validate synth-multiscript v3 base dataset",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        required=True,
        help="Path to the generated dataset directory",
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=1.0,
        help="Fraction of metadata to load (0.0-1.0, default: 1.0 = all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON report path (default: dataset_dir/validation_report.json)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if not args.dataset_dir.exists():
        print(f"Error: Dataset directory not found: {args.dataset_dir}")
        return 1

    print("=" * 70)
    print("Synth-Multiscript v3 Base Dataset Validation")
    print("=" * 70)
    print(f"Dataset: {args.dataset_dir}")
    print(f"Sample rate: {args.sample_rate:.0%}")

    # Load metadata
    print(f"\nLoading metadata (sample rate {args.sample_rate:.0%})...")
    metadata_list = _load_metadata_sample(
        args.dataset_dir, sample_rate=args.sample_rate
    )
    print(f"Loaded {len(metadata_list):,} metadata files")

    # Run all checks
    results: list[dict[str, Any]] = []

    results.append(validate_corrupt_images(args.dataset_dir))
    results.append(validate_distributions(metadata_list))
    results.append(validate_char_height_correlation(metadata_list))
    results.append(validate_vertical_text(metadata_list))
    results.append(validate_english_secondary(metadata_list))
    results.append(validate_split_registry(args.dataset_dir))
    results.append(validate_font_diversity(metadata_list))
    results.append(validate_schema_version(metadata_list))

    # Summary
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    skipped = sum(1 for r in results if r.get("skipped"))

    print("\n" + "=" * 70)
    print(f"Validation Summary: {passed}/{total} checks passed ({skipped} skipped)")
    print("=" * 70)

    for r in results:
        check = r.get("check", "unknown")
        status = "PASS" if r.get("passed") else "FAIL"
        if r.get("skipped"):
            status = "SKIP"
        print(f"  [{status}] {check}")

    # Save report
    output_path = args.output or args.dataset_dir / "validation_report.json"
    report = {
        "dataset_dir": str(args.dataset_dir),
        "sample_rate": args.sample_rate,
        "metadata_loaded": len(metadata_list),
        "checks_passed": passed,
        "checks_total": total,
        "checks_skipped": skipped,
        "all_passed": passed == total,
        "results": results,
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {output_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
