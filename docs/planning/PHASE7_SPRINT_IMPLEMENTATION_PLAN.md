---
schema_type: planning
title: "Phase 7 IQA Training - Sprint Implementation Plan"
description: "Detailed technical implementation plan with actionable sprints for MVP v2.1"
tags:
  - planning
  - phase7
  - iqa
  - sprints
  - implementation
status: draft
owner: core-maintainer
authors:
  - name: "Claude Code"
  - name: "Byron Williams"
purpose: Break down Phase 7 MVP into executable sprint tasks.
component: Strategy
source: Manual creation
---

> **Created**: 2025-12-15
> **Based On**: [PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md](PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md)
> **Target**: 6-week MVP with 14-source dataset (25K samples)
> **Primary Success Metric**: ECE < 0.08

---

# Phase 7 IQA Training - Sprint Implementation Plan

## Executive Summary

This document breaks down the Phase 7 MVP into **6 actionable sprints** with specific tasks, commands, acceptance criteria, and estimated durations. Each sprint builds on the previous and includes explicit go/no-go checkpoints.

**Timeline**: 6 weeks (can parallelize Sprint 0 with other work)

| Sprint | Focus | Duration | Key Deliverable |
|--------|-------|----------|-----------------|
| **Sprint 0** | Dataset Acquisition | 3-5 days | All 14 source datasets downloaded |
| **Sprint 1** | Base Image Consolidation | 2-3 days | `00_base_images/` with manifest |
| **Sprint 2** | Dataset Generation & Upload | 3-4 days | 25K augmented dataset on GCS |
| **Sprint 3** | Baseline Training | 4-5 days | ResNet-50 MSE baseline (ECE < 0.10) |
| **Sprint 4** | Production Model | 4-5 days | ResNet-50 Gaussian NLL (ECE < 0.08) |
| **Sprint 5** | Distillation & Validation | 5-7 days | ResNet-18 + triangulation validation |
| **Sprint 6** | Deployment | 3-4 days | ONNX export + integration |

---

## Sprint 0: Dataset Acquisition

**Duration**: ~1 day (mostly extraction)
**Objective**: Verify and extract all 14 source datasets
**Status**: 🟢 **MOSTLY COMPLETE** - datasets available at `E:\image_detection\benchmarks`

> **Note**: All datasets are pre-downloaded on the E: drive (Windows). Access via WSL at `/mnt/e/image_detection/benchmarks/`.

### 0.1 Current Status Assessment (Updated 2025-12-15)

**Two dataset locations on E: drive:**

- `E:\image_detection\benchmarks\` - Large benchmark datasets
- `E:\image_detection\v4_datasets\` - Additional curated datasets for MVP v2.1

| Dataset | Status | Location | Count | Action Required |
|---------|--------|----------|-------|-----------------|
| DIQA-5000 | ✅ Ready | `benchmarks/diqa-5000/` | 5,500 images | None |
| Tobacco-800 | ✅ Ready | `v4_datasets/tobacco800/images/` | 1,290 images | None |
| DIBCO | ✅ Ready | `v4_datasets/dibco/` | 128 images | None |
| RVL-CDIP | ✅ Ready | `v4_datasets/rvl_cdip/` | 16,000 images | None |
| NIST DB2 | ✅ Ready | `benchmarks/nist_db2/` | 5,590 images | None |
| NIST SD6 | ✅ Ready | `benchmarks/nist_sd6/` | 5,595 images | None |
| FUNSD+ | ✅ Ready | `v4_datasets/funsd_plus/` | 1,139 images | None |
| SROIE | ✅ Ready | `v4_datasets/sroie/` | 2,043 images | None |
| TableBank | ✅ Ready | `benchmarks/tablebank/` | 260,025 images | None |
| PubTabNet | ✅ Ready | `benchmarks/pubtabnet/` | 519,030 images | None |
| DocLayNet | ✅ Ready | `benchmarks/doclaynet/` | 81,471 PNG | **Already converted!** |
| NIST SD19 | ✅ Ready | `v4_datasets/nist_sd19_pages/` | 3,669 images | None |
| Maths/Handwriting | ✅ Ready | `v4_datasets/maths_handwriting/` | 15,000 images | Bonus dataset! |
| MathVerse | ✅ Ready | `v4_datasets/mathverse/` | 3,940 images | None |
| Historical Degraded | ✅ Ready | `v4_datasets/historical_degraded/` | 1,356 images | Bonus dataset! |
| Multimodal Textbook | ✅ Ready | `benchmarks/sample_100_images/` | 1,113 images | None |

### 0.1.1 Dataset Source Paths (E: Drive / WSL)

```bash
# E: drive paths (Windows)
E:\image_detection\benchmarks\     # Large benchmark datasets
E:\image_detection\v4_datasets\    # Curated MVP v2.1 datasets

# WSL paths
BENCHMARKS=/mnt/e/image_detection/benchmarks
V4_DATASETS=/mnt/e/image_detection/v4_datasets

# === BENCHMARKS FOLDER (large datasets) ===
# $BENCHMARKS/diqa-5000/           → 5,500 images (real degradation anchor)
# $BENCHMARKS/nist_db2/            → 5,590 images (check forms)
# $BENCHMARKS/nist_sd6/            → 5,595 images (tax forms)
# $BENCHMARKS/tablebank/           → 260,025 images (born-digital tables)
# $BENCHMARKS/pubtabnet/           → 519,030 images (scientific tables)
# $BENCHMARKS/doclaynet/           → 81,471 PNG images (mixed layouts)
# $BENCHMARKS/sample_100_images/   → 1,113 images (Multimodal Textbook)

# === V4_DATASETS FOLDER (curated for MVP v2.1) ===
# $V4_DATASETS/tobacco800/images/  → 1,290 images (historical scans)
# $V4_DATASETS/dibco/              → 128 images (document binarization)
# $V4_DATASETS/rvl_cdip/           → 16,000 images (16 document categories)
# $V4_DATASETS/funsd_plus/         → 1,139 images (form understanding)
# $V4_DATASETS/sroie/              → 2,043 images (receipts/mobile proxy)
# $V4_DATASETS/nist_sd19_pages/    → 3,669 images (handwriting)
# $V4_DATASETS/maths_handwriting/  → 15,000 images (math + handwriting)
# $V4_DATASETS/mathverse/          → 3,940 images (math diagrams)
# $V4_DATASETS/historical_degraded/→ 1,356 images (real degradation)
```

### 0.2 Task Breakdown

#### Task 0.2.1: Create Symlink to E: Drive (5 min)

```bash
# Create symlink from project data directory to E: drive benchmarks
cd /home/byron/dev/image_detection
ln -sfn /mnt/e/image_detection/benchmarks data/benchmarks_e_drive

# Verify symlink
ls -la data/benchmarks_e_drive/
```

#### Task 0.2.2: Verify Existing Datasets (15 min)

```bash
# Run verification against E: drive
cd /home/byron/dev/image_detection

# DIQA-5000 (5,500 total confirmed)
find /mnt/e/image_detection/benchmarks/diqa-5000 -name "*.jpg" -o -name "*.png" | wc -l

# DIBCO (131 confirmed, more in zip)
find /mnt/e/image_detection/benchmarks/dibco -name "*.png" -o -name "*.bmp" | wc -l

# NIST DB2 (5,590 confirmed)
find /mnt/e/image_detection/benchmarks/nist_db2 -name "*.png" | wc -l

# NIST SD6 (5,595 confirmed)
find /mnt/e/image_detection/benchmarks/nist_sd6 -name "*.png" | wc -l

# TableBank (260,025 confirmed)
find /mnt/e/image_detection/benchmarks/tablebank -name "*.png" -o -name "*.jpg" | wc -l

# PubTabNet (519,030 confirmed)
find /mnt/e/image_detection/benchmarks/pubtabnet -name "*.png" | wc -l

# DocLayNet (81,471 PNG confirmed - already converted!)
find /mnt/e/image_detection/benchmarks/doclaynet -name "*.png" | wc -l

# FUNSD+ (Arrow format)
python -c "from datasets import load_from_disk; ds = load_from_disk('/mnt/e/image_detection/benchmarks/funsd_plus'); print(f'FUNSD+ train: {len(ds[\"train\"])} samples')"

# Multimodal Textbook sample (1,113 confirmed)
ls /mnt/e/image_detection/benchmarks/sample_100_images/*.jpg | wc -l
```

**Acceptance Criteria** (all confirmed ✅):

- [x] DIQA-5000: 5,500 images ✅
- [x] DIBCO: 131+ images ✅ (extract DIBCO.zip for more)
- [x] NIST DB2: 5,590 images ✅
- [x] NIST SD6: 5,595 images ✅
- [x] TableBank: 260,025 images ✅
- [x] PubTabNet: 519,030 images ✅
- [x] DocLayNet: 81,471 PNG images ✅
- [x] FUNSD+: Arrow format ✅
- [x] Multimodal Textbook: 1,113 images ✅

#### Task 0.2.3: Extract Additional DIBCO Images (15 min)

```bash
# Extract DIBCO.zip for additional degraded document images
cd /mnt/e/image_detection/benchmarks

# Extract DIBCO archive
unzip -o DIBCO.zip -d dibco_full/

# Count total DIBCO images
find dibco_full -name "*.png" -o -name "*.bmp" -o -name "*.tif" | wc -l
# Expected: ~600+ images
```

**Acceptance Criteria**:

- [ ] DIBCO.zip extracted
- [ ] At least 500 document images available
- [ ] Mixed degradation types (stains, fading, bleed-through)

#### Task 0.2.4: Extract NIST SD19 (Handwriting) (15 min)

```bash
# Extract NIST SD19 handwriting samples from hsf_page.zip
cd /mnt/e/image_detection/benchmarks

# Extract hsf_page archive (NIST SD19 full page images)
unzip -o hsf_page.zip -d nist_sd19/

# Count page images
find nist_sd19 -name "*.png" -o -name "*.ppm" | wc -l
# Expected: 1,500+ full page handwriting images
```

**Acceptance Criteria**:

- [ ] hsf_page.zip extracted
- [ ] At least 1,500 full-page handwriting images
- [ ] Various handwriting styles

#### Task 0.2.5: Extract im2latex (Math Formulas) (15 min)

```bash
# Extract im2latex formula images from archive.zip
cd /mnt/e/image_detection/benchmarks

# Extract archive.zip (likely im2latex)
unzip -o archive.zip -d im2latex/

# Count formula images
find im2latex -name "*.png" | wc -l
# Expected: 10,000+ formula images
```

**Acceptance Criteria**:

- [ ] archive.zip extracted
- [ ] At least 5,000 formula images
- [ ] Various complexity levels

#### Task 0.2.6: Optional Downloads (Only if needed)

The following datasets are **optional** and can be skipped since we have >880K images available:

```bash
# OPTIONAL: Download Tobacco-800 from HuggingFace (if needed)
# poetry run python -c "
# from datasets import load_dataset
# from pathlib import Path
# ds = load_dataset('rvl_cdip', 'tobacco_800')
# output = Path('/mnt/e/image_detection/benchmarks/tobacco-800')
# output.mkdir(exist_ok=True)
# for i, sample in enumerate(ds['test']):
#     sample['image'].save(output / f'tobacco_{i:04d}.tif')
# "

# OPTIONAL: Download MathVerse from HuggingFace (if more math content needed)
# poetry run python -c "
# from datasets import load_dataset
# from pathlib import Path
# ds = load_dataset('AI4Math/MathVerse', split='test')
# output = Path('/mnt/e/image_detection/benchmarks/mathverse')
# output.mkdir(exist_ok=True)
# for i, sample in enumerate(ds[:500]):
#     if sample.get('image'):
#         sample['image'].save(output / f'mathverse_{i:04d}.png')
# "
```

**Note**: DocLayNet is **already converted to PNG** at `/mnt/e/image_detection/benchmarks/doclaynet/` (81,471 images). No conversion needed!

### 0.3 Sprint 0 Completion Checklist

```bash
# Final verification script (updated for E: drive)
cat > scripts/verify_all_datasets.py << 'EOF'
"""Verify all source datasets are available on E: drive."""
from pathlib import Path

# E: drive via WSL
BENCHMARKS_ROOT = Path("/mnt/e/image_detection/benchmarks")

# Updated dataset paths for E: drive (confirmed counts)
EXPECTED = {
    "diqa_5000": (BENCHMARKS_ROOT / "diqa-5000", "**/*.jpg", 5500),
    "dibco": (BENCHMARKS_ROOT / "dibco", "**/*.png", 131),  # Extract DIBCO.zip for more
    "nist_db2": (BENCHMARKS_ROOT / "nist_db2", "**/*.png", 5590),
    "nist_sd6": (BENCHMARKS_ROOT / "nist_sd6", "**/*.png", 5595),
    "funsd_plus": (BENCHMARKS_ROOT / "funsd_plus", None, 1000),  # Arrow format
    "tablebank": (BENCHMARKS_ROOT / "tablebank", "**/*.png", 260025),
    "pubtabnet": (BENCHMARKS_ROOT / "pubtabnet", "**/*.png", 519030),
    "doclaynet": (BENCHMARKS_ROOT / "doclaynet", "**/*.png", 81471),
    "multimodal_textbook": (BENCHMARKS_ROOT / "sample_100_images", "*.jpg", 1113),
    # These need extraction from zip files:
    # "nist_sd19": (BENCHMARKS_ROOT / "nist_sd19", "**/*.png", 1500),  # hsf_page.zip
    # "im2latex": (BENCHMARKS_ROOT / "im2latex", "**/*.png", 5000),    # archive.zip
}

print("=" * 60)
print("DATASET VERIFICATION REPORT")
print("=" * 60)

total_available = 0
total_needed = 0

for name, (full_path, pattern, target) in EXPECTED.items():
    if pattern is None:
        # HuggingFace format
        try:
            from datasets import load_from_disk
            ds = load_from_disk(str(full_path))
            count = len(ds)
        except:
            count = 0
    else:
        if full_path.exists():
            count = len(list(full_path.glob(pattern)))
        else:
            count = 0

    status = "✅" if count >= target * 0.9 else "❌"
    print(f"{status} {name}: {count:,} / {target:,} ({count/target*100:.0f}%)")

    total_available += min(count, target)
    total_needed += target

print("=" * 60)
print(f"TOTAL: {total_available:,} / {total_needed:,} ({total_available/total_needed*100:.1f}%)")

if total_available < total_needed * 0.8:
    print("\n⚠️  WARNING: Less than 80% of target samples available!")
    print("   Complete missing downloads before proceeding to Sprint 1.")
else:
    print("\n✅ Ready for Sprint 1: Base Image Consolidation")
EOF

poetry run python scripts/verify_all_datasets.py
```

**Sprint 0 Go/No-Go** (Status: 🟢 **COMPLETE**):

- [x] ≥80% of target samples available → **>920K images across 16 sources** ✅
- [x] Real degradation sources available (DIQA, Tobacco-800, DIBCO, Historical) ✅
- [x] **ALL 14+ sources ready** - no downloads needed! ✅
- [x] RVL-CDIP: 16,000 images (16 document categories) ✅
- [x] SROIE: 2,043 receipt images (mobile capture proxy) ✅
- [x] MathVerse: 3,940 math diagrams ✅
- [x] NIST SD19: 3,669 handwriting pages ✅
- [x] **BONUS**: maths_handwriting (15K), historical_degraded (1.3K) ✅

---

## Sprint 1: Base Image Consolidation

**Duration**: 2-3 days
**Objective**: Create tracked staging area of clean source images
**Prerequisites**: Sprint 0 complete (≥80% datasets available)

### 1.1 Implementation Tasks

#### Task 1.1.1: Create Consolidation Script (2-3 hours)

```bash
# Create the base image consolidation script
cat > scripts/consolidate_base_images.py << 'EOF'
#!/usr/bin/env python3
"""
Consolidate selected base images into tracked staging area.

Creates:
- data/phase7_mvp/00_base_images/{source}/ - symlinks to source images
- data/phase7_mvp/00_base_images/manifest.json - tracking metadata
"""
import hashlib
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
BENCHMARKS = Path("/mnt/e/image_detection/benchmarks")
V4_DATASETS = Path("/mnt/e/image_detection/v4_datasets")
OUTPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/00_base_images"

# Target composition (updated for available datasets on E: drive)
# Total: 25,000 samples for MVP - ALL 14 SOURCES NOW AVAILABLE!
COMPOSITION = {
    # Real degradation anchors (21.5%)
    "diqa_5000": 3_500,           # Real degradation (5,500 available)
    "tobacco_800": 1_285,         # Historical scans (1,290 available)
    "dibco": 128,                 # Document binarization (128 available)
    "historical_degraded": 500,   # BONUS: Additional degraded docs (1,356 available)
    # Multi-category diversity (14%)
    "rvl_cdip": 3_500,            # 16 document categories (16,000 available)
    # Structured forms (15.2%)
    "nist_db2": 1_250,            # Check images (5,590 available)
    "nist_sd6": 1_250,            # Tax forms (5,595 available)
    "funsd_plus": 1_139,          # Form understanding (1,139 available)
    # Mobile capture proxy (6%)
    "sroie": 1_500,               # Receipts (2,043 available)
    # Born-digital tables (18%)
    "tablebank": 2_500,           # LaTeX/Word tables (260,025 available)
    "pubtabnet": 2_000,           # Scientific tables (519,030 available)
    # Mixed layouts (10%)
    "doclaynet": 2_500,           # Document layouts (81,471 available)
    # Handwriting (6%)
    "nist_sd19": 1_500,           # Handwriting pages (3,669 available)
    # Math/formulas (6.8%)
    "mathverse": 500,             # Math diagrams (3,940 available)
    "maths_handwriting": 1_200,   # Math + handwriting (15,000 available)
    # Educational content (4.5%)
    "multimodal_textbook": 747,   # Educational (1,113 available)
}

# Source paths (E: drive via WSL - two locations)
SOURCE_PATHS = {
    # From BENCHMARKS folder
    "diqa_5000": (BENCHMARKS / "diqa-5000", "**/*.jpg"),
    "nist_db2": (BENCHMARKS / "nist_db2", "**/*.png"),
    "nist_sd6": (BENCHMARKS / "nist_sd6", "**/*.png"),
    "tablebank": (BENCHMARKS / "tablebank", "**/*.png"),
    "pubtabnet": (BENCHMARKS / "pubtabnet", "**/*.png"),
    "doclaynet": (BENCHMARKS / "doclaynet", "**/*.png"),
    "multimodal_textbook": (BENCHMARKS / "sample_100_images", "*.jpg"),
    # From V4_DATASETS folder
    "tobacco_800": (V4_DATASETS / "tobacco800/images", "**/*.jpg"),
    "dibco": (V4_DATASETS / "dibco", "**/*.png"),
    "historical_degraded": (V4_DATASETS / "historical_degraded", "**/*.png"),
    "rvl_cdip": (V4_DATASETS / "rvl_cdip", "**/*.tif"),
    "funsd_plus": (V4_DATASETS / "funsd_plus", "**/*.png"),
    "sroie": (V4_DATASETS / "sroie", "**/*.jpg"),
    "nist_sd19": (V4_DATASETS / "nist_sd19_pages", "**/*.png"),
    "mathverse": (V4_DATASETS / "mathverse", "**/*.png"),
    "maths_handwriting": (V4_DATASETS / "maths_handwriting", "**/*.png"),
}


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_source_files(source_name: str) -> list[Path]:
    """Get list of source files for a dataset."""
    source_path, pattern = SOURCE_PATHS[source_name]

    if not source_path.exists():
        print(f"  ⚠️ {source_name}: Path not found: {source_path}")
        return []

    if pattern is None:
        # HuggingFace format - return indices
        return list(range(COMPOSITION[source_name]))

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
        return 0

    # Sample if we have more than needed
    if len(source_files) > target_count:
        random.seed(42)  # Reproducibility
        source_files = random.sample(source_files, target_count)

    actual_count = min(len(source_files), target_count)

    # Handle HuggingFace datasets specially
    if SOURCE_PATHS[source_name][1] is None:
        from datasets import load_from_disk
        from PIL import Image

        ds_path = PROJECT_ROOT / SOURCE_PATHS[source_name][0]
        dataset = load_from_disk(str(ds_path))

        for i in tqdm(range(min(len(dataset), target_count)), desc=f"  {source_name}"):
            img = dataset[i]["image"]
            dest_path = dest_dir / f"{source_name}_{i:05d}.png"
            img.save(dest_path)

            manifest["sources"].append({
                "source": source_name,
                "original_path": f"hf://{ds_path}[{i}]",
                "consolidated_path": str(dest_path.relative_to(OUTPUT_DIR.parent)),
                "sha256": compute_sha256(dest_path),
            })

        return min(len(dataset), target_count)

    # Regular file-based datasets
    for i, src_path in enumerate(tqdm(source_files[:actual_count], desc=f"  {source_name}")):
        dest_path = dest_dir / f"{source_name}_{i:05d}{src_path.suffix}"

        if use_symlinks:
            # Create relative symlink
            if dest_path.exists():
                dest_path.unlink()
            dest_path.symlink_to(src_path.resolve())
        else:
            # Copy file
            import shutil
            shutil.copy2(src_path, dest_path)

        manifest["sources"].append({
            "source": source_name,
            "original_path": str(src_path),
            "consolidated_path": str(dest_path.relative_to(OUTPUT_DIR.parent)),
            "sha256": compute_sha256(src_path),
        })

    return actual_count


def main():
    print("=" * 60)
    print("BASE IMAGE CONSOLIDATION")
    print("=" * 60)
    print(f"Output: {OUTPUT_DIR}")
    print(f"Target: {sum(COMPOSITION.values()):,} images from {len(COMPOSITION)} sources")
    print()

    # Initialize manifest
    manifest = {
        "created": datetime.now().isoformat(),
        "target_total": sum(COMPOSITION.values()),
        "composition": COMPOSITION,
        "sources": [],
    }

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Consolidate each source
    total_consolidated = 0
    for source_name, target_count in COMPOSITION.items():
        print(f"\n{source_name} (target: {target_count:,})")
        count = consolidate_source(source_name, target_count, manifest)
        total_consolidated += count
        print(f"  → Consolidated: {count:,}")

    # Save manifest
    manifest["total_images"] = len(manifest["sources"])
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 60)
    print("CONSOLIDATION COMPLETE")
    print("=" * 60)
    print(f"Total images: {total_consolidated:,} / {sum(COMPOSITION.values()):,}")
    print(f"Manifest: {manifest_path}")

    # Coverage report
    print("\nCoverage by source:")
    for source in COMPOSITION:
        source_count = sum(1 for s in manifest["sources"] if s["source"] == source)
        target = COMPOSITION[source]
        pct = source_count / target * 100 if target > 0 else 0
        status = "✅" if pct >= 90 else "⚠️"
        print(f"  {status} {source}: {source_count:,} / {target:,} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
EOF

chmod +x scripts/consolidate_base_images.py
```

#### Task 1.1.2: Run Consolidation (1-2 hours)

```bash
# Execute consolidation
poetry run python scripts/consolidate_base_images.py

# Verify output
ls -la data/phase7_mvp/00_base_images/
cat data/phase7_mvp/00_base_images/manifest.json | python -m json.tool | head -50

# Check total count
find data/phase7_mvp/00_base_images -type l -o -type f -name "*.png" -o -name "*.jpg" -o -name "*.tif" | wc -l
```

**Acceptance Criteria**:

- [ ] `00_base_images/` directory created with 9 subdirectories (available sources)
- [ ] `manifest.json` contains SHA256 hashes for all images
- [ ] Total image count ≥ 20,000 (80% of 25K target)
- [ ] All real degradation sources (DIQA, Tobacco, DIBCO) fully populated

#### Task 1.1.3: Create Manifest Verification Script (30 min)

```bash
cat > scripts/verify_manifest.py << 'EOF'
"""Verify manifest integrity and image accessibility."""
import json
import hashlib
from pathlib import Path
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data/phase7_mvp/00_base_images/manifest.json"

with open(MANIFEST_PATH) as f:
    manifest = json.load(f)

print(f"Verifying {len(manifest['sources'])} images...")

errors = []
for entry in tqdm(manifest["sources"]):
    path = PROJECT_ROOT / "data/phase7_mvp" / entry["consolidated_path"]

    # Check existence
    if not path.exists():
        errors.append(f"Missing: {path}")
        continue

    # Verify hash (sample 10%)
    if hash(entry["consolidated_path"]) % 10 == 0:
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != entry["sha256"]:
            errors.append(f"Hash mismatch: {path}")

if errors:
    print(f"\n❌ {len(errors)} errors found:")
    for e in errors[:10]:
        print(f"  {e}")
else:
    print("\n✅ All images verified successfully")
EOF

poetry run python scripts/verify_manifest.py
```

### 1.2 Sprint 1 Completion Checklist

- [ ] `data/phase7_mvp/00_base_images/` populated
- [ ] `manifest.json` created with SHA256 hashes
- [ ] ≥20,000 images consolidated
- [ ] Manifest verification passes
- [ ] Git: `git add -A && git commit -m "feat(phase7): consolidate base images for MVP v2.1"`

---

## Sprint 2: Dataset Generation & Upload

**Duration**: 3-4 days
**Objective**: Generate augmented 25K dataset and upload to GCS
**Prerequisites**: Sprint 1 complete

### 2.1 Implementation Tasks

#### Task 2.1.1: Update Dataset Generator (2-3 hours)

The `scripts/generate_iqa_dataset.py` has been updated with 14 sources. Now add the consolidation workflow:

```bash
# Add consolidation step to generator
# See generate_iqa_dataset.py for full implementation

# Key addition: Use 00_base_images/ as source instead of raw benchmark dirs
```

#### Task 2.1.2: Generate Augmented Dataset (4-8 hours)

```bash
# Generate dataset from consolidated base images
poetry run python scripts/generate_iqa_dataset.py \
    --output-dir data/phase7_mvp/01_augmented \
    --seed 42

# Expected output structure:
# data/phase7_mvp/01_augmented/
# ├── images/
# │   └── sample_XXXXXX.jpg (25,000 images)
# └── metadata.json
```

#### Task 2.1.3: Create Train/Val/Test Splits (1 hour)

```bash
cat > scripts/create_splits.py << 'EOF'
"""Create stratified train/val/test splits."""
import json
import random
import shutil
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/01_augmented"
OUTPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/splits"

# Load metadata
with open(INPUT_DIR / "metadata.json") as f:
    metadata = json.load(f)

samples = metadata["samples"]
print(f"Total samples: {len(samples)}")

# Stratify by source dataset and defect level
strata = defaultdict(list)
for sample in samples:
    key = (sample["source_dataset"], sample.get("defect_level", "unknown"))
    strata[key].append(sample)

# Split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

train_samples = []
val_samples = []
test_samples = []

random.seed(42)
for key, group in strata.items():
    random.shuffle(group)
    n = len(group)
    n_train = int(n * TRAIN_RATIO)
    n_val = int(n * VAL_RATIO)

    train_samples.extend(group[:n_train])
    val_samples.extend(group[n_train:n_train + n_val])
    test_samples.extend(group[n_train + n_val:])

print(f"Train: {len(train_samples)}, Val: {len(val_samples)}, Test: {len(test_samples)}")

# Create split directories and copy/link images
for split_name, split_samples in [("train", train_samples), ("val", val_samples), ("test", test_samples)]:
    split_dir = OUTPUT_DIR / split_name / "images"
    split_dir.mkdir(parents=True, exist_ok=True)

    split_metadata = []
    for sample in tqdm(split_samples, desc=f"Creating {split_name}"):
        src = INPUT_DIR / "images" / sample["filename"]
        dst = split_dir / sample["filename"]

        if src.exists():
            dst.symlink_to(src.resolve())
            split_metadata.append(sample)

    # Save split metadata
    with open(OUTPUT_DIR / split_name / "metadata.json", "w") as f:
        json.dump({"samples": split_metadata, "count": len(split_metadata)}, f, indent=2)

print(f"\nSplits created at {OUTPUT_DIR}")
EOF

poetry run python scripts/create_splits.py
```

#### Task 2.1.4: Create TAR Archives for Modal (1-2 hours)

```bash
cat > scripts/create_tar_archives.py << 'EOF'
"""Create TAR archives for Modal training."""
import tarfile
from pathlib import Path
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
SPLITS_DIR = PROJECT_ROOT / "data/phase7_mvp/splits"
OUTPUT_DIR = PROJECT_ROOT / "data/phase7_mvp/archives"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for split in ["train", "val", "test"]:
    split_dir = SPLITS_DIR / split
    tar_path = OUTPUT_DIR / f"phase7_mvp_{split}.tar"

    print(f"Creating {tar_path}...")

    with tarfile.open(tar_path, "w") as tar:
        # Add images
        images_dir = split_dir / "images"
        for img_path in tqdm(list(images_dir.glob("*")), desc=f"  {split} images"):
            # Resolve symlinks
            real_path = img_path.resolve()
            tar.add(real_path, arcname=f"images/{img_path.name}")

        # Add metadata
        metadata_path = split_dir / "metadata.json"
        tar.add(metadata_path, arcname="metadata.json")

    # Report size
    size_mb = tar_path.stat().st_size / (1024 * 1024)
    print(f"  → {tar_path.name}: {size_mb:.1f} MB")

print("\nArchives ready for upload to GCS")
EOF

poetry run python scripts/create_tar_archives.py
```

#### Task 2.1.5: Upload to GCS (30 min - 1 hour)

```bash
# Upload to GCS for Modal training
gsutil -m cp data/phase7_mvp/archives/*.tar gs://your-bucket/phase7_mvp/

# Verify upload
gsutil ls -l gs://your-bucket/phase7_mvp/
```

### 2.2 Sprint 2 Completion Checklist

- [ ] 25K augmented images generated
- [ ] Stratified train/val/test splits created (70/15/15)
- [ ] TAR archives created (~10-15 GB total)
- [ ] Archives uploaded to GCS
- [ ] Git: `git commit -m "feat(phase7): generate 25K dataset with 14-source distribution"`

---

## Sprint 3: Baseline Training

**Duration**: 4-5 days
**Objective**: Train ResNet-50 with Pure MSE loss, establish baseline
**Prerequisites**: Sprint 2 complete

### 3.1 Implementation Tasks

#### Task 3.1.1: Create Modal Training Script (3-4 hours)

```python
# modal/train_phase7_baseline.py
# See existing modal/train_phase2_iqa.py for template
# Key changes:
# - Input resolution: 384x384
# - Loss: Pure MSE
# - 5 severity heads (blur, noise, skew, contrast, compression)
# - Batch size: 64 (for 384x384)
```

#### Task 3.1.2: Run Baseline Training (8-12 hours GPU time)

```bash
# Launch Modal training
poetry run modal run modal/train_phase7_baseline.py \
    --dataset gs://your-bucket/phase7_mvp/ \
    --epochs 50 \
    --batch-size 64 \
    --lr 1e-4

# Monitor training
# - Check TensorBoard logs
# - Watch for val loss convergence
# - Monitor per-head ECE
```

#### Task 3.1.3: Evaluate Baseline (2-3 hours)

```bash
# Download checkpoint
gsutil cp gs://your-bucket/checkpoints/resnet50_mse_baseline.pth models/

# Run evaluation
poetry run python scripts/evaluate_checkpoint.py \
    --checkpoint models/resnet50_mse_baseline.pth \
    --test-data data/phase7_mvp/splits/test

# Expected metrics:
# - Overall ECE < 0.10
# - Per-head ECE within targets
# - No severe overfitting
```

### 3.2 Sprint 3 Completion Checklist

- [ ] Modal training script created
- [ ] Baseline training completed (~50 epochs)
- [ ] Checkpoint saved: `resnet50_mse_baseline.pth`
- [ ] Overall ECE < 0.10 achieved
- [ ] Training curves show convergence (no overfitting)
- [ ] Git: `git commit -m "feat(phase7): baseline ResNet-50 MSE training (ECE < 0.10)"`

---

## Sprint 4: Production Model

**Duration**: 4-5 days
**Objective**: Train ResNet-50 with Gaussian NLL loss, achieve ECE < 0.08
**Prerequisites**: Sprint 3 complete, baseline ECE < 0.10

### 4.1 Implementation Tasks

#### Task 4.1.1: Implement Gaussian NLL Loss (2-3 hours)

```python
# src/image_preprocessing_detector/models/loss_functions.py

class GaussianNLLLoss(nn.Module):
    """Uncertainty-aware regression loss."""

    def __init__(self, eps=1e-6):
        super().__init__()
        self.eps = eps

    def forward(self, mu, log_var, target):
        var = torch.exp(log_var) + self.eps
        nll = 0.5 * log_var + 0.5 * ((target - mu) ** 2) / var
        return nll.mean()
```

#### Task 4.1.2: Add Uncertainty Heads to Model (1-2 hours)

```python
# Update SeverityHead to output both mu and log_var
# See PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md Section 2.2
```

#### Task 4.1.3: Run Production Training (8-12 hours GPU time)

```bash
poetry run modal run modal/train_phase7_production.py \
    --dataset gs://your-bucket/phase7_mvp/ \
    --loss gaussian_nll \
    --epochs 100 \
    --batch-size 64 \
    --lr 1e-4 \
    --early-stop-metric val_ece \
    --early-stop-target 0.08
```

#### Task 4.1.4: Generate Calibration Report (2-3 hours)

```bash
# Generate reliability diagrams
poetry run python scripts/generate_calibration_report.py \
    --checkpoint models/resnet50_gaussian_nll_prod.pth \
    --output reports/calibration_report.pdf
```

### 4.2 Sprint 4 Completion Checklist

- [ ] Gaussian NLL loss implemented
- [ ] Uncertainty heads added to model
- [ ] Production training completed
- [ ] **ECE < 0.08** achieved (PRIMARY TARGET)
- [ ] Per-head ECE meets targets
- [ ] Calibration report generated
- [ ] Git: `git commit -m "feat(phase7): production ResNet-50 Gaussian NLL (ECE < 0.08)"`

---

## Sprint 5: Student Distillation & Validation

**Duration**: 5-7 days
**Objective**: Train ResNet-18 student, validate with triangulation
**Prerequisites**: Sprint 4 complete, production model ECE < 0.08

### 5.1 Student Distillation Tasks

#### Task 5.1.1: Implement Distillation Trainer (2-3 hours)

```python
# Knowledge distillation: soft targets from teacher + hard targets from ground truth
distillation_loss = (
    0.7 * kl_divergence(student_logits / T, teacher_logits / T) +
    0.3 * mse_loss(student_severity, ground_truth)
)
```

#### Task 5.1.2: Train ResNet-18 Student (6-8 hours GPU time)

```bash
poetry run modal run modal/train_phase7_distillation.py \
    --teacher models/resnet50_gaussian_nll_prod.pth \
    --student resnet18 \
    --temperature 2.0 \
    --alpha 0.7
```

#### Task 5.1.3: Export to ONNX (1-2 hours)

```bash
poetry run python scripts/export_onnx.py \
    --checkpoint models/resnet18_distilled.pth \
    --output models/resnet18_distilled.onnx \
    --quantize int8
```

### 5.2 Validation Triangulation Tasks

#### Task 5.2.1: Implement Triangulation Validation (3-4 hours)

```python
# Validate on DIQA-5000 val/test (held out from training)
# Three signals:
# 1. SSIM correlation
# 2. OCR WER correlation
# 3. Human MOS correlation
```

#### Task 5.2.2: Run External Baseline Comparison (2-3 hours)

```bash
# Compare against BRISQUE
poetry run python scripts/run_baselines.py \
    --methods brisque \
    --test-data data/phase7_mvp/splits/test
```

### 5.3 Sprint 5 Completion Checklist

- [ ] ResNet-18 distillation completed
- [ ] Student ECE within +0.03 of teacher
- [ ] ONNX export successful (INT8 quantized)
- [ ] CPU latency < 60ms verified
- [ ] DIQA val/test evaluation: ECE < 0.10
- [ ] Triangulation shows agreement (std < 0.15)
- [ ] Outperforms BRISQUE baseline
- [ ] Git: `git commit -m "feat(phase7): ResNet-18 distillation + validation triangulation"`

---

## Sprint 6: Deployment

**Duration**: 3-4 days
**Objective**: Integration, deployment, documentation
**Prerequisites**: Sprint 5 complete

### 6.1 Integration Tasks

#### Task 6.1.1: Integration with DQS Pipeline (2-3 hours)

```python
# Update src/image_preprocessing_detector/metrics/dqs_calculator.py
# to use new ML IQA model instead of classical detectors
```

#### Task 6.1.2: Create Deployment Configs (1-2 hours)

```yaml
# config/phase7_production.yaml
model:
  checkpoint: models/resnet50_gaussian_nll_prod.pth
  input_size: 384
  device: cuda  # or cpu for ONNX

thresholds:
  route_to_ocr: 0.70  # DQS threshold
  route_to_correction: 0.50
  reject: 0.30
```

#### Task 6.1.3: End-to-End Testing (3-4 hours)

```bash
# Run integration tests
poetry run pytest tests/integration/test_phase7_pipeline.py -v

# Performance benchmarks
poetry run python scripts/benchmark_inference.py
```

### 6.2 Documentation Tasks

#### Task 6.2.1: Update Model Cards (1-2 hours)

```markdown
# models/phase7_resnet50_v1.md
## Model Card: Phase 7 IQA ResNet-50

**Version**: 1.0.0
**ECE**: 0.078
**Training Data**: 25K samples from 14 sources
**Input**: 384x384 RGB
**Output**: 5 severity scores [0, 1] + uncertainties
```

#### Task 6.2.2: Update PROJECT_PLAN.md (1 hour)

Mark Phase 7 checkpoints as complete.

### 6.3 Sprint 6 Completion Checklist

- [ ] DQS pipeline integration complete
- [ ] Integration tests pass
- [ ] Latency targets met (GPU < 30ms, CPU < 60ms)
- [ ] Model cards created
- [ ] Documentation updated
- [ ] Production deployment ready
- [ ] Git: `git commit -m "feat(phase7): production deployment complete"`

---

## Appendix A: Quick Reference Commands

```bash
# Sprint 0: Dataset Acquisition
poetry run python scripts/verify_all_datasets.py

# Sprint 1: Base Image Consolidation
poetry run python scripts/consolidate_base_images.py
poetry run python scripts/verify_manifest.py

# Sprint 2: Dataset Generation
poetry run python scripts/generate_iqa_dataset.py --output-dir data/phase7_mvp/01_augmented
poetry run python scripts/create_splits.py
poetry run python scripts/create_tar_archives.py
gsutil -m cp data/phase7_mvp/archives/*.tar gs://your-bucket/phase7_mvp/

# Sprint 3: Baseline Training
poetry run modal run modal/train_phase7_baseline.py

# Sprint 4: Production Model
poetry run modal run modal/train_phase7_production.py

# Sprint 5: Distillation & Validation
poetry run modal run modal/train_phase7_distillation.py
poetry run python scripts/export_onnx.py

# Sprint 6: Deployment
poetry run pytest tests/integration/test_phase7_pipeline.py -v
```

## Appendix B: Success Metrics Summary

| Sprint | Primary Metric | Target | Blocking? |
|--------|---------------|--------|-----------|
| 0 | Dataset availability | ≥80% (20K images) | Yes |
| 1 | Consolidation complete | manifest.json valid | Yes |
| 2 | Dataset generated | 25K images + splits | Yes |
| 3 | Baseline ECE | < 0.10 | Yes |
| 4 | **Production ECE** | **< 0.08** | **Yes** |
| 5 | Student ECE gap | < +0.03 vs teacher | Yes |
| 6 | Integration tests | 100% pass | Yes |

---

**Document Version**: 1.0.0
**Created**: 2025-12-15
**Owner**: Byron Williams
**Next Review**: After Sprint 2 completion
