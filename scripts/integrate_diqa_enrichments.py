#!/usr/bin/env python3
"""Integrate all enrichment sources into DIQA-5000 Layer 2 metadata.

Merges 7 data sources into the main metadata JSON for all 5,500 records:
  1. Parser data (tier_0): capture_method, split, MOS scores
  2. LLM enrichment (tier_2, 500 ori/ images): domain, content flags, orientation
  3. Language enrichment (tier_2, 5,499 images): iso639, iso15924, script_family
  4. Egret-xlarge layout (tier_2, preferred): 17-class with per-detection confidence
  5. Docling GPU layout (tier_2, fallback): layout detections (COCO xywh)
  6. Docling GPU OCR (tier_2, 5,500 images): text_content, text_statistics
  7. Derived fields (tier_3): image_properties, paper_size, degradations

Layout priority: egret_xlarge > docling_gpu > DocLayout-YOLO (v1).
Creates a new enrichment version in each sample's enrichments.versions[].

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/integrate_diqa_enrichments.py

    # Dry run (report only, no write):
    PYTHONPATH=... uv run python3 scripts/integrate_diqa_enrichments.py --dry-run

    # Custom paths:
    PYTHONPATH=... uv run python3 scripts/integrate_diqa_enrichments.py \
        --metadata /path/to/diqa-5000_metadata.json \
        --output /path/to/output.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import statistics
import time
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

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
METADATA_PATH = REGISTRY_DIR / "json" / "diqa-5000_metadata.json"
LLM_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "diqa-5000_llm_enrichment.json"
LANG_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "diqa-5000_language_enrichment.json"
LAYOUT_BATCH_DIR = REGISTRY_DIR / "extracted" / "diqa-5000"
EGRET_BATCH_DIR = REGISTRY_DIR / "extracted" / "diqa-5000-egret"
OCR_BATCH_DIR = REGISTRY_DIR / "extracted" / "diqa-5000"
DATASET_DIR = Path("/mnt/e/image_detection/02_benchmark_only/diqa-5000")
ORPHAN_CORRECTIONS_PATH = Path(
    "scripts/audit/results/diqa-5000/orphan_corrections.json"
)

SCRIPT_VERSION = "2.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v3"

# Valid script_family enum values (from schema)
SCRIPT_FAMILY_MAPPING: dict[str, str] = {
    "Arab": "arabic",
    "Hebr": "arabic",
    "Hans": "cjk",
    "Hant": "cjk",
    "Jpan": "cjk",
    "Kore": "cjk",
    "Deva": "indic",
    "Beng": "indic",
    "Guru": "indic",
    "Gujr": "indic",
    "Orya": "indic",
    "Taml": "indic",
    "Telu": "indic",
    "Knda": "indic",
    "Mlym": "indic",
    "Sinh": "indic",
    "Thai": "indic",
    "Latn": "latin",
    "Cyrl": "cyrillic",
    "Grek": "latin",
}

# Content flag derivation from canonical layout classes
TABLE_CLASSES = {"TABLE"}
FORMULA_CLASSES = {"FORMULA"}
FIGURE_CLASSES = {"PICTURE", "CHART"}
CODE_CLASSES = {"CODE"}

# Docling layout category -> canonical class mapping (for content flag derivation)
DOCLING_CATEGORY_TO_CANONICAL: dict[str, str] = {
    "caption": "CAPTION",
    "checkbox_unselected": "CHECKBOX_UNSELECTED",
    "code": "CODE",
    "footnote": "FOOTNOTE",
    "formula": "FORMULA",
    "list_item": "LIST_ITEM",
    "picture": "PICTURE",
    "section_header": "SECTION_HEADER",
    "table": "TABLE",
    "text": "TEXT",
}


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def load_metadata(path: Path) -> dict[str, Any]:
    """Load main metadata JSON."""
    log.info("Loading metadata from %s ...", path)
    with open(path) as fh:
        data = json.load(fh)
    log.info("  Loaded %d samples", len(data["samples"]))
    return data


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment, indexed by original_filename."""
    log.info("Loading LLM enrichment from %s ...", path)
    with open(path) as fh:
        data = json.load(fh)

    index: dict[str, dict[str, Any]] = {}
    for sample in data["samples"]:
        # image_id is like "test_ori_00001", need "test_ori_00001.jpg"
        filename = sample["image_id"] + ".jpg"
        index[filename] = sample

    log.info("  Indexed %d LLM enrichment records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment, indexed by original_filename."""
    log.info("Loading language enrichment from %s ...", path)
    with open(path) as fh:
        data = json.load(fh)

    index: dict[str, dict[str, Any]] = {}
    for sample in data["samples"]:
        filename = sample["image_id"] + ".jpg"
        index[filename] = sample

    log.info("  Indexed %d language enrichment records", len(index))
    return index


def load_layout_batches(batch_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all Docling GPU layout batches, indexed by filename.

    Returns dict mapping filename -> list of annotation dicts (COCO xywh format).
    """
    log.info("Loading layout batches from %s ...", batch_dir)
    batch_files = sorted(batch_dir.glob("layout_batch_*.json"))
    if not batch_files:
        log.warning("  No layout batch files found!")
        return {}

    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0

    for bf in batch_files:
        with open(bf) as fh:
            batch = json.load(fh)

        # Build image_id -> filename mapping for this batch
        image_id_to_filename: dict[int, str] = {}
        for img in batch["images"]:
            image_id_to_filename[img["id"]] = img["file_name"]
            if img["file_name"] not in index:
                index[img["file_name"]] = []

        # Process annotations
        for ann in batch["annotations"]:
            img_id = ann["image_id"]
            filename = image_id_to_filename.get(img_id)
            if filename is None:
                continue

            # bbox is already in COCO [x, y, w, h] format per the batch schema
            detection = {
                "class_name": ann["category_name"],
                "bbox": ann["bbox"],
                "confidence": 1.0,  # Docling doesn't provide per-annotation confidence
                "source": "docling_gpu",
                "canonical_class": DOCLING_CATEGORY_TO_CANONICAL.get(
                    ann["category_name"], ann["category_name"].upper()
                ),
                "source_schema": "docling",
                "text_snippet": ann.get("text", "")[:200] if ann.get("text") else "",
            }
            index[filename].append(detection)
            total_annotations += 1

    log.info(
        "  Loaded %d annotations across %d images from %d batch files",
        total_annotations,
        len(index),
        len(batch_files),
    )
    return index


def load_egret_batches(batch_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load egret-xlarge layout batches, indexed by filename.

    Returns dict mapping filename -> list of annotation dicts (COCO xywh format).
    Compatible with the layout_index format expected by integrate_sample().
    """
    log.info("Loading egret batches from %s ...", batch_dir)
    if not batch_dir.exists():
        log.warning("  Egret batch directory does not exist: %s", batch_dir)
        return {}

    batch_files = sorted(batch_dir.glob("egret_batch_*.json"))
    if not batch_files:
        log.warning("  No egret batch files found!")
        return {}

    index: dict[str, list[dict[str, Any]]] = {}
    total_annotations = 0

    for bf in batch_files:
        with open(bf) as fh:
            batch = json.load(fh)

        # Build image_id -> filename mapping for this batch
        image_id_to_filename: dict[int, str] = {}
        for img in batch["images"]:
            image_id_to_filename[img["id"]] = img["file_name"]
            if img["file_name"] not in index:
                index[img["file_name"]] = []

        # Process annotations - egret already has confidence + canonical_class
        for ann in batch["annotations"]:
            img_id = ann["image_id"]
            filename = image_id_to_filename.get(img_id)
            if filename is None:
                continue

            detection = {
                "class_name": ann.get("category_name", ""),
                "bbox": ann["bbox"],
                "confidence": ann.get("confidence", 0.9),
                "source": "egret_xlarge",
                "canonical_class": ann.get(
                    "canonical_class",
                    DOCLING_CATEGORY_TO_CANONICAL.get(
                        ann.get("category_name", ""), "UNKNOWN"
                    ),
                ),
                "source_schema": "docling",
                "text_snippet": "",
            }
            index[filename].append(detection)
            total_annotations += 1

    log.info(
        "  Loaded %d egret annotations across %d images from %d batch files",
        total_annotations,
        len(index),
        len(batch_files),
    )
    return index


def load_ocr_batches(batch_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all Docling GPU OCR batches, indexed by filename.

    Returns dict mapping filename -> OCR record with text and metadata.
    """
    log.info("Loading OCR batches from %s ...", batch_dir)
    batch_files = sorted(batch_dir.glob("ocr_batch_*.jsonl"))
    if not batch_files:
        log.warning("  No OCR batch files found!")
        return {}

    index: dict[str, dict[str, Any]] = {}

    for bf in batch_files:
        with open(bf) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                # Extract filename from GCS path
                filename = record["source"].split("/")[-1]
                index[filename] = record

    log.info(
        "  Loaded %d OCR records from %d batch files", len(index), len(batch_files)
    )
    return index


def load_mos_scores(
    dataset_dir: Path,
) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    """Load MOS scores from all split CSVs.

    Returns:
        Tuple of:
        - mos_index: dict mapping filename -> {overall, sharpness, color_fidelity}
        - res_to_ori: dict mapping res filename -> ori filename
    """
    log.info("Loading MOS scores from %s ...", dataset_dir)
    mos_index: dict[str, dict[str, float]] = {}
    res_to_ori: dict[str, str] = {}

    for split in ["train", "val", "test"]:
        csv_path = dataset_dir / split / f"{split}.csv"
        if not csv_path.is_file():
            log.warning("  MOS CSV not found: %s", csv_path)
            continue

        with open(csv_path, newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                res_filename = row["res"].strip()
                ori_filename = row["ori"].strip()

                scores = {
                    "overall": float(row["overall"]),
                    "sharpness": float(row["sharpness"]),
                    "color_fidelity": float(row["color_fidelity"]),
                }

                # Index by res filename (the enhanced image)
                mos_index[res_filename] = scores

                # Build res->ori mapping for domain/language transfer
                res_to_ori[res_filename] = ori_filename

                # Also store a reference for ori images (use average of its res variants)
                # Use the first one encountered as representative
                if ori_filename not in mos_index:
                    mos_index[ori_filename] = scores

    log.info(
        "  Loaded MOS scores for %d images, %d res->ori mappings",
        len(mos_index),
        len(res_to_ori),
    )
    return mos_index, res_to_ori


# ---------------------------------------------------------------------------
# Text statistics computation
# ---------------------------------------------------------------------------
def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from OCR output."""
    if not text or text.strip() == "":
        return {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "has_content": False,
        }

    # Clean up image placeholders
    clean_text = text.replace("<!-- image -->", "").strip()

    lines = clean_text.split("\n")
    non_empty_lines = [ln for ln in lines if ln.strip()]
    words = clean_text.split()

    # Detect CJK characters (Chinese, Japanese, Korean)
    cjk_pattern = re.compile(
        r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\u3040-\u309f"
        r"\u30a0-\u30ff\uac00-\ud7af]"
    )
    cjk_chars = len(cjk_pattern.findall(clean_text))
    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))

    return {
        "char_count": len(clean_text),
        "word_count": len(words),
        "line_count": len(non_empty_lines),
        "cjk_char_count": cjk_chars,
        "latin_word_count": latin_words,
        "has_content": len(clean_text) > 0,
        "avg_line_length": round(statistics.mean(len(ln) for ln in non_empty_lines), 1)
        if non_empty_lines
        else 0,
    }


# ---------------------------------------------------------------------------
# Paper size estimation
# ---------------------------------------------------------------------------
def estimate_paper_size(
    width_px: int, height_px: int, dpi: int | None = None
) -> dict[str, Any]:
    """Estimate paper size from image dimensions.

    Assumes 300 DPI if not specified (DIQA-5000 was printed at 300 DPI).
    """
    effective_dpi = dpi if dpi and dpi > 0 else 300

    width_in = width_px / effective_dpi
    height_in = height_px / effective_dpi

    # Ensure width < height for comparison (portrait orientation)
    short = min(width_in, height_in)
    long_side = max(width_in, height_in)

    # Common paper sizes (width x height in inches, portrait)
    paper_sizes = {
        "A4": (8.27, 11.69),
        "Letter": (8.5, 11.0),
        "A3": (11.69, 16.54),
        "A5": (5.83, 8.27),
        "Legal": (8.5, 14.0),
        "B5": (6.93, 9.84),
    }

    best_match = "unknown"
    best_distance = float("inf")

    for name, (pw, ph) in paper_sizes.items():
        dist = math.sqrt((short - pw) ** 2 + (long_side - ph) ** 2)
        if dist < best_distance:
            best_distance = dist
            best_match = name

    return {
        "estimated_size": best_match,
        "estimated_width_in": round(width_in, 2),
        "estimated_height_in": round(height_in, 2),
        "assumed_dpi": effective_dpi,
        "confidence": 0.6 if best_distance < 2.0 else 0.3,
    }


def load_orphan_corrections(path: Path) -> dict[str, dict[str, Any]]:
    """Load manual corrections for orphan images, indexed by filename.

    Returns dict mapping filename -> corrections dict with field overrides.
    """
    if not path.exists():
        log.info("No orphan corrections file at %s", path)
        return {}

    log.info("Loading orphan corrections from %s ...", path)
    with open(path) as fh:
        data = json.load(fh)

    index: dict[str, dict[str, Any]] = {}
    for entry in data.get("corrections", []):
        corr = entry.get("corrections", {})
        # Single filename entry
        if "filename" in entry:
            index[entry["filename"]] = corr
        # Multi-filename entry
        for fn in entry.get("filenames", []):
            index[fn] = corr

    log.info("  Loaded corrections for %d images", len(index))
    return index


# ---------------------------------------------------------------------------
# Derive content flags from layout detections
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


# ---------------------------------------------------------------------------
# Derive physical degradation for ori/ images
# ---------------------------------------------------------------------------
def infer_ori_degradation_category(filename: str) -> str | None:
    """Infer distortion category for ori/ images from filename pattern.

    DIQA-5000 has 500 ori images across 5 distortion categories (100 each).
    Without explicit mapping, we can't determine which category from the filename alone.
    Returns None (requires lookup table or paper appendix).
    """
    # The paper doesn't provide a filename-to-distortion mapping
    # This would need to come from additional metadata
    return None


# ---------------------------------------------------------------------------
# MOS to quality tier mapping
# ---------------------------------------------------------------------------
def mos_to_quality_tier(overall_mos: float) -> str:
    """Map MOS overall score (1-5) to quality tier."""
    if overall_mos >= 4.0:
        return "high"
    if overall_mos >= 3.0:
        return "medium"
    if overall_mos >= 2.0:
        return "low"
    return "very_low"


def mos_to_normalized(mos: float) -> float:
    """Normalize MOS score from 1-5 to 0-1 range."""
    return round(max(0.0, min(1.0, (mos - 1.0) / 4.0)), 4)


# ---------------------------------------------------------------------------
# Reliability summary computation
# ---------------------------------------------------------------------------
def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict."""
    fields: list[dict[str, Any]] = []

    # Define field -> (confidence_key, tier) mappings
    field_defs = [
        ("capture_method", "capture_confidence", "capture_detection_method"),
        ("domain", "domain_confidence", None),
        ("language", "language_confidence", None),
        ("layout_detections", "layout_confidence", None),
        ("content_flags", "content_flags_confidence", None),
        ("text_quality", "text_quality_confidence", None),
        ("image_properties", "image_properties_confidence", None),
        ("geometric", "geometric_confidence", None),
        ("quality_scores", "quality_scores_confidence", None),
        ("text_content", "text_content_confidence", None),
    ]

    for field_name, conf_key, _method_key in field_defs:
        confidence = data.get(conf_key, 0.0)
        if confidence is None:
            confidence = 0.0

        # Categorize by confidence
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


# ---------------------------------------------------------------------------
# Main integration logic
# ---------------------------------------------------------------------------
def integrate_sample(
    sample: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    mos_index: dict[str, dict[str, float]],
    res_to_ori: dict[str, str],
    egret_index: dict[str, list[dict[str, Any]]] | None = None,
    orphan_corrections: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create integrated enrichment data for a single sample.

    Returns a new enrichment version data dict with all sources merged.
    Layout priority: egret_xlarge > docling_gpu > v1 (DocLayout-YOLO).
    """
    filename = sample["source"]["original_filename"]
    original_path = sample["source"]["original_path"]
    width = sample["original_file"]["width_px"]
    height = sample["original_file"]["height_px"]
    dpi = sample["original_file"].get("dpi")

    is_ori = "/ori/" in original_path
    is_res = "/res/" in original_path

    # Get existing v1 data as baseline
    v1_data = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][0].get("data", {})

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # 1. Split (D01) - from path
    # -------------------------------------------------------------------
    split = "unknown"
    path_lower = original_path.lower()
    for split_name in ["train", "val", "test"]:
        if f"/{split_name}/" in path_lower or path_lower.startswith(f"{split_name}/"):
            split = split_name
            break
    data["split"] = split

    # -------------------------------------------------------------------
    # 2. Capture method (D02) - from ori/res path
    # -------------------------------------------------------------------
    if is_ori:
        data["capture_method"] = "camera_smartphone"
        data["capture_confidence"] = 0.95
        data["capture_detection_method"] = "parser_dociq_paper"
    elif is_res:
        data["capture_method"] = "synthetic"
        data["capture_confidence"] = 1.0
        data["capture_detection_method"] = "parser_dociq_paper"
    else:
        data["capture_method"] = "unknown"
        data["capture_confidence"] = 0.5
        data["capture_detection_method"] = "dataset_config"

    # -------------------------------------------------------------------
    # 3. Resolution (from original_file)
    # -------------------------------------------------------------------
    data["resolution_category"] = v1_data.get("resolution_category", "unknown")
    data["resolution_pixels"] = [width, height]

    # -------------------------------------------------------------------
    # 4. Domain (D05) - from LLM enrichment
    # -------------------------------------------------------------------
    llm = llm_index.get(filename)

    if llm:
        data["domain_level1"] = llm["domain_level1"]
        data["domain_confidence"] = llm["domain_confidence"]
        data["domain_detection_method"] = "llm_vision"
        data["domain_content_type"] = llm.get("content_type", "")
    elif is_res:
        # res/ images share domain with their ori/ counterpart
        # Use CSV-based res->ori mapping for accurate lookup
        ori_filename = res_to_ori.get(filename)
        ori_llm = llm_index.get(ori_filename) if ori_filename else None
        if ori_llm:
            data["domain_level1"] = ori_llm["domain_level1"]
            # Lower confidence since it's transferred from ori -> res
            data["domain_confidence"] = round(ori_llm["domain_confidence"] * 0.9, 4)
            data["domain_detection_method"] = "llm_vision_transferred_from_ori"
            data["domain_content_type"] = ori_llm.get("content_type", "")
        else:
            data["domain_level1"] = "UNK"
            data["domain_confidence"] = 0.3
            data["domain_detection_method"] = "none"
    else:
        data["domain_level1"] = "UNK"
        data["domain_confidence"] = 0.3
        data["domain_detection_method"] = "none"

    # -------------------------------------------------------------------
    # 5. Language & script (D04, D06) - from language enrichment + LLM
    # -------------------------------------------------------------------
    lang = lang_index.get(filename)

    if lang and lang.get("confidence", 0) >= 0.5:
        data["iso639_language"] = lang["language"]
        data["iso15924_script"] = lang["script"]
        data["language_confidence"] = lang["confidence"]
        data["text_scope_detection_method"] = "openlid_v2"
    elif llm:
        data["iso639_language"] = llm.get("iso639_language", "und")
        data["iso15924_script"] = llm.get("iso15924_script", "Zyyy")
        data["language_confidence"] = 0.8
        data["text_scope_detection_method"] = "llm_vision"
    elif lang:
        # Low confidence OpenLID result - still better than nothing
        data["iso639_language"] = lang["language"]
        data["iso15924_script"] = lang["script"]
        data["language_confidence"] = lang["confidence"]
        data["text_scope_detection_method"] = "openlid_v2_low_confidence"
    elif is_res:
        # Transfer language from ori counterpart via CSV mapping
        ori_filename = res_to_ori.get(filename)
        ori_lang = lang_index.get(ori_filename) if ori_filename else None
        ori_llm = llm_index.get(ori_filename) if ori_filename else None
        if ori_lang and ori_lang.get("confidence", 0) >= 0.5:
            data["iso639_language"] = ori_lang["language"]
            data["iso15924_script"] = ori_lang["script"]
            data["language_confidence"] = round(ori_lang["confidence"] * 0.9, 4)
            data["text_scope_detection_method"] = "openlid_v2_transferred_from_ori"
        elif ori_llm:
            data["iso639_language"] = ori_llm.get("iso639_language", "und")
            data["iso15924_script"] = ori_llm.get("iso15924_script", "Zyyy")
            data["language_confidence"] = 0.7
            data["text_scope_detection_method"] = "llm_vision_transferred_from_ori"
        else:
            data["iso639_language"] = "und"
            data["iso15924_script"] = "Zyyy"
            data["language_confidence"] = 0.0
            data["text_scope_detection_method"] = "none"
    else:
        data["iso639_language"] = "und"
        data["iso15924_script"] = "Zyyy"
        data["language_confidence"] = 0.0
        data["text_scope_detection_method"] = "none"

    # Script family (D04 fix)
    data["script_family"] = SCRIPT_FAMILY_MAPPING.get(
        data.get("iso15924_script", ""), "other"
    )

    # -------------------------------------------------------------------
    # 6. Layout detections (D07, D08) - egret_xlarge > docling_gpu > v1
    # -------------------------------------------------------------------
    egret_dets = (egret_index or {}).get(filename, [])
    layout_dets = layout_index.get(filename, [])

    if egret_dets:
        # Prefer egret-xlarge (17-class, per-detection confidence)
        data["layout_detections"] = egret_dets
        data["layout_source"] = "egret_xlarge"
        avg_conf = (
            sum(d.get("confidence", 0.9) for d in egret_dets) / len(egret_dets)
            if egret_dets
            else 0.9
        )
        data["layout_confidence"] = round(avg_conf, 4)
        data["layout_detection_count"] = len(egret_dets)

        flags = derive_content_flags(egret_dets)
        data["has_table"] = flags["has_table"]
        data["has_formula"] = flags["has_formula"]
        data["has_figure"] = flags["has_figure"]
        data["has_code"] = flags["has_code"]
        data["content_flags_tier"] = "tier_2_model"
        data["content_flags_source"] = "egret_xlarge"
        data["content_flags_confidence"] = round(avg_conf, 4)
    elif layout_dets:
        data["layout_detections"] = layout_dets
        data["layout_source"] = "docling_gpu"
        data["layout_confidence"] = 0.85
        data["layout_detection_count"] = len(layout_dets)

        flags = derive_content_flags(layout_dets)
        data["has_table"] = flags["has_table"]
        data["has_formula"] = flags["has_formula"]
        data["has_figure"] = flags["has_figure"]
        data["has_code"] = flags["has_code"]
        data["content_flags_tier"] = "tier_2_model"
        data["content_flags_source"] = "docling_gpu"
        data["content_flags_confidence"] = 0.85
    else:
        # Fall back to v1 layout detections if available
        v1_layout = v1_data.get("layout_detections", [])
        data["layout_detections"] = v1_layout
        data["layout_source"] = v1_data.get("content_flags_source", "doclayout_yolo")
        data["layout_confidence"] = 0.7
        data["layout_detection_count"] = len(v1_layout)

        flags = derive_content_flags(v1_layout)
        data["has_table"] = flags["has_table"]
        data["has_formula"] = flags["has_formula"]
        data["has_figure"] = flags["has_figure"]
        data["has_code"] = flags["has_code"]
        data["content_flags_tier"] = "tier_2_model"
        data["content_flags_source"] = v1_data.get(
            "content_flags_source", "doclayout_yolo"
        )
        data["content_flags_confidence"] = 0.7

    # Override content flags with LLM data (more reliable for has_handwriting)
    # For res/ images, transfer from their ori/ counterpart via CSV mapping
    llm_for_flags = llm
    if not llm_for_flags and is_res:
        ori_filename = res_to_ori.get(filename)
        llm_for_flags = llm_index.get(ori_filename) if ori_filename else None

    if llm_for_flags:
        if llm_for_flags.get("has_handwriting"):
            data["has_handwriting"] = True
        else:
            data["has_handwriting"] = data.get("has_handwriting", False)

        if llm_for_flags.get("has_table"):
            data["has_table"] = True
        if llm_for_flags.get("has_formula"):
            data["has_formula"] = True
        if llm_for_flags.get("has_figure"):
            data["has_figure"] = True
        if llm_for_flags.get("has_signature"):
            data["has_signature"] = True
    else:
        data["has_handwriting"] = data.get("has_handwriting", False)

    # -------------------------------------------------------------------
    # 7. Text content & statistics (D14, D15) - from OCR batches
    # -------------------------------------------------------------------
    ocr = ocr_index.get(filename)

    if ocr and ocr.get("success") and ocr.get("text"):
        data["text_content"] = ocr["text"]
        data["text_content_confidence"] = ocr.get("confidence", 0.8)
        data["text_content_source"] = "docling_gpu_ocr"
        data["text_statistics"] = compute_text_statistics(ocr["text"])
    else:
        data["text_content"] = ""
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # Text quality from OCR
    text_stats = data["text_statistics"]
    if text_stats["has_content"]:
        data["text_quality_confidence"] = min(data["text_content_confidence"], 0.8)
        data["text_quality_method"] = "docling_ocr"
        data["text_quality_provenance_tier"] = "tier_2_model"
    else:
        data["text_quality_confidence"] = 0.0
        data["text_quality_method"] = "none"
        data["text_quality_provenance_tier"] = "tier_3_heuristic"

    # -------------------------------------------------------------------
    # 8. Quality scores (D09) - from MOS CSVs
    # -------------------------------------------------------------------
    mos = mos_index.get(filename)

    if mos:
        data["quality_overall_mos"] = mos["overall"]
        data["quality_sharpness_mos"] = mos["sharpness"]
        data["quality_color_fidelity_mos"] = mos["color_fidelity"]
        data["quality_overall_normalized"] = mos_to_normalized(mos["overall"])
        data["quality_tier"] = mos_to_quality_tier(mos["overall"])
        data["quality_scores_confidence"] = 0.95
        data["quality_scores_source"] = "human_mos_itur_bt500"
    else:
        data["quality_scores_confidence"] = 0.0
        data["quality_scores_source"] = "none"

    # -------------------------------------------------------------------
    # 9. Geometric properties (D10) - from LLM enrichment
    # -------------------------------------------------------------------
    # For res/ images, transfer from ori/ counterpart
    llm_for_geo = llm
    if not llm_for_geo and is_res:
        ori_filename = res_to_ori.get(filename)
        llm_for_geo = llm_index.get(ori_filename) if ori_filename else None

    if llm_for_geo and llm_for_geo.get("orientation"):
        orientation_str = llm_for_geo["orientation"]
        if orientation_str == "portrait":
            data["orientation_class"] = 0
        elif orientation_str == "landscape":
            data["orientation_class"] = 90
        else:
            data["orientation_class"] = 0

        data["geometric_confidence"] = 0.85 if llm else 0.75
        data["geometric_source"] = (
            "llm_vision" if llm else "llm_vision_transferred_from_ori"
        )
    else:
        # Default: assume portrait based on dimensions
        if width < height:
            data["orientation_class"] = 0
        else:
            data["orientation_class"] = 90
        data["geometric_confidence"] = 0.6
        data["geometric_source"] = "dimension_heuristic"

    # -------------------------------------------------------------------
    # 10. Physical degradation (D11) - for ori/ images
    # -------------------------------------------------------------------
    if is_ori:
        data["physical_degradation_present"] = True
        data["physical_degradation_types"] = [
            "shadow",
            "occlusion",
            "blur",
            "creases",
            "moire",
        ]
        data["physical_degradation_note"] = (
            "DIQA-5000 ori/ images have real-world degradations. "
            "Specific distortion category per image requires lookup table "
            "not provided in the public dataset."
        )
        data["physical_degradation_confidence"] = 0.7
    else:
        data["physical_degradation_present"] = False
        data["physical_degradation_types"] = []
        data["physical_degradation_confidence"] = 0.9

    # -------------------------------------------------------------------
    # 11. Image properties (D13) - derived
    # -------------------------------------------------------------------
    data["image_properties_color_mode"] = "color"
    data["image_properties_document_age"] = "modern"
    data["image_properties_confidence"] = 0.95
    data["image_properties_source"] = "dataset_paper_ground_truth"

    # -------------------------------------------------------------------
    # 12. Paper size (D17) - estimated
    # -------------------------------------------------------------------
    data["paper_size"] = estimate_paper_size(width, height, dpi)

    # -------------------------------------------------------------------
    # 13. Handwriting assessment (D16) - from LLM
    # -------------------------------------------------------------------
    # For res/ images, transfer from ori/ counterpart
    llm_for_hw = llm
    if not llm_for_hw and is_res:
        ori_filename = res_to_ori.get(filename)
        llm_for_hw = llm_index.get(ori_filename) if ori_filename else None

    if llm_for_hw:
        data["handwriting_present"] = llm_for_hw.get("has_handwriting", False)
        data["handwriting_confidence"] = 0.85 if llm else 0.75
        data["handwriting_source"] = (
            "llm_vision" if llm else "llm_vision_transferred_from_ori"
        )
    else:
        data["handwriting_present"] = False
        data["handwriting_confidence"] = 0.5
        data["handwriting_source"] = "none"

    # -------------------------------------------------------------------
    # 14. LLM scores integration (D18)
    # -------------------------------------------------------------------
    # For res/ images, reference the ori/ LLM data
    llm_for_scores = llm
    if not llm_for_scores and is_res:
        ori_filename = res_to_ori.get(filename)
        llm_for_scores = llm_index.get(ori_filename) if ori_filename else None

    if llm_for_scores:
        data["llm_domain_level1"] = llm_for_scores.get("domain_level1")
        data["llm_domain_confidence"] = llm_for_scores.get("domain_confidence")
        data["llm_language"] = llm_for_scores.get("iso639_language")
        data["llm_script"] = llm_for_scores.get("iso15924_script")
        data["llm_content_type"] = llm_for_scores.get("content_type")
        data["llm_reasoning"] = llm_for_scores.get("reasoning", "")[:500]
        data["llm_model"] = llm_for_scores.get("model_used")
        data["llm_data_available"] = True
        data["llm_data_is_direct"] = llm is not None
    else:
        data["llm_data_available"] = False
        data["llm_data_is_direct"] = False

    # -------------------------------------------------------------------
    # 15. Dataset short code
    # -------------------------------------------------------------------
    data["dataset_short_code"] = "diqa-5000"

    # -------------------------------------------------------------------
    # 16. Text scope
    # -------------------------------------------------------------------
    data["text_scope_content_type"] = "printed"
    if data.get("has_handwriting"):
        data["text_scope_content_type"] = "mixed"

    # -------------------------------------------------------------------
    # Apply orphan corrections (manual overrides for missing enrichments)
    # -------------------------------------------------------------------
    if orphan_corrections and filename in orphan_corrections:
        corr = orphan_corrections[filename]
        data.update(corr)

    # -------------------------------------------------------------------
    # Compute reliability summary
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


def run_integration(
    metadata: dict[str, Any],
    llm_index: dict[str, dict[str, Any]],
    lang_index: dict[str, dict[str, Any]],
    layout_index: dict[str, list[dict[str, Any]]],
    ocr_index: dict[str, dict[str, Any]],
    mos_index: dict[str, dict[str, float]],
    res_to_ori: dict[str, str],
    egret_index: dict[str, list[dict[str, Any]]] | None = None,
    orphan_corrections: dict[str, dict[str, Any]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run integration across all samples."""
    samples = metadata["samples"]
    total = len(samples)

    # Statistics counters
    stats: dict[str, int] = Counter()

    log.info("Integrating enrichment data for %d samples ...", total)
    start = time.time()

    for idx, sample in enumerate(samples):
        filename = sample["source"]["original_filename"]

        # Create integrated enrichment data
        integrated_data = integrate_sample(
            sample,
            llm_index,
            lang_index,
            layout_index,
            ocr_index,
            mos_index,
            res_to_ori,
            egret_index,
            orphan_corrections,
        )

        # Track statistics
        if filename in llm_index:
            stats["llm_matched"] += 1
        if filename in lang_index:
            stats["lang_matched"] += 1
        if (egret_index or {}).get(filename):
            stats["egret_matched"] += 1
        if filename in layout_index:
            stats["layout_matched"] += 1
        if filename in ocr_index:
            stats["ocr_matched"] += 1
        if filename in mos_index:
            stats["mos_matched"] += 1

        # Track language source distribution
        lang_method = integrated_data.get("text_scope_detection_method", "none")
        stats[f"lang_source_{lang_method}"] += 1

        # Track domain source distribution
        domain_method = integrated_data.get("domain_detection_method", "none")
        stats[f"domain_source_{domain_method}"] += 1

        # Track split distribution
        split_val = integrated_data.get("split", "unknown")
        stats[f"split_{split_val}"] += 1

        rel = integrated_data.get("sample_reliability_summary", {})
        cat = rel.get("min_confidence_category", "unreliable")
        stats[f"reliability_{cat}"] += 1

        if not dry_run:
            # Fix split in source (D01)
            if integrated_data.get("split") != "unknown":
                sample["source"]["split"] = integrated_data["split"]

            # Fix original_labels with MOS scores (D03)
            if integrated_data.get("quality_overall_mos"):
                if not sample.get("original_labels"):
                    sample["original_labels"] = {}
                sample["original_labels"]["mos_overall"] = integrated_data[
                    "quality_overall_mos"
                ]
                sample["original_labels"]["mos_sharpness"] = integrated_data[
                    "quality_sharpness_mos"
                ]
                sample["original_labels"]["mos_color_fidelity"] = integrated_data[
                    "quality_color_fidelity_mos"
                ]

            # Create new enrichment version
            new_version = {
                "version": sample["enrichments"]["current_version"] + 1,
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": f"integrate_diqa_enrichments.py_v{SCRIPT_VERSION}",
                "method": "multi_source_integration",
                "description": (
                    "Integrated: LLM enrichment (domain, content), "
                    "OpenLID (language), egret-xlarge layout (preferred) + "
                    "Docling GPU fallback (layout, OCR), "
                    "MOS scores, paper ground truth"
                ),
                "script_version": SCRIPT_VERSION,
                "data": integrated_data,
            }

            sample["enrichments"]["versions"].append(new_version)
            sample["enrichments"]["current_version"] = new_version["version"]

        if (idx + 1) % 500 == 0:
            elapsed = time.time() - start
            rate = (idx + 1) / elapsed
            log.info(
                "  [%d/%d] %.0f samples/sec",
                idx + 1,
                total,
                rate,
            )

    elapsed = time.time() - start
    log.info("Integration complete in %.1f seconds", elapsed)

    # Update top-level metadata
    if not dry_run:
        # Recount splits
        split_counts: dict[str, int] = Counter()
        for s in samples:
            split_counts[s["source"]["split"]] += 1
        metadata["splits_included"] = sorted(split_counts.keys())
        metadata["split_counts"] = dict(split_counts)

    return dict(stats)


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(stats: dict[str, int], total: int) -> None:
    """Print integration summary."""
    print("\n" + "=" * 65)
    print("  DIQA-5000 Enrichment Integration Summary")
    print("=" * 65)
    print(f"  Total samples:       {total}")
    print("\n  Source match rates:")
    print(f"    LLM enrichment:    {stats.get('llm_matched', 0):>5d} / {total}")
    print(f"    Language (OpenLID): {stats.get('lang_matched', 0):>5d} / {total}")
    print(f"    Layout (egret):     {stats.get('egret_matched', 0):>5d} / {total}")
    print(f"    Layout (Docling):   {stats.get('layout_matched', 0):>5d} / {total}")
    print(f"    OCR (Docling):      {stats.get('ocr_matched', 0):>5d} / {total}")
    print(f"    MOS scores:         {stats.get('mos_matched', 0):>5d} / {total}")

    print("\n  Reliability distribution:")
    for cat in ["hard_label", "soft_label", "active_learning", "unreliable"]:
        count = stats.get(f"reliability_{cat}", 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"    {cat:<20s} {count:>5d}  ({pct:5.1f}%)")

    # Language source breakdown
    print("\n  Language source breakdown:")
    for key, count in sorted(stats.items()):
        if key.startswith("lang_source_"):
            method = key.replace("lang_source_", "")
            pct = count / total * 100
            print(f"    {method:<40s} {count:>5d}  ({pct:5.1f}%)")

    # Domain source breakdown
    print("\n  Domain source breakdown:")
    for key, count in sorted(stats.items()):
        if key.startswith("domain_source_"):
            method = key.replace("domain_source_", "")
            pct = count / total * 100
            print(f"    {method:<40s} {count:>5d}  ({pct:5.1f}%)")

    # Split breakdown
    print("\n  Split distribution:")
    for key, count in sorted(stats.items()):
        if key.startswith("split_"):
            split_name = key.replace("split_", "")
            pct = count / total * 100
            print(f"    {split_name:<20s} {count:>5d}  ({pct:5.1f}%)")

    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into DIQA-5000 metadata.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to diqa-5000_metadata.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input file)",
    )
    parser.add_argument(
        "--egret-dir",
        type=Path,
        default=EGRET_BATCH_DIR,
        help="Path to egret batch output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args()

    output_path = args.output or args.metadata

    # Load all data sources
    metadata = load_metadata(args.metadata)
    llm_index = load_llm_enrichment(LLM_ENRICHMENT_PATH)
    lang_index = load_language_enrichment(LANG_ENRICHMENT_PATH)
    layout_index = load_layout_batches(LAYOUT_BATCH_DIR)
    egret_index = load_egret_batches(args.egret_dir)
    ocr_index = load_ocr_batches(OCR_BATCH_DIR)
    mos_index, res_to_ori = load_mos_scores(DATASET_DIR)
    orphan_corr = load_orphan_corrections(ORPHAN_CORRECTIONS_PATH)

    # Run integration
    stats = run_integration(
        metadata=metadata,
        llm_index=llm_index,
        lang_index=lang_index,
        layout_index=layout_index,
        ocr_index=ocr_index,
        mos_index=mos_index,
        res_to_ori=res_to_ori,
        egret_index=egret_index if egret_index else None,
        orphan_corrections=orphan_corr if orphan_corr else None,
        dry_run=args.dry_run,
    )

    # Print summary
    print_summary(stats, len(metadata["samples"]))

    if args.dry_run:
        log.info("Dry run - no output written")
        return

    # Write output
    log.info("Writing integrated metadata to %s ...", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as fh:
        json.dump(metadata, fh, indent=2, ensure_ascii=False)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info("  Written %.1f MB", file_size_mb)
    log.info("Done.")


if __name__ == "__main__":
    main()
