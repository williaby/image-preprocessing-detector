#!/usr/bin/env python3
"""Integrate enrichment sources into casia-hwdb2-line Layer 2 metadata.

CASIA-HWDB2-line is a line-level extraction from CASIA HWDB2 full-page handwriting
scans. The Teklia HuggingFace edition (52,160 images, height=128px, variable width)
provides Chinese handwriting line images with ground-truth transcriptions.

Images are materialized from Parquet downloads via scripts/materialize_casia_hwdb2_line.py
and stored as JPEG under images/{split}/.

Enrichments applied:
  - capture_method: "scanner_flatbed" (cropped from scanned full pages)
  - has_handwriting: True (all samples)
  - iso639_language: "zh" (Chinese)
  - iso15924_script: "Hans" (Simplified Chinese)
  - script_family: "han"
  - text_direction: "ltr"
  - domain_level1: "EDU" (academic handwriting collection, CASIA research)
  - text_scope: "line"
  - text_scope_content_type: "handwritten"
  - schema_version: "2.4.0"

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_casia_hwdb2_line_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__   = "integrate-script"
__l4_dataset__    = "casia-hwdb2-line"
__l4_workstream__ = "WS4"
__l4_parser__     = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/casia_hwdb2_line.py"
)


import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ===================================================================
# DATASET CONFIGURATION
# ===================================================================
DATASET_NAME = "casia-hwdb2-line"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "casia-hwdb2-line_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v1"
ENRICHMENT_VERSION_NUMBER = 1

_BASE_DATA_DIR = Path("/mnt/e/image_detection/01_base_data")
SIDECAR_DIR = _BASE_DATA_DIR / "handwriting" / "casia-hwdb2-line"
# JSONL index files: {split}_index.jsonl with keys: filename, text
_SIDECAR_SPLITS = ("train", "test", "validation")


def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to the *_metadata.json file.

    Returns:
        Full metadata dict with ``"samples"`` list.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_transcription_index(sidecar_dir: Path) -> dict[str, str]:
    """Load JSONL sidecar files into a filename → Chinese text lookup dict.

    Reads ``{split}_index.jsonl`` files from *sidecar_dir*.  Each line is a
    JSON object with at least ``"filename"`` and ``"text"`` keys.

    Args:
        sidecar_dir: Directory containing ``*_index.jsonl`` files.

    Returns:
        Dict mapping bare filename (e.g. ``"00000001.png"``) to transcription.
        Returns empty dict on error or if files are absent.
    """
    index: dict[str, str] = {}
    for split in _SIDECAR_SPLITS:
        jsonl_path = sidecar_dir / f"{split}_index.jsonl"
        if not jsonl_path.is_file():
            log.debug("Sidecar not found: %s", jsonl_path)
            continue
        loaded = 0
        try:
            with open(jsonl_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    filename = rec.get("filename", "")
                    text = rec.get("text", "")
                    if filename and text:
                        index[filename] = text
                        loaded += 1
            log.info("  %s_index.jsonl: %d transcriptions loaded", split, loaded)
        except Exception:
            log.exception("Failed to load sidecar: %s", jsonl_path)
    log.info("  Total transcription index size: %d", len(index))
    return index


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Reliability summary dict with per-field confidence breakdown.
    """
    field_defs = [
        ("capture_method",    "capture_confidence"),
        ("domain",            "domain_confidence"),
        ("language",          "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags",     "content_flags_confidence"),
    ]
    fields: list[dict[str, Any]] = []
    for field_name, conf_key in field_defs:
        confidence = float(data.get(conf_key) or 0.0)
        if confidence >= 0.9:
            category = "hard_label"
        elif confidence >= 0.7:
            category = "soft_label"
        elif confidence >= 0.5:
            category = "active_learning"
        else:
            category = "unreliable"
        fields.append({
            "field":         field_name,
            "confidence":    round(confidence, 4),
            "category":      category,
            "is_soft_label": category == "soft_label",
        })

    min_field = min(fields, key=lambda f: f["confidence"])
    return {
        "min_confidence":          min_field["confidence"],
        "min_confidence_field":    min_field["field"],
        "min_confidence_category": min_field["category"],
        "assessed_field_count":    len(fields),
        "hard_field_count":  sum(1 for f in fields if f["category"] == "hard_label"),
        "soft_field_count":  sum(1 for f in fields if f["category"] == "soft_label"),
        "field_summary":     fields,
        "computed_at":       datetime.now(UTC).isoformat(),
    }


def integrate_sample(
    sample: dict[str, Any],
    transcription_index: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single casia-hwdb2-line sample.

    Args:
        sample: A single sample from the L2 metadata ``"samples"`` list.
        transcription_index: Optional bare-filename → Chinese text lookup.

    Returns:
        New enrichment data dict with language, handwriting, and schema fields.
    """
    # Preserve any fields already written (resolution, orientation, etc.)
    v1_data: dict[str, Any] = {}
    if sample.get("enrichments", {}).get("versions"):
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # SPLIT
    # The parser maps images/train/ and images/test/ but NOT images/validation/.
    # Derive from original_path when split is "unknown".
    # -------------------------------------------------------------------
    split = sample.get("source", {}).get("split", "unknown")
    if split == "unknown":
        orig_path = sample.get("source", {}).get("original_path", "")
        if "/validation/" in orig_path:
            split = "val"
        elif "/train/" in orig_path:
            split = "train"
        elif "/test/" in orig_path:
            split = "test"
    data["split"] = split

    # -------------------------------------------------------------------
    # CAPTURE METHOD
    # Line images cropped from CASIA-HWDB2 full-page flatbed scans.
    # -------------------------------------------------------------------
    data["capture_method"]           = "scanner_flatbed"
    data["capture_confidence"]       = 0.95
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN
    # Academic handwriting research collection (CASIA / NLPR, China)
    # -------------------------------------------------------------------
    data["domain_level1"]           = "EDU"
    data["domain_confidence"]       = 0.9
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # Simplified Chinese (ISO 639-1: zh) in Hans script (ISO 15924: Hans)
    # -------------------------------------------------------------------
    data["iso639_language"]    = "zh"
    data["iso15924_script"]    = "Hans"
    data["language_confidence"] = 0.99
    data["script_family"]      = "han"
    data["text_direction"]          = "ltr"
    data["text_directions_present"] = ["ltr"]
    data["text_scope_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS  (not applicable for single line crops)
    # -------------------------------------------------------------------
    data["layout_detections"]      = []
    data["layout_source"]          = "none"
    data["layout_confidence"]      = 0.0
    data["layout_detection_count"] = 0

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # All samples are single-line Chinese handwriting crops
    # -------------------------------------------------------------------
    data["has_table"]       = False
    data["has_figure"]      = False
    data["has_formula"]     = False
    data["has_handwriting"] = True   # Primary characteristic of this dataset
    data["has_signature"]   = False
    data["has_code"]        = False
    data["handwriting_present"]      = True
    data["content_flags_tier"]       = "tier_3_heuristic"
    data["content_flags_source"]     = "dataset_documentation"
    data["content_flags_confidence"] = 0.99

    # -------------------------------------------------------------------
    # ORIENTATION
    # Line crops are all upright (horizontal left-to-right)
    # -------------------------------------------------------------------
    data["orientation_class"]            = int(v1_data.get("orientation_class", 0))
    data["orientation_confidence"]       = float(v1_data.get("orientation_confidence", 0.9))
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # TEXT CONTENT
    # Line-level Chinese handwriting; transcription from sidecar JSONL index
    # -------------------------------------------------------------------
    data["text_has_content"]        = True
    data["text_content_confidence"] = 0.9
    data["text_content_source"]     = "dataset_documentation"
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"]              = "line"

    # Look up transcription from sidecar JSONL index (keyed by bare filename)
    orig_path = sample.get("source", {}).get("original_path", "")
    filename = Path(orig_path).name  # e.g. "00000001.png"
    if transcription_index and filename in transcription_index:
        data["transcription"] = transcription_index[filename]
    elif "transcription" in v1_data:
        data["transcription"] = v1_data["transcription"]

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # Fixed height 128px, variable width; grayscale or color
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

    # Preserve resolution fields if previously populated (except resolution_category)
    for field in (
        "resolution_pixels",
        "resolution_quality_score",
        "resolution_quality_bucket",
        "resolution_char_height_px",
    ):
        if field in v1_data:
            data[field] = v1_data[field]
    # resolution_category is meaningless for 128px line crops — suppress it
    data["resolution_category"] = None

    # -------------------------------------------------------------------
    # ADDITIONAL
    # -------------------------------------------------------------------
    data["dataset_short_code"]         = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


def run_integration(
    metadata: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with ``"samples"`` list.
        dry_run: If True, compute statistics without modifying metadata.

    Returns:
        Stats dict with distribution Counters.
    """
    transcription_index = load_transcription_index(SIDECAR_DIR)

    stats: dict[str, Any] = {
        "total":               0,
        "integrated":          0,
        "capture_method_dist": Counter(),
        "script_family_dist":  Counter(),
        "domain_dist":         Counter(),
        "split_dist":          Counter(),
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample, transcription_index)
        stats["integrated"] += 1
        stats["capture_method_dist"][integrated_data["capture_method"]] += 1
        stats["script_family_dist"][integrated_data["script_family"]] += 1
        stats["domain_dist"][integrated_data["domain_level1"]] += 1
        stats["split_dist"][integrated_data["split"]] += 1

        if not dry_run:
            new_version: dict[str, Any] = {
                "version":        ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",
                "created_at":     now,
                "created_by":     "integrate_casia_hwdb2_line_enrichments.py",
                "method":         "tier_3_heuristic",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset-documentation heuristics for CASIA-HWDB2-line Chinese handwriting"
                ),
                "script_version": SCRIPT_VERSION,
                "data":           integrated_data,
            }
            versions = sample["enrichments"]["versions"]
            replaced = False
            for i, ver in enumerate(versions):
                if ver.get("version") == ENRICHMENT_VERSION_NUMBER:
                    versions[i] = new_version
                    replaced = True
                    break
            if not replaced:
                versions.append(new_version)
            sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER

    return stats


def print_summary(stats: dict[str, Any]) -> None:
    """Print integration statistics.

    Args:
        stats: Stats dict returned by run_integration().
    """
    total = max(stats["total"], 1)
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:  {stats['total']}")
    print(f"Integrated:     {stats['integrated']}")
    print()
    print("Capture method distribution:")
    for method, count in stats["capture_method_dist"].most_common():
        print(f"  {method:25s}: {count:6d} ({count / total * 100:.1f}%)")
    print()
    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        print(f"  {sf:20s}: {count:6d} ({count / total * 100:.1f}%)")
    print()
    print("Domain distribution:")
    for dom, count in stats["domain_dist"].most_common():
        print(f"  {dom:20s}: {count:6d} ({count / total * 100:.1f}%)")
    print()
    print("Split distribution:")
    for sp, count in stats["split_dist"].most_common():
        print(f"  {sp:20s}: {count:6d} ({count / total * 100:.1f}%)")
    print("=" * 60)


def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    p = argparse.ArgumentParser(
        description=f"Integrate per-dataset enrichments into {DATASET_NAME} metadata.",
    )
    p.add_argument("--metadata", type=Path, default=METADATA_PATH)
    p.add_argument("--output",   type=Path, default=None,
                   help="Output path (default: overwrite input)")
    p.add_argument("--dry-run",  action="store_true",
                   help="Report statistics only, do not write output")
    args = p.parse_args()

    output_path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)

    start = time.monotonic()
    stats = run_integration(metadata, dry_run=args.dry_run)
    elapsed = time.monotonic() - start

    print_summary(stats)
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run — no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
