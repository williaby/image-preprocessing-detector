#!/usr/bin/env python3
"""Create and enrich Kuzushiji Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

Kuzushiji specifics:
  - Three sub-datasets: K-MNIST (70K), K-49 (270.9K), K-Kanji (140.4K) = 481,336 total
  - Pre-modern Japanese cursive character crops (Edo period and earlier)
  - Source: ROIS-DS CODH, downloaded via Kaggle mirrors
  - No existing base metadata JSON — this script creates the full record from sidecars
  - No LLM enrichment available (character-level crops, no document context)
  - Language: ja / Jpan (Japanese, all sub-datasets)
  - capture_method: scanner_flatbed (archival digitization)
  - has_handwriting: True for ALL samples
  - Image dimensions: 28x28 px (K-MNIST/K-49), 64x64 px (K-Kanji), grayscale

Sidecar JSONL sources (produced by scripts/materialize_kuzushiji.py):
  - kmnist/train_index.jsonl  (60,000 lines)
  - kmnist/test_index.jsonl   (10,000 lines)
  - k49/train_index.jsonl     (232,365 lines)
  - k49/test_index.jsonl      (38,547 lines)
  - kkanji/all_index.jsonl    (140,424 lines)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_kuzushiji_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "kuzushiji"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/kuzushiji.py"
)


import argparse
import json
import logging
import sys
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "kuzushiji"
IS_SYNTHETIC_DATASET = False

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
OUTPUT_PATH = REGISTRY_DIR / "json" / "kuzushiji_metadata.json"

KUZUSHIJI_ROOT = Path("/mnt/e/image_detection/01_base_data/handwriting/kuzushiji")

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1
TARGET_SCHEMA_VERSION = "2.3.0"

KNOWN_CAPTURE_METHOD = "scanner_flatbed"

# Native resolutions per sub-dataset (px, square)
_RESOLUTION_PX: dict[str, int] = {
    "kmnist": 28,
    "k49": 28,
    "kkanji": 64,
}


# ===================================================================
# SIDECAR LOADING
# ===================================================================


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file, returning a list of records."""
    records: list[dict[str, Any]] = []
    if not path.exists():
        log.warning("Sidecar not found: %s", path)
        return records
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_all_sidecars(
    kuzushiji_root: Path,
) -> list[dict[str, Any]]:
    """Load all five sidecar JSONL files and merge into a flat list.

    Returns:
        List of dicts, each with keys:
          sub_dataset, split, filename, char_unicode,
          label_int (kmnist/k49 only), image_path_rel
    """
    entries: list[dict[str, Any]] = []

    # K-MNIST
    for split in ("train", "test"):
        path = kuzushiji_root / "kmnist" / f"{split}_index.jsonl"
        recs = _load_jsonl(path)
        for r in recs:
            entries.append(
                {
                    "sub_dataset": "kmnist",
                    "split": r.get("split", split),
                    "filename": r["filename"],
                    "char_unicode": r.get("char_unicode", ""),
                    "label_int": r.get("label_int"),
                    # relative path within kuzushiji root
                    "image_path_rel": f"kmnist/images/{split}/{r['filename']}",
                }
            )
        log.info("  kmnist/%s: %d records", split, len(recs))

    # K-49
    for split in ("train", "test"):
        path = kuzushiji_root / "k49" / f"{split}_index.jsonl"
        recs = _load_jsonl(path)
        for r in recs:
            entries.append(
                {
                    "sub_dataset": "k49",
                    "split": r.get("split", split),
                    "filename": r["filename"],
                    "char_unicode": r.get("char_unicode", ""),
                    "label_int": r.get("label_int"),
                    "image_path_rel": f"k49/images/{split}/{r['filename']}",
                }
            )
        log.info("  k49/%s: %d records", split, len(recs))

    # K-Kanji: filename is "<char>/xxxxxxxx.png"
    path = kuzushiji_root / "kkanji" / "all_index.jsonl"
    recs = _load_jsonl(path)
    for r in recs:
        entries.append(
            {
                "sub_dataset": "kkanji",
                "split": "all",
                "filename": r["filename"],
                "char_unicode": r.get("char_unicode", ""),
                "label_int": None,
                "image_path_rel": f"kkanji/kkanji2/{r['filename']}",
            }
        )
    log.info("  kkanji/all: %d records", len(recs))

    log.info("Total entries loaded: %d", len(entries))
    return entries


# ===================================================================
# SAMPLE RECORD CONSTRUCTION
# ===================================================================


def _resolution_category(px: int) -> str:
    """Map pixel dimension to resolution category string."""
    if px < 150:
        return "low_<150"
    if px < 300:
        return "medium_150-299"
    if px == 300:
        return "standard_300"
    return "high_>300"


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary from enrichment data."""
    fields: list[dict[str, Any]] = []
    for field_name, conf_key in [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
    ]:
        confidence = float(data.get(conf_key) or 0.0)
        if confidence >= 0.9:
            category = "hard_label"
        elif confidence >= 0.7:
            category = "soft_label"
        elif confidence >= 0.5:
            category = "active_learning"
        else:
            category = "unreliable"
        fields.append(
            {
                "field": field_name,
                "confidence": round(confidence, 4),
                "category": category,
                "is_soft_label": category == "soft_label",
            }
        )
    min_field = min(fields, key=lambda f: f["confidence"])
    return {
        "min_confidence": min_field["confidence"],
        "min_confidence_field": min_field["field"],
        "min_confidence_category": min_field["category"],
        "assessed_field_count": len(fields),
        "hard_field_count": sum(1 for f in fields if f["category"] == "hard_label"),
        "soft_field_count": sum(1 for f in fields if f["category"] == "soft_label"),
        "field_summary": fields,
        "computed_at": datetime.now(UTC).isoformat(),
    }


def _build_enrichment_data(entry: dict[str, Any]) -> dict[str, Any]:
    """Build the enrichment data dict for a single Kuzushiji sample."""
    sub_dataset = entry["sub_dataset"]
    px = _RESOLUTION_PX.get(sub_dataset, 28)

    data: dict[str, Any] = {}

    # LAYOUT — single character crop, single text region
    data["layout_detections"] = [
        {
            "class_name": "Text",
            "canonical_class": "TEXT",
            "bbox": [0, 0, px, px],
            "confidence": 1.0,
            "source": "dataset_documentation",
            "source_label": "handwritten_character",
        }
    ]
    data["layout_source"] = "dataset_documentation"
    data["layout_confidence"] = 1.0
    data["layout_detection_count"] = 1

    # CAPTURE METHOD — archival scanner digitization
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN — Historical/cultural documents
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 0.9
    data["domain_detection_method"] = "dataset_documentation"
    data["domain_content_type"] = "handwritten_character"

    # LANGUAGE / SCRIPT
    data["iso639_language"] = "ja"
    data["iso15924_script"] = "Jpan"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Jpan")

    # CONTENT FLAGS
    data["has_table"] = False
    data["has_formula"] = False
    data["has_code"] = False
    data["has_signature"] = False
    data["has_figure"] = False
    data["has_handwriting"] = True
    data["content_flags_tier"] = "tier_0_exact"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 1.0
    data["handwriting_present"] = True

    # ORIENTATION — character crops, canonical upright orientation
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.9
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT
    data["split"] = entry.get("split", "unknown")

    # TEXT SCOPE — single character
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "character"

    # IMAGE PROPERTIES — all kuzushiji images are grayscale PNGs
    data["image_properties_color_mode"] = "grayscale"

    # RESOLUTION — from dataset documentation (fixed dimensions)
    data["resolution_pixels"] = [px, px]
    data["resolution_category"] = _resolution_category(px)

    # TEXT CONTENT — Unicode character transcription
    char_unicode = entry.get("char_unicode", "")
    if char_unicode:
        data["text_has_content"] = True
        data["text_content_confidence"] = 1.0
        data["text_content_source"] = "dataset_labels"
        data["text_statistics"] = {
            "char_count": 1,
            "word_count": 0,
            "line_count": 1,
            "has_content": True,
        }
        data["transcription"] = char_unicode
    else:
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "has_content": False,
        }

    # TEXT DIRECTION — Japanese can be horizontal or vertical; character crops are neutral
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # SUB-DATASET TAG
    data["sub_dataset"] = sub_dataset

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)
    return data


def _build_sample_record(
    entry: dict[str, Any],
    now_iso: str,
) -> dict[str, Any]:
    """Build a complete sample metadata record from a sidecar entry."""
    sub_dataset = entry["sub_dataset"]
    px = _RESOLUTION_PX.get(sub_dataset, 28)
    image_path_rel = entry["image_path_rel"]

    # Extract the bare filename (last component)
    bare_filename = Path(image_path_rel).name

    # Original labels
    raw_labels: dict[str, Any] = {
        "dataset": "kuzushiji",
        "sub_dataset": sub_dataset,
        "split": entry.get("split", "unknown"),
        "writing_system": "classical-japanese",
        "historical": True,
        "resolution_px": px,
    }
    char_unicode = entry.get("char_unicode", "")
    if char_unicode:
        raw_labels["char_unicode"] = char_unicode
    if entry.get("label_int") is not None:
        raw_labels["label_int"] = entry["label_int"]

    original_labels: dict[str, Any] = {
        "raw_labels": raw_labels,
    }
    if char_unicode:
        original_labels["transcription"] = char_unicode
        original_labels["language_code"] = "ja"
        original_labels["script_name"] = "Jpan"
        original_labels["iso15924_script_code"] = "Jpan"

    enrichment_data = _build_enrichment_data(entry)
    enrichment_version: dict[str, Any] = {
        "version": ENRICHMENT_VERSION_NUMBER,
        "created_at": now_iso,
        "created_by": "integrate_kuzushiji_enrichments.py",
        "method": "tier_1_annotation",
        "description": (
            f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
            "dataset documentation + sidecar labels. "
            "Language ja/Jpan, capture scanner_flatbed, has_handwriting=True."
        ),
        "script_version": SCRIPT_VERSION,
        "data": enrichment_data,
    }

    return {
        "id": str(uuid.uuid4()),
        "file_hash": None,
        "source": {
            "dataset_name": DATASET_NAME,
            "dataset_version": "1.0",
            "original_path": image_path_rel,
            "original_filename": bare_filename,
            "download_date": "2026-02-23",
            "split": entry.get("split", "unknown"),
        },
        "original_labels": original_labels,
        "original_file": {
            "format": "PNG",
            "width_px": px,
            "height_px": px,
            "channels": 1,
            "bit_depth": 8,
            "file_size_bytes": None,
            "dpi": None,
            "color_space": "L",
        },
        "enrichments": {
            "current_version": ENRICHMENT_VERSION_NUMBER,
            "versions": [enrichment_version],
        },
        "record_meta": {
            "created_at": now_iso,
            "created_by": "integrate_kuzushiji_enrichments.py",
            "schema_version": TARGET_SCHEMA_VERSION,
        },
    }


# ===================================================================
# MAIN INTEGRATION
# ===================================================================


def run_integration(
    entries: list[dict[str, Any]],
    dry_run: bool = False,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build all sample records with enrichment data."""
    now_iso = datetime.now(UTC).isoformat()

    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "has_transcription": 0,
        "sub_dataset_dist": Counter(),
        "split_dist": Counter(),
        "domain_dist": Counter(),
    }

    samples: list[dict[str, Any]] = []
    work_entries = entries if limit is None else entries[:limit]

    for entry in work_entries:
        stats["total"] += 1
        record = _build_sample_record(entry, now_iso)
        stats["integrated"] += 1
        char = entry.get("char_unicode", "")
        if char:
            stats["has_transcription"] += 1
        stats["sub_dataset_dist"][entry["sub_dataset"]] += 1
        stats["split_dist"][entry.get("split", "unknown")] += 1
        stats["domain_dist"]["EDU"] += 1

        if not dry_run:
            samples.append(record)

        if stats["total"] % 50_000 == 0:
            log.info(
                "  Progress: %d / %d records processed",
                stats["total"],
                len(work_entries),
            )

    return samples, stats


def print_summary(stats: dict[str, Any]) -> None:
    """Print integration summary."""
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total entries:       {stats['total']}")
    print(f"Integrated:          {stats['integrated']}")
    print(f"Has transcription:   {stats['has_transcription']}")
    print("\nSub-dataset distribution:")
    for k, v in sorted(stats["sub_dataset_dist"].items()):
        print(f"  {k:12s}: {v:7d}")
    print("\nSplit distribution:")
    for k, v in sorted(stats["split_dist"].items()):
        print(f"  {k:12s}: {v:7d}")
    print("=" * 60)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"Create and enrich {DATASET_NAME} Layer 2 metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Output JSON path (default: %(default)s)",
    )
    parser.add_argument(
        "--kuzushiji-root",
        type=Path,
        default=KUZUSHIJI_ROOT,
        help="Root directory containing kuzushiji sub-datasets",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process and report stats without writing output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N entries (for testing)",
    )
    args = parser.parse_args()

    if not args.kuzushiji_root.is_dir():
        log.error("Kuzushiji root not found: %s", args.kuzushiji_root)
        return 1

    log.info("Loading sidecar JSONL files from %s", args.kuzushiji_root)
    entries = load_all_sidecars(args.kuzushiji_root)
    if not entries:
        log.error(
            "No sidecar entries found — run scripts/materialize_kuzushiji.py first"
        )
        return 1

    start = time.monotonic()
    samples, stats = run_integration(entries, dry_run=args.dry_run, limit=args.limit)
    elapsed = time.monotonic() - start

    print_summary(stats)
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run — no output written")
    else:
        split_counts: dict[str, int] = dict(stats["split_dist"])
        metadata: dict[str, Any] = {
            "dataset_name": DATASET_NAME,
            "sample_count": len(samples),
            "splits_included": sorted(split_counts.keys()),
            "split_counts": split_counts,
            "created_at": datetime.now(UTC).isoformat(),
            "schema_version": TARGET_SCHEMA_VERSION,
            "script_version": SCRIPT_VERSION,
            "git_sha": None,
            "samples": samples,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing %d samples to %s ...", len(samples), args.output)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False)
        size_mb = args.output.stat().st_size / (1024 * 1024)
        log.info("Done. Written %d samples (%.1f MB).", len(samples), size_mb)

    return 0


if __name__ == "__main__":
    sys.exit(main())
