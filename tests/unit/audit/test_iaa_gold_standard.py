"""Tests for IAA gold standard framework."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.iaa_gold_standard import (
    IAAConfig,
    IAAReport,
    compute_cohens_kappa,
    compute_iaa_from_labels,
    compute_pairwise_agreement,
    compute_srcc,
    load_iaa_config,
    select_samples,
    write_iaa_report,
    write_sample_set,
)


@pytest.fixture
def iaa_config() -> IAAConfig:
    """Create a minimal IAA config."""
    return IAAConfig(
        datasets=["ds1", "ds2"],
        samples_per_dataset=5,
        categorical_fields=["domain_level1", "capture_method"],
        continuous_fields=["quality_overall"],
        models=["model_a", "model_b"],
    )


class TestCohensKappa:
    """Tests for compute_cohens_kappa."""

    def test_perfect_agreement(self) -> None:
        labels = ["a", "b", "c", "a", "b"]
        assert compute_cohens_kappa(labels, labels) == pytest.approx(1.0)

    def test_no_agreement(self) -> None:
        a = ["a", "a", "a", "a"]
        b = ["b", "b", "b", "b"]
        kappa = compute_cohens_kappa(a, b)
        # Non-overlapping categories: p_o=0, p_e=0, kappa=0
        assert kappa == pytest.approx(0.0)

    def test_moderate_agreement(self) -> None:
        a = ["a", "b", "a", "b", "a", "b", "a", "b", "a", "b"]
        b = ["a", "b", "a", "a", "a", "b", "b", "b", "a", "b"]
        kappa = compute_cohens_kappa(a, b)
        assert 0.0 < kappa < 1.0

    def test_empty_lists(self) -> None:
        assert compute_cohens_kappa([], []) == 0.0

    def test_length_mismatch(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            compute_cohens_kappa(["a"], ["a", "b"])

    def test_known_value(self) -> None:
        # 20 items, 2 categories
        a = ["y"] * 15 + ["n"] * 5
        b = ["y"] * 12 + ["n"] * 3 + ["y"] * 2 + ["n"] * 3
        kappa = compute_cohens_kappa(a, b)
        # p_o=15/20=0.75, p_e=(15*14+5*6)/400=0.6, kappa=0.375
        assert kappa == pytest.approx(0.375, abs=0.01)


class TestSRCC:
    """Tests for compute_srcc."""

    def test_perfect_positive(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert compute_srcc(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_perfect_negative(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [50.0, 40.0, 30.0, 20.0, 10.0]
        assert compute_srcc(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_no_correlation(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0]
        b = [2.0, 4.0, 1.0, 3.0]
        srcc = compute_srcc(a, b)
        assert -1.0 <= srcc <= 1.0

    def test_length_mismatch(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            compute_srcc([1.0], [1.0, 2.0])

    def test_single_value(self) -> None:
        assert compute_srcc([1.0], [2.0]) == 0.0

    def test_tied_ranks(self) -> None:
        a = [1.0, 1.0, 2.0, 3.0]
        b = [1.0, 2.0, 2.0, 3.0]
        srcc = compute_srcc(a, b)
        assert 0.5 < srcc < 1.0  # High but not perfect


class TestPairwiseAgreement:
    """Tests for compute_pairwise_agreement."""

    def test_perfect(self) -> None:
        labels = ["a", "b", "c"]
        assert compute_pairwise_agreement(labels, labels) == 100.0

    def test_none(self) -> None:
        a = ["a", "a", "a"]
        b = ["b", "b", "b"]
        assert compute_pairwise_agreement(a, b) == 0.0

    def test_partial(self) -> None:
        a = ["a", "b", "c", "d"]
        b = ["a", "b", "x", "y"]
        assert compute_pairwise_agreement(a, b) == 50.0

    def test_empty(self) -> None:
        assert compute_pairwise_agreement([], []) == 0.0


class TestSelectSamples:
    """Tests for select_samples."""

    def test_correct_count(self, iaa_config: IAAConfig) -> None:
        samples = select_samples(iaa_config)
        assert len(samples) == 10  # 2 datasets * 5 samples

    def test_datasets_represented(self, iaa_config: IAAConfig) -> None:
        samples = select_samples(iaa_config)
        datasets = {s.dataset for s in samples}
        assert "ds1" in datasets
        assert "ds2" in datasets


class TestWriteSampleSet:
    """Tests for write_sample_set."""

    def test_writes_json(self, tmp_path: Path, iaa_config: IAAConfig) -> None:
        samples = select_samples(iaa_config)
        path = write_sample_set(samples, output_dir=tmp_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_samples"] == 10


class TestComputeIAAFromLabels:
    """Tests for compute_iaa_from_labels."""

    def test_computes_metrics(self, tmp_path: Path, iaa_config: IAAConfig) -> None:
        # Create label files for two models
        labels_a = {
            "img1": {
                "domain_level1": "finance",
                "capture_method": "scan",
                "quality_overall": 3.5,
            },
            "img2": {
                "domain_level1": "legal",
                "capture_method": "scan",
                "quality_overall": 2.0,
            },
            "img3": {
                "domain_level1": "finance",
                "capture_method": "photo",
                "quality_overall": 4.0,
            },
        }
        labels_b = {
            "img1": {
                "domain_level1": "finance",
                "capture_method": "scan",
                "quality_overall": 3.0,
            },
            "img2": {
                "domain_level1": "legal",
                "capture_method": "photo",
                "quality_overall": 2.5,
            },
            "img3": {
                "domain_level1": "finance",
                "capture_method": "photo",
                "quality_overall": 4.5,
            },
        }

        path_a = tmp_path / "iaa_labels_model_a.json"
        path_b = tmp_path / "iaa_labels_model_b.json"
        path_a.write_text(json.dumps({"labels": labels_a}), encoding="utf-8")
        path_b.write_text(json.dumps({"labels": labels_b}), encoding="utf-8")

        label_files = {"model_a": path_a, "model_b": path_b}
        report = compute_iaa_from_labels(label_files, iaa_config)

        assert report.total_samples == 3
        assert len(report.agreements) > 0
        assert report.overall_kappa is not None
        assert report.overall_srcc is not None

    def test_insufficient_models(self, tmp_path: Path, iaa_config: IAAConfig) -> None:
        report = compute_iaa_from_labels({}, iaa_config)
        assert report.total_samples == 0
        assert report.agreements == []


class TestWriteIAAReport:
    """Tests for write_iaa_report."""

    def test_writes_json(self, tmp_path: Path) -> None:
        report = IAAReport(
            total_samples=100,
            total_fields=10,
            overall_kappa=0.72,
            overall_srcc=0.85,
        )
        path = write_iaa_report(report, output_dir=tmp_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["overall_kappa"] == 0.72


class TestLoadIAAConfig:
    """Tests for load_iaa_config."""

    def test_loads_real_config(self) -> None:
        config = load_iaa_config()
        assert len(config.datasets) == 10
        assert config.samples_per_dataset == 10
        assert len(config.models) == 3

    def test_missing_config(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_iaa_config(tmp_path / "nonexistent.yaml")
