#!/usr/bin/env python3
"""Shared utilities for Layer 2 metadata integration scripts.

Provides common helpers used across integrate_*.py scripts that write
enrichment data into L2 metadata JSON files.

Functions and constants in this module are extracted from the integrate_*
scripts to eliminate code duplication. Each integrate script should import
from here rather than defining its own copy.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants (identical across all integrate_* scripts)
# ---------------------------------------------------------------------------

# Full Docling lowercase -> DocLayNet PascalCase mapping.
# Covers core 11 DocLayNet classes plus Docling extensions (KI-001).
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

SCRIPT_TO_TEXT_DIRECTION: dict[str, str] = {"Arab": "rtl", "Hebr": "rtl"}

# Content flag class sets used by derive_content_flags()
TABLE_CLASSES: frozenset[str] = frozenset({"TABLE"})
FORMULA_CLASSES: frozenset[str] = frozenset({"FORMULA", "ISOLATE_FORMULA"})
FIGURE_CLASSES: frozenset[str] = frozenset({"PICTURE", "FIGURE", "CHART"})
CODE_CLASSES: frozenset[str] = frozenset({"CODE"})


def get_sample_filename(sample: dict[str, Any]) -> str | None:
    """Extract the original filename from a L2 metadata sample.

    Handles multiple field locations used across datasets.

    Args:
        sample: A single sample dict from the L2 metadata.

    Returns:
        The original filename string, or None if not found.
    """
    # Try source.original_filename first (standard L2 field)
    source = sample.get("source", {})
    filename = source.get("original_filename")
    if filename:
        return str(Path(filename).name)

    # Fallback: sample_id may contain the filename
    sample_id = sample.get("sample_id", "")
    if sample_id and "." in sample_id:
        return sample_id

    return None


def next_version_number(enrichments: dict[str, Any]) -> int:
    """Compute the next version number from the enrichments structure.

    Args:
        enrichments: The enrichments dict for a sample (contains
            ``current_version`` and ``versions`` keys).

    Returns:
        Integer version number to use for the new enrichment entry.
    """
    current_ver = enrichments.get("current_version")
    if isinstance(current_ver, int):
        return current_ver + 1
    if isinstance(current_ver, str):
        if current_ver.startswith("v"):
            try:
                return int(current_ver[1:]) + 1
            except ValueError:
                return len(enrichments.get("versions", [])) + 1
        if current_ver.isdigit():
            return int(current_ver) + 1
    return len(enrichments.get("versions", [])) + 1


# ---------------------------------------------------------------------------
# Data loaders (identical across all integrate_* scripts)
# ---------------------------------------------------------------------------


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


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id.

    Expected JSON structure: {"samples": [{"image_id": "...", ...}]}

    Args:
        path: Path to *_llm_enrichment.json.

    Returns:
        Dict mapping image_id (filename stem) to enrichment record.
    """
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
            index[image_id] = rec
    log.info("  Indexed %d LLM records", len(index))
    return index


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by image_id.

    Expected JSON structure: {"samples": [{"image_id": "...", ...}]}

    Args:
        path: Path to *_language_enrichment.json.

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


def load_skew_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load skew/orientation labels and index by filename.

    Expected JSON structure from label_skew_orientation.py:
      {"results": [{"image_path": "...", ...}], "metadata": {...}}

    Note: Indexed by full filename (with extension), not stem.

    Args:
        path: Path to *_skew_labels.json.

    Returns:
        Dict mapping filename to skew/orientation measurement.
    """
    if not path.exists():
        log.warning("Skew labels not found: %s", path)
        return {}
    log.info("Loading skew labels from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    results = raw.get("results", [])
    index: dict[str, dict[str, Any]] = {}
    for rec in results:
        if rec.get("error"):
            continue
        image_path = rec.get("image_path", "")
        filename = Path(image_path).name
        if filename:
            index[filename] = rec
    log.info("  Indexed %d skew records", len(index))
    return index


def load_resolution_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load resolution quality labels and index by filename.

    Expected JSON structure from label_resolution_quality.py:
      {"results": [{"image_path": "...", ...}], "metadata": {...}}

    Args:
        path: Path to *_resolution_labels.json.

    Returns:
        Dict mapping filename to resolution quality measurement.
    """
    if not path.exists():
        log.warning("Resolution labels not found: %s", path)
        return {}
    log.info("Loading resolution labels from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    results = raw.get("results", [])
    index: dict[str, dict[str, Any]] = {}
    for rec in results:
        if rec.get("error"):
            continue
        image_path = rec.get("image_path", "")
        filename = Path(image_path).name
        if filename:
            index[filename] = rec
    log.info("  Indexed %d resolution records", len(index))
    return index


# ---------------------------------------------------------------------------
# Computation helpers (identical across all integrate_* scripts)
# ---------------------------------------------------------------------------


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text.

    Counts characters, words, lines, and script-specific characters.

    Args:
        text: Raw transcription text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content,
        and avg_line_length. Script-specific counts included when
        non-zero.
    """
    if not text or text.strip() == "":
        return {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "has_content": False,
        }

    clean_text = text.strip()
    lines = clean_text.split("\n")
    non_empty_lines = [ln for ln in lines if ln.strip()]
    words = clean_text.split()

    deva_chars = len(re.findall(r"[\u0900-\u097f]", clean_text))
    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))

    avg_line_len = 0.0
    if non_empty_lines:
        avg_line_len = round(
            sum(len(ln.strip()) for ln in non_empty_lines) / len(non_empty_lines),
            1,
        )

    stats: dict[str, Any] = {
        "char_count": len(clean_text),
        "word_count": len(words),
        "line_count": len(non_empty_lines),
        "has_content": True,
        "avg_line_length": avg_line_len,
    }

    if deva_chars > 0:
        stats["devanagari_char_count"] = deva_chars
    if latin_words > 0:
        stats["latin_word_count"] = latin_words

    return stats


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
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
