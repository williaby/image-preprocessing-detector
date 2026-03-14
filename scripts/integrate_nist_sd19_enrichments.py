#!/usr/bin/env python3
"""Integrate all enrichment sources into nist-sd19 Layer 2 metadata.

TEMPLATE VERSION: 1.1.0

nist-sd19 specifics:
  - 3,669 scanned handwritten digit/character images (NIST SD19).
  - GOV domain (census forms), English, scanner_flatbed
  - Language enrichment available, no Docling layout
  - 100% handwriting

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_nist_sd19_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "nist-sd19"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd19.py"
)


import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

from l2_integration_utils import (
    compute_reliability_summary,
    compute_text_statistics,
    load_language_enrichment,
    load_metadata,
    DOCLING_TO_DOCLAYNET,
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
DATASET_NAME = "nist-sd19"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "nist_sd19_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "nist-sd19_language_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================
APPLY_KI_001_LAYOUT_CASING = False


KNOWN_CAPTURE_METHOD: str | None = "scanner_flatbed"


# ===================================================================
# Content flag class mappings
# ===================================================================


# ===================================================================
# Data loaders
# ===================================================================
def standardize_class_name(class_name: str) -> str:
    """Convert layout class_name to DocLayNet PascalCase."""
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def integrate_sample(
    sample: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    lang_enrichment = lang_index.get(filename_stem)

    data: dict[str, Any] = {}

    # SPLIT
    data["split"] = sample.get("source", {}).get("split", "train")
    if data["split"] == "unknown":
        data["split"] = "train"

    # CAPTURE METHOD
    data["capture_method"] = "scanner_flatbed"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    data["domain_level1"] = "GOV"
    data["domain_confidence"] = 0.95
    data["domain_detection_method"] = "dataset_documentation"

    # LANGUAGE / SCRIPT
    if lang_enrichment:
        le_lang = lang_enrichment.get("language", "en")
        le_script = lang_enrichment.get("script", "Latn")
        le_conf = lang_enrichment.get("confidence", 0.70)
        if le_lang and le_lang != "und":
            data["iso639_language"] = le_lang
            data["iso15924_script"] = le_script or "Latn"
            data["language_confidence"] = min(le_conf, 0.70)
            data["text_scope_detection_method"] = "openlid_v2"
        else:
            data["iso639_language"] = "en"
            data["iso15924_script"] = "Latn"
            data["language_confidence"] = 0.95
            data["text_scope_detection_method"] = "dataset_documentation"
    else:
        data["iso639_language"] = "en"
        data["iso15924_script"] = "Latn"
        data["language_confidence"] = 0.95
        data["text_scope_detection_method"] = "dataset_documentation"

    # KI-008: script_family
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # v2.3.0: TEXT DIRECTION
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # LAYOUT DETECTIONS
    v1_layout = v1_data.get("layout_detections", [])
    if isinstance(v1_layout, list) and v1_layout:
        data["layout_detections"] = v1_layout
    else:
        data["layout_detections"] = []
    data["layout_source"] = v1_data.get("layout_source", "none")
    data["layout_confidence"] = 0.5
    data["layout_detection_count"] = len(data["layout_detections"])

    # CONTENT FLAGS
    data["has_table"] = v1_data.get("has_table", False)
    data["has_formula"] = v1_data.get("has_formula", False)
    data["has_figure"] = v1_data.get("has_figure", False)
    data["has_code"] = False
    data["has_handwriting"] = True
    data["has_signature"] = v1_data.get("has_signature", False)
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "base_metadata"
    data["content_flags_confidence"] = 0.70
    data["handwriting_present"] = data["has_handwriting"]

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.7
    data["orientation_detection_method"] = "dataset_documentation"

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "page"

    # IMAGE PROPERTIES
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "grayscale"
    )

    # RESOLUTION (preserve v1)
    for field in ("resolution_category", "resolution_pixels", "resolution_dpi"):
        if field in v1_data:
            data[field] = v1_data[field]

    # TEXT CONTENT
    data["text_has_content"] = False
    data["text_content"] = ""
    data["text_content_confidence"] = 0.0
    data["text_content_source"] = "none"
    data["text_statistics"] = compute_text_statistics("")

    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)
    return data


# ===================================================================
# Integration runner
# ===================================================================
def run_integration(
    metadata: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "lang_matched": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "capture_method_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }
    now = datetime.now(timezone.utc).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        integrated_data = integrate_sample(sample, lang_index)
        stats["integrated"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
        ] += 1
        for flag in ("has_table", "has_formula", "has_handwriting", "has_figure"):
            if integrated_data.get(flag):
                stats[f"{flag}_count"] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": f"Integrated enrichment {ENRICHMENT_VERSION_TAG}",
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
    safe_total = max(total_samples, 1)
    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total: {stats['total']}, Integrated: {stats['integrated']}")
    print(f"Domain: {dict(stats['domain_dist'])}")
    print(
        f"has_table: {stats['has_table_count']}, has_handwriting: {stats['has_handwriting_count']}"
    )
    print("=" * 60)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"Integrate enrichments into {DATASET_NAME} metadata.",
    )
    parser.add_argument("--metadata", type=Path, default=METADATA_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    lang_index = load_language_enrichment(args.language_enrichment)

    start = time.monotonic()
    stats = run_integration(metadata, lang_index, dry_run=args.dry_run)
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
