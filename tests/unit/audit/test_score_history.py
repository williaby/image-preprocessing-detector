"""Tests for temporal score tracking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.score_history import (
    ScoreSnapshot,
    append_to_history,
    compute_dimension_trends,
    compute_trend,
    load_history,
)


@pytest.fixture
def sample_scorecard() -> dict:
    """Create a sample scorecard dict."""
    return {
        "dataset": "test-ds",
        "overall_score": 85.0,
        "grade": "B",
        "dimension_scores": {
            "field_coverage": 80.0,
            "field_validity": 90.0,
            "doc_completeness": 100.0,
        },
    }


@pytest.fixture
def improved_scorecard() -> dict:
    """Create an improved scorecard dict."""
    return {
        "dataset": "test-ds",
        "overall_score": 92.0,
        "grade": "A",
        "dimension_scores": {
            "field_coverage": 90.0,
            "field_validity": 95.0,
            "doc_completeness": 100.0,
        },
    }


@pytest.fixture
def degraded_scorecard() -> dict:
    """Create a degraded scorecard dict."""
    return {
        "dataset": "test-ds",
        "overall_score": 72.0,
        "grade": "C",
        "dimension_scores": {
            "field_coverage": 65.0,
            "field_validity": 75.0,
            "doc_completeness": 80.0,
        },
    }


class TestScoreSnapshot:
    """Tests for ScoreSnapshot dataclass."""

    def test_create(self) -> None:
        snap = ScoreSnapshot(
            timestamp="2026-02-14T00:00:00+00:00",
            overall_score=85.0,
            grade="B",
            dimension_scores={"field_coverage": 80.0},
        )
        assert snap.overall_score == 85.0
        assert snap.grade == "B"

    def test_frozen(self) -> None:
        snap = ScoreSnapshot(
            timestamp="2026-02-14T00:00:00+00:00",
            overall_score=85.0,
            grade="B",
            dimension_scores={},
        )
        with pytest.raises(AttributeError):
            snap.overall_score = 90.0  # type: ignore[misc]

    def test_to_dict(self) -> None:
        snap = ScoreSnapshot(
            timestamp="2026-02-14T00:00:00+00:00",
            overall_score=85.0,
            grade="B",
            dimension_scores={"field_coverage": 80.0},
        )
        d = snap.to_dict()
        assert d["overall_score"] == 85.0
        assert d["dimension_scores"]["field_coverage"] == 80.0
        # Must be JSON-serializable
        json.dumps(d)


class TestAppendToHistory:
    """Tests for append_to_history."""

    def test_creates_file(self, tmp_path: Path, sample_scorecard: dict) -> None:
        path = append_to_history(
            "test-ds",
            sample_scorecard,
            results_dir=tmp_path,
            timestamp="2026-02-14T00:00:00+00:00",
        )
        assert path.exists()
        assert path.name == "scorecard_history.jsonl"

    def test_appends_to_existing(self, tmp_path: Path, sample_scorecard: dict) -> None:
        append_to_history(
            "test-ds",
            sample_scorecard,
            results_dir=tmp_path,
            timestamp="2026-02-14T00:00:00+00:00",
        )
        append_to_history(
            "test-ds",
            sample_scorecard,
            results_dir=tmp_path,
            timestamp="2026-02-14T01:00:00+00:00",
        )
        path = tmp_path / "test-ds" / "scorecard_history.jsonl"
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_snapshot_content(self, tmp_path: Path, sample_scorecard: dict) -> None:
        append_to_history(
            "test-ds",
            sample_scorecard,
            results_dir=tmp_path,
            timestamp="2026-02-14T00:00:00+00:00",
        )
        path = tmp_path / "test-ds" / "scorecard_history.jsonl"
        data = json.loads(path.read_text(encoding="utf-8").strip())
        assert data["overall_score"] == 85.0
        assert data["grade"] == "B"
        assert data["dimension_scores"]["field_coverage"] == 80.0

    def test_auto_timestamp(self, tmp_path: Path, sample_scorecard: dict) -> None:
        append_to_history("test-ds", sample_scorecard, results_dir=tmp_path)
        path = tmp_path / "test-ds" / "scorecard_history.jsonl"
        data = json.loads(path.read_text(encoding="utf-8").strip())
        assert "timestamp" in data
        assert len(data["timestamp"]) > 10  # ISO format


class TestLoadHistory:
    """Tests for load_history."""

    def test_empty_for_missing_dataset(self, tmp_path: Path) -> None:
        history = load_history("nonexistent", results_dir=tmp_path)
        assert history == []

    def test_loads_snapshots(self, tmp_path: Path, sample_scorecard: dict) -> None:
        for i in range(3):
            append_to_history(
                "test-ds",
                sample_scorecard,
                results_dir=tmp_path,
                timestamp=f"2026-02-1{i}T00:00:00+00:00",
            )
        history = load_history("test-ds", results_dir=tmp_path)
        assert len(history) == 3
        assert all(isinstance(s, ScoreSnapshot) for s in history)

    def test_preserves_order(self, tmp_path: Path, sample_scorecard: dict) -> None:
        for i in range(3):
            sc = {**sample_scorecard, "overall_score": 80.0 + i}
            append_to_history(
                "test-ds",
                sc,
                results_dir=tmp_path,
                timestamp=f"2026-02-1{i}T00:00:00+00:00",
            )
        history = load_history("test-ds", results_dir=tmp_path)
        scores = [s.overall_score for s in history]
        assert scores == [80.0, 81.0, 82.0]

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        ds_dir = tmp_path / "test-ds"
        ds_dir.mkdir()
        hist_path = ds_dir / "scorecard_history.jsonl"
        snap = {
            "timestamp": "2026-02-14T00:00:00+00:00",
            "overall_score": 85.0,
            "grade": "B",
            "dimension_scores": {},
        }
        content = json.dumps(snap) + "\n\n" + json.dumps(snap) + "\n"
        hist_path.write_text(content, encoding="utf-8")
        history = load_history("test-ds", results_dir=tmp_path)
        assert len(history) == 2


class TestComputeTrend:
    """Tests for compute_trend."""

    def test_insufficient_data_empty(self) -> None:
        assert compute_trend([]) == "insufficient_data"

    def test_insufficient_data_single(self) -> None:
        snap = ScoreSnapshot(
            timestamp="t1",
            overall_score=85.0,
            grade="B",
            dimension_scores={},
        )
        assert compute_trend([snap]) == "insufficient_data"

    def test_improving(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 80.0, "B", {}),
            ScoreSnapshot("t2", 85.0, "B", {}),
            ScoreSnapshot("t3", 90.0, "A", {}),
        ]
        assert compute_trend(snaps) == "improving"

    def test_degrading(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 90.0, "A", {}),
            ScoreSnapshot("t2", 85.0, "B", {}),
            ScoreSnapshot("t3", 82.0, "B", {}),
        ]
        assert compute_trend(snaps) == "degrading"

    def test_stable(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 85.0, "B", {}),
            ScoreSnapshot("t2", 85.5, "B", {}),
            ScoreSnapshot("t3", 86.0, "B", {}),
        ]
        assert compute_trend(snaps) == "stable"

    def test_custom_threshold(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 85.0, "B", {}),
            ScoreSnapshot("t2", 88.0, "B", {}),
        ]
        # Default threshold=2.0 -> improving (delta=3.0)
        assert compute_trend(snaps) == "improving"
        # Higher threshold -> stable
        assert compute_trend(snaps, threshold=5.0) == "stable"

    def test_window_limits(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 60.0, "D", {}),  # Outside window=3
            ScoreSnapshot("t2", 85.0, "B", {}),
            ScoreSnapshot("t3", 86.0, "B", {}),
            ScoreSnapshot("t4", 87.0, "B", {}),
        ]
        # Window=3 uses last 3 (85, 86, 87) -> stable
        assert compute_trend(snaps, window=3) == "stable"
        # Window=4 uses all 4 (60->87) -> improving
        assert compute_trend(snaps, window=4) == "improving"


class TestComputeDimensionTrends:
    """Tests for compute_dimension_trends."""

    def test_insufficient_data(self) -> None:
        assert compute_dimension_trends([]) == {}

    def test_per_dimension(self) -> None:
        snaps = [
            ScoreSnapshot(
                "t1",
                80.0,
                "B",
                {
                    "field_coverage": 70.0,
                    "field_validity": 90.0,
                },
            ),
            ScoreSnapshot(
                "t2",
                85.0,
                "B",
                {
                    "field_coverage": 80.0,
                    "field_validity": 88.0,
                },
            ),
        ]
        trends = compute_dimension_trends(snaps)
        assert trends["field_coverage"] == "improving"
        assert trends["field_validity"] == "stable"

    def test_missing_dimension_in_one(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 80.0, "B", {"field_coverage": 70.0}),
            ScoreSnapshot(
                "t2",
                85.0,
                "B",
                {
                    "field_coverage": 80.0,
                    "vlm_accuracy": 90.0,
                },
            ),
        ]
        trends = compute_dimension_trends(snaps)
        assert trends["field_coverage"] == "improving"
        assert trends["vlm_accuracy"] == "insufficient_data"

    def test_degrading_dimension(self) -> None:
        snaps = [
            ScoreSnapshot("t1", 90.0, "A", {"field_validity": 95.0}),
            ScoreSnapshot("t2", 85.0, "B", {"field_validity": 80.0}),
        ]
        trends = compute_dimension_trends(snaps)
        assert trends["field_validity"] == "degrading"
