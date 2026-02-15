"""Active learning bridge for VLM relabeling queue.

Reads VLM accuracy scores from scorecards and emits a prioritized
``relabel_queue.json`` for datasets below threshold.  Cross-references
with training criticality to focus relabeling effort where it matters.

Usage::

    python scripts/audit/active_learning_bridge.py --threshold 60.0
    python scripts/audit/active_learning_bridge.py --threshold 50.0 --output results/relabel_queue.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RelabelCandidate:
    """A dataset flagged for VLM relabeling.

    Attributes:
        dataset: Canonical dataset name.
        vlm_accuracy: Current VLM accuracy score (0-100).
        overall_grade: Current scorecard grade.
        training_criticality: Training importance (1-5).
        priority: Computed relabel priority (higher = more urgent).
        reason: Why this dataset was flagged.
    """

    dataset: str
    vlm_accuracy: float
    overall_grade: str
    training_criticality: int
    priority: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def scan_vlm_accuracy(
    *,
    results_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Scan all scorecards for VLM accuracy scores.

    Args:
        results_dir: Override results directory.

    Returns:
        List of dicts with dataset, vlm_accuracy, grade.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    entries: list[dict[str, Any]] = []

    if not base.is_dir():
        return entries

    for ds_dir in sorted(base.iterdir()):
        scorecard_path = ds_dir / "scorecard.json"
        if not scorecard_path.exists():
            continue

        try:
            with scorecard_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        dim_scores = data.get("dimension_scores", {})
        vlm_acc = dim_scores.get("vlm_accuracy")

        entries.append(
            {
                "dataset": data.get("dataset", ds_dir.name),
                "vlm_accuracy": vlm_acc,
                "grade": data.get("grade", "?"),
            }
        )

    return entries


def load_criticality_map(
    results_dir: Path | None = None,
) -> dict[str, int]:
    """Load training criticality mapping.

    Args:
        results_dir: Override results directory.

    Returns:
        Dict mapping dataset name to criticality (1-5).
    """
    base = results_dir or AUDIT_RESULTS_DIR
    path = base / "training_criticality.json"
    if not path.exists():
        return {}

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return {
            ds: entry.get("criticality", 1)
            for ds, entry in data.get("datasets", {}).items()
        }
    except (json.JSONDecodeError, KeyError):
        return {}


def build_relabel_queue(
    *,
    threshold: float = 60.0,
    results_dir: Path | None = None,
) -> list[RelabelCandidate]:
    """Build prioritized relabel queue from scorecard data.

    Datasets are flagged if:
    - VLM accuracy is below threshold, OR
    - VLM accuracy is null (never evaluated)

    Priority = (100 - vlm_accuracy) * criticality_weight

    Args:
        threshold: VLM accuracy threshold (0-100).
        results_dir: Override results directory.

    Returns:
        List of RelabelCandidate sorted by priority (descending).
    """
    entries = scan_vlm_accuracy(results_dir=results_dir)
    crit_map = load_criticality_map(results_dir=results_dir)

    candidates: list[RelabelCandidate] = []
    for entry in entries:
        dataset = entry["dataset"]
        vlm_acc = entry["vlm_accuracy"]
        grade = entry["grade"]
        criticality = crit_map.get(dataset, 1)

        if vlm_acc is None:
            # Never evaluated -> flag for initial labeling
            priority = 100.0 * (1 + criticality * 0.5)
            candidates.append(
                RelabelCandidate(
                    dataset=dataset,
                    vlm_accuracy=0.0,
                    overall_grade=grade,
                    training_criticality=criticality,
                    priority=priority,
                    reason="VLM accuracy not evaluated",
                )
            )
        elif vlm_acc < threshold:
            deficit = threshold - vlm_acc
            priority = deficit * (1 + criticality * 0.5)
            candidates.append(
                RelabelCandidate(
                    dataset=dataset,
                    vlm_accuracy=vlm_acc,
                    overall_grade=grade,
                    training_criticality=criticality,
                    priority=priority,
                    reason=f"VLM accuracy {vlm_acc:.1f}% below {threshold:.0f}% threshold",
                )
            )

    candidates.sort(key=lambda c: c.priority, reverse=True)
    return candidates


def write_relabel_queue(
    candidates: list[RelabelCandidate],
    *,
    output_path: Path | None = None,
    results_dir: Path | None = None,
) -> Path:
    """Write the relabel queue to JSON.

    Args:
        candidates: List of relabel candidates.
        output_path: Override output file path.
        results_dir: Override results directory.

    Returns:
        Path to the written file.
    """
    if output_path is None:
        base = results_dir or AUDIT_RESULTS_DIR
        output_path = base / "relabel_queue.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_candidates": len(candidates),
        "candidates": [c.to_dict() for c in candidates],
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info("Wrote %d candidates to %s", len(candidates), output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build VLM relabeling queue from audit scorecards."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="VLM accuracy threshold (default: 60.0).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path.",
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

    candidates = build_relabel_queue(threshold=args.threshold)

    if not candidates:
        print("No datasets flagged for relabeling.")
        return

    print(
        f"\n{'Dataset':<25} {'VLM Acc':>8} {'Grade':>5}"
        f" {'Crit':>4} {'Priority':>8}  Reason"
    )
    print("-" * 90)
    for c in candidates:
        print(
            f"{c.dataset:<25} {c.vlm_accuracy:>7.1f}%"
            f" {c.overall_grade:>5} {c.training_criticality:>4}"
            f" {c.priority:>8.1f}  {c.reason}"
        )
    print(f"\nTotal: {len(candidates)} candidates")

    path = write_relabel_queue(candidates, output_path=args.output)
    print(f"Queue written to {path}")


if __name__ == "__main__":
    main()
