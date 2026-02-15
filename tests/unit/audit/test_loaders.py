"""Tests for consolidated data loaders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit.integration.loaders import (
    compute_text_statistics,
    load_enrichment_by_image_id,
    load_language_enrichment,
    load_llm_enrichment,
    load_resolution_labels,
    load_results_by_filename,
    load_skew_labels,
    load_vlm_enrichment,
    load_vlm_text_labels,
)


@pytest.fixture
def sample_enrichment_json(tmp_path: Path) -> Path:
    """Create a sample enrichment JSON file."""
    data = {
        "samples": [
            {"image_id": "sample_001", "domain_level1": "SCI", "confidence": 0.9},
            {"image_id": "sample_002", "domain_level1": "FIN", "confidence": 0.8},
            {"image_id": "", "domain_level1": "UNK"},
        ]
    }
    path = tmp_path / "test_enrichment.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def sample_results_json(tmp_path: Path) -> Path:
    """Create a sample results JSON file."""
    data = {
        "results": [
            {
                "image_path": "/data/img/sample_001.jpg",
                "skew_angle": 2.5,
                "confidence": 0.95,
            },
            {
                "image_path": "/data/img/sample_002.png",
                "skew_angle": 0.1,
                "confidence": 0.99,
            },
            {
                "image_path": "/data/img/sample_003.jpg",
                "error": "Processing failed",
            },
        ],
        "metadata": {"version": "1.0"},
    }
    path = tmp_path / "test_results.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def sample_vlm_enrichment_json(tmp_path: Path) -> Path:
    """Create a sample VLM enrichment JSON file."""
    data = {
        "samples": {
            "sample_001": {"domain": "SCI", "has_table": True},
            "sample_002": {"domain": "FIN", "has_table": False},
        }
    }
    path = tmp_path / "vlm_enrichment.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def sample_vlm_text_labels_json(tmp_path: Path) -> Path:
    """Create a sample VLM text labels JSON file."""
    data = {
        "labels": [
            {"image_id": "train/sample_001", "transcription": "Hello world"},
            {"image_id": "sample_002", "transcription": "Test text"},
            {"image_id": "", "transcription": "Empty ID"},
        ]
    }
    path = tmp_path / "text_labels.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestLoadEnrichmentByImageId:
    """Tests for generic enrichment loader."""

    def test_loads_and_indexes(self, sample_enrichment_json: Path) -> None:
        result = load_enrichment_by_image_id(sample_enrichment_json, "test enrichment")
        assert len(result) == 2
        assert "sample_001" in result
        assert "sample_002" in result
        assert result["sample_001"]["domain_level1"] == "SCI"

    def test_skips_empty_image_id(self, sample_enrichment_json: Path) -> None:
        result = load_enrichment_by_image_id(sample_enrichment_json, "test enrichment")
        assert len(result) == 2

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_enrichment_by_image_id(tmp_path / "nonexistent.json", "missing")
        assert result == {}

    def test_custom_keys(self, tmp_path: Path) -> None:
        data = {"records": [{"file_id": "abc", "value": 1}]}
        path = tmp_path / "custom.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = load_enrichment_by_image_id(
            path, "custom", samples_key="records", id_key="file_id"
        )
        assert len(result) == 1
        assert "abc" in result


class TestLoadLlmEnrichment:
    """Tests for LLM enrichment loader."""

    def test_delegates_to_generic(self, sample_enrichment_json: Path) -> None:
        result = load_llm_enrichment(sample_enrichment_json)
        assert len(result) == 2

    def test_missing_file(self, tmp_path: Path) -> None:
        result = load_llm_enrichment(tmp_path / "missing.json")
        assert result == {}


class TestLoadLanguageEnrichment:
    """Tests for language enrichment loader."""

    def test_delegates_to_generic(self, sample_enrichment_json: Path) -> None:
        result = load_language_enrichment(sample_enrichment_json)
        assert len(result) == 2


class TestLoadResultsByFilename:
    """Tests for results loader indexed by filename."""

    def test_loads_and_indexes_by_filename(self, sample_results_json: Path) -> None:
        result = load_results_by_filename(sample_results_json, "skew labels")
        assert len(result) == 2
        assert "sample_001.jpg" in result
        assert "sample_002.png" in result

    def test_skips_error_records(self, sample_results_json: Path) -> None:
        result = load_results_by_filename(sample_results_json, "skew labels")
        assert "sample_003.jpg" not in result

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_results_by_filename(tmp_path / "nonexistent.json", "missing")
        assert result == {}


class TestLoadSkewLabels:
    """Tests for skew labels loader."""

    def test_delegates_to_results_loader(self, sample_results_json: Path) -> None:
        result = load_skew_labels(sample_results_json)
        assert len(result) == 2


class TestLoadResolutionLabels:
    """Tests for resolution labels loader."""

    def test_delegates_to_results_loader(self, sample_results_json: Path) -> None:
        result = load_resolution_labels(sample_results_json)
        assert len(result) == 2


class TestLoadVlmEnrichment:
    """Tests for VLM enrichment loader."""

    def test_loads_pre_indexed(self, sample_vlm_enrichment_json: Path) -> None:
        result = load_vlm_enrichment(sample_vlm_enrichment_json)
        assert len(result) == 2
        assert result["sample_001"]["domain"] == "SCI"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_vlm_enrichment(tmp_path / "missing.json")
        assert result == {}


class TestLoadVlmTextLabels:
    """Tests for VLM text transcription labels loader."""

    def test_loads_and_indexes_by_stem(self, sample_vlm_text_labels_json: Path) -> None:
        result = load_vlm_text_labels(sample_vlm_text_labels_json)
        assert len(result) == 2
        assert "sample_001" in result
        assert "sample_002" in result

    def test_extracts_stem_from_path(self, sample_vlm_text_labels_json: Path) -> None:
        result = load_vlm_text_labels(sample_vlm_text_labels_json)
        assert result["sample_001"]["transcription"] == "Hello world"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = load_vlm_text_labels(tmp_path / "missing.json")
        assert result == {}


class TestComputeTextStatistics:
    """Tests for compute_text_statistics function."""

    def test_basic_text(self) -> None:
        stats = compute_text_statistics("Hello world\nThis is a test")
        assert stats["char_count"] == 26
        assert stats["word_count"] == 6
        assert stats["line_count"] == 2
        assert stats["has_content"] is True
        assert "avg_line_length" in stats

    def test_empty_text(self) -> None:
        stats = compute_text_statistics("")
        assert stats["char_count"] == 0
        assert stats["has_content"] is False

    def test_none_text(self) -> None:
        stats = compute_text_statistics(None)  # type: ignore[arg-type]
        assert stats["has_content"] is False

    def test_whitespace_only(self) -> None:
        stats = compute_text_statistics("   \n  \n  ")
        assert stats["has_content"] is False

    def test_devanagari_detection(self) -> None:
        stats = compute_text_statistics("Hello नमस्ते world")
        assert stats["devanagari_char_count"] == 6
        assert stats["latin_word_count"] == 2

    def test_cjk_detection(self) -> None:
        stats = compute_text_statistics("Hello 你好世界 test")
        assert stats["cjk_char_count"] == 4
        assert stats["latin_word_count"] == 2

    def test_arabic_detection(self) -> None:
        stats = compute_text_statistics("Hello مرحبا test")
        assert stats["arabic_char_count"] == 5
        assert stats["latin_word_count"] == 2

    def test_no_script_keys_when_zero(self) -> None:
        stats = compute_text_statistics("Hello world")
        assert "devanagari_char_count" not in stats
        assert "cjk_char_count" not in stats
        assert "arabic_char_count" not in stats

    def test_multiline_avg_length(self) -> None:
        stats = compute_text_statistics("abcde\nfgh\n\nij")
        assert stats["line_count"] == 3
        assert stats["avg_line_length"] == pytest.approx(3.3, abs=0.1)
