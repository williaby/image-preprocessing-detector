#!/usr/bin/env python3
"""Evaluate OOD detection performance of the cross-model agreement system.

Measures how well the system distinguishes in-distribution (DIQA-5000) documents
from out-of-distribution documents (Tobacco800, RVL-CDIP, CORD, etc.).

Metrics:
  - AUROC: Area under ROC curve (higher = better discrimination)
  - FPR@95TPR: False positive rate at 95% true positive rate
  - Correlation between reliability_score and actual SigLIP2 error magnitude

Usage:
    # Evaluate Tier 1 (embedding OOD) only:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/evaluate_ood_detection.py \
        --ood-params models/ood/ood_params.npz \
        --in-dist-embeddings results/embeddings/diqa5000_val.npy \
        --ood-embeddings results/embeddings/tobacco800.npy \
        --ood-name tobacco800

    # Evaluate full pipeline (Tier 1 + Tier 2):
    PYTHONPATH=... uv run python3 scripts/evaluate_ood_detection.py \
        --ood-params models/ood/ood_params.npz \
        --calibration models/ood/calibration_params.json \
        --in-dist-results results/ood_eval/diqa5000_val_full.jsonl \
        --ood-results results/ood_eval/tobacco800_full.jsonl \
        --ood-name tobacco800
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def compute_fpr_at_tpr(
    labels: np.ndarray,
    scores: np.ndarray,
    target_tpr: float = 0.95,
) -> float:
    """Compute FPR at a target TPR level.

    Args:
        labels: Binary labels (1 = OOD, 0 = in-dist).
        scores: OOD scores (higher = more OOD).
        target_tpr: Target true positive rate.

    Returns:
        False positive rate at the target TPR.
    """
    fpr, tpr, _ = roc_curve(labels, scores)
    # Note: TPR from sklearn.metrics.roc_curve is monotonically non-decreasing
    # by construction (thresholds are sorted descending, TPR can only stay or rise).
    # np.nonzero(tpr >= target_tpr)[0] therefore always returns the first optimal
    # operating point — no need for additional sorting or clipping.
    indices = np.nonzero(tpr >= target_tpr)[0]
    if len(indices) == 0:
        return float(fpr[-1])
    return float(fpr[indices[0]])


def evaluate_tier1(
    in_dist_embeddings: np.ndarray,
    ood_embeddings: np.ndarray,
    ood_name: str,
    ood_params_path: str | None = None,
) -> dict[str, float]:
    """Evaluate Tier 1 embedding OOD detection.

    Args:
        in_dist_embeddings: In-distribution embeddings (n_in, embed_dim).
        ood_embeddings: OOD embeddings (n_ood, embed_dim).
        ood_name: Name of the OOD dataset.
        ood_params_path: Path to saved OOD detector params. If None, fits on
            in_dist_embeddings.

    Returns:
        Dict with auroc, fpr_at_95tpr, n_in, n_ood.
    """
    from image_preprocessing_detector.detection.ood_detector import (
        EmbeddingOODDetector,
    )

    if ood_params_path and Path(ood_params_path).exists():
        detector = EmbeddingOODDetector.load(ood_params_path)
    else:
        log.info(
            "Fitting OOD detector on %d in-dist embeddings", len(in_dist_embeddings)
        )
        detector = EmbeddingOODDetector.from_embeddings(in_dist_embeddings)

    # Score both distributions
    in_results = detector.score_batch(in_dist_embeddings)
    ood_results = detector.score_batch(ood_embeddings)

    in_scores = np.array([r.mahalanobis_distance for r in in_results])
    ood_scores = np.array([r.mahalanobis_distance for r in ood_results])

    # Labels: 0 = in-dist, 1 = OOD
    labels = np.concatenate(
        [
            np.zeros(len(in_scores)),
            np.ones(len(ood_scores)),
        ]
    )
    scores = np.concatenate([in_scores, ood_scores])

    auroc = float(roc_auc_score(labels, scores))
    fpr95 = compute_fpr_at_tpr(labels, scores, target_tpr=0.95)

    log.info("=" * 50)
    log.info("Tier 1 OOD Detection: %s", ood_name)
    log.info("  AUROC:        %.4f", auroc)
    log.info("  FPR@95TPR:    %.4f (%.1f%%)", fpr95, fpr95 * 100)
    log.info(
        "  In-dist:      n=%d, mean_dist=%.2f, std=%.2f",
        len(in_scores),
        in_scores.mean(),
        in_scores.std(),
    )
    log.info(
        "  OOD (%s): n=%d, mean_dist=%.2f, std=%.2f",
        ood_name,
        len(ood_scores),
        ood_scores.mean(),
        ood_scores.std(),
    )

    return {
        "auroc": auroc,
        "fpr_at_95tpr": fpr95,
        "in_dist_mean": float(in_scores.mean()),
        "in_dist_std": float(in_scores.std()),
        "ood_mean": float(ood_scores.mean()),
        "ood_std": float(ood_scores.std()),
        "n_in": len(in_scores),
        "n_ood": len(ood_scores),
        "ood_name": ood_name,
    }


def evaluate_tier2(
    in_dist_results_path: str,
    ood_results_path: str,
    ood_name: str,
) -> dict[str, float]:
    """Evaluate full pipeline (Tier 1 + Tier 2) using pre-computed results.

    Args:
        in_dist_results_path: JSONL with ReliabilityResult for in-dist images.
        ood_results_path: JSONL with ReliabilityResult for OOD images.
        ood_name: Name of the OOD dataset.

    Returns:
        Dict with auroc, fpr_at_95tpr for both tiers.
    """

    def load_results(path: str) -> list[dict]:
        results = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    log.warning(
                        "Skipping malformed JSONL line in %s: %s", path, line[:100]
                    )
        return results

    in_results = load_results(in_dist_results_path)
    ood_results = load_results(ood_results_path)

    # Evaluate on agreement_distance (Tier 2)
    in_agreement = np.array([r["agreement_distance"] for r in in_results])
    ood_agreement = np.array([r["agreement_distance"] for r in ood_results])

    labels = np.concatenate(
        [
            np.zeros(len(in_agreement)),
            np.ones(len(ood_agreement)),
        ]
    )
    scores = np.concatenate([in_agreement, ood_agreement])

    auroc_agreement = float(roc_auc_score(labels, scores))
    fpr95_agreement = compute_fpr_at_tpr(labels, scores, target_tpr=0.95)

    # Evaluate on reliability_score (combined)
    in_reliability = np.array([r["reliability_score"] for r in in_results])
    ood_reliability = np.array([r["reliability_score"] for r in ood_results])
    scores_rel = np.concatenate([in_reliability, ood_reliability])

    auroc_reliability = float(roc_auc_score(labels, scores_rel))
    fpr95_reliability = compute_fpr_at_tpr(labels, scores_rel, target_tpr=0.95)

    # Evaluate on Tier 1 OOD distance alone
    in_ood = np.array([r["ood"]["mahalanobis_distance"] for r in in_results])
    ood_ood = np.array([r["ood"]["mahalanobis_distance"] for r in ood_results])
    scores_ood = np.concatenate([in_ood, ood_ood])

    auroc_tier1 = float(roc_auc_score(labels, scores_ood))
    fpr95_tier1 = compute_fpr_at_tpr(labels, scores_ood, target_tpr=0.95)

    log.info("=" * 50)
    log.info("Full Pipeline OOD Detection: %s", ood_name)
    log.info(
        "  Tier 1 (embedding):   AUROC=%.4f  FPR@95=%.4f", auroc_tier1, fpr95_tier1
    )
    log.info(
        "  Tier 2 (agreement):   AUROC=%.4f  FPR@95=%.4f",
        auroc_agreement,
        fpr95_agreement,
    )
    log.info(
        "  Combined (reliability): AUROC=%.4f  FPR@95=%.4f",
        auroc_reliability,
        fpr95_reliability,
    )

    return {
        "tier1_auroc": auroc_tier1,
        "tier1_fpr95": fpr95_tier1,
        "tier2_auroc": auroc_agreement,
        "tier2_fpr95": fpr95_agreement,
        "combined_auroc": auroc_reliability,
        "combined_fpr95": fpr95_reliability,
        "n_in": len(in_results),
        "n_ood": len(ood_results),
        "ood_name": ood_name,
    }


def main() -> None:
    """Run OOD detection evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate OOD detection")
    parser.add_argument(
        "--ood-params", type=str, help="Path to OOD detector params (.npz)"
    )
    parser.add_argument(
        "--in-dist-embeddings", type=str, help="In-dist embeddings (.npy)"
    )
    parser.add_argument(
        "--ood-embeddings", type=str, nargs="+", help="OOD embeddings (.npy)"
    )
    parser.add_argument("--ood-name", type=str, nargs="+", help="OOD dataset names")
    parser.add_argument(
        "--in-dist-results", type=str, help="In-dist full results (.jsonl)"
    )
    parser.add_argument(
        "--ood-results", type=str, nargs="+", help="OOD full results (.jsonl)"
    )
    parser.add_argument(
        "--output", type=str, default="results/ood_evaluation", help="Output dir"
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, dict] = {}

    # Tier 1 evaluation
    if args.in_dist_embeddings and args.ood_embeddings:
        in_emb = np.load(args.in_dist_embeddings)
        ood_names = args.ood_name or [
            f"ood_{i}" for i in range(len(args.ood_embeddings))
        ]

        for ood_path, ood_name in zip(args.ood_embeddings, ood_names, strict=True):
            ood_emb = np.load(ood_path)
            metrics = evaluate_tier1(in_emb, ood_emb, ood_name, args.ood_params)
            all_results[f"tier1_{ood_name}"] = metrics

    # Full pipeline evaluation
    if args.in_dist_results and args.ood_results:
        ood_names = args.ood_name or [f"ood_{i}" for i in range(len(args.ood_results))]

        for ood_path, ood_name in zip(args.ood_results, ood_names, strict=True):
            metrics = evaluate_tier2(args.in_dist_results, ood_path, ood_name)
            all_results[f"full_{ood_name}"] = metrics

    # Save summary
    summary_path = output_dir / "ood_evaluation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    log.info("Summary saved to %s", summary_path)


if __name__ == "__main__":
    main()
