"""Create tarballs for Stage 1 datasets (max 4GB each).

This creates tarballs organized by dataset and split, storing them on E: drive
to maintain a complete training trail.

Output structure:
    /mnt/e/image_detection/06_staging/stage1_tarballs/
        diqa-5000_part1.tar.gz
        diqa-5000_part2.tar.gz
        smartdoc-qa_part1.tar.gz
        smartdoc-qa_part2.tar.gz
        smartdoc-qa_part3.tar.gz
        smartdoc-qa_part4.tar.gz
        sroie_part1.tar.gz
        tobacco-800_part1.tar.gz
        funsd_part1.tar.gz
        manifest.json  (maps tarball -> images)
"""

import json
import subprocess
import tarfile
from pathlib import Path

# Maximum tarball size (4GB)
MAX_TARBALL_SIZE = 4 * 1024**3

# Dataset configurations
DATASETS = {
    "diqa-5000": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/diqa-5000_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/diqa-5000",
    },
    "smartdoc-qa": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/smartdoc-qa_manifest.json",
        "root_dir": "/mnt/e/image_detection/02_benchmark_only/smartdoc-qa/Dataset SmartDoc-QA/Captured_Images",
    },
    "sroie": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/sroie_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/forms/sroie",
    },
    "tobacco-800": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/tobacco-800_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/degraded/tobacco800",
    },
    "funsd": {
        "manifest": "/mnt/e/image_detection/06_staging/stage1_manifests/funsd_manifest.json",
        "root_dir": "/mnt/e/image_detection/01_base_data/forms/funsd",
    },
}

# Output directory
OUTPUT_DIR = Path("/mnt/e/image_detection/06_staging/stage1_tarballs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_tarballs_for_dataset(dataset_name: str, config: dict) -> list[dict]:
    """Create tarballs for a single dataset, splitting if needed.

    Returns:
        List of tarball metadata dicts with {filename, images, size_gb}
    """
    # Load manifest
    with open(config["manifest"]) as f:
        entries = json.load(f)

    root_dir = Path(config["root_dir"])

    # Get all valid image paths and sizes
    image_files = []
    for entry in entries:
        image_path = root_dir / entry["image"]
        if image_path.exists():
            image_files.append({
                "relative_path": entry["image"],
                "full_path": str(image_path),
                "size": image_path.stat().st_size,
            })

    if not image_files:
        print(f"⚠️  {dataset_name}: No valid images found, skipping")
        return []

    # Sort by size (largest first) for better packing
    image_files.sort(key=lambda x: -x["size"])

    # Pack into tarballs using greedy bin packing
    tarballs = []
    current_tarball = {
        "images": [],
        "size": 0,
    }

    for img in image_files:
        # If adding this would exceed limit, start new tarball
        if current_tarball["images"] and (current_tarball["size"] + img["size"]) > MAX_TARBALL_SIZE:
            tarballs.append(current_tarball)
            current_tarball = {"images": [], "size": 0}

        current_tarball["images"].append(img)
        current_tarball["size"] += img["size"]

    # Add final tarball
    if current_tarball["images"]:
        tarballs.append(current_tarball)

    # Create tarball files
    tarball_metadata = []
    for idx, tarball_data in enumerate(tarballs, start=1):
        part_suffix = f"_part{idx}" if len(tarballs) > 1 else ""
        tarball_filename = f"{dataset_name}{part_suffix}.tar.gz"
        tarball_path = OUTPUT_DIR / tarball_filename

        print(f"Creating {tarball_filename} ({len(tarball_data['images'])} images, "
              f"{tarball_data['size']/(1024**3):.2f} GB)...")

        # Create tarball
        with tarfile.open(tarball_path, "w:gz") as tar:
            for img in tarball_data["images"]:
                # Store with dataset-relative path (preserving structure)
                arcname = f"{dataset_name}/{img['relative_path']}"
                tar.add(img["full_path"], arcname=arcname)

        tarball_metadata.append({
            "filename": tarball_filename,
            "dataset": dataset_name,
            "part": idx,
            "total_parts": len(tarballs),
            "image_count": len(tarball_data["images"]),
            "images": [img["relative_path"] for img in tarball_data["images"]],
            "size_bytes": tarball_data["size"],
            "size_gb": tarball_data["size"] / (1024**3),
            "tarball_size_bytes": tarball_path.stat().st_size,
            "tarball_size_gb": tarball_path.stat().st_size / (1024**3),
        })

    return tarball_metadata


def main():
    """Create all tarballs and generate manifest."""
    print("=" * 80)
    print("Creating Stage 1 Tarballs (4GB max each)")
    print("=" * 80)

    all_metadata = []

    for dataset_name, config in DATASETS.items():
        print(f"\n{dataset_name}:")
        print("-" * 80)
        metadata = create_tarballs_for_dataset(dataset_name, config)
        all_metadata.extend(metadata)

    # Save manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(all_metadata, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_tarballs = len(all_metadata)
    total_images = sum(m["image_count"] for m in all_metadata)
    total_size_gb = sum(m["tarball_size_gb"] for m in all_metadata)

    print(f"Total tarballs: {total_tarballs}")
    print(f"Total images: {total_images:,}")
    print(f"Total size: {total_size_gb:.2f} GB")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
