#!/usr/bin/env python3
"""Compare DeQA quantization results using KL-divergence and correlation metrics.

Per multi-model consensus validation requirements:
- Measure KL-divergence between quantized and FP16 distributions
- Calculate SRCC (Spearman) and PLCC (Pearson) correlation
- Check distribution entropy shifts
- Generate comprehensive comparison report

Decision Gates:
- INT8: KL-div <0.03 AND SRCC loss <1% → Approve
- NF4: KL-div <0.05 AND SRCC loss <2% → Approve

Usage:
    python scripts/compare_quantization_results.py \
        --fp16 results/validation/validation_fp16_deqa_labels.jsonl \
        --int8 results/validation/validation_8bit_deqa_labels.jsonl \
        --nf4 results/validation/validation_4bit_deqa_labels.jsonl \
        --output results/quantization_comparison_report.json
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats


def load_results(filepath: Path) -> list[dict]:
    """Load JSONL results file."""
    results = []
    with open(filepath) as f:
        for line in f:
            results.append(json.loads(line))
    return results


def compute_kl_divergence(p_probs: dict, q_probs: dict, epsilon=1e-10) -> float:
    """Compute KL-divergence between two probability distributions.

    KL(P || Q) = sum(P(i) * log(P(i) / Q(i)))

    Args:
        p_probs: Reference distribution (FP16)
        q_probs: Comparison distribution (quantized)
        epsilon: Small value to avoid log(0)

    Returns:
        KL-divergence value
    """
    kl_div = 0.0
    for level in p_probs.keys():
        p = max(p_probs[level], epsilon)
        q = max(q_probs[level], epsilon)
        kl_div += p * math.log(p / q)
    return kl_div


def compute_entropy(probs: dict, epsilon=1e-10) -> float:
    """Compute Shannon entropy of distribution.

    H(P) = -sum(P(i) * log(P(i)))
    """
    entropy = 0.0
    for p in probs.values():
        if p > epsilon:
            entropy -= p * math.log(p)
    return entropy


def compare_distributions(
    fp16_results: list[dict], quant_results: list[dict], mode: str
) -> dict:
    """Compare quantized results against FP16 baseline.

    Args:
        fp16_results: FP16 baseline results
        quant_results: Quantized mode results
        mode: Quantization mode name ('INT8' or 'NF4')

    Returns:
        Dict with comparison metrics
    """
    # Align results by image path
    fp16_map = {(r["dataset"], r["image"]): r for r in fp16_results}
    quant_map = {(r["dataset"], r["image"]): r for r in quant_results}

    # Find common samples
    common_keys = set(fp16_map.keys()) & set(quant_map.keys())
    print(f"\n{mode} Comparison:")
    print(f"  FP16 samples: {len(fp16_results)}")
    print(f"  {mode} samples: {len(quant_results)}")
    print(f"  Common samples: {len(common_keys)}")

    if not common_keys:
        return {"error": "No common samples found"}

    # Compute per-sample metrics
    kl_divergences = []
    entropy_shifts = []
    score_diffs = []
    fp16_scores = []
    quant_scores = []

    for key in common_keys:
        fp16_entry = fp16_map[key]
        quant_entry = quant_map[key]

        # KL-divergence between probability distributions
        kl_div = compute_kl_divergence(fp16_entry["probs"], quant_entry["probs"])
        kl_divergences.append(kl_div)

        # Entropy shift
        fp16_entropy = compute_entropy(fp16_entry["probs"])
        quant_entropy = compute_entropy(quant_entry["probs"])
        entropy_shift = abs(quant_entropy - fp16_entropy)
        entropy_shifts.append(entropy_shift)

        # Score difference
        score_diff = abs(fp16_entry["predicted_score"] - quant_entry["predicted_score"])
        score_diffs.append(score_diff)

        # Collect scores for correlation
        fp16_scores.append(fp16_entry["predicted_score"])
        quant_scores.append(quant_entry["predicted_score"])

    # Aggregate statistics
    mean_kl_div = np.mean(kl_divergences)
    max_kl_div = np.max(kl_divergences)
    p95_kl_div = np.percentile(kl_divergences, 95)

    mean_entropy_shift = np.mean(entropy_shifts)
    max_entropy_shift = np.max(entropy_shifts)

    mean_score_diff = np.mean(score_diffs)
    max_score_diff = np.max(score_diffs)

    # Correlation metrics
    srcc, srcc_pvalue = stats.spearmanr(fp16_scores, quant_scores)
    plcc, plcc_pvalue = stats.pearsonr(fp16_scores, quant_scores)

    # SRCC loss percentage
    srcc_loss_pct = (1 - srcc) * 100

    return {
        "mode": mode,
        "n_samples": len(common_keys),
        "kl_divergence": {
            "mean": float(mean_kl_div),
            "max": float(max_kl_div),
            "p95": float(p95_kl_div),
        },
        "entropy_shift": {
            "mean": float(mean_entropy_shift),
            "max": float(max_entropy_shift),
        },
        "score_difference": {
            "mean": float(mean_score_diff),
            "max": float(max_score_diff),
        },
        "correlation": {
            "srcc": float(srcc),
            "srcc_pvalue": float(srcc_pvalue),
            "srcc_loss_pct": float(srcc_loss_pct),
            "plcc": float(plcc),
            "plcc_pvalue": float(plcc_pvalue),
        },
    }


def evaluate_decision_gate(metrics: dict, mode: str) -> dict:
    """Evaluate if quantization mode passes validation gates.

    Decision Gates (per consensus):
    - INT8: KL-div <0.03 AND SRCC loss <1%
    - NF4: KL-div <0.05 AND SRCC loss <2%

    Args:
        metrics: Comparison metrics dict
        mode: Quantization mode ('INT8' or 'NF4')

    Returns:
        Dict with pass/fail status and reasoning
    """
    mean_kl = metrics["kl_divergence"]["mean"]
    srcc_loss = metrics["correlation"]["srcc_loss_pct"]

    if mode == "INT8":
        kl_threshold = 0.03
        srcc_threshold = 1.0
    elif mode == "NF4":
        kl_threshold = 0.05
        srcc_threshold = 2.0
    else:
        return {"error": f"Unknown mode: {mode}"}

    kl_pass = mean_kl < kl_threshold
    srcc_pass = srcc_loss < srcc_threshold
    overall_pass = kl_pass and srcc_pass

    return {
        "mode": mode,
        "pass": overall_pass,
        "kl_divergence": {
            "value": mean_kl,
            "threshold": kl_threshold,
            "pass": kl_pass,
        },
        "srcc_loss": {
            "value": srcc_loss,
            "threshold": srcc_threshold,
            "pass": srcc_pass,
        },
        "recommendation": (
            f"✅ {mode} APPROVED for production"
            if overall_pass
            else f"❌ {mode} REJECTED - use FP16 baseline"
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare quantization results vs FP16 baseline"
    )
    parser.add_argument(
        "--fp16", type=str, required=True, help="FP16 baseline results JSONL"
    )
    parser.add_argument("--int8", type=str, required=True, help="INT8 results JSONL")
    parser.add_argument("--nf4", type=str, required=True, help="NF4 results JSONL")
    parser.add_argument(
        "--output",
        type=str,
        default="results/quantization_comparison_report.json",
        help="Output path for comparison report",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("DeQA Quantization Validation Analysis")
    print("=" * 70)

    # Load results
    print("\nLoading results...")
    fp16_results = load_results(Path(args.fp16))
    int8_results = load_results(Path(args.int8))
    nf4_results = load_results(Path(args.nf4))

    print(f"  FP16: {len(fp16_results)} samples")
    print(f"  INT8: {len(int8_results)} samples")
    print(f"  NF4: {len(nf4_results)} samples")

    # Compare distributions
    int8_metrics = compare_distributions(fp16_results, int8_results, "INT8")
    nf4_metrics = compare_distributions(fp16_results, nf4_results, "NF4")

    # Evaluate decision gates
    print("\n" + "=" * 70)
    print("Decision Gate Evaluation")
    print("=" * 70)

    int8_decision = evaluate_decision_gate(int8_metrics, "INT8")
    nf4_decision = evaluate_decision_gate(nf4_metrics, "NF4")

    print(f"\nINT8 Quantization:")
    print(
        f"  Mean KL-div: {int8_metrics['kl_divergence']['mean']:.4f} (threshold: <0.03)"
    )
    print(
        f"  SRCC loss: {int8_metrics['correlation']['srcc_loss_pct']:.2f}% (threshold: <1%)"
    )
    print(f"  Decision: {int8_decision['recommendation']}")

    print(f"\nNF4 Quantization:")
    print(
        f"  Mean KL-div: {nf4_metrics['kl_divergence']['mean']:.4f} (threshold: <0.05)"
    )
    print(
        f"  SRCC loss: {nf4_metrics['correlation']['srcc_loss_pct']:.2f}% (threshold: <2%)"
    )
    print(f"  Decision: {nf4_decision['recommendation']}")

    # Generate comprehensive report
    report = {
        "analysis_date": "2025-12-21",
        "validation_samples": len(fp16_results),
        "int8": {
            "metrics": int8_metrics,
            "decision": int8_decision,
        },
        "nf4": {
            "metrics": nf4_metrics,
            "decision": nf4_decision,
        },
        "recommendation": generate_final_recommendation(int8_decision, nf4_decision),
    }

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Comparison report saved: {output_path}")

    # Print final recommendation
    print("\n" + "=" * 70)
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(report["recommendation"])


def generate_final_recommendation(int8_decision: dict, nf4_decision: dict) -> str:
    """Generate final production recommendation."""
    int8_pass = int8_decision["pass"]
    nf4_pass = nf4_decision["pass"]

    if int8_pass and nf4_pass:
        return (
            "✅ Both INT8 and NF4 APPROVED\n\n"
            "Recommendation: Use NF4 for production\n"
            "Reason: Same quality as INT8, lower VRAM (9GB vs 14GB)\n"
            "Enables future local inference on consumer GPUs (RTX 3090/4090)"
        )
    elif int8_pass:
        return (
            "✅ INT8 APPROVED, NF4 rejected\n\n"
            "Recommendation: Use INT8 for production\n"
            "Reason: Safer quality preservation than NF4"
        )
    elif nf4_pass:
        return (
            "✅ NF4 APPROVED, INT8 rejected\n\n"
            "Recommendation: Use NF4 for production\n"
            "Reason: Passed quality gates, lower VRAM than rejected INT8"
        )
    else:
        return (
            "❌ Both INT8 and NF4 REJECTED\n\n"
            "Recommendation: Use FP16 baseline for production\n"
            "Reason: Quantization introduces unacceptable quality degradation"
        )


if __name__ == "__main__":
    main()
