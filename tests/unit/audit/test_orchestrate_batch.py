"""Tests for agent orchestration protocol."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.orchestrate_batch import (
    AuditTask,
    check_handoff_ready,
    compute_priority,
    detect_audit_phase,
    generate_batch_status,
    load_orchestration_config,
    plan_batch,
    write_batch_status,
)


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    """Create a results directory with mixed datasets."""
    # Complete dataset (A grade)
    ds_a = tmp_path / "good-dataset"
    ds_a.mkdir()
    (ds_a / "scorecard.json").write_text(
        json.dumps({"grade": "A", "overall_score": 92.0}), encoding="utf-8"
    )
    (ds_a / "automated_screening.json").write_text("{}", encoding="utf-8")
    (ds_a / "compliance_report.json").write_text("{}", encoding="utf-8")

    # D grade dataset (partial)
    ds_d = tmp_path / "bad-dataset"
    ds_d.mkdir()
    (ds_d / "scorecard.json").write_text(
        json.dumps({"grade": "D", "overall_score": 68.0}), encoding="utf-8"
    )
    (ds_d / "automated_screening.json").write_text("{}", encoding="utf-8")

    # Unaudited dataset
    ds_new = tmp_path / "new-dataset"
    ds_new.mkdir()

    return tmp_path


class TestCheckHandoffReady:
    """Tests for check_handoff_ready."""

    def test_ready_when_all_artifacts_present(self, results_dir: Path) -> None:
        ready, missing = check_handoff_ready("good-dataset", results_dir=results_dir)
        assert ready is True
        assert missing == []

    def test_not_ready_when_missing(self, results_dir: Path) -> None:
        ready, missing = check_handoff_ready("new-dataset", results_dir=results_dir)
        assert ready is False
        assert "scorecard.json" in missing

    def test_custom_artifacts(self, results_dir: Path) -> None:
        ready, missing = check_handoff_ready(
            "good-dataset",
            results_dir=results_dir,
            required_artifacts=["scorecard.json", "nonexistent.json"],
        )
        assert ready is False
        assert "nonexistent.json" in missing


class TestDetectAuditPhase:
    """Tests for detect_audit_phase."""

    def test_complete(self, results_dir: Path) -> None:
        assert detect_audit_phase("good-dataset", results_dir=results_dir) == "complete"

    def test_prescreening(self, results_dir: Path) -> None:
        assert (
            detect_audit_phase("bad-dataset", results_dir=results_dir) == "complete"
        )  # Has scorecard

    def test_unaudited(self, results_dir: Path) -> None:
        assert detect_audit_phase("new-dataset", results_dir=results_dir) == "unaudited"

    def test_nonexistent(self, results_dir: Path) -> None:
        assert detect_audit_phase("nonexistent", results_dir=results_dir) == "unaudited"

    def test_prescreening_only(self, tmp_path: Path) -> None:
        ds = tmp_path / "ds"
        ds.mkdir()
        (ds / "automated_screening.json").write_text("{}", encoding="utf-8")
        assert detect_audit_phase("ds", results_dir=tmp_path) == "prescreening"

    def test_partial(self, tmp_path: Path) -> None:
        ds = tmp_path / "ds"
        ds.mkdir()
        (ds / "automated_screening.json").write_text("{}", encoding="utf-8")
        (ds / "compliance_report.json").write_text("{}", encoding="utf-8")
        assert detect_audit_phase("ds", results_dir=tmp_path) == "partial"


class TestComputePriority:
    """Tests for compute_priority."""

    def test_base_criticality(self) -> None:
        assert compute_priority("A", 3) == 3.0

    def test_d_grade_boost(self) -> None:
        config = {"priority": {"grade_boost": {"D": 2, "F": 3}}}
        assert compute_priority("D", 3, config=config) == 5.0

    def test_f_grade_boost(self) -> None:
        config = {"priority": {"grade_boost": {"D": 2, "F": 3}}}
        assert compute_priority("F", 1, config=config) == 4.0

    def test_no_config(self) -> None:
        assert compute_priority("B", 2) == 2.0


class TestPlanBatch:
    """Tests for plan_batch."""

    def test_discovers_datasets(self, results_dir: Path) -> None:
        tasks = plan_batch(results_dir=results_dir)
        datasets = {t.dataset for t in tasks}
        assert "good-dataset" in datasets
        assert "bad-dataset" in datasets
        # new-dataset has no scorecard, so not discovered
        assert "new-dataset" not in datasets

    def test_explicit_datasets(self, results_dir: Path) -> None:
        tasks = plan_batch(datasets=["good-dataset"], results_dir=results_dir)
        assert len(tasks) == 1
        assert tasks[0].dataset == "good-dataset"

    def test_sorted_by_priority(self, results_dir: Path) -> None:
        config = {"priority": {"grade_boost": {"D": 2, "F": 3}}}
        tasks = plan_batch(results_dir=results_dir, config=config)
        priorities = [t.priority for t in tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_priority_min_filter(self, results_dir: Path) -> None:
        tasks = plan_batch(results_dir=results_dir, priority_min=999.0)
        assert tasks == []


class TestGenerateBatchStatus:
    """Tests for generate_batch_status."""

    def test_summary_fields(self) -> None:
        tasks = [
            AuditTask(
                dataset="ds1",
                current_grade="A",
                audit_phase="complete",
                handoff_ready=True,
            ),
            AuditTask(
                dataset="ds2",
                current_grade="D",
                audit_phase="prescreening",
                handoff_ready=False,
            ),
        ]
        status = generate_batch_status(tasks)
        assert status["total_datasets"] == 2
        assert status["audit_complete"] == 1
        assert status["handoff_ready"] == 1
        assert status["grade_distribution"]["A"] == 1
        assert status["grade_distribution"]["D"] == 1

    def test_tasks_serialized(self) -> None:
        tasks = [AuditTask(dataset="ds1")]
        status = generate_batch_status(tasks)
        assert len(status["tasks"]) == 1
        assert status["tasks"][0]["dataset"] == "ds1"


class TestWriteBatchStatus:
    """Tests for write_batch_status."""

    def test_writes_json(self, tmp_path: Path) -> None:
        tasks = [AuditTask(dataset="test-ds", current_grade="B")]
        path = write_batch_status(tasks, results_dir=tmp_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_datasets"] == 1


class TestLoadOrchestrationConfig:
    """Tests for load_orchestration_config."""

    def test_loads_real_config(self) -> None:
        cfg = load_orchestration_config()
        assert "agents" in cfg
        assert "layer2-audit-agent" in cfg["agents"]

    def test_missing_config(self, tmp_path: Path) -> None:
        cfg = load_orchestration_config(tmp_path / "nonexistent.yaml")
        assert cfg == {}
