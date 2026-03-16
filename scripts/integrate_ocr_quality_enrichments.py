#!/usr/bin/env python3
"""Integrate all enrichment sources into ocr-quality Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

ocr-quality specifics:
  - 1K images for OCR quality assessment
  - Multi-lingual content (various scripts and languages)
  - Has 3 enrichment sources: BASE + LLM + LANG
  - capture_method: mixed (use LLM detection)
  - domain: mixed (use LLM detection)
  - No Docling layout available

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_ocr_quality_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "ocr-quality"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/quality/ocr_quality.py"
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
DATASET_NAME = "ocr-quality"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "ocr_quality_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "ocr-quality_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "ocr_quality_language_enrichment.json"
)

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# No Docling layout
APPLY_KI_001_LAYOUT_CASING = False

# Content flags: use LLM detection (mixed content)
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# Mixed capture methods -- rely on LLM detection
KNOWN_CAPTURE_METHOD: str | None = None

# ===================================================================
# Content flag class mappings
# ===================================================================


# ===================================================================
# Data loaders
# ===================================================================
def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for an ocr-quality sample.

    Priority chain (KI-009: LLM > language_enrichment > docs):
      1. Parser GT (confidence 0.95)
      2. LLM vision (confidence 0.65)
      3. Language enrichment / OpenLID (confidence 0.70)
      4. Fallback: undetermined

    Args:
        sample: The full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        lang_enrichment: Language enrichment record (or None).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
    # Source 1: Parser GT
    original_labels = sample.get("original_labels", {})
    parser_lang = original_labels.get("language_code", "")
    if parser_lang and parser_lang not in ("", "und"):
        parser_script = original_labels.get("iso15924_script_code", "") or "Zyyy"
        return (parser_lang, parser_script, 0.95, "parser_gt")

    # Source 2: LLM vision
    if llm:
        llm_lang = llm.get("iso639_language")
        llm_script = llm.get("iso15924_script")
        if llm_lang and llm_lang != "und":
            return (llm_lang, llm_script or "Zyyy", 0.65, "llm_vision")

    # Source 3: Language enrichment / OpenLID
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        le_script = lang_enrichment.get("script")
        le_conf = lang_enrichment.get("confidence", 0.5)
        if le_lang and le_lang != "und":
            return (le_lang, le_script or "Zyyy", min(le_conf, 0.70), "openlid_v2")

    # Fallback: multilingual dataset, no single default
    return ("und", "Zyyy", 0.1, "none")


def resolve_capture_method(
    llm: dict[str, Any] | None,
) -> tuple[str, float, str]:
    """Resolve capture method from LLM or fallback.

    ocr-quality has mixed capture methods -- rely on LLM.

    Args:
        llm: LLM enrichment record (or None).

    Returns:
        Tuple of (capture_method, confidence, detection_method).
    """
    if llm:
        method = llm.get("capture_method", "unknown")
        conf = llm.get("capture_confidence", 0.5)
        if method and method != "unknown":
            return (method, conf, "llm_vision")

    return ("unknown", 0.3, "none")


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        llm_index: LLM enrichment index (stem -> record).
        lang_index: Language enrichment index (stem -> record).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS (keep v1 layout)
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    data["layout_detections"] = v1_layout
    data["layout_source"] = v1_data.get("layout_source", "none")
    data["layout_confidence"] = v1_data.get("layout_confidence", 0.0)
    data["layout_detection_count"] = len(v1_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (from LLM, mixed dataset)
    # -------------------------------------------------------------------
    capture, capture_conf, capture_method_src = resolve_capture_method(llm)
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # -------------------------------------------------------------------
    # DOMAIN (from LLM enrichment)
    # -------------------------------------------------------------------
    if llm:
        data["domain_level1"] = llm.get("domain_level1", "UNK")
        data["domain_confidence"] = llm.get("domain_confidence", 0.5)
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = v1_data.get("domain_level1", "UNK")
        data["domain_confidence"] = v1_data.get("domain_confidence", 0.3)
        data["domain_detection_method"] = v1_data.get("domain_detection_method", "none")

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT (KI-009)
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # SCRIPT FAMILY (KI-008: re-derive)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # CONTENT FLAGS (from LLM if available)
    # -------------------------------------------------------------------
    if llm:
        data["has_table"] = bool(llm.get("has_table", False))
        data["has_figure"] = bool(llm.get("has_figure", False))
        data["has_formula"] = bool(llm.get("has_formula", False))
        data["has_handwriting"] = bool(llm.get("has_handwriting", False))
        data["has_signature"] = bool(llm.get("has_signature", False))
    else:
        data["has_table"] = False
        data["has_figure"] = False
        data["has_formula"] = False
        data["has_handwriting"] = False
        data["has_signature"] = False

    data["has_code"] = False
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "llm_vision"
    data["content_flags_confidence"] = 0.65 if llm else 0.3
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # ORIENTATION (from LLM or default upright)
    # -------------------------------------------------------------------
    if llm and llm.get("orientation") is not None:
        data["orientation_class"] = llm.get("orientation", 0)
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "llm_vision"
    else:
        data["orientation_class"] = 0
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "default_upright"

    # -------------------------------------------------------------------
    # SPLIT
    # -------------------------------------------------------------------
    data["split"] = sample.get("source", {}).get("split", "unknown")
    if data["split"] == "unknown":
        data["split"] = "train"

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type if content_type else "unknown"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "unknown"
        )

    data["text_scope"] = v1_data.get("text_scope", "printed")

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # -------------------------------------------------------------------
    # RESOLUTION QUALITY (preserve v1)
    # -------------------------------------------------------------------
    for field in (
        "resolution_category",
        "resolution_pixels",
        "resolution_quality_score",
        "resolution_quality_bucket",
        "resolution_char_height_px",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # TEXT CONTENT (no text labels available)
    # -------------------------------------------------------------------
    data["text_has_content"] = False
    data["text_content"] = ""
    data["text_content_confidence"] = 0.0
    data["text_content_source"] = "none"
    data["text_statistics"] = compute_text_statistics("")

    # -------------------------------------------------------------------
    # ADDITIONAL DERIVED FIELDS
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        llm_index: LLM enrichment index.
        lang_index: Language enrichment index.
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "capture_method_dist": Counter(),
        "content_type_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
    }

    now = datetime.now(timezone.utc).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem

        integrated_data = integrate_sample(sample, llm_index, lang_index)

        stats["integrated"] += 1
        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["lang_method_dist"][
            integrated_data.get("text_scope_detection_method", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
        ] += 1
        stats["content_type_dist"][
            integrated_data.get("text_scope_content_type", "unknown")
        ] += 1

        if integrated_data.get("has_table"):
            stats["has_table_count"] += 1
        if integrated_data.get("has_formula"):
            stats["has_formula_count"] += 1
        if integrated_data.get("has_handwriting"):
            stats["has_handwriting_count"] += 1
        if integrated_data.get("has_figure"):
            stats["has_figure_count"] += 1

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": (
                    f"integrate_{DATASET_NAME.replace('-', '_')}_enrichments.py"
                ),
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "LLM vision + language enrichment"
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


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary.

    Args:
        stats: Stats dict returned by run_integration().
        total_samples: Total number of samples in the metadata.
    """
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print()

    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {domain:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Language distribution (top 15):")
    for lang, count in stats["lang_dist"].most_common(15):
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print("=" * 60)


# ===================================================================
# CLI
# ===================================================================
def main() -> int:
    """Entry point with argument parsing.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to dataset metadata JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--llm-enrichment",
        type=Path,
        default=LLM_ENRICHMENT_PATH,
        help="Path to LLM enrichment JSON",
    )
    parser.add_argument(
        "--language-enrichment",
        type=Path,
        default=LANGUAGE_ENRICHMENT_PATH,
        help="Path to language enrichment JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)

    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(metadata["samples"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
