"""Synchronize TCC registry with disk state.

Fixes:
1. LOC WDL path prefix: registry has 'wdl/...' but disk has 'loc/wdl/...'
2. Removes ghost entries (registered but never downloaded): 352 NDL, 2 Met, 2 Wikimedia
3. Reports unregistered files on disk (LOC WDL images needing registration)

Usage:
    python scripts/sync_tcc_registry.py --dry-run   # Preview changes
    python scripts/sync_tcc_registry.py              # Execute sync
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, UTC
from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DATA = Path("/mnt/e/image_detection/01_base_data/calligraphy/thousand-character-classic")
REGISTRY_PATH = Path(
    "/mnt/e/image_detection/metadata_registry/thousand_character_classic_registry.jsonl"
)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_image_dimensions(file_path: Path) -> list[int]:
    """Get [width, height] of an image file."""
    with Image.open(file_path) as img:
        return list(img.size)


def sync_registry(dry_run: bool) -> dict[str, int]:
    """Fix registry paths and remove ghost entries."""
    stats = {
        "loc_paths_fixed": 0,
        "ghost_entries_removed": 0,
        "new_entries_added": 0,
        "errors": 0,
    }

    # Load registry
    entries: list[dict] = []
    with open(REGISTRY_PATH) as f:
        for line in f:
            entries.append(json.loads(line))

    original_count = len(entries)

    # --- Step 1: Fix LOC WDL paths ---
    print("\n=== Step 1: Fix LOC WDL path prefix (wdl/ → loc/wdl/) ===")
    for entry in entries:
        if entry.get("source_institution") == "loc_wdl":
            old_path = entry["source_path"]
            if old_path.startswith("wdl/") and not old_path.startswith("loc/wdl/"):
                new_path = f"loc/{old_path}"
                if (BASE_DATA / new_path).exists():
                    # Always update in-memory so downstream steps see correct paths
                    entry["source_path"] = new_path
                    prefix = "[DRY RUN] Would fix" if dry_run else "Fixed"
                    print(f"  {prefix}: {old_path} → {new_path}")
                    stats["loc_paths_fixed"] += 1
                else:
                    print(f"  WARNING: corrected path not on disk: {new_path}")

    # --- Step 2: Remove ghost entries ---
    print("\n=== Step 2: Remove ghost entries (registered but not on disk) ===")
    kept: list[dict] = []
    removed_by_inst: dict[str, int] = {}

    for entry in entries:
        source_path = entry.get("source_path", "")
        disk_path = BASE_DATA / source_path
        if disk_path.exists():
            kept.append(entry)
        else:
            inst = entry.get("source_institution", "unknown")
            removed_by_inst[inst] = removed_by_inst.get(inst, 0) + 1
            stats["ghost_entries_removed"] += 1

    for inst, count in sorted(removed_by_inst.items()):
        action = "[DRY RUN] Would remove" if dry_run else "Removed"
        print(f"  {action} {count} ghost entries from {inst}")

    if not dry_run:
        entries = kept

    # --- Step 3: Register unregistered LOC WDL files ---
    print("\n=== Step 3: Register unregistered LOC WDL files ===")
    registered_paths = {e["source_path"] for e in entries}
    loc_dir = BASE_DATA / "loc" / "wdl"

    if loc_dir.exists():
        unregistered: list[Path] = []
        for f in sorted(loc_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                rel = str(f.relative_to(BASE_DATA))
                if rel not in registered_paths:
                    unregistered.append(f)

        print(f"  Found {len(unregistered)} unregistered LOC WDL files")

        if unregistered:
            import uuid

            for f in unregistered:
                rel = str(f.relative_to(BASE_DATA))
                if dry_run:
                    stats["new_entries_added"] += 1
                    continue

                sha = compute_sha256(f)
                dims = get_image_dimensions(f)
                new_entry = {
                    "sample_id": str(uuid.uuid4()),
                    "sha256": sha,
                    "source_path": rel,
                    "source_url": "",
                    "source_institution": "loc_wdl",
                    "catalog_number": None,
                    "license": "Public Domain",
                    "registered_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                    "original_dimensions": dims,
                    "acquisition_method": "loc_wdl_iiif",
                }
                entries.append(new_entry)
                stats["new_entries_added"] += 1

            if dry_run:
                print(f"  [DRY RUN] Would register {stats['new_entries_added']} new files")
            else:
                print(f"  Registered {stats['new_entries_added']} new files")

    # --- Step 4: Write updated registry ---
    print("\n=== Step 4: Write updated registry ===")
    if not dry_run:
        backup = REGISTRY_PATH.with_suffix(".jsonl.pre-sync-bak")
        shutil.copyfile(REGISTRY_PATH, backup)
        print(f"  Backed up to: {backup.name}")

        with open(REGISTRY_PATH, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"  Wrote {len(entries)} entries (was {original_count})")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync TCC registry with disk state")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    args = parser.parse_args()

    print(f"TCC Registry Sync {'(DRY RUN)' if args.dry_run else '(LIVE)'}")

    stats = sync_registry(dry_run=args.dry_run)

    print("\n=== Summary ===")
    print(f"  LOC paths fixed:       {stats['loc_paths_fixed']}")
    print(f"  Ghost entries removed: {stats['ghost_entries_removed']}")
    print(f"  New entries added:     {stats['new_entries_added']}")
    print(f"  Errors:                {stats['errors']}")

    if args.dry_run:
        print("\n  ** DRY RUN — no changes made. **")


if __name__ == "__main__":
    main()
