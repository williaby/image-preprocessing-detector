#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Select representative images from any dataset for metadata audit.

Generic stratified sampling tool that works with any dataset registered
in ``audit_config.py``.  Uses the dataset's configured stratification
axes to partition samples into strata, then applies proportional
allocation to select a representative subset.

Dynamic sample sizing:
    - N < 200:           audit 100 % of samples (no stratification)
    - 200 <= N < 10000:  default 36 samples
    - N >= 10000:        min(36, ceil(sqrt(N))) samples
    - ``--sample-size``  overrides all auto-scaling

Usage::

    python -m scripts.audit.select_audit_samples --dataset diqa-5000
    python -m scripts.audit.select_audit_samples --dataset doclaynet --seed 42
    python -m scripts.audit.select_audit_samples --dataset funsd --dry-run
    python -m scripts.audit.select_audit_samples --dataset sroie -v
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.audit.audit_config import (
    DatasetAuditConfig,
    list_known_datasets,
    load_dataset_config,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_SEED = 2026
SCRIPT_DIR = Path(__file__).resolve().parent

# Boolean-typed stratification axes (converted to "true"/"false" strings)
_BOOLEAN_AXES: frozenset[str] = frozenset({"has_table", "has_handwriting"})

# Mapping from stratification axis name to the nested path inside
# the enrichment ``data`` dict.  Most axes are direct field names;
# ``quality_overall`` sits one level deeper.
_AXIS_FIELD_MAP: dict[str, str] = {
    "capture_method": "capture_method",
    "domain_level1": "domain_level1",
    "resolution_category": "resolution_category",
    "quality_overall": "quality_overall",
    "layout_type": "layout_type",
    "text_density": "text_density",
    "script_family": "script_family",
    "has_table": "has_table",
    "has_handwriting": "has_handwriting",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class SampleRecord:
    """Lightweight record for a single candidate sample."""

    sample_id: str
    image_path: str
    original_filename: str
    dataset_name: str
    axis_values: dict[str, str] = field(default_factory=dict)
    stratum_key: str = ""
    selection_reason: str = ""

    def to_output_dict(self) -> dict[str, Any]:
        """Serialize for the output JSON."""
        return {
            "sample_id": self.sample_id,
            "image_path": self.image_path,
            "original_filename": self.original_filename,
            "dataset_name": self.dataset_name,
            "axis_values": self.axis_values,
            "stratum_key": self.stratum_key,
            "selection_reason": self.selection_reason,
        }


# ---------------------------------------------------------------------------
# Dynamic sample sizing
# ---------------------------------------------------------------------------
def compute_sample_size(
    total_samples: int,
    override: int | None = None,
    config_default: int = 36,
) -> int:
    """Determine the target sample count using dynamic scaling.

    Args:
        total_samples: Total number of available samples.
        override: Explicit ``--sample-size`` value (takes priority).
        config_default: Default from the dataset config.

    Returns:
        Target number of samples to select.
    """
    if override is not None:
        return override

    if total_samples < 200:
        return total_samples  # audit all

    if total_samples < 10_000:
        return config_default

    return min(config_default, math.ceil(math.sqrt(total_samples)))


# ---------------------------------------------------------------------------
# Enrichment field extraction
# ---------------------------------------------------------------------------
def _extract_enrichment_data(sample: dict[str, Any]) -> dict[str, Any]:
    """Return the data dict from the latest enrichment version.

    Navigates ``sample["enrichments"]["versions"][-1]["data"]``.
    Returns an empty dict when no enrichment is available.
    """
    enrichments = sample.get("enrichments", {})
    versions = enrichments.get("versions", [])
    if not versions:
        return {}
    return versions[-1].get("data", {})


def _extract_axis_value(
    data: dict[str, Any],
    axis: str,
) -> str:
    """Extract a single stratification axis value from enrichment data.

    Args:
        data: The ``data`` dict from the latest enrichment version.
        axis: One of the valid stratification axis names.

    Returns:
        A string representation suitable for grouping.  Missing or
        ``None`` values become ``"unknown"``.
    """
    field_name = _AXIS_FIELD_MAP.get(axis, axis)
    raw = data.get(field_name)

    if raw is None:
        return "unknown"

    if axis in _BOOLEAN_AXES:
        return "true" if raw else "false"

    # quality_overall is a float 0-1; bucket into low/mid/high
    if axis == "quality_overall":
        try:
            score = float(raw)
        except (TypeError, ValueError):
            return "unknown"
        if score < 0.4:
            return "low"
        if score < 0.7:
            return "mid"
        return "high"

    return str(raw)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_samples(
    config: DatasetAuditConfig,
    axes: tuple[str, ...],
) -> list[SampleRecord]:
    """Load metadata JSON and build sample records with axis values.

    Args:
        config: Dataset audit configuration.
        axes: Stratification axes to extract from enrichments.

    Returns:
        List of ``SampleRecord`` instances.

    Raises:
        FileNotFoundError: If the metadata JSON does not exist.
        ValueError: If the metadata JSON is missing ``"samples"``.
    """
    path = config.metadata_json_path
    if path is None:
        msg = f"No metadata_json_path configured for dataset '{config.dataset_name}'."
        raise FileNotFoundError(msg)

    logger.info("Loading metadata from %s", path)
    with open(path) as fh:
        metadata = json.load(fh)

    raw_samples: list[dict[str, Any]] = metadata.get("samples", [])
    if not raw_samples:
        msg = f"No 'samples' array found in {path}"
        raise ValueError(msg)

    records: list[SampleRecord] = []
    for sample in raw_samples:
        source = sample.get("source", {})
        enrichment_data = _extract_enrichment_data(sample)

        axis_vals: dict[str, str] = {}
        for axis in axes:
            axis_vals[axis] = _extract_axis_value(enrichment_data, axis)

        stratum_key = "|".join(f"{axis}={axis_vals[axis]}" for axis in axes)

        records.append(
            SampleRecord(
                sample_id=sample.get("id", ""),
                image_path=source.get("original_path", ""),
                original_filename=source.get("original_filename", ""),
                dataset_name=config.dataset_name,
                axis_values=axis_vals,
                stratum_key=stratum_key,
            )
        )

    logger.info("Loaded %d sample records", len(records))
    return records


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------
def build_strata(
    records: list[SampleRecord],
) -> dict[str, list[SampleRecord]]:
    """Partition records into strata by their composite stratum key.

    Args:
        records: All candidate sample records.

    Returns:
        Mapping from stratum key to list of records.
    """
    strata: dict[str, list[SampleRecord]] = {}
    for rec in records:
        strata.setdefault(rec.stratum_key, []).append(rec)
    return strata


def allocate_proportional(
    strata: dict[str, list[SampleRecord]],
    target: int,
) -> dict[str, int]:
    """Compute proportional allocation across strata.

    Uses largest-remainder method to distribute *target* samples
    proportionally to stratum sizes while ensuring every non-empty
    stratum gets at least 1 sample (up to *target*).

    Args:
        strata: Mapping of stratum key to records.
        target: Total number of samples to select.

    Returns:
        Mapping from stratum key to number of samples allocated.
    """
    total_population = sum(len(v) for v in strata.values())
    if total_population == 0:
        return {}

    # Initial float proportions
    proportions: dict[str, float] = {
        key: (len(recs) / total_population) * target for key, recs in strata.items()
    }

    # Floor allocation (each stratum gets at least 1 if non-empty)
    allocation: dict[str, int] = {}
    for key in proportions:
        allocation[key] = max(1, int(proportions[key]))

    # Adjust if we over- or under-allocated
    allocated = sum(allocation.values())
    if allocated < target:
        # Distribute remainder by largest fractional part
        remainders = {key: proportions[key] - allocation[key] for key in proportions}
        sorted_keys = sorted(
            remainders,
            key=lambda k: remainders[k],
            reverse=True,
        )
        shortfall = target - allocated
        for key in sorted_keys[:shortfall]:
            allocation[key] += 1
    elif allocated > target:
        # Shrink strata with smallest fractional parts first
        remainders = {
            key: proportions[key] - int(proportions[key]) for key in proportions
        }
        sorted_keys = sorted(remainders, key=lambda k: remainders[k])
        surplus = allocated - target
        for key in sorted_keys:
            if surplus <= 0:
                break
            if allocation[key] > 1:
                allocation[key] -= 1
                surplus -= 1

    return allocation


def select_stratified(
    records: list[SampleRecord],
    target: int,
    rng: random.Random,
) -> list[SampleRecord]:
    """Run proportional stratified sampling.

    Args:
        records: All candidate sample records.
        target: Number of samples to select.
        rng: Seeded random instance for reproducibility.

    Returns:
        List of selected ``SampleRecord`` instances.
    """
    if target >= len(records):
        for rec in records:
            rec.selection_reason = "full population (N < target)"
        return list(records)

    strata = build_strata(records)
    allocation = allocate_proportional(strata, target)

    logger.info(
        "Proportional allocation across %d strata for %d samples",
        len(strata),
        target,
    )

    selected: list[SampleRecord] = []
    for key, count in allocation.items():
        candidates = list(strata[key])
        rng.shuffle(candidates)
        picks = candidates[:count]
        for pick in picks:
            pick.selection_reason = f"stratum={key}"
        selected.extend(picks)

    # If rounding left us short, fill from remaining pool
    if len(selected) < target:
        selected_ids = {r.sample_id for r in selected}
        remaining = [r for r in records if r.sample_id not in selected_ids]
        rng.shuffle(remaining)
        shortfall = target - len(selected)
        for rec in remaining[:shortfall]:
            rec.selection_reason = "proportional fill"
        selected.extend(remaining[:shortfall])

    return selected


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------
def build_output(
    selected: list[SampleRecord],
    config: DatasetAuditConfig,
    total_population: int,
    seed: int,
    axes: tuple[str, ...],
) -> dict[str, Any]:
    """Build the final JSON output structure.

    Args:
        selected: Selected sample records.
        config: Dataset audit configuration.
        total_population: Total number of available samples.
        seed: Random seed used.
        axes: Stratification axes used.

    Returns:
        Dictionary ready for JSON serialization.
    """
    # Distribution by stratum
    stratum_dist: dict[str, int] = {}
    for rec in selected:
        stratum_dist[rec.stratum_key] = stratum_dist.get(rec.stratum_key, 0) + 1

    # Per-axis value distribution
    axis_distributions: dict[str, dict[str, int]] = {}
    for axis in axes:
        counter: Counter[str] = Counter()
        for rec in selected:
            counter[rec.axis_values.get(axis, "unknown")] += 1
        axis_distributions[axis] = dict(
            sorted(counter.items(), key=lambda x: x[1], reverse=True)
        )

    return {
        "dataset": config.dataset_name,
        "sample_count": len(selected),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "random_seed": seed,
        "selection_criteria": {
            "total_population": total_population,
            "target_count": len(selected),
            "stratification_axes": list(axes),
            "sizing_rule": _describe_sizing_rule(total_population),
        },
        "distribution_summary": {
            "by_stratum": dict(
                sorted(
                    stratum_dist.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "by_axis": axis_distributions,
        },
        "samples": [rec.to_output_dict() for rec in selected],
    }


def _describe_sizing_rule(total: int) -> str:
    """Return a human-readable description of the auto-sizing rule."""
    if total < 200:
        return f"full_population (N={total} < 200)"
    if total < 10_000:
        return "default_36 (200 <= N < 10000)"
    return f"sqrt_scaling (N={total}, ceil(sqrt)={math.ceil(math.sqrt(total))})"


# ---------------------------------------------------------------------------
# Summary printing
# ---------------------------------------------------------------------------
def print_summary(
    selected: list[SampleRecord],
    config: DatasetAuditConfig,
    total_population: int,
    axes: tuple[str, ...],
) -> None:
    """Print a human-readable distribution table.

    Args:
        selected: Selected sample records.
        config: Dataset audit configuration.
        total_population: Total number of available samples.
        axes: Stratification axes used.
    """
    header = f"{config.dataset_name} Audit Sample Selection Summary"
    width = max(62, len(header) + 4)
    sep = "-" * width

    print(f"\n{header:^{width}}")
    print(sep)
    print(f"  Population:       {total_population}")
    print(f"  Selected:         {len(selected)}")
    print(f"  Axes:             {', '.join(axes)}")
    print(sep)

    # Per-axis distributions
    for axis in axes:
        counter: Counter[str] = Counter()
        for rec in selected:
            counter[rec.axis_values.get(axis, "unknown")] += 1

        print(f"\n  {axis}:")
        print(f"    {'Value':<30} {'Count':>6}")
        print(f"    {'-' * 30} {'-' * 6}")
        for value, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
            print(f"    {value:<30} {count:>6}")

    # Stratum distribution (top 20)
    stratum_counter: Counter[str] = Counter()
    for rec in selected:
        stratum_counter[rec.stratum_key] += 1

    num_strata = len(stratum_counter)
    show_count = min(20, num_strata)
    print(f"\n  Strata ({num_strata} total, showing top {show_count}):")
    print(f"    {'Stratum Key':<50} {'Count':>6}")
    print(f"    {'-' * 50} {'-' * 6}")
    for key, count in stratum_counter.most_common(show_count):
        display_key = key if len(key) <= 50 else key[:47] + "..."
        print(f"    {display_key:<50} {count:>6}")
    if num_strata > show_count:
        print(f"    ... and {num_strata - show_count} more strata")

    print(sep)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run_selection(
    dataset_name: str,
    seed: int = DEFAULT_SEED,
    sample_size_override: int | None = None,
    dry_run: bool = False,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Execute the full sample selection pipeline.

    Args:
        dataset_name: Canonical dataset name from the audit registry.
        seed: Random seed for reproducibility.
        sample_size_override: Explicit sample size (bypasses auto-scaling).
        dry_run: If True, print summary but do not write output file.
        output_path: Custom output file path. Defaults to
            ``scripts/audit/results/{dataset}/sample_set.json``.

    Returns:
        The output JSON structure.

    Raises:
        ValueError: If the dataset name is not recognised.
        FileNotFoundError: If the metadata JSON is missing.
    """
    rng = random.Random(seed)

    # Step 1: Load configuration
    config = load_dataset_config(
        dataset_name,
        sample_size=sample_size_override,
    )
    axes = config.stratification_axes
    logger.info(
        "Dataset=%s  axes=%s  config_sample_size=%d",
        config.dataset_name,
        axes,
        config.sample_size,
    )

    # Step 2: Load and parse samples
    records = load_samples(config, axes)
    total_population = len(records)

    # Step 3: Compute target sample size
    target = compute_sample_size(
        total_population,
        override=sample_size_override,
        config_default=config.sample_size,
    )
    logger.info(
        "Population=%d  target=%d  rule=%s",
        total_population,
        target,
        _describe_sizing_rule(total_population),
    )

    # Step 4: Stratified selection
    selected = select_stratified(records, target, rng)
    logger.info("Selected %d samples", len(selected))

    # Step 5: Print summary
    print_summary(selected, config, total_population, axes)

    # Step 6: Build output
    output = build_output(selected, config, total_population, seed, axes)

    # Step 7: Write output
    if not dry_run:
        if output_path is None:
            output_path = SCRIPT_DIR / "results" / dataset_name / "sample_set.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False)
        logger.info("Wrote %d samples to %s", len(selected), output_path)
        print(f"\nOutput written to: {output_path}")
    else:
        print("\n[DRY RUN] No output file written.")

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point for CLI execution."""
    known = list_known_datasets()

    parser = argparse.ArgumentParser(
        description=(
            "Select representative samples from any dataset for Layer 2 metadata audit."
        ),
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=known,
        metavar="NAME",
        help=(f"Dataset to sample from. Known datasets: {', '.join(known)}."),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help=(
            "Override auto-scaled sample count.  "
            "Without this flag, sample size is computed dynamically."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing output file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Custom output file path.  Defaults to "
            "scripts/audit/results/{dataset}/sample_set.json."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        run_selection(
            dataset_name=args.dataset,
            seed=args.seed,
            sample_size_override=args.sample_size,
            dry_run=args.dry_run,
            output_path=args.output,
        )
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
