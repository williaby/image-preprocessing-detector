"""Tests for dataset integration configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.audit.integration.config import (
    DatasetIntegrationConfig,
    KIMitigationConfig,
    VLMCorrections,
    load_config_from_yaml,
)


class TestDatasetIntegrationConfig:
    """Tests for DatasetIntegrationConfig."""

    def test_minimal_config(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="test-dataset")
        assert config.dataset_name == "test-dataset"
        assert config.is_synthetic is False
        assert config.known_capture_method is None
        assert config.enrichment_version_number == 2

    def test_full_config(self) -> None:
        config = DatasetIntegrationConfig(
            dataset_name="jssoda",
            is_synthetic=True,
            known_capture_method="synthetic",
            doc_language="ja",
            doc_script="Jpan",
            script_version="1.1.0",
        )
        assert config.dataset_name == "jssoda"
        assert config.is_synthetic is True
        assert config.known_capture_method == "synthetic"
        assert config.doc_language == "ja"

    def test_empty_dataset_name_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            DatasetIntegrationConfig(dataset_name="")

    def test_whitespace_dataset_name_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            DatasetIntegrationConfig(dataset_name="   ")

    def test_dataset_name_stripped(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="  jssoda  ")
        assert config.dataset_name == "jssoda"

    def test_frozen(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="test")
        with pytest.raises(Exception):  # noqa: B017
            config.dataset_name = "other"  # type: ignore[misc]

    def test_resolve_path_relative(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="test")
        registry = Path("/mnt/e/registry")
        result = config.resolve_path("json/test.json", registry)
        assert result == Path("/mnt/e/registry/json/test.json")

    def test_resolve_path_absolute(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="test")
        registry = Path("/mnt/e/registry")
        result = config.resolve_path("/absolute/path.json", registry)
        assert result == Path("/absolute/path.json")

    def test_resolve_path_none(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="test")
        registry = Path("/mnt/e/registry")
        result = config.resolve_path(None, registry)
        assert result is None

    def test_get_metadata_path_convention(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="jssoda")
        registry = Path("/mnt/e/registry")
        result = config.get_metadata_path(registry)
        assert result == Path("/mnt/e/registry/json/jssoda_metadata.json")

    def test_get_metadata_path_custom(self) -> None:
        config = DatasetIntegrationConfig(
            dataset_name="test",
            metadata_path="custom/path.json",
        )
        registry = Path("/mnt/e/registry")
        result = config.get_metadata_path(registry)
        assert result == Path("/mnt/e/registry/custom/path.json")

    def test_get_llm_enrichment_path_convention(self) -> None:
        config = DatasetIntegrationConfig(dataset_name="doclaynet")
        registry = Path("/mnt/e/registry")
        result = config.get_llm_enrichment_path(registry)
        assert result == Path("/mnt/e/registry/json/doclaynet_llm_enrichment.json")


class TestKIMitigationConfig:
    """Tests for KI mitigation configuration."""

    def test_defaults_all_true(self) -> None:
        config = KIMitigationConfig()
        assert config.apply_ki_001_layout_casing is True
        assert config.apply_ki_005_capture_override is True
        assert config.layout_source == "docling"

    def test_selective_disable(self) -> None:
        config = KIMitigationConfig(
            apply_ki_002_table_override=False,
            apply_ki_006_formula_override=False,
        )
        assert config.apply_ki_002_table_override is False
        assert config.apply_ki_006_formula_override is False
        assert config.apply_ki_001_layout_casing is True

    def test_doclayout_yolo_source(self) -> None:
        config = KIMitigationConfig(layout_source="doclayout_yolo")
        assert config.layout_source == "doclayout_yolo"


class TestVLMCorrections:
    """Tests for VLM corrections configuration."""

    def test_defaults_empty(self) -> None:
        config = VLMCorrections()
        assert len(config.table_true_positives) == 0
        assert len(config.formula_true_positives) == 0

    def test_with_values(self) -> None:
        config = VLMCorrections(
            table_true_positives=frozenset({"s1", "s2"}),
            formula_true_positives=frozenset({"s3"}),
        )
        assert "s1" in config.table_true_positives
        assert len(config.formula_true_positives) == 1


class TestLoadConfigFromYaml:
    """Tests for YAML config loading."""

    def test_loads_minimal_yaml(self, tmp_path: Path) -> None:
        config_data = {"dataset_name": "test-dataset"}
        path = tmp_path / "test.yaml"
        path.write_text(yaml.dump(config_data), encoding="utf-8")
        config = load_config_from_yaml(path)
        assert config.dataset_name == "test-dataset"

    def test_loads_full_yaml(self, tmp_path: Path) -> None:
        config_data = {
            "dataset_name": "jssoda",
            "is_synthetic": True,
            "known_capture_method": "synthetic",
            "doc_language": "ja",
            "doc_script": "Jpan",
            "ki_config": {
                "apply_ki_001_layout_casing": True,
                "layout_source": "docling",
            },
            "vlm_corrections": {
                "formula_true_positives": ["sample_537", "sample_956"],
            },
        }
        path = tmp_path / "jssoda.yaml"
        path.write_text(yaml.dump(config_data), encoding="utf-8")
        config = load_config_from_yaml(path)
        assert config.dataset_name == "jssoda"
        assert config.is_synthetic is True
        assert config.ki_config.layout_source == "docling"
        assert "sample_537" in config.vlm_corrections.formula_true_positives

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config_from_yaml(tmp_path / "nonexistent.yaml")

    def test_loads_pilot_jssoda_config(self) -> None:
        config_path = Path(
            "/home/byron/dev/image_detection/config/integration_configs/jssoda.yaml"
        )
        if not config_path.exists():
            pytest.skip("Pilot config not available")
        config = load_config_from_yaml(config_path)
        assert config.dataset_name == "jssoda"
        assert config.is_synthetic is True
        assert config.known_capture_method == "synthetic"
        assert config.doc_language == "ja"
        assert (
            "jssoda_horizontal_00537" in config.vlm_corrections.formula_true_positives
        )

    def test_loads_all_pilot_configs(self) -> None:
        config_dir = Path("/home/byron/dev/image_detection/config/integration_configs")
        if not config_dir.exists():
            pytest.skip("Config directory not available")
        yaml_files = list(config_dir.glob("*.yaml"))
        # Exclude schema doc
        yaml_files = [f for f in yaml_files if not f.name.startswith("_")]
        assert len(yaml_files) >= 5, (
            f"Expected >= 5 pilot configs, got {len(yaml_files)}"
        )
        for path in yaml_files:
            config = load_config_from_yaml(path)
            assert config.dataset_name, f"Empty dataset_name in {path.name}"
