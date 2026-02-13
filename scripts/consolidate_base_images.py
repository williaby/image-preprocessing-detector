#!/usr/bin/env python3
"""
Consolidate selected base images into tracked staging area for Phase 7 MVP.

Creates:
- data/phase7_mvp/00_base_images/{source}/ - symlinks to source images
- data/phase7_mvp/00_base_images/manifest.json - tracking metadata

Updated 2025-12-16: E: drive reorganized to category-based structure.
- 01_base_data/{category}/{dataset}/ - Training data by category
- 02_benchmark_only/{dataset}/ - Evaluation-only datasets (human MOS)
"""

import hashlib
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent

# E: drive base paths (reorganized 2025-12-16)
E_DRIVE_ROOT = Path("/mnt/e/image_detection")
BASE_DATA = E_DRIVE_ROOT / "01_base_data"  # Training data by category
BENCHMARK_ONLY = E_DRIVE_ROOT / "02_benchmark_only"  # Evaluation-only datasets

OUTPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/00_base_images"

# Target composition - 25,000 samples total for MVP
# All 16 sources available on E: drive!
COMPOSITION = {
    # Real degradation anchors (22.5%)
    "diqa_5000": 3_500,  # Real degradation with human MOS (5,500 available)
    "tobacco_800": 1_285,  # Historical scans (1,290 available)
    "dibco": 128,  # Document binarization (128 available)
    "historical_degraded": 700,  # Additional degraded docs (1,356 available)
    # Multi-category diversity (14%)
    "rvl_cdip": 3_500,  # 16 document categories (16,000 available)
    # Structured forms (14.6%)
    "nist-sd2": 1_200,  # Check images (5,590 available)
    "nist_sd6": 1_200,  # Tax forms (5,595 available)
    "funsd_plus": 1_139,  # Form understanding (1,139 available)
    # Mobile capture proxy (6%)
    "sroie": 973,  # Receipts (973 available - full ICDAR 2019 set)
    # Born-digital tables (18%)
    "tablebank": 2_500,  # LaTeX/Word tables (260,025 available)
    "pubtabnet": 2_000,  # Scientific tables (519,030 available)
    # Mixed layouts (10%)
    "doclaynet": 2_500,  # Document layouts (81,471 available)
    # Handwriting (6%)
    "nist_sd19": 1_500,  # Handwriting pages (3,669 available)
    # Math/formulas (6.8%)
    "mathverse": 500,  # Math diagrams (3,940 available)
    "maths_handwriting": 1_200,  # Math + handwriting (15,000 available)
    # Educational content (2.9%)
    "multimodal_textbook": 648,  # Educational (1,113 available)
}

# Source paths (E: drive reorganized 2025-12-16)
# Structure: 01_base_data/{category}/{dataset}/ and 02_benchmark_only/{dataset}/
# File extensions verified 2025-12-16
SOURCE_PATHS: dict[str, tuple[Path, str]] = {
    # === 02_benchmark_only (evaluation-only, human MOS) ===
    "diqa_5000": (BENCHMARK_ONLY / "diqa-5000", "**/*.jpg"),
    "dibco": (BENCHMARK_ONLY / "dibco", "**/*.*"),
    # === 01_base_data/degraded (real degradation) ===
    "tobacco_800": (BASE_DATA / "degraded/tobacco800/images", "*.png"),
    "historical_degraded": (BASE_DATA / "degraded/historical_degraded", "**/*.png"),
    # === 01_base_data/documents (multi-category) ===
    "rvl_cdip": (BASE_DATA / "documents/rvl_cdip/images", "*.jpg"),
    "doclaynet": (BASE_DATA / "documents/doclaynet", "**/*.png"),
    # === 01_base_data/forms (structured forms) ===
    "nist-sd2": (BASE_DATA / "forms/nist-sd2", "**/*.png"),
    "nist_sd6": (BASE_DATA / "forms/nist_sd6", "**/*.png"),
    "funsd_plus": (BASE_DATA / "forms/funsd_plus/images", "*.jpg"),
    "sroie": (BASE_DATA / "forms/sroie_icdar2019", "**/*.jpg"),
    # === 01_base_data/tables (tabular data) ===
    "tablebank": (BASE_DATA / "tables/tablebank/TableBank/Detection/images", "*.jpg"),
    "pubtabnet": (BASE_DATA / "tables/pubtabnet", "**/*.png"),
    # === 01_base_data/handwriting ===
    "nist_sd19": (BASE_DATA / "handwriting/nist-sd19", "**/*.png"),
    "maths_handwriting": (BASE_DATA / "handwriting/maths_handwriting", "**/*.png"),
    # === 01_base_data/formulas (math content) ===
    "mathverse": (BASE_DATA / "formulas/mathverse/images", "*.jpg"),
    # === 01_base_data/educational ===
    "multimodal_textbook": (BASE_DATA / "educational/sample_100_images", "*.jpg"),
}


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file (first 64KB for speed)."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read first 64KB for speed (sufficient for uniqueness)
        chunk = f.read(65536)
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def get_source_files(source_name: str) -> list[Path]:
    """Get list of source files for a dataset."""
    if source_name not in SOURCE_PATHS:
        print(f"  WARNING: {source_name} not in SOURCE_PATHS")
        return []

    source_path, pattern = SOURCE_PATHS[source_name]

    if not source_path.exists():
        print(f"  WARNING: {source_name}: Path not found: {source_path}")
        return []

    files = sorted(source_path.glob(pattern))
    return files


def consolidate_source(
    source_name: str,
    target_count: int,
    manifest: dict[str, Any],
    use_symlinks: bool = True,
) -> int:
    """Consolidate images from one source."""
    dest_dir = OUTPUT_DIR / source_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    source_files = get_source_files(source_name)

    if not source_files:
        print(f"  {source_name}: No files found")
        return 0

    # Sample if we have more than needed
    actual_count = min(len(source_files), target_count)
    if len(source_files) > target_count:
        random.seed(42)  # Reproducibility
        source_files = random.sample(source_files, target_count)
    else:
        source_files = source_files[:actual_count]

    # Create symlinks and track in manifest
    for i, src_path in enumerate(
        tqdm(source_files, desc=f"  {source_name}", leave=False)
    ):
        dest_path = dest_dir / f"{source_name}_{i:05d}{src_path.suffix}"

        if use_symlinks:
            # Create symlink
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()
            dest_path.symlink_to(src_path.resolve())
        else:
            # Copy file
            import shutil

            shutil.copy2(src_path, dest_path)

        manifest["sources"].append(
            {
                "source": source_name,
                "original_path": str(src_path),
                "consolidated_path": str(dest_path.relative_to(OUTPUT_DIR.parent)),
                "sha256": compute_sha256(src_path),
            }
        )

    return actual_count


def main():
    """Run consolidation."""
    print("=" * 70)
    print("PHASE 7 MVP - BASE IMAGE CONSOLIDATION")
    print("=" * 70)
    print(f"Output: {OUTPUT_DIR}")
    print(
        f"Target: {sum(COMPOSITION.values()):,} images from {len(COMPOSITION)} sources"
    )
    print()

    # Initialize manifest
    manifest: dict[str, Any] = {
        "created": datetime.now().isoformat(),
        "target_total": sum(COMPOSITION.values()),
        "composition": COMPOSITION,
        "sources": [],
    }

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Consolidate each source
    total_consolidated = 0
    results = {}

    for source_name, target_count in COMPOSITION.items():
        print(f"\n{source_name} (target: {target_count:,})")
        count = consolidate_source(source_name, target_count, manifest)
        results[source_name] = count
        total_consolidated += count
        print(f"  Consolidated: {count:,}")

    # Save manifest
    manifest["total_images"] = len(manifest["sources"])
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Summary report
    print("\n" + "=" * 70)
    print("CONSOLIDATION COMPLETE")
    print("=" * 70)
    print(f"Total images: {total_consolidated:,} / {sum(COMPOSITION.values()):,}")
    print(f"Manifest: {manifest_path}")

    print("\nCoverage by source:")
    for source, target in COMPOSITION.items():
        actual = results.get(source, 0)
        pct = actual / target * 100 if target > 0 else 0
        status = "OK" if pct >= 90 else "LOW"
        print(f"  [{status}] {source}: {actual:,} / {target:,} ({pct:.0f}%)")

    # Domain distribution summary
    print("\nDomain Distribution:")
    domains = {
        "Real Degradation": [
            "diqa_5000",
            "tobacco_800",
            "dibco",
            "historical_degraded",
        ],
        "Multi-Category": ["rvl_cdip"],
        "Forms": ["nist-sd2", "nist_sd6", "funsd_plus"],
        "Mobile/Receipts": ["sroie"],
        "Tables": ["tablebank", "pubtabnet"],
        "Layouts": ["doclaynet"],
        "Handwriting": ["nist_sd19"],
        "Math": ["mathverse", "maths_handwriting"],
        "Educational": ["multimodal_textbook"],
    }

    for domain, sources in domains.items():
        count = sum(results.get(s, 0) for s in sources)
        pct = count / total_consolidated * 100 if total_consolidated > 0 else 0
        print(f"  {domain}: {count:,} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
