#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Assemble a per-field comparison of enrichment sources for any dataset.

Generic version of ``assemble_diqa_comparison.py``.  Auto-discovers
available enrichment sources from the ``audit_config`` registry and the
filesystem, compares field values pairwise across all present sources,
and outputs a structured JSON report.

Sources auto-discovered (each is optional):

    l2_metadata         Primary Layer 2 metadata (config.metadata_json_path)
    llm_enrichment      LLM enrichment (config.llm_enrichment_path)
    language_enrichment Language enrichment (config.language_enrichment_path)
    docling_layout      Docling GPU COCO layout batches
    egret_layout        Egret layout results
    visual_gt           Visual ground truth
    resolution_quality  Resolution quality labels

Usage::

    python -m scripts.audit.assemble_comparison --dataset diqa-5000
    python -m scripts.audit.assemble_comparison --dataset funsd --verbose
    python -m scripts.audit.assemble_comparison --dataset doclaynet \\
        --fields capture_method domain_level1 has_table --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.audit.audit_config import (
    PROJECT_ROOT,
    DatasetAuditConfig,
    list_known_datasets,
    load_dataset_config,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_EXTRACTED_ROOT = Path("/mnt/e/image_detection/metadata_registry/extracted")
AUDIT_RESULTS_ROOT = PROJECT_ROOT / "scripts" / "audit" / "results"
RESULTS_ROOT = PROJECT_ROOT / "results"

# Default comparison fields (order preserved for report readability).
DEFAULT_COMPARISON_FIELDS: list[str] = [
    "capture_method",
    "domain_level1",
    "iso639_language",
    "script_family",
    "orientation_class",
    "has_table",
    "has_formula",
    "has_figure",
    "has_handwriting",
    "layout_class_count",
    "color_mode",
    "physical_degradation",
    "split",
]

CONTENT_FLAG_FIELDS: frozenset[str] = frozenset(
    {"has_table", "has_formula", "has_figure", "has_handwriting"}
)

_NOT_CONFIGURED = "not configured"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _image_id_from_filename(filename: str) -> str:
    """Derive image_id from a filename like ``test_ori_00001.jpg``."""
    return Path(filename).stem


def _id_variants(image_id: str, dataset: str = "") -> list[str]:
    """Return candidate lookup keys for *image_id*.

    Different enrichment sources use different ID conventions:
    - L2 metadata ``id``: ``{dataset}_{original_filename}``
    - LLM / generic: ``{original_filename_stem}``
    - Sample-set ``sample_id``: same as L2 ``id``

    This helper returns all plausible forms so that a single audit ID
    can be matched against any source dictionary.
    """
    candidates: list[str] = [image_id]
    stem = Path(image_id).stem
    if stem != image_id:
        candidates.append(stem)
    # Strip dataset prefix (e.g. "jssoda_jssoda_h..." -> "jssoda_h...")
    if dataset:
        prefix = f"{dataset}_"
        if image_id.startswith(prefix):
            stripped = image_id[len(prefix) :]
            if stripped not in candidates:
                candidates.append(stripped)
            stripped_stem = Path(stripped).stem
            if stripped_stem not in candidates:
                candidates.append(stripped_stem)
    return candidates


def _safe_get(record: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Nested dict access that returns *default* on any missing key."""
    current: Any = record
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def _normalize_value(value: Any) -> Any:
    """Normalize a value for comparison.

    Booleans stay booleans; ``None`` stays ``None``; lists are sorted
    lowercase strings.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        return sorted(str(v).lower() for v in value)
    if isinstance(value, (int, float)):
        return value
    return str(value).strip().lower()


def _values_match(val_a: Any, val_b: Any) -> bool:
    """Return ``True`` when two normalized values are equal."""
    norm_a = _normalize_value(val_a)
    norm_b = _normalize_value(val_b)
    if norm_a is None or norm_b is None:
        return False
    return norm_a == norm_b  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Generic Source Loading
# ---------------------------------------------------------------------------
def _load_json_safely(path: Path) -> dict[str, Any] | list[Any] | None:
    """Load a JSON file, returning ``None`` on any error."""
    try:
        with path.open() as fh:
            return json.load(fh)  # type: ignore[no-any-return]
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _index_by_image_id(
    records: list[dict[str, Any]],
    id_key: str = "image_id",
) -> dict[str, dict[str, Any]]:
    """Index a list of records by *id_key*, falling back to ``sample_id``."""
    result: dict[str, dict[str, Any]] = {}
    for rec in records:
        image_id = rec.get(id_key, "") or rec.get("sample_id", "")
        if image_id:
            result[image_id] = rec
    return result


def load_l2_metadata(
    path: Path,
) -> dict[str, dict[str, Any]]:
    """Load L2 metadata keyed by ``original_filename`` stem.

    Also indexes by the full ``id`` field so lookups succeed with
    either format (e.g. ``jssoda_horizontal_00000`` or
    ``jssoda_jssoda_horizontal_00000.png``).

    Each value contains ``raw``, ``enrichment``, and ``split`` keys.
    """
    raw = _load_json_safely(path)
    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for sample in raw.get("samples", []):
        filename = _safe_get(sample, "source", "original_filename", default="")
        image_id = _image_id_from_filename(filename)
        if not image_id:
            continue

        enrichment_data: dict[str, Any] = {}
        versions = _safe_get(sample, "enrichments", "versions", default=[])
        if versions:
            enrichment_data = versions[-1].get("data", {})

        entry = {
            "raw": sample,
            "enrichment": enrichment_data,
            "split": _safe_get(sample, "source", "split"),
        }
        result[image_id] = entry

        # Also index by the full sample id for sample_set compatibility.
        full_id: str = sample.get("id", "")
        if full_id and full_id != image_id:
            result[full_id] = entry

    return result


def load_samples_json(
    path: Path,
) -> dict[str, dict[str, Any]]:
    """Load a JSON file with a ``samples`` array keyed by ``image_id``."""
    raw = _load_json_safely(path)
    if not isinstance(raw, dict):
        return {}
    return _index_by_image_id(raw.get("samples", []))


def load_results_json(
    path: Path,
) -> dict[str, dict[str, Any]]:
    """Load a JSON file with a ``results`` array keyed by ``image_id``."""
    raw = _load_json_safely(path)
    if not isinstance(raw, dict):
        return {}
    return _index_by_image_id(raw.get("results", []))


def _merge_docling_batch(
    result: dict[str, dict[str, Any]],
    per_image: dict[str, list[str]],
) -> None:
    """Merge per-image annotation data into the accumulated result dict."""
    for image_id, cats in per_image.items():
        if image_id not in result:
            result[image_id] = {
                "annotation_count": len(cats),
                "category_names": sorted(set(cats)),
            }
        else:
            result[image_id]["annotation_count"] += len(cats)
            existing = set(result[image_id]["category_names"])
            existing.update(cats)
            result[image_id]["category_names"] = sorted(existing)


def _parse_docling_batch(raw: dict[str, Any]) -> dict[str, list[str]]:
    """Parse a single COCO-format batch into per-image category lists."""
    cat_map: dict[int, str] = {c["id"]: c["name"] for c in raw.get("categories", [])}

    img_id_to_name: dict[int, str] = {}
    for img in raw.get("images", []):
        img_id_to_name[img["id"]] = _image_id_from_filename(img["file_name"])

    per_image: dict[str, list[str]] = defaultdict(list)
    for ann in raw.get("annotations", []):
        numeric_id = ann.get("image_id")
        name = img_id_to_name.get(numeric_id, "")
        if name:
            cat_name = cat_map.get(ann.get("category_id", -1), "unknown")
            per_image[name].append(cat_name)

    return dict(per_image)


def load_docling_layout(
    directory: Path,
) -> dict[str, dict[str, Any]]:
    """Load Docling GPU layout from COCO-format batch files.

    Returns a dict keyed by image_id with ``annotation_count`` and
    ``category_names`` (unique class names detected).
    """
    batch_files = sorted(directory.glob("layout_batch_*.json"))
    if not batch_files:
        return {}

    result: dict[str, dict[str, Any]] = {}

    for batch_path in batch_files:
        raw = _load_json_safely(batch_path)
        if not isinstance(raw, dict):
            continue
        per_image = _parse_docling_batch(raw)
        _merge_docling_batch(result, per_image)

    return result


def load_resolution_quality(
    path: Path,
) -> dict[str, dict[str, Any]]:
    """Load resolution quality labels keyed by image_id.

    Supports both ``results`` and ``samples`` top-level keys.
    """
    raw = _load_json_safely(path)
    if not isinstance(raw, dict):
        return {}

    records = raw.get("results", raw.get("samples", []))
    return _index_by_image_id(records)


# ---------------------------------------------------------------------------
# Source Discovery
# ---------------------------------------------------------------------------
def _log_source(label: str, count: int, path: Path | str, *, verbose: bool) -> None:
    """Log a discovered source to stderr when verbose."""
    if verbose:
        print(
            f"  {label:<24s} {count:>6,} records  ({path})",
            file=sys.stderr,
        )


def _skip_source(label: str, path: Path | str, *, verbose: bool) -> None:
    """Log a skipped source to stderr when verbose."""
    if verbose:
        print(
            f"  {label:<24s}   skip  ({path})",
            file=sys.stderr,
        )


def _try_load_json_source(
    label: str,
    path: Path | None,
    loader: Any,
    sources: dict[str, dict[str, dict[str, Any]]],
    *,
    verbose: bool,
) -> None:
    """Attempt to load a JSON source and add it to *sources*."""
    if path and path.exists():
        data = loader(path)
        if data:
            sources[label] = data
            _log_source(label, len(data), path, verbose=verbose)
            return
    _skip_source(label, path or _NOT_CONFIGURED, verbose=verbose)


def _discover_docling_layout(
    config: DatasetAuditConfig,
    extracted_dir: Path,
    sources: dict[str, dict[str, dict[str, Any]]],
    *,
    verbose: bool,
) -> None:
    """Discover and load Docling layout source."""
    docling_dir: Path | None = None
    if config.docling_layout_path and config.docling_layout_path.is_dir():
        docling_dir = config.docling_layout_path
    elif extracted_dir.is_dir():
        docling_dir = extracted_dir

    if docling_dir is None:
        _skip_source("docling_layout", extracted_dir, verbose=verbose)
        return

    data = load_docling_layout(docling_dir)
    if data:
        sources["docling_layout"] = data
        _log_source("docling_layout", len(data), docling_dir, verbose=verbose)
    else:
        _skip_source("docling_layout", docling_dir, verbose=verbose)


def _discover_resolution_quality(
    dataset: str,
    sources: dict[str, dict[str, dict[str, Any]]],
    *,
    verbose: bool,
) -> None:
    """Discover and load resolution quality labels."""
    res_candidates = [
        RESULTS_ROOT / f"{dataset}_resolution_labels.json",
        RESULTS_ROOT / f"{dataset.replace('-', '')}_resolution_labels.json",
    ]
    for res_path in res_candidates:
        if res_path.exists():
            data = load_resolution_quality(res_path)
            if data:
                sources["resolution_quality"] = data
                _log_source("resolution_quality", len(data), res_path, verbose=verbose)
            return
    _skip_source("resolution_quality", res_candidates[0], verbose=verbose)


def discover_sources(
    config: DatasetAuditConfig,
    *,
    verbose: bool = False,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Auto-discover and load all available enrichment sources.

    Returns a dict of ``{source_name: {image_id: record}}``.
    """
    dataset = config.dataset_name
    extracted_dir = DEFAULT_EXTRACTED_ROOT / dataset
    audit_dir = AUDIT_RESULTS_ROOT / dataset

    sources: dict[str, dict[str, dict[str, Any]]] = {}

    # 1. L2 metadata
    _try_load_json_source(
        "l2_metadata",
        config.metadata_json_path,
        load_l2_metadata,
        sources,
        verbose=verbose,
    )

    # 2. LLM enrichment
    _try_load_json_source(
        "llm_enrichment",
        config.llm_enrichment_path,
        load_samples_json,
        sources,
        verbose=verbose,
    )

    # 3. Language enrichment
    _try_load_json_source(
        "language_enrichment",
        config.language_enrichment_path,
        load_samples_json,
        sources,
        verbose=verbose,
    )

    # 4. Docling layout
    _discover_docling_layout(config, extracted_dir, sources, verbose=verbose)

    # 5. Egret layout results
    _try_load_json_source(
        "egret_layout",
        audit_dir / "egret_results.json",
        load_results_json,
        sources,
        verbose=verbose,
    )

    # 6. Visual ground truth
    _try_load_json_source(
        "visual_gt",
        audit_dir / "visual_ground_truth.json",
        load_samples_json,
        sources,
        verbose=verbose,
    )

    # 7. Resolution quality labels
    _discover_resolution_quality(dataset, sources, verbose=verbose)

    return sources


# ---------------------------------------------------------------------------
# Field Extraction
# ---------------------------------------------------------------------------
def _extract_split_from_image_id(image_id: str) -> str | None:
    """Derive split from image_id prefix (e.g. ``train_ori_00272``)."""
    parts = image_id.split("_")
    if parts and parts[0] in ("train", "test", "val", "validation"):
        return parts[0]
    return None


def _egret_content_flags(
    egret_rec: dict[str, Any],
) -> dict[str, bool]:
    """Derive content flags from Egret detection results."""
    derived = egret_rec.get("content_flags_derived", {})
    if derived:
        return {
            "has_table": derived.get("has_table", False),
            "has_formula": derived.get("has_formula", False),
            "has_figure": derived.get("has_figure", False),
            "has_handwriting": False,
        }

    detections = egret_rec.get("detections", [])
    classes_found = {d.get("class_name_canonical", "").upper() for d in detections}
    return {
        "has_table": "TABLE" in classes_found,
        "has_formula": "FORMULA" in classes_found,
        "has_figure": ("PICTURE" in classes_found or "FIGURE" in classes_found),
        "has_handwriting": False,
    }


def _docling_content_flags(
    docling_rec: dict[str, Any],
) -> dict[str, bool]:
    """Derive content flags from Docling layout categories."""
    cats = set(docling_rec.get("category_names", []))
    return {
        "has_table": "table" in cats,
        "has_formula": "formula" in cats,
        "has_figure": "picture" in cats or "figure" in cats,
        "has_handwriting": False,
    }


def _lookup_source(
    source_data: dict[str, dict[str, Any]],
    image_id: str,
    dataset: str = "",
) -> dict[str, Any]:
    """Look up *image_id* in *source_data* trying all ID variants."""
    for variant in _id_variants(image_id, dataset):
        rec = source_data.get(variant)
        if rec is not None:
            return rec
    return {}


@dataclass(frozen=True)
class _SourceRecords:
    """Resolved per-source records for a single image."""

    l2_rec: dict[str, Any]
    l2_enrich: dict[str, Any]
    llm_rec: dict[str, Any]
    lang_rec: dict[str, Any]
    egret_rec: dict[str, Any]
    docling_rec: dict[str, Any]
    vgt_rec: dict[str, Any]


def _resolve_source_records(
    image_id: str,
    sources: dict[str, dict[str, dict[str, Any]]],
    dataset: str,
) -> _SourceRecords:
    """Look up all source records for a single image."""
    l2_rec = _lookup_source(sources.get("l2_metadata", {}), image_id, dataset)
    return _SourceRecords(
        l2_rec=l2_rec,
        l2_enrich=l2_rec.get("enrichment", {}),
        llm_rec=_lookup_source(sources.get("llm_enrichment", {}), image_id, dataset),
        lang_rec=_lookup_source(
            sources.get("language_enrichment", {}), image_id, dataset
        ),
        egret_rec=_lookup_source(sources.get("egret_layout", {}), image_id, dataset),
        docling_rec=_lookup_source(
            sources.get("docling_layout", {}), image_id, dataset
        ),
        vgt_rec=_lookup_source(sources.get("visual_gt", {}), image_id, dataset),
    )


def _extract_simple_field(field_name: str, recs: _SourceRecords) -> dict[str, Any]:
    """Extract a field present in l2_enrich, llm, and visual_gt."""
    values: dict[str, Any] = {}
    if recs.l2_enrich:
        values["l2_metadata"] = recs.l2_enrich.get(field_name)
    if recs.llm_rec:
        values["llm_enrichment"] = recs.llm_rec.get(field_name)
    if recs.vgt_rec:
        values["visual_gt"] = recs.vgt_rec.get(field_name)
    return values


def _extract_l2_vgt_field(field_name: str, recs: _SourceRecords) -> dict[str, Any]:
    """Extract a field present only in l2_enrich and visual_gt."""
    values: dict[str, Any] = {}
    if recs.l2_enrich:
        values["l2_metadata"] = recs.l2_enrich.get(field_name)
    if recs.vgt_rec:
        values["visual_gt"] = recs.vgt_rec.get(field_name)
    return values


def _extract_iso639_language(recs: _SourceRecords) -> dict[str, Any]:
    """Extract iso639_language from all relevant sources."""
    values: dict[str, Any] = {}
    if recs.l2_enrich:
        values["l2_metadata"] = recs.l2_enrich.get("iso639_language")
    if recs.lang_rec:
        values["language_enrichment"] = recs.lang_rec.get("language")
    if recs.llm_rec:
        values["llm_enrichment"] = recs.llm_rec.get(
            "iso639_language", recs.llm_rec.get("language")
        )
    if recs.vgt_rec:
        values["visual_gt"] = recs.vgt_rec.get("iso639_language")
    return values


def _extract_orientation_class(recs: _SourceRecords) -> dict[str, Any]:
    """Extract orientation_class with geometric fallback."""
    values: dict[str, Any] = {}
    if recs.l2_enrich:
        orientation = recs.l2_enrich.get("orientation_class")
        if orientation is None:
            geometric = recs.l2_enrich.get("geometric", {})
            if isinstance(geometric, dict):
                orientation = geometric.get("orientation_class")
        values["l2_metadata"] = orientation
    if recs.vgt_rec:
        values["visual_gt"] = recs.vgt_rec.get("orientation_class")
    return values


def _extract_content_flag(field_name: str, recs: _SourceRecords) -> dict[str, Any]:
    """Extract a content flag field from all sources."""
    values: dict[str, Any] = {}
    if recs.l2_enrich:
        values["l2_metadata"] = recs.l2_enrich.get(field_name)
    if recs.llm_rec:
        values["llm_enrichment"] = recs.llm_rec.get(field_name)
    if recs.egret_rec:
        values["egret_layout"] = _egret_content_flags(recs.egret_rec).get(field_name)
    if recs.docling_rec:
        values["docling_layout"] = _docling_content_flags(recs.docling_rec).get(
            field_name
        )
    if recs.vgt_rec:
        values["visual_gt"] = recs.vgt_rec.get(field_name)
    return values


def _extract_layout_class_count(recs: _SourceRecords) -> dict[str, Any]:
    """Extract layout_class_count from layout sources."""
    values: dict[str, Any] = {}
    if recs.l2_enrich:
        values["l2_metadata"] = len(recs.l2_enrich.get("layout_detections", []))
    if recs.egret_rec:
        values["egret_layout"] = recs.egret_rec.get(
            "detection_count", len(recs.egret_rec.get("detections", []))
        )
    if recs.docling_rec:
        values["docling_layout"] = recs.docling_rec.get("annotation_count", 0)
    return values


def _extract_split(image_id: str, recs: _SourceRecords) -> dict[str, Any]:
    """Extract split information from L2, image_id, and visual_gt."""
    values: dict[str, Any] = {}
    if recs.l2_rec:
        values["l2_metadata"] = recs.l2_rec.get("split")
    id_split = _extract_split_from_image_id(image_id)
    if id_split is not None:
        values["image_id_derived"] = id_split
    if recs.vgt_rec:
        values["visual_gt"] = recs.vgt_rec.get("split")
    return values


def _extract_single_field(
    field_name: str,
    image_id: str,
    recs: _SourceRecords,
) -> dict[str, Any]:
    """Extract values for a single field from all relevant sources."""
    if field_name in ("capture_method", "domain_level1"):
        return _extract_simple_field(field_name, recs)
    if field_name == "iso639_language":
        return _extract_iso639_language(recs)
    if field_name in ("script_family", "color_mode", "physical_degradation"):
        return _extract_l2_vgt_field(field_name, recs)
    if field_name == "orientation_class":
        return _extract_orientation_class(recs)
    if field_name in CONTENT_FLAG_FIELDS:
        return _extract_content_flag(field_name, recs)
    if field_name == "layout_class_count":
        return _extract_layout_class_count(recs)
    if field_name == "split":
        return _extract_split(image_id, recs)
    # Generic fallback
    return _extract_simple_field(field_name, recs)


def extract_field_values(
    image_id: str,
    sources: dict[str, dict[str, dict[str, Any]]],
    fields: list[str],
    dataset: str = "",
) -> dict[str, dict[str, Any]]:
    """Extract per-source values for comparison fields for one sample.

    Returns ``{field_name: {source_name: value}}``.
    """
    recs = _resolve_source_records(image_id, sources, dataset)
    result: dict[str, dict[str, Any]] = {}

    for field_name in fields:
        values = _extract_single_field(field_name, image_id, recs)
        # Strip entries where value is ``None`` AND source was empty.
        # Keep ``None`` if source existed but field was absent.
        result[field_name] = {
            k: v for k, v in values.items() if k in sources or k == "image_id_derived"
        }

    return result


# ---------------------------------------------------------------------------
# Agreement Metrics (pairwise, no ground-truth dependency)
# ---------------------------------------------------------------------------
def compute_agreement_metrics(
    all_comparisons: list[dict[str, Any]],
    fields: list[str],
    source_names: list[str],
) -> dict[str, Any]:
    """Compute pairwise agreement across all source pairs.

    If ``visual_gt`` is present it is also used as a reference for
    per-source accuracy, matching the DIQA report structure.

    Returns a dict with ``per_field`` and ``pairwise`` sections.
    """
    has_gt = "visual_gt" in source_names

    # Per-field statistics
    per_field: dict[str, dict[str, Any]] = {}

    # Pairwise agreement counters: (src_a, src_b) -> {matches, total}
    pair_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"matches": 0, "total": 0}
    )

    # Per-source vs GT counters (only when GT exists)
    gt_correct: dict[str, int] = defaultdict(int)
    gt_total: dict[str, int] = defaultdict(int)

    for field_name in fields:
        field_pair_matches: dict[tuple[str, str], dict[str, int]] = defaultdict(
            lambda: {"matches": 0, "total": 0}
        )

        for comp in all_comparisons:
            src_vals = comp.get("fields", {}).get(field_name, {}).get("sources", {})

            present = [(s, v) for s, v in src_vals.items() if v is not None]

            # Pairwise comparisons
            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    s_a, v_a = present[i]
                    s_b, v_b = present[j]
                    key = tuple(sorted([s_a, s_b]))
                    pair_key = (key[0], key[1])

                    field_pair_matches[pair_key]["total"] += 1
                    pair_stats[pair_key]["total"] += 1

                    if _values_match(v_a, v_b):
                        field_pair_matches[pair_key]["matches"] += 1
                        pair_stats[pair_key]["matches"] += 1

            # GT accuracy (if visual_gt present)
            if has_gt:
                gt_val = src_vals.get("visual_gt")
                if gt_val is not None:
                    for src, val in src_vals.items():
                        if src == "visual_gt" or val is None:
                            continue
                        gt_total[src] += 1
                        if _values_match(val, gt_val):
                            gt_correct[src] += 1

        # Summarize field-level pairwise agreement
        field_pairs: dict[str, float] = {}
        for pair_key, stats in field_pair_matches.items():
            label = f"{pair_key[0]} vs {pair_key[1]}"
            if stats["total"] > 0:
                field_pairs[label] = round(stats["matches"] / stats["total"], 4)

        per_field[field_name] = {
            "pairwise_agreement": field_pairs,
        }

        # If GT exists, add per-source accuracy for this field
        if has_gt:
            src_accs: dict[str, float] = {}
            best_source: str | None = None
            best_accuracy = -1.0
            for src in source_names:
                if src == "visual_gt":
                    continue
                for pair_key, stats in field_pair_matches.items():
                    if (
                        "visual_gt" in pair_key
                        and src in pair_key
                        and stats["total"] > 0
                    ):
                        acc = stats["matches"] / stats["total"]
                        src_accs[src] = round(acc, 4)
                        if acc > best_accuracy:
                            best_accuracy = acc
                            best_source = src
            per_field[field_name]["source_accuracies_vs_gt"] = src_accs
            per_field[field_name]["best_source"] = best_source
            per_field[field_name]["best_accuracy"] = (
                round(best_accuracy, 4) if best_accuracy >= 0 else None
            )

    # Overall pairwise summary
    pairwise_summary: dict[str, dict[str, Any]] = {}
    for pair_key, stats in sorted(pair_stats.items()):
        label = f"{pair_key[0]} vs {pair_key[1]}"
        pairwise_summary[label] = {
            "comparisons": stats["total"],
            "matches": stats["matches"],
            "agreement_rate": (
                round(stats["matches"] / stats["total"], 4)
                if stats["total"] > 0
                else None
            ),
        }

    result: dict[str, Any] = {
        "per_field": per_field,
        "pairwise": pairwise_summary,
    }

    # Per-source GT accuracy
    if has_gt:
        per_source_gt: dict[str, dict[str, Any]] = {}
        for src in sorted(set(gt_correct.keys()) | set(gt_total.keys())):
            total = gt_total[src]
            correct = gt_correct[src]
            per_source_gt[src] = {
                "fields_compared": total,
                "fields_matching_gt": correct,
                "overall_accuracy": (round(correct / total, 4) if total > 0 else None),
            }
        result["per_source_vs_gt"] = per_source_gt

    return result


# ---------------------------------------------------------------------------
# Disagreement Detail
# ---------------------------------------------------------------------------
def find_disagreements(
    all_comparisons: list[dict[str, Any]],
    fields: list[str],
) -> list[dict[str, Any]]:
    """Return all pairwise disagreements across sources."""
    disagreements: list[dict[str, Any]] = []

    for comp in all_comparisons:
        image_id = comp["image_id"]
        for field_name in fields:
            src_vals = comp.get("fields", {}).get(field_name, {}).get("sources", {})

            present = [(s, v) for s, v in src_vals.items() if v is not None]

            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    s_a, v_a = present[i]
                    s_b, v_b = present[j]
                    if not _values_match(v_a, v_b):
                        disagreements.append(
                            {
                                "image_id": image_id,
                                "field": field_name,
                                "source_a": s_a,
                                "source_b": s_b,
                                "value_a": v_a,
                                "value_b": v_b,
                            }
                        )

    return disagreements


# ---------------------------------------------------------------------------
# Main Assembly
# ---------------------------------------------------------------------------
def assemble_comparison(
    config: DatasetAuditConfig,
    fields: list[str],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Load all sources and assemble the full comparison report."""
    if verbose:
        print(
            f"Discovering sources for '{config.dataset_name}'...",
            file=sys.stderr,
        )

    sources = discover_sources(config, verbose=verbose)

    if not sources:
        print(
            "ERROR: No data sources found. Cannot build comparison.",
            file=sys.stderr,
        )
        sys.exit(1)

    source_names = sorted(sources.keys())
    if verbose:
        print(
            f"\n  Sources available: {', '.join(source_names)}",
            file=sys.stderr,
        )

    # Determine audit sample IDs.
    # Prefer sample_set.json if it exists; otherwise use the
    # intersection of all available sources.
    audit_dir = AUDIT_RESULTS_ROOT / config.dataset_name
    sample_set_path = audit_dir / "sample_set.json"

    audit_ids: list[str]
    if sample_set_path.exists():
        ss_data = load_samples_json(sample_set_path)
        audit_ids = sorted(ss_data.keys())
        if verbose:
            print(
                f"  Sample set loaded: {len(audit_ids)} samples from {sample_set_path}",
                file=sys.stderr,
            )
    else:
        # Fall back to union of all source IDs.
        all_ids: set[str] = set()
        for src_data in sources.values():
            all_ids.update(src_data.keys())
        audit_ids = sorted(all_ids)
        if verbose:
            print(
                f"  No sample_set.json; using union of "
                f"{len(audit_ids)} image IDs across sources",
                file=sys.stderr,
            )

    if not audit_ids:
        print("ERROR: No audit sample IDs found.", file=sys.stderr)
        sys.exit(1)

    # Build per-sample comparisons.
    all_comparisons: list[dict[str, Any]] = []

    for image_id in audit_ids:
        field_values = extract_field_values(
            image_id, sources, fields, dataset=config.dataset_name
        )

        sources_available = {
            name: any(
                v in src_data for v in _id_variants(image_id, config.dataset_name)
            )
            for name, src_data in sources.items()
        }

        sample_comparison: dict[str, Any] = {
            "image_id": image_id,
            "sources_available": sources_available,
            "fields": {},
        }

        for field_name in fields:
            src_vals = field_values.get(field_name, {})

            # Pairwise match matrix
            present = [(s, v) for s, v in src_vals.items() if v is not None]
            matches: dict[str, dict[str, bool | None]] = {}
            for i, (s_a, v_a) in enumerate(present):
                for j, (s_b, v_b) in enumerate(present):
                    if i >= j:
                        continue
                    matches.setdefault(s_a, {})[s_b] = _values_match(v_a, v_b)

            sample_comparison["fields"][field_name] = {
                "sources": src_vals,
                "pairwise_matches": matches,
            }

        all_comparisons.append(sample_comparison)

    # Aggregate metrics
    metrics = compute_agreement_metrics(all_comparisons, fields, source_names)
    disagreements = find_disagreements(all_comparisons, fields)

    # Build source path map for metadata
    source_paths: dict[str, str] = {}
    if config.metadata_json_path:
        source_paths["l2_metadata"] = str(config.metadata_json_path)
    if config.llm_enrichment_path:
        source_paths["llm_enrichment"] = str(config.llm_enrichment_path)
    if config.language_enrichment_path:
        source_paths["language_enrichment"] = str(config.language_enrichment_path)
    docling_dir = DEFAULT_EXTRACTED_ROOT / config.dataset_name
    if docling_dir.is_dir():
        source_paths["docling_layout"] = str(docling_dir)
    egret_path = audit_dir / "egret_results.json"
    if egret_path.exists():
        source_paths["egret_layout"] = str(egret_path)
    vgt_path = audit_dir / "visual_ground_truth.json"
    if vgt_path.exists():
        source_paths["visual_gt"] = str(vgt_path)

    report: dict[str, Any] = {
        "report_metadata": {
            "dataset": config.dataset_name,
            "audit_sample_count": len(audit_ids),
            "created_at": datetime.now(tz=UTC).isoformat(),
            "sources_discovered": source_names,
            "source_paths": source_paths,
            "fields_compared": fields,
        },
        "samples": all_comparisons,
        "agreement_metrics": metrics,
        "disagreements": disagreements,
        "disagreement_count": len(disagreements),
    }

    return report


# ---------------------------------------------------------------------------
# Summary Printer
# ---------------------------------------------------------------------------
def print_summary(report: dict[str, Any]) -> None:
    """Print human-readable summary statistics to stdout."""
    meta = report["report_metadata"]
    metrics = report["agreement_metrics"]
    n_samples = meta["audit_sample_count"]
    n_disagree = report["disagreement_count"]
    dataset = meta["dataset"]
    source_names = meta["sources_discovered"]
    fields = meta["fields_compared"]

    print("\n" + "=" * 72)
    print(f"  {dataset} Audit Comparison Report  ({n_samples} samples)")
    print("=" * 72)

    print(f"\n  Sources: {', '.join(source_names)}")
    print(f"  Fields:  {len(fields)}")

    # Per-source vs GT accuracy (if available)
    per_source_gt = metrics.get("per_source_vs_gt")
    if per_source_gt:
        print("\n--- Overall Accuracy by Source (vs Visual Ground Truth) ---")
        for src in sorted(per_source_gt.keys()):
            info = per_source_gt[src]
            acc = info.get("overall_accuracy")
            acc_str = f"{acc:.1%}" if acc is not None else "N/A"
            print(
                f"  {src:<24s}  "
                f"{info['fields_matching_gt']:>4d} / "
                f"{info['fields_compared']:>4d}  = {acc_str}"
            )

    # Pairwise agreement summary
    pairwise = metrics.get("pairwise", {})
    if pairwise:
        print("\n--- Pairwise Agreement ---")
        for label, info in sorted(pairwise.items()):
            rate = info.get("agreement_rate")
            rate_str = f"{rate:.1%}" if rate is not None else "N/A"
            print(
                f"  {label:<48s} "
                f"{info['matches']:>5d} / {info['comparisons']:>5d}"
                f"  = {rate_str}"
            )

    # Per-field pairwise agreement
    print("\n--- Per-Field Agreement ---")
    per_field = metrics.get("per_field", {})
    for field_name in fields:
        finfo = per_field.get(field_name, {})
        pairs = finfo.get("pairwise_agreement", {})
        if not pairs:
            print(f"  {field_name:<24s}  no comparisons")
            continue

        avg_agreement = sum(pairs.values()) / len(pairs)
        best_label = max(pairs, key=lambda k, pairs=pairs: pairs[k])
        best_val = pairs[best_label]
        print(
            f"  {field_name:<24s}  "
            f"avg={avg_agreement:.1%}  "
            f"best={best_label} ({best_val:.1%})"
        )

    # Disagreement summary
    print(f"\n--- Disagreements: {n_disagree} total ---")
    if n_disagree > 0:
        by_field: dict[str, int] = defaultdict(int)
        by_pair: dict[str, int] = defaultdict(int)
        for d in report["disagreements"]:
            by_field[d["field"]] += 1
            pair = f"{d['source_a']} vs {d['source_b']}"
            by_pair[pair] += 1

        print("  By field:")
        for field_name, count in sorted(by_field.items(), key=lambda x: -x[1]):
            print(f"    {field_name:<24s} {count:>3d}")

        print("  By source pair:")
        for pair, count in sorted(by_pair.items(), key=lambda x: -x[1]):
            print(f"    {pair:<48s} {count:>3d}")

    print("\n" + "=" * 72)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    known = list_known_datasets()

    parser = argparse.ArgumentParser(
        description=(
            "Assemble a per-field comparison report across all "
            "available enrichment sources for a dataset."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"Known datasets: {', '.join(known)}\n\n"
            "Sources are auto-discovered from the audit_config "
            "registry\nand the filesystem.  Missing sources are "
            "silently skipped."
        ),
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help=(
            "Canonical dataset name "
            f"(known: {', '.join(known)}). "
            "Unknown names will error unless paths "
            "are manually configured in audit_config."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output path for the comparison report JSON. "
            "Default: scripts/audit/results/{dataset}/"
            "comparison_report.json"
        ),
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=None,
        metavar="FIELD",
        help=(
            "Override the comparison fields "
            f"(default: {len(DEFAULT_COMPARISON_FIELDS)} fields). "
            "Specify one or more field names separated by spaces."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Discover sources and print what would be compared "
            "without producing the full report."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress to stderr.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the comparison assembler."""
    parser = build_parser()
    args = parser.parse_args(argv)

    dataset: str = args.dataset
    verbose: bool = args.verbose
    dry_run: bool = args.dry_run
    fields = args.fields or list(DEFAULT_COMPARISON_FIELDS)

    output_path: Path = args.output or (
        AUDIT_RESULTS_ROOT / dataset / "comparison_report.json"
    )

    # Load dataset config from the registry.
    try:
        config = load_dataset_config(dataset)
    except ValueError:
        print(
            f"ERROR: Unknown dataset '{dataset}'. "
            f"Known datasets: {', '.join(list_known_datasets())}",
            file=sys.stderr,
        )
        sys.exit(1)

    if verbose:
        print(
            f"Dataset:     {dataset}\n"
            f"Output:      {output_path}\n"
            f"Fields:      {fields}\n"
            f"Dry run:     {dry_run}",
            file=sys.stderr,
        )

    if dry_run:
        print(
            f"Discovering sources for '{dataset}'...",
            file=sys.stderr,
        )
        sources = discover_sources(config, verbose=True)
        print(
            f"\nWould compare {len(fields)} fields across {len(sources)} sources:",
            file=sys.stderr,
        )
        for name in sorted(sources.keys()):
            print(
                f"  {name}: {len(sources[name]):,} records",
                file=sys.stderr,
            )
        print(
            f"\nFields: {', '.join(fields)}",
            file=sys.stderr,
        )
        print(
            f"Output would be: {output_path}",
            file=sys.stderr,
        )
        return

    report = assemble_comparison(config, fields, verbose=verbose)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as fh:
        json.dump(report, fh, indent=2, default=str)

    print_summary(report)
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
