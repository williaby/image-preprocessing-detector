"""Tests for portfolio analytics dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.portfolio_analytics import (
    build_portfolio_analytics,
    compute_field_statistics,
    compute_grade_distribution,
    generate_csv,
    generate_html,
    generate_json,
    identify_systemic_gaps,
    load_all_coverage,
    load_dataset_coverage,
    write_outputs,
)


@pytest.fixture
def screening_a() -> dict:
    """Screening data for dataset A."""
    return {
        "dataset": "dataset-a",
        "total_samples": 100,
        "per_field_results": {
            "split": {"pass": 100, "fail": 0, "fail_rate_pct": 0.0},
            "domain_level1": {"pass": 90, "fail": 10, "fail_rate_pct": 10.0},
            "iso639_language": {"pass": 95, "fail": 5, "fail_rate_pct": 5.0},
        },
    }


@pytest.fixture
def screening_b() -> dict:
    """Screening data for dataset B with worse coverage."""
    return {
        "dataset": "dataset-b",
        "total_samples": 200,
        "per_field_results": {
            "split": {"pass": 200, "fail": 0, "fail_rate_pct": 0.0},
            "domain_level1": {"pass": 100, "fail": 100, "fail_rate_pct": 50.0},
            "iso639_language": {"pass": 120, "fail": 80, "fail_rate_pct": 40.0},
        },
    }


@pytest.fixture
def screening_c() -> dict:
    """Screening data for dataset C with bad domain coverage."""
    return {
        "dataset": "dataset-c",
        "total_samples": 50,
        "per_field_results": {
            "split": {"pass": 50, "fail": 0, "fail_rate_pct": 0.0},
            "domain_level1": {"pass": 10, "fail": 40, "fail_rate_pct": 80.0},
            "iso639_language": {"pass": 45, "fail": 5, "fail_rate_pct": 10.0},
        },
    }


@pytest.fixture
def results_dir(
    tmp_path: Path,
    screening_a: dict,
    screening_b: dict,
    screening_c: dict,
) -> Path:
    """Create a results directory with 3 datasets."""
    for screening, grade, score in [
        (screening_a, "A", 92.0),
        (screening_b, "D", 65.0),
        (screening_c, "B", 82.0),
    ]:
        ds = screening["dataset"]
        ds_dir = tmp_path / ds
        ds_dir.mkdir()
        (ds_dir / "automated_screening.json").write_text(
            json.dumps(screening), encoding="utf-8"
        )
        scorecard = {"grade": grade, "overall_score": score}
        (ds_dir / "scorecard.json").write_text(json.dumps(scorecard), encoding="utf-8")

    return tmp_path


class TestLoadDatasetCoverage:
    """Tests for load_dataset_coverage."""

    def test_loads_coverage(self, results_dir: Path) -> None:
        coverage = load_dataset_coverage(results_dir / "dataset-a")
        assert coverage is not None
        assert coverage.dataset == "dataset-a"
        assert coverage.grade == "A"
        assert coverage.field_pass_rates["split"] == 100.0
        assert coverage.field_pass_rates["domain_level1"] == 90.0
        assert coverage.total_samples == 100

    def test_missing_screening(self, tmp_path: Path) -> None:
        ds_dir = tmp_path / "empty-ds"
        ds_dir.mkdir()
        coverage = load_dataset_coverage(ds_dir)
        assert coverage is None


class TestLoadAllCoverage:
    """Tests for load_all_coverage."""

    def test_loads_all(self, results_dir: Path) -> None:
        coverages = load_all_coverage(results_dir=results_dir)
        assert len(coverages) == 3
        datasets = {c.dataset for c in coverages}
        assert "dataset-a" in datasets
        assert "dataset-b" in datasets

    def test_empty_dir(self, tmp_path: Path) -> None:
        coverages = load_all_coverage(results_dir=tmp_path)
        assert coverages == []


class TestComputeFieldStatistics:
    """Tests for compute_field_statistics."""

    def test_computes_stats(self, results_dir: Path) -> None:
        coverages = load_all_coverage(results_dir=results_dir)
        stats = compute_field_statistics(coverages)
        assert len(stats) > 0

        # Find domain_level1 stats
        domain_stat = next(s for s in stats if s.field_name == "domain_level1")
        # Dataset A: 90%, B: 50%, C: 20%
        assert domain_stat.mean_pass_rate == pytest.approx(53.33, abs=0.1)
        assert domain_stat.min_pass_rate == 20.0
        assert domain_stat.max_pass_rate == 90.0
        assert domain_stat.datasets_below_75 == 2

    def test_sorted_worst_first(self, results_dir: Path) -> None:
        coverages = load_all_coverage(results_dir=results_dir)
        stats = compute_field_statistics(coverages)
        means = [s.mean_pass_rate for s in stats]
        assert means == sorted(means)

    def test_empty_datasets(self) -> None:
        stats = compute_field_statistics([])
        assert stats == []


class TestComputeGradeDistribution:
    """Tests for compute_grade_distribution."""

    def test_counts_grades(self, results_dir: Path) -> None:
        coverages = load_all_coverage(results_dir=results_dir)
        dist = compute_grade_distribution(coverages)
        assert dist["A"] == 1
        assert dist["B"] == 1
        assert dist["D"] == 1


class TestIdentifySystemicGaps:
    """Tests for identify_systemic_gaps."""

    def test_finds_gaps(self, results_dir: Path) -> None:
        coverages = load_all_coverage(results_dir=results_dir)
        stats = compute_field_statistics(coverages)
        gaps = identify_systemic_gaps(stats, min_failing_datasets=2)
        # domain_level1 has 2 datasets below 75%
        field_names = [g["field"] for g in gaps]
        assert "domain_level1" in field_names

    def test_no_gaps_high_threshold(self, results_dir: Path) -> None:
        coverages = load_all_coverage(results_dir=results_dir)
        stats = compute_field_statistics(coverages)
        gaps = identify_systemic_gaps(stats, min_failing_datasets=10)
        assert gaps == []


class TestGenerateCSV:
    """Tests for CSV generation."""

    def test_generates_csv(self, results_dir: Path) -> None:
        analytics = build_portfolio_analytics(results_dir=results_dir)
        csv_str = generate_csv(analytics)
        assert "dataset" in csv_str
        assert "dataset-a" in csv_str
        assert "MEAN" in csv_str

    def test_empty_analytics(self) -> None:
        from scripts.audit.portfolio_analytics import PortfolioAnalytics

        analytics = PortfolioAnalytics()
        csv_str = generate_csv(analytics)
        assert csv_str == ""


class TestGenerateHTML:
    """Tests for HTML generation."""

    def test_generates_html(self, results_dir: Path) -> None:
        analytics = build_portfolio_analytics(results_dir=results_dir)
        html = generate_html(analytics)
        assert "<!DOCTYPE html>" in html
        assert "dataset-a" in html
        assert "MEAN" in html
        assert "#27ae60" in html or "#e74c3c" in html  # has colors

    def test_empty_analytics(self) -> None:
        from scripts.audit.portfolio_analytics import PortfolioAnalytics

        analytics = PortfolioAnalytics()
        html = generate_html(analytics)
        assert "No data" in html


class TestGenerateJSON:
    """Tests for JSON generation."""

    def test_generates_json(self, results_dir: Path) -> None:
        analytics = build_portfolio_analytics(results_dir=results_dir)
        data = generate_json(analytics)
        assert data["total_datasets"] == 3
        assert len(data["field_statistics"]) > 0
        assert len(data["datasets"]) == 3


class TestWriteOutputs:
    """Tests for file writing."""

    def test_writes_all_formats(self, results_dir: Path, tmp_path: Path) -> None:
        analytics = build_portfolio_analytics(results_dir=results_dir)
        output_dir = tmp_path / "output"
        written = write_outputs(analytics, output_dir=output_dir, formats={"all"})
        assert len(written) == 3
        assert (output_dir / "portfolio_heatmap.csv").exists()
        assert (output_dir / "portfolio_heatmap.html").exists()
        assert (output_dir / "portfolio_analytics.json").exists()

    def test_writes_single_format(self, results_dir: Path, tmp_path: Path) -> None:
        analytics = build_portfolio_analytics(results_dir=results_dir)
        output_dir = tmp_path / "output"
        written = write_outputs(analytics, output_dir=output_dir, formats={"csv"})
        assert len(written) == 1
        assert (output_dir / "portfolio_heatmap.csv").exists()
