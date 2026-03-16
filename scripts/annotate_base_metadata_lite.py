#!/usr/bin/env python3
"""Lightweight base metadata annotation script (stdlib-only).

Designed to run on remote servers without heavy ML dependencies.
Extracts: file metadata, SHA256, image dimensions, parser labels.
Outputs JSON compatible with annotate_base_metadata.py schema.

Usage:
    python3 annotate_base_metadata_lite.py --dataset docreal \
        --base-dir /path/to/01_base_data \
        --output-dir /path/to/output

    # Process all correction datasets
    python3 annotate_base_metadata_lite.py --all-correction \
        --base-dir /path/to/01_base_data \
        --output-dir /path/to/output
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import uuid
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path


# =============================================================================
# Dataset Configurations (correction datasets only)
# =============================================================================

CORRECTION_DATASETS: dict[str, dict] = {
    "anyphotodoc6300": {
        "path_suffix": "correction/anyphotodoc6300",
        "pattern": "init_*/*.[jJ][pP][gG]",
        "capture_method": "camera_smartphone",
        "domain": "unknown",
    },
    "docalign12k": {
        "path_suffix": "correction/docalign12k",
        "pattern": "distorted_hard/**/*.jpg",
        "capture_method": "synthetic",
        "domain": "unknown",
    },
    "wsrd": {
        "path_suffix": "correction/wsrd",
        "pattern": "**/*.png",
        "capture_method": "camera_smartphone",
        "domain": "unknown",
    },
    "warpdoc": {
        "path_suffix": "correction/warpdoc",
        "pattern": "WarpDoc/image/**/*.jpg",
        "capture_method": "camera_smartphone",
        "domain": "unknown",
    },
    "docreal": {
        "path_suffix": "correction/docreal",
        "pattern": "DocReal/distorted/*.png",
        "capture_method": "camera_smartphone",
        "domain": "unknown",
    },
    "sd7k": {
        "path_suffix": "correction/sd7k",
        "pattern": "**/input/*.png",
        "capture_method": "camera_smartphone",
        "domain": "unknown",
    },
}


# =============================================================================
# Image dimension readers (stdlib only - no PIL/OpenCV)
# =============================================================================


def get_png_dimensions(filepath: Path) -> tuple[int, int] | None:
    """Read PNG dimensions from IHDR chunk."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(24)
            if header[:8] != b"\x89PNG\r\n\x1a\n":
                return None
            width = struct.unpack(">I", header[16:20])[0]
            height = struct.unpack(">I", header[20:24])[0]
            return width, height
    except (OSError, struct.error):
        return None


def get_jpeg_dimensions(filepath: Path) -> tuple[int, int] | None:
    """Read JPEG dimensions from SOF marker."""
    try:
        with open(filepath, "rb") as f:
            data = f.read(2)
            if data != b"\xff\xd8":
                return None
            while True:
                marker = f.read(2)
                if len(marker) < 2:
                    return None
                if marker[0] != 0xFF:
                    return None
                # SOF markers (0xC0-0xCF except 0xC4 DHT and 0xCC DAC)
                if marker[1] in (
                    0xC0,
                    0xC1,
                    0xC2,
                    0xC3,
                    0xC5,
                    0xC6,
                    0xC7,
                    0xC9,
                    0xCA,
                    0xCB,
                    0xCD,
                    0xCE,
                    0xCF,
                ):
                    length_data = f.read(2)
                    if len(length_data) < 2:
                        return None
                    f.read(1)  # precision
                    height_data = f.read(2)
                    width_data = f.read(2)
                    if len(height_data) < 2 or len(width_data) < 2:
                        return None
                    height = struct.unpack(">H", height_data)[0]
                    width = struct.unpack(">H", width_data)[0]
                    return width, height
                # Skip this segment
                length_data = f.read(2)
                if len(length_data) < 2:
                    return None
                length = struct.unpack(">H", length_data)[0]
                f.seek(length - 2, 1)
    except (OSError, struct.error):
        return None


_JPEG_EXTENSIONS = frozenset({".jpg", ".jpeg"})


def get_image_dimensions(filepath: Path) -> tuple[int, int] | None:
    """Get image dimensions without PIL."""
    suffix = filepath.suffix.lower()
    if suffix == ".png":
        return get_png_dimensions(filepath)
    if suffix in _JPEG_EXTENSIONS:
        return get_jpeg_dimensions(filepath)
    return None


# =============================================================================
# Label parsers (correction datasets)
# =============================================================================


def parse_anyphotodoc6300_labels(dataset_path: Path, image_path: Path) -> dict:
    """Parse AnyPhotoDoc6300 labels."""
    labels: dict = {"source": "anyphotodoc6300", "capture_method": "camera_smartphone"}
    for part in image_path.relative_to(dataset_path).parts:
        if part.startswith("init_"):
            labels["image_type"] = "input_distorted"
            labels["batch"] = part
            break
        if part == "flat":
            labels["image_type"] = "ground_truth"
            break
    return labels


def parse_docalign12k_labels(dataset_path: Path, image_path: Path) -> dict:
    """Parse DocAlign12k labels."""
    labels: dict = {"source": "docalign12k", "capture_method": "camera_smartphone"}
    for part in image_path.relative_to(dataset_path).parts:
        if part.lower() in ("train", "test", "val", "validation"):
            labels["split"] = part.lower()
        if part.lower() == "input":
            labels["image_type"] = "input_distorted"
        elif part.lower() == "target":
            labels["image_type"] = "ground_truth"
    return labels


def parse_wsrd_labels(dataset_path: Path, image_path: Path) -> dict:
    """Parse WSRD labels."""
    labels: dict = {
        "source": "wsrd",
        "capture_method": "camera_smartphone",
        "is_degraded": True,
        "degradation_type": "shadow",
    }
    for part in image_path.relative_to(dataset_path).parts:
        if part.startswith("ntire"):
            labels["challenge_year"] = part
        if "_input" in part.lower():
            labels["image_type"] = "input_shadow"
            split = part.lower().replace("_input", "")
            if split in ("train", "val", "test"):
                labels["split"] = split
        elif "_gt" in part.lower():
            labels["image_type"] = "ground_truth"
            split = part.lower().replace("_gt", "")
            if split in ("train", "val", "test"):
                labels["split"] = split
    return labels


def parse_warpdoc_labels(dataset_path: Path, image_path: Path) -> dict:
    """Parse WarpDoc labels."""
    labels: dict = {"source": "warpdoc", "capture_method": "camera_smartphone"}
    for part in image_path.relative_to(dataset_path).parts:
        if part == "image":
            labels["image_type"] = "input_warped"
        elif part == "digital":
            labels["image_type"] = "ground_truth"
        elif part == "digital_margin":
            labels["image_type"] = "ground_truth_margin"
        if part.lower() in (
            "curved",
            "fold",
            "incomplete",
            "perspective",
            "random",
            "rotate",
        ):
            labels["distortion_type"] = part.lower()
    return labels


def parse_docreal_labels(dataset_path: Path, image_path: Path) -> dict:
    """Parse DocReal labels."""
    labels: dict = {"source": "docreal", "capture_method": "camera_smartphone"}
    parent = image_path.parent.name
    if parent == "distorted":
        labels["image_type"] = "input_distorted"
    elif parent == "scanned":
        labels["image_type"] = "ground_truth"
    return labels


def parse_sd7k_labels(dataset_path: Path, image_path: Path) -> dict:
    """Parse SD7K labels."""
    labels: dict = {
        "source": "sd7k",
        "capture_method": "camera_smartphone",
        "is_degraded": True,
        "degradation_type": "shadow",
    }
    for part in image_path.relative_to(dataset_path).parts:
        if part.lower() in ("train", "test"):
            labels["split"] = part.lower()
        if part.lower() == "input":
            labels["image_type"] = "input_shadow"
        elif part.lower() == "target":
            labels["image_type"] = "ground_truth"
    return labels


LABEL_PARSERS = {
    "anyphotodoc6300": parse_anyphotodoc6300_labels,
    "docalign12k": parse_docalign12k_labels,
    "wsrd": parse_wsrd_labels,
    "warpdoc": parse_warpdoc_labels,
    "docreal": parse_docreal_labels,
    "sd7k": parse_sd7k_labels,
}


# =============================================================================
# File matching (supports glob patterns with ** and character classes)
# =============================================================================


def matches_pattern(filepath: Path, base_dir: Path, pattern: str) -> bool:
    """Check if filepath matches the glob pattern relative to base_dir."""
    rel = str(filepath.relative_to(base_dir))
    # Handle ** globstar
    if "**" in pattern:
        # Split on ** and match parts
        parts = pattern.split("**")
        if len(parts) == 2:
            prefix, suffix = parts
            prefix = prefix.rstrip("/")
            suffix = suffix.lstrip("/")
            if prefix and not rel.startswith(prefix.replace("*", "")):
                # Use fnmatch for prefix with wildcards
                dir_parts = rel.split("/")
                if prefix:
                    if not fnmatch(dir_parts[0], prefix.rstrip("/")):
                        return False
            if suffix:
                return fnmatch(rel.split("/")[-1], suffix)
            return True
    return fnmatch(rel, pattern)


def find_images(dataset_path: Path, pattern: str) -> list[Path]:
    """Find all images matching pattern under dataset_path.

    Uses pathlib.Path.glob for reliable pattern matching including **.
    Falls back to rglob + fnmatch for character class patterns like [jJ].
    """
    image_exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

    # Character class patterns (e.g. [jJ][pP][gG]) aren't supported
    # by pathlib.glob on all Python versions, so handle specially
    if "[" in pattern:
        # Use rglob with fnmatch
        images = []
        for f in dataset_path.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in image_exts:
                continue
            if matches_pattern(f, dataset_path, pattern):
                images.append(f)
        return sorted(images)

    # Use pathlib.glob for standard patterns (handles ** correctly)
    images = []
    for f in dataset_path.glob(pattern):
        if f.is_file() and f.suffix.lower() in image_exts:
            images.append(f)
    return sorted(images)


# =============================================================================
# Metadata extraction
# =============================================================================


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_sample_metadata(
    dataset_name: str,
    dataset_path: Path,
    image_path: Path,
    parser_fn,
) -> dict:
    """Extract metadata for a single image file."""
    stat = image_path.stat()
    dims = get_image_dimensions(image_path)

    raw_labels = parser_fn(dataset_path, image_path) if parser_fn else {}

    # Determine split from labels or directory structure
    split = raw_labels.get("split", "unknown")

    sample = {
        "sample_id": str(uuid.uuid4()),
        "dataset_name": dataset_name,
        "file_path": str(image_path),
        "relative_path": str(image_path.relative_to(dataset_path)),
        "file_hash_sha256": compute_sha256(image_path),
        "split": split,
        "original_file_metadata": {
            "format": image_path.suffix.lstrip(".").lower(),
            "width_px": dims[0] if dims else None,
            "height_px": dims[1] if dims else None,
            "file_size_bytes": stat.st_size,
            "color_mode": None,  # Would need PIL
            "bit_depth": None,
        },
        "capture_method": raw_labels.get("capture_method", "camera_smartphone"),
        "domain_level1": "unknown",
        "enrichment_tier": "tier_3_heuristic",
        "original_labels": {
            "raw_labels": raw_labels,
        },
        "enrichment": {
            "has_text": None,
            "has_table": None,
            "has_formula": None,
            "has_figure": None,
            "has_handwriting": None,
            "text_scope": None,
            "layout_detections": None,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return sample


def process_dataset(
    dataset_name: str,
    base_dir: Path,
    output_dir: Path,
) -> None:
    """Process a single dataset and write metadata JSON."""
    config = CORRECTION_DATASETS[dataset_name]
    dataset_path = base_dir / config["path_suffix"]

    if not dataset_path.exists():
        print(f"  SKIP {dataset_name}: path {dataset_path} does not exist")
        return

    pattern = config["pattern"]
    parser_fn = LABEL_PARSERS.get(dataset_name)

    print(f"  Scanning {dataset_name}: {dataset_path}")
    images = find_images(dataset_path, pattern)
    print(f"  Found {len(images)} images matching '{pattern}'")

    if not images:
        print(f"  SKIP {dataset_name}: no images found")
        return

    samples = []
    for i, img_path in enumerate(images):
        if i % 500 == 0 and i > 0:
            print(f"    Progress: {i}/{len(images)}")
        try:
            sample = extract_sample_metadata(
                dataset_name, dataset_path, img_path, parser_fn
            )
            samples.append(sample)
        except Exception as e:
            print(f"    ERROR processing {img_path.name}: {e}")

    # Count images on disk (all images, not just pattern matches)
    all_images = sum(
        1
        for f in dataset_path.rglob("*")
        if f.is_file()
        and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff")
    )

    # Compute split counts
    split_counts: dict[str, int] = {}
    for s in samples:
        split_counts[s["split"]] = split_counts.get(s["split"], 0) + 1

    data = {
        "dataset_name": dataset_name,
        "sample_count": len(samples),
        "image_count_on_disk": all_images,
        "splits_included": list(split_counts.keys()),
        "split_counts": split_counts,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "2.1.0",
        "script_version": "lite-1.0.0",
        "git_sha": "lite-standalone",
        "samples": samples,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{dataset_name}_metadata.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"  Saved {len(samples)} samples to {output_file}")
    print(f"  (disk images: {all_images}, splits: {split_counts})")


# =============================================================================
# WSRD zip extraction (sequential, memory-safe)
# =============================================================================


def extract_wsrd_zips(base_dir: Path) -> None:
    """Extract WSRD zips into named subdirectories, one at a time."""
    import zipfile

    wsrd_dir = base_dir / "correction" / "wsrd"
    for challenge in ("ntire2023", "ntire2024"):
        challenge_dir = wsrd_dir / challenge
        if not challenge_dir.exists():
            print(f"  SKIP {challenge}: directory not found")
            continue

        zips = sorted(challenge_dir.glob("*.zip"))
        for zf_path in zips:
            target_dir = challenge_dir / zf_path.stem  # e.g. train_input/
            if target_dir.exists() and any(target_dir.iterdir()):
                print(
                    f"  SKIP {challenge}/{zf_path.name}: already extracted to {target_dir.name}/"
                )
                continue

            target_dir.mkdir(exist_ok=True)
            print(f"  Extracting {challenge}/{zf_path.name} -> {target_dir.name}/")
            try:
                with zipfile.ZipFile(zf_path, "r") as zf:
                    members = zf.namelist()
                    for j, member in enumerate(members):
                        if member.endswith("/"):
                            continue
                        # Extract file into target_dir (flatten if nested)
                        filename = os.path.basename(member)
                        if not filename:
                            continue
                        dest = target_dir / filename
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                dst.write(chunk)
                    print(
                        f"    Done: {len([m for m in members if not m.endswith('/')])} files"
                    )
            except Exception as e:
                print(f"    ERROR: {e}")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run lightweight metadata annotation."""
    parser = argparse.ArgumentParser(
        description="Lightweight base metadata annotation (stdlib-only)"
    )
    parser.add_argument("--dataset", help="Specific dataset to process")
    parser.add_argument(
        "--all-correction", action="store_true", help="Process all correction datasets"
    )
    parser.add_argument(
        "--extract-wsrd",
        action="store_true",
        help="Extract WSRD zips into named subdirectories",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        required=True,
        help="Base data directory (e.g. /mnt/e/image_detection/01_base_data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for metadata JSON files",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("LIGHTWEIGHT BASE METADATA ANNOTATION")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if args.extract_wsrd:
        print("\n--- Extracting WSRD zips ---")
        extract_wsrd_zips(args.base_dir)

    datasets_to_process = []
    if args.all_correction:
        datasets_to_process = list(CORRECTION_DATASETS.keys())
    elif args.dataset:
        if args.dataset not in CORRECTION_DATASETS:
            print(f"ERROR: Unknown dataset '{args.dataset}'")
            print(f"Available: {', '.join(CORRECTION_DATASETS.keys())}")
            sys.exit(1)
        datasets_to_process = [args.dataset]

    if datasets_to_process:
        print(f"\n--- Processing {len(datasets_to_process)} datasets ---")
        for name in datasets_to_process:
            print(f"\n[{name}]")
            process_dataset(name, args.base_dir, args.output_dir)

    print("\n--- Done ---")


if __name__ == "__main__":
    main()
