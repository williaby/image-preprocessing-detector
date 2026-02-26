#!/usr/bin/env python3
"""Integrate all enrichment sources into im2latex Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

im2latex specifics:
  - im2latex-100K subset (10,000 images)
  - Rendered LaTeX formula images (born-digital)
  - Language enrichment: empty (0 records)
  - No LLM enrichment, no Docling layout
  - capture_method: born_digital (rendered from LaTeX)
  - domain_level1: EDU (scientific/mathematical)
  - has_formula: True for ALL samples
  - has_handwriting: False (rendered, not handwritten)
  - Language: en/Latn (LaTeX math notation)
  - No layout detections needed (single formula per image)
  - Schema upgrade: v2.1 -> v2.3.0

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_im2latex_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__      = 'integrate-script'
__l4_dataset__       = 'im2latex'
__l4_workstream__    = 'WS3'
__l4_parser__        = 'src/image_preprocessing_detector/annotation/parsers/formula/im2latex.py'



import argparse
import json
import logging
import sys
import time
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
DATASET_NAME = "im2latex"
IS_SYNTHETIC_DATASET = False

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "im2latex_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "im2latex_language_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2
TARGET_SCHEMA_VERSION = "2.3.0"

KNOWN_CAPTURE_METHOD = "born_digital"


def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON."""
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def derive_color_mode(original_file: dict[str, Any]) -> str:
    """Derive color mode from image channel count."""
    channels = original_file.get("channels", 3)
    if channels == 1:
        return "grayscale"
    if channels == 4:
        return "color_alpha"
    return "color"


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary."""
    fields: list[dict[str, Any]] = []
    for field_name, conf_key in [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
    ]:
        confidence = data.get(conf_key, 0.0) or 0.0
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


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # LAYOUT - single formula detection covering full image
    res = v1_data.get("resolution_pixels", [100, 40])
    w = res[0] if isinstance(res, list) and len(res) >= 2 else 100
    h = res[1] if isinstance(res, list) and len(res) >= 2 else 40
    data["layout_detections"] = [
        {
            "class_name": "Formula",
            "canonical_class": "FORMULA",
            "bbox": [0, 0, w, h],
            "confidence": 1.0,
            "source": "dataset_documentation",
            "source_label": "rendered_latex",
        }
    ]
    data["layout_source"] = "dataset_documentation"
    data["layout_confidence"] = 1.0
    data["layout_detection_count"] = 1

    # CAPTURE METHOD
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 1.0
    data["domain_detection_method"] = "dataset_documentation"
    data["domain_content_type"] = "mathematical_formula"

    # LANGUAGE / SCRIPT
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Latn")

    # CONTENT FLAGS
    data["has_table"] = False
    data["has_formula"] = True  # Every image IS a formula
    data["has_code"] = False
    data["has_signature"] = False
    data["has_figure"] = False
    data["has_handwriting"] = False  # Rendered, not handwritten
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 1.0
    data["handwriting_present"] = False

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT
    data["split"] = sample.get("source", {}).get("split", "unknown")

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "formula"

    # IMAGE PROPERTIES
    original_file = sample.get("original_file", {})
    data["image_properties_color_mode"] = derive_color_mode(original_file)

    # TEXT CONTENT - LaTeX source is the text content
    # Check if original_labels has LaTeX formula text
    original_labels = sample.get("original_labels", {})
    raw_labels = original_labels.get("raw_labels", {})
    latex_src = raw_labels.get("formula", "") or raw_labels.get("latex", "")

    if latex_src:
        data["text_has_content"] = True
        data["text_content_confidence"] = 1.0
        data["text_content_source"] = "ground_truth"
        data["text_statistics"] = {
            "char_count": len(latex_src),
            "word_count": len(latex_src.split()),
            "line_count": 1,
            "has_content": True,
        }
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

    # TEXT DIRECTION
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # RESOLUTION
    for field in ("resolution_category", "resolution_pixels"):
        if field in v1_data:
            data[field] = v1_data[field]

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)
    return data


def run_integration(
    metadata: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "has_formula_count": 0,
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample)
        stats["integrated"] += 1

        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1
        if integrated_data.get("has_formula"):
            stats["has_formula_count"] += 1
        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_im2latex_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset documentation overrides. "
                    "KI-008. Schema v2.1 -> v2.3.0."
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
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


def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary."""
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
    print(f"Has formula:          {stats['has_formula_count']}")
    print("=" * 60)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"Integrate enrichment sources into {DATASET_NAME} metadata.",
    )
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)

    start = time.monotonic()
    stats = run_integration(metadata, dry_run=args.dry_run)
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        metadata["schema_version"] = TARGET_SCHEMA_VERSION
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
