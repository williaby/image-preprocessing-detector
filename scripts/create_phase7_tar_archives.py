#!/usr/bin/env python3
"""Create tar archives for Phase 7 v3 dataset upload to GCS.

Splits training data into 6 parts, plus 1 val and 1 test archive.
Each archive contains both images and metadata.
"""

import argparse
import json
import os
import tarfile
from pathlib import Path

from tqdm import tqdm


def split_list(lst: list, n_parts: int) -> list[list]:
    """Split a list into n roughly equal parts."""
    k, m = divmod(len(lst), n_parts)
    return [
        lst[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n_parts)
    ]


def create_tar_archive(
    archive_path: Path,
    images_dir: Path,
    metadata_items: list,
    split_name: str,
    part_num: int | None = None,
) -> dict:
    """Create a tar archive with images and metadata."""
    part_suffix = f"_part{part_num}" if part_num is not None else ""
    archive_name = f"phase7_v3_{split_name}{part_suffix}.tar.gz"
    archive_full_path = archive_path / archive_name

    print(f"\nCreating {archive_name}...")
    print(f"  Samples: {len(metadata_items):,}")

    # Create tar archive
    with tarfile.open(archive_full_path, "w:gz") as tar:
        # Add images
        for item in tqdm(metadata_items, desc="  Adding images"):
            img_filename = item["filename"]
            img_path = images_dir / img_filename
            if img_path.exists():
                # Store with relative path in archive
                tar.add(img_path, arcname=f"images/{img_filename}")

        # Save metadata to temp file and add to archive
        metadata_filename = f"{split_name}{part_suffix}_metadata.json"
        metadata_temp_path = archive_path / metadata_filename
        with open(metadata_temp_path, "w") as f:
            json.dump(metadata_items, f)
        tar.add(metadata_temp_path, arcname=metadata_filename)
        os.remove(metadata_temp_path)

    # Get archive size
    size_bytes = archive_full_path.stat().st_size
    size_gb = size_bytes / (1024**3)

    print(f"  Archive size: {size_gb:.2f} GB")

    return {
        "name": archive_name,
        "path": str(archive_full_path),
        "samples": len(metadata_items),
        "size_gb": round(size_gb, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Create Phase 7 v3 tar archives")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/iqa_phase7_150k_v3"),
        help="Path to dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/mnt/e/image_detection/iqa_phase7_150k_v3/archives"),
        help="Output directory for tar archives",
    )
    parser.add_argument(
        "--train-parts",
        type=int,
        default=6,
        help="Number of parts to split training data into",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip archives that already exist",
    )
    args = parser.parse_args()

    # Setup paths
    dataset_dir = args.dataset_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    images_dir = dataset_dir / "images"

    # Load metadata
    print("Loading metadata...")
    with open(dataset_dir / "train_metadata.json") as f:
        train_metadata = json.load(f)
    with open(dataset_dir / "val_metadata.json") as f:
        val_metadata = json.load(f)
    with open(dataset_dir / "test_metadata.json") as f:
        test_metadata = json.load(f)

    print(f"Train: {len(train_metadata):,}")
    print(f"Val: {len(val_metadata):,}")
    print(f"Test: {len(test_metadata):,}")
    print(f"Total: {len(train_metadata) + len(val_metadata) + len(test_metadata):,}")

    # Track all archives
    archives = []

    # Split training data into parts
    train_parts = split_list(train_metadata, args.train_parts)
    print(f"\nSplitting training data into {args.train_parts} parts:")
    for i, part in enumerate(train_parts, 1):
        print(f"  Part {i}: {len(part):,} samples")

    # Create training archives
    for i, part in enumerate(train_parts, 1):
        archive_name = f"phase7_v3_train_part{i}.tar.gz"
        archive_path = output_dir / archive_name
        if args.skip_existing and archive_path.exists():
            # Load existing archive info
            size_gb = round(archive_path.stat().st_size / (1024**3), 2)
            print(f"\nSkipping existing {archive_name} ({size_gb:.2f} GB)")
            archives.append(
                {
                    "name": archive_name,
                    "path": str(archive_path),
                    "samples": len(part),
                    "size_gb": size_gb,
                }
            )
            continue
        archive_info = create_tar_archive(
            output_dir, images_dir, part, "train", part_num=i
        )
        archives.append(archive_info)

    # Create validation archive
    val_archive_path = output_dir / "phase7_v3_val.tar.gz"
    if args.skip_existing and val_archive_path.exists():
        size_gb = round(val_archive_path.stat().st_size / (1024**3), 2)
        print(f"\nSkipping existing phase7_v3_val.tar.gz ({size_gb:.2f} GB)")
        archives.append(
            {
                "name": "phase7_v3_val.tar.gz",
                "path": str(val_archive_path),
                "samples": len(val_metadata),
                "size_gb": size_gb,
            }
        )
    else:
        archive_info = create_tar_archive(output_dir, images_dir, val_metadata, "val")
        archives.append(archive_info)

    # Create test archive
    test_archive_path = output_dir / "phase7_v3_test.tar.gz"
    if args.skip_existing and test_archive_path.exists():
        size_gb = round(test_archive_path.stat().st_size / (1024**3), 2)
        print(f"\nSkipping existing phase7_v3_test.tar.gz ({size_gb:.2f} GB)")
        archives.append(
            {
                "name": "phase7_v3_test.tar.gz",
                "path": str(test_archive_path),
                "samples": len(test_metadata),
                "size_gb": size_gb,
            }
        )
    else:
        archive_info = create_tar_archive(output_dir, images_dir, test_metadata, "test")
        archives.append(archive_info)

    # Summary
    print("\n" + "=" * 60)
    print("ARCHIVE SUMMARY")
    print("=" * 60)

    total_size = 0
    total_samples = 0
    for archive in archives:
        print(
            f"  {archive['name']}: {archive['samples']:,} samples, {archive['size_gb']:.2f} GB"
        )
        total_size += archive["size_gb"]
        total_samples += archive["samples"]

    print("-" * 60)
    print(f"  Total: {total_samples:,} samples, {total_size:.2f} GB")

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "version": "v3",
                "total_samples": total_samples,
                "total_size_gb": round(total_size, 2),
                "archives": archives,
            },
            f,
            indent=2,
        )
    print(f"\nManifest saved to: {manifest_path}")

    # Generate GCS upload commands
    print("\n" + "=" * 60)
    print("GCS UPLOAD COMMANDS")
    print("=" * 60)
    print("# Upload all archives to GCS:")
    for archive in archives:
        print(
            f"gsutil -m cp {archive['path']} gs://doc-quality-evaluation/datasets/phase7_v3/"
        )
    print("\n# Or upload the entire archives directory:")
    print(
        f"gsutil -m rsync -r {output_dir}/ gs://doc-quality-evaluation/datasets/phase7_v3/"
    )


if __name__ == "__main__":
    main()
