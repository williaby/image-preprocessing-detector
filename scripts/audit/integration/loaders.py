"""Consolidated data loaders for integration scripts.

Each loader handles missing files gracefully (log warning, return empty
dict). All loaders index by filename stem (image_id) unless noted
otherwise.

Extracted from integration_script_template.py to eliminate copy-paste
across 52 integration scripts.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


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


def load_enrichment_by_image_id(
    path: Path,
    source_name: str,
    *,
    samples_key: str = "samples",
    id_key: str = "image_id",
) -> dict[str, dict[str, Any]]:
    """Load an enrichment file and index by image_id.

    Generic loader for JSON files with a list of records keyed by
    image_id. Covers LLM enrichment, language enrichment, and similar
    formats.

    Args:
        path: Path to enrichment JSON file.
        source_name: Human-readable source name for log messages.
        samples_key: Top-level key containing the records list.
        id_key: Key within each record containing the image identifier.

    Returns:
        Dict mapping image_id (filename stem) to enrichment record.
    """
    if not path.exists():
        log.warning("%s not found: %s", source_name, path)
        return {}
    log.info("Loading %s from %s", source_name, path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get(samples_key, []):
        image_id = rec.get(id_key, "")
        if image_id:
            index[image_id] = rec
    log.info("  Indexed %d %s records", len(index), source_name)
    return index


def load_llm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load LLM enrichment and index by image_id.

    Args:
        path: Path to *_llm_enrichment.json.

    Returns:
        Dict mapping image_id (filename stem) to enrichment record.
    """
    return load_enrichment_by_image_id(path, "LLM enrichment")


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment (OpenLID) and index by image_id.

    Args:
        path: Path to *_language_enrichment.json.

    Returns:
        Dict mapping image_id to language enrichment record.
    """
    return load_enrichment_by_image_id(path, "language enrichment")


def load_results_by_filename(
    path: Path,
    source_name: str,
    *,
    results_key: str = "results",
    path_key: str = "image_path",
) -> dict[str, dict[str, Any]]:
    """Load a results file and index by filename (with extension).

    Generic loader for JSON files with a list of measurement records
    keyed by image_path. Covers skew labels, resolution labels, and
    similar formats.

    Args:
        path: Path to results JSON file.
        source_name: Human-readable source name for log messages.
        results_key: Top-level key containing the results list.
        path_key: Key within each record containing the image path.

    Returns:
        Dict mapping filename (with extension) to measurement record.
    """
    if not path.exists():
        log.warning("%s not found: %s", source_name, path)
        return {}
    log.info("Loading %s from %s", source_name, path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    results = raw.get(results_key, [])
    index: dict[str, dict[str, Any]] = {}
    for rec in results:
        if rec.get("error"):
            continue
        image_path = rec.get(path_key, "")
        filename = Path(image_path).name
        if filename:
            index[filename] = rec
    log.info("  Indexed %d %s records", len(index), source_name)
    return index


def load_skew_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load skew/orientation labels and index by filename.

    Note: Indexed by full filename (with extension), not stem.

    Args:
        path: Path to *_skew_labels.json.

    Returns:
        Dict mapping filename to skew/orientation measurement.
    """
    return load_results_by_filename(path, "skew labels")


def load_resolution_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load resolution quality labels and index by filename.

    Args:
        path: Path to *_resolution_labels.json.

    Returns:
        Dict mapping filename to resolution quality measurement.
    """
    return load_results_by_filename(path, "resolution labels")


def load_vlm_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM enrichment and index by image stem.

    VLM enrichments are typically pre-indexed by image stem.

    Args:
        path: Path to VLM enrichment JSON.

    Returns:
        Dict mapping image stem to VLM enrichment record.
    """
    if not path.exists():
        log.warning("VLM enrichment not found: %s", path)
        return {}
    log.info("Loading VLM enrichment from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = raw.get("samples", {})
    log.info("  Indexed %d VLM records", len(index))
    return index


def load_train_gt(
    path: Path,
    *,
    samples_key: str = "samples",
    id_key: str = "image_id",
) -> dict[str, dict[str, Any]]:
    """Load dataset-specific ground truth annotations.

    The JSON structure and key names vary per dataset. Override
    samples_key and id_key for non-standard formats.

    Args:
        path: Path to ground truth annotation file.
        samples_key: Top-level key containing the records list.
        id_key: Key within each record containing the image identifier.

    Returns:
        Dict mapping image identifier to GT record.
    """
    return load_enrichment_by_image_id(
        path, "train GT", samples_key=samples_key, id_key=id_key
    )


def load_vlm_text_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load VLM text transcription labels and index by filename stem.

    Used by Phase 6.5 conditional text labeling when text_has_content
    pass rate is below 50%.

    Args:
        path: Path to VLM text labels JSON.

    Returns:
        Dict mapping filename stem to label record.
    """
    if not path.exists():
        log.warning("VLM text labels not found: %s", path)
        return {}
    log.info("Loading VLM text labels from %s", path)
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    index: dict[str, dict[str, Any]] = {}
    for rec in raw.get("labels", []):
        image_id = rec.get("image_id", "")
        stem = image_id.split("/")[-1] if "/" in image_id else image_id
        if stem:
            index[stem] = rec
    log.info("  Indexed %d VLM text label records", len(index))
    return index


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute basic text statistics from transcription text.

    Counts characters, words, lines, and script-specific characters.
    Includes Devanagari, CJK, Arabic, and Latin character detection.

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

    # Script-specific character patterns
    deva_chars = len(re.findall(r"[\u0900-\u097f]", clean_text))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", clean_text))
    arabic_chars = len(re.findall(r"[\u0600-\u06ff]", clean_text))
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

    # Only include script-specific counts if non-zero
    if deva_chars > 0:
        stats["devanagari_char_count"] = deva_chars
    if cjk_chars > 0:
        stats["cjk_char_count"] = cjk_chars
    if arabic_chars > 0:
        stats["arabic_char_count"] = arabic_chars
    if latin_words > 0:
        stats["latin_word_count"] = latin_words

    return stats
