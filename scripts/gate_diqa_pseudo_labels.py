#!/usr/bin/env python3
"""OOD-gated acceptance of DIQA pseudo-labels for SigLIP 2 training.

Takes DeQA-Doc pseudo-labels (from generate_diqa_pseudo_labels.py) and
applies Mahalanobis distance-based OOD gating to assign sample weights.
Images close to the DIQA-5000 training distribution get high weight;
OOD images get low weight or are rejected.

Tiers:
    AUTO_ACCEPT  (d < p75):     weight=1.0  Trust DeQA-Doc directly
    LOW_WEIGHT   (p75-p90):     weight=0.5  Accept with reduced weight
    TIER2_TRIGGER (p90-p97.5):  weight=0.3  Accept with low weight (VLM optional)
    HARD_REJECT  (d > p97.5):   weight=0.0  Exclude from training

DIQA-5000 ground truth images always get weight=1.0 regardless of OOD score.

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python scripts/gate_diqa_pseudo_labels.py \\
            --pseudo-labels /path/to/diqa_pseudo_labels.jsonl \\
            --embeddings /path/to/corpus_embeddings.npy \\
            --embedding-ids /path/to/corpus_ids.json \\
            --ood-params /mnt/e/image_detection/embeddings/ood_params_4400.npz \\
            --output /path/to/gated_diqa_labels.jsonl \\
            --diqa-gt /path/to/diqa5000_train.json

Output format (JSONL):
    {
        "sha256": "abc123...",
        "image_path": "/abs/path/to/image.jpg",
        "overall_label": 0.605,
        "sharpness_label": 0.72,
        "color_fidelity_label": 0.81,
        "overall_level_probs": [0.02, 0.08, 0.30, 0.45, 0.15],
        "sharpness_level_probs": [...],
        "color_fidelity_level_probs": [...],
        "sample_weight": 1.0,
        "acceptance_tier": "AUTO_ACCEPT",
        "mahalanobis_distance": 22.3,
        "mahalanobis_percentile": 62.1,
        "label_source": "deqa_pseudo"
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


class AcceptanceTier(str, Enum):
    """Tiered acceptance levels for pseudo-labels."""

    AUTO_ACCEPT = "AUTO_ACCEPT"
    LOW_WEIGHT = "LOW_WEIGHT"
    TIER2_TRIGGER = "TIER2_TRIGGER"
    HARD_REJECT = "HARD_REJECT"
    GROUND_TRUTH = "GROUND_TRUTH"


# Default percentile thresholds (based on DIQA-5000 calibration distances)
DEFAULT_P75 = 75.0
DEFAULT_P90 = 90.0
DEFAULT_P975 = 97.5

# Weights per tier
TIER_WEIGHTS: dict[AcceptanceTier, float] = {
    AcceptanceTier.AUTO_ACCEPT: 1.0,
    AcceptanceTier.LOW_WEIGHT: 0.5,
    AcceptanceTier.TIER2_TRIGGER: 0.3,
    AcceptanceTier.HARD_REJECT: 0.0,
    AcceptanceTier.GROUND_TRUTH: 1.0,
}

DIMENSIONS = ("overall", "sharpness", "color_fidelity")


def _classify_tier(percentile: float) -> AcceptanceTier:
    """Classify an image into an acceptance tier based on OOD percentile.

    Args:
        percentile: Mahalanobis distance percentile (0-100) relative to
            the DIQA-5000 calibration set.

    Returns:
        AcceptanceTier for the image.
    """
    if percentile < DEFAULT_P75:
        return AcceptanceTier.AUTO_ACCEPT
    if percentile < DEFAULT_P90:
        return AcceptanceTier.LOW_WEIGHT
    if percentile < DEFAULT_P975:
        return AcceptanceTier.TIER2_TRIGGER
    return AcceptanceTier.HARD_REJECT


def _extract_gt_scores(record: dict[str, Any]) -> dict[str, float]:
    """Extract per-dimension scores from a single ground truth record."""
    return {dim: record.get(dim, record.get(f"{dim}_score", 0.0)) for dim in DIMENSIONS}


def _detect_gt_format(content: str) -> list[dict[str, Any]] | None:
    """Detect whether content is a JSON array and return parsed records if so.

    Returns the parsed list on success, or None if content is not a JSON array.
    """
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return None


def _parse_jsonl_records(content: str) -> list[dict[str, Any]]:
    """Parse JSONL content into a list of dicts, skipping malformed lines."""
    records: list[dict[str, Any]] = []
    for line in content.strip().split("\n"):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _load_diqa_gt(gt_path: Path | None) -> dict[str, dict[str, float]]:
    """Load DIQA-5000 ground truth labels.

    Supports both JSON array and JSONL formats. Returns mapping of
    sha256 -> {overall, sharpness, color_fidelity} normalized scores.
    """
    if gt_path is None or not gt_path.exists():
        return {}

    content = gt_path.read_text()
    records = _detect_gt_format(content)
    if records is None:
        records = _parse_jsonl_records(content)

    gt_map: dict[str, dict[str, float]] = {}
    for record in records:
        sha = record.get("sha256", "")
        if sha:
            gt_map[sha] = _extract_gt_scores(record)
    return gt_map


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for OOD-gated label acceptance."""
    parser = argparse.ArgumentParser(
        description="Gate DIQA pseudo-labels using OOD detection"
    )
    parser.add_argument(
        "--pseudo-labels",
        type=str,
        required=True,
        help="Input JSONL from generate_diqa_pseudo_labels.py",
    )
    parser.add_argument(
        "--embeddings",
        type=str,
        required=True,
        help="Corpus embeddings .npy file (N x 768)",
    )
    parser.add_argument(
        "--embedding-ids",
        type=str,
        required=True,
        help="JSON list of SHA256s matching embedding rows",
    )
    parser.add_argument(
        "--ood-params", type=str, required=True, help="OOD detector params .npz file"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Output gated labels JSONL"
    )
    parser.add_argument(
        "--diqa-gt",
        type=str,
        default=None,
        help="Optional DIQA-5000 ground truth JSON/JSONL",
    )
    parser.add_argument(
        "--ood-threshold",
        type=float,
        default=None,
        help="Override OOD threshold (default: from params)",
    )
    return parser.parse_args()


def _load_and_validate_inputs(
    args: argparse.Namespace,
) -> tuple[Any, Any, dict[str, int], dict[str, dict[str, float]], list[dict[str, Any]]]:
    """Load OOD detector, embeddings, ground truth, and pseudo-labels.

    Returns (detector, embeddings, sha_to_idx, diqa_gt, pseudo_labels).
    """
    from image_preprocessing_detector.detection.ood_detector import EmbeddingOODDetector

    print(f"Loading OOD detector from {args.ood_params}...", file=sys.stderr)
    detector = EmbeddingOODDetector.load(args.ood_params)
    if args.ood_threshold is not None:
        detector.threshold = args.ood_threshold

    print(f"Loading embeddings from {args.embeddings}...", file=sys.stderr)
    embeddings = np.load(args.embeddings)
    with open(args.embedding_ids) as fh:
        embedding_ids: list[str] = json.load(fh)

    if embeddings.shape[0] != len(embedding_ids):
        print(
            f"ERROR: Embedding count ({embeddings.shape[0]}) "
            f"!= ID count ({len(embedding_ids)})",
            file=sys.stderr,
        )
        sys.exit(1)

    sha_to_idx: dict[str, int] = {sha: i for i, sha in enumerate(embedding_ids)}
    print(
        f"Loaded {len(sha_to_idx)} embeddings ({embeddings.shape[1]}-dim)",
        file=sys.stderr,
    )

    diqa_gt = _load_diqa_gt(Path(args.diqa_gt) if args.diqa_gt else None)
    if diqa_gt:
        print(f"Loaded {len(diqa_gt)} DIQA-5000 ground truth records", file=sys.stderr)

    pseudo_labels: list[dict[str, Any]] = []
    with open(args.pseudo_labels) as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                try:
                    pseudo_labels.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue
    print(f"Loaded {len(pseudo_labels)} pseudo-label records", file=sys.stderr)

    return detector, embeddings, sha_to_idx, diqa_gt, pseudo_labels


def _build_gt_record(
    sha: str,
    image_path: str,
    gt: dict[str, float],
    record: dict[str, Any],
) -> dict[str, Any]:
    """Build an output record for a ground truth image."""
    output: dict[str, Any] = {
        "sha256": sha,
        "image_path": image_path,
        "overall_label": gt.get("overall", 0.0),
        "sharpness_label": gt.get("sharpness", 0.0),
        "color_fidelity_label": gt.get("color_fidelity", 0.0),
        "sample_weight": TIER_WEIGHTS[AcceptanceTier.GROUND_TRUTH],
        "acceptance_tier": AcceptanceTier.GROUND_TRUTH.value,
        "mahalanobis_distance": 0.0,
        "mahalanobis_percentile": 0.0,
        "label_source": "diqa_ground_truth",
    }
    for dim in DIMENSIONS:
        dim_data = record.get(dim)
        if dim_data and isinstance(dim_data, dict):
            output[f"{dim}_level_probs"] = dim_data.get("level_probs", [])
    return output


def _build_pseudo_record(
    sha: str,
    image_path: str,
    record: dict[str, Any],
    ood_result: Any,
    tier: AcceptanceTier,
) -> dict[str, Any]:
    """Build an output record for a pseudo-labeled image with OOD gating."""
    output: dict[str, Any] = {
        "sha256": sha,
        "image_path": image_path,
        "sample_weight": TIER_WEIGHTS[tier],
        "acceptance_tier": tier.value,
        "mahalanobis_distance": round(ood_result.mahalanobis_distance, 2),
        "mahalanobis_percentile": round(ood_result.percentile, 1),
        "label_source": "deqa_pseudo",
    }
    for dim in DIMENSIONS:
        dim_data = record.get(dim)
        if dim_data and isinstance(dim_data, dict):
            output[f"{dim}_label"] = dim_data.get("score", 0.0)
            output[f"{dim}_level_probs"] = dim_data.get("level_probs", [])
        else:
            output[f"{dim}_label"] = 0.0
            output[f"{dim}_level_probs"] = []
    return output


def _process_labels(
    pseudo_labels: list[dict[str, Any]],
    detector: Any,
    embeddings: Any,
    sha_to_idx: dict[str, int],
    diqa_gt: dict[str, dict[str, float]],
    output_path: Path,
) -> tuple[dict[str, int], int]:
    """Gate pseudo-labels and write output JSONL.

    Returns (tier_counts, missing_embeddings).
    """
    tier_counts: dict[str, int] = {t.value: 0 for t in AcceptanceTier}
    missing_embeddings = 0

    with output_path.open("w") as out_f:
        for record in pseudo_labels:
            sha = record.get("sha256", "")
            image_path = record.get("image_path", "")

            if sha in diqa_gt:
                output = _build_gt_record(sha, image_path, diqa_gt[sha], record)
                out_f.write(json.dumps(output) + "\n")
                tier_counts[AcceptanceTier.GROUND_TRUTH.value] += 1
                continue

            if sha not in sha_to_idx:
                missing_embeddings += 1
                continue

            embedding = embeddings[sha_to_idx[sha]]
            ood_result = detector.score(embedding)
            tier = _classify_tier(ood_result.percentile)

            output = _build_pseudo_record(sha, image_path, record, ood_result, tier)
            out_f.write(json.dumps(output) + "\n")
            tier_counts[tier.value] += 1

    return tier_counts, missing_embeddings


def _print_summary(
    tier_counts: dict[str, int],
    missing_embeddings: int,
    output_path: Path,
) -> None:
    """Print gating summary statistics to stderr."""
    total = sum(tier_counts.values())
    print(f"\n{'=' * 50}", file=sys.stderr)
    print(f"Gating Summary ({total} images processed):", file=sys.stderr)
    for tier_name, count in sorted(tier_counts.items()):
        pct = 100.0 * count / max(total, 1)
        weight = TIER_WEIGHTS.get(AcceptanceTier(tier_name), 0.0)
        print(
            f"  {tier_name:20s}: {count:6d} ({pct:5.1f}%)  weight={weight}",
            file=sys.stderr,
        )
    if missing_embeddings:
        print(
            f"  Missing embeddings:   {missing_embeddings:6d} (skipped)",
            file=sys.stderr,
        )
    print(f"{'=' * 50}", file=sys.stderr)
    print(f"Output: {output_path}", file=sys.stderr)


def main() -> None:
    """Run OOD-gated label acceptance pipeline."""
    args = _parse_args()

    detector, embeddings, sha_to_idx, diqa_gt, pseudo_labels = (
        _load_and_validate_inputs(args)
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tier_counts, missing_embeddings = _process_labels(
        pseudo_labels, detector, embeddings, sha_to_idx, diqa_gt, output_path
    )

    _print_summary(tier_counts, missing_embeddings, output_path)


if __name__ == "__main__":
    main()
