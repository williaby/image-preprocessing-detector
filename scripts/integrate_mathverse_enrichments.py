#!/usr/bin/env python3
"""Integrate all enrichment sources into mathverse Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

mathverse specifics:
  - MathVerse: Mathematical Visual Reasoning dataset (6,940 images)
  - Math problem images with diagrams (born-digital)
  - Language enrichment: empty (0 records)
  - No LLM enrichment, no Docling layout
  - v1 data uses NESTED structure (capture_method is a dict, not string!)
  - capture_method: born_digital (rendered)
  - domain_level1: EDU (mathematical education)
  - has_formula: True for ALL samples
  - has_handwriting: False (rendered)
  - has_figure: True (math diagrams/graphs)
  - Language: en/Latn
  - Schema upgrade: v2.1 -> v2.3.0

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_mathverse_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "mathverse"
__l4_workstream__ = "WS3"
__l4_parser__ = "src/image_preprocessing_detector/annotation/parsers/handwriting/maths_handwriting.py"


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

from l2_integration_utils import (
    compute_reliability_summary,
    load_metadata,
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
DATASET_NAME = "mathverse"
IS_SYNTHETIC_DATASET = False

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "mathverse_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "mathverse_language_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2
TARGET_SCHEMA_VERSION = "2.3.0"

KNOWN_CAPTURE_METHOD = "born_digital"


def derive_color_mode(original_file: dict[str, Any]) -> str:
    """Derive color mode from image channel count."""
    channels = original_file.get("channels", 3)
    if channels == 1:
        return "grayscale"
    if channels == 4:
        return "color_alpha"
    return "color"


def _extract_v1_flat(v1_data: dict[str, Any]) -> dict[str, Any]:
    """Extract flat fields from potentially nested v1 data.

    Mathverse v1 uses nested dicts (capture_method is {method, confidence, ...}).
    This extracts flat values for resolution preservation.
    """
    flat: dict[str, Any] = {}
    # Resolution from nested dict
    resolution = v1_data.get("resolution", {})
    if isinstance(resolution, dict):
        if resolution.get("category"):
            flat["resolution_category"] = resolution["category"]
        if resolution.get("pixels"):
            flat["resolution_pixels"] = resolution["pixels"]
    else:
        # Already flat
        for key in ("resolution_category", "resolution_pixels"):
            if key in v1_data:
                flat[key] = v1_data[key]
    return flat


def integrate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    v1_flat = _extract_v1_flat(v1_data)
    data: dict[str, Any] = {}

    # LAYOUT - math problem with formula + figure
    res = v1_flat.get("resolution_pixels", [200, 200])
    w = res[0] if isinstance(res, list) and len(res) >= 2 else 200
    h = res[1] if isinstance(res, list) and len(res) >= 2 else 200
    data["layout_detections"] = [
        {
            "class_name": "Formula",
            "canonical_class": "FORMULA",
            "bbox": [0, 0, w, h],
            "confidence": 0.95,
            "source": "dataset_documentation",
            "source_label": "math_problem",
        },
        {
            "class_name": "Picture",
            "canonical_class": "PICTURE",
            "bbox": [0, 0, w, h],
            "confidence": 0.85,
            "source": "dataset_documentation",
            "source_label": "math_diagram",
        },
    ]
    data["layout_source"] = "dataset_documentation"
    data["layout_confidence"] = 0.9
    data["layout_detection_count"] = 2

    # CAPTURE METHOD
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 1.0
    data["domain_detection_method"] = "dataset_documentation"
    data["domain_content_type"] = "mathematical_problem"

    # LANGUAGE / SCRIPT
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Latn")

    # CONTENT FLAGS
    data["has_table"] = False
    data["has_formula"] = True
    data["has_code"] = False
    data["has_signature"] = False
    data["has_figure"] = True  # Math diagrams/graphs
    data["has_handwriting"] = False  # Rendered
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 1.0
    data["handwriting_present"] = False

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT
    src_split = sample.get("source", {}).get("split")
    data["split"] = src_split if src_split else "test"

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "paragraph"

    # IMAGE PROPERTIES
    original_file = sample.get("original_file", {})
    data["image_properties_color_mode"] = derive_color_mode(original_file)

    # TEXT CONTENT
    # Check for math problem text in original_labels
    original_labels = sample.get("original_labels", {})
    raw_labels = original_labels.get("raw_labels", {})
    problem_text = raw_labels.get("problem_text", "") or raw_labels.get("question", "")

    if problem_text:
        data["text_has_content"] = True
        data["text_content_confidence"] = 1.0
        data["text_content_source"] = "ground_truth"
        data["text_statistics"] = {
            "char_count": len(problem_text),
            "word_count": len(problem_text.split()),
            "line_count": len([l for l in problem_text.split("\n") if l.strip()]),
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
        if field in v1_flat:
            data[field] = v1_flat[field]

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
        "has_figure_count": 0,
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
        if integrated_data.get("has_figure"):
            stats["has_figure_count"] += 1
        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_mathverse_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset documentation overrides. Flattened nested v1. "
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
    print(f"Has figure:           {stats['has_figure_count']}")
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
