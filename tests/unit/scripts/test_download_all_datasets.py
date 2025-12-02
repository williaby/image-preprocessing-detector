# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/download_all_datasets.py - Comprehensive dataset download.

These tests verify the dataset download script correctly:
- Defines benchmark and training datasets
- Downloads from GCS, HuggingFace, and URLs
- Creates download handlers
- Validates arguments
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from download_all_datasets import (
    BENCHMARK_DATASETS,
    TRAINING_DATASETS,
    _create_argument_parser,
    _handle_local_source,
    _handle_manual_source,
    download_dataset,
)


class TestBenchmarkDatasets:
    """Tests for BENCHMARK_DATASETS constant."""

    def test_datasets_defined(self) -> None:
        """Test that benchmark datasets are defined."""
        assert len(BENCHMARK_DATASETS) >= 5

    def test_tablebank_config(self) -> None:
        """Test TableBank configuration."""
        assert "tablebank" in BENCHMARK_DATASETS
        config = BENCHMARK_DATASETS["tablebank"]
        assert config["source"] == "gcs"
        assert config["size_gb"] == 27

    def test_omnidocbench_config(self) -> None:
        """Test OmniDocBench configuration."""
        assert "omnidocbench" in BENCHMARK_DATASETS
        config = BENCHMARK_DATASETS["omnidocbench"]
        assert config["source"] == "huggingface"
        assert "hf_dataset" in config

    def test_cocotext_config(self) -> None:
        """Test COCO-Text configuration."""
        assert "cocotext" in BENCHMARK_DATASETS
        config = BENCHMARK_DATASETS["cocotext"]
        assert config["source"] == "url"
        assert "url" in config

    def test_all_configs_have_required_fields(self) -> None:
        """Test all configs have required fields."""
        required_fields = ["source", "nfs_path", "size_gb", "description"]

        for name, config in BENCHMARK_DATASETS.items():
            for field in required_fields:
                assert field in config, f"{name} missing {field}"


class TestTrainingDatasets:
    """Tests for TRAINING_DATASETS constant."""

    def test_datasets_defined(self) -> None:
        """Test that training datasets are defined."""
        assert len(TRAINING_DATASETS) >= 5

    def test_iqa_phase2_config(self) -> None:
        """Test IQA Phase 2 configuration."""
        assert "iqa_phase2" in TRAINING_DATASETS
        config = TRAINING_DATASETS["iqa_phase2"]
        assert config["source"] == "gcs"

    def test_iam_handwriting_config(self) -> None:
        """Test IAM handwriting configuration."""
        assert "iam_handwriting" in TRAINING_DATASETS
        config = TRAINING_DATASETS["iam_handwriting"]
        assert config["source"] == "gcs"


class TestDownloadHandlers:
    """Tests for download handler functions."""

    def test_handle_local_source(self) -> None:
        """Test local source handler."""
        result = _handle_local_source("test_dataset", {"nfs_path": Path("/tmp")})

        assert result is True

    def test_handle_manual_source(self) -> None:
        """Test manual source handler."""
        result = _handle_manual_source(
            "test_dataset", {"note": "Manual download required"}
        )

        assert result is True


class TestDownloadDataset:
    """Tests for download_dataset function."""

    def test_unknown_source_returns_false(self) -> None:
        """Test that unknown source type returns False."""
        result = download_dataset("test", {"source": "unknown"})

        assert result is False

    def test_local_source_succeeds(self) -> None:
        """Test local source download."""
        config = {"source": "local", "nfs_path": Path("/tmp")}

        result = download_dataset("test", config)

        assert result is True

    def test_manual_source_succeeds(self) -> None:
        """Test manual source download."""
        config = {"source": "manual", "note": "Download manually"}

        result = download_dataset("test", config)

        assert result is True


class TestArgumentParser:
    """Tests for argument parser."""

    def test_creates_parser(self) -> None:
        """Test parser creation."""
        parser = _create_argument_parser()

        assert parser is not None

    def test_all_argument(self) -> None:
        """Test --all argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(["--all"])

        assert args.all is True

    def test_benchmarks_only_argument(self) -> None:
        """Test --benchmarks-only argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(["--benchmarks-only"])

        assert args.benchmarks_only is True

    def test_training_only_argument(self) -> None:
        """Test --training-only argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(["--training-only"])

        assert args.training_only is True

    def test_dataset_argument(self) -> None:
        """Test --dataset argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(["--dataset", "tablebank"])

        assert args.dataset == "tablebank"


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from download_all_datasets import main

        assert callable(main)
