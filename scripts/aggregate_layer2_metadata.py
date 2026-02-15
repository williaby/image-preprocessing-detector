#!/usr/bin/env python3
"""Aggregate Layer 2 metadata statistics for dataset quick reference.

This script processes Layer 2 enrichment metadata JSON files to compute
dataset-level statistics for:
- Capture method distributions
- Quality score ranges and distributions
- Degradation type frequencies
- Domain coverage
- Layout type distributions
- Language/script coverage
- Content flags prevalence
- Text scope distributions
- Paper size distributions

Output: JSON files in metadata_registry/aggregates/ with per-dataset statistics.

Supports both:
- Full nested schema format (post-migration, 2025-01-31+)
- Legacy flat field format (pre-migration)

Usage:
    python scripts/aggregate_layer2_metadata.py
    python scripts/aggregate_layer2_metadata.py --dataset tablebank
    python scripts/aggregate_layer2_metadata.py --output-dir custom/path/
    python scripts/aggregate_layer2_metadata.py --layer2-dir /mnt/e/image_detection/metadata_registry/json
"""

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.dataset_source import DATASET_REGISTRY


def get_nested_value(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely extract a value from nested dict structure.

    Handles both nested and flat formats:
    - Nested: data["capture_method"]["method"]
    - Flat: data["capture_method"] (string)

    Args:
        data: The data dictionary
        *keys: Key path (e.g., "capture_method", "method")
        default: Default value if not found

    Returns:
        The extracted value or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current if current is not None else default


def extract_capture_method(data: dict[str, Any]) -> str | None:
    """Extract capture method from either format.

    Nested: data["capture_method"]["method"]
    Flat: data["capture_method"]
    """
    cm = data.get("capture_method")
    if isinstance(cm, dict):
        return cm.get("method")
    if isinstance(cm, str):
        return cm
    return None


def extract_domain(data: dict[str, Any]) -> str | None:
    """Extract domain level1 from either format.

    Nested: data["domain"]["level1"]
    Flat: data["domain_level1"]
    """
    domain = data.get("domain")
    if isinstance(domain, dict):
        return domain.get("level1")
    return data.get("domain_level1")


def extract_layout_type(data: dict[str, Any]) -> str | None:
    """Extract layout type from either format.

    Nested: data["structure"]["layout_type"]
    Flat: data["layout_type"]
    """
    structure = data.get("structure")
    if isinstance(structure, dict):
        return structure.get("layout_type")
    return data.get("layout_type")


def extract_text_density(data: dict[str, Any]) -> str | None:
    """Extract text density from either format.

    Nested: data["structure"]["text_density"]
    Flat: data["text_density"]
    """
    structure = data.get("structure")
    if isinstance(structure, dict):
        return structure.get("text_density")
    return data.get("text_density")


def extract_language_info(
    data: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    """Extract language code, script code, and script family.

    Nested: data["language"]["language_code"], ["script_code"], ["script_family"]
    Flat: data["language_code"], data["script_code"], data["script_family"]
          or data["iso639_language"], data["iso15924_script"]

    Returns:
        Tuple of (language_code, script_code, script_family)
    """
    language = data.get("language")
    if isinstance(language, dict):
        return (
            language.get("language_code"),
            language.get("script_code"),
            language.get("script_family"),
        )
    # Flat format - try both naming conventions
    lang_code = data.get("language_code") or data.get("iso639_language")
    script_code = data.get("script_code") or data.get("iso15924_script")
    script_family = data.get("script_family")
    return (lang_code, script_code, script_family)


def extract_text_scope(data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract text scope and content type from either format.

    Nested: data["text_scope"]["scope"], data["text_scope"]["content_type"]
    Flat: data["text_scope"], data["content_type"] or data["text_scope_content_type"]

    Returns:
        Tuple of (scope, content_type)
    """
    ts = data.get("text_scope")
    if isinstance(ts, dict):
        return (ts.get("scope"), ts.get("content_type"))
    if isinstance(ts, str):
        # Flat format
        content_type = data.get("content_type") or data.get("text_scope_content_type")
        return (ts, content_type)
    return (None, None)


def extract_content_flags(data: dict[str, Any]) -> dict[str, bool]:
    """Extract content flags from either format.

    Nested: data["content_flags"]["has_table"], etc.
    Flat: data["has_table"], etc.

    Returns:
        Dictionary of flag_name -> bool
    """
    flags = {}
    flag_names = [
        "has_table",
        "has_formula",
        "has_handwriting",
        "has_signature",
        "has_figure",
    ]

    cf = data.get("content_flags")
    if isinstance(cf, dict):
        for flag in flag_names:
            if cf.get(flag) is True:
                flags[flag] = True
    else:
        # Flat format
        for flag in flag_names:
            if data.get(flag) is True:
                flags[flag] = True
    return flags


def extract_paper_size(data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract paper size and orientation from either format.

    Nested: data["paper_size"]["detected_size"], data["paper_size"]["orientation"]
    Flat: data["detected_paper_size"], data["paper_orientation"]

    Returns:
        Tuple of (detected_size, orientation)
    """
    ps = data.get("paper_size")
    if isinstance(ps, dict):
        return (ps.get("detected_size"), ps.get("orientation"))
    return (data.get("detected_paper_size"), data.get("paper_orientation"))


def extract_quality_info(data: dict[str, Any]) -> tuple[float | None, list[dict]]:
    """Extract quality score and degradations from either format.

    Nested: data["quality"]["overall_score"], data["quality"]["degradations"]
    Flat: data["overall_score"], data["degradations"]

    Returns:
        Tuple of (overall_score, degradations_list)
    """
    quality = data.get("quality")
    if isinstance(quality, dict):
        return (quality.get("overall_score"), quality.get("degradations", []))
    return (data.get("overall_score"), data.get("degradations", []))


def _accumulate_sample_stats(data: dict[str, Any], stats: dict[str, Any]) -> None:
    """Accumulate statistics from a single sample's enrichment data into stats.

    Args:
        data: Enrichment data dict from a sample's latest version.
        stats: Mutable stats dict to update in place.
    """
    # Simple single-value extractions mapped to their counter key
    _single_extractions: list[tuple[str, Any]] = [
        ("capture_methods", extract_capture_method(data)),
        ("domains", extract_domain(data)),
        ("layout_types", extract_layout_type(data)),
        ("text_densities", extract_text_density(data)),
    ]
    for key, value in _single_extractions:
        if value:
            stats[key][value] += 1

    # Language/Script (multiple return values)
    lang_code, script_code, script_family = extract_language_info(data)
    for key, value in [
        ("language_codes", lang_code),
        ("script_codes", script_code),
        ("script_families", script_family),
    ]:
        if value:
            stats[key][value] += 1

    # Content flags
    for flag_name in extract_content_flags(data):
        stats["content_flags"][flag_name] += 1

    # Text scope and content type
    scope, content_type = extract_text_scope(data)
    if scope:
        stats["text_scopes"][scope] += 1
    if content_type:
        stats["content_types"][content_type] += 1

    # Paper size and orientation
    paper_size, orientation = extract_paper_size(data)
    if paper_size:
        stats["paper_sizes"][paper_size] += 1
    if orientation:
        stats["paper_orientations"][orientation] += 1

    # Quality info
    quality_score, degradations = extract_quality_info(data)
    if quality_score is not None:
        stats["quality_scores"].append(quality_score)

    _accumulate_degradations(degradations, stats)


def _accumulate_degradations(degradations: list[Any], stats: dict[str, Any]) -> None:
    """Process degradation entries and accumulate into stats."""
    if not degradations:
        return
    for deg in degradations:
        if not isinstance(deg, dict):
            continue
        deg_type = deg.get("type")
        if not deg_type:
            continue
        stats["degradation_types"][deg_type] += 1
        severity = deg.get("severity_numeric")
        if severity is not None:
            stats["degradation_severities"][deg_type].append(severity)


def _compute_quality_summary(quality_scores: list[float]) -> dict[str, Any] | None:
    """Compute quality score summary statistics."""
    if not quality_scores:
        return None
    return {
        "min": round(min(quality_scores), 3),
        "max": round(max(quality_scores), 3),
        "mean": round(statistics.mean(quality_scores), 3),
        "median": round(statistics.median(quality_scores), 3),
        "stdev": round(statistics.stdev(quality_scores), 3)
        if len(quality_scores) > 1
        else 0,
    }


def _compute_degradation_summaries(
    degradation_severities: dict[str, list[float]],
) -> dict[str, dict[str, float]]:
    """Compute per-degradation-type severity summaries."""
    summaries: dict[str, dict[str, float]] = {}
    for deg_type, severities in degradation_severities.items():
        if severities:
            summaries[deg_type] = {
                "mean_severity": round(statistics.mean(severities), 3),
                "max_severity": round(max(severities), 3),
            }
    return summaries


def _compute_counter_percentages(stats: dict[str, Any], total: int) -> None:
    """Convert counter fields and content flags to percentage dicts in-place."""
    _counter_keys = [
        "capture_methods",
        "degradation_types",
        "domains",
        "layout_types",
        "text_densities",
        "script_codes",
        "script_families",
        "language_codes",
        "text_scopes",
        "content_types",
        "paper_sizes",
        "paper_orientations",
    ]
    for key in _counter_keys:
        counter = stats[key]
        stats[f"{key}_pct"] = (
            {k: round(v / total * 100, 1) for k, v in counter.items()}
            if counter
            else {}
        )

    stats["content_flags_pct"] = (
        {k: round(v / total * 100, 1) for k, v in stats["content_flags"].items()}
        if stats["content_flags"]
        else {}
    )


def _compute_top_n_list(
    counter: Counter,
    total: int,
    n: int,
    key_name: str,
    extra_data: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    """Build a top-N list from a Counter with percentages.

    Args:
        counter: The Counter to extract top items from.
        total: Total sample count for percentage calculation.
        n: Number of top items.
        key_name: Name of the key field in output dicts.
        extra_data: Optional dict mapping item names to extra fields to merge.

    Returns:
        List of dicts with name, count, percentage, and optional extra fields.
    """
    if not counter:
        return []
    result = []
    for item, count in counter.most_common(n):
        entry: dict[str, Any] = {
            key_name: item,
            "count": count,
            "percentage": round(count / total * 100, 1),
        }
        if extra_data and item in extra_data:
            entry.update(extra_data[item])
        result.append(entry)
    return result


def aggregate_dataset_metadata(
    dataset_name: str,
    layer2_dir: Path,
    verbose: bool = False,
) -> dict[str, Any]:
    """Aggregate Layer 2 metadata for a single dataset.

    Supports both nested (post-migration) and flat (legacy) schema formats.

    Args:
        dataset_name: Canonical dataset name
        layer2_dir: Directory containing Layer 2 JSON files
        verbose: Print progress messages

    Returns:
        Dictionary with aggregated statistics
    """
    # Find Layer 2 metadata file for this dataset.
    # Dataset names may use hyphens (e.g. "pucit-ohul") while the actual
    # metadata file on disk uses underscores (e.g. "pucit_ohul_metadata.json").
    # Try the canonical name first, then fall back to underscore variant.
    metadata_file = layer2_dir / f"{dataset_name}_metadata.json"

    if not metadata_file.exists():
        underscore_name = dataset_name.replace("-", "_")
        alt_file = layer2_dir / f"{underscore_name}_metadata.json"
        if alt_file.exists():
            metadata_file = alt_file
            if verbose:
                print(
                    f"ℹ️  Using underscore variant: {alt_file.name} "
                    f"(canonical: {dataset_name}_metadata.json)"
                )

    if not metadata_file.exists():
        if verbose:
            print(f"⚠️  No Layer 2 metadata file found for {dataset_name}")
        return {
            "dataset_name": dataset_name,
            "total_samples": 0,
            "error": "No Layer 2 metadata file found",
        }

    # Load dataset metadata file
    try:
        with open(metadata_file) as f:
            dataset_metadata = json.load(f)
    except Exception as e:
        if verbose:
            print(f"⚠️  Error loading {metadata_file}: {e}")
        return {
            "dataset_name": dataset_name,
            "total_samples": 0,
            "error": f"Failed to load metadata file: {e}",
        }

    samples = dataset_metadata.get("samples", [])

    stats: dict[str, Any] = {
        "dataset_name": dataset_name,
        "total_samples": len(samples),
        # Raw counters
        "capture_methods": Counter(),
        "quality_scores": [],
        "degradation_types": Counter(),
        "degradation_severities": defaultdict(list),
        "domains": Counter(),
        "layout_types": Counter(),
        "text_densities": Counter(),
        "script_codes": Counter(),
        "script_families": Counter(),
        "language_codes": Counter(),
        "content_flags": defaultdict(int),
        "text_scopes": Counter(),
        "content_types": Counter(),
        "paper_sizes": Counter(),
        "paper_orientations": Counter(),
    }

    for sample in samples:
        try:
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])
            if not versions:
                continue
            data = versions[-1].get("data", {})
            _accumulate_sample_stats(data, stats)
        except Exception as e:
            if verbose:
                sample_id = sample.get("id", "unknown")
                print(f"⚠️  Error processing sample {sample_id}: {e}")
            continue

    # Compute summary statistics
    stats["quality_summary"] = _compute_quality_summary(stats["quality_scores"])

    degradation_summaries = _compute_degradation_summaries(
        stats["degradation_severities"]
    )
    stats["degradation_summaries"] = degradation_summaries

    # Convert counters to percentages
    total = stats["total_samples"]
    _compute_counter_percentages(stats, total)

    # Top degradations (by frequency) - include mean_severity from summaries
    deg_extra = {
        k: {"mean_severity": v.get("mean_severity", 0)}
        for k, v in degradation_summaries.items()
    }
    stats["top_degradations"] = _compute_top_n_list(
        stats["degradation_types"], total, 5, "type", deg_extra
    )

    # Top scripts (by frequency)
    stats["top_scripts"] = _compute_top_n_list(
        stats["script_codes"], total, 10, "script"
    )

    # Top languages (by frequency)
    stats["top_languages"] = _compute_top_n_list(
        stats["language_codes"], total, 10, "language"
    )

    # Script family summary
    stats["script_family_summary"] = (
        dict(stats["script_families"].most_common()) if stats["script_families"] else {}
    )

    return stats


def main():
    """Aggregate metadata for all datasets."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Aggregate Layer 2 metadata statistics"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Process single dataset (canonical name)",
    )
    parser.add_argument(
        "--layer2-dir",
        type=Path,
        default=Path("metadata_registry/json"),
        help="Directory containing Layer 2 JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("metadata_registry/aggregates"),
        help="Output directory for aggregate statistics",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress messages",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset:
        # Process single dataset
        dataset_name = args.dataset
        print(f"Processing {dataset_name}...")
        stats = aggregate_dataset_metadata(dataset_name, args.layer2_dir, args.verbose)

        output_file = args.output_dir / f"{dataset_name}_stats.json"
        with open(output_file, "w") as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Aggregated metadata for {dataset_name}")
        print(f"   Output: {output_file}")
        print(f"   Samples: {stats['total_samples']}")

        if stats.get("quality_summary"):
            print(
                f"   Quality: {stats['quality_summary']['min']:.2f}-{stats['quality_summary']['max']:.2f} (μ={stats['quality_summary']['mean']:.2f})"
            )

        if stats.get("top_degradations"):
            print(
                f"   Top degradations: {', '.join(d['type'] for d in stats['top_degradations'][:3])}"
            )

    else:
        # Process all datasets in registry
        processed = 0
        errors = 0

        for dataset_name in sorted(DATASET_REGISTRY.keys()):
            if args.verbose:
                print(f"Processing {dataset_name}...")

            stats = aggregate_dataset_metadata(
                dataset_name, args.layer2_dir, args.verbose
            )

            if "error" in stats:
                errors += 1
                if args.verbose:
                    print(f"   ⚠️  {stats['error']}")
                continue

            output_file = args.output_dir / f"{dataset_name}_stats.json"
            with open(output_file, "w") as f:
                json.dump(stats, f, indent=2)

            processed += 1
            if args.verbose:
                print(f"   ✅ {stats['total_samples']} samples")

        print(f"\n✅ Processed {processed} datasets")
        if errors > 0:
            print(f"⚠️  {errors} datasets had no Layer 2 metadata")
        print(f"📁 Output: {args.output_dir}")


if __name__ == "__main__":
    main()
