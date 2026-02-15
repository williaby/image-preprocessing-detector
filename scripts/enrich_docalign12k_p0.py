#!/usr/bin/env python3
"""P0 enrichment for docalign12k: fix split labels from file lists.

Reads train_docalign12k.txt and test.txt split file lists, maps entries
to metadata samples via original_path, and updates the split field in
both source.split and the latest enrichment version data.split.

Usage:
    PYTHONPATH=. uv run python3 scripts/enrich_docalign12k_p0.py --dry-run
    PYTHONPATH=. uv run python3 scripts/enrich_docalign12k_p0.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Paths
DATASET_DIR = Path("/mnt/e/image_detection/01_base_data/correction/docalign12k")
METADATA_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/json/docalign12k_metadata.json"
)
TRAIN_LIST = DATASET_DIR / "train_docalign12k.txt"
TEST_LIST = DATASET_DIR / "test.txt"


def load_file_list(path: Path) -> set[str]:
    """Load a split file list and return set of entries (group/stem)."""
    if not path.exists():
        log.error("File list not found: %s", path)
        sys.exit(1)
    with open(path) as f:
        entries = {line.strip() for line in f if line.strip()}
    log.info("Loaded %d entries from %s", len(entries), path.name)
    return entries


def original_path_to_entry(original_path: str) -> str | None:
    """Convert original_path like 'distorted_hard/1/000101_00028.jpg' to '1/000101_00028'."""
    # Expected: distorted_hard/{group}/{stem}.jpg
    parts = original_path.split("/")
    if len(parts) < 3 or parts[0] != "distorted_hard":
        return None
    group = parts[1]
    stem = Path(parts[-1]).stem
    return f"{group}/{stem}"


def main() -> None:
    """Fix split labels from file lists."""
    parser = argparse.ArgumentParser(description="P0: Fix docalign12k split labels")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing",
    )
    args = parser.parse_args()

    # Load file lists
    train_entries = load_file_list(TRAIN_LIST)
    test_entries = load_file_list(TEST_LIST)
    log.info(
        "Split assignment: %d train-only, %d test (subset of train)",
        len(train_entries - test_entries),
        len(test_entries),
    )

    # Load metadata
    log.info("Loading metadata from %s", METADATA_PATH)
    t0 = time.monotonic()
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    samples = metadata.get("samples", [])
    log.info("Loaded %d samples in %.1fs", len(samples), time.monotonic() - t0)

    # Process samples
    stats: Counter[str] = Counter()
    unmatched: list[str] = []

    for sample in samples:
        original_path = sample.get("source", {}).get("original_path", "")
        entry = original_path_to_entry(original_path)

        if entry is None:
            stats["skip_no_entry"] += 1
            unmatched.append(original_path)
            continue

        # Determine split: test entries take priority over train
        if entry in test_entries:
            new_split = "test"
        elif entry in train_entries:
            new_split = "train"
        else:
            new_split = "unknown"
            stats["no_match"] += 1
            unmatched.append(original_path)
            continue

        old_split = sample.get("source", {}).get("split", "unknown")
        if old_split != new_split:
            stats[f"changed_{old_split}_to_{new_split}"] += 1
        else:
            stats["already_correct"] += 1

        # Update source.split
        sample["source"]["split"] = new_split

        # Update latest enrichment version data.split
        versions = sample.get("enrichments", {}).get("versions", [])
        if versions:
            latest = versions[-1]
            if "data" in latest:
                latest["data"]["split"] = new_split

        stats[f"split_{new_split}"] += 1

    # Report
    log.info("--- Results ---")
    for key, count in sorted(stats.items()):
        log.info("  %s: %d", key, count)

    if unmatched:
        log.warning("Unmatched samples: %d", len(unmatched))
        for path in unmatched[:5]:
            log.warning("  %s", path)

    # Update top-level split info
    split_counts = {
        "train": stats.get("split_train", 0),
        "test": stats.get("split_test", 0),
    }
    if stats.get("no_match", 0) > 0 or stats.get("skip_no_entry", 0) > 0:
        split_counts["unknown"] = stats.get("no_match", 0) + stats.get(
            "skip_no_entry", 0
        )

    metadata["splits_included"] = [s for s, c in split_counts.items() if c > 0]
    metadata["split_counts"] = {s: c for s, c in split_counts.items() if c > 0}

    if args.dry_run:
        log.info("DRY RUN - no changes written")
        return

    # Write
    log.info("Writing updated metadata to %s", METADATA_PATH)
    t0 = time.monotonic()
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    log.info("Written in %.1fs", time.monotonic() - t0)
    log.info("Done.")


if __name__ == "__main__":
    main()
