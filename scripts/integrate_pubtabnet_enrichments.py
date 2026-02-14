#!/usr/bin/env python3
"""Integrate all enrichment sources into PubTabNet Layer 2 metadata.

Resolves 10 defects (D01-D10) identified during audit Phase 1-3:
  D01: split="unknown" -> infer from source.original_path
  D02: script_family="ltr" -> re-derive via get_script_family() (KI-008)
  D03: layout_detections empty -> load from extracted COCO batches
  D04: text_has_content=False -> load GT text from OCR batches
  D05: orientation_class missing -> set 0 (born-digital)
  D06: color_mode missing -> derive from original_file.color_space
  D07: handwriting_present missing -> alias has_handwriting
  D08: text_direction missing -> set "ltr" (v2.3.0)
  D09: text_directions_present missing -> set ["ltr"] (v2.3.0)
  D10: content_flags_confidence missing -> set 1.0

Data sources:
  1. Base metadata (519K samples, schema v2.1)
  2. Language enrichment (1K partial, iso639/iso15924)
  3. Extracted layout (5,100 COCO batch files, table_cell bboxes)
  4. Extracted OCR (JSONL batch files, GT cell text)

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_pubtabnet_enrichments.py --dry-run

    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \\
        uv run python3 scripts/integrate_pubtabnet_enrichments.py
"""

from __future__ import annotations

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
# Configuration
# ===================================================================
DATASET_NAME = "pubtabnet"
IS_SYNTHETIC_DATASET = False
KNOWN_CAPTURE_METHOD = "born_digital"

REGISTRY_DIR = Path("/mnt/e/image_detection/metadata_registry")
METADATA_PATH = REGISTRY_DIR / "json" / "pubtabnet_metadata.json"
LANGUAGE_ENRICHMENT_PATH = REGISTRY_DIR / "json" / "pubtabnet_language_enrichment.json"
LAYOUT_BATCH_DIR = REGISTRY_DIR / "extracted" / "pubtabnet"
OCR_BATCH_DIR = REGISTRY_DIR / "extracted" / "pubtabnet"

SCRIPT_VERSION = "1.0.0"
ENRICHMENT_VERSION_TAG = "integrated_v2"
ENRICHMENT_VERSION_NUMBER = 2

# Color space to color mode mapping
COLOR_SPACE_TO_MODE: dict[str, str] = {
    "RGB": "color",
    "RGBA": "color",
    "L": "grayscale",
    "1": "binarized",
    "P": "color",
    "CMYK": "color",
}


# ===================================================================
# Data loaders
# ===================================================================
def load_metadata(path: Path) -> dict[str, Any]:
    """Load Layer 2 metadata JSON.

    Args:
        path: Path to pubtabnet_metadata.json.

    Returns:
        Full metadata dict with "samples" list.
    """
    log.info("Loading metadata from %s (this may take a moment for 2.6GB)...", path)
    start = time.monotonic()
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    elapsed = time.monotonic() - start
    log.info("  Loaded %d samples in %.1fs", len(data.get("samples", [])), elapsed)
    return data


def load_language_enrichment(path: Path) -> dict[str, dict[str, Any]]:
    """Load language enrichment and index by image_id.

    Args:
        path: Path to pubtabnet_language_enrichment.json.

    Returns:
        Dict mapping image_id to language record.
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


class LazyLayoutIndex:
    """Memory-efficient layout index with on-demand batch loading.

    Instead of loading all annotations into memory (~12GB for 519K images),
    builds a lightweight filename -> batch_index mapping (~50MB), then loads
    individual batch files on-demand with an LRU cache.

    Attributes:
        batch_files: Sorted list of layout batch file paths.
        filename_to_batch: Mapping of image filename to batch file index.
    """

    def __init__(self, batch_dir: Path, cache_size: int = 10) -> None:
        self.batch_files: list[Path] = []
        self.filename_to_batch: dict[str, int] = {}
        self._cache: dict[int, dict[str, list[dict[str, Any]]]] = {}
        self._cache_order: list[int] = []
        self._max_cache = cache_size
        self._total_annotations = 0

        if not batch_dir.exists():
            log.warning("Layout batch directory not found: %s", batch_dir)
            return

        self.batch_files = sorted(batch_dir.glob("layout_batch_*.json"))
        if not self.batch_files:
            log.warning("No layout_batch_*.json files in %s", batch_dir)
            return

        self._build_index()

    def _build_index(self) -> None:
        """Build lightweight filename -> batch_index mapping.

        Parses each batch to extract image filenames and annotation counts,
        but does NOT retain annotation data in memory.
        """
        log.info(
            "Building layout index from %d batch files (lightweight pass)...",
            len(self.batch_files),
        )
        start = time.monotonic()

        for batch_idx, batch_path in enumerate(self.batch_files):
            with open(batch_path, encoding="utf-8") as f:
                batch = json.load(f)

            for img in batch.get("images", []):
                self.filename_to_batch[img["file_name"]] = batch_idx

            self._total_annotations += len(batch.get("annotations", []))

            # Free batch data immediately
            del batch

            if (batch_idx + 1) % 500 == 0:
                log.info(
                    "  Indexed %d/%d layout batches...",
                    batch_idx + 1,
                    len(self.batch_files),
                )

        elapsed = time.monotonic() - start
        log.info(
            "  Index built: %d images, %d annotations tracked, in %.1fs",
            len(self.filename_to_batch),
            self._total_annotations,
            elapsed,
        )

    def _load_batch(self, batch_idx: int) -> dict[str, list[dict[str, Any]]]:
        """Load a single batch file and return filename -> annotations mapping.

        Uses LRU eviction when cache is full.

        Args:
            batch_idx: Index into self.batch_files.

        Returns:
            Dict mapping filename to list of annotation dicts for this batch.
        """
        if batch_idx in self._cache:
            return self._cache[batch_idx]

        # Evict oldest cached batch if at capacity
        while len(self._cache) >= self._max_cache:
            oldest = self._cache_order.pop(0)
            del self._cache[oldest]

        batch_path = self.batch_files[batch_idx]
        with open(batch_path, encoding="utf-8") as f:
            batch = json.load(f)

        id_to_filename: dict[int, str] = {}
        for img in batch.get("images", []):
            id_to_filename[img["id"]] = img["file_name"]

        result: dict[str, list[dict[str, Any]]] = {}
        for ann in batch.get("annotations", []):
            fn = id_to_filename.get(ann.get("image_id"))
            if fn:
                result.setdefault(fn, []).append(ann)

        self._cache[batch_idx] = result
        self._cache_order.append(batch_idx)
        return result

    def get(self, filename: str) -> list[dict[str, Any]]:
        """Get annotations for a given image filename.

        Args:
            filename: Image filename to look up.

        Returns:
            List of annotation dicts (empty if not found).
        """
        batch_idx = self.filename_to_batch.get(filename)
        if batch_idx is None:
            return []
        batch_data = self._load_batch(batch_idx)
        return batch_data.get(filename, [])

    def __contains__(self, filename: str) -> bool:
        return filename in self.filename_to_batch

    def __len__(self) -> int:
        return len(self.filename_to_batch)


def load_layout_index(batch_dir: Path) -> LazyLayoutIndex:
    """Create a memory-efficient lazy layout index.

    Args:
        batch_dir: Directory containing layout_batch_*.json files.

    Returns:
        LazyLayoutIndex with on-demand batch loading.
    """
    return LazyLayoutIndex(batch_dir)


def load_ocr_batches(batch_dir: Path) -> dict[str, dict[str, Any]]:
    """Load OCR batch files and pre-compute text statistics per image.

    Pre-computes text_statistics during loading to avoid storing full text
    strings in memory (saves ~500MB for 509K samples).

    Args:
        batch_dir: Directory containing ocr_batch_*.jsonl files.

    Returns:
        Dict mapping image filename to pre-computed OCR summary with
        keys: confidence, text_statistics, text_has_content.
    """
    if not batch_dir.exists():
        log.warning("OCR batch directory not found: %s", batch_dir)
        return {}

    batch_files = sorted(batch_dir.glob("ocr_batch_*.jsonl"))
    log.info("Loading %d OCR batch files from %s", len(batch_files), batch_dir)

    index: dict[str, dict[str, Any]] = {}
    start = time.monotonic()

    for i, batch_path in enumerate(batch_files):
        with open(batch_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                source = rec.get("source", "")
                text = rec.get("text", "")
                if source and rec.get("success") and text:
                    # Pre-compute text statistics; discard raw text
                    index[source] = {
                        "confidence": rec.get("confidence", 1.0),
                        "text_statistics": compute_text_statistics(text),
                        "text_has_content": True,
                    }

        if (i + 1) % 500 == 0:
            log.info("  Processed %d/%d OCR batch files...", i + 1, len(batch_files))

    elapsed = time.monotonic() - start
    log.info("  Indexed %d OCR records in %.1fs", len(index), elapsed)
    return index


# ===================================================================
# Derivation helpers
# ===================================================================
def infer_split(original_path: str) -> str:
    """Infer dataset split from the original file path.

    PubTabNet paths follow: pubtabnet/{split}/{filename}.png
    where split is train, val, or test.

    Args:
        original_path: The source.original_path field value.

    Returns:
        Split name ("train", "val", "test") or "unknown".
    """
    parts = Path(original_path).parts
    # Expect: ("pubtabnet", "train"|"val"|"test", "filename.png")
    if len(parts) >= 2:
        candidate = parts[-2].lower()
        if candidate in ("train", "val", "test"):
            return candidate
    # Fallback: search all parts
    for part in parts:
        if part.lower() in ("train", "val", "test"):
            return part.lower()
    return "unknown"


def compute_text_statistics(text: str) -> dict[str, Any]:
    """Compute text statistics from consolidated cell text.

    Args:
        text: Consolidated table text content.

    Returns:
        Dict with char_count, word_count, line_count, has_content,
        avg_line_length, latin_word_count.
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

    latin_words = len(re.findall(r"[a-zA-Z]+", clean_text))
    digit_count = len(re.findall(r"\d", clean_text))

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

    if latin_words > 0:
        stats["latin_word_count"] = latin_words
    if digit_count > 0:
        stats["digit_count"] = digit_count

    return stats


def compute_reliability_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sample_reliability_summary for an enrichment data dict.

    Assesses field groups and produces reliability tiers based on
    confidence thresholds.

    Args:
        data: The enrichment data dict being built for this sample.

    Returns:
        Reliability summary dict.
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


# ===================================================================
# Per-sample integration
# ===================================================================
def integrate_sample(
    sample: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
    layout_annotations: list[dict[str, Any]],
    ocr_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Create integrated enrichment data for a single PubTabNet sample.

    Addresses all 10 audit defects (D01-D10).

    Args:
        sample: A single sample from the L2 metadata "samples" list.
        lang_index: Language enrichment index (image_id -> record).
        layout_annotations: Pre-resolved list of layout annotations for this sample.
        ocr_index: OCR text index (filename -> record).

    Returns:
        New enrichment data dict with all sources merged.
    """
    filename = sample["source"]["original_filename"]
    original_path = sample["source"].get("original_path", "")

    # Get existing V1 enrichment data for fallback
    v1_data: dict[str, Any] = {}
    if sample["enrichments"]["versions"]:
        v1_data = sample["enrichments"]["versions"][-1].get("data", {})

    # Language enrichment lookup (1K partial)
    # Language enrichment indexed by image_id (includes .png extension)
    lang_enrichment = lang_index.get(filename)

    data: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # D01: SPLIT (infer from source.original_path)
    # -------------------------------------------------------------------
    data["split"] = infer_split(original_path)

    # -------------------------------------------------------------------
    # CAPTURE METHOD (born-digital, from documentation)
    # -------------------------------------------------------------------
    data["capture_method"] = KNOWN_CAPTURE_METHOD
    data["capture_confidence"] = 1.0
    data["capture_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # DOMAIN (SCI, from documentation)
    # -------------------------------------------------------------------
    data["domain_level1"] = "SCI"
    data["domain_confidence"] = 1.0
    data["domain_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # LANGUAGE / SCRIPT (from V1 or language enrichment)
    # -------------------------------------------------------------------
    if lang_enrichment:
        data["iso639_language"] = lang_enrichment.get("language", "en")
        data["iso15924_script"] = lang_enrichment.get("script", "Latn")
        data["language_confidence"] = min(lang_enrichment.get("confidence", 0.5), 0.70)
        data["text_scope_detection_method"] = "openlid_v2"
    else:
        # Fallback to V1 data (en/Latn from dataset_config)
        data["iso639_language"] = v1_data.get("iso639_language", "en")
        data["iso15924_script"] = v1_data.get("iso15924_script", "Latn")
        data["language_confidence"] = v1_data.get(
            "language_confidence",
            0.80,  # Dataset is known English scientific
        )
        data["text_scope_detection_method"] = v1_data.get(
            "text_scope_detection_method", "dataset_documentation"
        )

    # -------------------------------------------------------------------
    # D02: SCRIPT FAMILY (re-derive from iso15924_script, KI-008 fix)
    # -------------------------------------------------------------------
    data["script_family"] = _get_script_family(data["iso15924_script"])

    # -------------------------------------------------------------------
    # D03: LAYOUT DETECTIONS (from extracted COCO batches)
    # -------------------------------------------------------------------
    layout_count = len(layout_annotations)

    # Store layout summary only (full cell detections in extracted COCO batches)
    # This avoids storing ~25M annotation dicts in memory / on disk
    data["layout_detections"] = (
        [
            {
                "class_name": "table_cell",
                "canonical_class": "TABLE_CELL",
                "source_label": "table_cell",
                "count": layout_count,
            }
        ]
        if layout_count > 0
        else []
    )
    data["layout_source"] = "pubtabnet_gt"
    data["layout_confidence"] = 1.0 if layout_count > 0 else 0.0
    data["layout_detection_count"] = layout_count
    data["layout_detections_ref"] = (
        "metadata_registry/extracted/pubtabnet/layout_batch_*.json"
    )

    # -------------------------------------------------------------------
    # CONTENT FLAGS (by construction - 100% table dataset)
    # -------------------------------------------------------------------
    data["has_table"] = True
    data["has_formula"] = v1_data.get("has_formula", False)
    data["has_figure"] = v1_data.get("has_figure", False)
    data["has_handwriting"] = False  # Born-digital scientific
    data["has_signature"] = False
    data["has_code"] = False

    data["content_flags_tier"] = "tier_0_exact"
    data["content_flags_source"] = "dataset_construction"
    # D10: content_flags_confidence
    data["content_flags_confidence"] = 1.0

    # D07: handwriting_present alias
    data["handwriting_present"] = data["has_handwriting"]

    # -------------------------------------------------------------------
    # D05: ORIENTATION (born-digital, no rotation)
    # -------------------------------------------------------------------
    data["orientation_class"] = 0
    data["orientation_confidence"] = 1.0
    data["orientation_detection_method"] = "dataset_documentation"

    # -------------------------------------------------------------------
    # D04: TEXT CONTENT (from GT OCR batches)
    # -------------------------------------------------------------------
    ocr_rec = ocr_index.get(filename)
    if ocr_rec and ocr_rec.get("text_has_content"):
        data["text_has_content"] = True
        data["text_content_confidence"] = ocr_rec.get("confidence", 1.0)
        data["text_content_source"] = "ground_truth_cell_text"
        data["text_statistics"] = ocr_rec["text_statistics"]
    else:
        data["text_has_content"] = False
        data["text_content_confidence"] = 0.0
        data["text_content_source"] = "none"
        data["text_statistics"] = compute_text_statistics("")

    # -------------------------------------------------------------------
    # TEXT SCOPE
    # -------------------------------------------------------------------
    data["text_scope"] = v1_data.get("text_scope", "page")
    data["text_scope_content_type"] = v1_data.get("text_scope_content_type", "printed")

    # -------------------------------------------------------------------
    # D06: IMAGE PROPERTIES COLOR MODE
    # -------------------------------------------------------------------
    color_space = sample.get("original_file", {}).get("color_space", "RGB")
    data["image_properties_color_mode"] = COLOR_SPACE_TO_MODE.get(color_space, "color")

    # -------------------------------------------------------------------
    # RESOLUTION (preserve V1 values)
    # -------------------------------------------------------------------
    for field in (
        "resolution_category",
        "resolution_pixels",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # D08, D09: TEXT DIRECTION (v2.3.0 fields)
    # -------------------------------------------------------------------
    data["text_direction"] = "ltr"
    data["text_directions_present"] = ["ltr"]

    # -------------------------------------------------------------------
    # TEXT QUALITY (preserve V1 values)
    # -------------------------------------------------------------------
    for field in (
        "text_quality_confidence",
        "text_quality_is_soft_label",
        "text_quality_method",
        "text_quality_provenance_tier",
    ):
        if field in v1_data:
            data[field] = v1_data[field]

    # -------------------------------------------------------------------
    # DATASET SHORT CODE
    # -------------------------------------------------------------------
    data["dataset_short_code"] = DATASET_NAME

    # -------------------------------------------------------------------
    # RELIABILITY SUMMARY (must be last)
    # -------------------------------------------------------------------
    data["sample_reliability_summary"] = compute_reliability_summary(data)

    return data


# ===================================================================
# Integration runner
# ===================================================================
def _init_stats() -> dict[str, Any]:
    """Create empty stats tracking dict."""
    return {
        "total": 0,
        "integrated": 0,
        "lang_matched": 0,
        "layout_matched": 0,
        "ocr_matched": 0,
        "has_text_content_count": 0,
        "split_dist": Counter(),
        "lang_dist": Counter(),
        "script_family_dist": Counter(),
        "color_mode_dist": Counter(),
        "lang_method_dist": Counter(),
    }


def _process_one_sample(
    sample: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
    layout_annotations: list[dict[str, Any]],
    ocr_index: dict[str, dict[str, Any]],
    stats: dict[str, Any],
    dry_run: bool,
    now: str,
) -> None:
    """Integrate one sample, update stats, and optionally write enrichment.

    Args:
        sample: Metadata sample dict (mutated in-place if not dry_run).
        lang_index: Language enrichment index.
        layout_annotations: Pre-resolved layout annotations for this sample.
        ocr_index: OCR text index.
        stats: Stats dict to update.
        dry_run: If True, skip writing enrichment version.
        now: ISO timestamp for created_at.
    """
    filename = sample["source"]["original_filename"]

    integrated_data = integrate_sample(
        sample, lang_index, layout_annotations, ocr_index
    )

    stats["total"] += 1
    stats["integrated"] += 1
    if filename in lang_index:
        stats["lang_matched"] += 1
    if layout_annotations:
        stats["layout_matched"] += 1
    if filename in ocr_index:
        stats["ocr_matched"] += 1
    if integrated_data.get("text_has_content"):
        stats["has_text_content_count"] += 1

    stats["split_dist"][integrated_data.get("split", "unknown")] += 1
    stats["lang_dist"][integrated_data.get("iso639_language", "und")] += 1
    stats["script_family_dist"][integrated_data.get("script_family", "unknown")] += 1
    stats["color_mode_dist"][
        integrated_data.get("image_properties_color_mode", "unknown")
    ] += 1
    stats["lang_method_dist"][
        integrated_data.get("text_scope_detection_method", "unknown")
    ] += 1

    if not dry_run:
        new_version = {
            "version": ENRICHMENT_VERSION_NUMBER,
            "created_at": now,
            "created_by": "integrate_pubtabnet_enrichments.py",
            "method": "tier_2_model",
            "description": (
                f"Integrated enrichment {ENRICHMENT_VERSION_TAG}: "
                "dataset documentation + extracted layout GT "
                "+ extracted OCR GT + language enrichment"
            ),
            "script_version": SCRIPT_VERSION,
            "data": integrated_data,
        }
        versions = sample["enrichments"]["versions"]
        replaced = False
        for j, ver in enumerate(versions):
            if ver.get("version") == ENRICHMENT_VERSION_NUMBER:
                versions[j] = new_version
                replaced = True
                break
        if not replaced:
            versions.append(new_version)
        sample["enrichments"]["current_version"] = ENRICHMENT_VERSION_NUMBER


def run_integration(
    metadata: dict[str, Any],
    lang_index: dict[str, dict[str, Any]],
    layout_batch_dir: Path,
    ocr_index: dict[str, dict[str, Any]],
    dry_run: bool = False,
    limit: int = 0,
) -> dict[str, Any]:
    """Run batch-oriented integration for all samples.

    Processes layout batches sequentially (each file read once) to avoid
    random I/O over network mounts. Samples without layout data are
    processed in a second pass.

    Args:
        metadata: Full L2 metadata dict.
        lang_index: Language enrichment index.
        layout_batch_dir: Directory with layout_batch_*.json files.
        ocr_index: OCR text index.
        dry_run: If True, compute stats without modifying metadata.
        limit: If >0, process only this many samples (for testing).

    Returns:
        Stats dict with counts and distributions.
    """
    stats = _init_stats()
    now = datetime.now(UTC).isoformat()
    total_samples = len(metadata["samples"])
    start = time.monotonic()

    # Build filename -> sample index mapping
    log.info("Building filename -> sample index for %d samples...", total_samples)
    filename_to_idx: dict[str, int] = {}
    for i, sample in enumerate(metadata["samples"]):
        fn = sample["source"]["original_filename"]
        filename_to_idx[fn] = i

    # Phase 1: Process samples WITH layout data (batch-oriented, sequential I/O)
    processed: set[int] = set()
    batch_files = sorted(layout_batch_dir.glob("layout_batch_*.json"))
    log.info(
        "Phase 1: Processing %d layout batches sequentially...",
        len(batch_files),
    )

    for batch_num, batch_path in enumerate(batch_files):
        with open(batch_path, encoding="utf-8") as f:
            batch = json.load(f)

        # Build image_id -> filename for this batch
        id_to_fn: dict[int, str] = {}
        for img in batch.get("images", []):
            id_to_fn[img["id"]] = img["file_name"]

        # Group annotations by filename
        local_annotations: dict[str, list[dict[str, Any]]] = {}
        for ann in batch.get("annotations", []):
            fn = id_to_fn.get(ann.get("image_id"))
            if fn:
                local_annotations.setdefault(fn, []).append(ann)

        # Free raw batch data
        del batch

        # Process matching samples
        for fn, annotations in local_annotations.items():
            idx = filename_to_idx.get(fn)
            if idx is not None:
                if limit > 0 and stats["total"] >= limit:
                    break
                sample = metadata["samples"][idx]
                _process_one_sample(
                    sample,
                    lang_index,
                    annotations,
                    ocr_index,
                    stats,
                    dry_run,
                    now,
                )
                processed.add(idx)

        if limit > 0 and stats["total"] >= limit:
            break

        if (batch_num + 1) % 500 == 0:
            elapsed = time.monotonic() - start
            rate = stats["total"] / elapsed if elapsed > 0 else 0
            log.info(
                "  Batch %d/%d: %d samples processed (%.0f/sec)",
                batch_num + 1,
                len(batch_files),
                stats["total"],
                rate,
            )

    phase1_count = stats["total"]
    phase1_elapsed = time.monotonic() - start
    log.info(
        "Phase 1 complete: %d samples with layout in %.1fs (%.0f/sec)",
        phase1_count,
        phase1_elapsed,
        phase1_count / phase1_elapsed if phase1_elapsed > 0 else 0,
    )

    # Phase 2: Process remaining samples WITHOUT layout data
    remaining = total_samples - len(processed)
    if limit > 0:
        remaining = min(remaining, limit - stats["total"])
    log.info("Phase 2: Processing %d samples without layout data...", remaining)

    phase2_start = time.monotonic()
    for i, sample in enumerate(metadata["samples"]):
        if i in processed:
            continue
        if limit > 0 and stats["total"] >= limit:
            break
        _process_one_sample(
            sample,
            lang_index,
            [],
            ocr_index,
            stats,
            dry_run,
            now,
        )

        done_phase2 = stats["total"] - phase1_count
        if done_phase2 > 0 and done_phase2 % 5000 == 0:
            elapsed = time.monotonic() - phase2_start
            rate = done_phase2 / elapsed if elapsed > 0 else 0
            log.info(
                "  Phase 2: %d/%d no-layout samples (%.0f/sec)",
                done_phase2,
                remaining,
                rate,
            )

    total_elapsed = time.monotonic() - start
    log.info(
        "Integration complete: %d total samples in %.1fs (%.0f/sec)",
        stats["total"],
        total_elapsed,
        stats["total"] / total_elapsed if total_elapsed > 0 else 0,
    )

    return stats


# ===================================================================
# Summary printer
# ===================================================================
def print_summary(stats: dict[str, Any], total_samples: int) -> None:
    """Print integration summary.

    Args:
        stats: Stats dict from run_integration().
        total_samples: Total sample count.
    """
    safe_total = max(total_samples, 1)

    print("\n" + "=" * 60)
    print(f"{DATASET_NAME} Enrichment Integration Summary")
    print("=" * 60)
    print(f"Total samples:        {stats['total']:,}")
    print(f"Integrated:           {stats['integrated']:,}")
    print(f"Language matched:     {stats['lang_matched']:,}")
    print(f"Layout matched:       {stats['layout_matched']:,}")
    print(f"OCR matched:          {stats['ocr_matched']:,}")
    print(f"Has text content:     {stats['has_text_content_count']:,}")
    print()

    print("Split distribution:")
    for split, count in stats["split_dist"].most_common():
        print(f"  {split:20s}: {count:>8,}")
    print()

    print("Language distribution (top 10):")
    for lang, count in stats["lang_dist"].most_common(10):
        pct = count / safe_total * 100
        print(f"  {lang:20s}: {count:>8,} ({pct:.1f}%)")
    print()

    print("Script family distribution:")
    for sf, count in stats["script_family_dist"].most_common():
        pct = count / safe_total * 100
        print(f"  {sf:20s}: {count:>8,} ({pct:.1f}%)")
    print()

    print("Color mode distribution:")
    for cm, count in stats["color_mode_dist"].most_common():
        print(f"  {cm:20s}: {count:>8,}")
    print()

    print("Language method distribution:")
    for method, count in stats["lang_method_dist"].most_common():
        print(f"  {method:30s}: {count:>8,}")
    print("=" * 60)


# ===================================================================
# CLI
# ===================================================================
def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description="Integrate all enrichment sources into PubTabNet metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=METADATA_PATH,
        help="Path to metadata JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input)",
    )
    parser.add_argument(
        "--language-enrichment",
        type=Path,
        default=LANGUAGE_ENRICHMENT_PATH,
        help="Path to language enrichment JSON",
    )
    parser.add_argument(
        "--layout-batch-dir",
        type=Path,
        default=LAYOUT_BATCH_DIR,
        help="Directory with layout_batch_*.json files",
    )
    parser.add_argument(
        "--ocr-batch-dir",
        type=Path,
        default=OCR_BATCH_DIR,
        help="Directory with ocr_batch_*.jsonl files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N samples (for testing, 0=all)",
    )
    args = parser.parse_args()

    output_path: Path = args.output or args.metadata

    # Load all data sources
    if not args.metadata.is_file():
        log.error("Metadata file not found: %s", args.metadata)
        return 1

    metadata = load_metadata(args.metadata)
    lang_index = load_language_enrichment(args.language_enrichment)
    # Layout batches loaded on-demand in batch-oriented processing
    ocr_index = load_ocr_batches(args.ocr_batch_dir)

    # Run batch-oriented integration
    start = time.monotonic()
    stats = run_integration(
        metadata=metadata,
        lang_index=lang_index,
        layout_batch_dir=args.layout_batch_dir,
        ocr_index=ocr_index,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    elapsed = time.monotonic() - start

    print_summary(stats, len(metadata["samples"]))
    log.info(
        "Integration completed in %.1f seconds (%.0f samples/sec)",
        elapsed,
        stats["total"] / elapsed if elapsed > 0 else 0,
    )

    # Update metadata header
    if not args.dry_run:
        metadata["schema_version"] = "2.3.0"
        metadata["splits_included"] = sorted(stats["split_dist"].keys())
        metadata["split_counts"] = dict(stats["split_dist"])

    # Write output
    if args.dry_run:
        log.info("Dry run -- no output written")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s (this may take a moment)...", output_path)
        write_start = time.monotonic()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False)
        write_elapsed = time.monotonic() - write_start
        log.info(
            "  Written %d samples in %.1fs", len(metadata["samples"]), write_elapsed
        )

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
