"""Agent orchestration protocol for batch audit processing.

Lightweight status tracker for coordinating layer2-audit-agent and
dataset-catalog-agent workflows.  Not an execution engine -- agents
are invoked externally (via Claude Code Task tool or manually).

Usage::

    # Show plan for all eligible datasets
    python scripts/audit/orchestrate_batch.py --plan

    # Show current status
    python scripts/audit/orchestrate_batch.py --status

    # Plan specific datasets
    python scripts/audit/orchestrate_batch.py --plan --datasets jssoda,realdae
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "agent_orchestration.yaml"
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class AuditTask:
    """A single dataset audit task with priority and status.

    Attributes:
        dataset: Canonical dataset name.
        priority: Computed priority (higher = more urgent).
        current_grade: Current scorecard grade (or "?" if unaudited).
        training_criticality: Training importance score (1-5).
        audit_phase: Current audit phase (e.g. "prescreening", "complete").
        catalog_phase: Current catalog phase (e.g. "pending", "complete").
        handoff_ready: Whether audit outputs satisfy catalog pre-conditions.
        missing_artifacts: Artifacts needed before handoff.
    """

    dataset: str
    priority: float = 0.0
    current_grade: str = "?"
    training_criticality: int = 1
    audit_phase: str = "pending"
    catalog_phase: str = "pending"
    handoff_ready: bool = False
    missing_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
def load_orchestration_config(
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Load the agent orchestration config.

    Args:
        config_path: Override config file path.

    Returns:
        Parsed YAML config dict.
    """
    path = config_path or CONFIG_PATH
    if not path.exists():
        log.warning("Orchestration config not found: %s", path)
        return {}

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Artifact checking
# ---------------------------------------------------------------------------
def check_handoff_ready(
    dataset: str,
    *,
    results_dir: Path | None = None,
    required_artifacts: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Check whether audit outputs satisfy catalog handoff pre-conditions.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.
        required_artifacts: Override required artifact list.

    Returns:
        Tuple of (ready, missing_artifacts).
    """
    base = results_dir or AUDIT_RESULTS_DIR
    ds_dir = base / dataset

    if required_artifacts is None:
        required_artifacts = [
            "scorecard.json",
            "automated_screening.json",
        ]

    missing: list[str] = []
    for artifact in required_artifacts:
        if not (ds_dir / artifact).exists():
            missing.append(artifact)

    return len(missing) == 0, missing


def detect_audit_phase(
    dataset: str,
    *,
    results_dir: Path | None = None,
) -> str:
    """Detect the current audit phase from available artifacts.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Phase string: "unaudited", "prescreening", "partial", or "complete".
    """
    base = results_dir or AUDIT_RESULTS_DIR
    ds_dir = base / dataset

    if not ds_dir.is_dir():
        return "unaudited"

    has_screening = (ds_dir / "automated_screening.json").exists()
    has_scorecard = (ds_dir / "scorecard.json").exists()
    has_compliance = (ds_dir / "compliance_report.json").exists()

    if has_scorecard:
        return "complete"
    if has_screening and has_compliance:
        return "partial"
    if has_screening:
        return "prescreening"
    return "unaudited"


def detect_catalog_phase(
    dataset: str,
) -> str:
    """Detect the catalog documentation phase.

    Args:
        dataset: Canonical dataset name.

    Returns:
        Phase string: "missing", "exists", or "complete".
    """
    source_doc = PROJECT_ROOT / "docs" / "datasets" / "source" / f"{dataset}.md"
    if not source_doc.exists():
        return "missing"

    # Check if doc has audit results section (rough heuristic)
    content = source_doc.read_text(encoding="utf-8")
    if "## 10. Audit" in content or "audit_grade" in content:
        return "complete"
    return "exists"


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
def _load_grade(dataset: str, results_dir: Path | None = None) -> str:
    """Load the current grade from scorecard."""
    base = results_dir or AUDIT_RESULTS_DIR
    path = base / dataset / "scorecard.json"
    if not path.exists():
        return "?"
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("grade", "?")
    except (json.JSONDecodeError, KeyError):
        return "?"


def _load_criticality(dataset: str, results_dir: Path | None = None) -> int:
    """Load training criticality if available."""
    base = results_dir or AUDIT_RESULTS_DIR
    path = base / "training_criticality.json"
    if not path.exists():
        return 1
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        datasets = data.get("datasets", {})
        entry = datasets.get(dataset, {})
        return entry.get("criticality", 1)
    except (json.JSONDecodeError, KeyError):
        return 1


def compute_priority(
    grade: str,
    criticality: int,
    config: dict[str, Any] | None = None,
) -> float:
    """Compute task priority from grade and training criticality.

    Args:
        grade: Current scorecard grade.
        criticality: Training criticality (1-5).
        config: Orchestration config dict.

    Returns:
        Priority score (higher = more urgent).
    """
    cfg = config or {}
    grade_boost = cfg.get("priority", {}).get("grade_boost", {})
    boost = grade_boost.get(grade, 0)
    return float(criticality + boost)


def plan_batch(
    datasets: list[str] | None = None,
    *,
    results_dir: Path | None = None,
    config: dict[str, Any] | None = None,
    priority_min: float = 0.0,
) -> list[AuditTask]:
    """Create a priority-sorted batch plan.

    Args:
        datasets: Specific datasets to plan. If None, discovers from
            results directory.
        results_dir: Override results directory.
        config: Orchestration config.
        priority_min: Minimum priority to include.

    Returns:
        List of AuditTask sorted by priority (descending).
    """
    base = results_dir or AUDIT_RESULTS_DIR
    cfg = config or load_orchestration_config()

    if datasets is None:
        # Discover from results directory
        if base.is_dir():
            datasets = sorted(
                d.name
                for d in base.iterdir()
                if d.is_dir() and (d / "scorecard.json").exists()
            )
        else:
            datasets = []

    tasks: list[AuditTask] = []
    for ds in datasets:
        grade = _load_grade(ds, results_dir=results_dir)
        criticality = _load_criticality(ds, results_dir=results_dir)
        priority = compute_priority(grade, criticality, config=cfg)

        if priority < priority_min:
            continue

        audit_phase = detect_audit_phase(ds, results_dir=results_dir)
        catalog_phase = detect_catalog_phase(ds)
        ready, missing = check_handoff_ready(ds, results_dir=results_dir)

        tasks.append(
            AuditTask(
                dataset=ds,
                priority=priority,
                current_grade=grade,
                training_criticality=criticality,
                audit_phase=audit_phase,
                catalog_phase=catalog_phase,
                handoff_ready=ready,
                missing_artifacts=missing,
            )
        )

    tasks.sort(key=lambda t: t.priority, reverse=True)
    return tasks


# ---------------------------------------------------------------------------
# Status reporting
# ---------------------------------------------------------------------------
def generate_batch_status(
    tasks: list[AuditTask],
) -> dict[str, Any]:
    """Generate a batch status summary.

    Args:
        tasks: List of audit tasks.

    Returns:
        Status summary dict.
    """
    total = len(tasks)
    audit_complete = sum(1 for t in tasks if t.audit_phase == "complete")
    handoff_ready = sum(1 for t in tasks if t.handoff_ready)
    catalog_complete = sum(1 for t in tasks if t.catalog_phase == "complete")

    grade_dist: dict[str, int] = {}
    for t in tasks:
        grade_dist[t.current_grade] = grade_dist.get(t.current_grade, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_datasets": total,
        "audit_complete": audit_complete,
        "handoff_ready": handoff_ready,
        "catalog_complete": catalog_complete,
        "grade_distribution": grade_dist,
        "tasks": [t.to_dict() for t in tasks],
    }


def write_batch_status(
    tasks: list[AuditTask],
    *,
    results_dir: Path | None = None,
) -> Path:
    """Write batch status to a JSON file.

    Args:
        tasks: List of audit tasks.
        results_dir: Override results directory.

    Returns:
        Path to the written status file.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    base.mkdir(parents=True, exist_ok=True)

    status = generate_batch_status(tasks)
    path = base / "orchestration_status.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

    log.info("Wrote orchestration status to %s", path)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Agent orchestration for batch audit processing."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--plan",
        action="store_true",
        help="Show the batch plan.",
    )
    mode.add_argument(
        "--status",
        action="store_true",
        help="Show current status of all tasks.",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default=None,
        help="Comma-separated dataset names.",
    )
    parser.add_argument(
        "--priority-min",
        type=float,
        default=0.0,
        help="Minimum priority to include.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write status JSON to file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    ds_list = args.datasets.split(",") if args.datasets else None
    tasks = plan_batch(
        datasets=ds_list,
        priority_min=args.priority_min,
    )

    if args.plan or args.status:
        print(
            f"\n{'Dataset':<25} {'Grade':>5} {'Crit':>4} {'Pri':>5}"
            f"  {'Audit':<15} {'Catalog':<12} {'Handoff'}"
        )
        print("-" * 85)
        for t in tasks:
            handoff_str = (
                "READY"
                if t.handoff_ready
                else f"MISSING: {', '.join(t.missing_artifacts)}"
            )
            print(
                f"{t.dataset:<25} {t.current_grade:>5} {t.training_criticality:>4}"
                f" {t.priority:>5.1f}  {t.audit_phase:<15}"
                f" {t.catalog_phase:<12} {handoff_str}"
            )
        print(f"\nTotal: {len(tasks)} datasets")

    if args.output:
        write_batch_status(tasks, results_dir=args.output.parent)
        print(f"Status written to {args.output}")


if __name__ == "__main__":
    main()
