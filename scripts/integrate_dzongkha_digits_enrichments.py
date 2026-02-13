#!/usr/bin/env python3
"""Integrate all enrichment sources into dzongkha-digits Layer 2 metadata.

Simplified integration for a small, homogeneous dataset (62 samples).
All samples are single handwritten Tibetan digit images (class 0) captured
via Google Jamboard.

Available enrichment sources:
  1. Docling layout (all "Picture"): layout_detections, content_flags derivation
  2. Empty OCR text (Docling cannot read handwritten Tibetan digits)

Not available (hardcoded from dataset documentation instead):
  - No LLM enrichment
  - No language enrichment (OpenLID)
  - No skew/orientation labels
  - No resolution quality labels
  - No VLM enrichment
  - No train GT file

Also applies:
  - Layout label PascalCase conversion (KI-001): docling lowercase -> DocLayNet
  - Script family derivation (KI-008): Tibt -> "tibetan"
  - Hardcoded known values: capture_method=camera_smartphone, language=dz,
    script=Tibt, has_handwriting=True (all samples)
  - v2.3.0 fields: text_direction=ltr, text_directions_present=[ltr]
  - Reliability summary recomputation

Creates a new enrichment version (v2) in each sample's enrichments.versions[].

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_dzongkha_digits_enrichments.py --dry-run
"""

from __future__ import annotations

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
# DATASET CONFIGURATION - Customize these for your dataset
# ===================================================================
# The canonical short name used in filenames, paths, and metadata.
# Must match the name in DATASET_NAMING_STANDARD.md.
DATASET_NAME = "dzongkha-digits"

# False: camera-captured handwriting dataset (Google Jamboard).
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "dzongkha-digits_metadata.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"

# The enrichment version number written into each sample.
ENRICHMENT_VERSION_NUMBER = 2


# ===================================================================
# KNOWN ISSUE MITIGATIONS
#
# Toggle each based on applicability.
# See scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json for
# full descriptions, evidence, and remediation guidance.
#
# Pre-flight checklist:
#   [x] Read CROSS_DATASET_KNOWN_ISSUES.json
#   [x] Determine capture_method from dataset documentation
#   [x] Run standardize_layout_labels.py BEFORE this script (KI-001)
#   [x] No VLM inspection needed (all Picture, no ambiguous flags)
#   [x] Document VLM corrections - N/A (no corrections needed)
# ===================================================================

# --- KI-001: Docling layout label casing (CRITICAL) -----------------
# Set True if dataset has Docling layout extraction (lowercase labels).
# If False, layout labels are assumed already in PascalCase.
APPLY_KI_001_LAYOUT_CASING = True

# Full Docling lowercase -> DocLayNet PascalCase mapping.
# Covers core 11 DocLayNet classes plus Docling extensions.
DOCLING_TO_DOCLAYNET: dict[str, str] = {
    "text": "Text",
    "list_item": "List-Item",
    "section_header": "Section-Header",
    "table": "Table",
    "picture": "Picture",
    "formula": "Formula",
    "caption": "Caption",
    "footnote": "Footnote",
    "page_footer": "Page-Footer",
    "page_header": "Page-Header",
    "title": "Title",
    "code": "Code",
    "checkbox_selected": "Checkbox-Selected",
    "checkbox_unselected": "Checkbox-Unselected",
}

# --- KI-002: Table detection multi-column FP (HIGH) -----------------
# No tables in single digit images.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-003: Picture detection dense text FP (MEDIUM) ---------------
# All samples are correctly classified as "Picture" by Docling.
# Single handwritten digit images ARE pictures.
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-004: LLM handwriting on synthetic (HIGH) --------------------
# N/A for dzongkha-digits (IS_SYNTHETIC_DATASET=False).
# ALL samples are handwritten by dataset definition.
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-005: LLM cannot detect synthetic capture (HIGH) -------------
# Known capture method from documentation: Google Jamboard digitized.
KNOWN_CAPTURE_METHOD: str | None = "camera_smartphone"

# --- KI-006: LLM formula semantic confusion (MEDIUM) ----------------
# No formulas in single digit images.
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# ===================================================================
# Content flag class mappings (canonical layout -> content flags)
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}


# ===================================================================
# Data loaders
#
# Only load_metadata is needed for this dataset. All other enrichment
# sources are absent -- values are hardcoded from documentation.
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to the dataset's *_metadata.json file.

    Returns:
        Full metadata dict with "samples" list.

    Raises:
        FileNotFoundError: If the metadata file does not exist.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes.

    Scans all layout detections and checks canonical_class against
    known class sets for table, formula, figure, and code.

    Args:
        detections: List of layout detection dicts, each containing
            at minimum a "canonical_class" key.

    Returns:
        Dict with boolean flags: has_table, has_formula, has_figure,
        has_code.
    """
    canonical_classes = {
        d.get("canonical_class", "").upper()
        for d in detections
        if d.get("canonical_class")
    }
    return {
        "has_table": bool(canonical_classes & TABLE_CLASSES),
        "has_formula": bool(canonical_classes & FORMULA_CLASSES),
        "has_figure": bool(canonical_classes & FIGURE_CLASSES),
        "has_code": bool(canonical_classes & CODE_CLASSES),
    }


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Assesses five field groups (capture, domain, language, layout,
    content_flags) and produces a reliability tier for each based on
    confidence thresholds:
      >= 0.9 -> hard_label
      >= 0.7 -> soft_label
      >= 0.5 -> active_learning
      <  0.5 -> unreliable

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Dict with min_confidence, min_confidence_field,
        min_confidence_category, field counts, field_summary list,
        and computed_at timestamp.
    """
    fields: list[dict[str, Any]] = []

    field_defs = [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
    ]

    for field_name, conf_key in field_defs:
        confidence = data.get(conf_key, 0.0)
        if confidence is None:
            confidence = 0.0

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


def standardize_class_name(class_name: str) -> str:
    """Convert layout extractor class_name to DocLayNet PascalCase.

    Uses DOCLING_TO_DOCLAYNET mapping by default (KI-001).
    Passes through unmapped names unchanged.

    Args:
        class_name: Raw class name from layout extractor output.

    Returns:
        Standardized PascalCase class name.
    """
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def resolve_language() -> tuple[str, str, float, str]:
    """Resolve language/script for dzongkha-digits.

    All samples are monolingual Dzongkha (Tibetan script).
    Known from dataset documentation with full confidence.

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
    return ("dz", "Tibt", 1.0, "dataset_documentation")


def resolve_capture_method() -> tuple[str, float, str]:
    """Resolve capture method for dzongkha-digits.

    All samples are digitized via Google Jamboard (camera/smartphone).
    Known from dataset documentation with full confidence.

    Returns:
        Tuple of (capture_method, confidence, detection_method).
    """
    return ("camera_smartphone", 1.0, "dataset_documentation")


# ===================================================================
# Per-sample integration
#
# Simplified for dzongkha-digits: no external enrichment lookups,
# all values derived from dataset documentation and Docling layout.
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    All values are hardcoded from dataset documentation or derived
    from the existing Docling layout detections. No external enrichment
    sources are needed for this dataset.

    Args:
        sample: A single sample from the L2 metadata "samples" list.

    Returns:
        New enrichment data dict with all fields populated.
    """
    # Get existing enrichment data (latest version) for fallback
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # LAYOUT DETECTIONS (with KI-001 casing fix)
    #
    # Standardizes class_name from layout extractor output to DocLayNet
    # PascalCase. Preserves original label in source_label field.
    # All 62 samples have Docling layout: all classified as "picture".
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    standardized_layout: list[dict[str, Any]] = []
    for det in v1_layout:
        new_det = dict(det)
        original_class = det.get("class_name", "")
        new_det["class_name"] = standardize_class_name(original_class)
        # Preserve original label for traceability
        if not new_det.get("source_label"):
            new_det["source_label"] = original_class
        standardized_layout.append(new_det)

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (from dataset documentation)
    #
    # Google Jamboard digitized -> camera_smartphone.
    # -------------------------------------------------------------------
    capture, capture_conf, capture_method_src = resolve_capture_method()
    data["capture_method"] = capture
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = capture_method_src

    # -------------------------------------------------------------------
    # DOMAIN (from dataset documentation)
    #
    # dzongkha-digits is educational handwriting practice data.
    # -------------------------------------------------------------------
    data["domain_level1"] = "EDU"
    data["domain_confidence"] = 0.90
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT (from dataset documentation)
    #
    # Monolingual Dzongkha (dz) / Tibetan script (Tibt).
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language()
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # SCRIPT FAMILY (derived from iso15924_script)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # CONTENT FLAGS (with KI-002, KI-003, KI-004, KI-006 overrides)
    #
    # All 62 samples are single digit images classified as "Picture"
    # by Docling. No tables, formulas, code, or signatures.
    # has_figure is False because these are isolated digit samples,
    # not document figures (VLM true positives set is empty).
    # -------------------------------------------------------------------
    flags = derive_content_flags(standardized_layout)

    # KI-002: has_table -- no tables in digit images
    data["has_table"] = False

    # KI-003: has_figure -- no VLM-confirmed figures
    data["has_figure"] = False

    # KI-006: has_formula -- no formulas in digit images
    data["has_formula"] = False

    # KI-004: has_handwriting
    # Ground truth: ALL samples are handwritten (dataset documentation).
    data["has_handwriting"] = True

    data["has_signature"] = False
    data["has_code"] = flags["has_code"]

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "dataset_documentation+docling_gpu"
    # High confidence: hardcoded from dataset documentation
    data["content_flags_confidence"] = 0.95

    # Alias used by prescreening checks
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # ORIENTATION (default - no MobileNetV4 labels available)
    #
    # Assume upright (0 degrees) with low confidence pending VLM
    # verification.
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.5
    data["orientation_detection_method"] = "default_upright"

    # -------------------------------------------------------------------
    # SPLIT (hardcoded - all samples are train)
    #
    # dzongkha-digits has no official splits. All 62 samples are in
    # the "train" partition. The sample["source"] dict does NOT have
    # a "split" field for this dataset.
    # -------------------------------------------------------------------
    data["split"] = "train"

    # -------------------------------------------------------------------
    # TEXT SCOPE (single handwritten digit images)
    # -------------------------------------------------------------------
    data["text_scope_content_type"] = "handwritten"
    data["text_scope"] = "character"

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    # Camera-captured handwriting via Google Jamboard
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # -------------------------------------------------------------------
    # TEXT CONTENT (empty - OCR cannot read handwritten Tibetan digits)
    # -------------------------------------------------------------------
    data["text_has_content"] = False
    data["text_content"] = ""
    data["text_content_confidence"] = 0.0
    data["text_content_source"] = "none"
    data["text_statistics"] = {
        "char_count": 0,
        "word_count": 0,
        "line_count": 0,
        "has_content": False,
    }

    # -------------------------------------------------------------------
    # v2.3.0 FIELDS
    # -------------------------------------------------------------------
    # Tibetan/Dzongkha is written left-to-right
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]
    # Not synthetic - no rendered character height or output size
    data["character_height_rendered_px"] = None
    data["output_size_px"] = None

    # -------------------------------------------------------------------
    # SCHEMA VERSION
    # -------------------------------------------------------------------
    data["schema_version"] = "2.3.0"

    # -------------------------------------------------------------------
    # ADDITIONAL DERIVED FIELDS
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

    # Handwriting assessment from dataset documentation
    data["handwriting_assessment"] = {
        "presence": "DOMINANT",
        "legibility": "GOOD",
        "content_type": "numeric",
        "detection_method": "dataset_documentation",
        "confidence": 1.0,
    }

    # -------------------------------------------------------------------
    # RELIABILITY SUMMARY (must be last -- uses confidence fields above)
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def run_integration(
    metadata: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Iterates over every sample in metadata, calls integrate_sample(),
    tracks statistics, and (unless dry_run) writes a new enrichment
    version into each sample.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
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
        "has_text_content_count": 0,
    }

    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1

        integrated_data = integrate_sample(sample)

        # ----- Track statistics -----
        stats["integrated"] += 1

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
        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1

        # ----- Write enrichment version -----
        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": (f"integrate_{DATASET_NAME}_enrichments.py"),
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "dataset documentation + Docling layout + "
                    "KI-001 casing fix (v2.3.0)"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            # Replace existing version if present, otherwise append
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
    """Print integration summary with distributions.

    Shows match rates, domain/split/language/capture distributions,
    and content flag counts.

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
    print()

    print("Domain distribution:")
    for domain, count in stats["domain_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {domain:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"  {split:20s}: {count:5d}")
    print()

    print("Language distribution:")
    for lang, count in stats["lang_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:5d}")
    print()

    print("Capture method distribution:")
    for cm, count in stats["capture_method_dist"].most_common():
        print(f"  {cm:20s}: {count:5d}")
    print()

    print("Content type:")
    for ct, count in stats["content_type_dist"].most_common():
        print(f"  {ct:30s}: {count:5d}")
    print()

    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print(f"  has_text_content:   {stats['has_text_content_count']}")
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
        description=(f"Integrate all enrichment sources into {DATASET_NAME} metadata."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to dataset metadata JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    # ----- Load metadata -----
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)

    # ----- Run integration -----
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        dry_run=args.dry_run,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info("Integration completed in %.2f seconds", elapsed)

    # ----- Write output -----
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
