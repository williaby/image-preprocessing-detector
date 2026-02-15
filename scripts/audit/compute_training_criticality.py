#!/usr/bin/env python3
"""Compute training criticality scores from task index references.

Parses the 7 task index files in docs/datasets/indices/ to count how
many training tasks reference each dataset and with what role weight.
Outputs a criticality score (1-5) per dataset.

Usage::

    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/compute_training_criticality.py

    # Show details
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/compute_training_criticality.py --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "training_criticality.yaml"
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Load training criticality configuration.

    Args:
        config_path: Override config path.

    Returns:
        Parsed YAML config dict.
    """
    path = config_path or CONFIG_PATH
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DatasetReference:
    """A single reference to a dataset in a task index.

    Attributes:
        dataset: Canonical dataset name.
        task_index: Path to the task index file.
        role: Role type (primary, supplementary, benchmark).
        weight: Computed weight for this reference.
    """

    dataset: str
    task_index: str
    role: str
    weight: float


@dataclass
class CriticalityResult:
    """Training criticality computation for a dataset.

    Attributes:
        dataset: Canonical dataset name.
        weighted_score: Sum of weighted references.
        criticality: Criticality level (1-5).
        references: Individual references found.
        task_count: Number of distinct tasks referencing this dataset.
    """

    dataset: str
    weighted_score: float = 0.0
    criticality: int = 1
    references: list[DatasetReference] = field(default_factory=list)
    task_count: int = 0


# ---------------------------------------------------------------------------
# Task index parsing
# ---------------------------------------------------------------------------
# Regex to extract dataset names from markdown table rows
# Matches: | dataset-name | or | dataset_name |
_TABLE_ROW_RE = re.compile(
    r"^\|\s*([a-z0-9][a-z0-9_-]*[a-z0-9])\s*\|",
    re.IGNORECASE,
)

# Also matches dataset names in markdown links: [dataset-name.md](...)
_LINK_RE = re.compile(
    r"\[([a-z0-9][a-z0-9_-]*[a-z0-9])\.md\]",
    re.IGNORECASE,
)


def _classify_section(
    line: str,
    section_markers: dict[str, list[str]],
) -> str | None:
    """Classify a markdown heading into a role type.

    Args:
        line: A markdown line (stripped).
        section_markers: Config mapping role -> list of heading prefixes.

    Returns:
        Role string or None if not a matching heading.
    """
    for role, markers in section_markers.items():
        for marker in markers:
            if line.startswith(marker):
                return role
    return None


def parse_task_index(
    index_path: Path,
    config: dict[str, Any],
) -> list[DatasetReference]:
    """Parse a single task index file for dataset references.

    Args:
        index_path: Path to the task index markdown file.
        config: Training criticality config.

    Returns:
        List of DatasetReference found in this index.
    """
    if not index_path.exists():
        log.warning("Task index not found: %s", index_path)
        return []

    role_weights = config.get("role_weights", {})
    section_markers = config.get("section_markers", {})

    content = index_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    current_role = "supplementary"  # Default for content before any section
    refs: list[DatasetReference] = []
    seen_datasets: set[str] = set()
    index_name = index_path.stem

    for line in lines:
        stripped = line.strip()

        # Check for section heading
        if stripped.startswith("##"):
            new_role = _classify_section(stripped, section_markers)
            if new_role:
                current_role = new_role

        # Extract dataset names from table rows
        table_match = _TABLE_ROW_RE.match(stripped)
        if table_match:
            ds_name = table_match.group(1).lower()
            # Skip header rows (contain words like "dataset", "images")
            if ds_name in ("dataset", "images", "source", "format"):
                continue
            if ds_name not in seen_datasets:
                seen_datasets.add(ds_name)
                weight = role_weights.get(current_role, 1.0)
                refs.append(
                    DatasetReference(
                        dataset=ds_name,
                        task_index=index_name,
                        role=current_role,
                        weight=weight,
                    )
                )

        # Also check for dataset names in markdown links
        for link_match in _LINK_RE.finditer(stripped):
            ds_name = link_match.group(1).lower()
            if ds_name not in seen_datasets:
                seen_datasets.add(ds_name)
                weight = role_weights.get(current_role, 1.0)
                refs.append(
                    DatasetReference(
                        dataset=ds_name,
                        task_index=index_name,
                        role=current_role,
                        weight=weight,
                    )
                )

    return refs


# ---------------------------------------------------------------------------
# Criticality computation
# ---------------------------------------------------------------------------
def compute_criticality(
    all_refs: list[DatasetReference],
    config: dict[str, Any],
) -> dict[str, CriticalityResult]:
    """Compute criticality scores from all references.

    Args:
        all_refs: All dataset references from all task indices.
        config: Training criticality config.

    Returns:
        Dict mapping dataset name to CriticalityResult.
    """
    scale_thresholds = config.get("scale_thresholds", {})
    overrides = config.get("overrides", {}) or {}

    # Group references by dataset
    by_dataset: dict[str, list[DatasetReference]] = {}
    for ref in all_refs:
        by_dataset.setdefault(ref.dataset, []).append(ref)

    results: dict[str, CriticalityResult] = {}
    for dataset, refs in by_dataset.items():
        weighted_score = sum(r.weight for r in refs)
        task_indices = {r.task_index for r in refs}

        # Determine criticality level
        criticality = 1
        for level in sorted(scale_thresholds.keys(), reverse=True):
            threshold = scale_thresholds[level]
            if weighted_score >= threshold:
                criticality = int(level)
                break

        # Apply manual override if present
        if dataset in overrides:
            criticality = int(overrides[dataset])

        results[dataset] = CriticalityResult(
            dataset=dataset,
            weighted_score=round(weighted_score, 2),
            criticality=criticality,
            references=refs,
            task_count=len(task_indices),
        )

    return results


def compute_all_criticality(
    *,
    config_path: Path | None = None,
) -> dict[str, CriticalityResult]:
    """Parse all task indices and compute criticality for all datasets.

    Args:
        config_path: Override config path.

    Returns:
        Dict mapping dataset name to CriticalityResult.
    """
    config = load_config(config_path)
    task_indices = config.get("task_indices", [])

    all_refs: list[DatasetReference] = []
    for index_rel_path in task_indices:
        index_path = PROJECT_ROOT / index_rel_path
        refs = parse_task_index(index_path, config)
        all_refs.extend(refs)
        log.info("Parsed %s: %d references", index_path.name, len(refs))

    return compute_criticality(all_refs, config)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_criticality_report(
    results: dict[str, CriticalityResult],
    *,
    output_path: Path | None = None,
) -> Path:
    """Write criticality scores to JSON.

    Args:
        results: Criticality results by dataset.
        output_path: Override output path.

    Returns:
        Path to written file.
    """
    path = output_path or (AUDIT_RESULTS_DIR / "training_criticality.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_datasets": len(results),
        "criticality_distribution": {},
        "datasets": {},
    }

    dist: dict[int, int] = {}
    for result in results.values():
        dist[result.criticality] = dist.get(result.criticality, 0) + 1
        report["datasets"][result.dataset] = {
            "criticality": result.criticality,
            "weighted_score": result.weighted_score,
            "task_count": result.task_count,
            "references": [
                {
                    "task": r.task_index,
                    "role": r.role,
                    "weight": r.weight,
                }
                for r in result.references
            ],
        }

    report["criticality_distribution"] = {str(k): v for k, v in sorted(dist.items())}

    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log.info("Criticality report written to %s", path)
    return path


def print_criticality(
    results: dict[str, CriticalityResult],
    *,
    verbose: bool = False,
) -> None:
    """Print criticality scores to console.

    Args:
        results: Criticality results by dataset.
        verbose: Show per-dataset details.
    """
    print(f"\n{'=' * 65}")
    print("Training Criticality Scores")
    print(f"{'=' * 65}")

    # Sort by criticality descending, then name
    sorted_results = sorted(
        results.values(),
        key=lambda r: (-r.criticality, r.dataset),
    )

    for result in sorted_results:
        print(
            f"  [{result.criticality}] {result.dataset:30s}  "
            f"score={result.weighted_score:5.1f}  "
            f"tasks={result.task_count}"
        )
        if verbose:
            for ref in result.references:
                print(f"       -> {ref.task_index} ({ref.role}, w={ref.weight})")

    # Distribution
    dist: dict[int, int] = {}
    for r in results.values():
        dist[r.criticality] = dist.get(r.criticality, 0) + 1
    print(f"\n  Distribution: {dict(sorted(dist.items()))}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments. Uses sys.argv if None.

    Returns:
        Exit code (always 0).
    """
    parser = argparse.ArgumentParser(
        description="Compute training criticality scores from task indices."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Override config path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output path.",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args(argv)

    results = compute_all_criticality(config_path=args.config)

    if not args.quiet:
        print_criticality(results, verbose=args.verbose)

    write_criticality_report(results, output_path=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
