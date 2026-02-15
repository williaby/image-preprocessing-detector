"""Tests for batch remediation runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.batch_remediation import (
    DatasetRemediationPlan,
    EnrichmentAction,
    RemediationResult,
    build_all_remediation_plans,
    build_remediation_plan,
    execute_plan,
    identify_remediation_datasets,
    load_scorecard,
    load_screening,
    write_remediation_report,
)


@pytest.fixture
def d_grade_scorecard() -> dict:
    """Create a D-grade scorecard."""
    return {
        "dataset": "bad-dataset",
        "grade": "D",
        "overall_score": 68.5,
        "dimension_scores": {
            "field_coverage": 65.0,
            "field_validity": 80.0,
        },
    }


@pytest.fixture
def f_grade_scorecard() -> dict:
    """Create an F-grade scorecard."""
    return {
        "dataset": "terrible-dataset",
        "grade": "F",
        "overall_score": 35.0,
        "dimension_scores": {
            "field_coverage": 0.0,
        },
    }


@pytest.fixture
def b_grade_scorecard() -> dict:
    """Create a B-grade scorecard (should not be remediated)."""
    return {
        "dataset": "good-dataset",
        "grade": "B",
        "overall_score": 85.0,
    }


@pytest.fixture
def screening_with_failures() -> dict:
    """Create screening data with fields below critical threshold."""
    return {
        "dataset": "bad-dataset",
        "per_field_results": {
            "split": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
            "capture_method": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
            "domain_level1": {"pass": 40, "fail": 60, "fail_rate_pct": 60.0},
            "iso639_language": {"pass": 50, "fail": 50, "fail_rate_pct": 50.0},
            "script_family": {"pass": 50, "fail": 50, "fail_rate_pct": 50.0},
            "layout_detections": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
        },
    }


@pytest.fixture
def results_dir(
    tmp_path: Path,
    d_grade_scorecard: dict,
    f_grade_scorecard: dict,
    b_grade_scorecard: dict,
    screening_with_failures: dict,
) -> Path:
    """Create a results directory with mixed-grade datasets."""
    # D-grade dataset with screening
    bad_dir = tmp_path / "bad-dataset"
    bad_dir.mkdir()
    (bad_dir / "scorecard.json").write_text(
        json.dumps(d_grade_scorecard), encoding="utf-8"
    )
    (bad_dir / "automated_screening.json").write_text(
        json.dumps(screening_with_failures), encoding="utf-8"
    )

    # F-grade dataset without screening
    terrible_dir = tmp_path / "terrible-dataset"
    terrible_dir.mkdir()
    (terrible_dir / "scorecard.json").write_text(
        json.dumps(f_grade_scorecard), encoding="utf-8"
    )

    # B-grade dataset (should be excluded)
    good_dir = tmp_path / "good-dataset"
    good_dir.mkdir()
    (good_dir / "scorecard.json").write_text(
        json.dumps(b_grade_scorecard), encoding="utf-8"
    )

    return tmp_path


class TestEnrichmentAction:
    """Tests for EnrichmentAction dataclass."""

    def test_create(self) -> None:
        action = EnrichmentAction(
            field_name="domain_level1",
            script_path="scripts/enrich_metadata_from_llm.py",
            requires_gpu=True,
            description="LLM enrichment",
        )
        assert action.requires_gpu is True
        assert action.priority == 10


class TestIdentifyRemediationDatasets:
    """Tests for identify_remediation_datasets."""

    def test_finds_d_and_f_datasets(self, results_dir: Path) -> None:
        datasets = identify_remediation_datasets(results_dir=results_dir)
        assert "bad-dataset" in datasets
        assert "terrible-dataset" in datasets
        assert "good-dataset" not in datasets

    def test_custom_grades(self, results_dir: Path) -> None:
        datasets = identify_remediation_datasets(
            results_dir=results_dir, grades=frozenset({"F"})
        )
        assert "terrible-dataset" in datasets
        assert "bad-dataset" not in datasets

    def test_empty_results_dir(self, tmp_path: Path) -> None:
        datasets = identify_remediation_datasets(results_dir=tmp_path)
        assert datasets == []


class TestBuildRemediationPlan:
    """Tests for build_remediation_plan."""

    def test_builds_plan_with_screening(self, results_dir: Path) -> None:
        plan = build_remediation_plan("bad-dataset", results_dir=results_dir)
        assert plan.dataset == "bad-dataset"
        assert plan.current_grade == "D"
        assert plan.has_scorecard is True
        assert plan.has_screening is True
        assert "domain_level1" in plan.failing_fields
        assert "iso639_language" in plan.failing_fields
        assert len(plan.actions) > 0

    def test_builds_plan_without_screening(self, results_dir: Path) -> None:
        plan = build_remediation_plan("terrible-dataset", results_dir=results_dir)
        assert plan.has_scorecard is True
        assert plan.has_screening is False
        assert plan.failing_fields == []
        assert plan.actions == []

    def test_builds_plan_no_scorecard(self, tmp_path: Path) -> None:
        plan = build_remediation_plan("nonexistent", results_dir=tmp_path)
        assert plan.has_scorecard is False
        assert plan.current_grade == "?"

    def test_deduplicates_actions(self, results_dir: Path) -> None:
        """Domain and capture_method both map to LLM enrichment."""
        plan = build_remediation_plan("bad-dataset", results_dir=results_dir)
        script_paths = [a.script_path for a in plan.actions]
        # No duplicates
        assert len(script_paths) == len(set(script_paths))

    def test_actions_sorted_by_priority(self, results_dir: Path) -> None:
        plan = build_remediation_plan("bad-dataset", results_dir=results_dir)
        priorities = [a.priority for a in plan.actions]
        assert priorities == sorted(priorities)

    def test_requires_gpu_flag(self, results_dir: Path) -> None:
        plan = build_remediation_plan("bad-dataset", results_dir=results_dir)
        assert plan.requires_gpu is True


class TestBuildAllRemediationPlans:
    """Tests for build_all_remediation_plans."""

    def test_finds_all_eligible(self, results_dir: Path) -> None:
        plans = build_all_remediation_plans(results_dir=results_dir)
        assert len(plans) == 2
        datasets = {p.dataset for p in plans}
        assert "bad-dataset" in datasets
        assert "terrible-dataset" in datasets

    def test_specific_datasets(self, results_dir: Path) -> None:
        plans = build_all_remediation_plans(
            results_dir=results_dir, datasets=["bad-dataset"]
        )
        assert len(plans) == 1
        assert plans[0].dataset == "bad-dataset"


class TestExecutePlan:
    """Tests for execute_plan."""

    def test_dry_run(self, results_dir: Path) -> None:
        plan = build_remediation_plan("bad-dataset", results_dir=results_dir)
        result = execute_plan(plan, dry_run=True)
        assert result.success is True
        assert len(result.actions_executed) > 0
        assert result.before_grade == "D"

    def test_skip_gpu(self, results_dir: Path) -> None:
        plan = build_remediation_plan("bad-dataset", results_dir=results_dir)
        result = execute_plan(plan, dry_run=True, skip_gpu=True)
        # GPU actions should be skipped
        assert len(result.actions_skipped) > 0

    def test_empty_plan(self, results_dir: Path) -> None:
        plan = build_remediation_plan("terrible-dataset", results_dir=results_dir)
        result = execute_plan(plan, dry_run=True)
        assert result.success is True
        assert result.actions_executed == []


class TestWriteRemediationReport:
    """Tests for write_remediation_report."""

    def test_writes_plan_report(self, tmp_path: Path) -> None:
        plans = [
            DatasetRemediationPlan(
                dataset="test-ds",
                current_grade="D",
                current_score=68.5,
                failing_fields=["domain_level1"],
            )
        ]
        path = write_remediation_report(plans, results_dir=tmp_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_datasets"] == 1

    def test_writes_with_results(self, tmp_path: Path) -> None:
        plans = [DatasetRemediationPlan(dataset="test-ds", current_grade="D")]
        results = [
            RemediationResult(
                dataset="test-ds",
                before_grade="D",
                before_score=68.5,
                actions_executed=["scripts/enrich.py"],
            )
        ]
        path = write_remediation_report(plans, results, results_dir=tmp_path)
        with path.open() as f:
            data = json.load(f)
        assert "results" in data
        assert len(data["results"]) == 1


class TestLoadHelpers:
    """Tests for scorecard/screening loaders."""

    def test_load_scorecard(self, results_dir: Path) -> None:
        sc = load_scorecard("bad-dataset", results_dir=results_dir)
        assert sc is not None
        assert sc["grade"] == "D"

    def test_load_scorecard_missing(self, tmp_path: Path) -> None:
        sc = load_scorecard("nonexistent", results_dir=tmp_path)
        assert sc is None

    def test_load_screening(self, results_dir: Path) -> None:
        scr = load_screening("bad-dataset", results_dir=results_dir)
        assert scr is not None
        assert "per_field_results" in scr

    def test_load_screening_missing(self, tmp_path: Path) -> None:
        scr = load_screening("nonexistent", results_dir=tmp_path)
        assert scr is None
