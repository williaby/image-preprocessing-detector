"""Tests for scripts/measure_dataset_sufficiency.py - Dataset sufficiency measurement.

These tests verify the dataset sufficiency measurement script correctly:
- Determines sufficiency status
- Counts files and annotations
- Calculates FR requirements
- Generates reports
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

# Scripts directory added to sys.path via tests/conftest.py
from measure_dataset_sufficiency import (
    DatasetInventory,
    DatasetSufficiencyMeasurer,
    FRRequirement,
    SufficiencyReport,
    SufficiencyStatus,
)


class TestSufficiencyStatus:
    """Tests for SufficiencyStatus enum."""

    def test_sufficient_status(self) -> None:
        """Test SUFFICIENT status value."""
        assert SufficiencyStatus.SUFFICIENT.value == "✅ SUFFICIENT"

    def test_partial_status(self) -> None:
        """Test PARTIAL status value."""
        assert SufficiencyStatus.PARTIAL.value == "⚠️ PARTIAL"

    def test_critical_gap_status(self) -> None:
        """Test CRITICAL_GAP status value."""
        assert SufficiencyStatus.CRITICAL_GAP.value == "❌ CRITICAL GAP"

    def test_not_measured_status(self) -> None:
        """Test NOT_MEASURED status value."""
        assert SufficiencyStatus.NOT_MEASURED.value == "🔍 NOT MEASURED"


class TestFRRequirement:
    """Tests for FRRequirement dataclass."""

    def test_create_requirement(self) -> None:
        """Test creating FR requirement."""
        req = FRRequirement(
            fr_id="FR-2.1",
            name="Document Classification",
            min_samples=10000,
            status=SufficiencyStatus.SUFFICIENT,
            current_count=15000,
            notes="Test notes",
        )

        assert req.fr_id == "FR-2.1"
        assert req.min_samples == 10000
        assert req.current_count == 15000
        assert req.status == SufficiencyStatus.SUFFICIENT

    def test_default_values(self) -> None:
        """Test default values are set."""
        req = FRRequirement(
            fr_id="FR-1.0",
            name="Test",
            min_samples=100,
        )

        assert req.status == SufficiencyStatus.NOT_MEASURED
        assert req.current_count == 0
        assert req.real_world_count == 0
        assert req.synthetic_count == 0
        assert req.notes == ""
        assert req.cost_estimate is None


class TestSufficiencyReport:
    """Tests for SufficiencyReport dataclass."""

    def test_create_report(self) -> None:
        """Test creating sufficiency report."""
        report = SufficiencyReport()

        assert report.fr_requirements == {}
        assert report.layout_class_coverage == {}
        assert isinstance(report.dqs_routing_matrix, np.ndarray)
        assert report.dqs_routing_matrix.shape == (3, 3)
        assert report.total_cost_estimate == pytest.approx(0.0)
        assert report.overall_status == SufficiencyStatus.NOT_MEASURED


class TestDatasetInventory:
    """Tests for DatasetInventory dataclass."""

    def test_create_inventory(self, tmp_path: Path) -> None:
        """Test creating dataset inventory."""
        inventory = DatasetInventory(
            doclaynet_path=tmp_path / "doclaynet",
            tablebank_path=tmp_path / "tablebank",
            signatr6k_path=tmp_path / "signatr6k",
            wili2018_path=tmp_path / "wili2018",
            phase2_iqa_path=tmp_path / "phase2_iqa",
            iam_handwriting_path=tmp_path / "iam",
            omnidocbench_path=tmp_path / "omnidocbench",
            pubtabnet_path=tmp_path / "pubtabnet",
            fintabnet_path=tmp_path / "fintabnet",
            invoices_kaggle_path=tmp_path / "invoices",
            mobile_receipts_path=tmp_path / "receipts",
            receipts_hitl_path=tmp_path / "hitl",
            docsynth300k_path=tmp_path / "docsynth",
            docbank_path=tmp_path / "docbank",
            nist_sd2_path=tmp_path / "nist",
            docile_path=tmp_path / "docile",
        )

        assert inventory.doclaynet_path == tmp_path / "doclaynet"
        assert inventory.tablebank_path == tmp_path / "tablebank"


class TestDatasetSufficiencyMeasurer:
    """Tests for DatasetSufficiencyMeasurer class."""

    @pytest.fixture
    def mock_inventory(self, tmp_path: Path) -> DatasetInventory:
        """Create mock dataset inventory."""
        return DatasetInventory(
            doclaynet_path=tmp_path / "doclaynet",
            tablebank_path=tmp_path / "tablebank",
            signatr6k_path=tmp_path / "signatr6k",
            wili2018_path=tmp_path / "wili2018",
            phase2_iqa_path=tmp_path / "phase2_iqa",
            iam_handwriting_path=tmp_path / "iam",
            omnidocbench_path=tmp_path / "omnidocbench",
            pubtabnet_path=tmp_path / "pubtabnet",
            fintabnet_path=tmp_path / "fintabnet",
            invoices_kaggle_path=tmp_path / "invoices",
            mobile_receipts_path=tmp_path / "receipts",
            receipts_hitl_path=tmp_path / "hitl",
            docsynth300k_path=tmp_path / "docsynth",
            docbank_path=tmp_path / "docbank",
            nist_sd2_path=tmp_path / "nist",
            docile_path=tmp_path / "docile",
        )

    def test_init(self, mock_inventory: DatasetInventory) -> None:
        """Test measurer initialization."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        assert measurer.inventory == mock_inventory
        assert isinstance(measurer.report, SufficiencyReport)

    def test_determine_sufficiency_status_sufficient(
        self, mock_inventory: DatasetInventory
    ) -> None:
        """Test determining SUFFICIENT status."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        status = measurer._determine_sufficiency_status(100, 100)

        assert status == SufficiencyStatus.SUFFICIENT

    def test_determine_sufficiency_status_partial(
        self, mock_inventory: DatasetInventory
    ) -> None:
        """Test determining PARTIAL status."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        status = measurer._determine_sufficiency_status(60, 100)

        assert status == SufficiencyStatus.PARTIAL

    def test_determine_sufficiency_status_critical(
        self, mock_inventory: DatasetInventory
    ) -> None:
        """Test determining CRITICAL_GAP status."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        status = measurer._determine_sufficiency_status(30, 100)

        assert status == SufficiencyStatus.CRITICAL_GAP

    def test_count_image_files(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test counting image files."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        # Create test directory with images
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "img1.png").write_text("png")
        (images_dir / "img2.jpg").write_text("jpg")
        (images_dir / "doc.txt").write_text("txt")

        count = measurer._count_image_files(images_dir)

        assert count == 2

    def test_count_image_files_recursive(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test counting image files recursively."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        # Create nested directory structure
        images_dir = tmp_path / "images"
        subdir = images_dir / "subdir"
        subdir.mkdir(parents=True)
        (images_dir / "img1.png").write_text("png")
        (subdir / "img2.jpg").write_text("jpg")

        count = measurer._count_image_files_recursive(images_dir)

        assert count == 2

    def test_count_image_files_empty_dir(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test counting images in empty directory."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        count = measurer._count_image_files(empty_dir)

        assert count == 0

    def test_count_image_files_nonexistent_dir(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test counting images in nonexistent directory."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        count = measurer._count_image_files(tmp_path / "nonexistent")

        assert count == 0

    def test_load_json_labels(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test loading JSON labels."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        labels_file = tmp_path / "labels.json"
        labels_data = [{"id": 1}, {"id": 2}]
        labels_file.write_text(json.dumps(labels_data))

        result = measurer._load_json_labels(labels_file)

        assert len(result) == 2

    def test_load_json_labels_missing_file(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test loading labels from missing file."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        result = measurer._load_json_labels(tmp_path / "missing.json")

        assert result == []

    def test_count_coco_annotations(
        self, mock_inventory: DatasetInventory, tmp_path: Path
    ) -> None:
        """Test counting COCO annotations."""
        measurer = DatasetSufficiencyMeasurer(mock_inventory)

        coco_dir = tmp_path / "coco"
        coco_dir.mkdir()

        coco_data = {
            "annotations": [
                {"category_id": 1},
                {"category_id": 1},
                {"category_id": 2},
            ]
        }
        (coco_dir / "train.json").write_text(json.dumps(coco_data))

        counts = measurer._count_coco_annotations(coco_dir)

        assert counts[1] == 2
        assert counts[2] == 1


class TestDoclaynetClassMinimums:
    """Tests for DocLayNet class minimums."""

    def test_class_minimums_defined(self) -> None:
        """Test that class minimums are defined."""
        minimums = DatasetSufficiencyMeasurer.DOCLAYNET_CLASS_MINIMUMS

        assert len(minimums) == 11
        assert 1 in minimums
        assert 11 in minimums

    def test_class_minimums_values(self) -> None:
        """Test specific class minimum values."""
        minimums = DatasetSufficiencyMeasurer.DOCLAYNET_CLASS_MINIMUMS

        assert minimums[1] == 5000  # Text
        assert minimums[4] == 3000  # Table


class TestDqsRoutingMinimums:
    """Tests for DQS routing minimums."""

    def test_routing_minimums_defined(self) -> None:
        """Test that routing minimums are defined."""
        minimums = DatasetSufficiencyMeasurer.DQS_ROUTING_MINIMUMS

        assert len(minimums) == 9  # 3x3 grid

    def test_routing_minimums_coverage(self) -> None:
        """Test that all 3x3 grid cells are covered."""
        minimums = DatasetSufficiencyMeasurer.DQS_ROUTING_MINIMUMS

        for i in range(3):
            for j in range(3):
                assert (i, j) in minimums


class TestGenerateMarkdownReport:
    """Tests for generate_markdown_report function."""

    def test_generates_report_file(self, tmp_path: Path) -> None:
        """Test that markdown report is generated."""
        from measure_dataset_sufficiency import generate_markdown_report

        report = SufficiencyReport()
        report.fr_requirements["FR-1.0"] = FRRequirement(
            fr_id="FR-1.0",
            name="Test Requirement",
            min_samples=1000,
            current_count=500,
            status=SufficiencyStatus.PARTIAL,
        )

        output_file = tmp_path / "report.md"
        generate_markdown_report(report, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "Dataset Sufficiency Report" in content
        assert "FR-1.0" in content


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from measure_dataset_sufficiency import main

        assert callable(main)
