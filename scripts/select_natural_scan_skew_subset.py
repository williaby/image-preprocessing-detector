#!/usr/bin/env python3
"""Select stratified natural scan subset for skew training dataset.

Scans available document-level datasets on disk, loads Layer 2 metadata where
available, and selects a stratified subset for the skew training pipeline.
Outputs a manifest JSON (not images) that downstream tools use to copy/label.

This script does NOT run classical skew detection — that's a separate step
(`scripts/label_skew_classical.py`) that operates on the manifest output.

Stratification dimensions:
  1. Page orientation (portrait/landscape/square)
  2. Text direction (LTR/RTL/vertical/mixed)
  3. Document layout type (inferred from dataset + metadata)
  4. Domain (from Layer 2 metadata or dataset defaults)
  5. Handwriting presence (from metadata or dataset defaults)
  6. Capture method (from metadata or dataset defaults)

Held-back scripts (test-only, never in training):
  - Japanese (Jpan) from MDIW13 — vertical text generalization
  (Synthetic dataset already covers Geor, Armn, Kore held-backs)

Output:
  output_dir/
    natural_scan_manifest.json   # Full manifest with all selected images
    selection_report.json        # Stratification statistics

Usage:
    # Dry run (statistics only)
    python scripts/select_natural_scan_skew_subset.py \\
        --base-dir /mnt/e/image_detection/01_base_data \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --output-dir /mnt/e/image_detection/03_training_datasets/skew \\
        --total-images 20000 --dry-run

    # Full selection
    python scripts/select_natural_scan_skew_subset.py \\
        --base-dir /mnt/e/image_detection/01_base_data \\
        --metadata-dir /mnt/e/image_detection/metadata_registry/json \\
        --output-dir /mnt/e/image_detection/03_training_datasets/skew \\
        --total-images 20000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_IMAGE_DIM = 400  # Minimum pixels on shorter side for document-level images
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10

# Scripts held back for test-only in natural scan subset
# (synthetic dataset already covers Geor, Armn, Kore)
HELD_BACK_SCRIPTS = {"Jpan"}

# Script name normalization (folder name -> ISO 15924 code)
SCRIPT_NAME_MAP: dict[str, str] = {
    "Arabic": "Arab",
    "Bangla": "Beng",
    "Gujrati": "Gujr",
    "Gurmukhi": "Guru",
    "Hindi": "Deva",
    "Japanese": "Jpan",
    "Kannada": "Knda",
    "Malayalam": "Mlym",
    "Oriya": "Orya",
    "Roman": "Latn",
    "Tamil": "Taml",
    "Telugu": "Telu",
    "Thai": "Thai",
}

# Script -> text direction mapping
SCRIPT_DIRECTION: dict[str, str] = {
    "Arab": "rtl",
    "Hebr": "rtl",
    "Latn": "ltr",
    "Cyrl": "ltr",
    "Deva": "ltr",
    "Beng": "ltr",
    "Gujr": "ltr",
    "Guru": "ltr",
    "Knda": "ltr",
    "Mlym": "ltr",
    "Orya": "ltr",
    "Taml": "ltr",
    "Telu": "ltr",
    "Thai": "ltr",
    "Tibt": "ltr",
    "Hans": "vertical",
    "Hant": "vertical",
    "Jpan": "vertical",
    "Kore": "vertical",
}


# ---------------------------------------------------------------------------
# Dataset configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatasetConfig:
    """Configuration for a source dataset."""

    name: str
    base_path: str  # Relative to --base-dir
    script: str | None  # ISO 15924 code, None if multi-script with folder structure
    text_direction: str  # ltr, rtl, vertical, mixed
    capture_method: str  # scanner_flatbed, camera, born_digital, mixed
    domain: str  # ADM, FIN, SCI, EDU, GOV, TEC, IDT, COM, MIX
    has_handwriting: bool
    layout_type: str  # single_column, multi_column, table, form, mixed
    image_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tif", ".tiff")
    max_depth: int = 5  # How deep to search for images
    multi_script_folders: bool = False  # True if organized by script subfolder
    target_count: int = 0  # Target selection count (0 = proportional)
    min_dim: int = MIN_IMAGE_DIM  # Override minimum dimension


# All available datasets with document-level images
# Targets tuned for: ~60% LTR, ~22% RTL, ~12% multi-script/Indic, ~6% other
# to provide meaningful non-Latin coverage for skew model generalization.
DATASET_CONFIGS: list[DatasetConfig] = [
    # --- Latin LTR (reduced from 66% to ~52% to allow more RTL/multilingual) ---
    DatasetConfig(
        name="rvl-cdip",
        base_path="documents/rvl_cdip/images",
        script="Latn",
        text_direction="ltr",
        capture_method="scanner_flatbed",
        domain="MIX",
        has_handwriting=False,
        layout_type="mixed",
        target_count=4500,
    ),
    DatasetConfig(
        name="tobacco800",
        base_path="degraded/tobacco800/images",
        script="Latn",
        text_direction="ltr",
        capture_method="scanner_flatbed",
        domain="GOV",
        has_handwriting=False,
        layout_type="single_column",
        target_count=800,
    ),
    DatasetConfig(
        name="nist-sd6",
        base_path="forms/nist_sd6/sd06/data",
        script="Latn",
        text_direction="ltr",
        capture_method="scanner_flatbed",
        domain="FIN",
        has_handwriting=True,
        layout_type="form",
        target_count=500,
    ),
    # --- Arabic RTL (increased to ~22% total) ---
    DatasetConfig(
        name="arabic-docs",
        base_path="language/arabic_docs_ocr/Documents/Documents",
        script="Arab",
        text_direction="rtl",
        capture_method="mixed",
        domain="MIX",
        has_handwriting=False,
        layout_type="mixed",
        target_count=2000,
    ),
    DatasetConfig(
        name="yarmouk",
        base_path="language/yarmouk",
        script="Arab",
        text_direction="rtl",
        capture_method="scanner_flatbed",
        domain="EDU",
        has_handwriting=False,
        layout_type="single_column",
        target_count=2000,
    ),
    # --- Multi-script (MDIW13 documents — all available) ---
    DatasetConfig(
        name="mdiw13-hw-doc",
        base_path="language/mdiw13/SIW_Database/SIW_MultiscriptDatabase/MultiscriptHandwrittenDocuments",
        script=None,  # Multi-script via folder structure
        text_direction="mixed",
        capture_method="scanner_flatbed",
        domain="EDU",
        has_handwriting=True,
        layout_type="single_column",
        multi_script_folders=True,
        target_count=382,  # Take all available
    ),
    DatasetConfig(
        name="mdiw13-pr-doc",
        base_path="language/mdiw13/SIW_Database/SIW_MultiscriptDatabase/MultiscriptPrintedDocuments",
        script=None,  # Multi-script via folder structure
        text_direction="mixed",
        capture_method="scanner_flatbed",
        domain="EDU",
        has_handwriting=False,
        layout_type="single_column",
        multi_script_folders=True,
        target_count=753,  # Take all available
    ),
    # --- DocLayNet (reduced, diverse born-digital) ---
    DatasetConfig(
        name="doclaynet",
        base_path="documents/doclaynet/documents/png",
        script="Latn",
        text_direction="ltr",
        capture_method="born_digital",
        domain="MIX",
        has_handwriting=False,
        layout_type="mixed",
        target_count=4500,
    ),
    # --- ID documents (camera captures) ---
    DatasetConfig(
        name="midv500",
        base_path="documents/midv500/midv500",
        script="Latn",
        text_direction="mixed",
        capture_method="camera",
        domain="IDT",
        has_handwriting=False,
        layout_type="form",
        target_count=500,
    ),
    # --- Indic scripts (increased for non-Latin coverage) ---
    DatasetConfig(
        name="cvsi",
        base_path="language/cvsi",
        script="Deva",
        text_direction="ltr",
        capture_method="camera",
        domain="EDU",
        has_handwriting=False,
        layout_type="single_column",
        min_dim=200,  # Video captions are smaller
        target_count=500,
    ),
    DatasetConfig(
        name="nepali-hw",
        base_path="language/nepali_handwritten",
        script="Deva",
        text_direction="ltr",
        capture_method="scanner_flatbed",
        domain="EDU",
        has_handwriting=True,
        layout_type="single_column",
        min_dim=200,
        target_count=500,
    ),
    # --- DIQA-5000 (quality-diverse, mixed capture) ---
    DatasetConfig(
        name="diqa-5000",
        base_path="ocr_quality/pics",
        script="Latn",
        text_direction="ltr",
        capture_method="mixed",
        domain="MIX",
        has_handwriting=False,
        layout_type="mixed",
        target_count=1000,
    ),
    # --- MLT19 (scene text, multi-language, camera captures) ---
    DatasetConfig(
        name="mlt19",
        base_path="language/mlt19",
        script="Latn",
        text_direction="mixed",
        capture_method="camera",
        domain="COM",
        has_handwriting=False,
        layout_type="mixed",
        min_dim=200,
        target_count=1000,
    ),
]


# ---------------------------------------------------------------------------
# Image candidate record
# ---------------------------------------------------------------------------


@dataclass
class ImageCandidate:
    """A candidate image for the natural scan subset."""

    path: str  # Absolute path to image
    dataset: str  # Source dataset name
    filename: str  # Original filename
    script: str  # ISO 15924 code
    text_direction: str  # ltr, rtl, vertical, mixed
    capture_method: str  # scanner_flatbed, camera, born_digital, mixed
    domain: str  # Domain code
    has_handwriting: bool
    layout_type: str  # Layout category
    width: int = 0  # Image width (populated if --check-dims)
    height: int = 0  # Image height (populated if --check-dims)
    orientation: str = "unknown"  # portrait, landscape, square
    split: str = ""  # train, val, test (assigned during stratification)
    file_hash: str = ""  # SHA256 of path for deterministic splitting


# ---------------------------------------------------------------------------
# Discovery functions
# ---------------------------------------------------------------------------


def discover_dataset_images(
    base_dir: Path, config: DatasetConfig
) -> list[ImageCandidate]:
    """Discover all images in a dataset directory.

    Args:
        base_dir: Root base data directory.
        config: Dataset configuration.

    Returns:
        List of ImageCandidate records.
    """
    dataset_path = base_dir / config.base_path
    if not dataset_path.exists():
        logger.warning("Dataset path not found: %s (%s)", dataset_path, config.name)
        return []

    candidates: list[ImageCandidate] = []
    extensions = set(config.image_extensions)

    if config.multi_script_folders:
        # Images organized by script subfolder (e.g., MDIW13)
        for script_dir in sorted(dataset_path.iterdir()):
            if not script_dir.is_dir():
                continue
            folder_name = script_dir.name
            script_code = SCRIPT_NAME_MAP.get(folder_name, folder_name)
            text_dir = SCRIPT_DIRECTION.get(script_code, config.text_direction)

            for img_path in _find_images(script_dir, extensions, config.max_depth):
                candidates.append(
                    ImageCandidate(
                        path=str(img_path),
                        dataset=config.name,
                        filename=img_path.name,
                        script=script_code,
                        text_direction=text_dir,
                        capture_method=config.capture_method,
                        domain=config.domain,
                        has_handwriting=config.has_handwriting,
                        layout_type=config.layout_type,
                    )
                )
    else:
        # Flat or nested structure, single script
        script_code = config.script or "UNK"
        for img_path in _find_images(dataset_path, extensions, config.max_depth):
            candidates.append(
                ImageCandidate(
                    path=str(img_path),
                    dataset=config.name,
                    filename=img_path.name,
                    script=script_code,
                    text_direction=config.text_direction,
                    capture_method=config.capture_method,
                    domain=config.domain,
                    has_handwriting=config.has_handwriting,
                    layout_type=config.layout_type,
                )
            )

    logger.info(
        "Discovered %d images in %s (%s)",
        len(candidates),
        config.name,
        dataset_path,
    )
    return candidates


def _find_images(
    root: Path, extensions: set[str], max_depth: int
) -> list[Path]:
    """Recursively find image files up to max_depth."""
    results: list[Path] = []
    _walk_images(root, extensions, max_depth, 0, results)
    return results


def _walk_images(
    current: Path,
    extensions: set[str],
    max_depth: int,
    depth: int,
    results: list[Path],
) -> None:
    """Walk directory tree collecting image files."""
    if depth > max_depth:
        return
    try:
        for entry in sorted(current.iterdir()):
            if entry.is_file() and entry.suffix.lower() in extensions:
                results.append(entry)
            elif entry.is_dir() and depth < max_depth:
                _walk_images(entry, extensions, max_depth, depth + 1, results)
    except PermissionError:
        logger.warning("Permission denied: %s", current)


def enrich_with_rvl_class(candidate: ImageCandidate) -> None:
    """Extract RVL-CDIP class from filename pattern: rvl_{class}_{num}.ext."""
    parts = candidate.filename.split("_")
    if len(parts) >= 2 and parts[0] == "rvl":
        rvl_class = parts[1]
        # Map RVL classes to layout types
        rvl_layout_map = {
            "letter": "single_column",
            "memo": "single_column",
            "email": "single_column",
            "resume": "single_column",
            "handwritten": "single_column",
            "advertisement": "mixed",
            "presentation": "mixed",
            "news": "multi_column",
            "scientific": "multi_column",
            "budget": "table",
            "invoice": "table",
            "form": "form",
            "questionnaire": "form",
            "specification": "single_column",
            "file": "single_column",
        }
        candidate.layout_type = rvl_layout_map.get(rvl_class, "mixed")
        if rvl_class == "handwritten":
            candidate.has_handwriting = True


def enrich_with_arabic_docs_class(candidate: ImageCandidate) -> None:
    """Extract Arabic-Docs category from path."""
    path = Path(candidate.path)
    # Structure: .../Documents/Documents/{Category}/img/{file}
    parts = path.parts
    for i, part in enumerate(parts):
        if part == "Documents" and i + 2 < len(parts):
            category = parts[i + 1]
            category_layout_map = {
                "Administrative form": "form",
                "Book": "single_column",
                "Business card": "form",
                "Comics": "mixed",
                "Handwritten text": "single_column",
                "Invoice": "table",
                "Label": "mixed",
                "Magazine": "multi_column",
                "Map": "mixed",
                "Newspaper": "multi_column",
                "Official document": "single_column",
                "Receipt": "table",
            }
            candidate.layout_type = category_layout_map.get(category, "mixed")
            if category == "Handwritten text":
                candidate.has_handwriting = True
            break


# ---------------------------------------------------------------------------
# Dimension checking
# ---------------------------------------------------------------------------


def check_image_dimensions(
    candidates: list[ImageCandidate], min_dim: int
) -> list[ImageCandidate]:
    """Filter candidates by minimum image dimension and set orientation.

    Args:
        candidates: List of image candidates.
        min_dim: Minimum pixel dimension on shorter side.

    Returns:
        Filtered list with width/height/orientation populated.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL not available; skipping dimension check")
        return candidates

    valid: list[ImageCandidate] = []
    skipped = 0
    errors = 0

    for i, c in enumerate(candidates):
        if i % 5000 == 0 and i > 0:
            logger.info(
                "Dimension check progress: %d/%d (valid: %d, skipped: %d)",
                i,
                len(candidates),
                len(valid),
                skipped,
            )
        try:
            with Image.open(c.path) as img:
                w, h = img.size
        except Exception:
            errors += 1
            continue

        shorter = min(w, h)
        if shorter < min_dim:
            skipped += 1
            continue

        c.width = w
        c.height = h
        if abs(w - h) < 50:
            c.orientation = "square"
        elif w > h:
            c.orientation = "landscape"
        else:
            c.orientation = "portrait"
        valid.append(c)

    logger.info(
        "Dimension check: %d valid, %d too small, %d errors (from %d)",
        len(valid),
        skipped,
        errors,
        len(candidates),
    )
    return valid


# ---------------------------------------------------------------------------
# Stratified selection
# ---------------------------------------------------------------------------


def compute_file_hash(path: str) -> str:
    """Compute deterministic hash from file path for reproducible splitting."""
    return hashlib.sha256(path.encode()).hexdigest()


def assign_splits(
    candidates: list[ImageCandidate],
    seed: int = 42,
) -> None:
    """Assign train/val/test splits with held-back script enforcement.

    Held-back scripts go exclusively to test. Remaining images are split
    80/10/10 using deterministic path hashing for reproducibility.
    """
    rng = random.Random(seed)

    for c in candidates:
        c.file_hash = compute_file_hash(c.path)

        if c.script in HELD_BACK_SCRIPTS:
            c.split = "test"
        else:
            # Deterministic split based on hash
            hash_val = int(c.file_hash[:8], 16) / 0xFFFFFFFF
            if hash_val < TRAIN_RATIO:
                c.split = "train"
            elif hash_val < TRAIN_RATIO + VAL_RATIO:
                c.split = "val"
            else:
                c.split = "test"

    # Count splits
    split_counts = Counter(c.split for c in candidates)
    logger.info(
        "Split assignment: train=%d, val=%d, test=%d",
        split_counts["train"],
        split_counts["val"],
        split_counts["test"],
    )

    # Count held-back in test
    held_back = sum(1 for c in candidates if c.script in HELD_BACK_SCRIPTS)
    total_test = split_counts["test"]
    logger.info(
        "Test split: %d held-back scripts (%.1f%% of test), %d in-distribution",
        held_back,
        100 * held_back / total_test if total_test else 0,
        total_test - held_back,
    )


def stratified_select(
    all_candidates: dict[str, list[ImageCandidate]],
    dataset_configs: dict[str, DatasetConfig],
    total_target: int,
    seed: int = 42,
) -> list[ImageCandidate]:
    """Select stratified subset from all candidates.

    Uses per-dataset target counts from config, with proportional fallback
    for datasets without explicit targets.

    Args:
        all_candidates: Candidates grouped by dataset name.
        dataset_configs: Dataset configurations keyed by name.
        total_target: Total images to select.
        seed: Random seed for reproducibility.

    Returns:
        Selected candidates list.
    """
    rng = random.Random(seed)
    selected: list[ImageCandidate] = []
    remaining_budget = total_target

    # Phase 1: Fill datasets with explicit targets
    targeted_datasets = {
        name: cfg
        for name, cfg in dataset_configs.items()
        if cfg.target_count > 0 and name in all_candidates
    }

    for name, cfg in targeted_datasets.items():
        pool = all_candidates.get(name, [])
        if not pool:
            logger.warning("No candidates for %s (target: %d)", name, cfg.target_count)
            continue

        target = min(cfg.target_count, len(pool))
        if target < cfg.target_count:
            logger.warning(
                "%s: only %d available (target: %d)", name, len(pool), cfg.target_count
            )

        sample = rng.sample(pool, target)
        selected.extend(sample)
        remaining_budget -= target
        logger.info(
            "Selected %d from %s (target: %d, available: %d)",
            target,
            name,
            cfg.target_count,
            len(pool),
        )

    # Phase 2: Fill remaining budget proportionally from untargeted datasets
    untargeted = {
        name: cands
        for name, cands in all_candidates.items()
        if name not in targeted_datasets and cands
    }

    if remaining_budget > 0 and untargeted:
        total_available = sum(len(c) for c in untargeted.values())
        for name, pool in untargeted.items():
            proportion = len(pool) / total_available
            target = min(int(remaining_budget * proportion), len(pool))
            if target > 0:
                sample = rng.sample(pool, target)
                selected.extend(sample)
                logger.info(
                    "Selected %d from %s (proportional)", target, name
                )

    logger.info(
        "Total selected: %d (target: %d)", len(selected), total_target
    )
    return selected


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def generate_report(candidates: list[ImageCandidate]) -> dict[str, Any]:
    """Generate stratification statistics report."""
    report: dict[str, Any] = {
        "total_selected": len(candidates),
        "splits": dict(Counter(c.split for c in candidates)),
    }

    # Per-dimension distributions
    for dim in [
        "dataset",
        "script",
        "text_direction",
        "orientation",
        "layout_type",
        "domain",
        "capture_method",
    ]:
        dist = Counter(getattr(c, dim) for c in candidates)
        report[f"{dim}_distribution"] = dict(dist.most_common())

    # Handwriting
    hw_count = sum(1 for c in candidates if c.has_handwriting)
    report["handwriting_percentage"] = round(100 * hw_count / len(candidates), 1)

    # Per-split breakdown
    for split_name in ["train", "val", "test"]:
        split_cands = [c for c in candidates if c.split == split_name]
        if split_cands:
            report[f"{split_name}_count"] = len(split_cands)
            report[f"{split_name}_scripts"] = dict(
                Counter(c.script for c in split_cands).most_common()
            )
            report[f"{split_name}_datasets"] = dict(
                Counter(c.dataset for c in split_cands).most_common()
            )

    # Held-back verification
    held_back_in_train = [
        c for c in candidates if c.script in HELD_BACK_SCRIPTS and c.split == "train"
    ]
    held_back_in_val = [
        c for c in candidates if c.script in HELD_BACK_SCRIPTS and c.split == "val"
    ]
    report["held_back_leak_train"] = len(held_back_in_train)
    report["held_back_leak_val"] = len(held_back_in_val)
    report["held_back_scripts"] = list(HELD_BACK_SCRIPTS)

    return report


def print_report(report: dict[str, Any]) -> None:
    """Print human-readable report summary."""
    print("\n" + "=" * 70)
    print("NATURAL SCAN SELECTION REPORT")
    print("=" * 70)

    print(f"\nTotal selected: {report['total_selected']}")
    print(f"Splits: {report['splits']}")

    for dim in [
        "dataset",
        "script",
        "text_direction",
        "orientation",
        "layout_type",
        "domain",
        "capture_method",
    ]:
        key = f"{dim}_distribution"
        if key in report:
            print(f"\n{dim.upper()} DISTRIBUTION:")
            dist = report[key]
            total = sum(dist.values())
            for name, count in dist.items():
                pct = 100 * count / total if total else 0
                bar = "#" * int(pct / 2)
                print(f"  {name:25s} {count:6d} ({pct:5.1f}%) {bar}")

    print(f"\nHandwriting: {report['handwriting_percentage']:.1f}%")

    # Held-back verification
    leak_train = report.get("held_back_leak_train", 0)
    leak_val = report.get("held_back_leak_val", 0)
    if leak_train > 0 or leak_val > 0:
        print(f"\nWARNING: Held-back leak — train: {leak_train}, val: {leak_val}")
    else:
        print("\nHeld-back scripts: CLEAN (no leakage into train/val)")

    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run natural scan subset selection."""
    parser = argparse.ArgumentParser(
        description="Select stratified natural scan subset for skew training"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        required=True,
        help="Root base data directory (e.g., /mnt/e/image_detection/01_base_data)",
    )
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=None,
        help="Layer 2 metadata directory (optional, for enrichment)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for manifest and report",
    )
    parser.add_argument(
        "--total-images",
        type=int,
        default=20000,
        help="Total images to select (default: 20000)",
    )
    parser.add_argument(
        "--check-dims",
        action="store_true",
        default=False,
        help="Check image dimensions (slow but filters small crops)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show statistics without writing output",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    start_time = time.time()
    base_dir = args.base_dir

    if not base_dir.exists():
        logger.error("Base directory not found: %s", base_dir)
        return 1

    # Phase 1: Discover all candidate images
    logger.info("Phase 1: Discovering candidate images...")
    all_candidates: dict[str, list[ImageCandidate]] = {}
    dataset_configs: dict[str, DatasetConfig] = {}
    total_discovered = 0

    for config in DATASET_CONFIGS:
        candidates = discover_dataset_images(base_dir, config)
        if not candidates:
            continue

        # Enrich with dataset-specific metadata
        if config.name == "rvl-cdip":
            for c in candidates:
                enrich_with_rvl_class(c)
        elif config.name == "arabic-docs":
            for c in candidates:
                enrich_with_arabic_docs_class(c)

        all_candidates[config.name] = candidates
        dataset_configs[config.name] = config
        total_discovered += len(candidates)

    logger.info("Total discovered: %d images across %d datasets", total_discovered, len(all_candidates))

    if total_discovered == 0:
        logger.error("No images found. Check --base-dir path.")
        return 1

    # Phase 2: Dimension filtering (optional, slow)
    if args.check_dims:
        logger.info("Phase 2: Checking image dimensions (this may take a while)...")
        for name, candidates in list(all_candidates.items()):
            config = dataset_configs[name]
            min_dim = config.min_dim
            filtered = check_image_dimensions(candidates, min_dim)
            all_candidates[name] = filtered
            logger.info(
                "%s: %d -> %d after dimension filter (min_dim=%d)",
                name,
                len(candidates),
                len(filtered),
                min_dim,
            )
        total_after_filter = sum(len(c) for c in all_candidates.values())
        logger.info("After dimension filter: %d images", total_after_filter)

    # Phase 3: Stratified selection
    logger.info("Phase 3: Stratified selection (target: %d)...", args.total_images)
    selected = stratified_select(
        all_candidates, dataset_configs, args.total_images, seed=args.seed
    )

    # Phase 4: Assign splits
    logger.info("Phase 4: Assigning train/val/test splits...")
    assign_splits(selected, seed=args.seed)

    # Phase 5: Generate report
    report = generate_report(selected)
    print_report(report)

    elapsed = time.time() - start_time
    report["elapsed_seconds"] = round(elapsed, 1)

    if args.dry_run:
        logger.info("Dry run complete (%.1fs). No files written.", elapsed)
        return 0

    # Phase 6: Write outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest_path = args.output_dir / "natural_scan_manifest.json"
    manifest_data = {
        "version": "1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_images": len(selected),
        "base_dir": str(base_dir),
        "seed": args.seed,
        "held_back_scripts": list(HELD_BACK_SCRIPTS),
        "images": [
            {
                "path": c.path,
                "dataset": c.dataset,
                "filename": c.filename,
                "script": c.script,
                "text_direction": c.text_direction,
                "capture_method": c.capture_method,
                "domain": c.domain,
                "has_handwriting": c.has_handwriting,
                "layout_type": c.layout_type,
                "orientation": c.orientation,
                "split": c.split,
                "width": c.width,
                "height": c.height,
            }
            for c in selected
        ],
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info("Manifest written: %s (%d images)", manifest_path, len(selected))

    # Write report
    report_path = args.output_dir / "natural_scan_selection_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Report written: %s", report_path)

    logger.info("Done! (%.1fs)", elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
