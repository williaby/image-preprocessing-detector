#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Collect VLM IQA labels and integrate into Layer 2 metadata.

Reads VLM quality assessment results (JSON) from Opus 4.6 in-session
labeling and integrates them into the Layer 2 enrichment metadata.
Also computes validation metrics (SRCC/PLCC) against DIQA-5000 MOS.

Input format (from VLM labeling sessions):
    {
        "labels": [
            {
                "image_id": "diqa-5000/train/ori/img_001.jpg",
                "scores": {
                    "sharpness": 4.2,
                    "noise": 3.8,
                    "contrast": 4.0,
                    "illumination": 3.5,
                    "compression": 4.5,
                    "overall": 4.0
                }
            },
            ...
        ]
    }

Usage:
    # Validate VLM labels against DIQA-5000 MOS:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/collect_vlm_iqa_labels.py \
        --labels results/iqa_vlm_labeling/vlm_labels_batch_001.json \
        --validate

    # Integrate into Layer 2 metadata:
    PYTHONPATH=... uv run python3 scripts/collect_vlm_iqa_labels.py \
        --labels results/iqa_vlm_labeling/vlm_labels_batch_001.json \
        --integrate --metadata /mnt/e/.../diqa-5000_metadata.json

    # Merge multiple label batches:
    PYTHONPATH=... uv run python3 scripts/collect_vlm_iqa_labels.py \
        --labels results/iqa_vlm_labeling/vlm_labels_batch_*.json \
        --merge --output results/iqa_vlm_labeling/vlm_labels_merged.json
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

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
OUTPUT_DIR = Path("results/iqa_vlm_labeling")

VLM_DIMENSIONS = [
    "sharpness",
    "noise",
    "contrast",
    "illumination",
    "compression",
    "overall",
]

SCRIPT_VERSION = "1.0.0"
PROMPT_VERSION = "1.0"  # Track prompt template version for reproducibility


# ---------------------------------------------------------------------------
# Label I/O
# ---------------------------------------------------------------------------
def load_vlm_labels(label_paths: list[Path]) -> list[dict[str, Any]]:
    """Load VLM labels from one or more JSON files.

    Supports both single-file and batch-file formats.
    """
    all_labels: list[dict[str, Any]] = []

    for path in label_paths:
        log.info("Loading labels from %s", path)
        with open(path) as fh:
            data = json.load(fh)

        if "labels" in data:
            labels = data["labels"]
        elif isinstance(data, list):
            labels = data
        else:
            log.warning("Unrecognized format in %s, skipping", path)
            continue

        for label in labels:
            label["source_file"] = str(path)
            all_labels.append(label)

    log.info("Loaded %d VLM labels from %d files", len(all_labels), len(label_paths))
    return all_labels


def validate_label(label: dict[str, Any]) -> bool:
    """Validate a single VLM label has required fields and valid ranges."""
    if "image_id" not in label and "id" not in label:
        return False

    scores = label.get("scores", {})
    for dim in VLM_DIMENSIONS:
        val = scores.get(dim)
        if val is None:
            return False
        if not (1.0 <= float(val) <= 5.0):
            return False

    return True


# ---------------------------------------------------------------------------
# Validation against DIQA-5000 MOS
# ---------------------------------------------------------------------------
def validate_against_diqa(
    labels: list[dict[str, Any]],
    metadata_path: Path,
) -> dict[str, Any]:
    """Compute SRCC/PLCC between VLM scores and DIQA-5000 MOS.

    Cross-validates on the overlap set (DIQA-5000 images that have both
    VLM labels and human MOS scores).

    Returns validation report dict.
    """
    log.info("Loading DIQA-5000 metadata for validation...")
    with open(metadata_path) as fh:
        metadata = json.load(fh)

    # Build MOS index by sample id and path
    mos_by_id: dict[str, dict[str, float]] = {}
    mos_by_path: dict[str, dict[str, float]] = {}
    for sample in metadata.get("samples", []):
        original_labels = sample.get("original_labels", {})
        mos_overall = original_labels.get("mos_overall")
        if mos_overall is None:
            continue

        sample_id = sample.get("id", "")
        rel_path = sample.get("source", {}).get("original_path", "")

        mos_data = {
            "mos_overall": float(mos_overall),
            "mos_sharpness": float(original_labels.get("mos_sharpness", 0)),
            "mos_color_fidelity": float(
                original_labels.get("mos_color_fidelity", 0)
            ),
        }
        mos_by_id[sample_id] = mos_data
        if rel_path:
            mos_by_path[rel_path] = mos_data

    # Match VLM labels to MOS scores
    matched: list[dict[str, Any]] = []
    for label in labels:
        image_id = label.get("image_id", label.get("id", ""))

        mos = mos_by_id.get(image_id) or mos_by_path.get(image_id)
        if mos is None:
            # Try partial path match
            for path_key, mos_val in mos_by_path.items():
                if image_id.endswith(path_key) or path_key.endswith(image_id):
                    mos = mos_val
                    break

        if mos is not None:
            matched.append({"vlm": label["scores"], "mos": mos})

    log.info("Matched %d/%d VLM labels to DIQA-5000 MOS", len(matched), len(labels))

    if len(matched) < 10:
        log.warning("Too few matches for meaningful correlation")
        return {"error": "insufficient_matches", "matched": len(matched)}

    # Compute correlations
    report: dict[str, Any] = {
        "num_matched": len(matched),
        "num_total_vlm": len(labels),
        "correlations": {},
    }

    # VLM overall vs MOS overall
    vlm_overall = np.array([m["vlm"]["overall"] for m in matched])
    mos_overall = np.array([m["mos"]["mos_overall"] for m in matched])

    srcc = stats.spearmanr(vlm_overall, mos_overall)
    plcc = stats.pearsonr(vlm_overall, mos_overall)

    report["correlations"]["vlm_overall_vs_mos_overall"] = {
        "srcc": round(float(getattr(srcc, "statistic", srcc.correlation)), 4),
        "srcc_pvalue": float(srcc.pvalue),
        "plcc": round(float(getattr(plcc, "statistic", plcc[0])), 4),
        "plcc_pvalue": float(plcc.pvalue),
    }

    # VLM sharpness vs MOS sharpness
    vlm_sharpness = np.array([m["vlm"]["sharpness"] for m in matched])
    mos_sharpness = np.array([m["mos"]["mos_sharpness"] for m in matched])

    if np.std(mos_sharpness) > 1e-8:
        srcc = stats.spearmanr(vlm_sharpness, mos_sharpness)
        plcc = stats.pearsonr(vlm_sharpness, mos_sharpness)
        report["correlations"]["vlm_sharpness_vs_mos_sharpness"] = {
            "srcc": round(
                float(getattr(srcc, "statistic", srcc.correlation)), 4
            ),
            "srcc_pvalue": float(srcc.pvalue),
            "plcc": round(float(getattr(plcc, "statistic", plcc[0])), 4),
            "plcc_pvalue": float(plcc.pvalue),
        }

    # VLM contrast vs MOS color_fidelity
    vlm_contrast = np.array([m["vlm"]["contrast"] for m in matched])
    mos_color = np.array([m["mos"]["mos_color_fidelity"] for m in matched])

    if np.std(mos_color) > 1e-8:
        srcc = stats.spearmanr(vlm_contrast, mos_color)
        plcc = stats.pearsonr(vlm_contrast, mos_color)
        report["correlations"]["vlm_contrast_vs_mos_color_fidelity"] = {
            "srcc": round(
                float(getattr(srcc, "statistic", srcc.correlation)), 4
            ),
            "srcc_pvalue": float(srcc.pvalue),
            "plcc": round(float(getattr(plcc, "statistic", plcc[0])), 4),
            "plcc_pvalue": float(plcc.pvalue),
        }

    # Inter-dimension correlation matrix (check independence)
    dim_arrays = {
        dim: np.array([m["vlm"][dim] for m in matched]) for dim in VLM_DIMENSIONS
    }
    intercorr: dict[str, dict[str, float]] = {}
    for dim_a in VLM_DIMENSIONS:
        intercorr[dim_a] = {}
        for dim_b in VLM_DIMENSIONS:
            if dim_a == dim_b:
                intercorr[dim_a][dim_b] = 1.0
            else:
                r = stats.spearmanr(dim_arrays[dim_a], dim_arrays[dim_b])
                intercorr[dim_a][dim_b] = round(
                    float(getattr(r, "statistic", r.correlation)), 4
                )

    report["vlm_intercorrelation"] = intercorr

    # Check independence criteria (r < 0.8 between non-overall pairs)
    high_corr_pairs: list[str] = []
    for dim_a in VLM_DIMENSIONS:
        for dim_b in VLM_DIMENSIONS:
            if dim_a >= dim_b or dim_a == "overall" or dim_b == "overall":
                continue
            r = abs(intercorr[dim_a][dim_b])
            if r >= 0.8:
                high_corr_pairs.append(f"{dim_a}-{dim_b}: {r:.4f}")

    report["independence_check"] = {
        "threshold": 0.8,
        "high_correlation_pairs": high_corr_pairs,
        "passes": len(high_corr_pairs) == 0,
    }

    # Summary statistics per dimension
    report["dimension_stats"] = {}
    for dim in VLM_DIMENSIONS:
        values = [m["vlm"][dim] for m in matched]
        report["dimension_stats"][dim] = {
            "mean": round(float(np.mean(values)), 3),
            "std": round(float(np.std(values)), 3),
            "min": round(float(np.min(values)), 1),
            "max": round(float(np.max(values)), 1),
        }

    # Log key results
    log.info("=" * 60)
    log.info("VALIDATION RESULTS")
    log.info("=" * 60)
    for pair_name, corr in report["correlations"].items():
        log.info("  %s: SRCC=%.4f, PLCC=%.4f", pair_name, corr["srcc"], corr["plcc"])

    if high_corr_pairs:
        log.warning("High inter-dimension correlations: %s", high_corr_pairs)
    else:
        log.info("Independence check PASSED (all non-overall pairs r < 0.8)")

    return report


# ---------------------------------------------------------------------------
# Integration into Layer 2 metadata
# ---------------------------------------------------------------------------
def integrate_labels(
    labels: list[dict[str, Any]],
    metadata_path: Path,
    output_path: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Integrate VLM labels into Layer 2 enrichment metadata.

    Creates a new enrichment version with VLM quality scores for each
    matched sample.

    Returns number of samples updated.
    """
    log.info("Loading metadata from %s", metadata_path)
    with open(metadata_path) as fh:
        metadata = json.load(fh)

    # Index labels by id and path
    labels_by_id: dict[str, dict[str, Any]] = {}
    labels_by_path: dict[str, dict[str, Any]] = {}
    for label in labels:
        image_id = label.get("image_id", label.get("id", ""))
        labels_by_id[image_id] = label
        labels_by_path[image_id] = label

    updated = 0
    for sample in metadata.get("samples", []):
        sample_id = sample.get("id", "")
        rel_path = sample.get("source", {}).get("original_path", "")

        label = labels_by_id.get(sample_id) or labels_by_path.get(rel_path)
        if label is None:
            continue

        scores = label.get("scores", {})
        if not all(dim in scores for dim in VLM_DIMENSIONS):
            continue

        # Get existing enrichments
        enrichments = sample.setdefault("enrichments", {})
        current_version = enrichments.get("current_version", 0)
        versions = enrichments.setdefault("versions", [])

        # Copy latest data
        latest_data = versions[-1].get("data", {}).copy() if versions else {}

        # Add VLM quality scores
        latest_data["vlm_iqa_sharpness"] = float(scores["sharpness"])
        latest_data["vlm_iqa_noise"] = float(scores["noise"])
        latest_data["vlm_iqa_contrast"] = float(scores["contrast"])
        latest_data["vlm_iqa_illumination"] = float(scores["illumination"])
        latest_data["vlm_iqa_compression"] = float(scores["compression"])
        latest_data["vlm_iqa_overall"] = float(scores["overall"])
        latest_data["vlm_iqa_model_name"] = "opus_4.6"
        latest_data["vlm_iqa_model_version"] = "claude-opus-4-6"
        latest_data["vlm_iqa_prompt_version"] = PROMPT_VERSION

        # Create new version
        new_version = {
            "version": current_version + 1,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": f"collect_vlm_iqa_labels.py_v{SCRIPT_VERSION}",
            "method": "tier_1_annotation",
            "description": "VLM 6-dim IQA quality assessment (Opus 4.6 in-session)",
            "script_version": SCRIPT_VERSION,
            "data": latest_data,
        }

        versions.append(new_version)
        enrichments["current_version"] = current_version + 1
        updated += 1

    log.info("Updated %d/%d samples with VLM labels", updated, len(labels))

    if dry_run:
        log.info("Dry run - not saving")
        return updated

    save_path = output_path or metadata_path
    log.info("Saving metadata to %s", save_path)
    with open(save_path, "w") as fh:
        json.dump(metadata, fh, indent=2, default=str)

    return updated


# ---------------------------------------------------------------------------
# Merge label batches
# ---------------------------------------------------------------------------
def merge_label_batches(
    label_paths: list[Path],
    output_path: Path,
) -> int:
    """Merge multiple VLM label batch files into one.

    Deduplicates by image_id (keeps latest).
    """
    all_labels = load_vlm_labels(label_paths)

    # Deduplicate by image_id (last wins)
    by_id: dict[str, dict[str, Any]] = {}
    for label in all_labels:
        image_id = label.get("image_id", label.get("id", ""))
        by_id[image_id] = label

    merged = list(by_id.values())

    output = {
        "created_at": datetime.now(UTC).isoformat(),
        "source_files": [str(p) for p in label_paths],
        "total_labels": len(merged),
        "deduplicated_from": len(all_labels),
        "labels": merged,
    }

    with open(output_path, "w") as fh:
        json.dump(output, fh, indent=2, default=str)

    log.info(
        "Merged %d labels (%d before dedup) from %d files -> %s",
        len(merged),
        len(all_labels),
        len(label_paths),
        output_path,
    )
    return len(merged)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    """Collect, validate, and integrate VLM IQA labels."""
    parser = argparse.ArgumentParser(
        description="Collect and integrate VLM IQA labels"
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        required=True,
        help="VLM label JSON file(s) (supports glob patterns)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate labels against DIQA-5000 MOS",
    )
    parser.add_argument(
        "--integrate",
        action="store_true",
        help="Integrate labels into Layer 2 metadata",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge multiple label batches",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DIQA_METADATA_PATH,
        help="Layer 2 metadata JSON path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (for merge or integrate)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save changes",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for reports",
    )

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Expand glob patterns in label paths
    label_paths: list[Path] = []
    for pattern in args.labels:
        expanded = glob.glob(pattern)
        if expanded:
            label_paths.extend(Path(p) for p in expanded)
        else:
            label_paths.append(Path(pattern))

    if not any(p.exists() for p in label_paths):
        log.error("No label files found: %s", args.labels)
        return 1

    # Merge mode
    if args.merge:
        output = args.output or args.output_dir / "vlm_labels_merged.json"
        merge_label_batches(label_paths, output)
        return 0

    # Load labels
    labels = load_vlm_labels([p for p in label_paths if p.exists()])

    # Validate labels
    valid_labels = [lbl for lbl in labels if validate_label(lbl)]
    if len(valid_labels) < len(labels):
        log.warning(
            "Filtered %d invalid labels (missing dims or out-of-range)",
            len(labels) - len(valid_labels),
        )

    # Validate against DIQA-5000
    if args.validate:
        report = validate_against_diqa(valid_labels, args.metadata)
        report_path = args.output_dir / "vlm_validation_report.json"
        with open(report_path, "w") as fh:
            json.dump(report, fh, indent=2)
        log.info("Validation report saved to %s", report_path)

    # Integrate into metadata
    if args.integrate:
        updated = integrate_labels(
            valid_labels,
            args.metadata,
            output_path=args.output,
            dry_run=args.dry_run,
        )
        log.info("Integration complete: %d samples updated", updated)

    if not args.validate and not args.integrate:
        log.info("No action specified. Use --validate, --integrate, or --merge")
        log.info("Labels loaded: %d total, %d valid", len(labels), len(valid_labels))

    return 0


if __name__ == "__main__":
    sys.exit(main())
