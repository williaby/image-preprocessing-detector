#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""
Create symlinks from local data/ directory to NFS storage.

This script creates symlinks from:
  data/benchmarks/* → /mnt/unraid/training_data/image_detection/benchmarks/*
  data/training/*   → /mnt/unraid/training_data/image_detection/training/*

Usage:
    python scripts/create_symlinks.py --all
    python scripts/create_symlinks.py --benchmarks-only
    python scripts/create_symlinks.py --verify
"""

import argparse
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
LOCAL_ROOT = PROJECT_ROOT / "data"
NFS_ROOT = Path("/mnt/unraid/training_data/image_detection")


# Symlink mappings
SYMLINK_MAPPINGS = [
    # Benchmarks
    ("data/benchmarks/tablebank", "benchmarks/tablebank"),
    ("data/benchmarks/pubtabnet", "benchmarks/pubtabnet"),
    ("data/benchmarks/diqa-5000", "benchmarks/diqa-5000"),
    ("data/benchmarks/funsd_plus", "benchmarks/funsd_plus"),
    ("data/benchmarks/doclaynet", "benchmarks/doclaynet"),
    ("data/benchmarks/fintabnet", "benchmarks/fintabnet"),
    ("data/benchmarks/omnidocbench", "benchmarks/omnidocbench"),
    ("data/benchmarks/ohr-bench", "benchmarks/ohr-bench"),
    ("data/benchmarks/external_iqa", "benchmarks/external_iqa"),
    ("data/benchmarks/signatr6k", "benchmarks/signatr6k"),
    ("data/benchmarks/wili_2018", "benchmarks/wili_2018"),
    ("data/benchmarks/cocotext", "benchmarks/cocotext"),
    # Training datasets (Phase 2 IQA)
    ("data/training/iqa_phase2", "training/iqa_phase2"),
    ("data/training/iqa_phase2_100k", "training/iqa_phase2_100k"),
    # Training datasets (Real-world receipts & invoices)
    ("data/training/receipts_hitl", "training/receipts_hitl"),
    ("data/training/mobile_receipts_voxel51", "training/mobile_receipts_voxel51"),
    ("data/training/invoices_kaggle", "training/invoices_kaggle"),
    # Training datasets (Phase 3 - handwriting & layout)
    ("data/training/iam_handwriting", "training/iam_handwriting"),
    ("data/training/docsynth300k", "training/docsynth300k"),
    ("data/training/nist_db2", "training/nist_db2"),
]


def create_symlink(local_rel_path: str, nfs_rel_path: str) -> tuple[bool, str]:
    """
    Create a symlink from local to NFS.

    Returns:
        (success, message) tuple
    """
    local_path = PROJECT_ROOT / local_rel_path
    nfs_path = NFS_ROOT / nfs_rel_path

    # Check if NFS target exists
    if not nfs_path.exists():
        return (False, f"NFS target does not exist: {nfs_path}")

    # Remove existing local path if it's a symlink
    if local_path.is_symlink():
        if local_path.readlink() == nfs_path:
            return (True, f"Symlink already correct: {local_path} → {nfs_path}")
        local_path.unlink()

    # Remove existing local path if it's a directory (and empty)
    elif local_path.is_dir():
        try:
            local_path.rmdir()  # Only works if empty
        except OSError:
            return (False, f"Local path exists and is not empty: {local_path}")

    # Create parent directory
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Create symlink
    try:
        local_path.symlink_to(nfs_path)
        return (True, f"✅ Created: {local_path} → {nfs_path}")
    except Exception as e:
        return (False, f"Failed to create symlink: {e}")


def verify_symlinks() -> list[tuple[str, str, bool, str]]:
    """
    Verify all symlinks are correctly configured.

    Returns:
        List of (local_path, nfs_path, is_valid, status) tuples
    """
    results = []

    for local_rel, nfs_rel in SYMLINK_MAPPINGS:
        local_path = PROJECT_ROOT / local_rel
        nfs_path = NFS_ROOT / nfs_rel

        if not nfs_path.exists():
            results.append((local_rel, nfs_rel, False, "NFS target missing"))
        elif not local_path.exists():
            results.append((local_rel, nfs_rel, False, "Local symlink missing"))
        elif not local_path.is_symlink():
            results.append((local_rel, nfs_rel, False, "Local path is not a symlink"))
        elif local_path.readlink() != nfs_path:
            results.append(
                (
                    local_rel,
                    nfs_rel,
                    False,
                    f"Symlink points to wrong target: {local_path.readlink()}",
                )
            )
        else:
            results.append((local_rel, nfs_rel, True, "✅ Valid"))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Create symlinks from local data/ to NFS storage"
    )
    parser.add_argument("--all", action="store_true", help="Create all symlinks")
    parser.add_argument(
        "--benchmarks-only", action="store_true", help="Create only benchmark symlinks"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify existing symlinks"
    )

    args = parser.parse_args()

    # Check NFS mount
    if not NFS_ROOT.exists():
        print(f"❌ NFS mount not found: {NFS_ROOT}")
        sys.exit(1)

    if args.verify:
        print(f"\n{'=' * 80}")
        print("Symlink Verification")
        print(f"{'=' * 80}\n")

        results = verify_symlinks()
        valid_count = sum(1 for _, _, is_valid, _ in results if is_valid)
        invalid_count = len(results) - valid_count

        for local_rel, nfs_rel, is_valid, status in results:
            symbol = "✅" if is_valid else "❌"
            print(f"{symbol} {local_rel}")
            print(f"   → {nfs_rel}")
            print(f"   {status}")
            print()

        print(f"\nSummary: {valid_count} valid, {invalid_count} invalid")
        return invalid_count == 0

    # Determine which symlinks to create
    if args.benchmarks_only:
        symlinks = [
            (link, nfs)
            for link, nfs in SYMLINK_MAPPINGS
            if link.startswith("data/benchmarks/")
        ]
    elif args.all:
        symlinks = SYMLINK_MAPPINGS
    else:
        parser.print_help()
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print("Creating Symlinks")
    print(f"{'=' * 80}\n")
    print(f"Symlinks to create: {len(symlinks)}\n")

    # Create symlinks
    success_count = 0
    fail_count = 0

    for local_rel, nfs_rel in symlinks:
        success, message = create_symlink(local_rel, nfs_rel)
        print(message)
        if success:
            success_count += 1
        else:
            fail_count += 1

    print(f"\n{'=' * 80}")
    print(f"Summary: {success_count} successful, {fail_count} failed")
    print(f"{'=' * 80}\n")

    return fail_count == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
