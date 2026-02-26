#!/usr/bin/env python3
"""Integrate all enrichment sources into midv2020 Layer 2 metadata.

TEMPLATE VERSION: 1.1.0
CREATED FROM: scripts/audit/integration_script_template.py

midv2020 specifics:
  - ID document images from 10 document types (5 countries), camera + flatbed
  - Camera mode: smartphone-captured (various conditions)
  - Flatbed mode: high-quality scanner capture
  - Capture method: camera_smartphone OR scanner (per image, from path)
  - Script: predominantly Cyrillic (Russian-issued documents)
  - Domain: GOV (government-issued identity documents)
  - Has 3 enrichment sources: BASE + LLM + LANG
  - No Docling layout (ID documents, not standard page layout)
  - License: CC BY-SA 2.5

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_midv2020_enrichments.py --dry-run
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "integrate-script"
__l4_dataset__ = "midv2020"
__l4_workstream__ = "WS3"
__l4_parser__ = (
    "src/image_preprocessing_detector/annotation/parsers/document/midv2020.py"
)


import argparse
import json
import logging
import re
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
DATASET_NAME = "midv2020"
IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "midv2020_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "midv2020_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "midv2020_language_enrichment.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# --- KI-001: Docling layout label casing ---------------------------
# No Docling layout for midv2020 (ID documents, not page-level)
APPLY_KI_001_LAYOUT_CASING = False

# --- Content flag overrides (ID documents only) --------------------
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_HANDWRITING_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# --- KI-005: Capture method resolved per-image from parser --------
# midv2020 has TWO capture methods (camera + flatbed) determined per image
KNOWN_CAPTURE_METHOD: str | None = None  # resolved per-sample

# ===================================================================
# Content flag class mappings
# ===================================================================
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# Countries with Cyrillic-primary documents in this dataset
_CYRILLIC_COUNTRIES: frozenset[str] = frozenset(
    {
        "RU",
        "RUS",
        "UA",
        "UKR",
        "BY",
        "BLR",
        "BG",
        "BGR",
        "RS",
        "SRB",
    }
)


# ===================================================================
# Data loaders
# ===================================================================


def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to the dataset's *_metadata.json file.

    Returns:
        Full metadata dict with "samples" list.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by filename stem.

    Args:
        path: Path to *_llm_enrichment.json.

    Returns:
        Dict mapping filename stem to enrichment record.
    """
    if not path.exists():
        log.warning("LLM enrichment not found: %s", path)
        return {}
    log.info("Loading LLM enrichment from %s", path)
    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[Path(image_id).stem] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by image_id stem.

    Args:
        path: Path to *_language_enrichment.json.

    Returns:
        Dict mapping filename stem to language enrichment record.
    """
    if not path.exists():
        log.warning("Language enrichment not found: %s", path)
        return {}
    log.info("Loading language enrichment from %s", path)
    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = json.load(fh)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[Path(image_id).stem] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text.

    Args:
        text: Raw transcription text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content.
    """
    if not text or not text.strip():
        return {"char_count": 0, "word_count": 0, "line_count": 0, "has_content": False}

    clean = text.strip()
    lines = [ln for ln in clean.split("\n") if ln.strip()]
    words = clean.split()
    cyrillic = len(re.findall(r"[\u0400-\u04ff]", clean))
    latin = len(re.findall(r"[a-zA-Z]+", clean))

    stats: dict[str, Any] = {
        "char_count": len(clean),
        "word_count": len(words),
        "line_count": len(lines),
        "has_content": True,
        "avg_line_length": round(sum(len(ln.strip()) for ln in lines) / len(lines), 1)
        if lines
        else 0.0,
    }
    if cyrillic:
        stats["cyrillic_char_count"] = cyrillic
    if latin:
        stats["latin_word_count"] = latin
    return stats


# ===================================================================
# Derivation helpers
# ===================================================================


def _resolve_capture_method(sample: dict[str, Any]) -> tuple[str, float]:
    """Resolve capture method from parser labels or filename path.

    Priority:
      1. Parser original_labels.capture_method (set from path structure)
      2. Path heuristic on original_filename

    Args:
        sample: Full sample dict from L2 metadata.

    Returns:
        Tuple of (capture_method, confidence).
    """
    # capture_method is nested inside original_labels.raw_labels
    raw = sample.get("original_labels", {}).get("raw_labels", {})
    method = raw.get("capture_method", "")
    # D01: map bare "scanner" to "scanner_flatbed" (v2.4.0 schema enum value)
    if method == "camera_smartphone":
        return "camera_smartphone", 1.0
    if method in ("scanner", "scanner_flatbed"):
        return "scanner_flatbed", 1.0

    # Fallback: original_path heuristic (photo/ → camera, scan*/ → scanner_flatbed)
    original_path = sample.get("source", {}).get("original_path", "").lower()
    if original_path.startswith("photo/"):
        return "camera_smartphone", 0.95
    if original_path.startswith(("scan_", "templates/")):
        return "scanner_flatbed", 0.95  # D01: was bare "scanner"

    # Last resort: filename path heuristic
    filename = sample.get("source", {}).get("original_filename", "").lower()
    if "flatbed" in filename or "scan" in filename:
        return "scanner_flatbed", 0.9  # D01: was bare "scanner"
    if "camera" in filename or "mobile" in filename:
        return "camera_smartphone", 0.9

    # Default for MIDV-2020: most images are camera-captured
    return "camera_smartphone", 0.5


def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a midv2020 sample.

    Priority chain:
      1. Parser GT (country code → language, confidence 0.90)
      2. LLM vision   (confidence 0.65)
      3. Language enrichment / OpenLID (confidence 0.70)
      4. Fallback: Russian (most documents are Russian-issued)

    Args:
        sample: Full sample dict from L2 metadata.
        llm: LLM enrichment record (or None).
        lang_enrichment: Language enrichment record (or None).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence, method).
    """
    # country_code and iso15924_script are nested inside original_labels.raw_labels
    raw = sample.get("original_labels", {}).get("raw_labels", {})

    # Source 1: ISO 15924 script from parser (direct from doc type lookup)
    parser_script = raw.get("iso15924_script", "")
    if parser_script == "Cyrl":
        lang_map_cyrl = {
            "RUS": "rus",
            "SRB": "srp",
        }
        country_code = raw.get("country_code", "").upper()
        lang = lang_map_cyrl.get(country_code, "rus")
        return (lang, "Cyrl", 0.95, "parser_script")
    if parser_script == "Grek":
        return ("ell", "Grek", 0.95, "parser_script")
    if parser_script == "Latn":
        # Use parser iso639_language directly
        lang = raw.get("iso639_language", "und")
        if lang and lang != "und":
            return (lang, "Latn", 0.95, "parser_script")

    country = (raw.get("country_code") or "").upper()
    if country in _CYRILLIC_COUNTRIES:
        lang_map = {
            "RU": "rus",
            "RUS": "rus",
            "UA": "ukr",
            "UKR": "ukr",
            "BY": "bel",
            "BLR": "bel",
            "BG": "bul",
            "BGR": "bul",
            "RS": "srp",
            "SRB": "srp",
        }
        return (lang_map.get(country, "rus"), "Cyrl", 0.90, "parser_country_code")

    # Source 2: LLM vision
    if llm:
        llm_lang = llm.get("iso639_language")
        llm_script = llm.get("iso15924_script")
        if llm_lang and llm_lang != "und":
            return (llm_lang, llm_script or "Zyyy", 0.65, "llm_vision")

    # Source 3: Language enrichment
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        le_script = lang_enrichment.get("script")
        le_conf = lang_enrichment.get("confidence", 0.5)
        if le_lang and le_lang != "und":
            return (le_lang, le_script or "Zyyy", min(le_conf, 0.70), "openlid_v2")

    # Source 4: Default (Russian — dominant in MIDV-2020)
    return ("rus", "Cyrl", 0.40, "dataset_default")


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Reliability summary dict.
    """
    field_defs = [
        ("capture_method", "capture_confidence"),
        ("domain", "domain_confidence"),
        ("language", "language_confidence"),
        ("layout_detections", "layout_confidence"),
        ("content_flags", "content_flags_confidence"),
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
    # LAYOUT DETECTIONS
    # midv2020: ID documents — no standard page layout.
    # Preserve parser-extracted document + field quads if present.
    # -------------------------------------------------------------------
    orig_labels = sample.get("original_labels", {})
    parser_detections = orig_labels.get("layout_detections", [])
    v1_layout = v1_data.get("layout_detections", parser_detections)
    data["layout_detections"] = v1_layout
    data["layout_source"] = v1_data.get("layout_source", "midv2020_annotation")
    data["layout_confidence"] = 1.0 if v1_layout else 0.0
    data["layout_detection_count"] = len(v1_layout)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (per-image: camera or flatbed)
    # -------------------------------------------------------------------
    capture_method, capture_conf = _resolve_capture_method(sample)
    data["capture_method"] = capture_method
    data["capture_confidence"] = capture_conf
    data["capture_detection_method"] = "parser_path_structure"

    # -------------------------------------------------------------------
    # DOMAIN (GOV for all ID documents)
    # -------------------------------------------------------------------
    data["domain_level1"] = "GOV"
    data["domain_confidence"] = 1.0
    data["domain_detection_method"] = "dataset_documentation"
    data["domain_content_type"] = "identity_document"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # SCRIPT FAMILY
    # D06: "greek" is not in VALID_SCRIPT_FAMILIES enum; remap to "other"
    # -------------------------------------------------------------------
    sf = _get_script_family(script)
    data["script_family"] = sf if sf != "greek" else "other"

    # -------------------------------------------------------------------
    # CONTENT FLAGS
    # ID documents: portraits present, no tables/formulas/code
    # -------------------------------------------------------------------
    data["has_table"] = False
    data["has_figure"] = True  # ID docs include portrait photos
    data["has_formula"] = False
    data["has_handwriting"] = False  # Printed identity documents
    data["has_signature"] = False
    data["has_code"] = False

    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "dataset_documentation"
    data["content_flags_confidence"] = 0.95
    data["handwriting_present"] = False

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
    data["split"] = sample.get("source", {}).get("split", "train")

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    data["text_scope_content_type"] = "identity_document"
    data["text_scope"] = v1_data.get("text_scope", "printed")

    # -------------------------------------------------------------------
    # IMAGE PROPERTIES
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # -------------------------------------------------------------------
    # RESOLUTION QUALITY (preserve v1 if present)
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
    # TEXT CONTENT
    # midv2020: field text available from parser (Cyrillic names etc.)
    # -------------------------------------------------------------------
    transcription = sample.get("original_labels", {}).get("transcription", "") or ""
    if transcription:
        data["text_has_content"] = True
        data["text_content"] = transcription
        data["text_content_confidence"] = 0.95
        data["text_content_source"] = "parser_gt"
    else:
        # D08: ID documents always contain printed text (names, MRZ, document numbers)
        # even when the parser did not extract a transcription string.
        data["text_has_content"] = True
        data["text_content"] = ""
        data["text_content_confidence"] = 0.5
        data["text_content_source"] = "dataset_documentation"
    data["text_statistics"] = compute_text_statistics(transcription)

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
        "script_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
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

        integrated_data = integrate_sample(sample, llm_index, lang_index)
        stats["integrated"] += 1

        if filename_stem in llm_index:
            stats["llm_matched"] += 1
        if filename_stem in lang_index:
            stats["lang_matched"] += 1

        stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
        stats["split_dist"][integrated_data.get("split", "unknown")] += 1
        stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
        stats["script_dist"][integrated_data.get("iso15924_script", "Zyyy")] += 1
        stats["script_family_dist"][
            integrated_data.get("script_family", "unknown")
        ] += 1
        stats["lang_method_dist"][
            integrated_data.get("text_scope_detection_method", "unknown")
        ] += 1
        stats["capture_method_dist"][
            integrated_data.get("capture_method", "unknown")
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
            new_version: dict[str, Any] = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "schema_version": "2.4.0",  # D10: was absent
                "created_at": now,
                "created_by": f"integrate_{DATASET_NAME}_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "parser path structure + LLM vision + language enrichment"
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

    print("Capture method distribution:")
    for method, count in stats["capture_method_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {method:25s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script distribution:")
    for script, count in stats["script_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {script:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:5d} ({pct:.1f}%)")
    print()

    print("Language distribution (top 10):")
    for lang, count in stats["lang_dist"].most_common(10):
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:5d} ({pct:.1f}%)")
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
    p = argparse.ArgumentParser(
        description=f"Integrate all enrichment sources into {DATASET_NAME} metadata.",
    )
    p.add_argument("--metadata", type=Path, default=METADATA_PATH)
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    p.add_argument("--llm-enrichment", type=Path, default=LLM_ENRICHMENT_PATH)
    p.add_argument("--language-enrichment", type=Path, default=LANGUAGE_ENRICHMENT_PATH)
    p.add_argument(
        "--dry-run", action="store_true", help="Report only, do not write output"
    )
    args = p.parse_args()

    output_path = args.output or args.metadata

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
