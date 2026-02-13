#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Comprehensive dataset audit across 5 dimensions with gap reports.

Audits all datasets from docs/datasets/source/ across:
  1. Documentation compliance  2. Layer 2 metadata completeness
  3. Parser status  4. Cross-file consistency  5. Aggregation status

Usage:
    uv run python scripts/audit_datasets.py
    uv run python scripts/audit_datasets.py --dataset funsd
    uv run python scripts/audit_datasets.py --output report.json
    uv run python scripts/audit_datasets.py --dimension docs
    uv run python scripts/audit_datasets.py --markdown-output report.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

# -- Project paths ----------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "docs" / "datasets" / "source"
INDICES_DIR = PROJECT_ROOT / "docs" / "datasets" / "indices"
QUICK_REF = PROJECT_ROOT / "docs" / "datasets" / "DATASET_QUICK_REFERENCE.md"
PROCESSING_STATUS = PROJECT_ROOT / "docs" / "datasets" / "DATASET_PROCESSING_STATUS.md"
NAMING_STANDARD = PROJECT_ROOT / "docs" / "datasets" / "DATASET_NAMING_STANDARD.md"
PARSERS_ROOT = (
    PROJECT_ROOT / "src" / "image_preprocessing_detector" / "annotation" / "parsers"
)
DATASETS_CONFIG_FILE = (
    PROJECT_ROOT
    / "src"
    / "image_preprocessing_detector"
    / "annotation"
    / "config"
    / "datasets.py"
)
AGGREGATES_LOCAL = PROJECT_ROOT / "metadata_registry" / "aggregates"
AGGREGATES_EXT = Path("/mnt/e/image_detection/metadata_registry/aggregates")
SAMPLES_PARQUET = Path("/mnt/e/image_detection/metadata_registry/samples.parquet")

# -- Field categories (from metadata_completeness_report.py) ----------------
FIELD_CATEGORIES: dict[str, list[str]] = {
    "identity": ["sample_id", "file_hash", "dataset_name", "original_filename"],
    "file_info": ["width_px", "height_px", "file_size_bytes", "dpi", "format"],
    "quality_scores": ["diqa_mos", "ocr_quality_score", "smartdoc_mos"],
    "original_labels": [
        "writer_id",
        "transcription",
        "original_language_code",
        "original_script_name",
    ],
    "enrichment": [
        "enrichment_version",
        "enrichment_tier",
        "enrichment_source",
        "capture_method",
        "capture_confidence",
        "domain_level1",
        "resolution_category",
    ],
    "content_flags": [
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_signature",
        "has_figure",
    ],
    "language_script": [
        "iso639_language",
        "iso15924_script",
        "script_family",
        "bcp47_tag",
    ],
    "text_scope": [
        "text_scope",
        "text_scope_content_type",
        "text_scope_estimated_chars",
        "text_scope_estimated_words",
    ],
    "paper_size": ["paper_size", "paper_size_standard", "paper_size_orientation"],
    "dataset_source": ["dataset_short_code"],
    "element_counts": ["table_count", "formula_count"],
    "reproducibility": ["git_sha", "model_checkpoint", "script_version"],
    "annotations": [
        "doclaynet_annotations_json",
        "tablebank_annotations_json",
        "funsd_annotations_json",
        "layout_detections_json",
    ],
}

ALL_TRACKED_FIELDS: list[str] = [f for fs in FIELD_CATEGORIES.values() for f in fs]

# Required template sections (1-7, 9 required; 8, 10 optional).
REQUIRED_SECTIONS: dict[str, str] = {
    "1_overview": r"(?:#{2,5})\s*(?:1\.?\s+)?Overview",
    "2_source_data": r"(?:#{2,5})\s*(?:2\.?\s+)?Source Data",
    "3_project_usage": r"(?:#{2,5})\s*(?:3\.?\s+)?Project Usage",
    "4_statistics": r"(?:#{2,5})\s*(?:4\.?\s+)?(?:Dataset )?Statistics",
    "5_content": r"(?:#{2,5})\s*(?:5\.?\s+)?Content",
    "6_iqa_profile": r"(?:#{2,5})\s*(?:6\.?\s+)?IQA Profile",
    "7_known_issues": r"(?:#{2,5})\s*(?:7\.?\s+)?Known Issues",
    "9_references": r"(?:#{2,5})\s*(?:9\.?\s+)?References",
}
OPTIONAL_SECTIONS: dict[str, str] = {
    "8_representative": r"(?:#{2,5})\s*(?:8\.?\s+)?Representative",
    "10_notes": r"(?:#{2,5})\s*(?:10\.?\s+)?(?:Dataset.Specific )?Notes",
}

DIMS = ["documentation", "metadata", "parser", "cross_file", "aggregation"]


# -- Utilities --------------------------------------------------------------
def normalize_dataset_name(name: str) -> str:
    """Convert any variant to canonical kebab-case."""
    return name.replace("_", "-").lower()


def to_config_key(canonical_name: str) -> str:
    """Convert canonical kebab-case name to snake_case config key."""
    return canonical_name.replace("-", "_")


def discover_datasets() -> list[str]:
    """Return sorted canonical dataset names from source dir."""
    return sorted(
        f.stem for f in SOURCE_DIR.glob("*.md") if f.name.lower() != "readme.md"
    )


def _safe_read(path: Path) -> str:
    """Read file text, returning empty string on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# -- Module 1: Documentation Compliance ------------------------------------
def check_documentation(name: str) -> dict[str, Any]:
    """Score template compliance for a dataset source doc."""
    doc_path = SOURCE_DIR / f"{name}.md"
    result: dict[str, Any] = {
        "file_exists": doc_path.exists(),
        "has_frontmatter": False,
        "sections_present": {},
        "optional_sections_present": {},
        "needs_profiling_count": 0,
        "needs_verification_count": 0,
        "documentation_score": 0.0,
    }
    if not doc_path.exists():
        return result

    content = _safe_read(doc_path)
    if not content:
        return result

    result["has_frontmatter"] = bool(re.match(r"\A---\s*\n", content))

    for key, pattern in REQUIRED_SECTIONS.items():
        result["sections_present"][key] = bool(
            re.search(pattern, content, re.IGNORECASE)
        )
    for key, pattern in OPTIONAL_SECTIONS.items():
        result["optional_sections_present"][key] = bool(
            re.search(pattern, content, re.IGNORECASE)
        )

    result["needs_profiling_count"] = content.count("[NEEDS_PROFILING]")
    result["needs_verification_count"] = content.count("[NEEDS_VERIFICATION]")

    total = len(REQUIRED_SECTIONS)
    present = sum(1 for v in result["sections_present"].values() if v)
    result["documentation_score"] = round(present / total * 100, 1) if total else 0.0
    return result


# -- Module 2: Layer 2 Metadata Completeness --------------------------------
def _load_parquet_dataset_names() -> dict[str, Any] | None:
    """Load per-dataset field coverage from parquet (column-pruned)."""
    if not SAMPLES_PARQUET.exists():
        return None
    try:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError:
        print("WARNING: pyarrow not installed, skipping metadata.", file=sys.stderr)
        return None
    try:
        pf = pq.ParquetFile(SAMPLES_PARQUET)
        available = set(pf.schema_arrow.names)
        cols = [c for c in ["dataset_name", *ALL_TRACKED_FIELDS] if c in available]
        table = pf.read(columns=list(dict.fromkeys(cols)))
        ds_col = table.column("dataset_name")

        result: dict[str, Any] = {}
        for ds_name in ds_col.unique().to_pylist():
            subset = table.filter(pc.equal(ds_col, ds_name))
            total = subset.num_rows
            coverage: dict[str, float] = {}
            for field in ALL_TRACKED_FIELDS:
                if field in available and field != "dataset_name":
                    non_null = total - subset.column(field).null_count
                    coverage[field] = round(non_null / total * 100, 1) if total else 0.0
            result[ds_name] = {"total_samples": total, "field_coverage": coverage}
        return result
    except Exception as exc:
        print(f"WARNING: Could not read parquet: {exc}", file=sys.stderr)
        return None


def check_metadata(name: str, parquet_data: dict[str, Any] | None) -> dict[str, Any]:
    """Check Layer 2 metadata completeness for a dataset."""
    result: dict[str, Any] = {
        "in_parquet": False,
        "total_samples": 0,
        "field_coverage": {},
        "critical_gaps": [],
        "metadata_score": 0.0,
    }
    if parquet_data is None:
        result["error"] = "parquet_unavailable"
        return result

    # Try canonical, snake_case, and underscore variants
    ds_data = (
        parquet_data.get(name)
        or parquet_data.get(to_config_key(name))
        or parquet_data.get(name.replace("-", "_"))
    )
    if ds_data is None:
        return result

    result["in_parquet"] = True
    result["total_samples"] = ds_data["total_samples"]
    result["field_coverage"] = ds_data["field_coverage"]

    for field in ["capture_method", "domain_level1", "enrichment_version"]:
        if math.isclose(ds_data["field_coverage"].get(field, 0.0), 0.0):
            result["critical_gaps"].append(field)

    tracked = ds_data["field_coverage"]
    if tracked:
        non_zero = sum(1 for v in tracked.values() if v > 0)
        result["metadata_score"] = round(non_zero / len(tracked) * 100, 1)
    return result


# -- Module 3: Parser Status ------------------------------------------------
def _load_config_keys() -> set[str]:
    """Extract DATASET_CONFIGS keys from the config Python file."""
    if not DATASETS_CONFIG_FILE.exists():
        return set()
    content = _safe_read(DATASETS_CONFIG_FILE)
    return {
        m.group(1)
        for m in re.finditer(
            r'^\s+"([a-z0-9_-]+)"\s*:\s*DatasetConfig\(', content, re.MULTILINE
        )
    }


def check_parsers(name: str, config_keys: set[str]) -> dict[str, Any]:
    """Check parser file existence and DATASET_CONFIGS entry."""
    result: dict[str, Any] = {
        "parser_file": None,
        "file_exists": False,
        "in_dataset_configs": False,
        "config_key": None,
    }
    snake = to_config_key(name)
    variants = {name, snake}

    for parser_py in PARSERS_ROOT.rglob("*.py"):
        if parser_py.name == "__init__.py":
            continue
        if parser_py.stem in variants:
            result["parser_file"] = str(parser_py.relative_to(PARSERS_ROOT))
            result["file_exists"] = True
            break

    for variant in [name, snake]:
        if variant in config_keys:
            result["in_dataset_configs"] = True
            result["config_key"] = variant
            break
    return result


# -- Module 4: Cross-File Consistency ---------------------------------------
def check_cross_file(
    name: str,
    quick_ref: str,
    processing: str,
    naming: str,
    indices: dict[str, str],
) -> dict[str, Any]:
    """Verify dataset presence across documentation files."""
    snake = to_config_key(name)

    def _in(text: str) -> bool:
        return name in text or snake in text

    return {
        "in_source_file": (SOURCE_DIR / f"{name}.md").exists(),
        "in_quick_reference": _in(quick_ref),
        "in_processing_status": _in(processing),
        "in_naming_standard": _in(naming),
        "in_task_indices": sorted(k for k, v in indices.items() if _in(v)),
    }


# -- Module 5: Aggregation Status -------------------------------------------
def check_aggregation(name: str) -> dict[str, Any]:
    """Check if aggregate stats JSON exists with key fields."""
    result: dict[str, Any] = {
        "stats_file_exists": False,
        "has_capture": False,
        "has_domain": False,
        "has_content_flags": False,
    }
    snake = to_config_key(name)
    candidates = [f"{name}_stats.json", f"{snake}_stats.json"]

    stats_path: Path | None = None
    for loc in [AGGREGATES_LOCAL, AGGREGATES_EXT]:
        if not loc.exists():
            continue
        for cand in candidates:
            if (loc / cand).exists():
                stats_path = loc / cand
                break
        if stats_path:
            break
    if stats_path is None:
        return result

    result["stats_file_exists"] = True
    try:
        data = json.loads(stats_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return result

    result["has_capture"] = bool(data.get("capture_methods_pct"))
    result["has_domain"] = bool(data.get("domains_pct"))
    result["has_content_flags"] = bool(data.get("content_flags_pct"))
    return result


# -- Orchestrator -----------------------------------------------------------
def audit_dataset(
    name: str,
    *,
    parquet_data: dict[str, Any] | None,
    config_keys: set[str],
    quick_ref: str,
    processing: str,
    naming: str,
    indices: dict[str, str],
    dimension: str | None = None,
) -> dict[str, Any]:
    """Run audit dimensions for a single dataset."""
    entry: dict[str, Any] = {"dataset": name}
    dim_map: dict[str, tuple[str, Any]] = {
        "docs": ("documentation", lambda: check_documentation(name)),
        "metadata": ("metadata", lambda: check_metadata(name, parquet_data)),
        "parser": ("parser", lambda: check_parsers(name, config_keys)),
        "cross_file": (
            "cross_file",
            lambda: check_cross_file(name, quick_ref, processing, naming, indices),
        ),
        "aggregation": ("aggregation", lambda: check_aggregation(name)),
    }

    if dimension and dimension in dim_map:
        key, func = dim_map[dimension]
        entry[key] = func()
    else:
        for key, func in dim_map.values():
            entry[key] = func()

    doc_score = entry.get("documentation", {}).get("documentation_score", 0.0)
    meta_score = entry.get("metadata", {}).get("metadata_score", 0.0)
    scores = [s for s in [doc_score, meta_score] if s is not None]
    entry["overall_score"] = round(sum(scores) / len(scores), 1) if scores else 0.0
    return entry


def run_audit(
    datasets: list[str], *, dimension: str | None = None
) -> list[dict[str, Any]]:
    """Run audit across all datasets, returning results sorted worst-first."""
    print(f"Auditing {len(datasets)} datasets...", file=sys.stderr)

    parquet_data: dict[str, Any] | None = None
    if dimension is None or dimension == "metadata":
        print("  Loading parquet metadata...", file=sys.stderr)
        parquet_data = _load_parquet_dataset_names()
        status = (
            f"Loaded {len(parquet_data)} datasets" if parquet_data else "unavailable"
        )
        print(f"  Parquet: {status}.", file=sys.stderr)

    config_keys = _load_config_keys()
    quick_ref = _safe_read(QUICK_REF)
    processing = _safe_read(PROCESSING_STATUS)
    naming = _safe_read(NAMING_STANDARD)
    indices: dict[str, str] = (
        {f.stem: _safe_read(f) for f in sorted(INDICES_DIR.glob("*.md"))}
        if INDICES_DIR.exists()
        else {}
    )

    results = [
        audit_dataset(
            name,
            parquet_data=parquet_data,
            config_keys=config_keys,
            quick_ref=quick_ref,
            processing=processing,
            naming=naming,
            indices=indices,
            dimension=dimension,
        )
        for name in datasets
    ]
    results.sort(key=lambda r: r.get("overall_score", 0.0))
    print("  Audit complete.", file=sys.stderr)
    return results


# -- Status & priority helpers ----------------------------------------------
def _dimension_status(entry: dict[str, Any], dim: str) -> str:
    """Return Complete/Partial/Missing/N-A for a dimension."""
    data = entry.get(dim, {})
    if not data:
        return "N/A"

    if dim == "documentation":
        score = data.get("documentation_score", 0)
        if score >= 90:
            return "Complete"
        return "Partial" if score >= 50 else "Missing"

    if dim == "metadata":
        if data.get("error"):
            return "N/A"
        if not data.get("in_parquet"):
            return "Missing"
        return "Complete" if data.get("metadata_score", 0) >= 50 else "Partial"

    if dim == "parser":
        has_file = data.get("file_exists", False)
        has_cfg = data.get("in_dataset_configs", False)
        if has_file and has_cfg:
            return "Complete"
        return "Partial" if (has_file or has_cfg) else "Missing"

    if dim == "cross_file":
        present = sum(
            1
            for k in [
                "in_source_file",
                "in_quick_reference",
                "in_processing_status",
                "in_naming_standard",
            ]
            if data.get(k)
        )
        if present == 4:
            return "Complete"
        return "Partial" if present >= 2 else "Missing"

    if dim == "aggregation":
        if not data.get("stats_file_exists"):
            return "Missing"
        flags = [
            data.get("has_capture"),
            data.get("has_domain"),
            data.get("has_content_flags"),
        ]
        return "Complete" if all(flags) else "Partial"

    return "N/A"


def _prioritize(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """Generate (priority, action) pairs for a dataset."""
    actions: list[tuple[str, str]] = []
    name = entry["dataset"]

    meta = entry.get("metadata", {})
    if meta.get("error") != "parquet_unavailable":
        if not meta.get("in_parquet"):
            actions.append(("P0", f"{name}: No Layer 2 metadata in parquet"))
        else:
            for gap in meta.get("critical_gaps", []):
                actions.append(("P1", f"{name}: Critical field '{gap}' at 0%"))

    docs = entry.get("documentation", {})
    if not docs.get("file_exists"):
        actions.append(("P2", f"{name}: Missing source documentation file"))
    elif docs.get("documentation_score", 0) < 75:
        missing = [k for k, v in docs.get("sections_present", {}).items() if not v]
        if missing:
            actions.append(("P2", f"{name}: Missing sections: {', '.join(missing)}"))

    profiling = docs.get("needs_profiling_count", 0)
    verify = docs.get("needs_verification_count", 0)
    if profiling or verify:
        actions.append(
            ("P3", f"{name}: {profiling} NEEDS_PROFILING, {verify} NEEDS_VERIFICATION")
        )

    if not entry.get("aggregation", {}).get("stats_file_exists"):
        actions.append(("P3", f"{name}: No aggregation stats file"))

    return actions


# -- Markdown report --------------------------------------------------------
def generate_markdown_report(results: list[dict[str, Any]]) -> str:
    """Build a human-readable markdown gap report."""
    lines: list[str] = [
        "# Dataset Audit Report\n",
        f"**Datasets audited**: {len(results)}\n",
        "## Executive Summary\n",
        "| Dimension | Complete | Partial | Missing |",
        "|-----------|----------|---------|---------|",
    ]

    for dim in DIMS:
        counts: dict[str, int] = {"Complete": 0, "Partial": 0, "Missing": 0, "N/A": 0}
        for entry in results:
            counts[_dimension_status(entry, dim)] += 1
        lines.append(
            f"| {dim} | {counts['Complete']} | {counts['Partial']} "
            f"| {counts['Missing']} |"
        )
    lines.append("")

    # Per-dataset table
    lines.append("## Per-Dataset Status (worst first)\n")
    lines.append(
        "| Dataset | Score | Docs | Metadata | Parser | Cross-File | Aggregation |"
    )
    lines.append(
        "|---------|-------|------|----------|--------|------------|-------------|"
    )
    for entry in results:
        cols = " | ".join(_dimension_status(entry, d) for d in DIMS)
        lines.append(
            f"| {entry['dataset']} | {entry.get('overall_score', 0.0):.1f} | {cols} |"
        )
    lines.append("")

    # Action items
    lines.append("## Action Items\n")
    all_actions: list[tuple[str, str]] = []
    for entry in results:
        all_actions.extend(_prioritize(entry))

    labels = {
        "P0": "No Layer 2 metadata",
        "P1": "Critical metadata field gaps",
        "P2": "Documentation compliance gaps",
        "P3": "Aggregation / optional sections",
    }
    for pri in ["P0", "P1", "P2", "P3"]:
        items = [a for a in all_actions if a[0] == pri]
        if items:
            lines.append(f"### {pri}: {labels[pri]}\n")
            lines.extend(f"- {action}" for _, action in items)
            lines.append("")

    return "\n".join(lines)


# -- Console summary -------------------------------------------------------
def _print_console_summary(results: list[dict[str, Any]]) -> None:
    """Print compact audit summary to stdout."""
    print(f"\n{'=' * 72}")
    print("DATASET AUDIT SUMMARY")
    print(f"{'=' * 72}")
    print(f"Datasets audited: {len(results)}\n")

    for dim in DIMS:
        counts: dict[str, int] = {}
        for entry in results:
            status = _dimension_status(entry, dim)
            counts[status] = counts.get(status, 0) + 1
        print(
            f"  {dim:<16} Complete: {counts.get('Complete', 0):>3}  "
            f"Partial: {counts.get('Partial', 0):>3}  "
            f"Missing: {counts.get('Missing', 0):>3}"
        )

    print(f"\n{'-' * 72}\nLOWEST SCORING DATASETS\n{'-' * 72}")
    print(f"{'Dataset':<30} {'Score':>8}\n{'-' * 38}")
    for entry in results[:10]:
        print(f"  {entry['dataset']:<28} {entry.get('overall_score', 0.0):>6.1f}")

    all_actions: list[tuple[str, str]] = []
    for entry in results:
        all_actions.extend(_prioritize(entry))

    print(f"\n{'-' * 72}\nACTION ITEMS BY PRIORITY\n{'-' * 72}")
    for pri in ["P0", "P1", "P2", "P3"]:
        count = sum(1 for a in all_actions if a[0] == pri)
        if count:
            print(f"  {pri}: {count} items")

    print(f"\n{'=' * 72}")
    print("Use --output report.json or --markdown-output report.md for full details.")


# -- CLI --------------------------------------------------------------------
def main() -> None:
    """Entry point for the dataset audit script."""
    parser = argparse.ArgumentParser(
        description="Audit datasets across 5 dimensions and produce gap reports."
    )
    parser.add_argument("--dataset", help="Audit a single dataset by canonical name")
    parser.add_argument("--output", type=Path, help="JSON output file path")
    parser.add_argument("--markdown-output", type=Path, help="Markdown report path")
    parser.add_argument(
        "--dimension",
        choices=["docs", "metadata", "parser", "cross_file", "aggregation"],
        help="Audit only a single dimension",
    )
    args = parser.parse_args()

    all_datasets = discover_datasets()
    if not all_datasets:
        print(f"ERROR: No dataset files found in {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    if args.dataset:
        canonical = normalize_dataset_name(args.dataset)
        if canonical not in all_datasets:
            print(
                f"ERROR: '{canonical}' not found. Available: "
                f"{', '.join(all_datasets[:10])}...",
                file=sys.stderr,
            )
            sys.exit(1)
        datasets = [canonical]
    else:
        datasets = all_datasets

    print(
        f"Discovered {len(all_datasets)} datasets, auditing {len(datasets)}.",
        file=sys.stderr,
    )

    results = run_audit(datasets, dimension=args.dimension)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(results, indent=2, default=str), encoding="utf-8"
        )
        print(f"JSON report written to {args.output}", file=sys.stderr)

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            generate_markdown_report(results), encoding="utf-8"
        )
        print(f"Markdown report written to {args.markdown_output}", file=sys.stderr)

    if not args.markdown_output:
        _print_console_summary(results)


if __name__ == "__main__":
    main()
