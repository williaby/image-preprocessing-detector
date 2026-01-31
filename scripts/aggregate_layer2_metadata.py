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

Usage:
    python scripts/aggregate_layer2_metadata.py
    python scripts/aggregate_layer2_metadata.py --dataset tablebank
    python scripts/aggregate_layer2_metadata.py --output-dir custom/path/
"""

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from image_preprocessing_detector.schema_utils.dataset_source import DATASET_REGISTRY


def aggregate_dataset_metadata(
    dataset_name: str,
    layer2_dir: Path,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Aggregate Layer 2 metadata for a single dataset.

    Args:
        dataset_name: Canonical dataset name
        layer2_dir: Directory containing Layer 2 JSON files
        verbose: Print progress messages

    Returns:
        Dictionary with aggregated statistics
    """
    # Find Layer 2 metadata file for this dataset
    metadata_file = layer2_dir / f"{dataset_name}_metadata.json"

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

    stats: Dict[str, Any] = {
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
            # Extract latest enrichment version data
            enrichments = sample.get("enrichments", {})
            versions = enrichments.get("versions", [])
            if not versions:
                continue

            # Get latest version (last in array)
            latest = versions[-1]
            data = latest.get("data", {})

            # Capture method (direct string field)
            if "capture_method" in data:
                method = data["capture_method"]
                if method:
                    stats["capture_methods"][method] += 1

            # Domains (direct string field)
            if "domain_level1" in data:
                level1 = data["domain_level1"]
                if level1:
                    stats["domains"][level1] += 1

            # Layout type (if present)
            if "layout_type" in data:
                layout_type = data["layout_type"]
                if layout_type:
                    stats["layout_types"][layout_type] += 1

            # Text density (if present)
            if "text_density" in data:
                text_density = data["text_density"]
                if text_density:
                    stats["text_densities"][text_density] += 1

            # Language/Script (if present)
            if "script_code" in data:
                script_code = data["script_code"]
                if script_code:
                    stats["script_codes"][script_code] += 1

            if "script_family" in data:
                script_family = data["script_family"]
                if script_family:
                    stats["script_families"][script_family] += 1

            if "language_code" in data:
                language_code = data["language_code"]
                if language_code:
                    stats["language_codes"][language_code] += 1

            # Content flags (boolean fields)
            for flag in ["has_table", "has_formula", "has_handwriting", "has_signature", "has_figure"]:
                if flag in data and data[flag] is True:
                    stats["content_flags"][flag] += 1

            # Text scope (if present)
            if "text_scope" in data:
                scope = data["text_scope"]
                if scope:
                    stats["text_scopes"][scope] += 1

            # Content type (if present)
            if "content_type" in data:
                content_type = data["content_type"]
                if content_type:
                    stats["content_types"][content_type] += 1

            # Paper size (if present)
            if "detected_paper_size" in data:
                detected_size = data["detected_paper_size"]
                if detected_size:
                    stats["paper_sizes"][detected_size] += 1

            if "paper_orientation" in data:
                orientation = data["paper_orientation"]
                if orientation:
                    stats["paper_orientations"][orientation] += 1

        except Exception as e:
            if verbose:
                sample_id = sample.get("id", "unknown")
                print(f"⚠️  Error processing sample {sample_id}: {e}")
            continue

    # Compute summary statistics
    if stats["quality_scores"]:
        stats["quality_summary"] = {
            "min": round(min(stats["quality_scores"]), 3),
            "max": round(max(stats["quality_scores"]), 3),
            "mean": round(statistics.mean(stats["quality_scores"]), 3),
            "median": round(statistics.median(stats["quality_scores"]), 3),
            "stdev": round(statistics.stdev(stats["quality_scores"]), 3)
            if len(stats["quality_scores"]) > 1
            else 0,
        }
    else:
        stats["quality_summary"] = None

    # Degradation severity summaries
    degradation_summaries = {}
    for deg_type, severities in stats["degradation_severities"].items():
        if severities:
            degradation_summaries[deg_type] = {
                "mean_severity": round(statistics.mean(severities), 3),
                "max_severity": round(max(severities), 3),
            }
    stats["degradation_summaries"] = degradation_summaries

    # Convert counters to percentages
    total = stats["total_samples"]
    for key in [
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
    ]:
        counter = stats[key]
        if counter:
            stats[f"{key}_pct"] = {
                k: round(v / total * 100, 1) for k, v in counter.items()
            }
        else:
            stats[f"{key}_pct"] = {}

    # Content flags as percentages
    if stats["content_flags"]:
        stats["content_flags_pct"] = {
            k: round(v / total * 100, 1) for k, v in stats["content_flags"].items()
        }
    else:
        stats["content_flags_pct"] = {}

    # Top degradations (by frequency)
    if stats["degradation_types"]:
        top_degradations = stats["degradation_types"].most_common(5)
        stats["top_degradations"] = [
            {
                "type": deg_type,
                "count": count,
                "percentage": round(count / total * 100, 1),
                "mean_severity": degradation_summaries.get(deg_type, {}).get(
                    "mean_severity", 0
                ),
            }
            for deg_type, count in top_degradations
        ]
    else:
        stats["top_degradations"] = []

    # Top scripts (by frequency)
    if stats["script_codes"]:
        top_scripts = stats["script_codes"].most_common(10)
        stats["top_scripts"] = [
            {"script": script, "count": count, "percentage": round(count / total * 100, 1)}
            for script, count in top_scripts
        ]
    else:
        stats["top_scripts"] = []

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
            print(f"   Quality: {stats['quality_summary']['min']:.2f}-{stats['quality_summary']['max']:.2f} (μ={stats['quality_summary']['mean']:.2f})")

        if stats.get("top_degradations"):
            print(f"   Top degradations: {', '.join(d['type'] for d in stats['top_degradations'][:3])}")

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
