#!/usr/bin/env python3
"""Integrate all enrichment sources into fintabnet Layer 2 metadata.

TEMPLATE VERSION: 1.1.0

fintabnet specifics:
  - 97,475 born-digital financial table images from SEC filings
  - BASE + LANG + DOCL enrichment sources
  - Docling layout uses table-specific categories (table_row, table_cell, etc.)
    NOT standard DocLayNet classes -- these need mapping
  - FIN domain (100% financial SEC filings)
  - 100% English, Latin script
  - All images contain tables (has_table=True by definition)
  - No GT text available; text_has_content remains False
  - Language enrichment available

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_fintabnet_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "fintabnet"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/layout/fintabnet.py"
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

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

from l2_integration_utils import (
    compute_reliability_summary,
    compute_text_statistics,
    load_language_enrichment,
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
DATASET_NAME = "fintabnet"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "fintabnet_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "fintabnet_language_enrichment.json"
DOCLING_LAYOUT_PATH = REGISTRY_DIR / "extracted" / "fintabnet" / "layout_batch_0.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================
# Docling layout uses table-internal categories, not DocLayNet
# We treat the entire image as a Table detection instead
APPLY_KI_001_LAYOUT_CASING = False
KNOWN_CAPTURE_METHOD: str | None = "born_digital"


# ===================================================================
# Data loaders
# ===================================================================
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
    data["split"] = "train"  # FinTabNet is single-split for detection

    # CAPTURE METHOD
    data["capture_method"] = "born_digital"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # DOMAIN
    data["domain_level1"] = "FIN"
    data["domain_confidence"] = 1.0
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

    # LAYOUT DETECTIONS: Docling extracted table-internal layout but not
    # standard DocLayNet. Use documentation-based Table detection.
    data["layout_detections"] = [
        {
            "class_name": "Table",
            "bbox": [0, 0, 1, 1],
            "confidence": 1.0,
            "source": "dataset_documentation",
            "source_label": "table",
        }
    ]
    data["layout_source"] = "dataset_documentation"
    data["layout_confidence"] = 1.0
    data["layout_detection_count"] = 1

    # CONTENT FLAGS
    data["has_table"] = True
    data["has_formula"] = False
    data["has_figure"] = False
    data["has_code"] = False
    data["has_handwriting"] = False
    data["has_signature"] = False
    data["content_flags_tier"] = "tier_0_exact"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 1.0
    data["handwriting_present"] = False

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # TEXT SCOPE
    data["text_scope_content_type"] = "printed"
    data["text_scope"] = "page"

    # IMAGE PROPERTIES
    data["image_properties_color_mode"] = "color"

    # RESOLUTION (preserve v1)
    for field in ("resolution_category", "resolution_pixels"):
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
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename_stem = Path(sample["source"]["original_filename"]).stem
        integrated_data = integrate_sample(sample, lang_index)
        stats["integrated"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
        ] += 1
        if integrated_data.get("has_table"):
            stats["has_table_count"] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "dataset_documentation",
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
    print(f"Lang matched: {stats['lang_matched']}")
    print(f"has_table: {stats['has_table_count']}")
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
