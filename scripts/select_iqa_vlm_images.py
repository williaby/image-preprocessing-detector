#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Select stratified image samples for VLM IQA labeling (Phase 1).

Selects images from DIQA-5000 and OHR-Bench using stratified sampling
to ensure quality diversity. Outputs a manifest JSON with image paths
and existing MOS scores for cross-validation.

Stratification Strategy:
  - DIQA-5000: 5 MOS quintiles x capture_type (ori/res) = 10 strata
  - OHR-Bench: 5 quality quintiles x category bins = variable strata

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/select_iqa_vlm_images.py

    # Pilot mode (200 images for validation):
    PYTHONPATH=... uv run python3 scripts/select_iqa_vlm_images.py \
        --target-count 200 --output vlm_pilot_manifest.json

    # Full scale (2000 images):
    PYTHONPATH=... uv run python3 scripts/select_iqa_vlm_images.py \
        --target-count 2000 --output vlm_full_manifest.json

    # DIQA-5000 only:
    PYTHONPATH=... uv run python3 scripts/select_iqa_vlm_images.py \
        --diqa-only --target-count 500
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
DIQA_METADATA_PATH = REGISTRY_DIR / "json" / "diqa-5000_metadata.json"
DIQA_DATASET_DIR = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
OHRBENCH_DATASET_DIR = Path("/mnt/e/image_detection/02_benchmark_only/ohr-bench")
OUTPUT_DIR = Path("results/iqa_vlm_labeling")


def _assign_quintiles(
    samples: list[dict[str, Any]], value_key: str, quintile_key: str
) -> None:
    """Assign quintile labels (1-5) to samples in-place based on a numeric field."""
    values = [s[value_key] for s in samples]
    edges = np.quantile(values, [0.2, 0.4, 0.6, 0.8])
    for sample in samples:
        # np.searchsorted returns 0-3 for values <= edges, so add 1 for 1-indexed quintile
        sample[quintile_key] = (
            int(np.searchsorted(edges, sample[value_key], side="right")) + 1
        )


def load_diqa5000_for_selection(
    metadata_path: Path,
    splits: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load DIQA-5000 metadata for stratified selection.

    Returns list of dicts with: id, path, split, mos_overall, mos_sharpness,
    mos_color_fidelity, capture_type, mos_quintile.
    """
    if splits is None:
        splits = ["train", "val", "test"]

    log.info("Loading DIQA-5000 metadata from %s", metadata_path)
    with open(metadata_path) as fh:
        metadata = json.load(fh)

    samples = []
    for sample in metadata.get("samples", []):
        original_labels = sample.get("original_labels", {})
        source = sample.get("source", {})

        mos_overall = original_labels.get("mos_overall")
        if mos_overall is None:
            continue

        split = source.get("split", "unknown")
        if split not in splits:
            continue

        rel_path = source.get("original_path", "")
        capture_type = "ori" if "/ori/" in rel_path else "res"

        samples.append(
            {
                "id": sample.get("id", ""),
                "dataset": "diqa-5000",
                "path": rel_path,
                "abs_path": str(DIQA_DATASET_DIR / rel_path),
                "split": split,
                "mos_overall": float(mos_overall),
                "mos_sharpness": float(original_labels.get("mos_sharpness", 0)),
                "mos_color_fidelity": float(
                    original_labels.get("mos_color_fidelity", 0)
                ),
                "capture_type": capture_type,
            }
        )

    _assign_quintiles(samples, "mos_overall", "mos_quintile")

    log.info("Loaded %d DIQA-5000 samples (splits: %s)", len(samples), splits)
    return samples


def stratified_select_diqa(
    samples: list[dict[str, Any]],
    target_count: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Select stratified sample from DIQA-5000.

    Stratifies by MOS quintile x capture_type (ori/res) = 10 strata.
    Equal allocation across strata (floor division + remainder to lowest strata).
    """
    rng = np.random.default_rng(seed)

    # Group into strata
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        key = f"q{s['mos_quintile']}_{s['capture_type']}"
        strata[key].append(s)

    log.info("DIQA-5000 strata distribution:")
    for key in sorted(strata):
        log.info("  %s: %d images", key, len(strata[key]))

    # Allocate per stratum
    num_strata = len(strata)
    per_stratum = target_count // num_strata
    remainder = target_count % num_strata

    selected: list[dict[str, Any]] = []
    for idx, (key, stratum_samples) in enumerate(sorted(strata.items())):
        n = per_stratum + (1 if idx < remainder else 0)
        n = min(n, len(stratum_samples))

        indices = rng.choice(len(stratum_samples), size=n, replace=False)
        for i in indices:
            selected.append(stratum_samples[i])

    log.info("Selected %d DIQA-5000 images across %d strata", len(selected), num_strata)
    return selected


def load_ohrbench_for_selection(
    dataset_dir: Path,
) -> list[dict[str, Any]]:
    """Load OHR-Bench samples for stratified selection."""
    log.info("Loading OHR-Bench from %s", dataset_dir)
    try:
        from datasets import load_from_disk

        ds = load_from_disk(str(dataset_dir))
        samples = []
        for idx, item in enumerate(ds):
            quality = item.get("quality_score")
            if quality is None:
                continue
            samples.append(
                {
                    "id": f"ohrbench_{idx:05d}",
                    "dataset": "ohr-bench",
                    "index": idx,
                    "quality_score": float(quality),
                    "category": item.get("category", "unknown"),
                }
            )

        _assign_quintiles(samples, "quality_score", "quality_quintile")

        log.info("Loaded %d OHR-Bench samples", len(samples))
        return samples
    except Exception as exc:
        log.warning("Failed to load OHR-Bench: %s", exc)
        return []


def stratified_select_ohrbench(
    samples: list[dict[str, Any]],
    target_count: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Select stratified sample from OHR-Bench by quality quintile."""
    if not samples:
        return []

    rng = np.random.default_rng(seed)

    strata: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for s in samples:
        strata[s["quality_quintile"]].append(s)

    per_stratum = target_count // len(strata)
    remainder = target_count % len(strata)

    selected: list[dict[str, Any]] = []
    for idx, (quintile, stratum_samples) in enumerate(sorted(strata.items())):
        n = per_stratum + (1 if idx < remainder else 0)
        n = min(n, len(stratum_samples))
        indices = rng.choice(len(stratum_samples), size=n, replace=False)
        for i in indices:
            selected.append(stratum_samples[i])

    log.info(
        "Selected %d OHR-Bench images across %d quintiles", len(selected), len(strata)
    )
    return selected


def main() -> int:
    """Select stratified images for VLM IQA labeling."""
    parser = argparse.ArgumentParser(
        description="Select stratified images for VLM IQA labeling"
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=500,
        help="Total target image count (default: 500 for pilot)",
    )
    parser.add_argument(
        "--diqa-ratio",
        type=float,
        default=0.6,
        help="Fraction allocated to DIQA-5000 (default: 0.6)",
    )
    parser.add_argument(
        "--diqa-only",
        action="store_true",
        help="Only select from DIQA-5000 (for validation overlap)",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "val", "test"],
        help="DIQA-5000 splits to select from",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output manifest JSON path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory",
    )
    parser.add_argument(
        "--diqa-metadata",
        type=Path,
        default=DIQA_METADATA_PATH,
        help="DIQA-5000 metadata JSON path",
    )
    parser.add_argument(
        "--ohrbench-dir",
        type=Path,
        default=OHRBENCH_DATASET_DIR,
        help="OHR-Bench directory",
    )

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Determine allocation
    if args.diqa_only:
        diqa_target = args.target_count
        ohrbench_target = 0
    else:
        diqa_target = int(args.target_count * args.diqa_ratio)
        ohrbench_target = args.target_count - diqa_target

    log.info(
        "Target: %d total (%d DIQA-5000, %d OHR-Bench)",
        args.target_count,
        diqa_target,
        ohrbench_target,
    )

    # Select from DIQA-5000
    diqa_samples = load_diqa5000_for_selection(args.diqa_metadata, args.splits)
    diqa_selected = stratified_select_diqa(diqa_samples, diqa_target, args.seed)

    # Select from OHR-Bench
    ohrbench_selected: list[dict[str, Any]] = []
    if ohrbench_target > 0:
        ohrbench_samples = load_ohrbench_for_selection(args.ohrbench_dir)
        ohrbench_selected = stratified_select_ohrbench(
            ohrbench_samples, ohrbench_target, args.seed
        )

    # Build manifest
    all_selected = diqa_selected + ohrbench_selected

    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "config": {
            "target_count": args.target_count,
            "diqa_ratio": args.diqa_ratio,
            "diqa_only": args.diqa_only,
            "splits": args.splits,
            "seed": args.seed,
        },
        "summary": {
            "total_selected": len(all_selected),
            "diqa_count": len(diqa_selected),
            "ohrbench_count": len(ohrbench_selected),
        },
        "samples": all_selected,
    }

    # Add stratification stats
    if diqa_selected:
        diqa_quintile_counts = defaultdict(int)
        for s in diqa_selected:
            diqa_quintile_counts[f"q{s['mos_quintile']}_{s['capture_type']}"] += 1
        manifest["diqa_strata"] = dict(sorted(diqa_quintile_counts.items()))

    if ohrbench_selected:
        ohr_quintile_counts = defaultdict(int)
        for s in ohrbench_selected:
            ohr_quintile_counts[f"q{s['quality_quintile']}"] += 1
        manifest["ohrbench_strata"] = dict(sorted(ohr_quintile_counts.items()))

    # Save manifest
    if args.output:
        output_path = args.output
    else:
        output_path = args.output_dir / f"vlm_manifest_{args.target_count}.json"

    with open(output_path, "w") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    log.info("Manifest saved to %s", output_path)
    log.info(
        "Summary: %d total (%d DIQA-5000, %d OHR-Bench)",
        len(all_selected),
        len(diqa_selected),
        len(ohrbench_selected),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
