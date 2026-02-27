#!/usr/bin/env python3
"""Select representative images from any dataset for metadata audit.

Generic stratified sampling tool that works with any dataset registered
in ``audit_config.py``.  Uses the dataset's configured stratification
axes to partition samples into strata, then applies proportional
allocation to select a representative subset.

**Phase 4.5 mode** (default): Stratified sampling for audit review.

Dynamic sample sizing:
    - N < 200:           audit 100 % of samples (no stratification)
    - 200 <= N < 10000:  default 36 samples
    - N >= 10000:        min(36, ceil(sqrt(N))) samples
    - ``--sample-size``  overrides all auto-scaling

**Phase 6 mode** (``--phase6``): Metadata-driven VLM sample selection.
Generates Track A (failing samples), Track B (contact sheet batch), and
Track C (passing validation) sample sets entirely from prescreening
results and metadata JSON -- no filesystem directory scanning.  This
avoids OOM issues on large network-mounted dataset directories (500K+).

Usage::

    # Phase 4.5: stratified audit sampling
    python -m scripts.audit.select_audit_samples --dataset diqa-5000
    python -m scripts.audit.select_audit_samples --dataset doclaynet --seed 42

    # Phase 6: metadata-driven VLM sampling
    python -m scripts.audit.select_audit_samples --dataset pubtabnet --phase6
    python -m scripts.audit.select_audit_samples --dataset pubtabnet --phase6 --tier 2
    python -m scripts.audit.select_audit_samples --dataset pubtabnet --phase6 --track-b-size 500
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


def _distribute_shortfall(
    allocation: dict[str, int],
    proportions: dict[str, float],
    shortfall: int,
) -> None:
    """Add shortfall samples to strata with the largest fractional remainders."""
    remainders = {key: proportions[key] - allocation[key] for key in proportions}
    sorted_keys = sorted(remainders, key=lambda k: remainders[k], reverse=True)
    for key in sorted_keys[:shortfall]:
        allocation[key] += 1


def _reduce_surplus(
    allocation: dict[str, int],
    proportions: dict[str, float],
    surplus: int,
) -> None:
    """Remove surplus samples from strata with the smallest fractional parts."""
    remainders = {key: proportions[key] - int(proportions[key]) for key in proportions}
    sorted_keys = sorted(remainders, key=lambda k: remainders[k])
    remaining = surplus
    for key in sorted_keys:
        if remaining <= 0:
            break
        if allocation[key] > 1:
            allocation[key] -= 1
            remaining -= 1


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

    proportions: dict[str, float] = {
        key: (len(recs) / total_population) * target for key, recs in strata.items()
    }

    allocation: dict[str, int] = {
        key: max(1, int(prop)) for key, prop in proportions.items()
    }

    allocated = sum(allocation.values())
    if allocated < target:
        _distribute_shortfall(allocation, proportions, target - allocated)
    elif allocated > target:
        _reduce_surplus(allocation, proportions, allocated - target)

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
    rng = random.Random(seed)  # nosec B311

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
# Phase 6: Metadata-driven VLM sample selection
# ---------------------------------------------------------------------------
_TRACK_B_DEFAULT_CAP = 10_000

# Structural validation fields that VLM cannot visually verify.
# These are excluded from Track A sample selection.
_TRACK_A_SKIP_FIELDS: frozenset[str] = frozenset(
    {
        "layout_bbox_valid",
        "image_properties_color_mode",
        "quality_overall_mos",
    }
)

# Large-dataset threshold: above this, use fixed counts only
# (not percentage) per README Scale-Aware Processing Guidance.
_LARGE_DATASET_THRESHOLD = 100_000


def load_prescreening(dataset_name: str) -> dict[str, Any]:
    """Load automated prescreening results for a dataset.

    Args:
        dataset_name: Canonical dataset name.

    Returns:
        Parsed prescreening JSON.

    Raises:
        FileNotFoundError: If prescreening results don't exist.
    """
    path = SCRIPT_DIR / "results" / dataset_name / "automated_screening.json"
    if not path.exists():
        msg = (
            f"Prescreening results not found at {path}. "
            f"Run automated_prescreening.py --dataset {dataset_name} first."
        )
        raise FileNotFoundError(msg)

    with open(path) as fh:
        return json.load(fh)


def compute_tier(prescreening: dict[str, Any]) -> int:
    """Determine VLM sampling tier from prescreening signals.

    Uses the highest tier triggered by any signal per the
    Adaptive VLM Sampling Policy (README.md).

    Signals checked:
        - Prescreening pass rate (>= 85% -> T1, 50-84% -> T2, < 50% -> T3)
        - Fields at 0% pass (0-1 -> T1, 2-3 -> T2, 4+ -> T3)

    Defect catalog and cross-source disagreement require manual
    tier adjustment via ``--tier``.

    Args:
        prescreening: Parsed prescreening JSON.

    Returns:
        Tier level (1, 2, or 3).
    """
    tier = 1

    total = prescreening.get("total_samples", 0)
    passed = prescreening.get("passed_all", 0)

    if total > 0:
        pass_rate = passed / total * 100
        if pass_rate < 50:
            tier = max(tier, 3)
        elif pass_rate < 85:
            tier = max(tier, 2)

    per_field = prescreening.get("per_field_results", {})
    zero_fields = sum(1 for v in per_field.values() if v.get("pass", 0) == 0)
    if zero_fields >= 4:
        tier = max(tier, 3)
    elif zero_fields >= 2:
        tier = max(tier, 2)

    return tier


def _tier_track_a_per_flag(tier: int, total: int) -> int:
    """Track A sample count per flag based on tier.

    For datasets > 100K, uses fixed counts only (not percentage)
    per Scale-Aware Processing Guidance in README.md.
    """
    fixed = {1: 10, 2: 15, 3: 25}[tier]
    if total > _LARGE_DATASET_THRESHOLD:
        return fixed
    if tier == 1:
        return max(10, math.ceil(total * 0.03))
    if tier == 2:
        return max(15, math.ceil(total * 0.10))
    return max(25, math.ceil(total * 0.15))


def _tier_track_c_count(tier: int, total: int) -> int:
    """Track C passing sample count based on tier.

    For datasets > 100K, uses fixed counts only (not percentage)
    per Scale-Aware Processing Guidance in README.md.
    """
    fixed = {1: 10, 2: 15, 3: 25}[tier]
    if total > _LARGE_DATASET_THRESHOLD:
        return fixed
    if tier == 1:
        return max(10, math.ceil(total * 0.02))
    if tier == 2:
        return max(15, math.ceil(total * 0.05))
    return max(25, math.ceil(total * 0.10))


def _tier_track_b_target(tier: int, total: int) -> int:
    """Track B target count based on tier, capped for practicality."""
    if tier == 1:
        raw = max(40, math.ceil(total * 0.05))
    elif tier == 2:
        raw = max(75, math.ceil(total * 0.15))
    else:
        raw = max(120, math.ceil(total * 0.25))
    return min(raw, _TRACK_B_DEFAULT_CAP)


def _load_phase6_data(
    config: DatasetAuditConfig,
    axes: tuple[str, ...],
) -> tuple[list[SampleRecord], dict[str, dict[str, str]]]:
    """Load metadata for Phase 6: sample records + ID lookup.

    Loads the metadata JSON once and builds both the SampleRecord
    list (for stratified sampling) and an ID-to-info lookup
    (for resolving failing sample filenames from prescreening).

    This avoids filesystem directory scanning entirely -- all
    filenames come from the metadata JSON.

    Args:
        config: Dataset audit configuration.
        axes: Stratification axes for sampling.

    Returns:
        Tuple of (records, id_lookup) where id_lookup maps
        image_id to {original_filename, original_path, split}.

    Raises:
        FileNotFoundError: If metadata JSON path not configured.
        ValueError: If metadata JSON has no samples.
    """
    path = config.metadata_json_path
    if path is None:
        msg = f"No metadata_json_path configured for '{config.dataset_name}'"
        raise FileNotFoundError(msg)

    logger.info("Loading Phase 6 data from %s", path)
    with open(path) as fh:
        metadata = json.load(fh)

    raw_samples: list[dict[str, Any]] = metadata.get("samples", [])
    if not raw_samples:
        msg = f"No 'samples' array in {path}"
        raise ValueError(msg)

    records: list[SampleRecord] = []
    id_lookup: dict[str, dict[str, str]] = {}

    for sample in raw_samples:
        source = sample.get("source", {})
        enrichment_data = _extract_enrichment_data(sample)
        sample_id = sample.get("id", "")
        filename = source.get("original_filename", "")
        image_path = source.get("original_path", "")
        split = enrichment_data.get("split") or sample.get("split", "unknown")

        axis_vals: dict[str, str] = {}
        for axis in axes:
            axis_vals[axis] = _extract_axis_value(enrichment_data, axis)
        stratum_key = "|".join(f"{a}={axis_vals[a]}" for a in axes)

        records.append(
            SampleRecord(
                sample_id=sample_id,
                image_path=image_path,
                original_filename=filename,
                dataset_name=config.dataset_name,
                axis_values=axis_vals,
                stratum_key=stratum_key,
            )
        )

        id_lookup[sample_id] = {
            "original_filename": filename,
            "original_path": image_path,
            "split": split,
        }

    logger.info("Loaded %d records + ID lookup", len(records))
    return records, id_lookup


def _select_track_a(
    prescreening: dict[str, Any],
    id_lookup: dict[str, dict[str, str]],
    per_flag_limit: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Select Track A samples: failing samples grouped by field.

    For each field that has failures, selects up to per_flag_limit
    samples (or all if fewer exist). Deduplicates across flags so
    the ``samples`` list has unique image entries.

    Args:
        prescreening: Parsed prescreening JSON.
        id_lookup: Mapping from image_id to file info.
        per_flag_limit: Maximum samples per failing field.
        rng: Seeded random instance.

    Returns:
        Track A output dict with per-flag and deduplicated samples.
    """
    failing_samples = prescreening.get("failing_samples", [])
    per_field = prescreening.get("per_field_results", {})

    by_field: dict[str, list[dict[str, Any]]] = {}
    for fs in failing_samples:
        for fld in fs.get("failed_fields", []):
            if fld in _TRACK_A_SKIP_FIELDS:
                continue
            by_field.setdefault(fld, []).append(fs)

    all_selected: list[dict[str, Any]] = []
    per_flag_selections: dict[str, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()

    for field_name in sorted(by_field):
        candidates = list(by_field[field_name])
        rng.shuffle(candidates)
        selected = candidates[:per_flag_limit]

        flag_entries: list[dict[str, Any]] = []
        for entry in selected:
            img_id = entry.get("image_id", "")
            info = id_lookup.get(img_id, {})
            rec = {
                "filename": info.get("original_filename", img_id),
                "image_path": info.get("original_path", ""),
                "split": info.get("split", "unknown"),
                "failed_field": field_name,
                "failed_reason": entry.get("details", {}).get(field_name, ""),
                "purpose": "flag_verification",
            }
            flag_entries.append(rec)
            if img_id not in seen_ids:
                all_selected.append(rec)
                seen_ids.add(img_id)

        per_flag_selections[field_name] = flag_entries

    return {
        "per_flag_limit": per_flag_limit,
        "per_flag_counts": {k: len(v) for k, v in per_flag_selections.items()},
        "per_flag_available": {
            k: per_field.get(k, {}).get("fail", 0) for k in by_field
        },
        "per_flag_samples": per_flag_selections,
        "total_unique_samples": len(all_selected),
        "samples": all_selected,
    }


def _select_track_b(
    records: list[SampleRecord],
    target: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Select Track B samples: stratified random for contact sheets.

    Args:
        records: All sample records from metadata.
        target: Number of samples to select.
        rng: Seeded random instance.

    Returns:
        Track B output dict with sample list.
    """
    selected = select_stratified(records, target, rng)

    samples = []
    for rec in selected:
        samples.append(
            {
                "filename": rec.original_filename,
                "image_path": rec.image_path,
                "purpose": "batch_classification",
            }
        )

    return {"total_samples": len(samples), "samples": samples}


def _select_track_c(
    records: list[SampleRecord],
    failing_ids: set[str],
    target: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Select Track C samples: passing samples only.

    Filters out all samples that failed any prescreening field,
    then applies stratified sampling to the remaining population.

    Args:
        records: All sample records from metadata.
        failing_ids: Set of image_ids that failed prescreening.
        target: Number of passing samples to select.
        rng: Seeded random instance.

    Returns:
        Track C output dict with sample list.
    """
    passing = [r for r in records if r.sample_id not in failing_ids]
    logger.info("Track C: %d passing / %d total", len(passing), len(records))
    selected = select_stratified(passing, target, rng)

    samples = []
    for rec in selected:
        samples.append(
            {
                "filename": rec.original_filename,
                "image_path": rec.image_path,
                "purpose": "passing_validation",
            }
        )

    return {"total_samples": len(samples), "samples": samples}


def run_phase6_selection(
    dataset_name: str,
    seed: int = DEFAULT_SEED,
    tier_override: int | None = None,
    track_b_size: int | None = None,
    dry_run: bool = False,
) -> dict[str, dict[str, Any]]:
    """Execute Phase 6 metadata-driven sample selection.

    Generates Track A, B, and C sample sets from prescreening
    results and metadata JSON with **no filesystem directory
    scanning**. All filenames are resolved from the Layer 2
    metadata JSON, avoiding OOM issues from ``Path.iterdir()``
    on large network-mounted dataset directories.

    Args:
        dataset_name: Canonical dataset name.
        seed: Random seed for reproducibility.
        tier_override: Force a specific tier (1-3) instead of
            auto-computing from prescreening signals.
        track_b_size: Override Track B sample count.
        dry_run: Print summary without writing output files.

    Returns:
        Dict mapping track name ('track_a', 'track_b', 'track_c')
        to track output data.

    Raises:
        FileNotFoundError: If prescreening or metadata is missing.
        ValueError: If dataset name is not recognised.
    """
    rng = random.Random(seed)  # nosec B311

    # 1. Load prescreening results
    prescreening = load_prescreening(dataset_name)
    total = prescreening.get("total_samples", 0)

    # 2. Compute tier
    tier = tier_override if tier_override is not None else compute_tier(prescreening)
    logger.info("Phase 6 tier=%d (override=%s)", tier, tier_override is not None)

    # 3. Load config + metadata (single load)
    config = load_dataset_config(dataset_name)
    records, id_lookup = _load_phase6_data(config, config.stratification_axes)

    # 4. Compute sample counts per tier
    a_per_flag = _tier_track_a_per_flag(tier, total)
    b_target = track_b_size or _tier_track_b_target(tier, total)
    c_count = _tier_track_c_count(tier, total)

    # 5. Track A: failing samples per flag
    track_a = _select_track_a(prescreening, id_lookup, a_per_flag, rng)

    # 6. Track B: contact sheet samples (datasets > 2,000 only)
    track_b: dict[str, Any] | None = None
    if total > 2000:
        track_b = _select_track_b(records, b_target, rng)

    # 7. Track C: passing sample validation
    # Exclude structural fields from the "failing" definition so that
    # samples only failing non-VLM fields are still eligible for Track C.
    failing_ids: set[str] = set()
    for fs in prescreening.get("failing_samples", []):
        vlm_failures = [
            f for f in fs.get("failed_fields", []) if f not in _TRACK_A_SKIP_FIELDS
        ]
        if vlm_failures:
            failing_ids.add(fs["image_id"])
    track_c = _select_track_c(records, failing_ids, c_count, rng)

    # 8. Attach common metadata to each track
    now_iso = datetime.now(tz=UTC).isoformat()
    common: dict[str, Any] = {
        "dataset": dataset_name,
        "tier": tier,
        "generated_at": now_iso,
    }

    track_a.update(common)
    track_a["track"] = "A"
    track_a["purpose"] = "Content flag verification on flagged/failing samples"

    if track_b is not None:
        track_b.update(common)
        track_b["track"] = "B"
        track_b["purpose"] = "Contact sheet batch classification"

    track_c.update(common)
    track_c["track"] = "C"
    track_c["purpose"] = "Passing sample validation"

    # 9. Print summary
    width = 60
    print(f"\n{'Phase 6 Sample Selection':^{width}}")
    print("-" * width)
    print(f"  Dataset:     {dataset_name}")
    print(f"  Population:  {total:,}")
    print(f"  Tier:        {tier}")
    print("-" * width)
    a_count = track_a["total_unique_samples"]
    print(
        f"  Track A:     {a_count} unique samples "
        f"across {len(track_a['per_flag_counts'])} flags"
    )
    for fld, cnt in sorted(track_a["per_flag_counts"].items()):
        avail = track_a["per_flag_available"].get(fld, "?")
        print(f"    {fld}: {cnt} selected / {avail} available")
    if track_b is not None:
        print(f"  Track B:     {track_b['total_samples']} samples for contact sheets")
    print(f"  Track C:     {track_c['total_samples']} passing samples")
    print("-" * width)

    # 10. Write output files
    outputs: dict[str, dict[str, Any]] = {
        "track_a": track_a,
        "track_c": track_c,
    }
    if track_b is not None:
        outputs["track_b"] = track_b

    if not dry_run:
        results_dir = SCRIPT_DIR / "results" / dataset_name
        results_dir.mkdir(parents=True, exist_ok=True)
        for key, data in outputs.items():
            out_path = results_dir / f"phase6_{key}_samples.json"
            with open(out_path, "w") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            print(f"  Wrote: {out_path}")
    else:
        print("\n[DRY RUN] No output files written.")

    return outputs


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

    # Phase 6 arguments
    phase6_group = parser.add_argument_group("Phase 6 (metadata-driven VLM sampling)")
    phase6_group.add_argument(
        "--phase6",
        action="store_true",
        help=(
            "Phase 6 mode: generate Track A/B/C sample sets from "
            "prescreening results and metadata JSON. No filesystem "
            "directory scanning -- all filenames resolved from metadata."
        ),
    )
    phase6_group.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help=(
            "Override auto-computed VLM sampling tier (1=Standard, "
            "2=Enhanced, 3=Comprehensive). Default: auto from prescreening."
        ),
    )
    phase6_group.add_argument(
        "--track-b-size",
        type=int,
        default=None,
        help=(
            "Override Track B contact sheet sample count. "
            "Default: tier-based formula, capped at 10,000."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        if args.phase6:
            run_phase6_selection(
                dataset_name=args.dataset,
                seed=args.seed,
                tier_override=args.tier,
                track_b_size=args.track_b_size,
                dry_run=args.dry_run,
            )
        else:
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
