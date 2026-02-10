#!/usr/bin/env python3
"""Reconcile dataset images on disk against metadata registry.

Walks DATASET_CONFIGS from annotate_base_metadata.py, resolves paths,
counts images, and compares against Layer 2 metadata JSON files.

Usage:
    python scripts/disk_manifest.py                 # Full reconciliation report
    python scripts/disk_manifest.py --json          # Machine-readable JSON output
    python scripts/disk_manifest.py --missing-only  # Only show datasets needing metadata
    python scripts/disk_manifest.py --dataset sroie # Single dataset check
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotate_base_metadata import DATASET_CONFIGS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

E_DRIVE_ROOT = Path("/mnt/e/image_detection")
METADATA_JSON_DIR = E_DRIVE_ROOT / "metadata_registry" / "json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def count_images(dataset_path: Path, pattern: str) -> int:
    """Count image files matching a glob pattern under a dataset path."""
    if not dataset_path.exists():
        return 0
    return sum(
        1 for f in dataset_path.glob(pattern) if f.suffix.lower() in IMAGE_EXTENSIONS
    )


def get_metadata_sample_count(dataset_name: str) -> int | None:
    """Read sample_count from existing metadata JSON, if present.

    Tries canonical name, then hyphen-to-underscore and underscore-to-hyphen
    variants to handle naming mismatches.
    """
    variants = [
        dataset_name,
        dataset_name.replace("-", "_"),
        dataset_name.replace("_", "-"),
    ]
    for name in variants:
        metadata_file = METADATA_JSON_DIR / f"{name}_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                return data.get("sample_count", 0)
            except (json.JSONDecodeError, OSError):
                return None
    return None


def reconcile_all(
    dataset_filter: str | None = None,
) -> list[dict]:
    """Reconcile all datasets, returning per-dataset status dicts."""
    results = []

    configs = DATASET_CONFIGS
    if dataset_filter:
        configs = {k: v for k, v in configs.items() if k == dataset_filter}
        if not configs:
            logger.error(f"Dataset '{dataset_filter}' not found in DATASET_CONFIGS")
            return results

    for name, config in sorted(configs.items()):
        dataset_path: Path = config["path"]
        pattern: str = config["pattern"]

        path_exists = dataset_path.exists()
        image_count = count_images(dataset_path, pattern) if path_exists else 0
        metadata_count = get_metadata_sample_count(name)

        # Determine status
        if not path_exists:
            status = "NO_PATH"
        elif image_count == 0:
            status = "NO_IMAGES"
        elif metadata_count is None:
            status = "NO_METADATA"
        elif metadata_count == 0:
            status = "EMPTY_METADATA"
        elif abs(metadata_count - image_count) / max(image_count, 1) > 0.05:
            status = "COUNT_MISMATCH"
        else:
            status = "OK"

        # Infer canonical name from path
        path_suffix = str(dataset_path.relative_to(dataset_path.parents[1]))
        leaf_folder = dataset_path.name
        name_matches_path = name == leaf_folder or name.replace(
            "-", "_"
        ) == leaf_folder.replace("-", "_")

        results.append(
            {
                "dataset": name,
                "path": str(dataset_path),
                "path_suffix": path_suffix,
                "path_exists": path_exists,
                "image_count": image_count,
                "metadata_count": metadata_count,
                "status": status,
                "name_matches_path": name_matches_path,
            }
        )

    return results


def print_table(results: list[dict], missing_only: bool = False) -> None:
    """Print a formatted reconciliation table."""
    if missing_only:
        results = [r for r in results if r["status"] != "OK"]

    # Status icons
    status_icons = {
        "OK": "  OK ",
        "NO_PATH": " MISS",
        "NO_IMAGES": " EMPT",
        "NO_METADATA": " META",
        "EMPTY_METADATA": " STUB",
        "COUNT_MISMATCH": " DIFF",
    }

    print()
    print("=" * 100)
    print("DATASET DISK MANIFEST — Reconciliation Report")
    print("=" * 100)
    print(
        f"{'Dataset':<28} {'Status':<6} {'On Disk':>10} "
        f"{'Metadata':>10} {'Gap':>8} {'Name=Path'}"
    )
    print("-" * 100)

    totals = {"disk": 0, "metadata": 0, "ok": 0, "issues": 0}
    for r in results:
        status = status_icons.get(r["status"], r["status"])
        disk = f"{r['image_count']:,}" if r["image_count"] else "-"
        meta = f"{r['metadata_count']:,}" if r["metadata_count"] is not None else "-"

        gap = ""
        if r["metadata_count"] is not None and r["image_count"] > 0:
            diff = r["image_count"] - r["metadata_count"]
            if diff != 0:
                gap = f"{diff:+,}"

        name_ok = "yes" if r["name_matches_path"] else "NO"

        print(
            f"{r['dataset']:<28} {status:<6} {disk:>10} {meta:>10} {gap:>8} {name_ok}"
        )

        totals["disk"] += r["image_count"]
        totals["metadata"] += r["metadata_count"] or 0
        if r["status"] == "OK":
            totals["ok"] += 1
        else:
            totals["issues"] += 1

    print("-" * 100)
    print(
        f"{'TOTAL':<28} {'':6} {totals['disk']:>10,} "
        f"{totals['metadata']:>10,} "
        f"{totals['disk'] - totals['metadata']:>+8,}"
    )
    print()

    # Summary
    total = len(results)
    print(
        f"Datasets: {total} total, {totals['ok']} OK, {totals['issues']} need attention"
    )

    # Breakdown of issues
    by_status: dict[str, list[str]] = {}
    for r in results:
        if r["status"] != "OK":
            by_status.setdefault(r["status"], []).append(r["dataset"])

    if by_status:
        print()
        for status, names in sorted(by_status.items()):
            print(f"  {status} ({len(names)}): {', '.join(names)}")

    # Name mismatches
    mismatches = [r for r in results if not r["name_matches_path"]]
    if mismatches:
        print(f"\nName-path mismatches ({len(mismatches)}):")
        for r in mismatches:
            print(f"  {r['dataset']:<28} -> {r['path_suffix']}")

    print()


def main() -> None:
    """Entry point for disk manifest reconciliation."""
    parser = argparse.ArgumentParser(
        description="Reconcile dataset images on disk against metadata registry.",
    )
    parser.add_argument("--dataset", type=str, help="Check single dataset")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only show datasets with issues",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    args = parser.parse_args()

    results = reconcile_all(dataset_filter=args.dataset)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_table(results, missing_only=args.missing_only)


if __name__ == "__main__":
    main()
