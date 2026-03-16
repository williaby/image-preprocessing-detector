"""Temporal score tracking for Layer 2 metadata audits.

Appends scorecard snapshots to a JSONL history file for each dataset,
enabling trend analysis (improving/stable/degrading) over time.

Usage from compute_scorecard.py::

    from scripts.audit.score_history import append_to_history
    append_to_history(dataset, scorecard_data)

Standalone query::

    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 -c "
        from scripts.audit.score_history import load_history, compute_trend
        history = load_history('jssoda')
        print(compute_trend(history))
        "
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScoreSnapshot:
    """A single point-in-time scorecard snapshot.

    Attributes:
        timestamp: ISO timestamp of when the snapshot was taken.
        overall_score: Overall weighted score (0-100).
        grade: Grade letter.
        dimension_scores: Per-dimension scores.
    """

    timestamp: str
    overall_score: float
    grade: str
    dimension_scores: dict[str, float | None]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# History management
# ---------------------------------------------------------------------------
def _history_path(dataset: str, *, results_dir: Path | None = None) -> Path:
    """Get the JSONL history file path for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        Path to scorecard_history.jsonl.
    """
    base = results_dir or AUDIT_RESULTS_DIR
    return base / dataset / "scorecard_history.jsonl"


def append_to_history(
    dataset: str,
    scorecard: dict[str, Any],
    *,
    results_dir: Path | None = None,
    timestamp: str | None = None,
) -> Path:
    """Append a scorecard snapshot to the dataset's history.

    Args:
        dataset: Canonical dataset name.
        scorecard: Scorecard data dict (from compute_scorecard.py).
        results_dir: Override results directory.
        timestamp: Override timestamp (for testing). Uses current time if None.

    Returns:
        Path to the history file.
    """
    path = _history_path(dataset, results_dir=results_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    dimension_scores = scorecard.get("dimension_scores", {})

    snapshot = ScoreSnapshot(
        timestamp=ts,
        overall_score=scorecard.get("overall_score", 0.0),
        grade=scorecard.get("grade", "?"),
        dimension_scores=dimension_scores,
    )

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")

    log.info(
        "Appended snapshot to %s (score=%.1f, grade=%s)",
        path,
        snapshot.overall_score,
        snapshot.grade,
    )
    return path


def load_history(
    dataset: str, *, results_dir: Path | None = None
) -> list[ScoreSnapshot]:
    """Load all historical snapshots for a dataset.

    Args:
        dataset: Canonical dataset name.
        results_dir: Override results directory.

    Returns:
        List of ScoreSnapshot in chronological order.
    """
    path = _history_path(dataset, results_dir=results_dir)
    if not path.exists():
        return []

    snapshots: list[ScoreSnapshot] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            snapshots.append(
                ScoreSnapshot(
                    timestamp=data["timestamp"],
                    overall_score=data["overall_score"],
                    grade=data["grade"],
                    dimension_scores=data.get("dimension_scores", {}),
                )
            )

    return snapshots


# ---------------------------------------------------------------------------
# Trend analysis
# ---------------------------------------------------------------------------
def compute_trend(
    history: list[ScoreSnapshot],
    *,
    window: int = 3,
    threshold: float = 2.0,
) -> str:
    """Compute the overall score trend from history.

    Uses the last `window` snapshots to determine if the score is
    improving, stable, or degrading.

    Args:
        history: Chronological list of snapshots.
        window: Number of recent snapshots to analyze.
        threshold: Minimum score change to classify as improving/degrading.

    Returns:
        One of "improving", "stable", "degrading", or "insufficient_data".
    """
    if len(history) < 2:
        return "insufficient_data"

    recent = history[-window:]
    if len(recent) < 2:
        return "insufficient_data"

    first_score = recent[0].overall_score
    last_score = recent[-1].overall_score
    delta = last_score - first_score

    if delta > threshold:
        return "improving"
    if delta < -threshold:
        return "degrading"
    return "stable"


def compute_dimension_trends(
    history: list[ScoreSnapshot],
    *,
    window: int = 3,
    threshold: float = 2.0,
) -> dict[str, str]:
    """Compute per-dimension score trends.

    Args:
        history: Chronological list of snapshots.
        window: Number of recent snapshots to analyze.
        threshold: Minimum score change to classify as improving/degrading.

    Returns:
        Dict mapping dimension name to trend string.
    """
    if len(history) < 2:
        return {}

    recent = history[-window:]
    if len(recent) < 2:
        return {}

    first = recent[0].dimension_scores
    last = recent[-1].dimension_scores

    all_dims = set(first.keys()) | set(last.keys())
    trends: dict[str, str] = {}

    for dim in all_dims:
        first_val = first.get(dim)
        last_val = last.get(dim)
        if first_val is None or last_val is None:
            trends[dim] = "insufficient_data"
            continue
        delta = last_val - first_val
        if delta > threshold:
            trends[dim] = "improving"
        elif delta < -threshold:
            trends[dim] = "degrading"
        else:
            trends[dim] = "stable"

    return trends
