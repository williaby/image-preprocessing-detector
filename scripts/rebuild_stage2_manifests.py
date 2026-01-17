#!/usr/bin/env python3
"""Rebuild Stage 2 manifests with new 3-dimension specialist_true labels.

This script:
1. Loads existing Stage 2 manifests
2. Replaces single-dimension labels with 3-dimension labels from specialist_true
3. Converts soft_label_10bin to per-dimension format
4. Validates label consistency
5. Outputs new manifests ready for training

Usage:
    python scripts/rebuild_stage2_manifests.py
    python scripts/rebuild_stage2_manifests.py --dry-run  # Preview only
    python scripts/rebuild_stage2_manifests.py --validate  # Validate only

Environment Variables:
    STAGE2_DIR: Path to Stage 2 dataset directory
    LABELS_DIR: Path to DeQA labels directory
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


def _get_default_paths() -> tuple[Path, Path, Path]:
    """Get default paths from environment or relative to repository root.

    Returns:
        Tuple of (stage2_dir, labels_dir, output_dir).

    Environment Variables:
        STAGE2_DIR: Path to Stage 2 dataset directory
        LABELS_DIR: Path to DeQA labels directory (defaults to repo/results/deqa_labels)
    """
    # Default labels directory relative to repository root (scripts/ is one level down)
    repo_root = Path(__file__).resolve().parent.parent
    default_labels_dir = repo_root / "results" / "deqa_labels"

    stage2_dir = Path(
        os.environ.get(
            "STAGE2_DIR",
            "/mnt/e/image_detection/03_training_datasets/stage2_diqa_ensemble",
        )
    )
    labels_dir = Path(os.environ.get("LABELS_DIR", str(default_labels_dir)))
    output_dir = stage2_dir / "splits_v2"
    return stage2_dir, labels_dir, output_dir


# Paths - configurable via environment variables
STAGE2_DIR, LABELS_DIR, OUTPUT_DIR = _get_default_paths()


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file."""
    entries = []
    with open(path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def save_jsonl(path: Path, entries: list[dict]) -> None:
    """Save JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(entry) + "\n" for entry in entries)


def probs_to_soft_label_10bin(probs: dict[str, float]) -> list[float]:
    """Convert 5-level probs to 10-bin soft labels.

    Maps each of 5 levels to 2 adjacent bins:
    - excellent (5.0) -> bins 8, 9
    - good (4.0) -> bins 6, 7
    - fair (3.0) -> bins 4, 5
    - poor (2.0) -> bins 2, 3
    - bad (1.0) -> bins 0, 1
    """
    # Initialize 10-bin distribution
    soft_label = [0.0] * 10

    # Map 5 levels to 10 bins (each level spans 2 bins)
    level_to_bins = {
        "bad": (0, 1),
        "poor": (2, 3),
        "fair": (4, 5),
        "good": (6, 7),
        "excellent": (8, 9),
    }

    for level, (bin1, bin2) in level_to_bins.items():
        prob = probs.get(level, 0.0)
        # Split probability evenly across both bins
        soft_label[bin1] = prob / 2
        soft_label[bin2] = prob / 2

    return soft_label


def _load_available_labels() -> tuple[dict[str, list[dict]], list[str]]:
    """Load all available specialist_true labels.

    Returns:
        Tuple of (available_labels dict, missing_labels list).
    """
    label_files = {
        "diqa-5000": LABELS_DIR / "diqa-5000_specialist_true_labels.jsonl",
        "smartdoc-qa": LABELS_DIR / "smartdoc-qa_specialist_true_labels.jsonl",
        "sroie": LABELS_DIR / "sroie_specialist_true_labels.jsonl",
        "tobacco-800": LABELS_DIR / "tobacco-800_specialist_true_labels.jsonl",
        "funsd": LABELS_DIR / "funsd_specialist_true_labels.jsonl",
    }

    available_labels: dict[str, list[dict]] = {}
    missing_labels: list[str] = []

    for dataset, path in label_files.items():
        if path.exists():
            print(f"✓ Found labels for {dataset}: {path}")
            available_labels[dataset] = load_jsonl(path)
            print(f"  → {len(available_labels[dataset])} entries")
        else:
            print(f"✗ Missing labels for {dataset}")
            missing_labels.append(dataset)

    return available_labels, missing_labels


def _build_label_index(available_labels: dict[str, list[dict]]) -> dict[str, dict]:
    """Build lookup index from available labels.

    Args:
        available_labels: Dictionary of dataset -> label entries.

    Returns:
        Dictionary mapping image path keys to label entries.
    """
    labels_by_image: dict[str, dict] = {}
    for dataset, entries in available_labels.items():
        for entry in entries:
            image_path = entry["image"]
            key = f"{dataset}/{image_path}"
            labels_by_image[key] = entry
    return labels_by_image


def _find_label_for_entry(
    entry: dict, labels_by_image: dict[str, dict]
) -> dict | None:
    """Find matching label for a manifest entry.

    Args:
        entry: Manifest entry with source_dataset and image_id.
        labels_by_image: Label index to search.

    Returns:
        Matching label dict or None if not found.
    """
    dataset = entry["source_dataset"]
    image_id = entry["image_id"]

    # Try primary key format
    key = image_id
    if "/" in image_id:
        parts = image_id.split("/", 1)
        if len(parts) == 2:
            rel_path = parts[1]
            key = f"{dataset}/{rel_path}"

    label = labels_by_image.get(key)
    if label is not None:
        return label

    # Try alternate key formats
    for alt_key in [image_id, f"{dataset}/{image_id}"]:
        label = labels_by_image.get(alt_key)
        if label is not None:
            return label

    return None


def _update_entry_with_label(entry: dict, label: dict) -> dict:
    """Update manifest entry with 3-dimension label data.

    Args:
        entry: Original manifest entry.
        label: Label data with scores and probs.

    Returns:
        Updated entry with 3-dimension labels.
    """
    new_entry = entry.copy()

    # Replace deqa_predicted_score with per-dimension scores
    new_entry["deqa_scores"] = label["scores"]

    # Replace single soft_label_10bin with per-dimension soft labels
    new_entry["soft_labels_10bin"] = {
        dim: probs_to_soft_label_10bin(label["probs"][dim])
        for dim in ["overall", "sharpness", "color"]
    }

    # Keep original deqa_predicted_score for backward compatibility
    new_entry["deqa_predicted_score"] = label["scores"]["overall"]

    # Replace single soft_label_10bin with overall dimension
    new_entry["soft_label_10bin"] = probs_to_soft_label_10bin(
        label["probs"]["overall"]
    )

    # Store raw probs for reference
    new_entry["deqa_probs_3dim"] = label["probs"]

    # Mark as updated
    new_entry["label_source"] = "specialist_true"
    new_entry["label_timestamp"] = label.get(
        "timestamp", datetime.now().isoformat()
    )

    return new_entry


def _process_split(
    split: str, labels_by_image: dict[str, dict], dry_run: bool
) -> None:
    """Process a single data split.

    Args:
        split: Split name (train, val, test).
        labels_by_image: Label index for lookups.
        dry_run: If True, don't write files.
    """
    input_path = STAGE2_DIR / "splits" / f"{split}.jsonl"
    output_path = OUTPUT_DIR / f"{split}.jsonl"

    if not input_path.exists():
        print(f"⚠ Missing split: {input_path}")
        return

    print(f"\nProcessing {split}...")
    entries = load_jsonl(input_path)
    updated_entries = []
    missing = 0
    updated = 0

    for entry in entries:
        label = _find_label_for_entry(entry, labels_by_image)

        if label is None:
            missing += 1
            updated_entries.append(entry)
            continue

        new_entry = _update_entry_with_label(entry, label)
        updated_entries.append(new_entry)
        updated += 1

    print(f"  Updated: {updated}")
    print(f"  Missing: {missing}")
    print(f"  Total: {len(entries)}")

    if not dry_run:
        save_jsonl(output_path, updated_entries)
        print(f"  Saved: {output_path}")
    else:
        print(f"  [DRY RUN] Would save: {output_path}")


def _save_manifest_metadata(dry_run: bool) -> None:
    """Save manifest metadata file.

    Args:
        dry_run: If True, skip writing.
    """
    if dry_run:
        return

    manifest = {
        "version": "2.0.0",
        "created": datetime.now().isoformat(),
        "description": "Stage 2 DIQA Ensemble Training Dataset - 3-Dimension Labels",
        "label_source": "DeQA-Doc specialist_true (3 dimension-specific models)",
        "dimensions": ["overall", "sharpness", "color"],
        "splits_dir": str(OUTPUT_DIR),
        "original_splits_dir": str(STAGE2_DIR / "splits"),
        "note": "Updated with true 3-dimension labels from DeQA-Doc specialists",
    }

    manifest_path = OUTPUT_DIR / "MANIFEST.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSaved manifest: {manifest_path}")


def rebuild_manifests(dry_run: bool = False, validate_only: bool = False) -> None:
    """Rebuild Stage 2 manifests with 3-dimension labels.

    Args:
        dry_run: If True, preview changes without writing.
        validate_only: If True, only validate labels exist.
    """
    print("=" * 60)
    print("Stage 2 Manifest Rebuild")
    print("=" * 60)

    available_labels, missing_labels = _load_available_labels()

    if missing_labels:
        print(f"\n⚠ Missing labels for: {', '.join(missing_labels)}")
        print("Run: ./scripts/stage2_label_regeneration.sh to generate them")
        if not validate_only:
            return

    if validate_only:
        print("\n[Validation only mode - no changes made]")
        return

    labels_by_image = _build_label_index(available_labels)
    print(f"\nTotal label entries: {len(labels_by_image)}")

    for split in ["train", "val", "test"]:
        _process_split(split, labels_by_image, dry_run)

    _save_manifest_metadata(dry_run)

    print("\n" + "=" * 60)
    print("Rebuild complete!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild Stage 2 manifests with 3-dim labels"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing"
    )
    parser.add_argument("--validate", action="store_true", help="Validate labels only")
    args = parser.parse_args()

    rebuild_manifests(dry_run=args.dry_run, validate_only=args.validate)


if __name__ == "__main__":
    main()
