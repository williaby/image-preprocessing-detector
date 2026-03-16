#!/usr/bin/env python3
"""Cross-dataset regression suite for Layer 2 metadata quality.

Compares current prescreening results against stored baselines to detect
quality regressions. Supports single-dataset and all-dataset modes, with
KI cross-referencing to annotate regressions with known-issue identifiers.

Usage::

    # Check single dataset against baseline
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/regression_check.py --dataset jssoda

    # Check all datasets
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/regression_check.py --all-datasets

    # Save current screening as baseline
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/regression_check.py --dataset jssoda --update-baseline

    # Custom regression threshold (default: 5.0 percentage points)
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/regression_check.py --all-datasets --threshold 3.0
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"
KI_PATH = AUDIT_RESULTS_DIR / "CROSS_DATASET_KNOWN_ISSUES.json"

DEFAULT_THRESHOLD = 5.0  # percentage points


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FieldDelta:
    """Change in a single field's fail rate between baseline and current.

    Attributes:
        field_name: Name of the prescreening field.
        baseline_fail_rate: Fail rate in baseline (0-100).
        current_fail_rate: Fail rate in current screening (0-100).
        delta: Change in fail rate (positive = regression).
        is_regression: Whether delta exceeds threshold.
        related_ki: Cross-referenced KI identifier, if any.
    """

    field_name: str
    baseline_fail_rate: float
    current_fail_rate: float
    delta: float
    is_regression: bool
    related_ki: str | None = None


@dataclass
class DatasetRegressionReport:
    """Regression analysis for a single dataset.

    Attributes:
        dataset: Canonical dataset name.
        has_baseline: Whether a baseline was found.
        baseline_date: ISO timestamp of baseline creation.
        current_date: ISO timestamp of current screening.
        threshold: Regression threshold in percentage points.
        field_deltas: Per-field change analysis.
        regressions_found: Count of fields exceeding threshold.
        improvements_found: Count of fields with negative delta exceeding threshold.
    """

    dataset: str
    has_baseline: bool = False
    baseline_date: str = ""
    current_date: str = ""
    threshold: float = DEFAULT_THRESHOLD
    field_deltas: list[FieldDelta] = field(default_factory=list)
    regressions_found: int = 0
    improvements_found: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        result = {
            "dataset": self.dataset,
            "has_baseline": self.has_baseline,
            "baseline_date": self.baseline_date,
            "current_date": self.current_date,
            "threshold": self.threshold,
            "regressions_found": self.regressions_found,
            "improvements_found": self.improvements_found,
            "field_deltas": [asdict(d) for d in self.field_deltas],
        }
        return result


# ---------------------------------------------------------------------------
# Baseline management
# ---------------------------------------------------------------------------
def _baseline_path(dataset: str, results_dir: Path | None = None) -> Path:
    """Get the baseline file path for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Path to baseline_screening.json.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    return base / dataset / "baseline_screening.json"


def _screening_path(dataset: str, results_dir: Path | None = None) -> Path:
    """Get the current screening file path for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Path to automated_screening.json.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    return base / dataset / "automated_screening.json"


def load_baseline(
    dataset: str, *, results_dir: Path | None = None
) -> dict[str, Any] | None:
    """Load stored baseline screening for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Baseline dict or None if no baseline exists.
    """
    path = _baseline_path(dataset, results_dir)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_screening(
    dataset: str, *, results_dir: Path | None = None
) -> dict[str, Any] | None:
    """Load current screening results for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Screening dict or None if no screening exists.
    """
    path = _screening_path(dataset, results_dir)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_baseline(
    dataset: str,
    screening: dict[str, Any],
    *,
    results_dir: Path | None = None,
) -> Path:
    """Store current screening as baseline.

    Args:
        dataset: Canonical dataset name.
        screening: Screening result dict to save.
        results_dir: Override results directory.

    Returns:
        Path to saved baseline file.
    """
    path = _baseline_path(dataset, results_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    baseline = {
        **screening,
        "baseline_created_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    log.info("Saved baseline for %s to %s", dataset, path)
    return path


# ---------------------------------------------------------------------------
# KI cross-reference
# ---------------------------------------------------------------------------
# Maps field names to KI identifiers that commonly affect them.
_FIELD_TO_KI: dict[str, list[str]] = {
    "layout_detections": ["KI-001"],
    "layout_bbox_valid": ["KI-001"],
    "content_flags_boolean": ["KI-002", "KI-003", "KI-004", "KI-006"],
    "capture_method": ["KI-005"],
    "domain_level1": ["KI-007"],
    "script_family": ["KI-008"],
    "iso639_language": ["KI-009"],
}


def load_known_issues(
    ki_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load KI advisory and index by ID.

    Args:
        ki_path: Override path to KI JSON file.

    Returns:
        Dict mapping KI ID to issue dict.
    """
    path = ki_path or KI_PATH
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    issues = data.get("issues", [])
    return {issue["id"]: issue for issue in issues if "id" in issue}


def cross_reference_known_issues(
    field_deltas: list[FieldDelta],
    ki_index: dict[str, dict[str, Any]] | None = None,
) -> list[FieldDelta]:
    """Annotate field deltas with related KI identifiers.

    Args:
        field_deltas: List of field change records.
        ki_index: Pre-loaded KI index. Loaded from default path if None.

    Returns:
        New list of FieldDelta with related_ki populated.
    """
    if ki_index is None:
        ki_index = load_known_issues()

    annotated: list[FieldDelta] = []
    for delta in field_deltas:
        ki_ids = _FIELD_TO_KI.get(delta.field_name, [])
        # Only annotate with KIs that actually exist in the advisory
        matching = [kid for kid in ki_ids if kid in ki_index]
        related = ", ".join(matching) if matching else None
        annotated.append(
            FieldDelta(
                field_name=delta.field_name,
                baseline_fail_rate=delta.baseline_fail_rate,
                current_fail_rate=delta.current_fail_rate,
                delta=delta.delta,
                is_regression=delta.is_regression,
                related_ki=related,
            )
        )
    return annotated


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------
def _extract_fail_rates(
    screening: dict[str, Any],
) -> dict[str, float]:
    """Extract per-field fail rates from a screening result.

    Args:
        screening: Prescreening result dict.

    Returns:
        Dict mapping field_name to fail_rate_pct.
    """
    per_field = screening.get("per_field_results", {})
    return {
        field_name: field_data.get("fail_rate_pct", 0.0)
        for field_name, field_data in per_field.items()
    }


def compute_deltas(
    baseline: dict[str, Any],
    current: dict[str, Any],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[FieldDelta]:
    """Compute per-field fail rate changes between baseline and current.

    A positive delta means the fail rate increased (regression).
    A negative delta means the fail rate decreased (improvement).

    Args:
        baseline: Baseline screening dict.
        current: Current screening dict.
        threshold: Regression threshold in percentage points.

    Returns:
        List of FieldDelta for all fields present in either result.
    """
    baseline_rates = _extract_fail_rates(baseline)
    current_rates = _extract_fail_rates(current)

    all_fields = sorted(set(baseline_rates) | set(current_rates))
    deltas: list[FieldDelta] = []

    for field_name in all_fields:
        base_rate = baseline_rates.get(field_name, 0.0)
        curr_rate = current_rates.get(field_name, 0.0)
        delta = round(curr_rate - base_rate, 4)
        is_regression = delta > threshold
        deltas.append(
            FieldDelta(
                field_name=field_name,
                baseline_fail_rate=round(base_rate, 4),
                current_fail_rate=round(curr_rate, 4),
                delta=delta,
                is_regression=is_regression,
            )
        )
    return deltas


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def check_dataset(
    dataset: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    results_dir: Path | None = None,
    ki_index: dict[str, dict[str, Any]] | None = None,
) -> DatasetRegressionReport:
    """Run regression check for a single dataset.

    Args:
        dataset: Canonical dataset name.
        threshold: Regression threshold in percentage points.
        results_dir: Override results directory.
        ki_index: Pre-loaded KI index.

    Returns:
        DatasetRegressionReport with deltas and regression counts.
    """
    report = DatasetRegressionReport(dataset=dataset, threshold=threshold)

    baseline = load_baseline(dataset, results_dir=results_dir)
    current = load_screening(dataset, results_dir=results_dir)

    if current is None:
        log.warning("No screening found for %s, skipping", dataset)
        return report

    report.current_date = current.get("audited_at", "")

    if baseline is None:
        log.info(
            "No baseline for %s - first run; set --update-baseline to create", dataset
        )
        return report

    report.has_baseline = True
    report.baseline_date = baseline.get(
        "baseline_created_at", baseline.get("audited_at", "")
    )

    deltas = compute_deltas(baseline, current, threshold)
    deltas = cross_reference_known_issues(deltas, ki_index)

    report.field_deltas = deltas
    report.regressions_found = sum(1 for d in deltas if d.is_regression)
    report.improvements_found = sum(1 for d in deltas if d.delta < -threshold)

    return report


def check_all_datasets(
    *,
    threshold: float = DEFAULT_THRESHOLD,
    results_dir: Path | None = None,
) -> list[DatasetRegressionReport]:
    """Run regression check for all datasets with screening results.

    Args:
        threshold: Regression threshold in percentage points.
        results_dir: Override results directory.

    Returns:
        List of DatasetRegressionReport, one per dataset.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    ki_index = load_known_issues()

    reports: list[DatasetRegressionReport] = []
    dataset_dirs = sorted(
        d for d in base.iterdir() if d.is_dir() and not d.name.startswith(".")
    )

    for dataset_dir in dataset_dirs:
        screening_file = dataset_dir / "automated_screening.json"
        if not screening_file.exists():
            continue
        report = check_dataset(
            dataset_dir.name,
            threshold=threshold,
            results_dir=results_dir,
            ki_index=ki_index,
        )
        reports.append(report)

    return reports


def write_regression_report(
    report: DatasetRegressionReport,
    *,
    results_dir: Path | None = None,
) -> Path:
    """Write a dataset regression report to JSON.

    Args:
        report: The regression report to write.
        results_dir: Override results directory.

    Returns:
        Path to the written file.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    output_path = base / report.dataset / "regression_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    return output_path


def write_summary_report(
    reports: list[DatasetRegressionReport],
    *,
    results_dir: Path | None = None,
) -> Path:
    """Write a cross-dataset regression summary.

    Args:
        reports: List of per-dataset reports.
        results_dir: Override results directory.

    Returns:
        Path to the written summary file.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    output_path = base / "regression_summary.json"

    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_datasets": len(reports),
        "datasets_with_baseline": sum(1 for r in reports if r.has_baseline),
        "datasets_with_regressions": sum(1 for r in reports if r.regressions_found > 0),
        "datasets_with_improvements": sum(
            1 for r in reports if r.improvements_found > 0
        ),
        "datasets": [r.to_dict() for r in reports],
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return output_path


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------
def print_report(report: DatasetRegressionReport) -> None:
    """Print a human-readable regression report.

    Args:
        report: The regression report to display.
    """
    print(f"\n{'=' * 60}")
    print(f"Regression Report: {report.dataset}")
    print(f"{'=' * 60}")

    if not report.has_baseline:
        print("  No baseline available - run with --update-baseline first")
        return

    print(f"  Baseline: {report.baseline_date}")
    print(f"  Current:  {report.current_date}")
    print(f"  Threshold: {report.threshold}pp")
    print()

    if report.regressions_found == 0 and report.improvements_found == 0:
        print("  No significant changes detected.")
        return

    if report.regressions_found > 0:
        print(f"  REGRESSIONS ({report.regressions_found}):")
        for delta in report.field_deltas:
            if delta.is_regression:
                ki_tag = f" [{delta.related_ki}]" if delta.related_ki else ""
                print(
                    f"    {delta.field_name}: "
                    f"{delta.baseline_fail_rate:.1f}% -> "
                    f"{delta.current_fail_rate:.1f}% "
                    f"(+{delta.delta:.1f}pp){ki_tag}"
                )

    if report.improvements_found > 0:
        print(f"\n  IMPROVEMENTS ({report.improvements_found}):")
        for delta in report.field_deltas:
            if delta.delta < -report.threshold:
                print(
                    f"    {delta.field_name}: "
                    f"{delta.baseline_fail_rate:.1f}% -> "
                    f"{delta.current_fail_rate:.1f}% "
                    f"({delta.delta:.1f}pp)"
                )


def print_summary(reports: list[DatasetRegressionReport]) -> None:
    """Print a cross-dataset regression summary.

    Args:
        reports: List of per-dataset reports.
    """
    with_baseline = [r for r in reports if r.has_baseline]
    with_regressions = [r for r in with_baseline if r.regressions_found > 0]

    print(f"\n{'=' * 60}")
    print("Cross-Dataset Regression Summary")
    print(f"{'=' * 60}")
    print(f"  Total datasets checked:    {len(reports)}")
    print(f"  With baselines:            {len(with_baseline)}")
    print(f"  With regressions:          {len(with_regressions)}")

    if with_regressions:
        print("\n  Datasets with regressions:")
        for r in with_regressions:
            regressed_fields = [d.field_name for d in r.field_deltas if d.is_regression]
            print(f"    {r.dataset}: {', '.join(regressed_fields)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI entry point for regression checking.

    Args:
        argv: Command-line arguments. Uses sys.argv if None.

    Returns:
        Exit code (0 = no regressions, 1 = regressions found).
    """
    parser = argparse.ArgumentParser(
        description="Check for quality regressions in Layer 2 metadata."
    )
    parser.add_argument("--dataset", help="Single dataset to check.")
    parser.add_argument(
        "--all-datasets",
        action="store_true",
        help="Check all datasets with screening results.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Save current screening as baseline.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Regression threshold in percentage points (default: {DEFAULT_THRESHOLD}).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Override results directory path.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress console output.")

    args = parser.parse_args(argv)

    if not args.dataset and not args.all_datasets:
        parser.error("Specify --dataset or --all-datasets")

    results_dir = args.results_dir
    exit_code = 0

    if args.update_baseline:
        datasets = (
            [args.dataset]
            if args.dataset
            else _list_datasets_with_screening(results_dir)
        )
        for ds in datasets:
            screening = load_screening(ds, results_dir=results_dir)
            if screening:
                save_baseline(ds, screening, results_dir=results_dir)
            else:
                log.warning("No screening found for %s, skipping baseline", ds)
        return 0

    if args.dataset:
        report = check_dataset(
            args.dataset,
            threshold=args.threshold,
            results_dir=results_dir,
        )
        if not args.quiet:
            print_report(report)
        write_regression_report(report, results_dir=results_dir)
        if report.regressions_found > 0:
            exit_code = 1
    else:
        reports = check_all_datasets(threshold=args.threshold, results_dir=results_dir)
        if not args.quiet:
            for r in reports:
                if r.has_baseline:
                    print_report(r)
            print_summary(reports)
        for r in reports:
            write_regression_report(r, results_dir=results_dir)
        write_summary_report(reports, results_dir=results_dir)
        if any(r.regressions_found > 0 for r in reports):
            exit_code = 1

    return exit_code


def _list_datasets_with_screening(
    results_dir: Path | None = None,
) -> list[str]:
    """List all datasets that have screening results.

    Args:
        results_dir: Override results directory.

    Returns:
        Sorted list of dataset names.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    return sorted(
        d.name
        for d in base.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and (d / "automated_screening.json").exists()
    )


if __name__ == "__main__":
    sys.exit(main())
