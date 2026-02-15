"""Tests for cross-dataset regression checking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.regression_check import (
    DatasetRegressionReport,
    FieldDelta,
    check_dataset,
    compute_deltas,
    cross_reference_known_issues,
    load_baseline,
    load_known_issues,
    load_screening,
    save_baseline,
    write_regression_report,
    write_summary_report,
)


@pytest.fixture
def screening_data() -> dict:
    """Create a realistic screening result dict."""
    return {
        "dataset": "test-dataset",
        "audited_at": "2026-02-14T10:00:00+00:00",
        "total_samples": 100,
        "per_field_results": {
            "split": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
            "capture_method": {"pass": 95, "fail": 5, "fail_rate_pct": 5.0},
            "domain_level1": {"pass": 80, "fail": 20, "fail_rate_pct": 20.0},
            "iso639_language": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
            "script_family": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
            "layout_detections": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
        },
    }


@pytest.fixture
def regressed_screening_data() -> dict:
    """Create screening data with regressions from the baseline."""
    return {
        "dataset": "test-dataset",
        "audited_at": "2026-02-14T12:00:00+00:00",
        "total_samples": 100,
        "per_field_results": {
            "split": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
            "capture_method": {"pass": 95, "fail": 5, "fail_rate_pct": 5.0},
            "domain_level1": {"pass": 60, "fail": 40, "fail_rate_pct": 40.0},
            "iso639_language": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
            "script_family": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
            "layout_detections": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
        },
    }


@pytest.fixture
def improved_screening_data() -> dict:
    """Create screening data with improvements from the baseline."""
    return {
        "dataset": "test-dataset",
        "audited_at": "2026-02-14T12:00:00+00:00",
        "total_samples": 100,
        "per_field_results": {
            "split": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
            "capture_method": {"pass": 95, "fail": 5, "fail_rate_pct": 5.0},
            "domain_level1": {"pass": 95, "fail": 5, "fail_rate_pct": 5.0},
            "iso639_language": {"pass": 99, "fail": 1, "fail_rate_pct": 1.0},
            "script_family": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
            "layout_detections": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
        },
    }


@pytest.fixture
def ki_json() -> dict:
    """Create a minimal known issues advisory."""
    return {
        "issues": [
            {"id": "KI-001", "title": "Layout casing", "severity": "CRITICAL"},
            {"id": "KI-007", "title": "Domain UNK", "severity": "HIGH"},
            {"id": "KI-009", "title": "Language priority", "severity": "MEDIUM"},
        ]
    }


@pytest.fixture
def results_dir(tmp_path: Path, screening_data: dict, ki_json: dict) -> Path:
    """Create a results directory with screening and KI data."""
    ds_dir = tmp_path / "test-dataset"
    ds_dir.mkdir()
    (ds_dir / "automated_screening.json").write_text(
        json.dumps(screening_data), encoding="utf-8"
    )
    (tmp_path / "CROSS_DATASET_KNOWN_ISSUES.json").write_text(
        json.dumps(ki_json), encoding="utf-8"
    )
    return tmp_path


class TestFieldDelta:
    """Tests for FieldDelta dataclass."""

    def test_create_regression(self) -> None:
        delta = FieldDelta(
            field_name="domain_level1",
            baseline_fail_rate=5.0,
            current_fail_rate=15.0,
            delta=10.0,
            is_regression=True,
            related_ki="KI-007",
        )
        assert delta.is_regression is True
        assert delta.related_ki == "KI-007"

    def test_create_improvement(self) -> None:
        delta = FieldDelta(
            field_name="split",
            baseline_fail_rate=10.0,
            current_fail_rate=2.0,
            delta=-8.0,
            is_regression=False,
        )
        assert delta.is_regression is False
        assert delta.related_ki is None


class TestDatasetRegressionReport:
    """Tests for DatasetRegressionReport."""

    def test_to_dict(self) -> None:
        report = DatasetRegressionReport(
            dataset="test",
            has_baseline=True,
            regressions_found=1,
            field_deltas=[
                FieldDelta("split", 0.0, 0.0, 0.0, False),
            ],
        )
        result = report.to_dict()
        assert result["dataset"] == "test"
        assert result["regressions_found"] == 1
        assert len(result["field_deltas"]) == 1

    def test_empty_report(self) -> None:
        report = DatasetRegressionReport(dataset="empty")
        result = report.to_dict()
        assert result["has_baseline"] is False
        assert result["field_deltas"] == []


class TestBaselineManagement:
    """Tests for baseline save/load."""

    def test_load_baseline_missing(self, tmp_path: Path) -> None:
        result = load_baseline("nonexistent", results_dir=tmp_path)
        assert result is None

    def test_save_and_load_baseline(self, tmp_path: Path, screening_data: dict) -> None:
        save_baseline("test-ds", screening_data, results_dir=tmp_path)
        loaded = load_baseline("test-ds", results_dir=tmp_path)
        assert loaded is not None
        assert loaded["dataset"] == "test-dataset"
        assert "baseline_created_at" in loaded

    def test_load_screening(self, results_dir: Path) -> None:
        screening = load_screening("test-dataset", results_dir=results_dir)
        assert screening is not None
        assert screening["dataset"] == "test-dataset"

    def test_load_screening_missing(self, tmp_path: Path) -> None:
        result = load_screening("missing", results_dir=tmp_path)
        assert result is None


class TestComputeDeltas:
    """Tests for compute_deltas."""

    def test_no_change(self, screening_data: dict) -> None:
        deltas = compute_deltas(screening_data, screening_data)
        assert all(d.delta == 0.0 for d in deltas)
        assert all(d.is_regression is False for d in deltas)

    def test_regression_detected(
        self, screening_data: dict, regressed_screening_data: dict
    ) -> None:
        deltas = compute_deltas(screening_data, regressed_screening_data)
        domain_delta = next(d for d in deltas if d.field_name == "domain_level1")
        assert domain_delta.delta == 20.0
        assert domain_delta.is_regression is True

    def test_improvement_detected(
        self, screening_data: dict, improved_screening_data: dict
    ) -> None:
        deltas = compute_deltas(screening_data, improved_screening_data)
        domain_delta = next(d for d in deltas if d.field_name == "domain_level1")
        assert domain_delta.delta == -15.0
        assert domain_delta.is_regression is False

    def test_custom_threshold(
        self, screening_data: dict, regressed_screening_data: dict
    ) -> None:
        # With threshold=25, the 20pp regression should not flag
        deltas = compute_deltas(
            screening_data, regressed_screening_data, threshold=25.0
        )
        domain_delta = next(d for d in deltas if d.field_name == "domain_level1")
        assert domain_delta.is_regression is False

    def test_new_field_in_current(self, screening_data: dict) -> None:
        current = {**screening_data}
        current["per_field_results"] = {
            **screening_data["per_field_results"],
            "new_field": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
        }
        deltas = compute_deltas(screening_data, current)
        new_delta = next(d for d in deltas if d.field_name == "new_field")
        assert new_delta.baseline_fail_rate == 0.0
        assert new_delta.current_fail_rate == 10.0


class TestCrossReferenceKnownIssues:
    """Tests for KI cross-referencing."""

    def test_annotates_matching_fields(self, ki_json: dict) -> None:
        ki_index = {issue["id"]: issue for issue in ki_json["issues"]}
        deltas = [
            FieldDelta("domain_level1", 5.0, 15.0, 10.0, True),
            FieldDelta("split", 0.0, 0.0, 0.0, False),
        ]
        annotated = cross_reference_known_issues(deltas, ki_index)
        assert annotated[0].related_ki == "KI-007"
        assert annotated[1].related_ki is None

    def test_no_ki_file(self) -> None:
        deltas = [FieldDelta("split", 0.0, 0.0, 0.0, False)]
        annotated = cross_reference_known_issues(deltas, ki_index={})
        assert annotated[0].related_ki is None

    def test_multiple_ki_for_field(self) -> None:
        ki_index = {
            "KI-002": {"id": "KI-002"},
            "KI-003": {"id": "KI-003"},
            "KI-004": {"id": "KI-004"},
            "KI-006": {"id": "KI-006"},
        }
        deltas = [
            FieldDelta("content_flags_boolean", 0.0, 10.0, 10.0, True),
        ]
        annotated = cross_reference_known_issues(deltas, ki_index)
        assert "KI-002" in annotated[0].related_ki
        assert "KI-003" in annotated[0].related_ki


class TestLoadKnownIssues:
    """Tests for load_known_issues."""

    def test_loads_from_file(self, results_dir: Path) -> None:
        ki_path = results_dir / "CROSS_DATASET_KNOWN_ISSUES.json"
        ki_index = load_known_issues(ki_path)
        assert "KI-001" in ki_index
        assert "KI-007" in ki_index

    def test_missing_file(self, tmp_path: Path) -> None:
        ki_index = load_known_issues(tmp_path / "nonexistent.json")
        assert ki_index == {}


class TestCheckDataset:
    """Tests for check_dataset end-to-end."""

    def test_no_baseline(self, results_dir: Path) -> None:
        report = check_dataset("test-dataset", results_dir=results_dir)
        assert report.has_baseline is False
        assert report.regressions_found == 0

    def test_with_baseline_no_regression(
        self, results_dir: Path, screening_data: dict
    ) -> None:
        save_baseline("test-dataset", screening_data, results_dir=results_dir)
        report = check_dataset("test-dataset", results_dir=results_dir)
        assert report.has_baseline is True
        assert report.regressions_found == 0

    def test_with_baseline_regression(
        self,
        results_dir: Path,
        screening_data: dict,
        regressed_screening_data: dict,
    ) -> None:
        save_baseline("test-dataset", screening_data, results_dir=results_dir)
        # Overwrite current screening with regressed data
        (results_dir / "test-dataset" / "automated_screening.json").write_text(
            json.dumps(regressed_screening_data), encoding="utf-8"
        )
        report = check_dataset("test-dataset", results_dir=results_dir)
        assert report.has_baseline is True
        assert report.regressions_found == 1

    def test_missing_dataset(self, tmp_path: Path) -> None:
        report = check_dataset("nonexistent", results_dir=tmp_path)
        assert report.has_baseline is False


class TestWriteReports:
    """Tests for report writing."""

    def test_write_regression_report(self, tmp_path: Path) -> None:
        report = DatasetRegressionReport(
            dataset="test-ds",
            has_baseline=True,
            regressions_found=1,
        )
        path = write_regression_report(report, results_dir=tmp_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["dataset"] == "test-ds"

    def test_write_summary_report(self, tmp_path: Path) -> None:
        reports = [
            DatasetRegressionReport(dataset="ds1", has_baseline=True),
            DatasetRegressionReport(
                dataset="ds2", has_baseline=True, regressions_found=2
            ),
        ]
        path = write_summary_report(reports, results_dir=tmp_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_datasets"] == 2
        assert data["datasets_with_regressions"] == 1
