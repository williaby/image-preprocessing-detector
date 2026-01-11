#!/usr/bin/env python3
"""Prepare metadata manifests for Stage 1 DeQA-Doc inference.

This script generates JSON manifest files required by DeQA-Doc's iqa_eval.py
for each Stage 1 dataset.

Usage:
    python scripts/stage1_prepare_manifests.py

    # Prepare specific dataset only
    python scripts/stage1_prepare_manifests.py --dataset diqa-5000

Output:
    Creates JSON files in output_dir:
    - diqa-5000_manifest.json
    - smartdoc-qa_manifest.json
    - ocr-quality_manifest.json
    - dibco_manifest.json
    - funsd_manifest.json
    - sroie_manifest.json
    - tobacco-800_manifest.json
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatasetConfig:
    """Configuration for a Stage 1 dataset."""

    name: str
    root_dir: Path
    image_patterns: list[str]  # Glob patterns to find images
    priority: str = "HIGH"
    notes: str = ""


# Stage 1 Dataset Configurations
STAGE1_DATASETS: dict[str, DatasetConfig] = {
    "diqa-5000": DatasetConfig(
        name="diqa-5000",
        root_dir=Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000"),
        image_patterns=["train/res/*.jpg", "test/res/*.jpg", "val/res/*.jpg"],
        priority="CRITICAL",
        notes="Primary anchor with 3-dim human MOS scores (5,000 images)",
    ),
    "smartdoc-qa": DatasetConfig(
        name="smartdoc-qa",
        root_dir=Path(
            "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images"
        ),
        image_patterns=["**/*.jpg"],
        priority="HIGH",
        notes="OCR correlation validation (4,260 images)",
    ),
    "ocr-quality": DatasetConfig(
        name="ocr-quality",
        root_dir=Path("/mnt/e/image_detection/01_base_data/ocr_quality/pics"),
        image_patterns=["*.png"],
        priority="HIGH",
        notes="Human quality scores (1-4), multilingual (1,000 images)",
    ),
    "dibco": DatasetConfig(
        name="dibco",
        root_dir=Path("/mnt/e/image_detection/02_benchmark_only/dibco/DIBCO"),
        image_patterns=["**/*.png", "**/*.jpg", "**/*.tif", "**/*.bmp"],
        priority="HIGH",
        notes="Extreme degradation edge cases (148 images)",
    ),
    "funsd": DatasetConfig(
        name="funsd",
        root_dir=Path("/mnt/e/image_detection/01_base_data/forms/funsd"),
        image_patterns=["**/*.jpg", "**/*.png"],
        priority="MEDIUM",
        notes="Real noisy scanned forms (149 images)",
    ),
    "sroie": DatasetConfig(
        name="sroie",
        root_dir=Path("/mnt/e/image_detection/01_base_data/forms/sroie"),
        image_patterns=["**/*.jpg"],
        priority="MEDIUM",
        notes="Mobile capture / thermal print (2,043 images)",
    ),
    "tobacco-800": DatasetConfig(
        name="tobacco-800",
        root_dir=Path("/mnt/e/image_detection/01_base_data/degraded/tobacco800"),
        image_patterns=["**/*.tif", "**/*.jpg", "**/*.png"],
        priority="MEDIUM",
        notes="Real archival degradation (1,290 images)",
    ),
}


def discover_images(config: DatasetConfig) -> list[Path]:
    """Discover all images for a dataset based on its configuration."""
    images = []
    valid_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

    for pattern in config.image_patterns:
        for path in config.root_dir.glob(pattern):
            if path.suffix.lower() in valid_extensions and path.is_file():
                images.append(path)

    return sorted(set(images))


def create_manifest(config: DatasetConfig, output_dir: Path) -> dict:
    """Create a manifest JSON file for DeQA-Doc inference.

    Args:
        config: Dataset configuration
        output_dir: Directory to save manifest

    Returns:
        Dict with statistics
    """
    print(f"\nProcessing: {config.name}")
    print(f"  Root: {config.root_dir}")
    print(f"  Priority: {config.priority}")

    # Discover images
    images = discover_images(config)
    print(f"  Found: {len(images)} images")

    if not images:
        print("  WARNING: No images found!")
        return {"dataset": config.name, "images": 0, "manifest": None}

    # Create manifest entries
    # DeQA-Doc expects: [{"image": "relative/path/to/image.jpg"}, ...]
    manifest = []
    for image_path in images:
        rel_path = image_path.relative_to(config.root_dir)
        manifest.append({"image": str(rel_path)})

    # Save manifest
    manifest_path = output_dir / f"{config.name}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  Manifest: {manifest_path}")

    return {
        "dataset": config.name,
        "images": len(images),
        "manifest": str(manifest_path),
        "root_dir": str(config.root_dir),
        "priority": config.priority,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Prepare metadata manifests for Stage 1 DeQA-Doc inference"
    )

    parser.add_argument(
        "--dataset",
        type=str,
        choices=list(STAGE1_DATASETS.keys()),
        help="Process specific dataset only",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/mnt/e/image_detection/06_staging/stage1_manifests",
        help="Output directory for manifests",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available datasets and exit"
    )

    args = parser.parse_args()

    # List datasets
    if args.list:
        print("\nStage 1 Datasets:")
        print("-" * 80)
        total = 0
        for name, config in STAGE1_DATASETS.items():
            images = discover_images(config)
            total += len(images)
            print(
                f"  {name:15} | {len(images):6} images | {config.priority:8} | {config.notes[:40]}"
            )
        print("-" * 80)
        print(f"  {'TOTAL':15} | {total:6} images")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which datasets to process
    if args.dataset:
        datasets = [STAGE1_DATASETS[args.dataset]]
    else:
        datasets = list(STAGE1_DATASETS.values())

    # Process each dataset
    all_stats = []
    for config in datasets:
        stats = create_manifest(config, output_dir)
        all_stats.append(stats)

    # Summary
    print("\n" + "=" * 60)
    print("MANIFEST GENERATION COMPLETE")
    print("=" * 60)

    total_images = sum(s["images"] for s in all_stats)
    print(f"Total images: {total_images}")
    print(f"Output directory: {output_dir}")

    # Save summary with inference commands
    summary = {
        "datasets": all_stats,
        "total_images": total_images,
        "inference_commands": [],
    }

    # Generate inference commands
    print("\n" + "-" * 60)
    print("INFERENCE COMMANDS (run from DeQA-Score directory):")
    print("-" * 60)

    for stats in all_stats:
        if stats["manifest"]:
            cmd = f"""
# {stats["dataset"]} ({stats["images"]} images)
python src/evaluate/iqa_eval.py \\
    --model-path zhalala/DeQA-Doc-Mix \\
    --meta-paths {stats["manifest"]} \\
    --root-dir {stats["root_dir"]} \\
    --save-dir /mnt/e/image_detection/06_staging/stage1_deqa_labels \\
    --level-names excellent good fair poor bad \\
    --with-prob True \\
    --device cuda:0 \\
    --batch-size 4
"""
            print(cmd)
            summary["inference_commands"].append(
                {
                    "dataset": stats["dataset"],
                    "command": cmd.strip(),
                }
            )

    # Save summary
    summary_path = output_dir / "stage1_manifest_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")

    # Create a combined run script
    run_script_path = output_dir / "run_stage1_inference.sh"
    with open(run_script_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Stage 1 DeQA-Doc Inference Script\n")
        f.write("# Generated by stage1_prepare_manifests.py\n\n")
        f.write("set -e\n\n")
        f.write("cd /home/byron/dev/DeQA-Doc/DeQA-Score\n")
        f.write("export PYTHONPATH=./:$PYTHONPATH\n\n")
        f.write("OUTPUT_DIR=/mnt/e/image_detection/06_staging/stage1_deqa_labels\n")
        f.write("mkdir -p $OUTPUT_DIR\n\n")

        for stats in all_stats:
            if stats["manifest"]:
                dataset_name = stats["dataset"]
                num_images = stats["images"]
                manifest_path = stats["manifest"]
                root_dir = stats["root_dir"]
                f.write(f"# {dataset_name} ({num_images} images)\n")
                f.write(f"echo 'Processing {dataset_name}...'\n")
                f.write("python src/evaluate/iqa_eval.py \\\n")
                f.write("    --model-path zhalala/DeQA-Doc-Mix \\\n")
                f.write(f"    --meta-paths {manifest_path} \\\n")
                f.write(f"    --root-dir {root_dir} \\\n")
                f.write("    --save-dir $OUTPUT_DIR \\\n")
                f.write("    --level-names excellent good fair poor bad \\\n")
                f.write("    --with-prob True \\\n")
                f.write("    --device cuda:0 \\\n")
                f.write("    --batch-size 4\n\n")

        f.write("echo 'Stage 1 inference complete!'\n")

    run_script_path.chmod(0o755)
    print(f"Run script saved to: {run_script_path}")


if __name__ == "__main__":
    main()
