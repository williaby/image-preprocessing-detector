"""Tests for auto-discovery registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit.auto_discover import (
    build_discovered_config,
    discover_metadata_files,
    get_dataset_config,
    list_all_datasets,
    merge_known_and_discovered,
    normalize_dataset_name,
)


class TestNormalizeDatasetName:
    """Tests for normalize_dataset_name."""

    def test_underscore_to_hyphen(self) -> None:
        assert normalize_dataset_name("diqa_5000_metadata.json") == "diqa-5000"

    def test_hyphen_preserved(self) -> None:
        assert normalize_dataset_name("ohr-bench_metadata.json") == "ohr-bench"

    def test_multi_underscore(self) -> None:
        assert (
            normalize_dataset_name("hindi_ocr_synthetic_metadata.json")
            == "hindi-ocr-synthetic"
        )

    def test_simple_name(self) -> None:
        assert normalize_dataset_name("funsd_metadata.json") == "funsd"


class TestDiscoverMetadataFiles:
    """Tests for discover_metadata_files."""

    def test_discovers_files(self, tmp_path: Path) -> None:
        (tmp_path / "alpha_metadata.json").write_text("{}", encoding="utf-8")
        (tmp_path / "beta_test_metadata.json").write_text("{}", encoding="utf-8")
        # Non-metadata file should be ignored
        (tmp_path / "gamma_enrichment.json").write_text("{}", encoding="utf-8")

        result = discover_metadata_files(tmp_path)
        assert "alpha" in result
        assert "beta-test" in result
        assert len(result) == 2

    def test_empty_dir(self, tmp_path: Path) -> None:
        result = discover_metadata_files(tmp_path)
        assert result == {}

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        result = discover_metadata_files(tmp_path / "nonexistent")
        assert result == {}

    def test_paths_are_absolute(self, tmp_path: Path) -> None:
        (tmp_path / "test_metadata.json").write_text("{}", encoding="utf-8")
        result = discover_metadata_files(tmp_path)
        assert result["test"].is_absolute()


class TestBuildDiscoveredConfig:
    """Tests for build_discovered_config."""

    def test_basic_config(self, tmp_path: Path) -> None:
        meta = tmp_path / "test_metadata.json"
        meta.write_text("{}", encoding="utf-8")

        cfg = build_discovered_config("test", meta)
        assert cfg.dataset_name == "test"
        assert cfg.metadata_json_path == meta

    def test_detects_enrichment_files(self, tmp_path: Path) -> None:
        meta = tmp_path / "test_metadata.json"
        meta.write_text("{}", encoding="utf-8")
        llm = tmp_path / "test_llm_enrichment.json"
        llm.write_text("{}", encoding="utf-8")
        lang = tmp_path / "test_language_enrichment.json"
        lang.write_text("{}", encoding="utf-8")

        cfg = build_discovered_config("test", meta)
        assert cfg.llm_enrichment_path == llm
        assert cfg.language_enrichment_path == lang

    def test_missing_enrichment_files(self, tmp_path: Path) -> None:
        meta = tmp_path / "test_metadata.json"
        meta.write_text("{}", encoding="utf-8")

        cfg = build_discovered_config("test", meta)
        assert cfg.llm_enrichment_path is None
        assert cfg.language_enrichment_path is None

    def test_custom_image_root(self, tmp_path: Path) -> None:
        meta = tmp_path / "test_metadata.json"
        meta.write_text("{}", encoding="utf-8")
        img_root = tmp_path / "images"

        cfg = build_discovered_config("test", meta, image_root=img_root)
        assert cfg.image_base_path == img_root


class TestMergeKnownAndDiscovered:
    """Tests for merge_known_and_discovered."""

    def test_includes_known_datasets(self, tmp_path: Path) -> None:
        # Empty metadata dir -> only known configs
        result = merge_known_and_discovered(metadata_root=tmp_path)
        assert "jssoda" in result
        assert "doclaynet" in result

    def test_adds_discovered_datasets(self, tmp_path: Path) -> None:
        (tmp_path / "brand_new_metadata.json").write_text("{}", encoding="utf-8")
        result = merge_known_and_discovered(metadata_root=tmp_path)
        assert "brand-new" in result
        assert result["brand-new"].dataset_name == "brand-new"

    def test_known_takes_precedence(self, tmp_path: Path) -> None:
        # Create a metadata file for a known dataset
        (tmp_path / "jssoda_metadata.json").write_text("{}", encoding="utf-8")
        result = merge_known_and_discovered(metadata_root=tmp_path)
        # Should use the known config, not the discovered one
        cfg = result["jssoda"]
        assert cfg.llm_enrichment_path is not None  # Known config has this


class TestListAllDatasets:
    """Tests for list_all_datasets."""

    def test_includes_known(self, tmp_path: Path) -> None:
        datasets = list_all_datasets(metadata_root=tmp_path)
        assert "jssoda" in datasets
        assert "doclaynet" in datasets

    def test_includes_discovered(self, tmp_path: Path) -> None:
        (tmp_path / "new_dataset_metadata.json").write_text("{}", encoding="utf-8")
        datasets = list_all_datasets(metadata_root=tmp_path)
        assert "new-dataset" in datasets

    def test_sorted(self, tmp_path: Path) -> None:
        datasets = list_all_datasets(metadata_root=tmp_path)
        assert datasets == sorted(datasets)

    def test_no_duplicates(self, tmp_path: Path) -> None:
        # Create metadata for a known dataset
        (tmp_path / "jssoda_metadata.json").write_text("{}", encoding="utf-8")
        datasets = list_all_datasets(metadata_root=tmp_path)
        assert datasets.count("jssoda") == 1


class TestGetDatasetConfig:
    """Tests for get_dataset_config."""

    def test_known_dataset(self, tmp_path: Path) -> None:
        cfg = get_dataset_config("jssoda", metadata_root=tmp_path)
        assert cfg.dataset_name == "jssoda"

    def test_discovered_dataset(self, tmp_path: Path) -> None:
        (tmp_path / "novel_metadata.json").write_text("{}", encoding="utf-8")
        cfg = get_dataset_config("novel", metadata_root=tmp_path)
        assert cfg.dataset_name == "novel"
        assert cfg.metadata_json_path == tmp_path / "novel_metadata.json"

    def test_unknown_dataset_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown dataset"):
            get_dataset_config("does-not-exist", metadata_root=tmp_path)

    def test_sample_size_override(self, tmp_path: Path) -> None:
        cfg = get_dataset_config("jssoda", metadata_root=tmp_path, sample_size=100)
        assert cfg.sample_size == 100
