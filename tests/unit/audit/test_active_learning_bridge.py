"""Tests for active learning bridge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.active_learning_bridge import (
    RelabelCandidate,
    build_relabel_queue,
    load_criticality_map,
    scan_vlm_accuracy,
    write_relabel_queue,
)


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    """Create results with mixed VLM accuracy scores."""
    # Good VLM accuracy
    ds_good = tmp_path / "good-ds"
    ds_good.mkdir()
    (ds_good / "scorecard.json").write_text(
        json.dumps(
            {
                "dataset": "good-ds",
                "grade": "A",
                "dimension_scores": {"vlm_accuracy": 95.0},
            }
        ),
        encoding="utf-8",
    )

    # Low VLM accuracy
    ds_low = tmp_path / "low-ds"
    ds_low.mkdir()
    (ds_low / "scorecard.json").write_text(
        json.dumps(
            {
                "dataset": "low-ds",
                "grade": "D",
                "dimension_scores": {"vlm_accuracy": 8.3},
            }
        ),
        encoding="utf-8",
    )

    # No VLM accuracy (null)
    ds_null = tmp_path / "null-ds"
    ds_null.mkdir()
    (ds_null / "scorecard.json").write_text(
        json.dumps(
            {
                "dataset": "null-ds",
                "grade": "B",
                "dimension_scores": {"vlm_accuracy": None},
            }
        ),
        encoding="utf-8",
    )

    return tmp_path


class TestScanVlmAccuracy:
    """Tests for scan_vlm_accuracy."""

    def test_scans_all_datasets(self, results_dir: Path) -> None:
        entries = scan_vlm_accuracy(results_dir=results_dir)
        assert len(entries) == 3

    def test_extracts_vlm_accuracy(self, results_dir: Path) -> None:
        entries = scan_vlm_accuracy(results_dir=results_dir)
        by_name = {e["dataset"]: e for e in entries}
        assert by_name["good-ds"]["vlm_accuracy"] == 95.0
        assert by_name["low-ds"]["vlm_accuracy"] == 8.3
        assert by_name["null-ds"]["vlm_accuracy"] is None

    def test_empty_dir(self, tmp_path: Path) -> None:
        entries = scan_vlm_accuracy(results_dir=tmp_path)
        assert entries == []


class TestBuildRelabelQueue:
    """Tests for build_relabel_queue."""

    def test_flags_low_accuracy(self, results_dir: Path) -> None:
        candidates = build_relabel_queue(threshold=60.0, results_dir=results_dir)
        datasets = {c.dataset for c in candidates}
        assert "low-ds" in datasets
        assert "good-ds" not in datasets

    def test_flags_null_accuracy(self, results_dir: Path) -> None:
        candidates = build_relabel_queue(threshold=60.0, results_dir=results_dir)
        datasets = {c.dataset for c in candidates}
        assert "null-ds" in datasets

    def test_sorted_by_priority(self, results_dir: Path) -> None:
        candidates = build_relabel_queue(threshold=60.0, results_dir=results_dir)
        priorities = [c.priority for c in candidates]
        assert priorities == sorted(priorities, reverse=True)

    def test_custom_threshold(self, results_dir: Path) -> None:
        # Very high threshold catches everything
        candidates = build_relabel_queue(threshold=100.0, results_dir=results_dir)
        assert len(candidates) == 3  # All flagged

    def test_criticality_affects_priority(self, results_dir: Path) -> None:
        # Add criticality data
        crit_data = {
            "datasets": {
                "low-ds": {"criticality": 5},
                "null-ds": {"criticality": 1},
            }
        }
        (results_dir / "training_criticality.json").write_text(
            json.dumps(crit_data), encoding="utf-8"
        )
        candidates = build_relabel_queue(threshold=60.0, results_dir=results_dir)
        by_name = {c.dataset: c for c in candidates}
        # low-ds has higher criticality -> higher priority
        assert by_name["low-ds"].priority > by_name["null-ds"].priority


class TestWriteRelabelQueue:
    """Tests for write_relabel_queue."""

    def test_writes_json(self, tmp_path: Path) -> None:
        candidates = [
            RelabelCandidate(
                dataset="test",
                vlm_accuracy=40.0,
                overall_grade="D",
                training_criticality=3,
                priority=60.0,
                reason="Low accuracy",
            )
        ]
        path = write_relabel_queue(candidates, output_path=tmp_path / "queue.json")
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_candidates"] == 1
        assert data["candidates"][0]["dataset"] == "test"


class TestLoadCriticalityMap:
    """Tests for load_criticality_map."""

    def test_loads_map(self, tmp_path: Path) -> None:
        crit_data = {
            "datasets": {
                "ds1": {"criticality": 4},
                "ds2": {"criticality": 2},
            }
        }
        (tmp_path / "training_criticality.json").write_text(
            json.dumps(crit_data), encoding="utf-8"
        )
        result = load_criticality_map(results_dir=tmp_path)
        assert result["ds1"] == 4
        assert result["ds2"] == 2

    def test_missing_file(self, tmp_path: Path) -> None:
        result = load_criticality_map(results_dir=tmp_path)
        assert result == {}
