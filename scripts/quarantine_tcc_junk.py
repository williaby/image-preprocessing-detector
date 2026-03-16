"""Quarantine unsuitable images from the TCC dataset.

Removes junk files (website UI scraping artifacts, exact cross-source duplicates,
ghost registry entries) from disk, registry, and L2 metadata.

Usage:
    python scripts/quarantine_tcc_junk.py --dry-run   # Preview changes
    python scripts/quarantine_tcc_junk.py              # Execute cleanup
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DATA = Path(
    "/mnt/e/image_detection/01_base_data/calligraphy/thousand-character-classic"
)
REGISTRY_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/thousand_character_classic_registry.jsonl"
)
L2_DIR = Path(
    "/mnt/e/image_detection/metadata_registry/json/thousand-character-classic"
)
QUARANTINE_DIR = BASE_DATA / "_quarantined"

# Files to remove from disk + registry + L2 metadata
JUNK_FILES: list[str] = [
    # Korean NMK website scraping artifacts (logos, license badges, icons)
    "korean/korean_7031_000.jpg",  # 200x200 museum logo
    "korean/korean_7031_001.jpg",  # 149x54 KOGL license badge
    "korean/korean_7031_003.jpg",  # 20x16 website icon
    "korean/korean_7031_004.jpg",  # 16x14 website icon
    "korean/korean_7031_005.jpg",  # 8x15 website icon
    "korean/korean_7031_006.jpg",  # 17x16 website icon
    "korean/korean_7031_007.jpg",  # 20x14 website icon
    "korean/korean_7031_008.jpg",  # 17x16 website icon
    "korean/korean_7031_009.jpg",  # 208x55 museum header text
    # Wikimedia exact duplicates of Met Museum images (same SHA256 on disk)
    "wikimedia/\u660e_\u8a79\u666f\u9cf3_\u8349\u66f8\u5343\u5b57\u6587_\u5377-Thousand_Character_Classic_MET_DP701610.jpg",
    "wikimedia/\u660e_\u8a79\u666f\u9cf3_\u8349\u66f8\u5343\u5b57\u6587_\u5377-Thousand_Character_Classic_MET_DP701609.jpg",
]

# Files to remove from registry only (not on disk — ghost entries)
GHOST_ENTRIES: list[str] = [
    "wikimedia/Hanzi_regular.png",  # 180x180 font sample, deleted from disk
]

ALL_QUARANTINE_PATHS = set(JUNK_FILES + GHOST_ENTRIES)


def quarantine_files(dry_run: bool) -> dict[str, int]:
    """Move junk files to quarantine directory and clean registry/L2."""
    stats = {
        "files_quarantined": 0,
        "registry_entries_removed": 0,
        "l2_files_removed": 0,
        "ghost_entries_removed": 0,
        "errors": 0,
    }

    # --- Step 1: Move junk files to quarantine (preserving directory structure) ---
    print("\n=== Step 1: Quarantine junk files from disk ===")
    for rel_path in JUNK_FILES:
        src = BASE_DATA / rel_path
        dst = QUARANTINE_DIR / rel_path
        if src.exists():
            if dry_run:
                print(f"  [DRY RUN] Would move: {rel_path}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"  Moved: {rel_path}")
            stats["files_quarantined"] += 1
        else:
            print(f"  SKIP (not on disk): {rel_path}")

    # --- Step 2: Clean registry ---
    print("\n=== Step 2: Remove entries from registry ===")
    if not REGISTRY_PATH.exists():
        print(f"  ERROR: Registry not found at {REGISTRY_PATH}")
        stats["errors"] += 1
        return stats

    kept_lines: list[str] = []
    removed_count = 0
    removed_sample_ids: set[str] = set()

    with open(REGISTRY_PATH) as f:
        for line in f:
            rec = json.loads(line)
            source_path = rec.get("source_path", "")
            if source_path in ALL_QUARANTINE_PATHS:
                removed_count += 1
                removed_sample_ids.add(rec.get("sample_id", ""))
                if dry_run:
                    print(f"  [DRY RUN] Would remove registry entry: {source_path}")
                else:
                    print(f"  Removed: {source_path}")
            else:
                kept_lines.append(line)

    if not dry_run and removed_count > 0:
        # Backup original registry (copyfile only — WSL NTFS lacks chmod/utime)
        backup = REGISTRY_PATH.with_suffix(".jsonl.bak")
        shutil.copyfile(REGISTRY_PATH, backup)
        print(f"  Backed up registry to: {backup.name}")

        with open(REGISTRY_PATH, "w") as f:
            f.writelines(kept_lines)

    stats["registry_entries_removed"] = removed_count

    # --- Step 3: Clean L2 metadata ---
    print("\n=== Step 3: Remove L2 metadata files ===")
    if not L2_DIR.exists():
        print(f"  WARNING: L2 directory not found at {L2_DIR}")
    else:
        for sample_id in removed_sample_ids:
            l2_file = L2_DIR / f"{sample_id}.json"
            if l2_file.exists():
                if dry_run:
                    print(f"  [DRY RUN] Would remove L2: {l2_file.name}")
                else:
                    l2_file.unlink()
                    print(f"  Removed L2: {l2_file.name}")
                stats["l2_files_removed"] += 1

    # Also check for L2 files by source path pattern
    for rel_path in ALL_QUARANTINE_PATHS:
        stem = Path(rel_path).stem
        for l2_file in L2_DIR.glob(f"*{stem}*"):
            if dry_run:
                print(f"  [DRY RUN] Would remove L2 (pattern match): {l2_file.name}")
            else:
                l2_file.unlink()
                print(f"  Removed L2 (pattern match): {l2_file.name}")
            stats["l2_files_removed"] += 1

    # --- Step 4: Handle ghost entries ---
    print("\n=== Step 4: Ghost entries (already handled in Step 2) ===")
    for path in GHOST_ENTRIES:
        if path in ALL_QUARANTINE_PATHS:
            stats["ghost_entries_removed"] += 1
            print(f"  Ghost entry cleaned: {path}")

    # --- Step 5: Write quarantine manifest ---
    print("\n=== Step 5: Write quarantine manifest ===")
    manifest = {
        "quarantine_date": datetime.now(timezone.utc).isoformat(),
        "reason": "TCC dataset cleanup — unsuitable images",
        "dry_run": dry_run,
        "junk_files": JUNK_FILES,
        "ghost_entries": GHOST_ENTRIES,
        "stats": stats,
        "categories": {
            "website_ui_artifacts": [p for p in JUNK_FILES if "7031" in p],
            "cross_source_duplicates": [p for p in JUNK_FILES if "MET_DP70161" in p],
            "ghost_registry_entries": GHOST_ENTRIES,
        },
    }

    manifest_path = QUARANTINE_DIR / "quarantine_manifest.json"
    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"  Written: {manifest_path}")
    else:
        print(f"  [DRY RUN] Would write manifest to: {manifest_path}")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quarantine unsuitable TCC dataset images"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    args = parser.parse_args()

    print(f"TCC Dataset Quarantine {'(DRY RUN)' if args.dry_run else '(LIVE)'}")
    print(f"Base data: {BASE_DATA}")
    print(f"Registry: {REGISTRY_PATH}")
    print(f"L2 metadata: {L2_DIR}")
    print(f"Quarantine dir: {QUARANTINE_DIR}")

    stats = quarantine_files(dry_run=args.dry_run)

    print("\n=== Summary ===")
    print(f"  Files quarantined:        {stats['files_quarantined']}")
    print(f"  Registry entries removed: {stats['registry_entries_removed']}")
    print(f"  L2 metadata removed:      {stats['l2_files_removed']}")
    print(f"  Ghost entries cleaned:     {stats['ghost_entries_removed']}")
    print(f"  Errors:                    {stats['errors']}")

    if args.dry_run:
        print("\n  ** DRY RUN — no changes made. Run without --dry-run to execute. **")

    sys.exit(1 if stats["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
