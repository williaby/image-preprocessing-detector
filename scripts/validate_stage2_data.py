#!/usr/bin/env python3
"""Validate Stage 2 DIQA dataset distributions and label quality.

This script checks for common data issues that can cause training failures:
- Imbalanced soft label distributions
- Missing or corrupted labels
- Dataset-specific quality issues
- Label-image consistency
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def analyze_soft_labels(split_file: Path) -> dict:
    """Analyze soft label distribution from JSONL split file."""
    print(f"\n{'=' * 60}")
    print(f"Analyzing: {split_file.name}")
    print(f"{'=' * 60}")

    samples = []
    with open(split_file) as f:
        for line in f:
            samples.append(json.loads(line))

    print(f"Total samples: {len(samples)}")

    # Aggregate soft labels
    all_soft_labels = []
    deqa_scores = []
    human_mos_scores = []
    datasets = {}

    for sample in samples:
        soft_label = sample.get("soft_label_10bin", [])
        if soft_label:
            all_soft_labels.append(soft_label)

        deqa_score = sample.get("deqa_predicted_score")
        if deqa_score:
            deqa_scores.append(deqa_score)

        human_mos = sample.get("human_mos")
        if human_mos and isinstance(human_mos, dict):
            overall = human_mos.get("overall")
            if overall:
                human_mos_scores.append(overall)

        # Track by dataset
        dataset = sample.get("source_dataset", "unknown")
        if dataset not in datasets:
            datasets[dataset] = []
        datasets[dataset].append(sample)

    # Convert to numpy for analysis
    all_soft_labels = np.array(all_soft_labels)
    deqa_scores = np.array(deqa_scores)
    human_mos_scores = np.array(human_mos_scores)

    print(f"\n📊 Label Statistics:")
    print(f"  Samples with soft labels: {len(all_soft_labels)}")
    print(f"  Samples with DEQA scores: {len(deqa_scores)}")
    print(f"  Samples with human MOS: {len(human_mos_scores)}")

    # Check soft label distribution
    print(f"\n📈 Soft Label Distribution (10 bins):")
    mean_per_bin = all_soft_labels.mean(axis=0)
    std_per_bin = all_soft_labels.std(axis=0)

    for i, (mean, std) in enumerate(zip(mean_per_bin, std_per_bin)):
        bar = "█" * int(mean * 50)
        print(f"  Bin {i}: {mean:.4f} ± {std:.4f} {bar}")

    # Check for imbalance
    max_bin = mean_per_bin.max()
    min_bin = mean_per_bin.min()
    imbalance_ratio = max_bin / (min_bin + 1e-8)
    print(f"\n⚖️  Imbalance Ratio: {imbalance_ratio:.2f}x (max/min)")
    if imbalance_ratio > 5:
        print(f"  ⚠️  WARNING: High imbalance detected!")

    # Check DEQA scores
    if len(deqa_scores) > 0:
        print(f"\n📉 DEQA Score Distribution:")
        print(f"  Mean: {deqa_scores.mean():.3f}")
        print(f"  Std:  {deqa_scores.std():.3f}")
        print(f"  Min:  {deqa_scores.min():.3f}")
        print(f"  Max:  {deqa_scores.max():.3f}")
        print(f"  Range: {deqa_scores.max() - deqa_scores.min():.3f}")

        # Histogram
        hist, bins = np.histogram(deqa_scores, bins=10, range=(1, 5))
        print(f"\n  Histogram (1-5 scale):")
        for i, (count, start) in enumerate(zip(hist, bins[:-1])):
            bar = "█" * int(count / hist.max() * 30)
            print(f"    {start:.1f}-{bins[i + 1]:.1f}: {count:4d} {bar}")

    # Check human MOS
    if len(human_mos_scores) > 0:
        print(f"\n👥 Human MOS Distribution:")
        print(f"  Samples: {len(human_mos_scores)}")
        print(f"  Mean: {human_mos_scores.mean():.3f}")
        print(f"  Std:  {human_mos_scores.std():.3f}")
        print(f"  Range: {human_mos_scores.min():.3f} - {human_mos_scores.max():.3f}")

    # Per-dataset analysis
    print(f"\n📁 Per-Dataset Breakdown:")
    for dataset_name, dataset_samples in sorted(datasets.items()):
        print(f"\n  {dataset_name}: {len(dataset_samples)} samples")

        dataset_deqa = [
            s["deqa_predicted_score"]
            for s in dataset_samples
            if "deqa_predicted_score" in s
        ]
        if dataset_deqa:
            dataset_deqa = np.array(dataset_deqa)
            print(
                f"    DEQA mean: {dataset_deqa.mean():.3f} ± {dataset_deqa.std():.3f}"
            )
            print(
                f"    DEQA range: {dataset_deqa.min():.3f} - {dataset_deqa.max():.3f}"
            )

        # Check for potential issues
        has_mos = sum(
            1
            for s in dataset_samples
            if s.get("human_mos") and isinstance(s.get("human_mos"), dict)
        )
        print(
            f"    Human MOS: {has_mos}/{len(dataset_samples)} ({has_mos / len(dataset_samples) * 100:.1f}%)"
        )

    return {
        "total_samples": len(samples),
        "datasets": {k: len(v) for k, v in datasets.items()},
        "soft_label_stats": {
            "mean_per_bin": mean_per_bin.tolist(),
            "std_per_bin": std_per_bin.tolist(),
            "imbalance_ratio": float(imbalance_ratio),
        },
        "deqa_stats": {
            "mean": float(deqa_scores.mean()),
            "std": float(deqa_scores.std()),
            "range": float(deqa_scores.max() - deqa_scores.min()),
        }
        if len(deqa_scores) > 0
        else {},
    }


def main():
    """Run validation on all splits."""
    data_dir = Path("/home/byron/dev/image_detection")

    # Check local splits (if downloaded from Modal volume)
    splits_dir = data_dir / "stage2_diqa_ensemble" / "splits"

    if not splits_dir.exists():
        print(f"❌ Splits directory not found: {splits_dir}")
        print(f"\nTo download from Modal volume:")
        print(
            f"  poetry run modal volume get stage2-training-data stage2_diqa_ensemble/splits ./stage2_diqa_ensemble/splits"
        )
        return

    results = {}
    for split in ["train", "val", "test"]:
        split_file = splits_dir / f"{split}.jsonl"
        if split_file.exists():
            results[split] = analyze_soft_labels(split_file)

    # Summary
    print(f"\n{'=' * 60}")
    print("📋 SUMMARY")
    print(f"{'=' * 60}")

    for split, stats in results.items():
        print(f"\n{split.upper()}:")
        print(f"  Total samples: {stats['total_samples']}")
        print(f"  Datasets: {stats['datasets']}")
        if stats.get("soft_label_stats"):
            imbalance = stats["soft_label_stats"]["imbalance_ratio"]
            print(f"  Soft label imbalance: {imbalance:.2f}x")
            if imbalance > 5:
                print(f"    ⚠️  HIGH IMBALANCE - may cause training issues")

    # Check for critical issues
    print(f"\n🔍 Recommendations:")

    train_stats = results.get("train", {})
    if train_stats.get("soft_label_stats", {}).get("imbalance_ratio", 0) > 5:
        print(f"  ⚠️  Consider rebalancing soft labels or using class weights")

    # Check dataset sizes
    train_datasets = train_stats.get("datasets", {})
    if train_datasets:
        min_size = min(train_datasets.values())
        max_size = max(train_datasets.values())
        if max_size / (min_size + 1) > 10:
            print(f"  ⚠️  Dataset size imbalance: {min_size} to {max_size} samples")
            print(f"      Consider weighted sampling or balancing")


if __name__ == "__main__":
    main()
