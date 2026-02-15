"""Tests for BaseIntegrationScript."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.integration.base import BaseIntegrationScript
from scripts.audit.integration.config import DatasetIntegrationConfig


@pytest.fixture
def minimal_metadata(tmp_path: Path) -> Path:
    """Create a minimal metadata JSON for testing."""
    data = {
        "dataset_name": "test-dataset",
        "samples": [
            {
                "source": {
                    "original_filename": "test/sample_001.jpg",
                    "split": "train",
                },
                "original_labels": {
                    "language_code": "en",
                    "iso15924_script_code": "Latn",
                },
                "enrichments": {
                    "current_version": 1,
                    "versions": [
                        {
                            "version": 1,
                            "data": {
                                "layout_detections": [
                                    {
                                        "class_name": "text",
                                        "confidence": 0.9,
                                    }
                                ],
                                "domain_level1": "SCI",
                                "domain_confidence": 0.5,
                                "text_scope": "printed",
                                "image_properties_color_mode": "color",
                            },
                        }
                    ],
                },
            },
            {
                "source": {
                    "original_filename": "test/sample_002.png",
                    "split": "val",
                },
                "original_labels": {},
                "enrichments": {
                    "current_version": 1,
                    "versions": [
                        {
                            "version": 1,
                            "data": {
                                "layout_detections": [],
                                "text_scope": "printed",
                                "image_properties_color_mode": "grayscale",
                            },
                        }
                    ],
                },
            },
        ],
    }
    path = tmp_path / "json" / "test-dataset_metadata.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


@pytest.fixture
def llm_enrichment(tmp_path: Path) -> None:
    """Create LLM enrichment data."""
    data = {
        "samples": [
            {
                "image_id": "sample_001",
                "domain_level1": "SCI",
                "domain_confidence": 0.85,
                "content_type": "research_paper",
                "capture_method": "born_digital",
                "capture_confidence": 0.7,
                "iso639_language": "en",
                "iso15924_script": "Latn",
            },
        ]
    }
    path = tmp_path / "json" / "test-dataset_llm_enrichment.json"
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def lang_enrichment(tmp_path: Path) -> None:
    """Create language enrichment data."""
    data = {
        "samples": [
            {
                "image_id": "sample_001",
                "language": "en",
                "script": "Latn",
                "confidence": 0.88,
            },
        ]
    }
    path = tmp_path / "json" / "test-dataset_language_enrichment.json"
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def test_config() -> DatasetIntegrationConfig:
    """Create a test integration config."""
    return DatasetIntegrationConfig(
        dataset_name="test-dataset",
        is_synthetic=False,
        doc_language="en",
        doc_script="Latn",
    )


class TestBaseIntegrationScript:
    """Tests for BaseIntegrationScript."""

    def test_init(self, test_config: DatasetIntegrationConfig) -> None:
        script = BaseIntegrationScript(test_config)
        assert script.config.dataset_name == "test-dataset"
        assert script.metadata == {}

    def test_load_sources(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        assert len(script.metadata["samples"]) == 2
        assert "sample_001" in script.llm_index

    def test_integrate_sample(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        sample = script.metadata["samples"][0]
        result = script.integrate_sample(sample)

        assert result["dataset_short_code"] == "test-dataset"
        assert result["iso639_language"] == "en"
        assert result["layout_detections"][0]["class_name"] == "Text"
        assert "sample_reliability_summary" in result
        assert "field_confidence_provenance" in result

    def test_run_dry_run(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        stats = script.run(dry_run=True)

        assert stats["total"] == 2
        assert stats["integrated"] == 2
        assert stats["llm_matched"] == 1
        # Verify metadata was NOT modified (dry run)
        sample = script.metadata["samples"][0]
        assert len(sample["enrichments"]["versions"]) == 1

    def test_run_writes_enrichment(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        stats = script.run(dry_run=False)

        assert stats["integrated"] == 2
        sample = script.metadata["samples"][0]
        assert sample["enrichments"]["current_version"] == 2
        versions = sample["enrichments"]["versions"]
        new_version = next(v for v in versions if v["version"] == 2)
        assert "BaseIntegrationScript" in new_version["description"]

    def test_domain_from_llm(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        result = script.integrate_sample(script.metadata["samples"][0])
        assert result["domain_level1"] == "SCI"
        assert result["domain_confidence"] == 0.85

    def test_domain_fallback_without_llm(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        # sample_002 has no LLM enrichment
        result = script.integrate_sample(script.metadata["samples"][1])
        assert result["domain_level1"] == "UNK"

    def test_language_from_parser_gt(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        # sample_001 has parser GT language "en" at 0.95
        result = script.integrate_sample(script.metadata["samples"][0])
        assert result["iso639_language"] == "en"
        assert result["language_confidence"] == 0.95
        assert result["text_scope_detection_method"] == "parser_gt"

    def test_capture_method_from_doc(
        self,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        config = DatasetIntegrationConfig(
            dataset_name="test-dataset",
            known_capture_method="scanner_flatbed",
        )
        script = BaseIntegrationScript(config, registry_dir=minimal_metadata)
        script.load_sources()
        result = script.integrate_sample(script.metadata["samples"][0])
        assert result["capture_method"] == "scanner_flatbed"
        assert result["capture_confidence"] == 1.0

    def test_synthetic_overrides(
        self,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        config = DatasetIntegrationConfig(
            dataset_name="test-dataset",
            is_synthetic=True,
            known_capture_method="synthetic",
        )
        script = BaseIntegrationScript(config, registry_dir=minimal_metadata)
        script.load_sources()
        result = script.integrate_sample(script.metadata["samples"][0])
        assert result["capture_method"] == "synthetic"
        assert result["has_handwriting"] is False

    def test_stats_distributions(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        stats = script.run(dry_run=True)
        assert "domain_dist" in stats
        assert "lang_dist" in stats
        assert stats["domain_dist"]["SCI"] >= 1

    def test_write_output(
        self,
        test_config: DatasetIntegrationConfig,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        script = BaseIntegrationScript(test_config, registry_dir=minimal_metadata)
        script.load_sources()
        script.run(dry_run=False)

        output_path = minimal_metadata / "output.json"
        script.write_output(output_path)

        assert output_path.exists()
        with open(output_path) as f:
            written = json.load(f)
        assert len(written["samples"]) == 2

    def test_from_yaml(
        self,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
        tmp_path: Path,
    ) -> None:
        import yaml

        config_data = {
            "dataset_name": "test-dataset",
            "doc_language": "en",
        }
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(yaml.dump(config_data), encoding="utf-8")

        script = BaseIntegrationScript.from_yaml(
            config_path, registry_dir=minimal_metadata
        )
        script.load_sources()
        stats = script.run(dry_run=True)
        assert stats["total"] == 2


class TestBaseIntegrationScriptKI001:
    """Tests for KI-001 layout casing in base integration."""

    def test_docling_labels_standardized(
        self,
        minimal_metadata: Path,
        llm_enrichment: None,
        lang_enrichment: None,
    ) -> None:
        config = DatasetIntegrationConfig(dataset_name="test-dataset")
        script = BaseIntegrationScript(config, registry_dir=minimal_metadata)
        script.load_sources()
        result = script.integrate_sample(script.metadata["samples"][0])
        # "text" should be standardized to "Text"
        assert result["layout_detections"][0]["class_name"] == "Text"
        assert result["layout_detections"][0]["source_label"] == "text"
