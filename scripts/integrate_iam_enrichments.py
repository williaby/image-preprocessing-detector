#!/usr/bin/env python3
"""Integrate all enrichment sources into iam Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

iam specifics:
  - IAM Handwriting Database (~130K samples)
  - Handwritten English text lines, words, sentences
  - LLM enrichment: available (iam_llm_enrichment.json)
  - Language enrichment: available (iam_language_enrichment.json)
  - No Docling layout extraction
  - NOTE: iam_metadata.json does NOT exist yet - must be created first
  - capture_method: scanner_flatbed (scanned handwriting forms)
  - domain_level1: EDU (English handwriting samples)
  - has_handwriting: True for ALL samples
  - Language: en/Latn (English)
  - Schema upgrade: v2.1 -> v2.3.0

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_iam_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "iam"
__l4_workstream__ = "WS3"
__l4_parser__ = "src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py"


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
    load_llm_enrichment,
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
DATASET_NAME = "iam"
IS_SYNTHETIC_DATASET = False

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "iam_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "iam_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "iam_language_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2
TARGET_SCHEMA_VERSION = "2.3.0"

KNOWN_CAPTURE_METHOD = "scanner_flatbed"


def derive_color_mode(original_file: dict[str, Any]) -> str:
    """Derive color mode from image channel count."""
    channels = original_file.get("channels", 3)
    if channels == 1:
        return "grayscale"
    if channels == 4:
        return "color_alpha"
    return "color"


def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample."""
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    data: dict[str, Any] = {}

    # LAYOUT - handwriting line images, single text region
    res = v1_data.get("resolution_pixels", [300, 50])
    w = res[0] if isinstance(res, list) and len(res) >= 2 else 300
    h = res[1] if isinstance(res, list) and len(res) >= 2 else 50
    data["layout_detections"] = [
        {
            "class_name": "Text",
            "canonical_class": "TEXT",
            "bbox": [0, 0, w, h],
            "confidence": 1.0,
            "source": "dataset_documentation",
            "source_label": "handwritten_text_line",
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
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "EDU")
        data["domain_confidence"] = llm.get("domain_confidence", 0.8)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "handwritten_text")
    else:
        data["domain_level1"] = "EDU"
        data["domain_confidence"] = 0.9
        data["domain_detection_method"] = "dataset_documentation"
        data["domain_content_type"] = "handwritten_text"

    # LANGUAGE / SCRIPT
    # IAM is English handwriting, use dataset documentation
    data["iso639_language"] = "en"
    data["iso15924_script"] = "Latn"
    data["language_confidence"] = 1.0
    data["text_scope_detection_method"] = "dataset_documentation"
    data["script_family"] = _get_script_family("Latn")

    # CONTENT FLAGS
    data["has_table"] = False
    data["has_formula"] = False
    data["has_code"] = False
    data["has_signature"] = False
    data["has_figure"] = False
    data["has_handwriting"] = True
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "llm_vision+dataset_documentation"
    data["content_flags_confidence"] = 1.0
    data["handwriting_present"] = True

    # ORIENTATION
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # SPLIT
    data["split"] = sample.get("source", {}).get("split", "unknown")

    # TEXT SCOPE
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "line"

    # IMAGE PROPERTIES
    original_file = sample.get("original_file", {})
    data["image_properties_color_mode"] = derive_color_mode(original_file)

    # TEXT CONTENT - IAM has ground truth transcriptions
    original_labels = sample.get("original_labels", {})
    transcription = original_labels.get("transcription", "")

    if transcription:
        data["text_has_content"] = True
        data["text_content_confidence"] = 1.0
        data["text_content_source"] = "ground_truth"
        data["text_statistics"] = compute_text_statistics(transcription)
    else:
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

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
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "has_handwriting_count": 0,
    }
    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename_stem = Path(sample["source"]["original_filename"]).stem

        integrated_data = integrate_sample(sample, llm_index, lang_index)

        stats["integrated"] += 1
        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1
        if integrated_data.get("has_handwriting"):
            stats["has_handwriting_count"] += 1
        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_iam_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + language enrichment + "
                    "dataset documentation. KI-008. Schema v2.1 -> v2.3.0."
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
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
    print(f"Has handwriting:      {stats['has_handwriting_count']}")
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
        log.error(
            "IAM metadata file must be created first via annotate_base_metadata.py"
        )
        return 1

    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(LLM_ENRICHMENT_PATH)
    lang_index = load_language_enrichment(LANGUAGE_ENRICHMENT_PATH)

    start = time.monotonic()
    stats = run_integration(metadata, llm_index, lang_index, dry_run=args.dry_run)
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
