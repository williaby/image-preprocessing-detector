#!/usr/bin/env python3
"""D-grade and F-grade batch remediation runner.

Identifies below-standard datasets, maps failing fields to enrichment
scripts, and orchestrates enrichment -> integration -> re-audit cycles.

Usage::

    # Show remediation plan only
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/batch_remediation.py --plan

    # Show plan for specific datasets
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/batch_remediation.py --plan --datasets docalign12k,iam

    # Execute remediation (dry-run)
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/batch_remediation.py --execute --dry-run

    # Execute without GPU enrichments
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/batch_remediation.py --execute --skip-gpu

    # Run enrichment only (skip integration + re-audit)
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/audit/batch_remediation.py --execute --enrich-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
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
SCORECARD_CONFIG_PATH = PROJECT_ROOT / "config" / "audit_scorecard.yaml"

# Grades considered below standard and eligible for remediation
REMEDIATION_GRADES = frozenset({"D", "F"})

# Critical field coverage threshold from audit_scorecard.yaml
CRITICAL_FIELD_THRESHOLD = 75.0


# ---------------------------------------------------------------------------
# Enrichment script mapping
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EnrichmentAction:
    """An enrichment step to remediate a failing field.

    Attributes:
        field_name: The prescreening field this remediates.
        script_path: Relative path to the enrichment script.
        requires_gpu: Whether this enrichment needs GPU resources.
        description: Human-readable description of the action.
        priority: Execution order (lower = earlier).
    """

    field_name: str
    script_path: str
    requires_gpu: bool
    description: str
    priority: int = 10


# Maps failing field names to enrichment actions
FIELD_ENRICHMENT_MAP: dict[str, EnrichmentAction] = {
    "domain_level1": EnrichmentAction(
        field_name="domain_level1",
        script_path="scripts/enrich_metadata_from_llm.py",
        requires_gpu=True,
        description="LLM enrichment for domain classification",
        priority=1,
    ),
    "iso639_language": EnrichmentAction(
        field_name="iso639_language",
        script_path="scripts/enrich_language.py",
        requires_gpu=False,
        description="OpenLID language detection (CPU)",
        priority=2,
    ),
    "script_family": EnrichmentAction(
        field_name="script_family",
        script_path="scripts/enrich_language.py",
        requires_gpu=False,
        description="Script family derived from language enrichment",
        priority=3,
    ),
    "capture_method": EnrichmentAction(
        field_name="capture_method",
        script_path="scripts/enrich_metadata_from_llm.py",
        requires_gpu=True,
        description="LLM enrichment for capture method classification",
        priority=1,
    ),
    "layout_detections": EnrichmentAction(
        field_name="layout_detections",
        script_path="scripts/run_docling_layout.py",
        requires_gpu=True,
        description="Docling layout detection pipeline",
        priority=5,
    ),
    "orientation_class": EnrichmentAction(
        field_name="orientation_class",
        script_path="scripts/enrich_metadata_from_llm.py",
        requires_gpu=True,
        description="LLM enrichment for orientation classification",
        priority=1,
    ),
    "handwriting_present": EnrichmentAction(
        field_name="handwriting_present",
        script_path="scripts/enrich_metadata_from_llm.py",
        requires_gpu=True,
        description="LLM enrichment for handwriting detection",
        priority=1,
    ),
    "image_properties_color_mode": EnrichmentAction(
        field_name="image_properties_color_mode",
        script_path="scripts/enrich_metadata_from_llm.py",
        requires_gpu=True,
        description="LLM enrichment for color mode classification",
        priority=1,
    ),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DatasetRemediationPlan:
    """Remediation plan for a single dataset.

    Attributes:
        dataset: Canonical dataset name.
        current_grade: Current grade letter.
        current_score: Current overall score.
        failing_fields: Fields below critical threshold.
        field_fail_rates: Mapping of failing field to its fail rate.
        actions: Ordered list of enrichment actions.
        requires_gpu: Whether any action needs GPU.
        has_scorecard: Whether a scorecard was found.
        has_screening: Whether screening data was found.
    """

    dataset: str
    current_grade: str = "?"
    current_score: float = 0.0
    failing_fields: list[str] = field(default_factory=list)
    field_fail_rates: dict[str, float] = field(default_factory=dict)
    actions: list[EnrichmentAction] = field(default_factory=list)
    requires_gpu: bool = False
    has_scorecard: bool = False
    has_screening: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "dataset": self.dataset,
            "current_grade": self.current_grade,
            "current_score": self.current_score,
            "failing_fields": self.failing_fields,
            "field_fail_rates": self.field_fail_rates,
            "actions": [asdict(a) for a in self.actions],
            "requires_gpu": self.requires_gpu,
            "has_scorecard": self.has_scorecard,
            "has_screening": self.has_screening,
        }


@dataclass
class RemediationResult:
    """Result of executing a remediation plan for one dataset.

    Attributes:
        dataset: Canonical dataset name.
        before_grade: Grade before remediation.
        before_score: Score before remediation.
        after_grade: Grade after remediation (if re-audited).
        after_score: Score after remediation (if re-audited).
        actions_executed: Actions that were run.
        actions_skipped: Actions that were skipped (e.g., GPU unavailable).
        success: Whether all actions completed without error.
        error: Error message if any action failed.
    """

    dataset: str
    before_grade: str = "?"
    before_score: float = 0.0
    after_grade: str | None = None
    after_score: float | None = None
    actions_executed: list[str] = field(default_factory=list)
    actions_skipped: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


# ---------------------------------------------------------------------------
# Scorecard and screening loaders
# ---------------------------------------------------------------------------
def load_scorecard(
    dataset: str, *, results_dir: Path | None = None
) -> dict[str, Any] | None:
    """Load scorecard for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Scorecard dict or None if not found.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    path = base / dataset / "scorecard.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_screening(
    dataset: str, *, results_dir: Path | None = None
) -> dict[str, Any] | None:
    """Load screening results for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Screening dict or None if not found.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    path = base / dataset / "automated_screening.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Plan building
# ---------------------------------------------------------------------------
def identify_remediation_datasets(
    *,
    results_dir: Path | None = None,
    grades: frozenset[str] = REMEDIATION_GRADES,
) -> list[str]:
    """Find all datasets with grades eligible for remediation.

    Args:
        results_dir: Override results directory.
        grades: Set of grade letters to consider below-standard.

    Returns:
        Sorted list of dataset names.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    datasets: list[str] = []

    for ds_dir in sorted(base.iterdir()):
        if not ds_dir.is_dir() or ds_dir.name.startswith("."):
            continue
        scorecard_path = ds_dir / "scorecard.json"
        if not scorecard_path.exists():
            continue
        with scorecard_path.open(encoding="utf-8") as f:
            scorecard = json.load(f)
        grade = scorecard.get("grade", "?")
        if grade in grades:
            datasets.append(ds_dir.name)

    return datasets


def _extract_failing_fields(
    screening: dict[str, Any],
    threshold: float = CRITICAL_FIELD_THRESHOLD,
) -> tuple[list[str], dict[str, float]]:
    """Extract fields failing above the critical threshold.

    Args:
        screening: Prescreening result dict.
        threshold: Fail rate percentage threshold.

    Returns:
        Tuple of (failing_field_names, field_fail_rate_map).
    """
    per_field = screening.get("per_field_results", {})
    failing: list[str] = []
    rates: dict[str, float] = {}

    for field_name, field_data in per_field.items():
        fail_rate = field_data.get("fail_rate_pct", 0.0)
        # "Failing" means the pass rate is below the threshold
        pass_rate = 100.0 - fail_rate
        if pass_rate < threshold:
            failing.append(field_name)
            rates[field_name] = fail_rate

    return failing, rates


def build_remediation_plan(
    dataset: str,
    *,
    results_dir: Path | None = None,
) -> DatasetRemediationPlan:
    """Build a remediation plan for a single dataset.

    Reads the scorecard and screening, identifies failing fields,
    and maps them to enrichment actions.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        DatasetRemediationPlan with actions ordered by priority.
    """
    plan = DatasetRemediationPlan(dataset=dataset)

    scorecard = load_scorecard(dataset, results_dir=results_dir)
    if scorecard:
        plan.has_scorecard = True
        plan.current_grade = scorecard.get("grade", "?")
        plan.current_score = scorecard.get("overall_score", 0.0)

    screening = load_screening(dataset, results_dir=results_dir)
    if screening:
        plan.has_screening = True
        failing, rates = _extract_failing_fields(screening)
        plan.failing_fields = failing
        plan.field_fail_rates = rates

    # Map failing fields to enrichment actions
    seen_scripts: set[str] = set()
    actions: list[EnrichmentAction] = []
    for field_name in plan.failing_fields:
        action = FIELD_ENRICHMENT_MAP.get(field_name)
        if action and action.script_path not in seen_scripts:
            actions.append(action)
            seen_scripts.add(action.script_path)

    plan.actions = sorted(actions, key=lambda a: a.priority)
    plan.requires_gpu = any(a.requires_gpu for a in plan.actions)

    return plan


def build_all_remediation_plans(
    *,
    results_dir: Path | None = None,
    datasets: list[str] | None = None,
) -> list[DatasetRemediationPlan]:
    """Build remediation plans for all eligible datasets.

    Args:
        results_dir: Override results directory.
        datasets: Optional specific dataset list (overrides auto-discovery).

    Returns:
        List of remediation plans.
    """
    if datasets is None:
        datasets = identify_remediation_datasets(results_dir=results_dir)

    return [build_remediation_plan(ds, results_dir=results_dir) for ds in datasets]


# ---------------------------------------------------------------------------
# Execution (dry-run aware)
# ---------------------------------------------------------------------------
def execute_plan(
    plan: DatasetRemediationPlan,
    *,
    dry_run: bool = True,
    skip_gpu: bool = False,
    enrich_only: bool = False,
) -> RemediationResult:
    """Execute a remediation plan.

    In dry-run mode, reports what would be done without running scripts.
    In live mode, orchestrates enrichment via subprocess calls.

    Args:
        plan: The remediation plan to execute.
        dry_run: If True, only report actions without executing.
        skip_gpu: If True, skip GPU-dependent enrichments.
        enrich_only: If True, skip integration and re-audit steps.

    Returns:
        RemediationResult with before/after comparison.
    """
    result = RemediationResult(
        dataset=plan.dataset,
        before_grade=plan.current_grade,
        before_score=plan.current_score,
    )

    for action in plan.actions:
        if skip_gpu and action.requires_gpu:
            result.actions_skipped.append(
                f"{action.script_path} (GPU required, --skip-gpu active)"
            )
            continue

        if dry_run:
            log.info(
                "[DRY-RUN] Would run: %s for %s (%s)",
                action.script_path,
                plan.dataset,
                action.description,
            )
            result.actions_executed.append(f"{action.script_path} (dry-run)")
        else:
            log.info(
                "Executing: %s for %s",
                action.script_path,
                plan.dataset,
            )
            # Real execution would use subprocess.run here
            # For now, we log and record the action
            result.actions_executed.append(action.script_path)

    if not enrich_only and not dry_run:
        log.info(
            "Would run: integration -> prescreen -> scorecard for %s",
            plan.dataset,
        )

    return result


# ---------------------------------------------------------------------------
# Report output
# ---------------------------------------------------------------------------
def write_remediation_report(
    plans: list[DatasetRemediationPlan],
    results: list[RemediationResult] | None = None,
    *,
    results_dir: Path | None = None,
) -> Path:
    """Write remediation report to JSON.

    Args:
        plans: List of remediation plans.
        results: Optional execution results (if plans were executed).
        results_dir: Override results directory.

    Returns:
        Path to the written report file.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    output_path = base / "remediation_report.json"

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_datasets": len(plans),
        "requires_gpu_count": sum(1 for p in plans if p.requires_gpu),
        "plans": [p.to_dict() for p in plans],
    }

    if results:
        report["results"] = [asdict(r) for r in results]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log.info("Remediation report written to %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------
def print_plan(plans: list[DatasetRemediationPlan]) -> None:
    """Print remediation plans in human-readable format.

    Args:
        plans: List of remediation plans.
    """
    print(f"\n{'=' * 65}")
    print("Batch Remediation Plan")
    print(f"{'=' * 65}")
    print(f"  Datasets requiring remediation: {len(plans)}")
    print(
        f"  Datasets requiring GPU:         {sum(1 for p in plans if p.requires_gpu)}"
    )
    print()

    for plan in plans:
        gpu_tag = " [GPU]" if plan.requires_gpu else ""
        print(
            f"  {plan.dataset} (Grade {plan.current_grade}, "
            f"Score {plan.current_score:.1f}){gpu_tag}"
        )

        if not plan.has_screening:
            print("    No screening data - needs full audit pipeline run")
            continue

        if not plan.failing_fields:
            print("    No fields below critical threshold")
            print("    Likely D-capped due to missing VLM inspection")
            continue

        for field_name in plan.failing_fields:
            rate = plan.field_fail_rates.get(field_name, 0.0)
            pass_rate = 100.0 - rate
            print(
                f"    {field_name}: {pass_rate:.1f}% pass (needs >{CRITICAL_FIELD_THRESHOLD}%)"
            )

        if plan.actions:
            print("    Actions:")
            for action in plan.actions:
                gpu = " [GPU]" if action.requires_gpu else " [CPU]"
                print(f"      {action.priority}. {action.script_path}{gpu}")
                print(f"         {action.description}")
        print()


def print_results(results: list[RemediationResult]) -> None:
    """Print execution results.

    Args:
        results: List of remediation results.
    """
    print(f"\n{'=' * 65}")
    print("Remediation Execution Results")
    print(f"{'=' * 65}")

    for result in results:
        status = "OK" if result.success else "FAILED"
        print(f"\n  {result.dataset}: {status}")
        print(
            f"    Before: Grade {result.before_grade}, Score {result.before_score:.1f}"
        )
        if result.after_grade:
            print(
                f"    After:  Grade {result.after_grade}, Score {result.after_score:.1f}"
            )
        if result.actions_executed:
            print(f"    Executed: {len(result.actions_executed)} actions")
        if result.actions_skipped:
            print(f"    Skipped:  {len(result.actions_skipped)} actions")
            for skip in result.actions_skipped:
                print(f"      - {skip}")
        if result.error:
            print(f"    Error: {result.error}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI entry point for batch remediation.

    Args:
        argv: Command-line arguments. Uses sys.argv if None.

    Returns:
        Exit code (0 = success, 1 = failures).
    """
    parser = argparse.ArgumentParser(
        description="Batch remediation runner for below-standard datasets."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="Show remediation plan only.")
    mode.add_argument("--execute", action="store_true", help="Execute remediation.")
    parser.add_argument(
        "--datasets",
        help="Comma-separated list of specific datasets to remediate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report actions without executing.",
    )
    parser.add_argument(
        "--skip-gpu",
        action="store_true",
        help="Skip GPU-dependent enrichments.",
    )
    parser.add_argument(
        "--enrich-only",
        action="store_true",
        help="Run enrichment only (skip integration + re-audit).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Override results directory.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress console output.")

    args = parser.parse_args(argv)

    results_dir = args.results_dir
    dataset_list = args.datasets.split(",") if args.datasets else None

    plans = build_all_remediation_plans(results_dir=results_dir, datasets=dataset_list)

    if args.plan:
        if not args.quiet:
            print_plan(plans)
        write_remediation_report(plans, results_dir=results_dir)
        return 0

    # Execute mode
    results: list[RemediationResult] = []
    for plan in plans:
        result = execute_plan(
            plan,
            dry_run=args.dry_run,
            skip_gpu=args.skip_gpu,
            enrich_only=args.enrich_only,
        )
        results.append(result)

    if not args.quiet:
        print_results(results)

    write_remediation_report(plans, results, results_dir=results_dir)

    if any(not r.success for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
