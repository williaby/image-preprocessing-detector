#!/usr/bin/env python3
"""Integrate all enrichment sources into ohr-bench Layer 2 metadata.

TEMPLATE VERSION: 1.1.0 (customized for ohr-bench)
CREATED FROM: scripts/audit/integration_script_template.py

Merges 4 data sources into the main metadata JSON for 8,303 records:
  1. Base metadata (v2.1): source paths, existing enrichment v1 data
  2. Language enrichment (OpenLID, 8,259 records): language, script, confidence
  3. Docling layout (7 COCO batch files): per-page layout detections
  4. Docling OCR (7 JSONL batch files): per-document text extraction

Also applies:
  - Domain mapping from path subdirectory (academic->EDU, law->GOV, etc.)
  - Hardcoded capture_method=born_digital (PDF pages extracted at 300 DPI)
  - Layout label standardization (KI-001): Docling lowercase -> DocLayNet PascalCase
  - Content flag derivation from layout canonical_class (no VLM yet, 0.70 conf)
  - KI-008: Re-derive script_family from iso15924_script via get_script_family()
  - Reliability summary computation

v2 changes (schema v2.3.0):
  - Added text_direction (ltr/rtl) derived from iso15924_script
  - Added text_directions_present aggregated from per-page scripts

Known limitations:
  - No LLM enrichment available (missing)
  - Splits are all "unknown" in metadata; TODO: load HF parquet for actual splits
  - OCR text is full-document, not per-page; text_has_content is document-level
  - Content flags are layout-derived only (no VLM verification), confidence=0.70
  - KI-006/KI-007 cannot be applied without LLM enrichment

CRITICAL ID MISMATCH:
  Metadata uses 1-indexed page numbers: 2305.02437v3_p001.png
  Language enrichment uses 0-indexed page numbers: academic/2305.02437v3_page0
  Matching requires: extract domain from path, doc_name from filename,
  convert page number (p001 -> page0).

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_ohr_bench_enrichments.py --dry-run

    # Write output:
    PYTHONPATH=... uv run python3 scripts/integrate_ohr_bench_enrichments.py
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__      = 'integrate-script'
__l4_dataset__       = 'ohr-bench'
__l4_workstream__    = 'WS3'
__l4_parser__        = 'src/image_preprocessing_detector/annotation/parsers/document/ohr_bench.py'



import argparse
import json
import logging
import re
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
DATASET_NAME = "ohr-bench"

IS_SYNTHETIC_DATASET = False

# ===================================================================
# Paths
# ===================================================================
REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")

METADATA_PATH = REGISTRY_DIR / "json" / "ohr-bench_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "ohr-bench_language_enrichment.json"
HF_LANGUAGE_ENRICHMENT_PATH = (
    REGISTRY_DIR / "json" / "ohr-bench_hf_language_enrichment.json"
)

# Docling layout: 7 COCO-format batch files (layout_batch_0.json .. layout_batch_6.json)
DOCLING_LAYOUT_DIR = REGISTRY_DIR / "extracted" / "ohr-bench"

# Docling OCR: 7 JSONL batch files (ocr_batch_0.jsonl .. ocr_batch_6.jsonl)
DOCLING_OCR_DIR = REGISTRY_DIR / "extracted" / "ohr-bench"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# ===================================================================
# KNOWN ISSUE MITIGATIONS
# ===================================================================

# --- KI-001: Docling layout label casing (CRITICAL) -----------------
APPLY_KI_001_LAYOUT_CASING = True

# Full Docling lowercase -> DocLayNet PascalCase mapping.
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

# --- KI-005: Known capture method (from dataset documentation) -------
KNOWN_CAPTURE_METHOD = "born_digital"

# --- Content flag classes (canonical layout -> content flags) ---------
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA", "ISOLATE_FORMULA"}
FIGURE_CLASSES = {"PICTURE", "FIGURE", "CHART"}
CODE_CLASSES = {"CODE"}

# ===================================================================
# OHR-BENCH SPECIFIC: Domain mapping
#
# Extract domain from the path subdirectory in original_path.
# e.g., extracted_images/academic/2305.02437v3_p001.png -> "academic"
# Map to standardized domain_level1 codes.
# ===================================================================
DOMAIN_PATH_TO_LEVEL1: dict[str, str] = {
    "academic": "EDU",
    "textbook": "EDU",
    "law": "GOV",
    "administration": "GOV",
    "finance": "FIN",
    "news": "MED",
    "manual": "TEC",
}

# ISO 15924 script code -> text direction mapping (v2.3.0 schema)
# OHR-bench: born-digital PDFs, modern Chinese is horizontal ltr
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

# Regex to parse metadata filenames: {docname}_p{page_1indexed}.png
# e.g., "2305.02437v3_p001.png" -> docname="2305.02437v3", page_num=1
_METADATA_FILENAME_RE = re.compile(r"^(.+)_p(\d+)\.png$")


# ===================================================================
# OHR-BENCH SPECIFIC: ID bridging helpers
#
# The metadata and language enrichment use different ID schemes:
#   Metadata:   original_filename = "2305.02437v3_p001.png" (1-indexed)
#               original_path = "extracted_images/academic/2305.02437v3_p001.png"
#   Language:   image_id = "academic/2305.02437v3_page0" (0-indexed)
#
# We must bridge these by:
#   1. Extracting domain from the metadata original_path
#   2. Parsing doc_name and page_number from the filename
#   3. Converting page_number from 1-indexed to 0-indexed
#   4. Constructing the language enrichment key
# ===================================================================
def _extract_domain_from_path(original_path: str) -> str:
    """Extract domain subdirectory from an ohr-bench original_path.

    Args:
        original_path: Path like "extracted_images/academic/2305.02437v3_p001.png"

    Returns:
        Domain string (e.g., "academic"), or "misc" if not parseable.
    """
    parts = Path(original_path).parts
    # Expected: ("extracted_images", "academic", "2305.02437v3_p001.png")
    # The domain is the second-to-last component (parent of the filename).
    if len(parts) >= 2:
        return parts[-2]
    return "misc"


def _build_language_key(original_path: str, filename: str) -> str | None:
    """Build the language enrichment lookup key from metadata fields.

    Converts metadata's 1-indexed page scheme to language enrichment's
    0-indexed scheme.

    Args:
        original_path: e.g., "extracted_images/academic/2305.02437v3_p001.png"
        filename: e.g., "2305.02437v3_p001.png" or "DUDE_hash.png"

    Returns:
        Key like "academic/2305.02437v3_page0", or None if unparseable.
    """
    domain = _extract_domain_from_path(original_path)

    match = _METADATA_FILENAME_RE.match(filename)
    if match:
        doc_name = match.group(1)
        page_1indexed = int(match.group(2))
        page_0indexed = page_1indexed - 1
        return f"{domain}/{doc_name}_page{page_0indexed}"

    # Single-page documents: assume page 0
    stem = Path(filename).stem
    if stem:
        return f"{domain}/{stem}_page0"
    return None


def _build_layout_key(filename: str) -> str | None:
    """Build layout annotation lookup key from metadata filename.

    Layout annotations are indexed by "{docname}_p{page_1indexed}",
    which matches the metadata filename stem for multi-page documents.
    For single-page documents (no _pNNN suffix), try "{stem}_p001".

    Args:
        filename: e.g., "2305.02437v3_p001.png" or "DUDE_hash.png"

    Returns:
        Key like "2305.02437v3_p001", or None if unparseable.
    """
    match = _METADATA_FILENAME_RE.match(filename)
    if match:
        return Path(filename).stem
    # Single-page documents: try stem + _p001 (page 1)
    stem = Path(filename).stem
    if stem:
        return f"{stem}_p001"
    return None


def _extract_docname_from_filename(filename: str) -> str | None:
    """Extract document name (without page suffix) from metadata filename.

    Args:
        filename: e.g., "2305.02437v3_p001.png" or "DUDE_hash.png"

    Returns:
        Document name like "2305.02437v3", or None if unparseable.
    """
    match = _METADATA_FILENAME_RE.match(filename)
    if match:
        return match.group(1)
    # Single-page documents: use the stem directly as the docname
    stem = Path(filename).stem
    return stem if stem else None


# ===================================================================
# Data loaders
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to ohr-bench_metadata.json.

    Returns:
        Full metadata dict with "samples" list.
    """
    log.info("Loading metadata from %s", path)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    log.info("  Loaded %d samples", len(data.get("samples", [])))
    return data


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by ohr-bench image_id.

    The image_id format is "{domain}/{docname}_page{0-indexed}",
    e.g., "academic/2305.02437v3_page0".

    Args:
        path: Path to ohr-bench_language_enrichment.json.

    Returns:
        Dict mapping image_id to language enrichment record.
    """
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
            index[image_id] = rec
    log.info("  Indexed %d language records", len(index))
    return index


def load_docling_layout_batches(layout_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all 7 Docling layout batch files and build per-page annotation index.

    Each batch file is COCO format with "images", "annotations", "categories".
    Annotations have: bbox [x,y,w,h], category_name (lowercase Docling labels),
    page (1-indexed), text, image_id.

    Images are indexed by PDF filename (e.g., "2305.02437v3.pdf"), and
    annotations reference image_id. We build a per-page key:
    "{docname}_p{page_1indexed}" -> list of annotation dicts.

    Args:
        layout_dir: Directory containing layout_batch_0.json through
            layout_batch_6.json.

    Returns:
        Dict mapping page key (e.g., "2305.02437v3_p001") to list of
        annotation dicts with standardized fields.
    """
    if not layout_dir.exists():
        log.warning("Docling layout dir not found: %s", layout_dir)
        return {}

    # Collect all batch files
    batch_files = sorted(layout_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("No layout batch files found in %s", layout_dir)
        return {}

    log.info("Loading %d layout batch files from %s", len(batch_files), layout_dir)

    # CRITICAL: image_id values restart from 0 in each batch file.
    # We must process each batch independently to avoid ID collisions.
    page_index: dict[str, list[dict[str, Any]]] = {}
    total_images = 0
    total_annotations = 0
    skipped = 0

    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as f:
            batch: dict[str, Any] = json.load(f)

        # Build per-batch image_id -> docname mapping
        batch_id_to_docname: dict[int, str] = {}
        for img in batch.get("images", []):
            img_id = img.get("id")
            file_name = img.get("file_name", "")
            # file_name is like "2305.02437v3.pdf" or
            # "Groups_And_Symmetry(Armstrong).pdf_74.pdf"
            # Strip only trailing .pdf to get docname
            if file_name.endswith(".pdf"):
                docname = file_name[:-4]
            else:
                docname = file_name
            if img_id is not None and docname:
                batch_id_to_docname[img_id] = docname

        total_images += len(batch_id_to_docname)

        # Process this batch's annotations using this batch's mapping
        for ann in batch.get("annotations", []):
            total_annotations += 1
            img_id = ann.get("image_id")
            page_num = ann.get("page")  # 1-indexed

            docname = batch_id_to_docname.get(img_id, "")
            if not docname or page_num is None:
                skipped += 1
                continue

            # Build page key matching metadata filename stem format
            page_key = f"{docname}_p{page_num:03d}"

            if page_key not in page_index:
                page_index[page_key] = []

            page_index[page_key].append(
                {
                    "bbox": ann.get("bbox", []),
                    "category_name": ann.get("category_name", ""),
                    "text": ann.get("text", ""),
                    "confidence": ann.get("score", ann.get("confidence", 0.85)),
                }
            )

    log.info(
        "  Loaded %d images, %d annotations across all batches",
        total_images,
        total_annotations,
    )
    if skipped > 0:
        log.warning("  Skipped %d annotations (missing image_id or page)", skipped)
    log.info("  Built page index with %d pages", len(page_index))
    return page_index


def load_docling_ocr_batches(ocr_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all 7 Docling OCR batch files and index by document name.

    Each batch is JSONL format with one line per PDF document.
    Fields: source (like "pdfs.zip::academic/2305.02437v3.pdf"),
    text (full document text), confidence, success.

    Note: OCR text is full-document, NOT per-page. We can only determine
    whether the document has text at all, not per-page text content.

    Args:
        ocr_dir: Directory containing ocr_batch_0.jsonl through
            ocr_batch_6.jsonl.

    Returns:
        Dict mapping document name (e.g., "2305.02437v3") to OCR record.
    """
    if not ocr_dir.exists():
        log.warning("Docling OCR dir not found: %s", ocr_dir)
        return {}

    batch_files = sorted(ocr_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        log.warning("No OCR batch files found in %s", ocr_dir)
        return {}

    log.info("Loading %d OCR batch files from %s", len(batch_files), ocr_dir)

    index: dict[str, dict[str, Any]] = {}
    total_lines = 0
    errors = 0

    for batch_path in batch_files:
        with open(batch_path, encoding="utf-8") as f:
            for line in f:
                total_lines += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    rec: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    errors += 1
                    continue

                # Extract doc name from source field
                # source is like "pdfs.zip::academic/2305.02437v3.pdf"
                source = rec.get("source", "")
                # Extract the filename part after "::" and strip .pdf
                if "::" in source:
                    pdf_path = source.split("::", 1)[1]
                else:
                    pdf_path = source

                # Get just the filename without extension
                docname = Path(pdf_path).stem
                if docname:
                    index[docname] = rec

    if errors > 0:
        log.warning("  Skipped %d malformed JSONL lines", errors)
    log.info("  Indexed %d OCR records from %d total lines", len(index), total_lines)
    return index


# ===================================================================
# Derivation helpers
# ===================================================================
def derive_content_flags(
    detections: list[dict[str, Any]],
) -> dict[str, bool]:
    """Derive content flags from canonical layout classes.

    Scans all layout detections and checks canonical_class (or class_name)
    against known class sets for table, formula, figure, and code.

    Args:
        detections: List of layout detection dicts.

    Returns:
        Dict with boolean flags: has_table, has_formula, has_figure, has_code.
    """
    canonical_classes: set[str] = set()
    for det in detections:
        cls = det.get("canonical_class") or det.get("class_name", "")
        if cls:
            canonical_classes.add(cls.upper())

    return {
        "has_table": bool(canonical_classes & TABLE_CLASSES),
        "has_formula": bool(canonical_classes & FORMULA_CLASSES),
        "has_figure": bool(canonical_classes & FIGURE_CLASSES),
        "has_code": bool(canonical_classes & CODE_CLASSES),
    }


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Assesses five field groups and produces a reliability tier for each.

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Dict with min_confidence, field counts, field_summary list,
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
    """Convert Docling lowercase class_name to DocLayNet PascalCase (KI-001).

    Args:
        class_name: Raw class name from Docling layout output.

    Returns:
        Standardized PascalCase class name.
    """
    if APPLY_KI_001_LAYOUT_CASING:
        return DOCLING_TO_DOCLAYNET.get(class_name, class_name)
    return class_name


def derive_text_direction(iso15924_script: str) -> str | None:
    """Derive text reading direction from ISO 15924 script code.

    For ohr-bench, modern Chinese documents are horizontal ltr.

    Returns:
        "ltr", "rtl", or None if script is unknown/unresolvable.
    """
    if not iso15924_script or iso15924_script == "Zyyy":
        return None
    return SCRIPT_TO_DIRECTION.get(iso15924_script, "ltr")


def derive_text_directions_present(primary_script: str) -> list[str]:
    """Aggregate all text directions present in a sample.

    For ohr-bench, each page typically has a single dominant script.
    We derive direction from the primary resolved script only.

    Args:
        primary_script: The resolved iso15924_script for this sample.

    Returns:
        Sorted list of unique directions (e.g., ["ltr"]).
    """
    directions: set[str] = set()

    primary_dir = SCRIPT_TO_DIRECTION.get(primary_script)
    if primary_dir:
        directions.add(primary_dir)

    return sorted(directions) if directions else []


def resolve_language(
    lang_enrichment: dict[str, Any] | None,
    hf_lang_enrichment: dict[str, Any] | None = None,
) -> tuple[str, str, float, str]:
    """Resolve best language/script for an ohr-bench sample.

    Priority chain:
      1. Language enrichment (OpenLID, confidence capped at 0.70)
      2. HF ground truth text character analysis (confidence capped at 0.60)
      3. Fallback to "und"

    Args:
        lang_enrichment: OpenLID language enrichment record (or None).
        hf_lang_enrichment: HF-derived character script enrichment (or None).

    Returns:
        Tuple of (iso639_language, iso15924_script, confidence,
        detection_method).
    """
    # Source 1: Language enrichment (OpenLID) - highest priority
    if lang_enrichment:
        le_lang = lang_enrichment.get("language")
        if le_lang and le_lang != "und":
            le_script = lang_enrichment.get("script") or "Zyyy"
            le_conf = lang_enrichment.get("confidence", 0.5)
            return (le_lang, le_script, min(le_conf, 0.70), "openlid_v2")

    # Source 2: HF ground truth text character analysis - fallback
    if hf_lang_enrichment:
        hf_lang = hf_lang_enrichment.get("language")
        if hf_lang and hf_lang != "und":
            hf_script = hf_lang_enrichment.get("script") or "Zyyy"
            hf_conf = hf_lang_enrichment.get("confidence", 0.5)
            return (hf_lang, hf_script, min(hf_conf, 0.60), "hf_gt_char_script")

    # Fallback: no language information available
    return ("und", "Zyyy", 0.1, "none")


def resolve_domain(original_path: str) -> tuple[str, float, str]:
    """Resolve domain_level1 from the path subdirectory.

    OHR-bench organizes PDFs by domain in subdirectories:
    academic, law, finance, government, newspaper, manual, misc.

    Args:
        original_path: e.g., "extracted_images/academic/2305.02437v3_p001.png"

    Returns:
        Tuple of (domain_level1, confidence, detection_method).
    """
    domain_raw = _extract_domain_from_path(original_path)
    domain_level1 = DOMAIN_PATH_TO_LEVEL1.get(domain_raw, "UNK")

    # Path-based domain is reliable (from dataset organization)
    confidence = 0.95 if domain_level1 != "UNK" else 0.3
    return (domain_level1, confidence, "path_subdirectory")


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
    hf_lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single ohr-bench sample.

    Merges language enrichment, Docling layout, Docling OCR, and
    path-derived domain into a single enrichment data dict.

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        lang_index: Language enrichment index (ohr-bench image_id -> record).
        hf_lang_index: HF ground truth character script index (image_id -> record).
        layout_index: Docling layout index (page_key -> annotations list).
        ocr_index: Docling OCR index (docname -> OCR record).

    Returns:
        New enrichment data dict with all sources merged.
    """
    source = sample["source"]
    filename = source["original_filename"]
    original_path = source.get("original_path", "")

    # Get existing v1 data (if any)
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Build lookup keys for each enrichment source
    lang_key = _build_language_key(original_path, filename)
    layout_key = _build_layout_key(filename)
    docname = _extract_docname_from_filename(filename)

    # Look up enrichment records
    lang_enrichment = lang_index.get(lang_key) if lang_key else None
    hf_lang_enrichment = hf_lang_index.get(lang_key) if lang_key else None
    page_annotations = layout_index.get(layout_key, []) if layout_key else []
    ocr_rec = ocr_index.get(docname) if docname else None

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01 - split: from HuggingFace dataset
    # HF dataset (opendatalab/OHR-Bench) has all 8,561 pages in a
    # single "train" split. No train/val/test column exists despite
    # what the source documentation claims (doc section 2.2 is wrong).
    # -------------------------------------------------------------------
    data["split"] = "train"

    # -------------------------------------------------------------------
    # D02 - capture_method: ALL born_digital
    # OHR-bench contains PDF pages extracted at 300 DPI (not scanned/camera)
    # -------------------------------------------------------------------
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D02 - domain_level1: derived from path subdirectory
    # Maps: academic->EDU, law->GOV, finance->FIN, government->GOV,
    #        newspaper->MED, manual->TEC, misc->UNK
    # -------------------------------------------------------------------
    domain_level1, domain_conf, domain_method = resolve_domain(original_path)
    data["domain_level1"] = domain_level1
    data["domain_confidence"] = domain_conf
    data["domain_detection_method"] = domain_method
    data["domain_content_type"] = ""  # No LLM enrichment available

    # -------------------------------------------------------------------
    # D07/D11 - Language & script: from language enrichment (OpenLID)
    # No LLM enrichment or parser GT available for this dataset.
    # -------------------------------------------------------------------
    lang, script, lang_conf, lang_method = resolve_language(
        lang_enrichment, hf_lang_enrichment
    )
    data["iso639_language"] = lang
    data["iso15924_script"] = script
    data["language_confidence"] = lang_conf
    data["text_scope_detection_method"] = lang_method

    # -------------------------------------------------------------------
    # D03 - script_family: derived from iso15924_script (KI-008)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(script)

    # -------------------------------------------------------------------
    # D09 - Layout detections: from Docling GPU batch extraction
    # Standardize class names via KI-001 (Docling -> DocLayNet)
    # -------------------------------------------------------------------
    standardized_layout: list[dict[str, Any]] = []
    for ann in page_annotations:
        original_class = ann.get("category_name", "")
        canonical_class = standardize_class_name(original_class)
        standardized_layout.append(
            {
                "bbox": ann.get("bbox", []),
                "class_name": canonical_class,
                "canonical_class": canonical_class,
                "source_label": original_class,
                "text": ann.get("text", ""),
                "confidence": ann.get("confidence", 0.85),
            }
        )

    data["layout_detections"] = standardized_layout
    data["layout_source"] = "docling_gpu"
    data["layout_confidence"] = 0.85
    data["layout_detection_count"] = len(standardized_layout)

    # -------------------------------------------------------------------
    # D10 - Content flags: derived from layout detections
    # No VLM verification yet, so use layout-derived flags with lower
    # confidence (0.70) compared to VLM-verified datasets (0.85-0.95).
    # -------------------------------------------------------------------
    flags = derive_content_flags(standardized_layout)
    data["has_table"] = flags["has_table"]
    data["has_formula"] = flags["has_formula"]
    data["has_figure"] = flags["has_figure"]
    data["has_code"] = flags["has_code"]
    data["has_handwriting"] = False  # Born-digital PDFs have no handwriting
    data["has_signature"] = False
    data["content_flags_tier"] = "tier_2_model"
    data["content_flags_source"] = "docling_gpu"
    data["content_flags_confidence"] = 0.70  # Lower: not VLM-verified

    # D06 - handwriting_present: prescreening alias
    data["handwriting_present"] = False

    # -------------------------------------------------------------------
    # D04 - orientation_class: default upright
    # Born-digital PDFs are extracted at correct orientation.
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 0.95  # Born-digital is reliably upright
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D05 - image_properties_color_mode: born-digital PDFs are color
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = v1_data.get(
        "image_properties_color_mode", "color"
    )

    # -------------------------------------------------------------------
    # Text scope: document pages with full-page text
    # -------------------------------------------------------------------
    data["text_scope_content_type"] = v1_data.get("text_scope_content_type", "document")
    data["text_scope"] = v1_data.get("text_scope", "printed")

    # -------------------------------------------------------------------
    # Text content: derive from Docling OCR and layout annotation text
    #
    # OCR text is full-document (not per-page), so we use it as a
    # document-level signal. Additionally, layout annotations have
    # per-element text which is more granular.
    # -------------------------------------------------------------------
    has_text = False

    # Check if document-level OCR found text
    if ocr_rec and ocr_rec.get("success", False):
        doc_text = ocr_rec.get("text", "")
        if doc_text and doc_text.strip():
            has_text = True

    # Check if any layout annotation on this page has text
    if not has_text:
        for ann in standardized_layout:
            ann_text = ann.get("text", "")
            if ann_text and ann_text.strip():
                has_text = True
                break

    data["text_has_content"] = has_text
    data["text_statistics"] = {
        "has_content": has_text,
        "source": "docling_ocr+layout_text",
    }

    # -------------------------------------------------------------------
    # v2.3.0 - text_direction & text_directions_present
    # Derived from resolved iso15924_script.
    # -------------------------------------------------------------------
    text_dir = derive_text_direction(script)
    if text_dir:
        data["text_direction"] = text_dir
        data["text_direction_confidence"] = lang_conf

    dirs_present = derive_text_directions_present(script)
    if dirs_present:
        data["text_directions_present"] = dirs_present

    # -------------------------------------------------------------------
    # Resolution from v1 (if any)
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
    # Additional derived fields
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

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
    # Reliability summary recomputation
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def _track_sample_stats(
    stats: dict[str, Any],
    integrated_data: dict[str, Any],
    lang_key: str | None,
    layout_key: str | None,
    docname: str | None,
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
) -> None:
    """Accumulate per-sample statistics into the stats dict."""
    stats["integrated"] += 1

    if lang_key and lang_key in lang_index:
        stats["lang_matched"] += 1
    if layout_key and layout_key in layout_index:
        stats["layout_matched"] += 1
    if docname and docname in ocr_index:
        stats["ocr_matched"] += 1

    stats["domain_dist"][integrated_data.get("domain_level1", "UNK")] += 1
    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "unknown")] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1
    stats["capture_method_dist"][integrated_data.get("capture_method", "unknown")] += 1

    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    for flag_key, stat_key in (
        ("has_table", "has_table_count"),
        ("has_formula", "has_formula_count"),
        ("has_handwriting", "has_handwriting_count"),
        ("has_figure", "has_figure_count"),
        ("has_code", "has_code_count"),
    ):
        if integrated_data.get(flag_key):
            stats[stat_key] += 1

    # v2.3.0 tracking
    text_dir = integrated_data.get("text_direction")
    if text_dir:
        stats["text_direction_dist"][text_dir] += 1
    else:
        stats["text_direction_dist"]["null"] += 1

    for direction in integrated_data.get("text_directions_present", []):
        stats["text_directions_present_dist"][direction] += 1


def _upsert_enrichment_version(
    sample: dict[str, Any],
    new_version: dict[str, Any],
    version_number: int,
) -> None:
    """Replace existing enrichment version or append new one."""
    versions = sample["enrichments"]["versions"]
    for i, ver in enumerate(versions):
        if ver.get("version") == version_number:
            versions[i] = new_version
            sample["enrichments"]["current_version"] = version_number
            return
    versions.append(new_version)
    sample["enrichments"]["current_version"] = version_number


def run_integration(
    metadata: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
    hf_lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration for all samples.

    Iterates over every sample in metadata, calls integrate_sample(),
    tracks statistics, and (unless dry_run) writes a new enrichment
    version into each sample.

    Args:
        metadata: Full L2 metadata dict with "samples" list.
        lang_index: Language enrichment index (OpenLID).
        hf_lang_index: HF ground truth character script index.
        layout_index: Docling layout index (page_key -> annotations).
        ocr_index: Docling OCR index (docname -> OCR record).
        dry_run: If True, compute stats without modifying metadata.

    Returns:
        Stats dict with counts and distribution Counters.
    """
    stats: dict[str, Any] = {
        "total": 0,
        "integrated": 0,
        "lang_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "has_text_content_count": 0,
        "domain_dist": Counter(),
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "lang_method_dist": Counter(),
        "capture_method_dist": Counter(),
        "text_direction_dist": Counter(),
        "text_directions_present_dist": Counter(),
        "has_table_count": 0,
        "has_formula_count": 0,
        "has_handwriting_count": 0,
        "has_figure_count": 0,
        "has_code_count": 0,
    }

    now = datetime.now(UTC).isoformat()

    for sample in metadata["samples"]:
        stats["total"] += 1
        source = sample["source"]
        filename = source["original_filename"]
        original_path = source.get("original_path", "")

        integrated_data = integrate_sample(
            sample, lang_index, hf_lang_index, layout_index, ocr_index
        )

        # Build keys for stat tracking
        lang_key = _build_language_key(original_path, filename)
        layout_key = _build_layout_key(filename)
        docname = _extract_docname_from_filename(filename)

        _track_sample_stats(
            stats,
            integrated_data,
            lang_key,
            layout_key,
            docname,
            lang_index,
            layout_index,
            ocr_index,
        )

        if not dry_run:
            new_version = {
                "version": ENRICHMENT_VERSION_NUMBER,
                "created_at": now,
                "created_by": "integrate_ohr_bench_enrichments.py",
                "method": "tier_2_model",
                "description": (
                    f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                    "OpenLID language + Docling GPU layout (7 batches) + "
                    "Docling OCR (7 batches) + path-derived domain + "
                    "dataset documentation + "
                    "v2.3.0 text_direction/text_directions_present + "
                    "KI-001 layout label standardization + "
                    "KI-008 script_family re-derivation"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }
            _upsert_enrichment_version(sample, new_version, ENRICHMENT_VERSION_NUMBER)

    return stats


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary with distributions.

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
    print(f"Language matched:     {stats['lang_matched']}")
    print(f"Layout matched:       {stats['layout_matched']}")
    print(f"OCR matched:          {stats['ocr_matched']}")
    print(f"Has text content:     {stats['has_text_content_count']}")
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

    print("Capture method distribution:")
    for cm, count in stats["capture_method_dist"].most_common():
        print(f"  {cm:20s}: {count:5d}")
    print()

    print("Content flags:")
    print(f"  has_table:          {stats['has_table_count']}")
    print(f"  has_formula:        {stats['has_formula_count']}")
    print(f"  has_figure:         {stats['has_figure_count']}")
    print(f"  has_handwriting:    {stats['has_handwriting_count']}")
    print(f"  has_code:           {stats['has_code_count']}")
    print()

    # v2.3.0 fields
    print("Text direction distribution (v2.3.0):")
    for td, count in stats["text_direction_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {td:20s}: {count:5d} ({pct:.1f}%)")

    print("Text directions present (aggregate):")
    for direction, count in stats["text_directions_present_dist"].most_common():
        print(f"  {direction:20s}: {count:5d}")
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
        help="Path to ohr-bench metadata JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--language-enrichment",
        type=Path,
        default=LANGUAGE_ENRICHMENT_PATH,
        help="Path to language enrichment JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--layout-dir",
        type=Path,
        default=DOCLING_LAYOUT_DIR,
        help="Directory with layout_batch_*.json files (default: %(default)s)",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=DOCLING_OCR_DIR,
        help="Directory with ocr_batch_*.jsonl files (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    # ----- Load all data sources -----
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    lang_index = load_language_enrichment(args.language_enrichment)
    hf_lang_index = load_language_enrichment(HF_LANGUAGE_ENRICHMENT_PATH)
    layout_index = load_docling_layout_batches(args.layout_dir)
    ocr_index = load_docling_ocr_batches(args.ocr_dir)

    # ----- Run integration -----
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        lang_index=lang_index,
        hf_lang_index=hf_lang_index,
        layout_index=layout_index,
        ocr_index=ocr_index,
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
    raise SystemExit(main())
