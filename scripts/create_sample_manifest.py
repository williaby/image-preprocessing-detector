#!/usr/bin/env python3
"""Create a 100-item sample manifest for Modal test run.

Takes a stratified sample from each Stage 1 dataset proportional to size.
"""

import json
import random  # nosec B311 - used for dataset sampling, not cryptographic
from pathlib import Path

# Stage 1 dataset manifests
MANIFESTS = {
    "diqa-5000": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/diqa-5000_manifest.json"
    ),
    "smartdoc-qa": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/smartdoc-qa_manifest.json"
    ),
    "ocr-quality": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/ocr-quality_manifest.json"
    ),
    "dibco": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/dibco_manifest.json"
    ),
    "funsd": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/funsd_manifest.json"
    ),
    "sroie": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/sroie_manifest.json"
    ),
    "tobacco-800": Path(
        "/mnt/e/image_detection/06_staging/stage1_manifests/tobacco-800_manifest.json"
    ),
}

# Root directories for each dataset
ROOT_DIRS = {
    "diqa-5000": "/mnt/e/image_detection/02_benchmark_only/diqa-5000",
    "smartdoc-qa": "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images",
    "ocr-quality": "/mnt/e/image_detection/01_base_data/ocr_quality/pics",
    "dibco": "/mnt/e/image_detection/02_benchmark_only/dibco/DIBCO",
    "funsd": "/mnt/e/image_detection/01_base_data/forms/funsd",
    "sroie": "/mnt/e/image_detection/01_base_data/forms/sroie_icdar2019",
    "tobacco-800": "/mnt/e/image_detection/01_base_data/degraded/tobacco800",
}

TOTAL_SAMPLE = 100
OUTPUT_DIR = Path("/mnt/e/image_detection/06_staging/stage1_manifests")


def main():
    random.seed(42)  # Reproducible sampling

    # Load all manifests and count images
    all_data = {}
    total_images = 0

    for name, manifest_path in MANIFESTS.items():
        with open(manifest_path) as f:
            data = json.load(f)
        all_data[name] = data
        total_images += len(data)
        print(f"{name}: {len(data)} images")

    print(f"\nTotal: {total_images} images")
    print(f"Sample size: {TOTAL_SAMPLE} images")

    # Calculate proportional samples
    samples_per_dataset = {}
    remaining = TOTAL_SAMPLE

    for name, data in all_data.items():
        proportion = len(data) / total_images
        n_samples = max(1, round(proportion * TOTAL_SAMPLE))  # At least 1 per dataset
        samples_per_dataset[name] = min(n_samples, len(data), remaining)
        remaining -= samples_per_dataset[name]

    # Adjust if we're over/under
    while sum(samples_per_dataset.values()) < TOTAL_SAMPLE:
        # Add to largest dataset
        largest = max(all_data.keys(), key=lambda k: len(all_data[k]))
        if samples_per_dataset[largest] < len(all_data[largest]):
            samples_per_dataset[largest] += 1

    while sum(samples_per_dataset.values()) > TOTAL_SAMPLE:
        # Remove from smallest allocation (but keep at least 1)
        for name in sorted(
            samples_per_dataset.keys(), key=lambda k: samples_per_dataset[k]
        ):
            if samples_per_dataset[name] > 1:
                samples_per_dataset[name] -= 1
                break

    print("\nSamples per dataset:")
    for name, n in samples_per_dataset.items():
        print(f"  {name}: {n}")

    # Create combined sample manifest
    combined_manifest = []
    sample_summary = {}

    for name, n_samples in samples_per_dataset.items():
        data = all_data[name]
        sampled = random.sample(data, n_samples)

        for item in sampled:
            combined_manifest.append(
                {
                    "image": item["image"],
                    "dataset": name,
                    "root_dir": ROOT_DIRS[name],
                }
            )

        sample_summary[name] = {
            "sampled": n_samples,
            "total": len(data),
            "root_dir": ROOT_DIRS[name],
        }

    # Shuffle the combined manifest
    random.shuffle(combined_manifest)

    # Save combined manifest
    sample_manifest_path = OUTPUT_DIR / "sample_100_manifest.json"
    with open(sample_manifest_path, "w") as f:
        json.dump(combined_manifest, f, indent=2)

    print(f"\nSample manifest saved to: {sample_manifest_path}")

    # Save summary
    summary = {
        "total_samples": len(combined_manifest),
        "datasets": sample_summary,
        "seed": 42,
    }

    summary_path = OUTPUT_DIR / "sample_100_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary saved to: {summary_path}")

    # Print sample entries
    print("\nFirst 5 sample entries:")
    for entry in combined_manifest[:5]:
        print(f"  {entry['dataset']}: {entry['image']}")


if __name__ == "__main__":
    main()
