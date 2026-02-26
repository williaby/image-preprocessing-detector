#!/usr/bin/env python3
"""Integrate all enrichment sources into hiertext Layer 2 metadata.

TEMPLATE VERSION: 1.1.0 (customized)
CREATED FROM: scripts/audit/integration_script_template.py
REFERENCE: scripts/integrate_cocotext_enrichments.py (closest peer: scene text)

Merges 6 data sources into the main metadata JSON for all 11,639 records:
  1. Base metadata (v2.1, 11,639 samples)
  2. Parser GT via HiertextParser: split, handwriting, legibility, vertical,
     text content, word-level annotations (GOLD STANDARD for handwriting)
  3. LLM enrichment (8,278 samples, 71.1%): domain, language, script, content_type
  4. Language enrichment (OpenLID, 1,000 samples): language, script (LOW conf 0.153)
  5. Docling layout batches (59 files): layout_detections with bboxes
  6. Docling OCR batches (59 files): text_content fallback

Also applies:
  - Hardcoded known values: capture_method=camera_smartphone
  - Parser GT handwriting assessment: presence_ratio, legibility_ratio,
    presence_category, content_type (word-level ground truth)
  - Missing field population: split, orientation_class, color_mode
  - Reliability summary computation

Known issue mitigations:
  - KI-001 (Docling layout label casing): Run standardize_layout_labels.py before
  - KI-003 (picture detection FP): Scene photos are NOT embedded figures; override
  - KI-006 (formula semantic confusion): No formulas in scene text -> all False
  - KI-007 (UNK domain): Acceptable for scene text; high UNK rate expected
  - KI-008 (script_family directionality): Re-derive from ISO 15924
  - KI-009 (unreliable language claims): LLM > OpenLID > parser > docs fallback

v2 changes (schema v2.3.0):
  - Added text_direction (ltr/rtl/ttb) derived from iso15924_script
  - Added text_directions_present aggregated from parser GT vertical flags
  - HierText uniquely provides per-word 'vertical' boolean for ttb detection

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_hiertext_enrichments.py --dry-run

    # Write output:
    PYTHONPATH=... uv run python3 scripts/integrate_hiertext_enrichments.py
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__      = 'integrate-script'
__l4_dataset__       = 'hiertext'
__l4_workstream__    = 'WS3'
__l4_parser__        = 'src/image_preprocessing_detector/annotation/parsers/multilingual/hiertext.py'



import argparse
import json
import logging
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "hiertext_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "hiertext_llm_enrichment.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "hiertext_language_enrichment.json"

# Parser GT annotation files (single JSON object per file, despite .jsonl extension)
GT_DIR = Path("/mnt/e/image_detection/01_base_data/text_detection/hiertext/gt")

# Audit-phase enrichments (VLM contact sheet - populated after Phase 6)
AUDIT_DIR = Path("scripts/audit/results/hiertext")
VLM_TEST_ENRICHMENT_PATH = AUDIT_DIR / "vlm_test_enrichments.json"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# Content flag derivation classes (for Docling layout detections)
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# ISO 15924 script code -> text direction mapping (v2.3.0 schema)
# Scene text: CJK is predominantly horizontal (ltr) in signage context
SCRIPT_TO_DIRECTION: dict[str, str] = {
    "Arab": "rtl",
    "Hebr": "rtl",
    "Latn": "ltr",
    "Deva": "ltr",
    "Beng": "ltr",
    "Hans": "ltr",
    "Hant": "ltr",
    "Jpan": "ltr",
    "Hang": "ltr",
    "Kore": "ltr",
    "Cyrl": "ltr",
    "Grek": "ltr",
    "Zyyy": "ltr",
    "Zmth": "ltr",
}

# VLM corrections: per-sample overrides from visual inspection (Phase 6).
# Populated after VLM inspection completes.
VLM_TABLE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FIGURE_TRUE_POSITIVES: frozenset[str] = frozenset()
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset()

# NOTE: has_handwriting is derived from PARSER GROUND TRUTH (word-level handwritten
# boolean), NOT from VLM inspection. VLM set below is for additional corrections only.
VLM_HANDWRITING_CORRECTIONS: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Parser GT loader
# ---------------------------------------------------------------------------
def load_hiertext_gt(gt_dir: Path) -> dict[str, dict[str, Any]]:
    """Load HierText ground truth annotations and index by image_id.

    Reads the train.jsonl, validation.jsonl, test.jsonl files (which are
    actually single JSON objects despite the .jsonl extension).

    Returns:
        Dict mapping image_id (16-char hex) to parsed annotation data
        including handwriting/legibility/vertical statistics.
    """
    index: dict[str, dict[str, Any]] = {}

    for split_name in ("train", "validation", "test"):
        gt_path = gt_dir / f"{split_name}.jsonl"
        if not gt_path.exists():
            log.warning("GT file not found: %s", gt_path)
            continue

        log.info("Loading GT from %s", gt_path)
        with open(gt_path, encoding="utf-8") as f:
            gt_data: dict[str, Any] = json.load(f)

        annotations = gt_data.get("annotations", [])
        log.info("  Found %d annotations in %s", len(annotations), split_name)

        for ann in annotations:
            image_id = ann.get("image_id", "")
            if not image_id:
                continue

            # Parse word-level statistics from hierarchical structure
            total_words = 0
            handwritten_words = 0
            legible_words = 0
            illegible_handwritten = 0
            total_chars = 0
            handwritten_chars = 0
            has_vertical = False
            word_texts: list[str] = []

            for para in ann.get("paragraphs", []):
                for line in para.get("lines", []):
                    for word in line.get("words", []):
                        total_words += 1
                        text = word.get("text", "")
                        word_texts.append(text)
                        total_chars += len(text)

                        is_handwritten = word.get("handwritten", False)
                        is_legible = word.get("legible", True)
                        is_vertical = word.get("vertical", False)

                        if is_handwritten:
                            handwritten_words += 1
                            handwritten_chars += len(text)
                            if not is_legible:
                                illegible_handwritten += 1

                        if is_legible:
                            legible_words += 1

                        if is_vertical:
                            has_vertical = True

            # Compute handwriting assessment metrics
            presence_ratio = handwritten_words / total_words if total_words > 0 else 0.0
            legibility_ratio: float | None = None
            if handwritten_words > 0:
                legibility_ratio = round(
                    1.0 - (illegible_handwritten / handwritten_words), 4
                )

            # Presence category (matches HiertextParser thresholds)
            if presence_ratio == 0:
                presence_category = "NONE"
            elif presence_ratio < 0.1:
                presence_category = "SPARSE"
            elif presence_ratio < 0.3:
                presence_category = "MODERATE"
            elif presence_ratio < 0.6:
                presence_category = "SUBSTANTIAL"
            else:
                presence_category = "DOMINANT"

            # Infer content type from word characteristics
            content_type = _infer_handwriting_content_type(
                word_texts, handwritten_words
            )

            # Full text from all words (joined with spaces)
            full_text = " ".join(word_texts) if word_texts else ""

            index[image_id] = {
                "split": split_name,
                "total_word_count": total_words,
                "handwritten_word_count": handwritten_words,
                "legible_word_count": legible_words,
                "illegible_handwritten_count": illegible_handwritten,
                "total_char_count": total_chars,
                "handwritten_char_count": handwritten_chars,
                "has_handwriting": handwritten_words > 0,
                "has_text": total_words > 0,
                "has_vertical": has_vertical,
                "handwriting_presence_ratio": round(presence_ratio, 4),
                "handwriting_legibility_ratio": legibility_ratio,
                "handwriting_presence_category": presence_category,
                "handwriting_content_type": content_type,
                "full_text": full_text,
            }

    log.info("  Total GT records indexed: %d", len(index))
    return index


def _infer_handwriting_content_type(
    word_texts: list[str],
    handwritten_count: int,
) -> str:
    """Infer handwriting content type from word characteristics.

    Returns:
        One of: signatures_marks, numeric, alphanumeric, prose, mixed,
        not_applicable.
    """
    if handwritten_count == 0:
        return "not_applicable"
    if handwritten_count <= 2:
        return "signatures_marks"

    # Simple heuristic: check character composition
    numeric_count = sum(1 for w in word_texts if w.isdigit())
    alpha_count = sum(1 for w in word_texts if w.isalpha())

    if numeric_count > alpha_count * 2:
        return "numeric"
    if alpha_count > numeric_count * 2:
        if len(word_texts) > 10:
            return "prose"
        return "alphanumeric"
    return "mixed"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def load_metadata(path: Path) -> dict[str, Any]:
    """Load L2 metadata JSON."""
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id (16-char hex stem)."""
    if not path.exists():
        log.warning("LLM enrichment not found: %s", path)
        return {}
    log.info("Loading LLM enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[str(image_id)] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by image_id."""
    if not path.exists():
        log.warning("Language enrichment not found: %s", path)
        return {}
    log.info("Loading language enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("samples", []):
        image_id = rec.get("image_id", "")
        if image_id:
            index[str(image_id)] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def load_vlm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM contact sheet enrichment and index by image_id."""
    if not path.exists():
        log.info("VLM enrichment not found (Phase 6 pending): %s", path)
        return {}
    log.info("Loading VLM enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = raw.get("samples", {})
    log.info("  Indexed %d VLM records", len(index))
    return index


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes."""
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
    """Compute sample_reliability_summary for an enrichment data dict."""
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


def derive_text_direction(iso15924_script: str) -> str | None:
    """Derive text reading direction from ISO 15924 script code.

    Returns:
        "ltr", "rtl", or None if script is unknown/unresolvable.
    """
    if not iso15924_script or iso15924_script == "Zyyy":
        return None
    return SCRIPT_TO_DIRECTION.get(iso15924_script, "ltr")


def derive_text_directions_present(
    primary_script: str,
    parser_gt: dict[str, Any],
) -> list[str]:
    """Aggregate all text directions present in a HierText sample.

    HierText uniquely provides per-word 'vertical' boolean flags that
    directly indicate top-to-bottom text direction. This is more reliable
    than script-based inference for ttb detection.

    Args:
        primary_script: The resolved iso15924_script for this sample.
        parser_gt: Parsed GT data for this sample (from load_hiertext_gt).

    Returns:
        Sorted list of unique directions (e.g., ["ltr"], ["ltr", "ttb"]).
    """
    directions: set[str] = set()

    # Primary direction from resolved script
    primary_dir = SCRIPT_TO_DIRECTION.get(primary_script)
    if primary_dir:
        directions.add(primary_dir)

    # HierText-specific: word-level vertical flag -> "ttb"
    if parser_gt.get("has_vertical", False):
        directions.add("ttb")

    return sorted(directions) if directions else []


# ---------------------------------------------------------------------------
# Language resolution (KI-009 mitigation)
# ---------------------------------------------------------------------------
def resolve_language(
    sample: dict[str, Any],
    llm: dict[str, Any] | None,
    lang_enrichment: dict[str, Any] | None,
    vlm: dict[str, Any] | None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for a HierText sample.

    Priority chain (KI-009 mitigation):
      1. VLM contact sheet (highest confidence, Phase 6 visual ID)
      2. LLM enrichment iso639_language (confidence 0.65, 71.1% coverage)
      3. OpenLID language enrichment (UNRELIABLE - avg conf 0.153)
      4. Fallback to "und" (undetermined)

    NOTE: HierText has NO per-instance language labels in source annotations.
    Parser GT language_code is always None (multi-language dataset).

    Args:
        sample: Full sample dict from L2 metadata.
        llm: LLM enrichment record for this sample (or None).
        lang_enrichment: Language enrichment record (or None).
        vlm: VLM contact sheet record for this sample (or None).

    Returns:
        (iso639_language, iso15924_script, confidence, method)
    """
    # Source 1: VLM contact sheet (Phase 6 visual identification)
    if vlm:
        vlm_lang = vlm.get("lang")
        if vlm_lang and vlm_lang != "und":
            vlm_script = vlm.get("script") or "Zyyy"
            return (vlm_lang, vlm_script, 0.85, "vlm_contact_sheet")

    # Source 2: LLM enrichment (text-only, 71.1% coverage)
    if llm:
        llm_lang = llm.get("iso639_language")
        if llm_lang and llm_lang != "und":
            llm_script = llm.get("iso15924_script") or "Zyyy"
            return (llm_lang, llm_script, 0.65, "llm_text")

    # Source 3: OpenLID (UNRELIABLE for scene text, cap at 0.40)
    # KI-009: avg_confidence=0.153, essentially random for scene text
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        if le_lang and le_lang != "und":
            le_script = lang_enrichment.get("script") or "Zyyy"
            le_conf = lang_enrichment.get("confidence", 0.15)
            return (le_lang, le_script, min(le_conf, 0.40), "openlid_v2")

    # Fallback: no language information available
    return ("und", "Zyyy", 0.10, "none")


# ---------------------------------------------------------------------------
# Per-sample integration
# ---------------------------------------------------------------------------
def integrate_sample(
    sample: dict[str, Any],
    parser_gt: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single hiertext sample.

    Returns a new enrichment version data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    filename_stem = Path(filename).stem

    # Get existing v1 data (if any)
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Source lookups by filename stem (which IS the image_id for HierText)
    llm = llm_index.get(filename_stem)
    lang_enrichment = lang_index.get(filename_stem)
    vlm = vlm_index.get(filename_stem)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01 - split: from parser GT folder structure
    # -------------------------------------------------------------------
    gt_split = parser_gt.get("split", "unknown")
    data["split"] = gt_split
    # Also update source.split since it's currently "unknown"
    sample["source"]["split"] = gt_split

    # -------------------------------------------------------------------
    # D02 - capture_method: ALL camera_smartphone
    # Open Images Dataset = natural scene photographs
    # -------------------------------------------------------------------
    data["capture_method"] = "camera_smartphone"
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # Domain: LLM enrichment > VLM/keyword heuristic > UNK (KI-007)
    # -------------------------------------------------------------------
    if llm:
        domain = llm.get("domain_level1") or "UNK"
        domain_conf = 0.65 if domain != "UNK" else 0.40
        data["domain_level1"] = domain
        data["domain_confidence"] = domain_conf
        data["domain_detection_method"] = "llm_text"
        data["domain_content_type"] = llm.get("content_type", "")
    else:
        data["domain_level1"] = "UNK"
        data["domain_confidence"] = 0.10
        data["domain_detection_method"] = "none"
        data["domain_content_type"] = ""

    # VLM/keyword domain fallback for UNK samples
    if data["domain_level1"] == "UNK" and vlm:
        vlm_domain = vlm.get("domain")
        if vlm_domain and vlm_domain != "UNK":
            data["domain_level1"] = vlm_domain
            data["domain_confidence"] = vlm.get("domain_confidence", 0.40)
            data["domain_detection_method"] = vlm.get(
                "domain_method", "keyword_heuristic"
            )

    # -------------------------------------------------------------------
    # D03/D04 - Language & script: multi-source resolution (KI-009)
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        sample, llm, lang_enrichment, vlm
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # D04 - script_family: derived from iso15924_script (KI-008)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # -------------------------------------------------------------------
    # Layout detections: preserve v1 if present
    # -------------------------------------------------------------------
    v1_layout = v1_data.get("layout_detections", [])
    data["layout_detections"] = v1_layout
    data["layout_source"] = v1_data.get("layout_source", "none")
    data["layout_confidence"] = v1_data.get("layout_confidence", 0.0)
    data["layout_detection_count"] = len(v1_layout)

    # -------------------------------------------------------------------
    # D05/D10/D12 - Content flags: parser GT handwriting + layout + VLM
    # -------------------------------------------------------------------
    # has_handwriting: PARSER GROUND TRUTH (gold standard for this dataset)
    # HierText provides explicit word-level handwritten booleans.
    # LLM enrichment has 0% handwriting detection on scene text - USELESS.
    data["has_handwriting"] = parser_gt.get("has_handwriting", False) or (
        filename_stem in VLM_HANDWRITING_CORRECTIONS
    )

    # has_table/has_formula/has_figure: layout-derived + VLM-confirmed only
    # Scene text images are photos - "Picture" from Docling is the photo itself
    layout_flags = derive_content_flags(v1_layout)
    data["has_table"] = (
        layout_flags["has_table"] or filename_stem in VLM_TABLE_TRUE_POSITIVES
    )
    data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
    data["has_figure"] = filename_stem in VLM_FIGURE_TRUE_POSITIVES
    data["has_signature"] = False
    data["has_code"] = False

    data["content_flags_tier"] = "tier_1_gt"
    data["content_flags_source"] = "parser_gt+layout_derived"
    data["content_flags_confidence"] = 0.95

    # D05 - handwriting_present: prescreening alias
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # HierText-specific: graded handwriting assessment fields
    # These are the gold-standard labels that make this dataset unique
    # -------------------------------------------------------------------
    data["handwriting_presence_ratio"] = parser_gt.get(
        "handwriting_presence_ratio", 0.0
    )
    data["handwriting_presence_category"] = parser_gt.get(
        "handwriting_presence_category", "NONE"
    )
    data["handwriting_legibility_ratio"] = parser_gt.get("handwriting_legibility_ratio")
    data["handwriting_content_type"] = parser_gt.get(
        "handwriting_content_type", "not_applicable"
    )
    data["handwriting_word_count"] = parser_gt.get("handwritten_word_count", 0)
    data["total_word_count"] = parser_gt.get("total_word_count", 0)
    data["illegible_handwritten_word_count"] = parser_gt.get(
        "illegible_handwritten_count", 0
    )

    # -------------------------------------------------------------------
    # D06 - orientation_class: default upright (no source available)
    # -------------------------------------------------------------------
    if llm:
        llm_orient = llm.get("orientation_class")
        if llm_orient is not None:
            data["orientation_class"] = llm_orient
            data["orientation_confidence"] = 0.65
            data["orientation_detection_method"] = "llm_text"
        else:
            data["orientation_class"] = 0
            data["orientation_confidence"] = 0.5
            data["orientation_detection_method"] = "default_upright"
    else:
        data["orientation_class"] = 0
        data["orientation_confidence"] = 0.5
        data["orientation_detection_method"] = "default_upright"

    # -------------------------------------------------------------------
    # D08 - image_properties_color_mode: all camera photos are color
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = "color"

    # -------------------------------------------------------------------
    # Text scope: scene text with word-level annotations
    # -------------------------------------------------------------------
    if llm:
        content_type = llm.get("content_type", "")
        data["text_scope_content_type"] = content_type or "scene_text"
    else:
        data["text_scope_content_type"] = v1_data.get(
            "text_scope_content_type", "scene_text"
        )
    data["text_scope"] = "word"

    # -------------------------------------------------------------------
    # D09/D10 - v2.3.0: text_direction & text_directions_present
    # -------------------------------------------------------------------
    text_dir = derive_text_direction(script)
    if text_dir:
        data["text_direction"] = text_dir
        data["text_direction_confidence"] = lang_conf

    dirs_present = derive_text_directions_present(script, parser_gt)
    if dirs_present:
        data["text_directions_present"] = dirs_present

    # -------------------------------------------------------------------
    # D07 - Text content from parser GT (word-level transcriptions)
    # Parser GT is higher quality than Docling OCR (ground truth text)
    # -------------------------------------------------------------------
    full_text = parser_gt.get("full_text", "")
    total_words = parser_gt.get("total_word_count", 0)
    legible_words = parser_gt.get("legible_word_count", 0)

    data["text_has_content"] = total_words > 0
    data["text_statistics"] = {
        "has_content": total_words > 0,
        "word_count": total_words,
        "legible_word_count": legible_words,
        "char_count": parser_gt.get("total_char_count", 0),
        "source": "parser_hiertext_gt",
    }
    if full_text:
        data["text_content_source"] = "parser_ground_truth"
        data["text_content_confidence"] = 1.0

    # Resolution from v1 (if any)
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
    # Additional derived fields
    # -------------------------------------------------------------------
    data["dataset_short_code"] = "hiertext"

    # Preserve v1 text quality fields
    for field in (
        "text_quality_confidence",
        "text_quality_is_soft_label",
        "text_quality_method",
        "text_quality_provenance_tier",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # Reliability summary
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ---------------------------------------------------------------------------
# Integration runner
# ---------------------------------------------------------------------------
def _track_sample_stats(
    stats: dict[str, Any],
    filename_stem: str,
    integrated_data: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]],
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1
    if filename_stem in llm_index:
        stats["llm_matched"] += 1
    if filename_stem in lang_index:
        stats["lang_matched"] += 1
    if filename_stem in vlm_index:
        stats["vlm_matched"] += 1

    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "unknown")] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1

    for flag_key, stat_key in (
        ("has_table", "has_table_count"),
        ("has_formula", "has_formula_count"),
        ("has_handwriting", "has_handwriting_count"),
        ("has_figure", "has_figure_count"),
    ):
        if integrated_data.get(flag_key):
            stats[stat_key] += 1

    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    # v2.3.0 tracking
    td = integrated_data.get("text_direction")
    if td:
        stats["text_direction_dist"][td] += 1
    else:
        stats["text_direction_dist"]["null"] += 1

    for d in integrated_data.get("text_directions_present", []):
        stats["text_directions_present_dist"][d] += 1

    # Handwriting assessment tracking
    category = integrated_data.get("handwriting_presence_category", "NONE")
    stats["hw_presence_dist"][category] += 1


def _upsert_enrichment_version(
    sample: dict[str, Any],
    new_version: dict[str, Any],
    version_number: int,
) -> None:
    """Replace existing enrichment version or append new one."""
    versions = sample["enrichments"]["versions"]
    for i, v in enumerate(versions):
        if v.get("version") == version_number:
            versions[i] = new_version
            sample["enrichments"]["current_version"] = version_number
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = version_number


def run_integration(
    metadata: dict[str, Any],
    parser_gt_index: dict[str, dict[str, Any]],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    vlm_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples."""
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "gt_matched": 0,
        "gt_missed": 0,
        "llm_matched": 0,
        "lang_matched": 0,
        "vlm_matched": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "text_direction_dist": Counter(),
        "text_directions_present_dist": Counter(),
        "hw_presence_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
        "has_text_content_count": 0,
    }

    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem

        # Look up parser GT by image_id (filename stem for HierText)
        parser_gt = parser_gt_index.get(filename_stem, {})
        if parser_gt:
            stats["gt_matched"] += 1
        else:
            stats["gt_missed"] += 1
            log.debug("No parser GT for %s", filename_stem)

        integrated_data = integrate_sample(
            sample, parser_gt, llm_index, lang_index, vlm_index
        )

        _track_sample_stats(
            stats,
            filename_stem,
            integrated_data,
            llm_index,
            lang_index,
            vlm_index,
        )

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_hiertext_enrichments.py",
                "method": "tier_1_gt",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "parser GT (handwriting, legibility, vertical, text, split) + "
                    "LLM text enrichment + OpenLID language + "
                    "dataset documentation + "
                    "v2.3.0 text_direction/text_directions_present"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(sample, new_version, ENRICHMENT_VERSION_NUMBER)

    return stats


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary."""
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print("hiertext Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']}")
    print(f"Integrated:           {stats['integrated']}")
    print(f"GT matched:           {stats['gt_matched']}")
    print(f"GT missed:            {stats['gt_missed']}")
    print(f"LLM matched:          {stats['llm_matched']}")
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"VLM matched:          {stats['vlm_matched']}")
    print(f"Has text content:     {stats.get('has_text_content_count', 0)}")
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

    print("Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:5d}")
    print()

    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print()

    print("Handwriting assessment (gold standard):")
    for cat, count in stats["hw_presence_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {cat:20s}: {count:5d} ({pct:.1f}%)")
    print()

    # v2.3.0 fields
    print("Text direction distribution (v2.3.0):")
    for td, count in stats["text_direction_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {td:20s}: {count:5d} ({pct:.1f}%)")

    print("Text directions present (aggregate):")
    for d, count in stats["text_directions_present_dist"].most_common():
        print(f"  {d:20s}: {count:5d}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into hiertext metadata.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to hiertext_metadata.json (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--gt-dir",
        type=Path,
        default=GT_DIR,
        help="Path to HierText GT directory (default: %(default)s)",
    )
    parser.add_argument(
        "--llm-enrichment",
        type=Path,
        default=LLM_ENRICHMENT_PATH,
        help="Path to LLM enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--language-enrichment",
        type=Path,
        default=LANGUAGE_ENRICHMENT_PATH,
        help="Path to language enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--vlm-enrichment",
        type=Path,
        default=VLM_TEST_ENRICHMENT_PATH,
        help="Path to VLM contact sheet enrichment (default: %(default)s)",
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

    if not args.gt_dir.is_dir():
        log.error("GT directory not found: %s", args.gt_dir)
        return 1

    # Load all data sources
    metadata = load_metadata(args.metadata)
    parser_gt_index = load_hiertext_gt(args.gt_dir)
    llm_index = load_llm_enrichment(args.llm_enrichment)
    lang_index = load_language_enrichment(args.language_enrichment)
    vlm_index = load_vlm_enrichment(args.vlm_enrichment)

    # Run integration
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        parser_gt_index=parser_gt_index,
        llm_index=llm_index,
        lang_index=lang_index,
        vlm_index=vlm_index,
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
    raise SystemExit(main())
