"""Tests for training criticality computation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.compute_training_criticality import (
    CriticalityResult,
    DatasetReference,
    compute_criticality,
    load_config,
    parse_task_index,
    write_criticality_report,
)


@pytest.fixture
def config() -> dict:
    """Create a test config."""
    return {
        "role_weights": {
            "primary": 2.0,
            "supplementary": 1.0,
            "benchmark": 0.5,
        },
        "section_markers": {
            "primary": ["## Primary", "## Core"],
            "supplementary": ["## Additional", "## Supplementary"],
            "benchmark": ["## Benchmark", "## Evaluation"],
        },
        "scale_thresholds": {
            5: 6.0,
            4: 4.0,
            3: 2.0,
            2: 1.0,
            1: 0.0,
        },
        "overrides": {},
    }


@pytest.fixture
def task_index_content() -> str:
    """Create a task index markdown content."""
    return """\
# IQA Training Datasets

## Primary IQA Datasets

| Dataset | Images | Link |
|---------|--------|------|
| ohr-bench | 8,561 | [ohr-bench.md](../source/ohr-bench.md) |
| diqa-5000 | 5,500 | [diqa-5000.md](../source/diqa-5000.md) |

## Additional Datasets

| Dataset | Images | Link |
|---------|--------|------|
| tobacco800 | 1,290 | [tobacco800.md](../source/tobacco800.md) |
| dibco | 343 | [dibco.md](../source/dibco.md) |
"""


@pytest.fixture
def layout_index_content() -> str:
    """Create a layout task index markdown."""
    return """\
# Layout Detection Datasets

## Primary

| Dataset | Images | Link |
|---------|--------|------|
| doclaynet | 81,000 | [doclaynet.md](../source/doclaynet.md) |
| ohr-bench | 8,561 | [ohr-bench.md](../source/ohr-bench.md) |

## Benchmark

| Dataset | Images | Link |
|---------|--------|------|
| omnidocbench | 5,000 | [omnidocbench.md](../source/omnidocbench.md) |
"""


@pytest.fixture
def indices_dir(
    tmp_path: Path, task_index_content: str, layout_index_content: str
) -> Path:
    """Create a directory with task index files."""
    idx_dir = tmp_path / "indices"
    idx_dir.mkdir()
    (idx_dir / "IQA.md").write_text(task_index_content, encoding="utf-8")
    (idx_dir / "LAYOUT.md").write_text(layout_index_content, encoding="utf-8")
    return idx_dir


class TestParseTaskIndex:
    """Tests for parse_task_index."""

    def test_parses_primary_datasets(self, indices_dir: Path, config: dict) -> None:
        refs = parse_task_index(indices_dir / "IQA.md", config)
        primary_refs = [r for r in refs if r.role == "primary"]
        datasets = {r.dataset for r in primary_refs}
        assert "ohr-bench" in datasets
        assert "diqa-5000" in datasets

    def test_parses_supplementary_datasets(
        self, indices_dir: Path, config: dict
    ) -> None:
        refs = parse_task_index(indices_dir / "IQA.md", config)
        supp_refs = [r for r in refs if r.role == "supplementary"]
        datasets = {r.dataset for r in supp_refs}
        assert "tobacco800" in datasets

    def test_primary_weight(self, indices_dir: Path, config: dict) -> None:
        refs = parse_task_index(indices_dir / "IQA.md", config)
        ohr = next(r for r in refs if r.dataset == "ohr-bench")
        assert ohr.weight == 2.0

    def test_supplementary_weight(self, indices_dir: Path, config: dict) -> None:
        refs = parse_task_index(indices_dir / "IQA.md", config)
        tobacco = next(r for r in refs if r.dataset == "tobacco800")
        assert tobacco.weight == 1.0

    def test_benchmark_weight(self, indices_dir: Path, config: dict) -> None:
        refs = parse_task_index(indices_dir / "LAYOUT.md", config)
        bench_refs = [r for r in refs if r.role == "benchmark"]
        assert len(bench_refs) > 0
        assert bench_refs[0].weight == 0.5

    def test_missing_file(self, tmp_path: Path, config: dict) -> None:
        refs = parse_task_index(tmp_path / "nonexistent.md", config)
        assert refs == []

    def test_no_duplicates_per_index(self, indices_dir: Path, config: dict) -> None:
        refs = parse_task_index(indices_dir / "IQA.md", config)
        datasets = [r.dataset for r in refs]
        assert len(datasets) == len(set(datasets))


class TestComputeCriticality:
    """Tests for compute_criticality."""

    def test_multi_task_primary_high_criticality(self, config: dict) -> None:
        refs = [
            DatasetReference("ohr-bench", "IQA", "primary", 2.0),
            DatasetReference("ohr-bench", "LAYOUT", "primary", 2.0),
            DatasetReference("ohr-bench", "TABLES", "primary", 2.0),
        ]
        results = compute_criticality(refs, config)
        assert results["ohr-bench"].criticality == 5
        assert results["ohr-bench"].weighted_score == 6.0

    def test_single_primary_criticality_3(self, config: dict) -> None:
        refs = [
            DatasetReference("tobacco800", "IQA", "primary", 2.0),
        ]
        results = compute_criticality(refs, config)
        assert results["tobacco800"].criticality == 3

    def test_supplementary_only_criticality_2(self, config: dict) -> None:
        refs = [
            DatasetReference("dibco", "IQA", "supplementary", 1.0),
        ]
        results = compute_criticality(refs, config)
        assert results["dibco"].criticality == 2

    def test_manual_override(self, config: dict) -> None:
        config_with_override = {**config, "overrides": {"dibco": 5}}
        refs = [
            DatasetReference("dibco", "IQA", "supplementary", 1.0),
        ]
        results = compute_criticality(refs, config_with_override)
        assert results["dibco"].criticality == 5

    def test_task_count(self, config: dict) -> None:
        refs = [
            DatasetReference("ohr-bench", "IQA", "primary", 2.0),
            DatasetReference("ohr-bench", "LAYOUT", "primary", 2.0),
        ]
        results = compute_criticality(refs, config)
        assert results["ohr-bench"].task_count == 2


class TestWriteCriticalityReport:
    """Tests for write_criticality_report."""

    def test_writes_report(self, tmp_path: Path) -> None:
        results = {
            "ds1": CriticalityResult(
                dataset="ds1",
                weighted_score=4.0,
                criticality=4,
                references=[
                    DatasetReference("ds1", "IQA", "primary", 2.0),
                    DatasetReference("ds1", "LAYOUT", "primary", 2.0),
                ],
                task_count=2,
            )
        }
        output_path = tmp_path / "criticality.json"
        path = write_criticality_report(results, output_path=output_path)
        assert path.exists()
        with path.open() as f:
            data = json.load(f)
        assert data["total_datasets"] == 1
        assert data["datasets"]["ds1"]["criticality"] == 4


class TestLoadConfig:
    """Tests for config loading."""

    def test_loads_real_config(self) -> None:
        config_path = Path(
            "/home/byron/dev/image_detection/config/training_criticality.yaml"
        )
        if not config_path.exists():
            pytest.skip("Config not available")
        config = load_config(config_path)
        assert "role_weights" in config
        assert "scale_thresholds" in config
