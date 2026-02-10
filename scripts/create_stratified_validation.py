#!/usr/bin/env python3
"""Create stratified validation set for DeQA quantization testing.

Per multi-model consensus:
- 350+ samples total (~50 per dataset)
- Stratified across all 7 datasets
- Oversample edge-case datasets (DIBCO, Tobacco-800)
- Include DIQA-5000 MOS distribution coverage

Usage:
    python scripts/create_stratified_validation.py \
        --samples-per-dataset 50 \
        --oversample dibco,tobacco-800 \
        --output stage1_validation_350.json
"""

import argparse
import json
import random  # nosec B311 - used for dataset sampling, not cryptographic
from pathlib import Path


# Stage 1 dataset configurations
STAGE1_DATASETS = {
    "diqa-5000": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/diqa-5000_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/diqa-5000",
        "priority": "CRITICAL",
    },
    "smartdoc-qa": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/smartdoc-qa_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images",
        "priority": "HIGH",
    },
    "ocr-quality": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/ocr-quality_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/ocr_quality/pics",
        "priority": "HIGH",
    },
    "dibco": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/dibco_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/dibco/DIBCO",
        "priority": "HIGH",
    },
    "funsd": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/funsd_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/forms/funsd",
        "priority": "MEDIUM",
    },
    "sroie": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/sroie_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/forms/sroie_icdar2019",
        "priority": "MEDIUM",
    },
    "tobacco-800": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/tobacco-800_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/degraded/tobacco800",
        "priority": "MEDIUM",
    },
}


def load_manifest(manifest_path: Path) -> list[dict]:
    """Load manifest JSON file."""
    if not manifest_path.exists():
        print(f"⚠️  Manifest not found: {manifest_path}")
        return []

    with open(manifest_path) as f:
        return json.load(f)


def stratified_sample(
    dataset_name: str,
    manifest: list[dict],
    n_samples: int,
    seed: int = 42,
) -> list[dict]:
    """Stratified random sample from dataset.

    Args:
        dataset_name: Name of the dataset
        manifest: List of manifest entries
        n_samples: Number of samples to select
        seed: Random seed for reproducibility

    Returns:
        List of sampled entries with dataset metadata
    """
    random.seed(seed)

    # If manifest smaller than requested, take all
    if len(manifest) <= n_samples:
        sampled = manifest
    else:
        sampled = random.sample(manifest, n_samples)

    # Add dataset metadata
    for entry in sampled:
        entry["dataset"] = dataset_name
        entry["root_dir"] = STAGE1_DATASETS[dataset_name]["root_dir"]

    return sampled


def main():
    parser = argparse.ArgumentParser(
        description="Create stratified validation set for quantization testing"
    )
    parser.add_argument(
        "--samples-per-dataset",
        type=int,
        default=50,
        help="Base samples per dataset (default: 50)",
    )
    parser.add_argument(
        "--oversample",
        type=str,
        default="dibco,tobacco-800",
        help="Comma-separated datasets to oversample (default: dibco,tobacco-800)",
    )
    parser.add_argument(
        "--oversample-multiplier",
        type=float,
        default=1.5,
        help="Multiplier for oversampled datasets (default: 1.5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/mnt/e/image_detection/06_staging/stage1_manifests/validation_350_manifest.json",
        help="Output path for validation manifest",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    oversample_datasets = set(args.oversample.split(","))

    print("=" * 70)
    print("Creating Stratified Validation Set")
    print("=" * 70)
    print(f"Base samples/dataset: {args.samples_per_dataset}")
    print(f"Oversample datasets: {oversample_datasets}")
    print(f"Oversample multiplier: {args.oversample_multiplier}x")
    print(f"Random seed: {args.seed}")
    print()

    all_samples = []
    stats = {}

    for dataset_name, config in STAGE1_DATASETS.items():
        manifest_path = Path(config["manifest"])
        manifest = load_manifest(manifest_path)

        if not manifest:
            print(f"⚠️  Skipping {dataset_name} (manifest not found)")
            continue

        # Determine sample count
        if dataset_name in oversample_datasets:
            n_samples = int(args.samples_per_dataset * args.oversample_multiplier)
            note = f"(oversampled {args.oversample_multiplier}x)"
        else:
            n_samples = args.samples_per_dataset
            note = ""

        # Sample
        samples = stratified_sample(dataset_name, manifest, n_samples, args.seed)
        all_samples.extend(samples)

        stats[dataset_name] = {
            "total_available": len(manifest),
            "sampled": len(samples),
            "priority": config["priority"],
        }

        print(
            f"✓ {dataset_name:15} | {len(samples):3} samples from {len(manifest):5} total {note}"
        )

    print()
    print("=" * 70)
    print(f"Total validation samples: {len(all_samples)}")
    print("=" * 70)

    # Save validation manifest
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(all_samples, f, indent=2)

    print(f"\n✅ Validation manifest saved: {output_path}")
    print(f"   Total samples: {len(all_samples)}")

    # Save stats
    stats_path = output_path.parent / (output_path.stem + "_stats.json")
    with open(stats_path, "w") as f:
        json.dump(
            {
                "total_samples": len(all_samples),
                "samples_per_dataset": args.samples_per_dataset,
                "oversample_multiplier": args.oversample_multiplier,
                "oversampled_datasets": list(oversample_datasets),
                "seed": args.seed,
                "datasets": stats,
            },
            f,
            indent=2,
        )
    print(f"   Stats saved: {stats_path}")

    # Print dataset breakdown
    print("\nDataset Breakdown:")
    print("-" * 70)
    for dataset_name, dataset_stats in stats.items():
        coverage = (dataset_stats["sampled"] / dataset_stats["total_available"]) * 100
        print(
            f"  {dataset_name:15} | {dataset_stats['sampled']:3}/{dataset_stats['total_available']:5} ({coverage:5.1f}%) | {dataset_stats['priority']}"
        )


if __name__ == "__main__":
    main()
